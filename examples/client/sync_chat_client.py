"""Multi-server chat client with OpenAI integration.

This example demonstrates how to use the mcp-multi-server library with OpenAI
to create a chat interface that can call tools, access resources, and use prompts
from multiple MCP servers.
"""

import argparse
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
from examples.support.mcp import (
    convert_mcp_content_to_message,
    get_prompt_arguments,
    get_template_variables_from_user,
    handle_content_block,
    process_tool_result_content,
)
from mcp.types import (
    Prompt,
    Resource,
    ResourceTemplate,
)
from mcp_multi_server import SyncMultiServerClient
from mcp_multi_server.utils import (
    configure_logging,
    extract_template_variables,
    mcp_tools_to_openai_format,
    print_capabilities_summary,
    substitute_template_variables,
)
from openai import OpenAI


load_dotenv(find_dotenv())


def search_and_instantiate_prompt(
    client: SyncMultiServerClient, prompts: Dict[str, Prompt], name: str
) -> List[Dict[str, Any]]:
    """Retrieve a prompt by name and convert to OpenAI message format.

    Args:
        client: SyncMultiServerClient instance.
        prompts: Dict of prompts available from all MCP servers connected to the client.
        name: Name of the prompt to retrieve.

    Returns:
        List of OpenAI-formatted messages with proper image/audio support.

    """
    prompt: Union[Prompt, None]
    if prompts:
        prompt = prompts.get(name)
        if prompt:
            prompt_result = client.get_prompt(name, arguments=get_prompt_arguments(prompt))
            if prompt_result.messages:
                openai_messages = []
                for msg in prompt_result.messages:
                    # Display content to user (shows images/audio locally)
                    handle_content_block(msg.content)
                    # Convert to OpenAI message format (string for text, array for media)
                    content = convert_mcp_content_to_message(msg.content)
                    openai_messages.append({"role": msg.role, "content": content})
                return openai_messages
    return []


def search_and_instantiate_resource(
    client: SyncMultiServerClient,
    resources: Dict[str, Union[Resource, ResourceTemplate]],
    name: str,
    is_template: bool = False,
) -> str:
    """Retrieve a resource by name from the list of resources.

    Args:
        client: SyncMultiServerClient instance.
        resources: Dict of resources available from all MCP servers connected to the client.
        name: Name of the resource to retrieve.

    Returns:
        The resource content.

    """
    if resources:
        resource = resources.get(name)
        if resource:
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
            resource_result = client.read_resource(uri=uri)
            # Assuming single text message resource
            resource_result_text = resource_result.contents[0].text if resource_result.contents else ""  # type: ignore[union-attr]
            print(f"[Result] {resource_result_text}\n")
            return resource_result_text
    return ""


def sync_chat(config_path: str = "examples/mcp_servers.json", verbose: bool = False, model: str = "gpt-5.2") -> None:
    """Run the multi-server chat interface.

    Args:
        config_path: Path to the server configuration file.
        verbose: Enable verbose output for tool calls and results.
        model: OpenAI model to use for chat completions.
    """

    assert os.getenv("OPENAI_API_KEY"), "Error: OPENAI_API_KEY not found in environment"

    configure_logging(level="INFO" if verbose else "WARNING")

    try:
        with SyncMultiServerClient.from_config(config_path) as client:

            client.set_logging_level(level="info" if verbose else "warning")

            # Print capabilities summary
            print_capabilities_summary(client)

            # Fetch all prompts and resources from all servers
            all_prompts = {prompt.name: prompt for prompt in client.list_prompts().prompts}
            all_resources = {resource.name: resource for resource in client.list_resources().resources}
            all_resource_templates = {
                template.name: template for template in client.list_resource_templates().resourceTemplates
            }

            # Get tools from all servers and convert them to OpenAI format
            tools_result = client.list_tools().tools or []
            openai_tools = mcp_tools_to_openai_format(tools_result)

            # Initialize OpenAI client
            openai_client = OpenAI()

            # Chat loop
            messages: List[Dict[str, Any]] = []
            print("Sync-Multi-Server MCP Chat Client")
            print("Type 'exit' or 'quit' to end the conversation\n")

            query = input("> ")

            while query.lower() not in ("exit", "quit"):

                # Add user message, prompt or resource
                if query.startswith("+prompt:"):
                    prompt = query[len("+prompt:") :].strip()
                    prompt_messages = search_and_instantiate_prompt(client, all_prompts, prompt)
                    if prompt_messages:
                        if verbose:
                            print("****Retrieved prompt content (displayed above)\n")
                        # Add all prompt messages to conversation (supports multiple messages)
                        messages.extend(prompt_messages)
                    else:
                        print(f"Prompt '{prompt}' not found.")
                    query = input("> ")
                    continue

                if query.startswith("+resource:"):
                    resource_name = query[len("+resource:") :].strip()
                    resource = search_and_instantiate_resource(client, all_resources, resource_name)  # type: ignore[arg-type]
                    if resource:
                        if verbose:
                            print("****Retrieved resource content (displayed above)\n")
                        messages.append({"role": "user", "content": resource})
                    else:
                        print(f"Resource '{resource_name}' not found.")
                    query = input("> ")
                    continue

                if query.startswith("+template:"):
                    template_name = query[len("+template:") :].strip()
                    resource = search_and_instantiate_resource(
                        client, all_resource_templates, template_name, is_template=True  # type: ignore[arg-type]
                    )
                    if resource:
                        if verbose:
                            print("****Instantiated template content (displayed above)\n")
                        messages.append({"role": "user", "content": resource})
                    else:
                        print(f"Resource Template '{template_name}' not found.")
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
                            tool_result = client.call_tool(tool_name, tool_args)

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
                print(f"\n\033[34m{response.message.content}\033[0m\n")
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
    sync_chat(config_path=args.config, verbose=args.verbose, model=args.model)


if __name__ == "__main__":
    main()
