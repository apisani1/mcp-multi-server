"""
Test script for examples/client/chat_client.py functionality (tools, prompts and resources).

This module consolidates tests for audio, image, files, uris, prompt, and resource handling functionality
from the example chat client implementation.

Note: These are integration tests that require actual MCP servers to be running.
      Use `pytest -m integration` to run only these tests.
      Use `pytest -m "not integration"` to skip these tests (default in CI).
"""

import pytest

from examples.client.chat_client import (
    process_tool_result_content,
    search_and_instantiate_prompt,
    search_and_instantiate_resource,
)
from mcp_multi_server import MultiServerClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audio_tool() -> None:
    """Test the get_audio tool and audio handling functions."""
    async with MultiServerClient.from_config("examples/mcp_servers.json") as client:

        tool_result = await client.call_tool("get_audio", {"audio_path": "examples/assets/sound.mp3"})

        result_content = process_tool_result_content(tool_result, False)
        assert result_content == "[Audio: audio/mpeg received]"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_image_tool() -> None:
    """Test the get_image tool and image handling functions."""
    async with MultiServerClient.from_config("examples/mcp_servers.json") as client:

        tool_result = await client.call_tool("get_image", {"image_path": "examples/assets/picture.jpg"})

        result_content = process_tool_result_content(tool_result, False)
        assert result_content == "[Image: image/png received]"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_file_tool() -> None:
    """Test the get_file tool and file handling functions."""
    async with MultiServerClient.from_config("examples/mcp_servers.json") as client:

        tool_result = await client.call_tool("get_file", {"file_path": "examples/assets/document.txt"})

        result_content = process_tool_result_content(tool_result, False)
        assert result_content == "[Embedded resource: binary data received]"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_uri_tool() -> None:
    """Test the get_uri_content tool and uri handling functions."""
    async with MultiServerClient.from_config("examples/mcp_servers.json") as client:

        tool_result = await client.call_tool(
            "get_uri_content", {"content_uri": "https://modelcontextprotocol.io/docs/getting-started/intro"}
        )

        result_content = process_tool_result_content(tool_result, False)
        assert result_content == "[Resource link: https://modelcontextprotocol.io/docs/getting-started/intro]"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_simple_prompt() -> None:
    """Test proccesing of prompts without parameters."""
    async with MultiServerClient.from_config("examples/mcp_servers.json") as client:

        prompts_result = client.list_prompts()
        all_prompts = {prompt.name: prompt for prompt in prompts_result.prompts}
        prompt_messages = await search_and_instantiate_prompt(client, all_prompts, "inventory_check")

        assert (
            prompt_messages[0]["content"]
            == """
    Consult the inventory database and list every product that needs restocking, providing its name, SKU,
    on-hand quantity, and supplier.
    """
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_prompt_not_found() -> None:
    """Test that non-existent prompts return empty list."""
    async with MultiServerClient.from_config("examples/mcp_servers.json") as client:

        prompts_result = client.list_prompts()
        all_prompts = {prompt.name: prompt for prompt in prompts_result.prompts}
        prompt_messages = await search_and_instantiate_prompt(client, all_prompts, "nonexistent_prompt")

        assert len(prompt_messages) == 0, "Expected empty list for non-existent prompt"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resource() -> None:
    """Test proccesing of resources."""
    async with MultiServerClient.from_config("examples/mcp_servers.json") as client:

        resource_result = client.list_resources()
        all_resources = {resource.name: resource for resource in resource_result.resources}
        resource = await search_and_instantiate_resource(client, all_resources, "get_database_schema")  # type: ignore

        assert "{" in resource and "}" in resource, "Expected JSON content in resource"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resource_not_found() -> None:
    """Test that non-existent resources return empty string."""
    async with MultiServerClient.from_config("examples/mcp_servers.json") as client:

        resource_result = client.list_resources()
        all_resources = {resource.name: resource for resource in resource_result.resources}
        resource = await search_and_instantiate_resource(client, all_resources, "nonexistent_resource")  # type: ignore

        assert resource == "", "Expected empty string for non-existent resource"
