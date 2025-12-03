"""Multi-server chat client with OpenAI integration.

This example demonstrates how to use the mcp-multi-server library with OpenAI
to create a chat interface that can call tools, access resources, and use prompts
from multiple MCP servers.
"""

import argparse
import asyncio
import json
import os
import traceback
from typing import (
    Any,
    Dict,
    List,
    Union,
)

from dotenv import (
    find_dotenv,
    load_dotenv,
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
    Resource,
    ResourceLink,
    ResourceTemplate,
    TextContent,
)
from mcp_multi_server import MultiServerClient
from mcp_multi_server.utils import (
    configure_logging,
    extract_template_variables,
    mcp_tools_to_openai_format,
    print_capabilities_summary,
    substitute_template_variables,
)
from openai import OpenAI


load_dotenv(find_dotenv())

MODEL = "gpt-4o"


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


async def search_and_instantiate_prompt(
    client: MultiServerClient, prompts: List[Prompt], name: str
) -> List[Dict[str, Any]]:
    """Retrieve a prompt by name and convert to OpenAI message format.

    Args:
        client: MultiServerClient instance.
        prompts: List of prompts available from all MCP servers connected to the client.
        name: Name of the prompt to retrieve.

    Returns:
        List of OpenAI-formatted messages with proper image/audio support.

    """
    if prompts:
        for prompt in prompts:
            if prompt.name == name:
                prompt_result = await client.get_prompt(name, arguments=get_prompt_arguments(prompt))

                if not prompt_result.messages:
                    return []

                openai_messages = []
                for msg in prompt_result.messages:
                    # Display content to user (shows images/audio locally)
                    handle_content_block(msg.content)

                    # Convert to OpenAI message format (string for text, array for media)
                    content = convert_mcp_content_to_message(msg.content)

                    openai_messages.append({"role": msg.role, "content": content})

                return openai_messages
    return []


def get_prompt_arguments(prompt: Prompt) -> dict[str, str]:
    """Ask user for prompt arguments interactively."""
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


async def search_and_instantiate_resource(
    client: MultiServerClient, resources: List[Union[Resource, ResourceTemplate]], name: str, is_template: bool = False
) -> str:
    """Retrieve a resource by name from the list of resources.

    Args:
        client: MultiServerClient instance.
        resources: List of resources available from all MCP servers connected to the client.
        name: Name of the resource to retrieve.

    Returns:
        The resource content.

    """
    if resources:
        for resource in resources:
            if resource.name == name:
                if not is_template:
                    uri = resource.uri  # type: ignore[union-attr]
                else:
                    uri_template = resource.uriTemplate  # type: ignore[union-attr]
                    variables = extract_template_variables(uri_template)
                    print(f"Variables in template: {variables}")
                    if variables:
                        var_values = get_template_variables_from_user(uri_template)
                        uri = substitute_template_variables(uri_template, var_values)
                    else:
                        uri = uri_template
                resource_result = await client.read_resource(uri=uri)
                # Assuming single text message resource
                resource_result_text = resource_result.contents[0].text if resource_result.contents else ""  # type: ignore[union-attr]
                print(f"[Result] {resource_result_text}\n")
                return resource_result_text
    return ""


def get_template_variables_from_user(uri_template: str) -> dict[str, str]:
    """Extract variables from URI template and ask user for values."""
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


async def chat(config_path: str = "examples/mcp_servers.json", verbose: bool = False, model: str = "gpt-4o") -> None:
    """Run the multi-server chat interface.

    Args:
        config_path: Path to the server configuration file.
        verbose: Enable verbose output for tool calls and results.
        model: OpenAI model to use for chat completions.
    """

    assert os.getenv("OPENAI_API_KEY"), "Error: OPENAI_API_KEY not found in environment"

    configure_logging(level="INFO" if verbose else "WARNING")

    try:
        async with MultiServerClient.from_config(config_path) as client:

            await client.set_logging_level(level="info" if verbose else "warning")

            # Print capabilities summary
            print_capabilities_summary(client)

            # Fetch all prompts and resources from all servers
            all_prompts = client.list_prompts().prompts
            all_resources = client.list_resources().resources
            all_resource_templates = client.list_resource_templates().resourceTemplates

            # Get tools from all servers and convert them to OpenAI format
            tools_result = client.list_tools().tools or []
            openai_tools = mcp_tools_to_openai_format(tools_result)

            # Initialize OpenAI client
            openai_client = OpenAI()

            # Chat loop
            messages: List[Dict[str, Any]] = []
            print("Multi-Server MCP Chat Client")
            print("Type 'exit' or 'quit' to end the conversation\n")

            query = input("> ")

            while query.lower() not in ("exit", "quit"):

                # Add user message, prompt or resource
                if query.startswith("+prompt:"):
                    prompt = query[len("+prompt:") :].strip()
                    prompt_messages = await search_and_instantiate_prompt(client, all_prompts, prompt)
                    if not prompt_messages:
                        print(f"Prompt '{prompt}' not found.")
                    else:
                        if verbose:
                            print("****Retrieved prompt content (displayed above)\n")
                        # Add all prompt messages to conversation (supports multiple messages)
                        messages.extend(prompt_messages)
                    query = input("> ")
                    continue

                if query.startswith("+resource:"):
                    resource_name = query[len("+resource:") :].strip()
                    resource = await search_and_instantiate_resource(client, all_resources, resource_name)  # type: ignore[arg-type]
                    if not resource:
                        print(f"Resource '{resource_name}' not found.")
                    else:
                        if verbose:
                            print("****Retrieved resource content (displayed above)\n")
                        messages.append({"role": "user", "content": resource})
                    query = input("> ")
                    continue

                if query.startswith("+template:"):
                    template_name = query[len("+template:") :].strip()
                    resource = await search_and_instantiate_resource(
                        client, all_resource_templates, template_name, is_template=True  # type: ignore[arg-type]
                    )
                    if not resource:
                        print(f"Resource Template '{template_name}' not found.")
                    else:
                        if verbose:
                            print("****Instantiated template content (displayed above)\n")
                        messages.append({"role": "user", "content": resource})
                    query = input("> ")
                    continue

                messages.append({"role": "user", "content": query})

                # Make OpenAI LLM call to answer the user query
                response = openai_client.chat.completions.create(  # type: ignore[call-overload]
                    model=model,
                    messages=messages,
                    tools=openai_tools if openai_tools else None,
                    tool_choice="auto" if openai_tools else None,
                ).choices[0]

                # Handle tool calls
                while response.finish_reason == "tool_calls":
                    messages.append(response.message)

                    for tool_call in response.message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)

                        if verbose:
                            print(f"****[Tool Call] {tool_name}")
                            print(f"****[Arguments] {json.dumps(tool_args, indent=2)}")

                        # Execute tool via appropriate server
                        try:
                            tool_result = await client.call_tool(tool_name, tool_args)

                            # Process tool result content (handles images, audio, text, etc.)
                            # Returns string content (images are converted to text descriptions)
                            result_content = process_tool_result_content(tool_result, verbose=verbose)

                            # Add tool response to conversation
                            # Tool messages must always have string content (not arrays)
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": result_content,
                                }
                            )

                        except Exception as e:
                            error_msg = f"Error executing tool {tool_name}: {str(e)}"
                            print(f"[Error] {error_msg}\n")
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": error_msg,
                                }
                            )

                    # Get next response from LLM with tool results
                    response = openai_client.chat.completions.create(  # type: ignore[call-overload]
                        model=model,
                        messages=messages,
                        tools=openai_tools if openai_tools else None,
                        tool_choice="auto" if openai_tools else None,
                    ).choices[0]

                # Print assistant response
                print(f"\n\033[93m{response.message.content}\033[0m\n")
                messages.append(response.message)

                # Get next user input
                query = input("> ")

    except FileNotFoundError as e:
        print(f"Configuration error: {e}")
    except Exception:
        print("An error occurred:")
        traceback.print_exc()


def main() -> None:
    """Parse command-line arguments and run the chat client."""
    parser = argparse.ArgumentParser(
        description="Multi-server MCP chat client with OpenAI integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --config my_servers.json
  %(prog)s --model gpt-4-turbo --verbose
  %(prog)s -c custom.json -m gpt-3.5-turbo -v
        """,
    )

    parser.add_argument(
        "--config",
        "-c",
        default="examples/mcp_servers.json",
        help="Path to MCP server configuration JSON file (default: %(default)s)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output (tool calls and results)",
    )

    parser.add_argument(
        "--model",
        "-m",
        default="gpt-4o",
        help="OpenAI model to use (default: %(default)s)",
    )

    args = parser.parse_args()
    asyncio.run(chat(config_path=args.config, verbose=args.verbose, model=args.model))


if __name__ == "__main__":
    main()
