"""Tests for SyncMultiServerClient class."""

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

from mcp.types import (
    CallToolResult,
    GetPromptResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    PromptMessage,
    ReadResourceResult,
    TextContent,
    TextResourceContents,
    Tool,
)
from mcp_multi_server import SyncMultiServerClient


# ============================================================================
# Initialization Tests
# ============================================================================


class TestSyncClientInitialization:
    """Tests for SyncMultiServerClient initialization."""

    def test_init_requires_exactly_one_config_source(self) -> None:
        """Test that exactly one of config_path or config_dict must be provided."""
        # Neither provided
        with pytest.raises(ValueError, match="Exactly one"):
            SyncMultiServerClient()

        # Both provided
        with pytest.raises(ValueError, match="Exactly one"):
            SyncMultiServerClient(config_path="config.json", config_dict={"mcpServers": {}})

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_init_with_config_path(self, mock_client_class: MagicMock, sample_config_file: Path) -> None:
        """Test initialization with config_path."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_config.return_value = mock_client

        client = SyncMultiServerClient(config_path=sample_config_file)
        try:
            assert client.config_path == sample_config_file
            assert client.config_dict is None
            mock_client_class.from_config.assert_called_once_with(sample_config_file)
        finally:
            client.shutdown()

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_init_with_config_dict(self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]) -> None:
        """Test initialization with config_dict."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_dict.return_value = mock_client

        client = SyncMultiServerClient(config_dict=sample_config_dict)
        try:
            assert client.config_dict == sample_config_dict
            assert client.config_path is None
            mock_client_class.from_dict.assert_called_once_with(sample_config_dict)
        finally:
            client.shutdown()


class TestSyncFromConfigClassMethod:
    """Tests for from_config class method."""

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_from_config_creates_client(self, mock_client_class: MagicMock, sample_config_file: Path) -> None:
        """Test from_config creates client from file path."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_config.return_value = mock_client

        client = SyncMultiServerClient.from_config(sample_config_file)
        try:
            assert isinstance(client, SyncMultiServerClient)
            assert client.config_path == sample_config_file
        finally:
            client.shutdown()

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_from_config_with_string_path(self, mock_client_class: MagicMock, sample_config_file: Path) -> None:
        """Test from_config with string path."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_config.return_value = mock_client

        client = SyncMultiServerClient.from_config(str(sample_config_file))
        try:
            assert isinstance(client, SyncMultiServerClient)
        finally:
            client.shutdown()


class TestSyncFromDictClassMethod:
    """Tests for from_dict class method."""

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_from_dict_creates_client(self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]) -> None:
        """Test from_dict creates client from dictionary."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_dict.return_value = mock_client

        client = SyncMultiServerClient.from_dict(sample_config_dict)
        try:
            assert isinstance(client, SyncMultiServerClient)
            assert client.config_dict == sample_config_dict
        finally:
            client.shutdown()

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_from_dict_with_empty_config(self, mock_client_class: MagicMock, empty_config_dict: Dict[str, Any]) -> None:
        """Test from_dict with empty configuration."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_dict.return_value = mock_client

        client = SyncMultiServerClient.from_dict(empty_config_dict)
        try:
            assert isinstance(client, SyncMultiServerClient)
        finally:
            client.shutdown()


# ============================================================================
# Context Manager Tests
# ============================================================================


class TestSyncContextManager:
    """Tests for synchronous context manager protocol."""

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_context_manager_enter_exit(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test context manager enter and exit."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            assert client is not None
            assert client.mcp_client is not None

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_context_manager_cleans_up_on_exception(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test that context manager cleans up on exception."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_dict.return_value = mock_client

        try:
            with SyncMultiServerClient.from_dict(sample_config_dict) as client:
                assert client.mcp_client is not None
                raise ValueError("Test exception")
        except ValueError:
            pass

        # After exception, client should be shutdown
        assert client._shutdown is True

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_shutdown_can_be_called_multiple_times(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test that shutdown is safe to call multiple times."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_dict.return_value = mock_client

        client = SyncMultiServerClient.from_dict(sample_config_dict)
        client.shutdown()
        client.shutdown()  # Should not raise
        client.shutdown()  # Should not raise


# ============================================================================
# Capability Listing Tests
# ============================================================================


class TestSyncCapabilityListing:
    """Tests for listing capabilities through sync client."""

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_list_tools_returns_tools(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any], sample_tools: List[Tool]
    ) -> None:
        """Test list_tools returns tools from underlying client."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.list_tools.return_value = ListToolsResult(tools=sample_tools)
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            result = client.list_tools()

            assert len(result.tools) == 2
            assert result.tools[0].name == "get_weather"
            assert result.tools[1].name == "calculate"

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_list_tools_returns_empty_when_not_initialized(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test list_tools returns empty result when client not initialized."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_dict.return_value = mock_client

        client = SyncMultiServerClient.from_dict(sample_config_dict)
        client.mcp_client = None  # Simulate uninitialized state

        result = client.list_tools()
        assert result.tools == []
        client.shutdown()

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_list_resources_returns_resources(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any], sample_resources: list
    ) -> None:
        """Test list_resources returns resources from underlying client."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.list_resources.return_value = ListResourcesResult(resources=sample_resources, nextCursor=None)
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            result = client.list_resources()

            assert len(result.resources) == 2
            assert result.resources[0].name == "Inventory Overview"

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_list_resource_templates_returns_templates(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any], sample_resource_templates: list
    ) -> None:
        """Test list_resource_templates returns templates from underlying client."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.list_resource_templates.return_value = ListResourceTemplatesResult(
            resourceTemplates=sample_resource_templates, nextCursor=None
        )
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            result = client.list_resource_templates()

            assert len(result.resourceTemplates) == 2
            assert result.resourceTemplates[0].name == "Item by ID"

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_list_prompts_returns_prompts(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any], sample_prompts: list
    ) -> None:
        """Test list_prompts returns prompts from underlying client."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.list_prompts.return_value = ListPromptsResult(prompts=sample_prompts, nextCursor=None)
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            result = client.list_prompts()

            assert len(result.prompts) == 2
            assert result.prompts[0].name == "write_report"

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_capabilities_property_returns_dict(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test capabilities property returns capabilities dict."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.capabilities = {"server1": MagicMock()}
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            caps = client.capabilities

            assert "server1" in caps


# ============================================================================
# Tool Call Tests
# ============================================================================


class TestSyncToolCalling:
    """Tests for calling tools through sync client."""

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_call_tool_returns_result(self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]) -> None:
        """Test call_tool returns result from underlying client."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.call_tool = AsyncMock(
            return_value=CallToolResult(
                content=[TextContent(type="text", text="Weather: Sunny")],
                isError=False,
            )
        )
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            result = client.call_tool("get_weather", {"location": "NYC"})

            assert result.isError is False
            assert "Sunny" in result.content[0].text  # type: ignore

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_call_tool_returns_error_when_not_initialized(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test call_tool returns error result when client not initialized."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_dict.return_value = mock_client

        client = SyncMultiServerClient.from_dict(sample_config_dict)
        client.mcp_client = None  # Simulate uninitialized state

        result = client.call_tool("test_tool", {})
        assert result.isError is True
        assert "not initialized" in result.content[0].text  # type: ignore
        client.shutdown()

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_call_tool_with_server_name(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test call_tool with explicit server_name."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.call_tool = AsyncMock(
            return_value=CallToolResult(
                content=[TextContent(type="text", text="Result")],
                isError=False,
            )
        )
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            result = client.call_tool("my_tool", {"arg": "value"}, server_name="tool_server")

            assert result.isError is False
            # Verify server_name was passed to underlying client
            mock_client.call_tool.assert_called_once()
            call_kwargs = mock_client.call_tool.call_args[1]
            assert call_kwargs["server_name"] == "tool_server"


# ============================================================================
# Resource Reading Tests
# ============================================================================


class TestSyncResourceReading:
    """Tests for reading resources through sync client."""

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_read_resource_returns_result(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test read_resource returns result from underlying client."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.read_resource = AsyncMock(
            return_value=ReadResourceResult(
                contents=[TextResourceContents(uri="inventory://overview", mimeType="text/plain", text="Overview data")]
            )
        )
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            result = client.read_resource("resource_server:inventory://overview")

            assert len(result.contents) == 1
            assert "Overview" in result.contents[0].text  # type: ignore

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_read_resource_returns_empty_when_not_initialized(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test read_resource returns empty result when client not initialized."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_dict.return_value = mock_client

        client = SyncMultiServerClient.from_dict(sample_config_dict)
        client.mcp_client = None  # Simulate uninitialized state

        result = client.read_resource("some://uri")
        assert result.contents == []
        client.shutdown()

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_read_resource_with_server_name(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test read_resource with explicit server_name."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.read_resource = AsyncMock(
            return_value=ReadResourceResult(
                contents=[TextResourceContents(uri="inventory://items", mimeType="application/json", text="[]")]
            )
        )
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            result = client.read_resource("inventory://items", server_name="resource_server")

            assert len(result.contents) == 1
            # Verify server_name was passed
            call_kwargs = mock_client.read_resource.call_args[1]
            assert call_kwargs["server_name"] == "resource_server"


# ============================================================================
# Prompt Retrieval Tests
# ============================================================================


class TestSyncPromptRetrieval:
    """Tests for getting prompts through sync client."""

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_get_prompt_returns_result(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test get_prompt returns result from underlying client."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.get_prompt = AsyncMock(
            return_value=GetPromptResult(
                messages=[PromptMessage(role="user", content=TextContent(type="text", text="Write about AI"))]
            )
        )
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            result = client.get_prompt("write_report", {"topic": "AI"})

            assert len(result.messages) == 1
            assert "AI" in result.messages[0].content.text  # type: ignore

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_get_prompt_returns_empty_when_not_initialized(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test get_prompt returns empty result when client not initialized."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_dict.return_value = mock_client

        client = SyncMultiServerClient.from_dict(sample_config_dict)
        client.mcp_client = None  # Simulate uninitialized state

        result = client.get_prompt("test_prompt")
        assert result.messages == []
        client.shutdown()

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_get_prompt_with_server_name(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test get_prompt with explicit server_name."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.get_prompt = AsyncMock(
            return_value=GetPromptResult(
                messages=[PromptMessage(role="user", content=TextContent(type="text", text="Prompt content"))]
            )
        )
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            result = client.get_prompt("my_prompt", server_name="prompt_server")

            assert len(result.messages) == 1
            # Verify server_name was passed
            call_kwargs = mock_client.get_prompt.call_args[1]
            assert call_kwargs["server_name"] == "prompt_server"


# ============================================================================
# Timeout Tests
# ============================================================================


class TestSyncTimeoutHandling:
    """Tests for timeout handling in sync client."""

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_call_tool_with_timeout(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test call_tool respects timeout parameter."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.call_tool = AsyncMock(
            return_value=CallToolResult(
                content=[TextContent(type="text", text="Result")],
                isError=False,
            )
        )
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            # Should complete within timeout
            result = client.call_tool("test_tool", {}, timeout=5.0)
            assert result.isError is False

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_read_resource_with_timeout(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test read_resource respects timeout parameter."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.read_resource = AsyncMock(
            return_value=ReadResourceResult(
                contents=[TextResourceContents(uri="test://uri", mimeType="text/plain", text="Content")]
            )
        )
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            result = client.read_resource("server:test://uri", timeout=5.0)
            assert len(result.contents) == 1

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_get_prompt_with_timeout(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test get_prompt respects timeout parameter."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.get_prompt = AsyncMock(
            return_value=GetPromptResult(
                messages=[PromptMessage(role="user", content=TextContent(type="text", text="Content"))]
            )
        )
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            result = client.get_prompt("test_prompt", timeout=5.0)
            assert len(result.messages) == 1


# ============================================================================
# Lifecycle Tests
# ============================================================================


class TestSyncLifecycle:
    """Tests for lifecycle management in sync client."""

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_background_thread_starts(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test that background thread is started on initialization."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_dict.return_value = mock_client

        client = SyncMultiServerClient.from_dict(sample_config_dict)
        try:
            assert client.thread is not None
            assert client.thread.is_alive()
            assert client.loop is not None
        finally:
            client.shutdown()

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_shutdown_stops_thread(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test that shutdown stops the background thread."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_dict.return_value = mock_client

        client = SyncMultiServerClient.from_dict(sample_config_dict)
        thread = client.thread

        client.shutdown()

        assert client._shutdown is True
        # Thread should stop (may take a moment)
        if thread is not None:
            thread.join(timeout=2)
            assert not thread.is_alive()

    @patch("mcp_multi_server.sync_client.MultiServerClient")
    def test_context_manager_calls_shutdown(
        self, mock_client_class: MagicMock, sample_config_dict: Dict[str, Any]
    ) -> None:
        """Test that exiting context manager calls shutdown."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.from_dict.return_value = mock_client

        with SyncMultiServerClient.from_dict(sample_config_dict) as client:
            pass

        assert client._shutdown is True
