"""MCP client for managing connections to multiple MCP servers."""

import json
import logging
from contextlib import AsyncExitStack
from datetime import timedelta
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import AnyUrl

from mcp import (
    ClientSession,
    StdioServerParameters,
)
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError
from mcp.shared.session import ProgressFnT
from mcp.types import (
    CallToolResult,
    EmptyResult,
    ErrorData,
    GetPromptResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    LoggingLevel,
    PaginatedRequestParams,
    Prompt,
    ReadResourceResult,
    Resource,
    ResourceTemplate,
    TextContent,
    Tool,
)

from .config import (
    MCPServersConfig,
    ServerConfig,
)
from .types import ServerCapabilities
from .utils import (
    configure_logging,
    format_namespace_uri,
    parse_namespace_uri,
)


# Get logger for this module
# Note: Logging configuration should be done by the application using this library.
# Users can configure logging in their application code, or use the configure_logging()
# function provided by this library.
logger = logging.getLogger(__name__)


class MultiServerClient:
    """Manages multiple MCP server connections for a MCP host.

    This class handles:
        - Connecting to multiple MCP servers
        - Discovering and aggregating server capabilities (tools, resources, templates, prompts)
        - Routing tool, prompt and resource calls to the correct server
        - Managing session lifecycles with AsyncExitStack

    The client can be used as an async context manager for automatic cleanup:

    Examples:
    ::

        Basic usage with context manager:
        >>> async with MultiServerClient.from_config("mcp_servers.json") as client:
        ...     tools = client.list_tools()
        ...     result = await client.call_tool("my_tool", {"arg": "value"})

        Manual connection management:
        >>> async with AsyncExitStack() as stack:
        ...     client = MultiServerClient("mcp_servers.json")
        ...     await client.connect_all(stack)
        ...     tools = client.list_tools()

        Programmatic configuration:
        >>> config = MCPServersConfig(mcpServers={
        ...     "my_server": ServerConfig(command="python", args=["-m", "my_server"])
        ... })
        >>> async with MultiServerClient.from_dict(config.model_dump()) as client:
        ...     tools = client.list_tools()
    """

    def __init__(self, config_path: Union[str, Path] = "mcp_servers.json") -> None:
        """Initialize the multi-server client.

        Args:
            config_path: Path to the JSON configuration file containing server definitions.
                        Defaults to "mcp_servers.json" in the current directory.

        Note:
            This constructor only sets up the configuration path. The actual connection
            to servers happens when connect_all() is called or when using the client
            as a context manager.
        """
        self.config_path = Path(config_path)
        self.sessions: Dict[str, ClientSession] = {}
        self.capabilities: Dict[str, ServerCapabilities] = {}
        self.tool_to_server: Dict[str, str] = {}
        self.prompt_to_server: Dict[str, str] = {}
        self._stack: Optional[AsyncExitStack] = None
        self._config: Optional[MCPServersConfig] = None

    @classmethod
    def from_config(cls, config_path: Union[str, Path]) -> "MultiServerClient":
        """Create a client from a configuration file path.

        This is a convenience class method that's equivalent to the regular constructor.

        Args:
            config_path: Path to the JSON configuration file.

        Returns:
            A new MultiServerClient instance.

        Examples:
            >>> client = MultiServerClient.from_config("my_servers.json")
        """
        return cls(config_path)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "MultiServerClient":
        """Create a client from a configuration dictionary.

        This method allows programmatic configuration without needing a JSON file.

        Args:
            config_dict: Dictionary containing server configurations in the same
                        format as the JSON file (with "mcpServers" key).

        Returns:
            A new MultiServerClient instance with the provided configuration.

        Raises:
            pydantic.ValidationError: If the config dictionary doesn't match the schema.

        Examples:
            >>> config = {
            ...     "mcpServers": {
            ...         "tool_server": {
            ...             "command": "python",
            ...             "args": ["-m", "my_package.tool_server"]
            ...         }
            ...     }
            ... }
            >>> client = MultiServerClient.from_dict(config)
        """
        instance = cls.__new__(cls)
        instance.config_path = Path("memory://config")  # Dummy path for programmatic config
        instance.sessions = {}
        instance.capabilities = {}
        instance.tool_to_server = {}
        instance.prompt_to_server = {}
        instance._stack = None
        instance._config = MCPServersConfig.model_validate(config_dict)
        return instance

    async def __aenter__(self) -> "MultiServerClient":
        """Enter the async context manager.

        Automatically creates an AsyncExitStack and connects to all servers.

        Returns:
            The connected client instance.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            json.JSONDecodeError: If config file is invalid JSON.
            pydantic.ValidationError: If config data doesn't match schema.

        Note:
            Individual server connection failures are logged but don't prevent
            the context manager from succeeding.
        """
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        await self.connect_all(self._stack)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the async context manager.

        Automatically closes all server connections and cleans up resources.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        if self._stack:
            await self._stack.__aexit__(exc_type, exc_val, exc_tb)
            self._stack = None

    async def connect_all(self, stack: AsyncExitStack) -> None:
        """Connect to all configured MCP servers and discover their capabilities.

        Args:
            stack: AsyncExitStack for managing async context managers.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            json.JSONDecodeError: If config file is invalid JSON.
            pydantic.ValidationError: If config data doesn't match schema.

        Note:
            Individual server connection failures are caught and logged as warnings.
            The method will continue connecting to remaining servers if one fails.
        """
        config = self._load_config()

        logger.info("Connecting to %d MCP servers...", len(config.mcpServers))

        for server_name, server_config in config.mcpServers.items():
            try:
                await self._connect_server(stack, server_name, server_config)
            except Exception as e:
                logger.warning("Failed to connect to %s: %s", server_name, e)
                continue

        logger.info("Successfully connected to %d server(s)", len(self.sessions))

    def _load_config(self) -> MCPServersConfig:
        """Load server configuration from JSON file.

        Returns:
            Parsed configuration object.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            json.JSONDecodeError: If config file is invalid JSON.
            pydantic.ValidationError: If config data doesn't match schema.

        Note:
            This is a private method. Use from_config() or from_dict() instead.
        """
        # If config was set programmatically (from_dict), return it
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, encoding="utf-8") as f:
            config_data = json.load(f)

        return MCPServersConfig.model_validate(config_data)

    async def _connect_server(self, stack: AsyncExitStack, server_name: str, server_config: ServerConfig) -> None:
        """Connect to a single MCP server and discover its capabilities.

        Args:
            stack: AsyncExitStack for managing async context managers.
            server_name: Name identifier for this server.
            server_config: Server connection parameters.

        Raises:
            FileNotFoundError: If server command executable doesn't exist.
            PermissionError: If lacking permission to execute server command.
            OSError: If server process cannot be started.
            McpError: If MCP protocol initialization fails.
            TimeoutError: If connection or initialization times out.
            pydantic.ValidationError: If server parameters are invalid.

        Note:
            Failures during capability discovery are caught and logged as warnings.
            The server will still be registered with partial capabilities if connection and initialization succeed.
        """
        logger.info("[%s] connecting...", server_name)

        # Create server parameters
        params = StdioServerParameters(command=server_config.command, args=server_config.args)

        # Connect to server
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await stack.enter_async_context(ClientSession(read, write))

        # Initialize session
        await session.initialize()
        self.sessions[server_name] = session

        # Discover capabilities
        capabilities = ServerCapabilities(name=server_name)

        # Get tools
        try:
            tools_result = await session.list_tools()
            capabilities.tools = tools_result
            logger.info("[%s] Found %d tool(s)", server_name, len(tools_result.tools))

            # Map tools to server
            for tool in tools_result.tools:
                if tool.name in self.tool_to_server:
                    existing_server = self.tool_to_server[tool.name]
                    logger.warning(
                        "Tool '%s' collision detected! Already provided by '%s', now overridden by '%s'",
                        tool.name,
                        existing_server,
                        server_name,
                    )
                self.tool_to_server[tool.name] = server_name

        except Exception as e:
            logger.warning("Error while listing tools from [%s] : %s", server_name, e)

        # Get resources
        try:
            resources_result = await session.list_resources()
            capabilities.resources = resources_result
            logger.info("[%s] Found %d resource(s)", server_name, len(resources_result.resources))
        except Exception as e:
            logger.warning("Error while listing resources from [%s] : %s", server_name, e)

        # Get resource templates
        try:
            templates_result = await session.list_resource_templates()
            capabilities.resource_templates = templates_result
            logger.info("[%s] Found %d resource template(s)", server_name, len(templates_result.resourceTemplates))
        except Exception as e:
            logger.warning("Error while listing resource templates from [%s] : %s", server_name, e)

        # Get prompts
        try:
            prompts_result = await session.list_prompts()
            capabilities.prompts = prompts_result
            logger.info("[%s] Found %d prompt(s)", server_name, len(prompts_result.prompts))

            # Map prompts to server
            for prompt in prompts_result.prompts:
                if prompt.name in self.prompt_to_server:
                    existing_server = self.prompt_to_server[prompt.name]
                    logger.warning(
                        "Prompt '%s' collision detected! Already provided by '%s', now overridden by '%s'",
                        prompt.name,
                        existing_server,
                        server_name,
                    )
                self.prompt_to_server[prompt.name] = server_name

        except Exception as e:
            logger.warning("Error while listing prompts from [%s] : %s", server_name, e)

        self.capabilities[server_name] = capabilities

    async def set_logging_level(self, level: LoggingLevel) -> EmptyResult:
        """Set the logging level for the multi-server client and the MCP connected servers.

        Args:
            level: Logging level as a string in lower case (e.g., "debug", "info", "notice", "warning", "error",
                "critical", "alert", "emergency") as defined in MCP LoggingLevel.

        Note:
            The following mappings of MCP to Python logging leves are applied:
            - "notice" -> "WARNING"
            - "alert" and "emergency" -> "CRITICAL"

        Examples:
            >>> await MultiServerClient.set_logging_level("debug")
        """
        if level not in {"debug", "info", "notice", "warning", "error", "critical", "alert", "emergency"}:
            raise ValueError(
                f""""
                Invalid logging level: {level}.
                See: https://modelcontextprotocol.github.io/python-sdk/api/#mcp.ClientSession.set_logging_level")
            """
            )
        if level == "notice":
            level = "warning"
        elif level == "alert" or level == "emergency":
            level = "critical"
        for server_name, session in self.sessions.items():
            try:
                await session.set_logging_level(level=level)
            except Exception:
                # Most likely the server doesn't support logging level changes
                # See https://github.com/jlowin/fastmcp/issues/525
                logger.warning("Failed to set logging level for server '%s'", server_name)
        configure_logging(name="mcp_multi_server", level=level.upper())
        return EmptyResult()

    def list_tools(
        self, cursor: Optional[str] = None, *, params: Optional[PaginatedRequestParams] = None
    ) -> ListToolsResult:
        """Get combined list of all tools from all servers.

        This method mimics the MCP ClientSession.list_tools() signature but aggregates
        tools from all connected servers. Server attribution is included in each tool's
        meta field.

        Args:
            cursor: Optional pagination cursor. Not supported for multi-server aggregation,
                must be None if provided.
            params: Optional PaginatedRequestParams. Not supported for multi-server aggregation,
                must be None if provided.

        Returns:
            ListToolsResult containing all tools from all servers with the server name in the serverName meta field.
            The nextCursor field is always None (pagination not supported).

        Raises:
            ValueError: If cursor or params is not None (pagination not supported).

        Examples:
            >>> result = client.list_tools()
            >>> for tool in result.tools:
            ...     server = tool.meta.get("serverName") if tool.meta else None
            ...     print(f"{tool.name} from {server}")
        """
        if cursor is not None or params is not None:
            raise ValueError("Pagination not supported for multi-server aggregation")

        all_tools: List[Tool] = []
        for server_name, capabilities in self.capabilities.items():
            if capabilities.tools:
                for tool in capabilities.tools.tools:
                    # Add server name to tool's meta field
                    existing_meta = tool.meta or {}
                    tool_with_meta = tool.model_copy(update={"meta": {**existing_meta, "serverName": server_name}})
                    all_tools.append(tool_with_meta)

        return ListToolsResult(tools=all_tools, nextCursor=None)

    def list_prompts(
        self, cursor: Optional[str] = None, *, params: Optional[PaginatedRequestParams] = None
    ) -> ListPromptsResult:
        """Get combined list of all prompts from all servers.

        This method mimics the MCP ClientSession.list_prompts() signature but aggregates
        prompts from all connected servers. Server attribution is included in each prompt's
        meta field.

        Args:
            cursor: Optional pagination cursor. Not supported for multi-server aggregation,
                must be None if provided.
            params: Optional PaginatedRequestParams. Not supported for multi-server aggregation,
                must be None if provided.

        Returns:
            ListPromptsResult containing all prompts from all servers with the server name in the serverName meta fieldthe.
            The nextCursor field is always None (pagination not supported).

        Raises:
            ValueError: If cursor or params is not None (pagination not supported).

        Examples:
            >>> result = client.list_prompts()
            >>> for prompt in result.prompts:
            ...     server = prompt.meta.get("serverName") if prompt.meta else None
            ...     print(f"{prompt.name} from {server}")
        """
        if cursor is not None or params is not None:
            raise ValueError("Pagination not supported for multi-server aggregation")

        all_prompts: List[Prompt] = []
        for server_name, capabilities in self.capabilities.items():
            if capabilities.prompts:
                for prompt in capabilities.prompts.prompts:
                    # Add server name to prompt's meta field
                    existing_meta = prompt.meta or {}
                    prompt_with_meta = prompt.model_copy(update={"meta": {**existing_meta, "serverName": server_name}})
                    all_prompts.append(prompt_with_meta)

        return ListPromptsResult(prompts=all_prompts, nextCursor=None)

    def list_resources(
        self,
        cursor: Optional[str] = None,
        *,
        params: Optional[PaginatedRequestParams] = None,
        use_namespace: bool = True,
    ) -> ListResourcesResult:
        """Get combined list of all resources from all servers.

        This method mimics the MCP ClientSession.list_resources() signature but aggregates
        resources from all connected servers. Resources are returned with namespaced URIs
        (server:uri format) for auto-routing, and server attribution is included in each
        resource's meta field.

        Args:
            cursor: Optional pagination cursor. Not supported for multi-server aggregation,
                must be None if provided.
            params: Optional PaginatedRequestParams. Not supported for multi-server aggregation,
                must be None if provided.
            use_namespace: Whether to namespace the URIs with the server name.

        Returns:
            ListResourcesResult containing all resources from all servers with:
            - Namespaced URIs in format "server_name:original_uri" for auto-routing
            - the server name in the serverName meta field for explicit server identification
            The nextCursor field is always None (pagination not supported).

        Raises:
            ValueError: If cursor is not None (pagination not supported).

        Examples:
            >>> result = client.list_resources()
            >>> for resource in result.resources:
            ...     server = resource.meta.get("serverName") if resource.meta else None
            ...     # URI is already namespaced: "filesystem:file:///path"
            ...     content = await client.read_resource(resource.uri)
        """
        if cursor is not None or params is not None:
            raise ValueError("Pagination not supported for multi-server aggregation")

        all_resources: List[Resource] = []
        for server_name, capabilities in self.capabilities.items():
            if capabilities.resources:
                for resource in capabilities.resources.resources:
                    # Add server name to meta and namespace the URI
                    existing_meta = resource.meta or {}
                    resource_with_meta = resource.model_copy(
                        update={
                            "uri": format_namespace_uri(server_name, resource.uri) if use_namespace else resource.uri,
                            "meta": {**existing_meta, "serverName": server_name},
                        }
                    )
                    all_resources.append(resource_with_meta)

        return ListResourcesResult(resources=all_resources, nextCursor=None)

    def list_resource_templates(
        self,
        cursor: Optional[str] = None,
        *,
        params: Optional[PaginatedRequestParams] = None,
        use_namespace: bool = True,
    ) -> ListResourceTemplatesResult:
        """Get combined list of all resource templates from all servers.

        This method mimics the MCP ClientSession.list_resource_templates() signature but
        aggregates resource templates from all connected servers. Templates are returned
        with namespaced URI templates (server:template format) for auto-routing, and server
        attribution is included in each template's meta field.

        Args:
            cursor: Optional pagination cursor. Not supported for multi-server aggregation,
                must be None if provided.
            params: Optional PaginatedRequestParams. Not supported for multi-server aggregation,
                must be None if provided.
            use_namespace: Whether to namespace the URI templates with the server name.

        Returns:
            ListResourceTemplatesResult containing all templates from all servers with:
            - Namespaced URI templates in format "server_name:original_template"
            - the server name in the serverName meta field for explicit server identification
            The nextCursor field is always None (pagination not supported).

        Raises:
            ValueError: If cursor is not None (pagination not supported).

        Examples:
            >>> result = client.list_resource_templates()
            >>> for template in result.resourceTemplates:
            ...     server = template.meta.get("serverName") if template.meta else None
            ...     # URI template is already namespaced: "filesystem:file:///{path}"
            ...     # Needs to be filled in with actual path when used
            ...     uri = template.uriTemplate.replace("{path}", "example.txt")
            ...     content = await client.read_resource(uri)
        """
        if cursor is not None or params is not None:
            raise ValueError("Pagination not supported for multi-server aggregation")

        all_templates: List[ResourceTemplate] = []
        for server_name, capabilities in self.capabilities.items():
            if capabilities.resource_templates:
                for template in capabilities.resource_templates.resourceTemplates:
                    # Add server name to meta and namespace the URI template
                    existing_meta = template.meta or {}
                    template_with_meta = template.model_copy(
                        update={
                            "uriTemplate": (
                                format_namespace_uri(server_name, template.uriTemplate)
                                if use_namespace
                                else template.uriTemplate
                            ),
                            "meta": {**existing_meta, "serverName": server_name},
                        }
                    )
                    all_templates.append(template_with_meta)

        return ListResourceTemplatesResult(resourceTemplates=all_templates, nextCursor=None)

    def _create_error_result(self, error_message: str) -> CallToolResult:
        """Create a CallToolResult indicating an error.

        Args:
            error_message: The error message to include in the result.

        Returns:
            CallToolResult with isError=True and the error message in content.
        """
        return CallToolResult(
            content=[TextContent(type="text", text=error_message)],
            isError=True,
        )

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        read_timeout_seconds: Optional[timedelta] = None,
        progress_callback: Optional[ProgressFnT] = None,
        *,
        meta: Optional[dict[str, Any]] = None,
        server_name: Optional[str] = None,
    ) -> CallToolResult:
        """Route a tool call to the appropriate server.

        Args:
            name: Name of the tool to call.
            arguments: Arguments to pass to the tool.
            read_timeout_seconds: Optional timeout for reading the tool result.
            progress_callback: Optional callback for progress notifications.
            meta: Optional metadata dictionary to pass additional information.
            server_name: Optional server name to explicitly specify which server to use.
                If not provided, the server will be automatically determined from the tool name.

        Returns:
            Result from the tool execution. If the tool name is not found or routing fails,
            returns a CallToolResult with isError=True containing an error message.

        Raises:
            McpError: If the tool execution fails or times out (protocol-level errors).
            RuntimeError: If tool result validation fails (invalid structured content or schema).

        Note:
            Routing errors (unknown tool, unknown server) are returned as error results
            (isError=True) rather than raising exceptions, following MCP protocol conventions.
            Protocol-level errors from the underlying session are propagated as exceptions.
        """
        if server_name is None:
            # Auto-route using the tool mapping
            server_name = self.tool_to_server.get(name)
            if not server_name:
                return self._create_error_result(f"Unknown tool: {name}")
        else:
            # Validate the explicitly provided server name
            if server_name not in self.sessions:
                return self._create_error_result(f"Unknown server: {server_name}")

            # Validate that the tool exists on the specified server
            server_capabilities = self.capabilities[server_name]
            if server_capabilities.tools is None:
                return self._create_error_result(f"Server '{server_name}' has no tools")

            if name not in {tool.name for tool in server_capabilities.tools.tools}:
                return self._create_error_result(f"Tool '{name}' not found in server '{server_name}'")

        session = self.sessions[server_name]
        return await session.call_tool(
            name,
            arguments,
            read_timeout_seconds=read_timeout_seconds,
            progress_callback=progress_callback,
            meta=meta,
        )

    async def read_resource(self, uri: Union[str, AnyUrl], server_name: Optional[str] = None) -> ReadResourceResult:
        """Read a resource with optional auto-routing via namespaced URIs.

        Args:
            uri: Resource URI. Can be namespaced as "server:uri" for auto-routing.
                 URIs from list_resources() are already namespaced for convenience.
                 Accepts both str and AnyUrl types for MCP library compatibility.
            server_name: Optional explicit server name. If provided, assumes that
                there is no any namespace in the provided URI.

        Returns:
            Resource content.

        Raises:
            McpError: If server name is not found, URI is not namespaced when server_name
                     is not provided, or if the resource read fails or times out.

        Examples:
        ::

            Auto-routing with namespaced URI (from list_resources()):
            >>> resources = client.list_resources().resources
            >>> result = await client.read_resource(resources[0].uri)

            Explicit server (no namespace should be present in URI):
            >>> result = await client.read_resource("file:///path", server_name="filesystem")

            Manual namespacing:
            >>> result = await client.read_resource("filesystem:file:///path")

        Note:
            Raises McpError for both routing errors and protocol-level errors to align
            with MCP SDK behavior.
        """
        if server_name is None:
            # Try to extract server from namespaced URI
            server_name, uri = parse_namespace_uri(uri)
            if server_name is None:
                # No server specified and, URI is not namespaced or server in namespace is unknown
                raise McpError(
                    ErrorData(
                        code=-32601,
                        message="Must specify server_name or use namespaced URI format (server:uri)",
                    )
                )

        session = self.sessions.get(server_name)
        if not session:
            raise McpError(ErrorData(code=-32601, message=f"Unknown server: {server_name}"))

        return await session.read_resource(AnyUrl(uri))

    async def get_prompt(
        self,
        name: str,
        arguments: Optional[Dict[str, str]] = None,
        server_name: Optional[str] = None,
    ) -> GetPromptResult:
        """Get a prompt by automatically routing to the appropriate server.

        Args:
            name: Name of the prompt to get.
            arguments: Optional arguments for the prompt.
            server_name: Optional server name to explicitly specify which server to use.
                If not provided, the server will be automatically determined from the prompt name.

        Returns:
            Prompt result.

        Raises:
            McpError: If prompt name is not found, server name is not found, or if the
                prompt retrieval fails or times out.

        Note:
            Raises McpError for both routing errors and protocol-level errors to align
            with MCP SDK behavior.
        """
        if server_name is None:
            # Auto-route using the prompt mapping
            server_name = self.prompt_to_server.get(name)
            if not server_name:
                raise McpError(ErrorData(code=-32601, message=f"Unknown prompt: {name}"))
        else:
            # Validate the explicitly provided server name
            if server_name not in self.sessions:
                raise McpError(ErrorData(code=-32601, message=f"Unknown server: {server_name}"))

            # Validate that the prompt exists on the specified server
            server_capabilities = self.capabilities[server_name]
            if server_capabilities.prompts is None:
                raise McpError(ErrorData(code=-32601, message=f"Server '{server_name}' has no prompts"))

            if name not in {prompt.name for prompt in server_capabilities.prompts.prompts}:
                raise McpError(ErrorData(code=-32601, message=f"Prompt '{name}' not found in server '{server_name}'"))

        session = self.sessions[server_name]
        return await session.get_prompt(name, arguments=arguments or {})
