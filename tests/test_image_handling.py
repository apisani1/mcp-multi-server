"""Test script for image handling in chat_client.py"""

import asyncio
from contextlib import AsyncExitStack

import pytest
from dotenv import (
    find_dotenv,
    load_dotenv,
)

# Import the new functions we created
from examples.clients.chat_client import (
    convert_mcp_content_to_openai,
    process_tool_result_content,
)
from mcp_multi_server import MultiServerClient


load_dotenv(find_dotenv())


@pytest.mark.asyncio
async def test_image_tool():
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

        print(f"\n4. Tool response content (string):")
        print(f"   {result_content}")

        # Test individual content block conversion
        print("\n5. Testing individual content block conversion...")
        print("   For tool responses (images as text):")
        for block in tool_result.content:
            converted = convert_mcp_content_to_openai(block, for_tool_response=True)
            print(f"   Type: {type(block).__name__} -> text: {converted['text']}")

        print("\n   For user/assistant messages (images as image_url):")
        for block in tool_result.content:
            converted = convert_mcp_content_to_openai(block, for_tool_response=False)
            # For images, this returns an array; for text it returns a string
            if isinstance(converted, list):
                print(f"   Type: {type(block).__name__} -> OpenAI format: array with {len(converted)} item(s)")
                print(f"      First item type: {converted[0]['type']}")
            else:
                print(f"   Type: {type(block).__name__} -> OpenAI format: string (length: {len(converted)})")

        print("\n" + "=" * 80)
        print("Test completed successfully!")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_image_tool())
