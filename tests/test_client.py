"""Tests for MultiServerClient class."""

import json
from contextlib import AsyncExitStack
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest
from pydantic import (
    AnyUrl,
    ValidationError,
)

from mcp.shared.exceptions import McpError
from mcp.types import (
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    Prompt,
    Tool,
)
from mcp_multi_server import MultiServerClient
from mcp_multi_server.config import (
    MCPServersConfig,
    ServerConfig,
)
from mcp_multi_server.types import ServerCapabilities


# ============================================================================
# Initialization and Config Loading Tests
# ============================================================================


class TestClientInitialization:
    """Tests for MultiServerClient initialization."""

    def test_init_with_path_object(self, sample_config_file: Path) -> None:
        """Test initialization with path as string."""
        client = MultiServerClient(str(sample_config_file))

        assert client.config_path == sample_config_file
        assert client.sessions == {}
        assert client.capabilities == {}
        assert client.tool_to_server == {}
        assert client.prompt_to_server == {}
        assert client._config is None

    def test_init_with_nonexistent_file_succeeds(self) -> None:
        """Test initialization with non-existent file succeeds (lazy loading)."""
        # Initialization should succeed even with non-existent file
        client = MultiServerClient("/path/that/does/not/exist.json")
        assert client.config_path == Path("/path/that/does/not/exist.json")
        assert client._config is None

    def test_init_with_invalid_json_succeeds(self, tmp_path: Path) -> None:
        """Test initialization with invalid JSON succeeds (lazy loading)."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ this is not valid json }")

        # Initialization should succeed, error happens on connect_all()
        client = MultiServerClient(str(invalid_file))
        assert client.config_path == invalid_file
        assert client._config is None

    def test_init_with_invalid_config_schema_succeeds(self, tmp_path: Path) -> None:
        """Test initialization with invalid schema succeeds (lazy loading)."""
        invalid_file = tmp_path / "invalid_schema.json"
        invalid_file.write_text(json.dumps({"wrong_field": {}}))

        # Initialization should succeed, error happens on connect_all()
        client = MultiServerClient(invalid_file)
        assert client.config_path == invalid_file
        assert client._config is None


class TestFromConfigClassMethod:
    """Tests for from_config class method."""

    def test_from_config_with_path_object(self, sample_config_file: Path) -> None:
        """Test from_config with Path object."""
        client = MultiServerClient.from_config(sample_config_file)

        assert isinstance(client, MultiServerClient)
        assert client.config_path == sample_config_file

    def test_from_config_equivalent_to_init(self, sample_config_file: Path) -> None:
        """Test that from_config is equivalent to __init__."""
        client1 = MultiServerClient(sample_config_file)
        client2 = MultiServerClient.from_config(sample_config_file)

        assert client1.config_path == client2.config_path
        assert type(client1._config) == type(client2._config)


class TestFromDictClassMethod:
    """Tests for from_dict class method."""

    def test_from_dict_creates_client(self, sample_config_dict: Dict[str, Any]) -> None:
        """Test from_dict creates client from dictionary."""
        client = MultiServerClient.from_dict(sample_config_dict)

        assert isinstance(client, MultiServerClient)
        assert client.config_path == Path("memory://config")
        assert isinstance(client._config, MCPServersConfig)

    def test_from_dict_loads_servers(self, sample_config_dict: Dict[str, Any]) -> None:
        """Test from_dict loads server configurations."""
        client = MultiServerClient.from_dict(sample_config_dict)

        assert "tool_server" in client._config.mcpServers  # type: ignore
        assert "resource_server" in client._config.mcpServers  # type: ignore
        assert "prompt_server" in client._config.mcpServers  # type: ignore

    def test_from_dict_with_minimal_config(self, minimal_config_dict: Dict[str, Any]) -> None:
        """Test from_dict with minimal configuration."""
        client = MultiServerClient.from_dict(minimal_config_dict)

        assert len(client._config.mcpServers) == 1  # type: ignore
        assert "test_server" in client._config.mcpServers  # type: ignore

    def test_from_dict_with_empty_config(self, empty_config_dict: Dict[str, Any]) -> None:
        """Test from_dict with empty configuration."""
        client = MultiServerClient.from_dict(empty_config_dict)

        assert len(client._config.mcpServers) == 0  # type: ignore

    def test_from_dict_with_invalid_schema_raises_error(self) -> None:
        """Test from_dict with invalid schema raises pydantic ValidationError."""

        invalid_dict: Dict[str, Any] = {"wrong_field": {}}

        with pytest.raises(ValidationError):
            MultiServerClient.from_dict(invalid_dict)


class TestContextManager:
    """Tests for async context manager protocol."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self, sample_config_dict: Dict[str, Any]) -> None:
        """Test async context manager enter and exit."""
        client = MultiServerClient.from_dict(sample_config_dict)

        async with client as ctx_client:
            assert ctx_client is client
            assert client._stack is not None

        # After exit, stack should be cleaned up
        assert client._stack is None

    @pytest.mark.asyncio
    async def test_context_manager_multiple_uses_succeeds(self, sample_config_dict: Dict[str, Any]) -> None:
        """Test that using context manager twice succeeds (creates new stack each time)."""
        client = MultiServerClient.from_dict(sample_config_dict)

        async with client:
            assert client._stack is not None

        # Stack should be cleaned up
        assert client._stack is None

        # Second use should succeed (creates new stack)
        async with client:
            assert client._stack is not None

        assert client._stack is None

    @pytest.mark.asyncio
    async def test_context_manager_exception_cleanup(self, empty_config_dict: Dict[str, Any]) -> None:
        """Test that context manager cleans up on exception."""
        client = MultiServerClient.from_dict(empty_config_dict)

        try:
            async with client:
                assert client._stack is not None
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Stack should be cleaned up even after exception
        assert client._stack is None


# ============================================================================
# Connection and Capability Aggregation Tests
# ============================================================================


class TestConnectionManagement:
    """Tests for server connection management."""

    @pytest.mark.asyncio
    async def test_async_with_connects_all_servers(
        self, sample_config_dict: Dict[str, Any], mock_tool_server: MagicMock
    ) -> None:
        """Test successful connection to a server."""
        client = MultiServerClient.from_dict(sample_config_dict)

        # Mock the stdio_client context manager
        with patch("mcp_multi_server.client.stdio_client") as mock_stdio:
            mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
            mock_stdio.return_value.__aexit__ = AsyncMock()

            with patch("mcp_multi_server.client.ClientSession") as mock_session_class:
                mock_session = MagicMock()
                mock_session.initialize = AsyncMock()
                mock_session_class.return_value = mock_session

                async with client:
                    # Connection should be established
                    assert len(client.sessions) == 3
                    assert "tool_server" in client.sessions
                    assert "resource_server" in client.sessions
                    assert "prompt_server" in client.sessions

    @pytest.mark.asyncio
    async def test_connect_all_method_connects_all_servers(self, sample_config_dict: Dict[str, Any]) -> None:
        """Test connect_all connects to all configured servers."""
        client = MultiServerClient.from_dict(sample_config_dict)

        with patch("mcp_multi_server.client.stdio_client") as mock_stdio:
            mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
            mock_stdio.return_value.__aexit__ = AsyncMock()

            with patch("mcp_multi_server.client.ClientSession") as mock_session_class:
                mock_session = MagicMock()
                mock_session.initialize = AsyncMock()
                mock_session_class.return_value = mock_session

                async with client as ctx_client:
                    await ctx_client.connect_all(ctx_client._stack)  # type: ignore

                    # Should have connected to all 3 servers
                    assert len(client.sessions) == 3
                    assert "tool_server" in client.sessions
                    assert "resource_server" in client.sessions
                    assert "prompt_server" in client.sessions


class TestCapabilityAggregation:
    """Tests for aggregating capabilities from multiple servers."""

    def test_list_tools_aggregates_from_all_servers(
        self,
        sample_config_dict: Dict[str, Any],
        sample_tools: list,
        server2_tools: list,
    ) -> None:
        """Test list_tools aggregates tools from all servers."""

        client = MultiServerClient.from_dict(sample_config_dict)

        # Populate capabilities with TWO servers that have tools
        client.capabilities = {
            "tool_server": ServerCapabilities(
                name="tool_server", tools=ListToolsResult(tools=sample_tools, nextCursor=None)
            ),
            "email_server": ServerCapabilities(
                name="email_server", tools=ListToolsResult(tools=server2_tools, nextCursor=None)
            ),
        }

        result = client.list_tools()

        assert result.tools is not None
        assert len(result.tools) == 4  # 2 from tool_server + 2 from email_server

        # Verify tools from tool_server (appear first)
        assert result.tools[0].name == "get_weather"
        assert result.tools[0].meta.get("serverName") == "tool_server"  # type: ignore
        assert result.tools[1].name == "calculate"
        assert result.tools[1].meta.get("serverName") == "tool_server"  # type: ignore

        # Verify tools from email_server (appear second)
        assert result.tools[2].name == "send_email"
        assert result.tools[2].meta.get("serverName") == "email_server"  # type: ignore
        assert result.tools[3].name == "search_database"
        assert result.tools[3].meta.get("serverName") == "email_server"  # type: ignore

    def test_list_resources_aggregates_from_all_servers(
        self,
        sample_config_dict: Dict[str, Any],
        sample_resources: list,
        server2_resources: list,
    ) -> None:
        """Test list_resources aggregates resources from all servers."""

        client = MultiServerClient.from_dict(sample_config_dict)

        # Populate capabilities with TWO servers that have resources
        client.capabilities = {
            "resource_server": ServerCapabilities(
                name="resource_server", resources=ListResourcesResult(resources=sample_resources, nextCursor=None)
            ),
            "database_server": ServerCapabilities(
                name="database_server", resources=ListResourcesResult(resources=server2_resources, nextCursor=None)
            ),
        }

        result = client.list_resources()

        assert result.resources is not None
        assert len(result.resources) == 4  # 2 from resource_server + 2 from database_server

        # Verify resources from resource_server (appear first) with namespace prefix
        assert "resource_server:inventory://overview" == str(result.resources[0].uri)
        assert result.resources[0].name == "Inventory Overview"
        assert result.resources[0].meta.get("serverName") == "resource_server"  # type: ignore

        assert "resource_server:inventory://items" == str(result.resources[1].uri)
        assert result.resources[1].name == "All Items"
        assert result.resources[1].meta.get("serverName") == "resource_server"  # type: ignore

        # Verify resources from database_server (appear second) with namespace prefix
        assert "database_server:database://users" == str(result.resources[2].uri)
        assert result.resources[2].name == "User Database"
        assert result.resources[2].meta.get("serverName") == "database_server"  # type: ignore

        assert "database_server:database://logs" == str(result.resources[3].uri)
        assert result.resources[3].name == "System Logs"
        assert result.resources[3].meta.get("serverName") == "database_server"  # type: ignore

    def test_list_resource_templates_aggregates_from_all_servers(
        self,
        sample_config_dict: Dict[str, Any],
        sample_resource_templates: list,
        server2_resource_templates: list,
    ) -> None:
        """Test list_resource_templates aggregates resource templates from all servers."""

        client = MultiServerClient.from_dict(sample_config_dict)

        # Populate capabilities with TWO servers that have resource templates
        client.capabilities = {
            "resource_server": ServerCapabilities(
                name="resource_server",
                resource_templates=ListResourceTemplatesResult(
                    resourceTemplates=sample_resource_templates, nextCursor=None
                ),
            ),
            "database_server": ServerCapabilities(
                name="database_server",
                resource_templates=ListResourceTemplatesResult(
                    resourceTemplates=server2_resource_templates, nextCursor=None
                ),
            ),
        }

        result = client.list_resource_templates()

        assert result.resourceTemplates is not None
        assert len(result.resourceTemplates) == 4  # 2 from resource_server + 2 from database_server

        # Verify resources from resource_server (appear first) with namespace prefix
        assert "resource_server:inventory://item/{item_id}" == result.resourceTemplates[0].uriTemplate
        assert result.resourceTemplates[0].name == "Item by ID"
        assert result.resourceTemplates[0].meta.get("serverName") == "resource_server"  # type: ignore

        assert "resource_server:inventory://category/{category}" == result.resourceTemplates[1].uriTemplate
        assert result.resourceTemplates[1].name == "Items by Category"
        assert result.resourceTemplates[1].meta.get("serverName") == "resource_server"  # type: ignore
        # Verify resources from database_server (appear second) with namespace prefix
        assert "database_server:inventory://category_summary/{category}" == result.resourceTemplates[2].uriTemplate
        assert result.resourceTemplates[2].name == "Category Summary "
        assert result.resourceTemplates[2].meta.get("serverName") == "database_server"  # type: ignore

        assert "database_server:inventory://low_items/{category}" == result.resourceTemplates[3].uriTemplate
        assert result.resourceTemplates[3].name == "Category stock needing restock"
        assert result.resourceTemplates[3].meta.get("serverName") == "database_server"  # type: ignore

    def test_list_prompts_aggregates_from_all_servers(
        self,
        sample_config_dict: Dict[str, Any],
        sample_prompts: list,
        server2_prompts: list,
    ) -> None:
        """Test list_prompts aggregates prompts from all servers."""

        client = MultiServerClient.from_dict(sample_config_dict)

        # Populate capabilities with TWO servers that have prompts
        client.capabilities = {
            "prompt_server": ServerCapabilities(
                name="prompt_server", prompts=ListPromptsResult(prompts=sample_prompts, nextCursor=None)
            ),
            "assistant_server": ServerCapabilities(
                name="assistant_server", prompts=ListPromptsResult(prompts=server2_prompts, nextCursor=None)
            ),
        }

        result = client.list_prompts()

        assert result.prompts is not None
        assert len(result.prompts) == 4  # 2 from prompt_server + 2 from assistant_server

        # Verify prompts from prompt_server (appear first)
        assert result.prompts[0].name == "write_report"
        assert result.prompts[0].meta.get("serverName") == "prompt_server"  # type: ignore
        assert result.prompts[1].name == "roleplay"
        assert result.prompts[1].meta.get("serverName") == "prompt_server"  # type: ignore

        # Verify prompts from assistant_server (appear second)
        assert result.prompts[2].name == "code_review"
        assert result.prompts[2].meta.get("serverName") == "assistant_server"  # type: ignore
        assert result.prompts[3].name == "summarize"
        assert result.prompts[3].meta.get("serverName") == "assistant_server"  # type: ignore


# ============================================================================
# Routing Tests (Tools, Resources, Prompts)
# ============================================================================


class TestToolRouting:
    """Tests for tool routing to appropriate servers and error handling."""

    @pytest.mark.asyncio
    async def test_call_tool_routes_to_correct_server(
        self,
        sample_config_dict: Dict[str, Any],
        mock_tool_server: MagicMock,
    ) -> None:
        """Test call_tool routes to correct server."""
        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.tool_to_server = {"get_weather": "tool_server"}
        client.sessions = {"tool_server": mock_tool_server}

        result = await client.call_tool("get_weather", {"location": "San Francisco"})

        assert result.isError is False
        assert "San Francisco" in result.content[0].text  # type: ignore
        mock_tool_server.call_tool.assert_called_once_with(
            "get_weather", {"location": "San Francisco"}, read_timeout_seconds=None, progress_callback=None, meta=None
        )

    @pytest.mark.asyncio
    async def test_call_tool_with_unknown_tool_returns_error(
        self,
        sample_config_dict: Dict[str, Any],
        mock_tool_server: MagicMock,
    ) -> None:
        """Test call_tool with unknown tool returns error result."""
        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.tool_to_server = {"get_weather": "tool_server"}
        client.sessions = {"tool_server": mock_tool_server}

        result = await client.call_tool("not_a_tool", {})

        # Should return error result, not raise exception
        assert result.isError is True
        assert "Unknown tool" in result.content[0].text  # type: ignore

    @pytest.mark.asyncio
    async def test_call_tool_with_explicit_unknown_server_returns_error(
        self,
        sample_config_dict: Dict[str, Any],
        mock_tool_server: MagicMock,
    ) -> None:
        """Test call_tool with explicit unknown server name returns error result."""
        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.tool_to_server = {"get_weather": "tool_server"}
        client.sessions = {"tool_server": mock_tool_server}

        # Use explicit server_name parameter (not auto-routing)
        result = await client.call_tool("get_weather", {}, server_name="not_a_server")

        # Should return error result, not raise exception
        assert result.isError is True
        assert "Unknown server" in result.content[0].text  # type: ignore

    @pytest.mark.asyncio
    async def test_call_tool_with_server_with_no_tools_returns_error(
        self,
        sample_config_dict: Dict[str, Any],
        mock_tool_server: MagicMock,
        mock_resource_server: MagicMock,
        sample_tools: List[Tool],
    ) -> None:
        """Test call_tool with explicit knwon server that has no tools returns error result."""
        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.tool_to_server = {"get_weather": "tool_server"}
        client.sessions = {"tool_server": mock_tool_server, "resource_server": mock_resource_server}
        client.capabilities = {
            "tool_server": MagicMock(tools=MagicMock(tools=sample_tools)),
            "resource_server": MagicMock(tools=None),
        }

        # Use explicit server_name parameter (not auto-routing)
        result = await client.call_tool("get_weather", {}, server_name="resource_server")

        # Should return error result, not raise exception
        assert result.isError is True
        assert "has no tools" in result.content[0].text  # type: ignore

    @pytest.mark.asyncio
    async def test_call_tool_with_wrong_tool_raises_mcperror(
        self, sample_config_dict: Dict[str, Any], mock_tool_server: MagicMock, sample_tools: List[Tool]
    ) -> None:
        """Test call_tool with explicit server but unknown tool returns error result."""

        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.prompt_to_server = {"write_report": "prompt_server"}
        client.sessions = {"tool_server": mock_tool_server}
        client.capabilities = {
            "tool_server": MagicMock(prompts=MagicMock(prompts=sample_tools)),
        }

        # Use explicit server_name parameter (not auto-routing)
        result = await client.call_tool("wrong_tool", {}, server_name="tool_server")

        # Should return error result, not raise exception
        assert result.isError is True
        assert "not found in server" in result.content[0].text  # type: ignore


class TestResourceRouting:
    """Tests for resource routing to appropriate servers and error handling."""

    @pytest.mark.asyncio
    async def test_read_resource_with_namespace_routes_correctly(
        self,
        sample_config_dict: Dict[str, Any],
        mock_resource_server: MagicMock,
    ) -> None:
        """Test read_resource with namespaced URI routes correctly."""
        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.sessions = {"resource_server": mock_resource_server}

        # Read resource with namespace prefix
        result = await client.read_resource("resource_server:inventory://overview")

        assert len(result.contents) > 0
        # For TextResourceContents, the content is in the text field
        assert hasattr(result.contents[0], "text")
        assert "Inventory Overview" in result.contents[0].text
        # The mock server is called with AnyUrl type
        mock_resource_server.read_resource.assert_called_once_with(AnyUrl("inventory://overview"))

    @pytest.mark.asyncio
    async def test_read_resource_without_namespace_or_server_raises_mcperror(
        self, sample_config_dict: Dict[str, Any], mock_resource_server: MagicMock
    ) -> None:
        """Test read_resource without namespace or server_name raises McpError."""

        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.sessions = {"resource_server": mock_resource_server}

        with pytest.raises(McpError, match="Must specify server_name"):
            await client.read_resource("inventory://overview")

    @pytest.mark.asyncio
    async def test_read_resource_namespaced_with_unknown_server_raises_mcperror(
        self, sample_config_dict: Dict[str, Any], mock_resource_server: MagicMock
    ) -> None:
        """Test read_resource namespaced with unknown server raises McpError."""

        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.sessions = {"resource_server": mock_resource_server}

        with pytest.raises(McpError, match="Unknown server"):
            await client.read_resource("not_a_server:inventory://overview")

    @pytest.mark.asyncio
    async def test_read_resource_with_explicit_unknown_server_raises_mcperror(
        self, sample_config_dict: Dict[str, Any], mock_resource_server: MagicMock
    ) -> None:
        """Test read_resource with explicit unknown server raises McpError."""

        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.sessions = {"resource_server": mock_resource_server}

        with pytest.raises(McpError, match="Unknown server"):
            await client.read_resource("inventory://overview", server_name="not_a_server")


class TestPromptRouting:
    """Tests for prompt routing to appropriate servers."""

    @pytest.mark.asyncio
    async def test_get_prompt_routes_to_correct_server(
        self,
        sample_config_dict: Dict[str, Any],
        mock_prompt_server: MagicMock,
    ) -> None:
        """Test get_prompt routes to correct server."""
        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.prompt_to_server = {"write_report": "prompt_server"}
        client.sessions = {"prompt_server": mock_prompt_server}

        result = await client.get_prompt("write_report", {"topic": "AI", "length": "short"})

        assert len(result.messages) > 0
        assert "AI" in result.messages[0].content.text  # type: ignore
        # Check that server was called (actual parameters passed positionally, not named)
        mock_prompt_server.get_prompt.assert_called_once()
        # Verify the arguments
        call_args = mock_prompt_server.get_prompt.call_args
        assert call_args[0][0] == "write_report"  # first positional arg
        assert call_args[1]["arguments"] == {"topic": "AI", "length": "short"}  # keyword arg

    @pytest.mark.asyncio
    async def test_get_prompt_with_unknown_prompt_raises_mcperror(
        self, sample_config_dict: Dict[str, Any], mock_prompt_server: MagicMock
    ) -> None:
        """Test get_prompt with unknown prompt raises McpError."""

        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.prompt_to_server = {"write_report": "prompt_server"}
        client.sessions = {"prompt_server": mock_prompt_server}

        with pytest.raises(McpError, match="Unknown prompt"):
            await client.get_prompt("not_a_prompt", {})

    @pytest.mark.asyncio
    async def test_get_prompt_with_explicit_unknown_server_raises_mcperror(
        self, sample_config_dict: Dict[str, Any], mock_prompt_server: MagicMock
    ) -> None:
        """Test get_prompt with explicit unknown server raises McpError."""

        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.prompt_to_server = {"write_report": "prompt_server"}
        client.sessions = {"prompt_server": mock_prompt_server}

        with pytest.raises(McpError, match="Unknown server"):
            await client.get_prompt("write_report", {}, server_name="not_a_server")

    @pytest.mark.asyncio
    async def test_get_prompt_with_server_with_no_prompts_raises_mcperror(
        self,
        sample_config_dict: Dict[str, Any],
        mock_prompt_server: MagicMock,
        mock_resource_server: MagicMock,
        sample_prompts: List[Prompt],
    ) -> None:
        """Test get_prompt with explicit unknown server raises McpError."""

        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.prompt_to_server = {"write_report": "prompt_server"}
        client.sessions = {"prompt_server": mock_prompt_server, "resource_server": mock_resource_server}
        client.capabilities = {
            "prompt_server": MagicMock(prompts=MagicMock(prompts=sample_prompts)),
            "resource_server": MagicMock(prompts=None),
        }

        with pytest.raises(McpError, match="has no prompts"):
            await client.get_prompt("write_report", {}, server_name="resource_server")

    @pytest.mark.asyncio
    async def test_get_prompt_with_wrong_pront_raises_mcperror(
        self, sample_config_dict: Dict[str, Any], mock_prompt_server: MagicMock, sample_prompts: List[Prompt]
    ) -> None:
        """Test get_prompt with unknown prompt in a known server raises McpError."""

        client = MultiServerClient.from_dict(sample_config_dict)

        # Set up routing map
        client.prompt_to_server = {"write_report": "prompt_server", "roleplay": "prompt_server"}
        client.sessions = {"prompt_server": mock_prompt_server}
        client.capabilities = {
            "prompt_server": MagicMock(prompts=MagicMock(prompts=sample_prompts)),
        }

        with pytest.raises(McpError, match="not found in server"):
            await client.get_prompt("wrong_prompt", {}, server_name="prompt_server")


# ============================================================================
# Collision Detection Tests and Server Error Handling Tests
# ============================================================================


class TestCollisionDetection:
    """Tests for detecting and warning about collisions."""

    @pytest.mark.asyncio
    async def test_detect_tool_collision_logs_warning(
        self,
        empty_config_dict: Dict[str, Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that tool collisions are logged with server names."""

        # Create a tool that will be provided by both servers
        weather_tool = Tool(
            name="get_weather", description="Get weather", inputSchema={"type": "object", "properties": {}}
        )

        client = MultiServerClient.from_dict(empty_config_dict)

        # Create mock session that will be returned by ClientSession
        mock_session1 = MagicMock()
        mock_session1.initialize = AsyncMock()
        mock_session1.list_tools = AsyncMock(return_value=ListToolsResult(tools=[weather_tool], nextCursor=None))
        mock_session1.list_resources = AsyncMock(return_value=ListResourcesResult(resources=[], nextCursor=None))
        mock_session1.list_resource_templates = AsyncMock(
            return_value=ListResourceTemplatesResult(resourceTemplates=[], nextCursor=None)
        )
        mock_session1.list_prompts = AsyncMock(return_value=ListPromptsResult(prompts=[], nextCursor=None))

        mock_session2 = MagicMock()
        mock_session2.initialize = AsyncMock()
        mock_session2.list_tools = AsyncMock(return_value=ListToolsResult(tools=[weather_tool], nextCursor=None))
        mock_session2.list_resources = AsyncMock(return_value=ListResourcesResult(resources=[], nextCursor=None))
        mock_session2.list_resource_templates = AsyncMock(
            return_value=ListResourceTemplatesResult(resourceTemplates=[], nextCursor=None)
        )
        mock_session2.list_prompts = AsyncMock(return_value=ListPromptsResult(prompts=[], nextCursor=None))

        # Manually set up AsyncExitStack
        stack = AsyncExitStack()
        await stack.__aenter__()
        client._stack = stack

        try:
            # Mock the connection infrastructure
            with (
                patch("mcp_multi_server.client.stdio_client") as mock_stdio,
                patch("mcp_multi_server.client.ClientSession") as mock_client_session,
            ):

                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock()

                # First connection - mock ClientSession as async context manager
                mock_client_session.return_value.__aenter__ = AsyncMock(return_value=mock_session1)
                mock_client_session.return_value.__aexit__ = AsyncMock()

                with caplog.at_level("WARNING"):
                    await client._connect_server(stack, "server1", ServerConfig(command="python", args=["-m", "test"]))

                assert client.tool_to_server["get_weather"] == "server1"
                assert "collision" not in caplog.text.lower()  # No collision yet

                # Second connection (should cause collision) - update mock to return mock_session2
                mock_client_session.return_value.__aenter__ = AsyncMock(return_value=mock_session2)

                caplog.clear()
                with caplog.at_level("WARNING"):
                    await client._connect_server(stack, "server2", ServerConfig(command="python", args=["-m", "test"]))

                # Verify last-registered-wins
                assert client.tool_to_server["get_weather"] == "server2"

                # Verify collision warning was logged
                assert "collision detected" in caplog.text.lower()
                assert "get_weather" in caplog.text
                assert "server1" in caplog.text  # Already provided by
                assert "server2" in caplog.text  # Now overridden by
        finally:
            await stack.__aexit__(None, None, None)
            client._stack = None

    @pytest.mark.asyncio
    async def test_detect_prompt_collision_logs_warning(
        self,
        empty_config_dict: Dict[str, Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that prompt collisions are logged with server names."""

        # Create a prompt that will be provided by both servers
        report_prompt = Prompt(name="write_report", description="Generate a report", arguments=[])

        client = MultiServerClient.from_dict(empty_config_dict)

        # Create mock session that will be returned by ClientSession
        mock_session1 = MagicMock()
        mock_session1.initialize = AsyncMock()
        mock_session1.list_tools = AsyncMock(return_value=ListToolsResult(tools=[], nextCursor=None))
        mock_session1.list_resources = AsyncMock(return_value=ListResourcesResult(resources=[], nextCursor=None))
        mock_session1.list_resource_templates = AsyncMock(
            return_value=ListResourceTemplatesResult(resourceTemplates=[], nextCursor=None)
        )
        mock_session1.list_prompts = AsyncMock(
            return_value=ListPromptsResult(prompts=[report_prompt], nextCursor=None)
        )

        mock_session2 = MagicMock()
        mock_session2.initialize = AsyncMock()
        mock_session2.list_tools = AsyncMock(return_value=ListToolsResult(tools=[], nextCursor=None))
        mock_session2.list_resources = AsyncMock(return_value=ListResourcesResult(resources=[], nextCursor=None))
        mock_session2.list_resource_templates = AsyncMock(
            return_value=ListResourceTemplatesResult(resourceTemplates=[], nextCursor=None)
        )
        mock_session2.list_prompts = AsyncMock(
            return_value=ListPromptsResult(prompts=[report_prompt], nextCursor=None)
        )

        # Manually set up AsyncExitStack
        stack = AsyncExitStack()
        await stack.__aenter__()
        client._stack = stack

        try:
            # Mock the connection infrastructure
            with (
                patch("mcp_multi_server.client.stdio_client") as mock_stdio,
                patch("mcp_multi_server.client.ClientSession") as mock_client_session,
            ):

                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock()

                # First connection - mock ClientSession as async context manager
                mock_client_session.return_value.__aenter__ = AsyncMock(return_value=mock_session1)
                mock_client_session.return_value.__aexit__ = AsyncMock()

                with caplog.at_level("WARNING"):
                    await client._connect_server(stack, "server1", ServerConfig(command="python", args=["-m", "test"]))

                assert client.prompt_to_server["write_report"] == "server1"
                assert "collision" not in caplog.text.lower()  # No collision yet

                # Second connection (should cause collision) - update mock to return mock_session2
                mock_client_session.return_value.__aenter__ = AsyncMock(return_value=mock_session2)

                caplog.clear()
                with caplog.at_level("WARNING"):
                    await client._connect_server(stack, "server2", ServerConfig(command="python", args=["-m", "test"]))

                # Verify last-registered-wins
                assert client.prompt_to_server["write_report"] == "server2"

                # Verify collision warning was logged
                assert "collision detected" in caplog.text.lower()
                assert "write_report" in caplog.text
                assert "server1" in caplog.text  # Already provided by
                assert "server2" in caplog.text  # Now overridden by
        finally:
            await stack.__aexit__(None, None, None)
            client._stack = None


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_call_tool_propagates_server_error(self, sample_config_dict: Dict[str, Any]) -> None:
        """Test call_tool propagates server errors gracefully."""
        client = MultiServerClient.from_dict(sample_config_dict)

        mock_server = MagicMock()
        mock_server.call_tool = AsyncMock(side_effect=Exception("Server error"))

        client.tool_to_server = {"test_tool": "test_server"}
        client.sessions = {"test_server": mock_server}

        with pytest.raises(Exception, match="Server error"):
            await client.call_tool("test_tool", {})

    @pytest.mark.asyncio
    async def test_read_resource_propagates_server_error(self, sample_config_dict: Dict[str, Any]) -> None:
        """Test read_resource propagates server errors gracefully."""
        client = MultiServerClient.from_dict(sample_config_dict)

        mock_server = MagicMock()
        mock_server.read_resource = AsyncMock(side_effect=ValueError("Invalid URI"))

        client.sessions = {"test_server": mock_server}

        with pytest.raises(ValueError, match="Invalid URI"):
            await client.read_resource("test_server:invalid://uri")

    @pytest.mark.asyncio
    async def test_get_prompt_propagates_server_error(self, sample_config_dict: Dict[str, Any]) -> None:
        """Test get_prompt propagates server errors gracefully."""
        client = MultiServerClient.from_dict(sample_config_dict)

        mock_server = MagicMock()
        mock_server.get_prompt = AsyncMock(side_effect=ValueError("Invalid arguments"))

        client.prompt_to_server = {"test_prompt": "test_server"}
        client.sessions = {"test_server": mock_server}

        with pytest.raises(ValueError, match="Invalid arguments"):
            await client.get_prompt("test_prompt", {})
