"""MCP Multi-Server Client Library.

A Python library for managing connections to multiple MCP (Model Context Protocol) servers.
This library provides a unified interface for discovering, aggregating, and routing capabilities
(tools, resources, prompts) across multiple MCP servers.

Key Features:
    - Connect to multiple MCP servers simultaneously
    - Automatic capability discovery and aggregation
    - Intelligent routing of tool calls, resource reads, and prompt retrievals
    - Namespace-based URI routing for resources and resource templates
    - Collision detection for tools and prompts

Examples:
::

    Basic usage with context manager:
    >>> async with MultiServerClient.from_config("mcp_servers.json") as client:
    ...     tools = client.list_tools()
    ...     result = await client.call_tool("my_tool", {"arg": "value"})

    Programmatic configuration:
    >>> from mcp_multi_server import MultiServerClient, MCPServersConfig, ServerConfig
    >>> config = MCPServersConfig(mcpServers={
    ...     "my_server": ServerConfig(command="python", args=["-m", "my_server"])
    ... })
    >>> async with MultiServerClient.from_dict(config.model_dump()) as client:
    ...     tools = client.list_tools()

    OpenAI integration:
    >>> from mcp_multi_server import mcp_tools_to_openai_format
    >>> tools = client.list_tools()
    >>> openai_tools = mcp_tools_to_openai_format(tools.tools)

    Configuring logging:
    >>> from mcp_multi_server import configure_logging
    >>> configure_logging(level="DEBUG")  # Enable debug logging
    >>> # Or use Python's logging module directly:
    >>> import logging
    >>> logging.getLogger("mcp_multi_server").setLevel(logging.DEBUG)

See Also:
    - MCP Protocol Documentation: https://modelcontextprotocol.io
    - GitHub Repository: https://github.com/apisani1/mcp-multi-server
    - Examples: https://github.com/apisani1/mcp-multi-server/tree/main/examples
"""

__version__ = "1.0.0"

from .client import MultiServerClient
from .config import (
    MCPServersConfig,
    ServerConfig,
)
from .types import ServerCapabilities
from .utils import (
    configure_logging,
    extract_template_variables,
    format_namespace_uri,
    mcp_tools_to_openai_format,
    parse_namespace_uri,
    substitute_template_variables,
)


__all__ = [
    # Main client class
    "MultiServerClient",
    # Configuration models
    "ServerConfig",
    "MCPServersConfig",
    # Type definitions
    "ServerCapabilities",
    # Utility functions
    "configure_logging",
    "mcp_tools_to_openai_format",
    "format_namespace_uri",
    "parse_namespace_uri",
    "extract_template_variables",
    "substitute_template_variables",
    # Version
    "__version__",
]
