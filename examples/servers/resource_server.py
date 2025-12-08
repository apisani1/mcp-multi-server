from typing import (
    Dict,
    List,
    Union,
)
from urllib.parse import unquote

from mcp.server.fastmcp import FastMCP
from mcp_multi_server.utils import configure_logging


try:
    from ..support.inventory_db import (
        CategoryStatistics,
        DatabaseSchema,
        EnrichedInventoryItem,
        InventoryOverview,
        Product,
        Supplier,
        db,
    )
except ImportError:
    from examples.support.inventory_db import (
        CategoryStatistics,
        DatabaseSchema,
        EnrichedInventoryItem,
        InventoryOverview,
        Product,
        Supplier,
        db,
    )

# Initialize FastMCP server
mcp = FastMCP("Inventory Resource Server")


@mcp._mcp_server.set_logging_level()
async def set_logging_level(level: str) -> None:
    configure_logging(name="mcp", level=level)


@mcp.resource("inventory://overview")
def get_inventory_overview() -> InventoryOverview:
    """Returns comprehensive inventory overview."""
    total_items = len(db.list_enriched_items())
    category_stats = db.get_category_stats()
    return InventoryOverview(
        total_items=total_items,
        total_value=db.get_inventory_value(),
        low_stock_count=len(db.get_low_stock_items()),
        category_stats=category_stats,
        category_percentages={
            category: (count / total_items * 100) if total_items > 0 else 0
            for category, count in category_stats.items()
        },
    )


@mcp.resource("inventory://database-schema")
def get_database_schema() -> DatabaseSchema:
    """Returns the complete database schema definition."""

    # Define all entities with their field types
    entities = {
        "Category": {
            "name": "str (Primary Key)",
            "description": "Optional[str]",
        },
        "Supplier": {
            "id": "str (Primary Key)",
            "name": "str",
            "contact_email": "Optional[str]",
            "contact_phone": "Optional[str]",
            "address": "Optional[str]",
            "created_at": "datetime",
            "updated_at": "datetime",
        },
        "Product": {
            "id": "UUID (Primary Key)",
            "name": "str",
            "description": "Optional[str]",
            "category": "str (Enum)",
            "sku": "Optional[str]",
            "barcode": "Optional[str]",
            "weight": "Optional[Decimal]",
            "dimensions": "Optional[str]",
            "created_at": "datetime",
            "updated_at": "datetime",
        },
        "SupplierProduct": {
            "id": "UUID (Primary Key)",
            "product_id": "UUID (Foreign Key → Product.id)",
            "supplier_id": "str (Foreign Key → Supplier.id)",
            "supplier_part_number": "Optional[str]",
            "cost": "Optional[Decimal]",
            "lead_time_days": "Optional[int]",
            "minimum_order_quantity": "Optional[int]",
            "is_primary_supplier": "bool",
            "created_at": "datetime",
            "updated_at": "datetime",
        },
        "InventoryItem": {
            "id": "UUID (Primary Key)",
            "product_id": "UUID (Foreign Key → Product.id)",
            "location_id": "Optional[str]",
            "status": "ItemStatus (Enum)",
            "price": "Decimal",
            "quantity_on_hand": "int",
            "quantity_reserved": "int",
            "quantity_allocated": "int",
            "reorder_point": "int",
            "max_stock": "int",
            "created_at": "datetime",
            "updated_at": "datetime",
            "last_restocked_at": "Optional[datetime]",
            "last_counted_at": "Optional[datetime]",
        },
        "EnrichedInventoryItem": {
            "description": "View model combining data from all entities",
            "note": "Used for API responses - not stored in database",
        },
    }

    # Define relationships between entities
    relationships = [
        {
            "from": "SupplierProduct",
            "to": "Supplier",
            "type": "Many-to-One",
            "foreign_key": "supplier_id → Supplier.id",
            "description": "Each supplier-product relationship belongs to one supplier",
        },
        {
            "from": "SupplierProduct",
            "to": "Product",
            "type": "Many-to-One",
            "foreign_key": "product_id → Product.id",
            "description": "Each supplier-product relationship belongs to one product",
        },
        {
            "from": "InventoryItem",
            "to": "Product",
            "type": "Many-to-One",
            "foreign_key": "product_id → Product.id",
            "description": "Each inventory item tracks stock for one product",
        },
        {
            "from": "Supplier",
            "to": "Product",
            "type": "Many-to-Many",
            "through": "SupplierProduct",
            "description": "Suppliers can supply multiple products, products can have multiple suppliers",
        },
    ]

    # Define database indexes for performance
    indexes = {
        "primary_keys": ["Supplier.id", "Product.id", "SupplierProduct.id", "InventoryItem.id"],
        "foreign_key_indexes": [
            "SupplierProduct.product_id",
            "SupplierProduct.supplier_id",
            "InventoryItem.product_id",
        ],
        "business_logic_indexes": [
            "Product.name",
            "Product.sku",
            "Product.category",
            "InventoryItem.status",
            "InventoryItem.needs_reorder (computed)",
        ],
    }

    return DatabaseSchema(
        entities=entities,
        relationships=relationships,
        indexes=indexes,
        normalization_level="Third Normal Form (3NF)",
        description=(
            "Fully normalized inventory management database schema. Eliminates all redundancy by separating "
            "concerns into distinct entities: Supplier (vendor data), Product (item master data), "
            "SupplierProduct (supplier-product relationships with pricing), and InventoryItem (stock tracking). "
            "The EnrichedInventoryItem model provides a denormalized view for API consumption, combining data "
            "from all entities."
        ),
    )


@mcp.resource("inventory://categories")
def list_categories() -> List[Dict[str, str]]:
    """Returns list of all valid product categories with names and descriptions."""
    return db.list_categories()


@mcp.resource("inventory://category/stats/{category}")
def get_category_statistics(category: str) -> CategoryStatistics:
    """Returns comprehensive category statistics."""
    total_items = len(db.list_enriched_items(category=category))
    product_stats = db.get_product_stats(category=category)

    return CategoryStatistics(
        total_items=total_items,
        total_value=db.get_inventory_value(category=category),
        low_stock_count=len(db.get_low_stock_items(category=category)),
        product_stats=product_stats,
        product_percentages={
            product: (count / total_items * 100) if total_items > 0 else 0 for product, count in product_stats.items()
        },
    )


@mcp.resource("inventory://category/products/{category}")
def get_products_by_category(category: str) -> Union[List[Product], str]:
    """Get all products in a specific category - Use category names from inventory://categories.
    Examples: inventory://category/products/beverages, inventory://category/products/electronics
    Returns: List of all products in the specified category.
    """
    try:
        category_lower = category.lower()
        products = db.get_products_by_category(category=category_lower)

        if not products:
            return f"No products found in category '{category.title()}'."

        return products
    except ValueError:
        valid_categories = db.list_categories()
        valid_category_names = [cat["name"] for cat in valid_categories]
        return f"Invalid category. Valid categories: {', '.join(valid_category_names)}"


@mcp.resource("inventory://category/items/{category}")
def get_items_by_category(category: str) -> Union[List[EnrichedInventoryItem], str]:
    """Get all inventory items in a specific category - Use category names from inventory://categories.

    Examples: inventory://category/items/beverages, inventory://category/items/electronics
    Returns: List of all items in the specified category.
    """
    try:
        category_lower = category.lower()
        items = db.get_enriched_items_by_category(category=category_lower)

        if not items:
            return f"No items found in category '{category.title()}'."

        return items

    except ValueError:
        valid_categories = db.list_categories()
        valid_category_names = [cat["name"] for cat in valid_categories]
        return f"Invalid category. Valid categories: {', '.join(valid_category_names)}"


@mcp.resource("inventory://suppliers")
def list_suppliers() -> List[Supplier]:
    """Returns list of all valid inventory suppliers with names and descriptions."""
    return db.list_suppliers()


@mcp.resource("inventory://supplier/products/{supplier_name}")
def get_products_by_supplier(supplier_name: str) -> Union[List[Product], str]:
    """Get all products for a specific supplier - Use supplier names from inventory://suppliers.

    Examples: inventory://supplier/products/Colombian%20Coffee%20Co., inventory://supplier/products/TechSupply%20Inc.
    Returns: List of all products supplied by the specified supplier.
    """
    try:
        products = db.get_products_by_supplier_name(supplier_name)

        if not products:
            return f"No products found for supplier '{supplier_name}'."

        return products
    except ValueError:
        valid_suppliers = db.list_suppliers()
        valid_supplier_names = [supplier.name for supplier in valid_suppliers]
        return f"Invalid supplier name. Valid supplier names: {', '.join(valid_supplier_names)}"


@mcp.resource("inventory://supplier/items/{supplier_name}")
def get_items_by_supplier(supplier_name: str) -> Union[List[EnrichedInventoryItem], str]:
    """Get all inventory items for a specific supplier - Use supplier names from inventory://suppliers.

    Examples: inventory://supplier/items/Colombian%20Coffee%20Co., inventory://supplier/items/TechSupply%20Inc.
    Returns: List of all inventory items supplied by the specified supplier."""
    try:
        items = db.get_enriched_items_by_supplier_name(supplier_name)

        if not items:
            return f"No items found for supplier '{supplier_name}'."

        return items

    except ValueError:
        valid_suppliers = db.list_suppliers()
        valid_supplier_names = [supplier.name for supplier in valid_suppliers]
        return f"Invalid supplier name. Valid supplier names: {', '.join(valid_supplier_names)}"


@mcp.resource("inventory://products")
def list_products() -> List[Product]:
    """Returns list of all products defined."""
    return db.list_products()


@mcp.resource("inventory://product/item/{product_name}")
def get_items_by_name(product_name: str) -> Union[List[EnrichedInventoryItem], str]:
    """Find inventory items by exact product name.

    Supports Many-to-One relationship: returns all inventory items for a product
    (e.g., same product tracked at different locations).

    Parameter: product_name (string) - Exact product name (case-sensitive).
    Note: Names with spaces should be URL-encoded (e.g., %20 for spaces).
    Examples:
    - inventory://product/item/Premium%20Coffee%20Beans
    - inventory://product/item/Earl%20Grey%20Tea
    - inventory://product/item/Chocolate%20Chip%20Cookies
    Returns: List of inventory items if name matches exactly, or error message if not found."""
    # URL decode the product name to handle spaces and special characters
    decoded_name = unquote(product_name)
    items = db.get_enriched_items_by_name(decoded_name)

    if not items:
        return f"Item '{decoded_name}' not found."

    return items


@mcp.resource("inventory://search/item/{query}")
def search_inventory(query: str) -> Union[List[EnrichedInventoryItem], str]:
    """Search inventory by keyword in product name, description, or SKU. Not case-sensitive.

    Parameter: query (string) - Search term to match against:
    - Product names (e.g., 'coffee', 'bluetooth', 'python')
    - Product descriptions (e.g., 'wireless', 'high-quality', 'fresh')
    - Product SKUs (e.g., 'COF-001', 'ELEC-001', 'BOOK-001')
    Note: Queries with spaces should be URL-encoded (e.g., %20 for spaces).

    Examples:
    - inventory://search/item/coffee (finds coffee-related items)
    - inventory://search/item/wireless (finds wireless products)
    - inventory://search/item/chip%20cookies (finds items with "chip cookies")
    Returns: List of matching items, sorted by name."""
    # URL decode the query to handle spaces and special characters
    decoded_query = unquote(query)
    items = db.search_enriched_items(decoded_query)

    if not items:
        return f"No items found matching '{decoded_query}'."

    return items


@mcp.resource("inventory://low-stock")
def get_low_stock_items() -> Union[List[EnrichedInventoryItem], str]:
    """Returns items that need to be reordered."""
    items = db.get_low_stock_items()

    if not items:
        return "✅ All items are adequately stocked!"

    return items


if __name__ == "__main__":
    print("Starting MCP Resource Server...")
    mcp.run()
