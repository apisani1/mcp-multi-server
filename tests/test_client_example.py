"""Test script for examples/client/chat_client.py functionality (audio, images, prompts)

This module consolidates tests for audio, image, and prompt handling functionality
from the example chat client implementation.

Note: Full integration testing with actual prompts requires interactive input.
The prompt handling implementation supports images, audio, and all MCP content types.
"""

import asyncio
from contextlib import AsyncExitStack

import pytest

from dotenv import (
    find_dotenv,
    load_dotenv,
)
from examples.client.chat_client import (
    convert_mcp_content_to_message,
    convert_mcp_content_to_tool_response,
    process_tool_result_content,
    search_and_instantiate_prompt,
)
from mcp_multi_server import MultiServerClient


load_dotenv(find_dotenv())


@pytest.mark.asyncio
async def test_audio_tool() -> None:
    """Test the get_audio tool with our audio handling functions."""
    async with AsyncExitStack() as stack:
        # Initialize multi-server client
        client = MultiServerClient("examples/mcp_servers.json")
        await client.connect_all(stack)

        print("=" * 80)
        print("Testing Audio Handling")
        print("=" * 80)

        # Call the get_audio tool
        print("\n1. Calling get_audio tool...")
        tool_result = await client.call_tool("get_audio", {"audio_path": "examples/assets/sound.mp3"})

        print(f"\n2. Tool result has {len(tool_result.content)} content block(s)")

        # Test our audio processing function
        print("\n3. Processing content blocks...")
        result_content = process_tool_result_content(tool_result)

        print("\n4. Tool response content (string):")
        print(f"   {result_content}")

        # Test individual content block conversion
        print("\n5. Testing individual content block conversion...")
        print("   For tool responses (audio as text):")
        for block in tool_result.content:
            converted = convert_mcp_content_to_tool_response(block)
            print(f"   Type: {type(block).__name__} -> text: {converted['text']}")

        print("\n   For user/assistant messages (audio as array):")
        for block in tool_result.content:
            converted_msg = convert_mcp_content_to_message(block)
            # For audio, this returns an array; for text it returns a string
            if isinstance(converted_msg, list):
                print(f"   Type: {type(block).__name__} -> OpenAI format: array with {len(converted_msg)} item(s)")
                print(f"      First item: {converted_msg[0]}")
            else:
                print(f"   Type: {type(block).__name__} -> OpenAI format: string (length: {len(converted_msg)})")

        print("\n" + "=" * 80)
        print("Test completed successfully!")
        print("=" * 80)


@pytest.mark.asyncio
async def test_image_tool() -> None:
    """Test the get_image tool with our new image handling functions."""
    async with AsyncExitStack() as stack:
        # Initialize multi-server client
        client = MultiServerClient("examples/mcp_servers.json")
        await client.connect_all(stack)

        print("=" * 80)
        print("Testing Image Handling")
        print("=" * 80)

        # Call the get_image tool
        print("\n1. Calling get_image tool...")
        tool_result = await client.call_tool("get_image", {"image_path": "examples/assets/picture.jpg"})

        print(f"\n2. Tool result has {len(tool_result.content)} content block(s)")

        # Test our new function to process and display content
        print("\n3. Processing content blocks...")
        result_content = process_tool_result_content(tool_result)

        print("\n4. Tool response content (string):")
        print(f"   {result_content}")

        # Test individual content block conversion
        print("\n5. Testing individual content block conversion...")
        print("   For tool responses (images as text):")
        for block in tool_result.content:
            converted = convert_mcp_content_to_tool_response(block)
            print(f"   Type: {type(block).__name__} -> text: {converted['text']}")

        print("\n   For user/assistant messages (images as image_url):")
        for block in tool_result.content:
            converted_msg = convert_mcp_content_to_message(block)
            # For images, this returns an array; for text it returns a string
            if isinstance(converted_msg, list):
                print(f"   Type: {type(block).__name__} -> OpenAI format: array with {len(converted_msg)} item(s)")
                print(f"      First item type: {converted_msg[0]['type']}")
            else:
                print(f"   Type: {type(block).__name__} -> OpenAI format: string (length: {len(converted_msg)})")

        print("\n" + "=" * 80)
        print("Test completed successfully!")
        print("=" * 80)


@pytest.mark.asyncio
async def test_prompt_not_found() -> None:
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
    asyncio.run(test_audio_tool())
    asyncio.run(test_image_tool())
    asyncio.run(test_prompt_not_found())
