"""Multi-server chat client with OpenAI integration.

This example demonstrates how to use the mcp-multi-server library with OpenAI
to create an intelligent chat interface that can call tools, access resources,
and use prompts from multiple MCP servers.
"""

import asyncio
import json
import os
import re
import traceback
from contextlib import AsyncExitStack
from typing import (
    Any,
    Dict,
    List,
    Union,
)
from urllib.parse import quote

from dotenv import (
    find_dotenv,
    load_dotenv,
)
from examples.support.media_handler import (
    create_openai_image_url,
    decode_binary_file,
    describe_audio_content,
    display_audio_content,
    display_content_from_uri,
    display_image_content,
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
    Tool,
)
from mcp_multi_server import MultiServerClient
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
        display_audio_content(content_block)
        print()  # Add newline for consistency
    elif isinstance(content_block, EmbeddedResource):
        print(f"[Result] Embedded resource: {content_block.resource}")
        # Optionally save to file
        filename = input("Enter filename to save embedded resource (or press Enter to skip): ").strip()
        if filename:
            decode_binary_file(content_block, filename)
    elif isinstance(content_block, ResourceLink):
        print(f"[Result] Resource link: {content_block.uri}")
        display_content_from_uri(content_block)
    else:
        print(f"[Result] {str(content_block)}\n")


def convert_mcp_content_to_openai(
    content_block: ContentBlock,
    for_tool_response: bool = False,
) -> Union[str, List[Dict[str, Any]], Dict[str, Any]]:
    """Convert MCP content block to OpenAI message content format.

    Args:
        content_block: Content block from MCP tool result or prompt.
        for_tool_response: If True, return format suitable for tool messages (always dict).
                          If False, return format suitable for user/assistant messages
                          (string for text, array for media).

    Returns:
        For tool responses: Always returns dict with 'type' and 'text' keys.
        For user/assistant messages: Returns string for text-only, array for media content.
    """
    if isinstance(content_block, TextContent):
        # For tool responses, return dict format
        if for_tool_response:
            return {"type": "text", "text": content_block.text}
        # For user/assistant messages, return plain string
        return content_block.text

    if isinstance(content_block, ImageContent):
        # OpenAI only allows images in user/assistant messages, not tool messages
        if for_tool_response:
            return {"type": "text", "text": f"[Image: {content_block.mimeType} received]"}
        # For user/assistant, return array with image_url
        return [{"type": "image_url", "image_url": {"url": create_openai_image_url(content_block)}}]

    if isinstance(content_block, AudioContent):
        # OpenAI only allows audio in user/assistant messages, not tool messages
        if for_tool_response:
            return {"type": "text", "text": describe_audio_content(content_block)}
        # For future: return audio format for user/assistant messages when we integrate audio API
        # For now, return text description in array format
        return [{"type": "text", "text": f"[Audio: {content_block.mimeType}]"}]

    if isinstance(content_block, EmbeddedResource):
        text = f"[Embedded resource: {content_block.resource}]"
        if for_tool_response:
            return {"type": "text", "text": text}
        return text

    if isinstance(content_block, ResourceLink):
        text = f"[Resource link: {content_block.uri}]"
        if for_tool_response:
            return {"type": "text", "text": text}
        return text

    # Unknown content type
    text = str(content_block)
    if for_tool_response:
        return {"type": "text", "text": text}
    return text


def process_tool_result_content(tool_result: CallToolResult) -> str:
    """Process tool result content blocks and convert to OpenAI tool response format.

    Args:
        tool_result: CallToolResult from MCP server.

    Returns:
        String content for OpenAI tool response (images converted to text descriptions).
    """
    text_parts = []

    for content_block in tool_result.content:
        # Display to user (shows images locally)
        handle_content_block(content_block)
        # Convert to OpenAI format (for_tool_response=True converts images to text)
        converted = convert_mcp_content_to_openai(content_block, for_tool_response=True)
        text_parts.append(converted["text"])

    # Join all parts into a single string (required for tool role messages)
    return "\n".join(text_parts) if text_parts else ""


async def search_and_instantiate_prompt(
    client: MultiServerClient, prompts: List[Prompt], name: str
) -> List[Dict[str, Any]]:
    """Retrieve a prompt by name and convert to OpenAI message format.

    Args:
        client: MultiServerClient instance.
        prompts: List of prompt dictionaries.
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

                    # Convert to OpenAI format (returns proper format automatically)
                    content = convert_mcp_content_to_openai(msg.content, for_tool_response=False)

                    openai_messages.append({"role": msg.role, "content": content})

                return openai_messages
    return []


def get_prompt_arguments(prompt: Prompt) -> dict[str, str]:
    """Ask user for prompt arguments interactively."""
    arguments: dict[str, str] = {}

    if not prompt.arguments:
        return arguments

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
        resources: List of resource dictionaries.
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
                return resource_result.contents[0].text if resource_result.contents else ""  # type: ignore[union-attr]
    return ""


def extract_template_variables(uri_template: str) -> list[str]:
    """Extract variable names from a URI template."""
    pattern = r"\{([^}]+)\}"
    return re.findall(pattern, uri_template)


def get_template_variables_from_user(uri_template: str) -> dict[str, str]:
    """Extract variables from URI template and ask user for values."""
    pattern = r"\{([^}]+)\}"
    variables = re.findall(pattern, uri_template)

    if not variables:
        return {}

    print(f"\nTemplate: {uri_template}")
    print("Please provide values for the following variables:")

    values = {}
    for var in variables:
        value = input(f"Enter value for {var}: ").strip()
        values[var] = value

    return values


def substitute_template_variables(uri_template: str, variables: dict[str, str]) -> str:
    """Substitute variables in URI template with provided values.

    URL-encodes the values to handle spaces and special characters properly.
    """
    result = uri_template
    for var, value in variables.items():
        # URL encode the value to handle spaces and special characters
        encoded_value = quote(value, safe="")
        result = result.replace(f"{{{var}}}", encoded_value)
    return result


async def chat(config_path: str = "examples/mcp_servers.json") -> None:
    """Run the multi-server chat interface.

    Args:
        config_path: Path to the server configuration file.
    """
    assert os.getenv("OPENAI_API_KEY"), "Error: OPENAI_API_KEY not found in environment"

    try:
        async with AsyncExitStack() as stack:
            # Initialize multi-server client
            client = MultiServerClient(config_path)
            await client.connect_all(stack)

            # Print capabilities summary
            client.print_capabilities_summary()

            # Fetch all prompts and resources from all servers
            all_prompts = client.list_prompts().prompts
            all_resources = client.list_resources().resources
            all_resource_templates = client.list_resource_templates().resourceTemplates

            # Get all tools for OpenAI using the new list_tools() method
            tools_result = client.list_tools()
            all_tools: List[Tool] = tools_result.tools or []

            # Convert MCP tools to OpenAI format
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                }
                for tool in all_tools
            ]

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
                        print("****Retrieved prompt content (displayed above)\n")
                        # Add all prompt messages to conversation (supports multiple messages)
                        messages.extend(prompt_messages)
                    query = input("> ")
                    continue

                if query.startswith("+resource:"):
                    resource_name = query[len("+resource:") :].strip()
                    # List variance: List[Resource] not compatible with List[Union[Resource, ResourceTemplate]]
                    resource = await search_and_instantiate_resource(
                        client, all_resources, resource_name  # type: ignore[arg-type]
                    )
                    if not resource:
                        print(f"Resource '{resource_name}' not found.")
                    else:

                        print(f"****Retrieved resource content:\n{resource}\n")

                        messages.append({"role": "user", "content": resource})
                    query = input("> ")
                    continue

                if query.startswith("+template:"):
                    template_name = query[len("+template:") :].strip()
                    # List variance: List[ResourceTemplate] not compatible with List[Union[...]]
                    resource = await search_and_instantiate_resource(
                        client, all_resource_templates, template_name, is_template=True  # type: ignore[arg-type]
                    )
                    if not resource:
                        print(f"Resource Template '{template_name}' not found.")
                    else:

                        print(f"****Instantiated template content:\n{resource}\n")

                        messages.append({"role": "user", "content": resource})
                    query = input("> ")
                    continue

                messages.append({"role": "user", "content": query})

                # Make OpenAI LLM call to answer the user query
                response = openai_client.chat.completions.create(  # type: ignore[call-overload]
                    model=MODEL,
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

                        print(f"\n[Tool Call] {tool_name}")
                        print(f"[Arguments] {json.dumps(tool_args, indent=2)}")

                        # Execute tool via appropriate server
                        try:
                            tool_result = await client.call_tool(tool_name, tool_args)

                            # Process tool result content (handles images, audio, text, etc.)
                            # Returns string content (images are converted to text descriptions)
                            result_content = process_tool_result_content(tool_result)

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
                        model=MODEL,
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


if __name__ == "__main__":
    asyncio.run(chat())
