"""Test script for audio handling in chat_client.py"""

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


if __name__ == "__main__":
    asyncio.run(test_audio_tool())
