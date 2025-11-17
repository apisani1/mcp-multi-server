mcp\_multi\_server package
==========================

.. automodule:: mcp_multi_server
   :no-members:
   :show-inheritance:

This package provides a unified interface for managing multiple MCP
(Model Context Protocol) servers.

**Main Exports:**

- :class:`~mcp_multi_server.client.MultiServerClient` - Main client
  class for managing connections to multiple MCP servers
- :class:`~mcp_multi_server.config.ServerConfig` - Configuration model
  for individual server settings
- :class:`~mcp_multi_server.config.MCPServersConfig` - Configuration
  model for multiple servers
- :class:`~mcp_multi_server.types.ServerCapabilities` - Type definition
  for server capabilities
- Utility functions from :mod:`~mcp_multi_server.utils`:

  - :func:`~mcp_multi_server.utils.mcp_tools_to_openai_format` - Convert
    MCP tools to OpenAI format
  - :func:`~mcp_multi_server.utils.format_namespace_uri` - Format URI
    with namespace prefix
  - :func:`~mcp_multi_server.utils.parse_namespace_uri` - Parse
    namespaced URI
  - :func:`~mcp_multi_server.utils.extract_template_variables` - Extract
    variables from URI template
  - :func:`~mcp_multi_server.utils.substitute_template_variables` -
    Substitute variables in URI template
  - :func:`~mcp_multi_server.utils.print_capabilities_summary` - Print
    capabilities summary

See the submodules below for detailed API documentation.

Submodules
----------

mcp\_multi\_server.client module
--------------------------------

.. automodule:: mcp_multi_server.client
   :members:
   :show-inheritance:
   :undoc-members:

mcp\_multi\_server.config module
--------------------------------

.. automodule:: mcp_multi_server.config
   :members:
   :show-inheritance:
   :undoc-members:

mcp\_multi\_server.types module
-------------------------------

.. automodule:: mcp_multi_server.types
   :members:
   :show-inheritance:
   :undoc-members:

mcp\_multi\_server.utils module
-------------------------------

.. automodule:: mcp_multi_server.utils
   :members:
   :show-inheritance:
   :undoc-members:
