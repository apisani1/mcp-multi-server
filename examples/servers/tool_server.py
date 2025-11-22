"""Example showing structured input and output with tools."""

import logging
from decimal import Decimal
from typing import (  # Optional,; TypedDict,
    Dict,
    List,
    Optional,
    Union,
)
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from mcp.types import (
    AudioContent,
    CallToolResult,
    ImageContent,
)


try:
    from ..support.inventory_db import (
        CategoryStatistics,
        DatabaseSchema,
        EnrichedInventoryItem,
        InventoryItem,
        InventoryOverview,
        ItemStatus,
        Product,
        Supplier,
        SupplierProduct,
        db,
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
    from examples.support.inventory_db import (
        CategoryStatistics,
        DatabaseSchema,
        EnrichedInventoryItem,
        InventoryItem,
        InventoryOverview,
        ItemStatus,
        Product,
        Supplier,
        SupplierProduct,
        db,
    )
    from examples.support.media_handler import (
        get_audio,
        get_image,
    )

# Suppress MCP library INFO logs
logging.getLogger("mcp").setLevel(logging.WARNING)

# Create server
mcp = FastMCP("Inventory Tool Server")

# ==============================================================================
# CREATE Tools - Data Insertion Operations
# ==============================================================================


@mcp.tool(name="add_category")
def add_category_tool(name: str, description: str = "") -> Dict[str, str]:
    """Add a new product category to the inventory database.

    Categories are used to organize products into logical groups (e.g., 'electronics', 'clothing').
    Category names are case-insensitive and stored in lowercase.

    Parameters:
        name (str): Category name (required, case-insensitive)
        description (str): Category description (optional, defaults to empty string)

    Returns:
        Dict with 'name' and 'description' keys confirming the added category

    Raises:
        ValueError if category already exists

    Example:
        add_category("electronics", "Electronic devices and accessories")
    """
    return db.add_category(name, description if description else None)


@mcp.tool(name="add_supplier")
def add_supplier_tool(
    supplier_id: str,
    name: str,
    contact_email: Optional[str] = None,
    contact_phone: Optional[str] = None,
    address: Optional[str] = None,
) -> Supplier:
    """Add a new supplier to the inventory database.

    Suppliers provide products to the inventory. Each supplier must have a unique ID.

    Parameters:
        supplier_id (str): Unique supplier identifier (required, max 50 chars)
        name (str): Supplier name (required, 1-100 chars)
        contact_email (str): Contact email address (optional, max 100 chars)``
        contact_phone (str): Contact phone number (optional, max 20 chars)
        address (str): Supplier physical address (optional, max 200 chars)

    Returns:
        Supplier object with all details including auto-generated timestamps

    Raises:
        ValueError if supplier_id already exists

    Example:
        add_supplier("SUP001", "Acme Corp", "contact@acme.com", "+1-555-0100", "123 Main St")
    """
    supplier = Supplier(
        id=supplier_id,
        name=name,
        contact_email=contact_email,
        contact_phone=contact_phone,
        address=address,
    )
    return db.add_supplier(supplier)


@mcp.tool(name="add_product")
def add_product_tool(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    name: str,
    category: str,
    description: Optional[str] = None,
    sku: Optional[str] = None,
    barcode: Optional[str] = None,
    weight: float = 0.0,
    dimensions: Optional[str] = None,
) -> Product:
    """Add a new product to the inventory database.

    Products are items that can be stocked in inventory. Each product must belong to a valid category
    and have a unique name (case-insensitive) and SKU if provided.

    Parameters:
        name (str): Product name (required, unique, 1-100 chars)
        category (str): Product category (required, must exist in database)
        description (str): Product description (optional, max 500 chars)
        sku (str): Stock Keeping Unit code (optional, unique if provided, max 50 chars)
        barcode (str): Product barcode (optional, max 50 chars)
        weight (float): Weight in kilograms (optional, must be > 0 if provided)
        dimensions (str): Dimensions as LxWxH string (optional, max 50 chars)

    Returns:
        Product object with auto-generated UUID and timestamps

    Raises:
        ValueError if category doesn't exist, product name exists, or SKU exists

    Example:
        add_product("Laptop Pro 15", "electronics", "15-inch professional laptop", "LAP-001", weight=2.5)

    Note:
        Use list_categories tool to see valid category names before adding products.
    """

    product = Product(
        name=name,
        category=category,
        description=description,
        sku=sku,
        barcode=barcode,
        weight=Decimal(str(weight)) if weight > 0 else None,
        dimensions=dimensions,
    )
    return db.add_product(product)


@mcp.tool(name="add_supplier_product")
def add_supplier_product_tool(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    product_id: str,
    supplier_id: str,
    supplier_part_number: Optional[str] = None,
    cost: float = -1.0,
    lead_time_days: int = -1,
    minimum_order_quantity: int = 0,
    is_primary_supplier: bool = False,
) -> SupplierProduct:
    """Add a supplier-product relationship to link a supplier with a product.

    This creates the many-to-many relationship between suppliers and products, allowing
    multiple suppliers to provide the same product with different pricing and terms.

    Parameters:
        product_id (str): Product UUID (required, must exist)
        supplier_id (str): Supplier ID (required, must exist)
        supplier_part_number (str): Supplier's part number for this product (optional, max 50 chars)
        cost (float): Supplier's cost for this product (optional, >= 0)
        lead_time_days (int): Lead time in days for delivery (optional, >= 0)
        minimum_order_quantity (int): Minimum order quantity (optional, >= 1)
        is_primary_supplier (bool): Whether this is the primary supplier (optional, defaults to False)

    Returns:
        SupplierProduct object with auto-generated UUID and timestamps

    Raises:
        ValueError if product_id or supplier_id doesn't exist

    Example:
        add_supplier_product("550e8400-e29b-41d4-a716-446655440000", "SUP001",
                           supplier_part_number="ACME-LAP-001", cost=899.99,
                           lead_time_days=7, is_primary_supplier=True)

    Note:
        - Use list_products to get valid product IDs
        - Use list_suppliers to get valid supplier IDs
        - Product UUIDs are returned when adding products via add_product tool
    """

    supplier_product = SupplierProduct(
        product_id=UUID(product_id),
        supplier_id=supplier_id,
        supplier_part_number=supplier_part_number,
        cost=Decimal(str(cost)) if cost >= 0 else None,
        lead_time_days=lead_time_days if lead_time_days >= 0 else None,
        minimum_order_quantity=minimum_order_quantity if minimum_order_quantity >= 1 else None,
        is_primary_supplier=is_primary_supplier,
    )
    return db.add_supplier_product(supplier_product)


@mcp.tool(name="add_inventory_item")
def add_inventory_item_tool(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    product_id: str,
    price: float,
    location_id: Optional[str] = None,
    status: str = "active",
    quantity_on_hand: int = 0,
    quantity_reserved: int = 0,
    quantity_allocated: int = 0,
    reorder_point: int = 10,
    max_stock: int = 1000,
) -> InventoryItem:
    """Add a new inventory item for stock tracking at a specific location.

    Inventory items track the actual stock quantities and pricing for products at specific locations.
    Multiple inventory items can exist for the same product (e.g., different warehouse locations).

    Parameters:
        product_id (str): Product UUID (required, must exist)
        price (float): Current selling price (required, must be > 0)
        location_id (str): Storage location identifier (optional, max 50 chars)
        status (str): Inventory status (optional, one of: 'active', 'inactive', 'out_of_stock',
                     'discontinued', defaults to 'active')
        quantity_on_hand (int): Current stock quantity (optional, >= 0, defaults to 0)
        quantity_reserved (int): Reserved quantity (optional, >= 0, defaults to 0)
        quantity_allocated (int): Allocated quantity (optional, >= 0, defaults to 0)
        reorder_point (int): Reorder threshold (optional, >= 0, defaults to 10)
        max_stock (int): Maximum stock level (optional, > 0, defaults to 1000)

    Returns:
        InventoryItem object with auto-generated UUID and timestamps

    Raises:
        ValueError if product_id doesn't exist or price <= 0

    Example:
        add_inventory_item("550e8400-e29b-41d4-a716-446655440000", 1299.99,
                          location_id="WH-A-R1-S3", quantity_on_hand=25,
                          reorder_point=5, max_stock=100)

    Note:
        - Use list_products to get valid product IDs
        - Product UUIDs are returned when adding products via add_product tool
        - Valid status values: 'active', 'inactive', 'out_of_stock', 'discontinued'
        - This supports Many-to-One: multiple items can track the same product at different locations
    """

    inventory_item = InventoryItem(
        product_id=UUID(product_id),
        price=Decimal(str(price)),
        location_id=location_id,
        status=ItemStatus(status),
        quantity_on_hand=quantity_on_hand,
        quantity_reserved=quantity_reserved,
        quantity_allocated=quantity_allocated,
        reorder_point=reorder_point,
        max_stock=max_stock,
        last_restocked_at=None,
        last_counted_at=None,
    )
    return db.add_inventory_item(inventory_item)


# ==============================================================================
# READ Tools - Query and Retrieval Operations
# ==============================================================================


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
