"""Common MCP utility functions for chat clients.

This module provides shared functionality for handling MCP content blocks,
converting between MCP and OpenAI formats, and user interaction helpers.
"""

from typing import (
    Any,
    Dict,
    List,
    Union,
)

from examples.support.media_handler import (
    decode_binary_file,
    display_content_from_uri,
    display_image_content,
    play_audio_content,
)
from mcp.types import (
    AudioContent,
    CallToolResult,
    ContentBlock,
    EmbeddedResource,
    ImageContent,
    Prompt,
    ResourceLink,
    TextContent,
)
from mcp_multi_server.utils import extract_template_variables


def handle_content_block(
    content_block: ContentBlock,
) -> None:
    """Display a content block to the user based on its type.

    Args:
        content_block: Content block from MCP tool result or prompt.
    """
    if isinstance(content_block, TextContent):
        print(f"[Result] {content_block.text}\n")
    elif isinstance(content_block, ImageContent):
        print("[Result] Image content received")
        display_image_content(content_block)
    elif isinstance(content_block, AudioContent):
        print(f"[Result] Audio content received ({content_block.mimeType})")
        play_audio_content(content_block)
    elif isinstance(content_block, EmbeddedResource):
        if hasattr(content_block.resource, "text"):
            print(f"[Result] Embedded resource text: {content_block.resource.text}\n")
        else:
            print("[Result] Embedded resource blob")
            filename = input("Enter filename to save embedded resource (or press Enter to skip): ").strip()
            if filename:
                decode_binary_file(content_block, filename)
    elif isinstance(content_block, ResourceLink):
        print(f"[Result] Resource link: {content_block.uri}")
        display_content_from_uri(content_block)
    else:
        # Unknown content type
        content_block_text = str(content_block)
        print(f"[Result] {content_block_text[:min(80, len(content_block_text))]}\n")


def convert_mcp_content_to_tool_response(
    content_block: ContentBlock,
) -> Dict[str, Any]:
    """Convert MCP content block to OpenAI tool message format.

    Tool messages must always be text-only (no images/audio arrays).
    Images and audio are converted to text descriptions.

    Args:
        content_block: Content block from MCP tool result.

    Returns:
        Dict with 'type' and 'text' keys, suitable for OpenAI tool messages.
    """
    if isinstance(content_block, TextContent):
        return {"type": "text", "text": content_block.text}

    if isinstance(content_block, ImageContent):
        return {"type": "text", "text": f"[Image: {content_block.mimeType} received]"}

    if isinstance(content_block, AudioContent):
        return {"type": "text", "text": f"[Audio: {content_block.mimeType} received]"}

    if isinstance(content_block, EmbeddedResource):
        if hasattr(content_block.resource, "text"):
            return {"type": "text", "text": content_block.resource.text}
        return {"type": "text", "text": "[Embedded resource: binary data received]"}

    if isinstance(content_block, ResourceLink):
        return {"type": "text", "text": f"[Resource link: {content_block.uri}]"}

    # Unknown content type
    content_block_text = str(content_block)
    return {"type": "text", "text": content_block_text[: min(80, len(content_block_text))]}


def convert_mcp_content_to_message(
    content_block: ContentBlock,
) -> Union[str, List[Dict[str, Any]]]:
    """Convert MCP content block to OpenAI user/assistant message format.

    Returns plain string for text content, array for media content (images/audio).
    This format is suitable for user and assistant messages, which can include
    rich media content that OpenAI's vision API can process.

    Args:
        content_block: Content block from MCP prompt or resource.

    Returns:
        String for text-only content, array list for media content.
    """
    if isinstance(content_block, TextContent):
        return content_block.text

    if isinstance(content_block, ImageContent):
        # Return array with image_url for OpenAI vision API
        return [
            {"type": "image_url", "image_url": {"url": f"data:{content_block.mimeType};base64,{content_block.data}"}}
        ]

    if isinstance(content_block, AudioContent):
        # Standard GPT-4 cannot process audio, inform the LLM it was played locally
        return [
            {
                "type": "text",
                "text": f"[Audio content ({content_block.mimeType}) was played locally for the user but cannot be processed by the AI]",
            }
        ]

    if isinstance(content_block, EmbeddedResource):
        if hasattr(content_block.resource, "text"):
            return content_block.resource.text
        # TODO: Handle other embedded resource types appropriately
        content_block_text = str(content_block.resource)
        return f"[Embedded resource: {content_block_text[:min(80, len(content_block_text))]}]"

    if isinstance(content_block, ResourceLink):
        return f"[Resource link: {content_block.uri}]"

    # Unknown content type
    content_block_text = str(content_block)
    return content_block_text[: min(80, len(content_block_text))]


def process_tool_result_content(tool_result: CallToolResult, verbose: bool = True) -> str:
    """Process tool result content blocks and convert to OpenAI tool response format.

    Args:
        tool_result: CallToolResult from MCP server.
        verbose: If True, display content blocks to user.

    Returns:
        String content for OpenAI tool response (images and audio converted to text descriptions).
    """
    text_parts = []

    for content_block in tool_result.content:
        # Display to user (shows images and play audio locally)
        if verbose:
            handle_content_block(content_block)
        # Convert to OpenAI tool format (always returns dict with 'text' key)
        converted = convert_mcp_content_to_tool_response(content_block)
        text_parts.append(converted["text"])

    # Join all parts into a single string (required for tool role messages)
    return "\n".join(text_parts) if text_parts else ""


def get_prompt_arguments(prompt: Prompt) -> dict[str, str]:
    """Ask user for prompt arguments interactively.

    Args:
        prompt: MCP Prompt object with argument definitions.

    Returns:
        Dictionary of argument name to value mappings.
    """
    if not prompt.arguments:
        return {}

    arguments: dict[str, str] = {}
    print(f"\nEntering arguments for prompt '{prompt.name}':")
    print(f"Description: {prompt.description}")
    print("(Leave empty for optional arguments)\n")

    for arg in prompt.arguments:
        required_text = "(required)" if arg.required else "(optional)"
        user_input = input(f"Enter {arg.name} {required_text}: ").strip()

        if user_input or arg.required:
            arguments[arg.name] = user_input

    return arguments


def get_template_variables_from_user(uri_template: str) -> dict[str, str]:
    """Extract variables from URI template and ask user for values.

    Args:
        uri_template: URI template string with {variable} placeholders.

    Returns:
        Dictionary of variable name to value mappings.
    """
    variables = extract_template_variables(uri_template)

    if not variables:
        return {}

    print(f"\nTemplate: {uri_template}")
    print("Please provide values for the following variables:")

    values = {}
    for var in variables:
        value = input(f"Enter value for {var}: ").strip()
        values[var] = value

    return values
