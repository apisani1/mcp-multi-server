"""Test script for prompt handling in chat_client.py

Note: Full integration testing with actual prompts requires interactive input.
This test file only includes basic non-interactive functionality tests.
The prompt handling implementation supports images, audio, and all MCP content types.
"""

import asyncio
from contextlib import AsyncExitStack

import pytest
from dotenv import (
    find_dotenv,
    load_dotenv,
)

from examples.clients.chat_client import search_and_instantiate_prompt
from mcp_multi_server import MultiServerClient


load_dotenv(find_dotenv())


@pytest.mark.asyncio
async def test_prompt_not_found():
    """Test that non-existent prompts return empty list."""
    async with AsyncExitStack() as stack:
        # Initialize multi-server client
        client = MultiServerClient("examples/mcp_servers.json")
        await client.connect_all(stack)

        # Get available prompts
        prompts_result = client.list_prompts()
        all_prompts = prompts_result.prompts

        # Try to retrieve a non-existent prompt
        prompt_messages = await search_and_instantiate_prompt(client, all_prompts, "nonexistent_prompt")

        # Verify we got an empty list
        assert len(prompt_messages) == 0, "Expected empty list for non-existent prompt"


if __name__ == "__main__":
    asyncio.run(test_prompt_not_found())
