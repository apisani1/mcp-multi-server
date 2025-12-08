"""Utility functions for MCP multi-server client."""

import logging
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Union,
)
from urllib.parse import quote

from pydantic import AnyUrl

from mcp.types import Tool


if TYPE_CHECKING:
    from mcp_multi_server.client import MultiServerClient


def configure_logging(
    name: str = "mcp_multi_server",
    level: str = "INFO",
    format: Optional[str] = None,
    datefmt: Optional[str] = None,
) -> None:
    """
    Configure logging for the mcp_multi_server library but not for the MCP servers
    see MultiServerClient.set_logging_level().

    This function provides a convenient way to configure logging for the library.
    It ensures a handler is configured and sets the log level.

    Note:
        For more control, users can configure logging directly using Python's
        logging module in their application code.

    Args:
        level: Log level as a string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to "INFO".
        format: Optional custom format string for log messages.
                If not provided, uses a default format with timestamp and level.
        datefmt: Optional custom date format string.

    Examples:
    ::

        Basic usage - set log level to DEBUG:
        >>> from mcp_multi_server import configure_logging
        >>> configure_logging(level="DEBUG")

        Custom format:
        >>> configure_logging(
        ...     level="INFO",
        ...     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        ...     datefmt="%Y-%m-%d %H:%M:%S"
        ... )

        Using standard logging module for more control:
        >>> import logging
        >>> logging.getLogger("mcp_multi_server").setLevel(logging.DEBUG)
        >>> # Or configure entire app:
        >>> logging.basicConfig(level=logging.DEBUG)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Ensure root logger has a handler configured
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        # No handlers configured yet, set up basic configuration
        logging.basicConfig(
            level=log_level,
            format=format or "%(asctime)s %(levelname)-8s %(name)s - %(message)s",
            datefmt=datefmt or "%Y-%m-%d %H:%M:%S",
        )

    # Set the log level
    library_logger = logging.getLogger(name)
    library_logger.setLevel(log_level)


def print_capabilities_summary(client: "MultiServerClient") -> None:
    """Utility function to print a summary of all discovered capabilities in a MultiServerClient object."""

    def first_line_preview(text: str = "") -> str:
        first_line = text.splitlines()[0] if text else ""
        return first_line[:80]

    print("\n" + "=" * 80)
    print("CAPABILITIES SUMMARY")
    print("=" * 80)

    for server_name, caps in client.capabilities.items():
        print(f"\n[{server_name}]")

        if caps.tools and caps.tools.tools:
            print(f"  Tools ({len(caps.tools.tools)}):")
            for i, tool in enumerate(caps.tools.tools):
                print(first_line_preview(f"    - {i + 1}) {tool.name}: {tool.description}"))

        if caps.resources and caps.resources.resources:
            print(f"  Resources ({len(caps.resources.resources)}):")
            for i, resource in enumerate(caps.resources.resources):
                print(first_line_preview(f"    {i + 1}) {resource.name}: {resource.uri}"))

        if caps.resource_templates and caps.resource_templates.resourceTemplates:
            print(f"  Resource Templates ({len(caps.resource_templates.resourceTemplates)}):")
            for i, template in enumerate(caps.resource_templates.resourceTemplates):
                print(first_line_preview(f"    {i + 1}) {template.name}: {template.uriTemplate}"))

        if caps.prompts and caps.prompts.prompts:
            print(f"  Prompts ({len(caps.prompts.prompts)}):")
            for i, prompt in enumerate(caps.prompts.prompts):
                print(first_line_preview(f"    {i + 1}) {prompt.name}: {prompt.description}"))

    print("\n" + "=" * 80 + "\n")


def mcp_tools_to_openai_format(tools: List[Tool]) -> List[Dict[str, Any]]:
    """Convert MCP tools to OpenAI function calling format.

    This function transforms MCP tool definitions into the format expected by
    OpenAI's function calling API, enabling seamless integration between MCP
    servers and OpenAI language models.

    Args:
        tools: List of MCP Tool objects to convert.

    Returns:
        List of tool definitions in OpenAI format, where each tool is a dict with:
        - type: Always "function"
        - function: Dict containing name, description, and parameters (JSON schema)

    Example:
        >>> from mcp_multi_server import MultiServerClient
        >>> from mcp_multi_server.utils import mcp_tools_to_openai_format
        >>> from openai import OpenAI
        >>>
        >>> async with MultiServerClient.from_config("mcp_servers.json") as client:
        >>>     tools_result = client.list_tools().tools or []
        >>>     openai_tools = mcp_tools_to_openai_format(tools_result)
        >>>     openai_client = OpenAI()
        >>>     messages = [
        ...         {"role": "user", "content": "Find the weather in New York City."}
        ...     ]
        >>>     response = openai_client.chat.completions.create(
        ...                    model="gpt-4-0613",
        ...                    messages=messages,
        ...                    tools=openai_tools if openai_tools else None,
        ...                    tool_choice="auto" if openai_tools else None,
        ...                ).choices[0]


    Note:
        The inputSchema from MCP tools is used directly as the parameters field in OpenAI format,
        as both follow JSON Schema specifications.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        }
        for tool in tools
    ]


def format_namespace_uri(server_name: str, uri: Union[str, AnyUrl]) -> str:
    """Format a URI with a server namespace prefix.

    Args:
        server_name: Name of the server providing the resource.
        uri: Original URI of the resource.

    Returns:
        Namespaced URI in the format "server_name:uri".

    Examples:
        >>> format_namespace_uri("filesystem", "file:///path/to/file.txt")
        'filesystem:file:///path/to/file.txt'
        >>> format_namespace_uri("db", "records://users/123")
        'db:records://users/123'

    Note:
        This function is used internally by the client to namespace resource URIs
        for auto-routing. Users typically don't need to call this directly.
    """
    return f"{server_name}:{uri}"


def parse_namespace_uri(uri: Union[str, AnyUrl]) -> tuple[str | None, str]:
    """Parse a namespaced URI to extract server name and original URI.

    Args:
        uri: URI that may contain a server namespace prefix.

    Returns:
        Tuple of (server_name, uri). If no namespace is present, server_name is None
        and uri is the original input.

    Examples:
        >>> parse_namespace_uri("filesystem:file:///path/to/file.txt")
        ('filesystem', 'file:///path/to/file.txt')
        >>> parse_namespace_uri("file:///path/to/file.txt")
        (None, 'file:///path/to/file.txt')
        >>> parse_namespace_uri("db:records://users/123")
        ('db', 'records://users/123')

    Note:
        This function distinguishes between protocol schemes (scheme://) and
        namespace prefixes (namespace:). Protocol schemes are not treated as namespaces.
    """
    uri_str = str(uri)

    # Find the first colon
    colon_index = uri_str.find(":")
    if colon_index == -1:
        # No colon found, definitely no namespace
        return None, uri_str

    # Check if this colon is part of a protocol scheme (://)
    if colon_index + 2 < len(uri_str) and uri_str[colon_index : colon_index + 3] == "://":
        # This is a protocol scheme (e.g., file://, http://), not a namespace
        return None, uri_str

    # This is a namespace prefix, split on the first colon
    namespace = uri_str[:colon_index]
    remaining_uri = uri_str[colon_index + 1 :]
    return namespace, remaining_uri


def extract_template_variables(uri_template: Union[str, AnyUrl]) -> List[str]:
    """Extract variable names from a URI template.

    URI templates use curly braces to denote variables that should be substituted.
    Duplicate variables are automatically deduplicated while preserving order.

    Args:
        uri_template: URI template string with variables in {variable} format.

    Returns:
        List of unique variable names found in the template (without braces),
        in order of first appearance.

    Examples:
        >>> extract_template_variables("file:///{path}/to/{filename}")
        ['path', 'filename']
        >>> extract_template_variables("users/{id}/posts/{post_id}")
        ['id', 'post_id']
        >>> extract_template_variables("users/{id}/posts/{id}")
        ['id']
        >>> extract_template_variables("no/variables/here")
        []
    """
    pattern = r"\{([^}]+)\}"
    return list(dict.fromkeys(re.findall(pattern, str(uri_template))))


def substitute_template_variables(uri_template: Union[str, AnyUrl], variables: Dict[str, str]) -> str:
    """Substitute variables in URI template with provided values.

    Variable values are URL-encoded to handle spaces and special characters properly.

    Args:
        uri_template: URI template string with variables in {variable} format.
        variables: Dictionary mapping variable names to their replacement values.

    Returns:
        URI with all variables replaced by their encoded values. Special characters
        in values are percent-encoded to ensure valid URIs.

    Examples:
        >>> substitute_template_variables(
        ...     "file:///{path}/{filename}",
        ...     {"path": "my documents", "filename": "report.txt"}
        ... )
        'file:///my%20documents/report.txt'
        >>> substitute_template_variables(
        ...     "users/{id}",
        ...     {"id": "123"}
        ... )
        'users/123'

    Note:
        Values are URL-encoded to ensure proper handling of special characters in URIs.
    """
    result = str(uri_template)
    for var, value in variables.items():
        # URL encode the value to handle spaces and special characters
        encoded_value = quote(value, safe="")
        result = result.replace(f"{{{var}}}", encoded_value)
    return result
