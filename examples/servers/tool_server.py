"""Example showing structured input and output with tools."""

import logging
from typing import (  # Optional,; TypedDict,
    Dict,
    List,
    Union,
)

from mcp.server.fastmcp import FastMCP
from mcp.types import (
    AudioContent,
    CallToolResult,
    ImageContent,
)


# from pydantic import (
#     BaseModel,
#     Field,
# )

try:
    from ..support.inventory_db import (  # db,
        CategoryStatistics,
        DatabaseSchema,
        EnrichedInventoryItem,
        InventoryOverview,
        Product,
        Supplier,
    )
    from ..support.media_handler import (
        get_audio,
        get_image,
    )
    from .resource_server import (
        get_category_statistics,
        get_database_schema,
        get_inventory_overview,
        get_items_by_category,
        get_items_by_name,
        get_items_by_supplier,
        get_low_stock_items,
        get_products_by_category,
        get_products_by_supplier,
        list_categories,
        list_products,
        list_suppliers,
        search_inventory,
    )
except ImportError:
    from examples.servers.resource_server import (
        get_category_statistics,
        get_database_schema,
        get_inventory_overview,
        get_items_by_category,
        get_items_by_name,
        get_items_by_supplier,
        get_low_stock_items,
        get_products_by_category,
        get_products_by_supplier,
        list_categories,
        list_products,
        list_suppliers,
        search_inventory,
    )
    from examples.support.inventory_db import (  # db,
        CategoryStatistics,
        DatabaseSchema,
        EnrichedInventoryItem,
        InventoryOverview,
        Product,
        Supplier,
    )
    from examples.support.media_handler import (
        get_audio,
        get_image,
    )

# Suppress MCP library INFO logs
logging.getLogger("mcp").setLevel(logging.WARNING)

# Create server
mcp = FastMCP("Inventory Tool Server")


@mcp.tool(name="inventory_overview")
def get_inventory_overview_tool() -> InventoryOverview:
    """Get an overview of the inventory, including:
    - total inventory items
    - total inventory value
    - items with low level of stock
    - items per category
    - percentage of items per category
    """
    return get_inventory_overview()


@mcp.tool(name="database_schema")
def get_database_schema_tool() -> DatabaseSchema:
    """Get the complete database schema definition."""
    return get_database_schema()


@mcp.tool(name="list_categories")
def list_categories_tool() -> List[Dict[str, str]]:
    """Get the list of all valid product categories with names and descriptions.."""
    return list_categories()


@mcp.tool(name="category_statistics")
def get_category_statistics_tool(category: str) -> CategoryStatistics:
    """Get category statistics, including:
    - total category items in inventory
    - total category value in inventory
    - category items with low level of stock
    - items per products in the category
    - percentage of items per products in the category
    """
    return get_category_statistics(category)


@mcp.tool(name="products_by_category")
def get_products_by_category_tool(category: str) -> Union[List[Product], str]:
    """Get the list of all products in the specified category with full details."""
    return get_products_by_category(category)


@mcp.tool(name="items_by_category")
def get_items_by_category_tool(category: str) -> Union[List[EnrichedInventoryItem], str]:
    """Get the list of all inventory items in the specified category with full details."""
    return get_items_by_category(category)


@mcp.tool(name="list_suppliers")
def list_suppliers_tool() -> List[Supplier]:
    """Get the list of all valid suppliers with names and full descriptions."""
    return list_suppliers()


@mcp.tool(name="products_by_supplier")
def get_products_by_supplier_tool(supplier_name: str) -> Union[List[Product], str]:
    """Get the list of all products for a specific supplier with full details."""
    return get_products_by_supplier(supplier_name)


@mcp.tool(name="items_by_supplier")
def get_items_by_supplier_tool(supplier_name: str) -> Union[List[EnrichedInventoryItem], str]:
    """Get the list of all inventory items for a specific supplier with full details."""
    return get_items_by_supplier(supplier_name)


@mcp.tool(name="list_products")
def list_products_tool() -> List[Product]:
    """Get the list of all valid products with full details."""
    return list_products()


@mcp.tool(name="items_by_name")
def get_items_by_name_tool(product_name: str) -> Union[List[EnrichedInventoryItem], str]:
    """Find inventory items by exact product name.
    Supports Many-to-One relationship: returns all inventory items for a product
    (e.g., same product tracked at different locations).
    Parameter: product_name (string) - Exact product name (case-sensitive).
    Note: Names with spaces should be URL-encoded (e.g., %20 for spaces).
    Use list_products tool to get valid product names.
    Returns: List of inventory items if name matches exactly, or error message if not found.
    """
    return get_items_by_name(product_name)


@mcp.tool(name="search_inventory")
def search_inventory_tool(query: str) -> Union[List[EnrichedInventoryItem], str]:
    """Search inventory by keyword in product name, description, or SKU. Not case-sensitive.
    Note: Queries with spaces should be URL-encoded (e.g., %20 for spaces).
    Parameter: query (string) - Keyword to search for in inventory.
    Returns: List of matching items, sorted by name.
    """
    return search_inventory(query)


@mcp.tool(name="low_stock_items")
def get_low_stock_items_tool() -> Union[List[EnrichedInventoryItem], str]:
    """Get low stock inventory items."""
    return get_low_stock_items()


# Tools returning other types from media_handler for demonstration purposes
# Currently OpenAI function calling only supports text-based outputs and the
# chat client example will just display the media content from the tool call
# and send a text message acknowledging the media received.


@mcp.tool(name="get_image")
def get_image_tool(image_path: str) -> CallToolResult:
    """Get image data and MIME type from a file."""
    image_data, mime_type = get_image(image_path)
    return CallToolResult(isError=False, content=[ImageContent(type="image", data=image_data, mimeType=mime_type)])


@mcp.tool(name="get_audio")
def get_audio_tool(audio_path: str) -> CallToolResult:
    """Get audio data and MIME type from a file."""
    audio_data, mime_type = get_audio(audio_path)
    return CallToolResult(isError=False, content=[AudioContent(type="audio", data=audio_data, mimeType=mime_type)])


if __name__ == "__main__":
    print("Starting MCP Tool Server...")
    mcp.run()
