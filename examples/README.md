# MCP Multi-Server Examples

This directory contains comprehensive examples demonstrating how to use the `mcp-multi-server` library and how to implement your own MCP servers and clients.

## Directory Structure

```
examples/
├── servers/          # Example MCP server implementations
│   ├── tool_server.py      # Server providing tools (inventory CRUD operations)
│   ├── resource_server.py  # Server providing resources (read-only inventory data)
│   └── prompt_server.py    # Server providing prompts (inventory-focused prompt templates)
├── client/           # Example client implementations
│   ├── chat_client.py      # Async multi-server chat with OpenAI integration
│   └── sync_chat_client.py # Sync multi-server chat with OpenAI integration
├── support/          # Supporting modules
│   ├── inventory_db.py     # Inventory database with pickle persistence
│   ├── initialize_db.py    # Database initialization script
│   ├── media_handler.py    # Media file handling utilities
│   └── mcp.py              # Common MCP utilities for chat clients
├── assets/           # Media assets for examples
│   ├── picture.jpg
│   └── sound.mp3
└── mcp_servers.json  # Configuration for example servers
```

## Prerequisites

Install the library with examples dependencies:

```bash
# From the project root
poetry install --extras examples

# Or with pip
pip install -e ".[examples]"
```

You'll also need to set up an OpenAI API key for the chat client:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Example Servers

### 1. Tool Server ([tool_server.py](servers/tool_server.py))

Demonstrates MCP tools with full CRUD operations on an inventory database using Pydantic models.

**Features:**
- Complete inventory management (categories, suppliers, products, supplier-products, inventory items)
- Complex structured data with relationships and enriched queries
- Media content tools (images, audio, files, URIs)
- Cascade delete operations
- Statistical aggregations

**Run the server:**
```bash
python -m examples.servers.tool_server
```

**Available Tools (34 total):**

*Create Operations:*
- `add_category` - Add a product category
- `add_supplier` - Add a supplier with contact info
- `add_product` - Add a product with details
- `add_supplier_product` - Link supplier to product
- `add_inventory_item` - Add inventory item at location

*Read Operations:*
- `inventory_overview` - Get full inventory statistics
- `database_schema` - Get complete schema definition
- `list_categories` - List all categories
- `category_statistics` - Get category metrics
- `products_by_category` - Get products in category
- `items_by_category` - Get inventory items by category
- `list_suppliers` - List all suppliers
- `products_by_supplier` - Get products by supplier
- `items_by_supplier` - Get inventory items by supplier
- `supplier_products_by_supplier` - Get supplier-product relationships
- `supplier_products_by_product` - Get suppliers for product
- `list_products` - List all products
- `items_by_name` - Find items by product name
- `search_inventory` - Search inventory by keyword
- `low_stock_items` - Get items below reorder point

*Update Operations:*
- `update_category` - Update category description
- `update_supplier` - Update supplier information
- `update_product` - Update product details
- `update_supplier_product` - Update supplier-product relationship
- `update_inventory_item` - Update inventory item

*Delete Operations (with CASCADE):*
- `delete_inventory_item` - Delete an inventory item
- `delete_supplier_product` - Delete supplier-product link
- `delete_product` - Delete product and related data
- `delete_supplier` - Delete supplier and relationships
- `delete_category` - Delete category and related data

*Media & File Tools:*
- `get_image` - Load image as base64-encoded content
- `get_audio` - Load audio as base64-encoded content
- `get_file` - Load file as embedded resource
- `get_uri_content` - Create resource link for URI

### 2. Resource Server ([resource_server.py](servers/resource_server.py))

Demonstrates MCP resources for read-only data access with static resources and dynamic URI templates.

**Features:**
- Read-only inventory data access (complements tool server's CRUD operations)
- Static resources for common queries
- Dynamic resource templates with parameter substitution
- Structured data exposure via URIs
- Same underlying database as tool server

**Run the server:**
```bash
python -m examples.servers.resource_server
```

**Available Resources (6 static):**
- `inventory://overview` - Full inventory statistics and summary
- `inventory://database-schema` - Complete schema definition
- `inventory://categories` - List of all categories
- `inventory://suppliers` - List of all suppliers
- `inventory://products` - List of all products
- `inventory://low-stock` - Items below reorder point

**Available Resource Templates (7 dynamic):**
- `inventory://category/stats/{category}` - Category-specific statistics
- `inventory://category/products/{category}` - Products in category
- `inventory://category/items/{category}` - Inventory items in category
- `inventory://supplier/products/{supplier_name}` - Products by supplier
- `inventory://supplier/items/{supplier_name}` - Inventory items by supplier
- `inventory://product/item/{product_name}` - Items for product by name
- `inventory://search/item/{query}` - Search inventory by keyword

### 3. Prompt Server ([prompt_server.py](servers/prompt_server.py))

Demonstrates MCP prompts with various return types and media content handling.

**Features:**
- Text-based prompts for inventory operations
- Multi-message conversation prompts
- Media loading (images, audio) in prompt messages
- File embedding and URI linking
- Parameterized prompt templates

**Run the server:**
```bash
python -m examples.servers.prompt_server
```

**Available Prompts (7 total):**

*Inventory-Specific Prompts:*
- `category_promotion` - Generate prompt for category-wide discount pricing
- `inventory_restock_brief` - Multi-message prompt for low-stock analysis

*Media Loading Prompts:*
- `load_image` - Load image file as ImageContent in message
- `load_audio` - Load audio file as AudioContent in message
- `load_file` - Load any file as embedded BlobResource
- `load_uri_content` - Create ResourceLink for content URI

## Example Clients

### Async Chat Client ([client/chat_client.py](client/chat_client.py))

**PRIMARY EXAMPLE** - Full-featured async chat interface integrating all three MCP servers with OpenAI.

**Features:**
- Automatically starts and connects to all configured servers
- Converts MCP tools to OpenAI function calling format
- Interactive prompt and resource insertion with special syntax
- Template variable substitution
- Tool call execution with automatic routing to correct server
- Comprehensive error handling and logging

**Run the client:**
```bash
# Easiest method - uses Makefile to auto-start servers
make run-chat

# Or manually with poetry
poetry run python3 -m examples.client.chat_client

# Or manually with python (servers auto-start via mcp_servers.json)
python -m examples.client.chat_client
```

### Sync Chat Client ([client/sync_chat_client.py](client/sync_chat_client.py))

Synchronous version of the chat client using `SyncMultiServerClient`. Identical functionality to the async client but uses blocking calls instead of async/await.

**Run the client:**
```bash
# Using Makefile
make run-sync-chat

# Or manually with poetry
poetry run python3 -m examples.client.sync_chat_client

# Or manually with python
python -m examples.client.sync_chat_client
```

**When to use:**
- Non-async codebases that can't use `async`/`await`
- Simple scripts where async complexity isn't needed
- Integration with synchronous frameworks

**Usage:**
- **Normal chat**: Type your message and press Enter
- **Insert prompt**: Type `+prompt:category_promotion` to insert a prompt template
- **Insert resource**: Type `+resource:inventory://overview` to insert resource data
- **Insert template**: Type `+template:inventory://category/items/{category}` for parameterized resources
- **Exit**: Type `exit` or `quit` to end the session

**Example Interactions:**
```
> Show me the inventory overview
[Uses inventory://overview resource to provide comprehensive statistics]

> What electronics products do we have?
[Uses products_by_category tool with category="Electronics"]

> Find all low-stock items and recommend reorder quantities
[Uses low_stock_items tool and analyzes results]

> +prompt:category_promotion
[Inserts the category promotion prompt template for you to fill in]
```

## Configuration

The [mcp_servers.json](mcp_servers.json) file defines the three example servers:

```json
{
  "mcpServers": {
    "tool_server": {
      "command": "poetry",
      "args": ["run", "python3", "-m", "examples.servers.tool_server"]
    },
    "resource_server": {
      "command": "poetry",
      "args": ["run", "python3", "-m", "examples.servers.resource_server"]
    },
    "prompt_server": {
      "command": "poetry",
      "args": ["run", "python3", "-m", "examples.servers.prompt_server"]
    }
  }
}
```

## Inventory Database

The examples use a shared inventory database ([support/inventory_db.py](support/inventory_db.py)) that demonstrates:

- **Five entity types**: Categories, Suppliers, Products, Supplier-Products, Inventory Items
- **Relationships**: Products belong to categories, have suppliers, and have inventory at locations
- **Persistence**: Automatic pickle-based persistence to `sample_db.pkl`
- **Sample data**: Pre-populated with electronics, furniture, and clothing items
- **Indexes**: Fast lookups by name, SKU, category, and supplier
- **CRUD operations**: Full create, read, update, delete with cascade support

The database is initialized with sample data on first run via [support/initialize_db.py](support/initialize_db.py).

## Using the Library in Your Code

### Basic Multi-Server Setup

```python
import asyncio
from mcp_multi_server import MultiServerClient

async def main():
    async with MultiServerClient.from_config("examples/mcp_servers.json") as client:
        # Print what's available
        client.print_capabilities_summary()

        # List all tools from all servers
        tools = client.list_tools()
        print(f"Total tools: {len(tools.tools)}")

        # Call a tool (auto-routed to correct server)
        result = await client.call_tool("list_products", {})
        print(result)

asyncio.run(main())
```

### Synchronous Multi-Server Setup

```python
from mcp_multi_server import SyncMultiServerClient

# Using context manager (recommended)
with SyncMultiServerClient.from_config("examples/mcp_servers.json") as client:
    # Print what's available
    client.print_capabilities_summary()

    # List all tools from all servers
    tools = client.list_tools()
    print(f"Total tools: {len(tools.tools)}")

    # Call a tool (auto-routed to correct server)
    result = client.call_tool("list_products", {})
    print(result)
```

### OpenAI Integration

```python
from mcp_multi_server import MultiServerClient, mcp_tools_to_openai_format
from openai import OpenAI
import json

async def chat():
    async with MultiServerClient.from_config("examples/mcp_servers.json") as mcp_client:
        # Convert MCP tools to OpenAI format
        tools_result = mcp_client.list_tools()
        openai_tools = mcp_tools_to_openai_format(tools_result.tools)

        # Use with OpenAI
        openai_client = OpenAI()
        messages = [{"role": "user", "content": "Show me all products in the Electronics category"}]

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=openai_tools
        )

        # Handle tool calls
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                result = await mcp_client.call_tool(
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments)
                )
                print(f"Tool result: {result}")
```

### Using Resources

```python
async def get_inventory_data():
    async with MultiServerClient.from_config("examples/mcp_servers.json") as client:
        # Read a static resource
        overview = await client.read_resource("resource_server:inventory://overview")
        print(f"Inventory overview: {overview}")

        # Read a dynamic resource with template
        electronics = await client.read_resource(
            "resource_server:inventory://category/products/Electronics"
        )
        print(f"Electronics products: {electronics}")
```

### Using Prompts

```python
async def use_prompts():
    async with MultiServerClient.from_config("examples/mcp_servers.json") as client:
        # Get a text-based prompt
        result = await client.get_prompt(
            "category_promotion",
            {"category": "Electronics", "discount_percentage": "20"}
        )
        print(f"Generated prompt: {result.messages[0].content}")

        # Get a multi-message prompt
        result = await client.get_prompt(
            "inventory_restock_brief",
            {"category": "Electronics", "min_stock": 10}
        )
        print(f"Multi-message prompt has {len(result.messages)} messages")
```

## Learning Path

1. **Start with the chat client** - Run `make run-chat` to see the full system in action
2. **Explore the servers** - Examine how each server exposes different capability types
3. **Study the database** - Understand the inventory database structure and relationships
4. **Review integrations** - See how tools/resources/prompts work with OpenAI
5. **Build your own** - Use these examples as templates for your servers and clients

## Quick Start

The fastest way to see everything working:

```bash
# 1. Install dependencies
poetry install --extras examples

# 2. Set your OpenAI API key
export OPENAI_API_KEY="your-key-here"

# 3. Run the chat client (auto-starts all servers)
make run-chat          # async version
# or
make run-sync-chat     # sync version

# 4. Try some queries
> Show me the inventory overview
> What electronics products do we have in stock?
> Find all items below their reorder point
> Add a new product category called "Office Supplies"
```

## Common Patterns

### Server Patterns

1. **Tools**: Use `@mcp.tool()` decorator for executable functions
2. **Resources**: Use `@mcp.resource()` for data endpoints
3. **Prompts**: Use `@mcp.prompt()` for prompt templates
4. **Structured Data**: Use Pydantic models for type safety

### Client Patterns

1. **Context Manager**: Always use `async with` for automatic cleanup
2. **Auto-Routing**: Let the client route tools/prompts automatically
3. **Namespaced URIs**: Use server:uri format for resources
4. **Error Handling**: Check `CallToolResult.isError` for tool failures

## Troubleshooting

### Servers won't start
- Check that all dependencies are installed: `poetry install --extras examples`
- Verify Python version >= 3.10
- Check server logs for specific error messages

### Can't connect to servers
- Ensure servers are running before starting client
- Verify paths in mcp_servers.json are correct
- Check that ports aren't already in use

### OpenAI integration issues
- Verify OPENAI_API_KEY environment variable is set
- Check you have sufficient OpenAI API credits
- Ensure you're using a compatible model (gpt-4o, gpt-4-turbo, etc.)

## Next Steps

- Modify the example servers to add your own tools/resources/prompts
- Create your own MCP servers for your specific use cases
- Integrate the multi-server client into your applications
- Explore the main library documentation for advanced features

## Resources

- [MCP Protocol Documentation](https://modelcontextprotocol.io)
- [FastMCP Documentation](https://github.com/modelcontextprotocol/fastmcp)
- [Project Repository](https://github.com/apisani1/mcp-multi-server)
