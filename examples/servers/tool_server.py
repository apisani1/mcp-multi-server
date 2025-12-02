import base64
import mimetypes
from datetime import datetime
from decimal import Decimal
from typing import (
    Dict,
    List,
    Optional,
    Union,
)
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from mcp.types import (
    AudioContent,
    BlobResourceContents,
    CallToolResult,
    EmbeddedResource,
    ImageContent,
    ResourceLink,
)
from mcp_multi_server.utils import configure_logging


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

# Create server
mcp = FastMCP("Inventory Tool Server")


@mcp._mcp_server.set_logging_level()
async def set_logging_level(level: str) -> None:
    configure_logging(name="mcp", level=level)


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
        contact_email (str): Contact email address (optional, max 100 chars)
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
        ValueError if product_id doesn't exist or constraints are violated

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
    """Get a comprehensive overview of the entire inventory system.

    Provides high-level statistics and metrics for inventory management decisions.

    Parameters:
        None

    Returns:
        InventoryOverview object containing:
        - total_items: Total number of inventory items across all locations
        - total_value: Total monetary value of all inventory (sum of price * quantity)
        - low_stock_count: Number of items below their reorder point
        - items_by_category: Count of items in each category
        - category_percentages: Percentage distribution of items across categories

    Example:
        overview = inventory_overview()
        # Returns: {"total_items": 150, "total_value": 125000.50, "low_stock_count": 12, ...}
    """
    return get_inventory_overview()


@mcp.tool(name="database_schema")
def get_database_schema_tool() -> DatabaseSchema:
    """Get the complete database schema definition with all table structures.

    Returns the schema for all database tables including field names, types,
    constraints, and relationships. Useful for understanding the data model.

    Parameters:
        None

    Returns:
        DatabaseSchema object containing schema definitions for all tables:
        - categories: Product category table structure
        - suppliers: Supplier table structure
        - products: Product table structure
        - supplier_products: Supplier-product relationship table structure
        - inventory_items: Inventory item table structure

    Example:
        schema = database_schema()
        # Returns complete schema with all table definitions and relationships
    """
    return get_database_schema()


@mcp.tool(name="list_categories")
def list_categories_tool() -> List[Dict[str, str]]:
    """Get the list of all valid product categories with names and descriptions.

    Returns all categories that can be assigned to products. Use this before
    adding or updating products to ensure you use valid category names.

    Parameters:
        None

    Returns:
        List of dictionaries, each containing:
        - name: Category name (lowercase string)
        - description: Category description (string, may be empty)

    Example:
        categories = list_categories()
        # Returns: [{"name": "electronics", "description": "Electronic devices"}, ...]

    Note:
        Category names are case-insensitive and stored in lowercase.
    """
    return list_categories()


@mcp.tool(name="category_statistics")
def get_category_statistics_tool(category: str) -> CategoryStatistics:
    """Get detailed statistics for a specific product category.

    Provides analytics on inventory distribution and value within a category.

    Parameters:
        category (str): Category name to analyze (case-insensitive)

    Returns:
        CategoryStatistics object containing:
        - category: The category name
        - total_items: Total inventory items in this category
        - total_value: Total monetary value of category inventory
        - low_stock_count: Number of items below reorder point in this category
        - items_by_product: Count of inventory items per product in category
        - product_percentages: Percentage distribution across products in category

    Example:
        stats = category_statistics("electronics")
        # Returns category-specific metrics for inventory planning

    Note:
        Use list_categories tool to see valid category names.
    """
    return get_category_statistics(category)


@mcp.tool(name="products_by_category")
def get_products_by_category_tool(category: str) -> Union[List[Product], str]:
    """Get all products in a specific category with complete product information.

    Returns detailed product records for all products assigned to the specified category.

    Parameters:
        category (str): Category name to filter by (case-insensitive)

    Returns:
        List of Product objects, each containing:
        - id: Product UUID
        - name: Product name
        - category: Product category
        - description: Product description
        - sku: Stock Keeping Unit code
        - barcode: Product barcode
        - weight: Weight in kilograms
        - dimensions: Physical dimensions
        - created_at: Creation timestamp
        - updated_at: Last update timestamp

        Returns error message string if category doesn't exist.

    Example:
        products = products_by_category("electronics")
        # Returns list of all electronic products with full details

    Note:
        Use list_categories tool to see valid category names.
    """
    return get_products_by_category(category)


@mcp.tool(name="items_by_category")
def get_items_by_category_tool(category: str) -> Union[List[EnrichedInventoryItem], str]:
    """Get all inventory items in a specific category with enriched product details.

    Returns inventory records with joined product and supplier information for items in the category.

    Parameters:
        category (str): Category name to filter by (case-insensitive)

    Returns:
        List of EnrichedInventoryItem objects, each containing:
        - Inventory fields: id, price, location_id, status, quantities, last_restocked_at
        - Product fields: product_id, name, category, description, sku, barcode, weight, dimensions
        - Supplier fields: supplier_id, supplier_name, supplier_part_number, cost, profit_margin

        Returns error message string if category doesn't exist.

    Example:
        items = items_by_category("electronics")
        # Returns inventory items with product details for all electronics

    Note:
        - Use list_categories tool to see valid category names
        - This returns actual inventory stock records, not just product definitions
        - Supports Many-to-One: same product may appear multiple times at different locations
    """
    return get_items_by_category(category)


@mcp.tool(name="list_suppliers")
def list_suppliers_tool() -> List[Supplier]:
    """Get the list of all suppliers with complete contact and business information.

    Returns all registered suppliers in the system. Use this to find supplier IDs
    for creating supplier-product relationships or querying supplier data.

    Parameters:
        None

    Returns:
        List of Supplier objects, each containing:
        - id: Unique supplier identifier
        - name: Supplier business name
        - contact_email: Contact email address
        - contact_phone: Contact phone number
        - address: Physical business address
        - created_at: Registration timestamp
        - updated_at: Last modification timestamp

    Example:
        suppliers = list_suppliers()
        # Returns: [Supplier(id="SUP001", name="Acme Corp", ...), ...]

    Note:
        Supplier IDs are required for add_supplier_product and supplier query tools.
    """
    return list_suppliers()


@mcp.tool(name="products_by_supplier")
def get_products_by_supplier_tool(supplier_name: str) -> Union[List[Product], str]:
    """Get all products supplied by a specific supplier with complete product details.

    Returns product records for all products that have a supplier-product relationship
    with the specified supplier.

    Parameters:
        supplier_name (str): Supplier name to filter by (exact match, case-sensitive)

    Returns:
        List of Product objects for products supplied by this supplier, each containing:
        - id: Product UUID
        - name: Product name
        - category: Product category
        - description: Product description
        - sku: Stock Keeping Unit code
        - barcode: Product barcode
        - weight: Weight in kilograms
        - dimensions: Physical dimensions
        - created_at: Creation timestamp
        - updated_at: Last update timestamp

        Returns error message string if supplier not found.

    Example:
        products = products_by_supplier("Acme Corp")
        # Returns all products supplied by Acme Corp

    Note:
        - Use list_suppliers tool to see valid supplier names
        - Supplier name must match exactly (case-sensitive)
        - Products may have multiple suppliers; this shows one supplier's products
    """
    return get_products_by_supplier(supplier_name)


@mcp.tool(name="items_by_supplier")
def get_items_by_supplier_tool(supplier_name: str) -> Union[List[EnrichedInventoryItem], str]:
    """Get all inventory items for products supplied by a specific supplier.

    Returns inventory stock records with enriched product details for items whose
    products are supplied by the specified supplier.

    Parameters:
        supplier_name (str): Supplier name to filter by (exact match, case-sensitive)

    Returns:
        List of EnrichedInventoryItem objects, each containing:
        - Inventory fields: id, price, location_id, status, quantities, last_restocked_at
        - Product fields: product_id, name, category, description, sku, barcode, weight, dimensions
        - Supplier fields: supplier_id, supplier_name, supplier_part_number, cost, profit_margin

        Returns error message string if supplier not found.

    Example:
        items = items_by_supplier("Acme Corp")
        # Returns inventory stock for all products supplied by Acme Corp

    Note:
        - Use list_suppliers tool to see valid supplier names
        - Supplier name must match exactly (case-sensitive)
        - Shows actual inventory stock, not just product definitions
        - Supports Many-to-One: same product may appear at multiple locations
    """
    return get_items_by_supplier(supplier_name)


@mcp.tool(name="supplier_products_by_supplier")
def get_supplier_products_by_supplier_tool(supplier_id: str) -> List[SupplierProduct]:
    """Get all supplier-product relationships for a specific supplier ID.

    Returns detailed information about all products supplied by this supplier,
    including costs, lead times, and primary supplier status.

    Parameter: supplier_id (string) - Supplier ID (e.g., "SUP-001")
    Use list_suppliers tool to get valid supplier IDs.

    Returns: List of supplier-product relationship objects
    """
    return db.get_supplier_products_by_supplier_id(supplier_id)


@mcp.tool(name="supplier_products_by_product")
def get_supplier_products_by_product_tool(product_id: str) -> List[SupplierProduct]:
    """Get all supplier-product relationships for a specific product ID.

    Returns detailed information about all suppliers for this product,
    including costs, lead times, and which is the primary supplier.

    Parameter: product_id (string) - Product UUID
    Use list_products tool to get valid product IDs.

    Returns: List of supplier-product relationship objects
    """
    return db.get_supplier_products_by_product_id(UUID(product_id))


@mcp.tool(name="list_products")
def list_products_tool() -> List[Product]:
    """Get the complete list of all products in the system with full details.

    Returns all product records across all categories. Use this to discover product
    IDs for inventory operations or to browse the product catalog.

    Parameters:
        None

    Returns:
        List of Product objects, each containing:
        - id: Product UUID (use this for add_inventory_item, add_supplier_product)
        - name: Product name (unique, case-insensitive)
        - category: Product category
        - description: Product description
        - sku: Stock Keeping Unit code (unique if provided)
        - barcode: Product barcode
        - weight: Weight in kilograms
        - dimensions: Physical dimensions (LxWxH format)
        - created_at: Product creation timestamp
        - updated_at: Last modification timestamp

    Example:
        products = list_products()
        # Returns complete product catalog with all details

    Note:
        Product UUIDs (id field) are required for creating inventory items and supplier relationships.
    """
    return list_products()


@mcp.tool(name="items_by_name")
def get_items_by_name_tool(product_name: str) -> Union[List[EnrichedInventoryItem], str]:
    """Find all inventory items for a product by its exact name.

    Returns inventory stock records with enriched product details for items matching
    the exact product name. Supports Many-to-One: multiple inventory items can track
    the same product at different locations.

    Parameters:
        product_name (str): Exact product name (case-sensitive, use URL encoding for spaces)

    Returns:
        List of EnrichedInventoryItem objects (may contain multiple items for same product), each containing:
        - Inventory fields: id, price, location_id, status, quantities, last_restocked_at
        - Product fields: product_id, name, category, description, sku, barcode, weight, dimensions
        - Supplier fields: supplier_id, supplier_name, supplier_part_number, cost, profit_margin

        Returns error message string if no product with this exact name exists.

    Example:
        items = items_by_name("Laptop Pro 15")
        # Returns all inventory items for "Laptop Pro 15" across all locations

    Note:
        - Product name must match exactly (case-sensitive)
        - Use list_products tool to see valid product names
        - URL-encode names with spaces (e.g., "Laptop%20Pro%2015")
        - Multiple items may be returned for the same product at different locations
    """
    return get_items_by_name(product_name)


@mcp.tool(name="search_inventory")
def search_inventory_tool(query: str) -> Union[List[EnrichedInventoryItem], str]:
    """Search inventory items by keyword across product names, descriptions, and SKUs.

    Performs case-insensitive partial matching across multiple product fields to find
    relevant inventory items. More flexible than items_by_name for discovery.

    Parameters:
        query (str): Search keyword (case-insensitive, use URL encoding for spaces)

    Returns:
        List of EnrichedInventoryItem objects matching the query, sorted by product name:
        - Inventory fields: id, price, location_id, status, quantities, last_restocked_at
        - Product fields: product_id, name, category, description, sku, barcode, weight, dimensions
        - Supplier fields: supplier_id, supplier_name, supplier_part_number, cost, profit_margin

        Returns error message string if no matches found.

    Example:
        items = search_inventory("laptop")
        # Returns all inventory items where "laptop" appears in name, description, or SKU
        # Matches: "Laptop Pro 15", "Gaming Laptop", product with description "portable laptop"

    Note:
        - Case-insensitive partial matching
        - Searches across: product name, description, and SKU fields
        - URL-encode queries with spaces (e.g., "gaming%20laptop")
        - Results sorted alphabetically by product name
        - More flexible than items_by_name which requires exact match
    """
    return search_inventory(query)


@mcp.tool(name="low_stock_items")
def get_low_stock_items_tool() -> Union[List[EnrichedInventoryItem], str]:
    """Get all inventory items that are below their reorder point threshold.

    Identifies items requiring restocking based on comparing quantity_on_hand
    against the configured reorder_point for each item. Critical for inventory
    management and procurement planning.

    Parameters:
        None

    Returns:
        List of EnrichedInventoryItem objects where quantity_on_hand <= reorder_point:
        - Inventory fields: id, price, location_id, status, quantities, last_restocked_at
        - Product fields: product_id, name, category, description, sku, barcode, weight, dimensions
        - Supplier fields: supplier_id, supplier_name, supplier_part_number, cost, profit_margin

        Returns a confirmation string if no low stock items found.

    Example:
        low_stock = low_stock_items()
        # Returns items needing restocking, e.g., items with 5 units on hand and reorder_point of 10

    Note:
        - Items are flagged as low stock when: quantity_on_hand <= reorder_point
        - Use this regularly to prevent stockouts
        - Set appropriate reorder_point values when adding/updating inventory items
        - Results help prioritize purchasing and restocking activities
    """
    return get_low_stock_items()


# ==============================================================================
# UPDATE Tools - Data Modification Operations
# ==============================================================================


@mcp.tool(name="update_category")
def update_category_tool(name: str, description: str = "") -> Dict[str, str]:
    """Update an existing product category's description.

    The category name cannot be changed as it serves as the primary key.
    Only the description field can be updated. Names are case-insensitive.

    Parameters:
        name (str): Category name to update (required, case-insensitive)
        description (str): New category description (optional, defaults to empty string)

    Returns:
        Dict with 'name' and 'description' keys confirming the updated category

    Raises:
        ValueError if category does not exist

    Example:
        update_category("electronics", "Electronic devices and computer accessories")

    Notes:
        - Use list_categories tool to see existing categories before updating
        - Empty description will clear the category description
        - Category names are stored in lowercase
    """
    return db.update_category(name, description if description else None)


@mcp.tool(name="update_supplier")
def update_supplier_tool(
    supplier_id: str,
    name: Optional[str] = None,
    contact_email: Optional[str] = None,
    contact_phone: Optional[str] = None,
    address: Optional[str] = None,
) -> Supplier:
    """Update an existing supplier's information.

    Only provided fields will be updated. Fields not provided will retain their current values.
    The supplier_id cannot be changed. The updated_at timestamp is automatically updated.

    Parameters:
        supplier_id (str): Supplier ID to update (required, max 50 chars)
        name (str): New supplier name (optional, 1-100 chars)
        contact_email (str): New contact email (optional, max 100 chars)
        contact_phone (str): New contact phone (optional, max 20 chars)
        address (str): New supplier address (optional, max 200 chars)

    Returns:
        Supplier object with updated fields and auto-updated timestamp

    Raises:
        ValueError if supplier_id does not exist

    Example:
        update_supplier("SUP001", name="Acme Corporation Ltd", contact_email="new@acme.com")

    Notes:
        - Use list_suppliers tool to see existing suppliers and their IDs
        - Only provided parameters are updated (partial updates supported)
        - Supplier ID cannot be changed (it's the primary key)
    """
    return db.update_supplier(
        supplier_id=supplier_id,
        name=name,
        contact_email=contact_email,
        contact_phone=contact_phone,
        address=address,
    )


@mcp.tool(name="update_product")
def update_product_tool(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    product_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    sku: Optional[str] = None,
    barcode: Optional[str] = None,
    weight: float = -1.0,
    dimensions: Optional[str] = None,
) -> Product:
    """Update an existing product's information.

    Only provided fields will be updated. Fields not provided will retain their current values.
    The product_id cannot be changed. The updated_at timestamp is automatically updated.
    This method handles complex index updates when name, SKU, or category changes.

    Parameters:
        product_id (str): Product UUID to update (required)
        name (str): New product name (optional, must be unique case-insensitive, 1-100 chars)
        description (str): New product description (optional, max 500 chars)
        category (str): New product category (optional, must exist in database)
        sku (str): New SKU code (optional, must be unique if provided, max 50 chars)
        barcode (str): New barcode (optional, max 50 chars)
        weight (float): New weight in kilograms (optional, must be > 0 if provided)
        dimensions (str): New dimensions as LxWxH string (optional, max 50 chars)

    Returns:
        Product object with updated fields and auto-updated timestamp

    Raises:
        ValueError if product does not exist, category doesn't exist, name exists, or SKU exists

    Example:
        update_product("550e8400-e29b-41d4-a716-446655440000",
                      name="Laptop Pro 16", category="electronics",
                      weight=2.8, sku="LAP-002")

    Notes:
        - Use list_products tool to get valid product UUIDs and current values
        - Use list_categories tool to see valid category names
        - Only provided parameters are updated (partial updates supported)
        - Product ID cannot be changed (it's the primary key)
    """
    return db.update_product(
        product_id=UUID(product_id),
        name=name,
        description=description,
        category=category,
        sku=sku,
        barcode=barcode,
        weight=Decimal(str(weight)) if weight > 0 else None,
        dimensions=dimensions,
    )


@mcp.tool(name="update_supplier_product")
def update_supplier_product_tool(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    supplier_product_id: str,
    supplier_part_number: Optional[str] = None,
    cost: float = -1.0,
    lead_time_days: int = -1,
    minimum_order_quantity: int = 0,
    is_primary_supplier: Optional[bool] = None,
) -> SupplierProduct:
    """Update an existing supplier-product relationship.

    Only provided fields will be updated. Fields not provided will retain their current values.
    The relationship IDs (product_id, supplier_id) cannot be changed as they define the
    relationship. The updated_at timestamp is automatically updated.

    Parameters:
        supplier_product_id (str): SupplierProduct UUID to update (required)
        supplier_part_number (str): New supplier part number (optional, max 50 chars)
        cost (float): New supplier cost (optional, must be >= 0)
        lead_time_days (int): New lead time in days (optional, must be >= 0)
        minimum_order_quantity (int): New minimum order quantity (optional, must be >= 1)
        is_primary_supplier (bool): New primary supplier flag (optional)

    Returns:
        SupplierProduct object with updated fields and auto-updated timestamp

    Raises:
        ValueError if supplier-product relationship does not exist or constraints violated

    Example:
        update_supplier_product("650e8400-e29b-41d4-a716-446655440000",
                               cost=925.50, lead_time_days=5,
                               is_primary_supplier=True)

    Notes:
        - Only provided parameters are updated (partial updates supported)
        - The product_id and supplier_id are immutable (they define the relationship)
        - Use supplier_products_by_supplier or supplier_products_by_product tools
          to get valid supplier-product relationship IDs
    """
    return db.update_supplier_product(
        supplier_product_id=UUID(supplier_product_id),
        supplier_part_number=supplier_part_number,
        cost=Decimal(str(cost)) if cost >= 0 else None,
        lead_time_days=lead_time_days if lead_time_days >= 0 else None,
        minimum_order_quantity=minimum_order_quantity if minimum_order_quantity >= 1 else None,
        is_primary_supplier=is_primary_supplier,
    )


@mcp.tool(name="update_inventory_item")
def update_inventory_item_tool(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    inventory_item_id: str,
    location_id: Optional[str] = None,
    status: Optional[str] = None,
    price: float = -1.0,
    quantity_on_hand: int = -1,
    quantity_reserved: int = -1,
    quantity_allocated: int = -1,
    reorder_point: int = -1,
    max_stock: int = -1,
    last_restocked_at: Optional[str] = None,
    last_counted_at: Optional[str] = None,
) -> InventoryItem:
    """Update an existing inventory item's information.

    Only provided fields will be updated. Fields not provided will retain their current values.
    The inventory_item_id and product_id cannot be changed. The updated_at timestamp is
    automatically updated. Supports Many-to-One: multiple items can track the same product.

    Parameters:
        inventory_item_id (str): InventoryItem UUID to update (required)
        location_id (str): New storage location identifier (optional, max 50 chars)
        status (str): New inventory status (optional, one of: 'active', 'inactive',
                     'out_of_stock', 'discontinued')
        price (float): New selling price (optional, must be > 0)
        quantity_on_hand (int): New current stock quantity (optional, must be >= 0)
        quantity_reserved (int): New reserved quantity (optional, must be >= 0)
        quantity_allocated (int): New allocated quantity (optional, must be >= 0)
        reorder_point (int): New reorder threshold (optional, must be >= 0)
        max_stock (int): New maximum stock level (optional, must be > 0)
        last_restocked_at (str): New last restock timestamp in ISO format (optional,
                                e.g., "2024-01-15T10:30:00")
        last_counted_at (str): New last count timestamp in ISO format (optional,
                              e.g., "2024-01-15T14:45:00")

    Returns:
        InventoryItem object with updated fields and auto-updated timestamp

    Raises:
        ValueError if inventory item does not exist or field constraints violated

    Example:
        update_inventory_item("750e8400-e29b-41d4-a716-446655440000",
                             quantity_on_hand=150, status="active",
                             last_restocked_at="2024-01-15T10:30:00")

    Notes:
        - Use search_inventory or items_by_name tools to get valid inventory item IDs
        - Inventory item UUIDs are shown in search results (id field)
        - Only provided parameters are updated (partial updates supported)
        - The product_id is immutable (defines which product is tracked)
        - Valid status values: 'active', 'inactive', 'out_of_stock', 'discontinued'
        - Timestamps should be in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
        - This supports Many-to-One: multiple items can track same product at different locations
    """
    # Parse datetime strings if provided
    restocked_dt = datetime.fromisoformat(last_restocked_at) if last_restocked_at is not None else None
    counted_dt = datetime.fromisoformat(last_counted_at) if last_counted_at is not None else None

    return db.update_inventory_item(
        inventory_item_id=UUID(inventory_item_id),
        location_id=location_id,
        status=ItemStatus(status) if status else None,
        price=Decimal(str(price)) if price > 0 else None,
        quantity_on_hand=quantity_on_hand if quantity_on_hand >= 0 else None,
        quantity_reserved=quantity_reserved if quantity_reserved >= 0 else None,
        quantity_allocated=quantity_allocated if quantity_allocated >= 0 else None,
        reorder_point=reorder_point if reorder_point >= 0 else None,
        max_stock=max_stock if max_stock > 0 else None,
        last_restocked_at=restocked_dt,
        last_counted_at=counted_dt,
    )


# ==============================================================================
# DELETE Tools - Data Removal Operations
# ==============================================================================


@mcp.tool(name="delete_inventory_item")
def delete_inventory_item_tool(inventory_item_id: str) -> str:
    """Delete an inventory item from the database.

    WARNING: This permanently removes the inventory tracking record.

    Parameter: inventory_item_id (string) - Inventory item UUID
    Use search_inventory or items_by_name tools to get valid inventory item IDs.

    Returns: Success message

    Raises:
        ValueError if inventory item does not exist

    Example:
        delete_inventory_item("123e4567-e89b-12d3-a456-426614174000")
    """
    db.delete_inventory_item(UUID(inventory_item_id))
    return f"Successfully deleted inventory item '{inventory_item_id}'"


@mcp.tool(name="delete_supplier_product")
def delete_supplier_product_tool(supplier_product_id: str) -> str:
    """Delete a supplier-product relationship.

    Removes the link between a supplier and product. Does not delete the
    supplier or product themselves.

    Parameter: supplier_product_id (string) - SupplierProduct UUID
    Use supplier_products_by_supplier or supplier_products_by_product tools
    to get valid relationship IDs.

    Returns: Success message

    Raises:
        ValueError if supplier-product relationship does not exist

    Example:
        delete_supplier_product("123e4567-e89b-12d3-a456-426614174000")
    """
    db.delete_supplier_product(UUID(supplier_product_id))
    return f"Successfully deleted supplier-product relationship '{supplier_product_id}'"


@mcp.tool(name="delete_product")
def delete_product_tool(product_id: str) -> Dict[str, int]:
    """Delete a product and all related data (CASCADE).

    WARNING: This will also delete:
    - All supplier-product relationships for this product
    - All inventory items tracking this product

    This is a destructive operation that cannot be undone.

    Parameter: product_id (string) - Product UUID
    Use list_products tool to get valid product IDs.

    Returns:
        Dictionary with counts of deleted entities:
        {
            "deleted_supplier_products": int,
            "deleted_inventory_items": int,
            "deleted_product": 1
        }

    Raises:
        ValueError if product does not exist

    Example:
        delete_product("123e4567-e89b-12d3-a456-426614174000")
    """
    return db.delete_product(UUID(product_id))


@mcp.tool(name="delete_supplier")
def delete_supplier_tool(supplier_id: str) -> Dict[str, int]:
    """Delete a supplier and all related relationships (CASCADE).

    WARNING: This will also delete:
    - All supplier-product relationships for this supplier

    Products themselves are NOT deleted, only the supplier relationships.

    Parameter: supplier_id (string) - Supplier ID (e.g., "SUP-001")
    Use list_suppliers tool to get valid supplier IDs.

    Returns:
        Dictionary with counts of deleted entities:
        {
            "deleted_supplier_products": int,
            "deleted_supplier": 1
        }

    Raises:
        ValueError if supplier does not exist

    Example:
        delete_supplier("SUP-001")
    """
    return db.delete_supplier(supplier_id)


@mcp.tool(name="delete_category")
def delete_category_tool(name: str) -> Dict[str, int]:
    """Delete a category and all related data (CASCADE).

    WARNING: This will also delete:
    - All products in this category
    - All supplier-product relationships for those products
    - All inventory items for those products

    This is the most destructive operation and cannot be undone.

    Parameter: name (string) - Category name (case-insensitive)
    Use list_categories tool to get valid category names.

    Returns:
        Dictionary with counts of deleted entities:
        {
            "deleted_products": int,
            "deleted_supplier_products": int,
            "deleted_inventory_items": int,
            "deleted_category": 1
        }

    Raises:
        ValueError if category does not exist

    Example:
        delete_category("electronics")
    """
    return db.delete_category(name)


# Tools returning non text types for tool demonstration purposes
# Currently OpenAI function calling only supports text-based outputs and the
# chat client example will just display the media content from the tool call
# and send a text message to the LLM acknowledging the media received.


@mcp.tool(name="get_image")
def get_image_tool(image_path: str) -> CallToolResult:
    """Load an image file and return its contents as base64-encoded image content.

    Reads image files from the filesystem and returns them in MCP ImageContent format
    with automatic MIME type detection. Supports common image formats (PNG, JPEG, GIF, etc.).

    Parameters:
        image_path (str): Absolute or relative file path to the image file

    Returns:
        CallToolResult containing:
        - isError: False
        - content: List with single ImageContent object containing:
          - type: "image"
          - data: Base64-encoded image data
          - mimeType: Detected MIME type (e.g., "image/png", "image/jpeg")

    Raises:
        FileNotFoundError if image file doesn't exist
        IOError if file cannot be read

    Example:
        result = get_image("/path/to/product-photo.png")
        # Returns ImageContent with base64 data and mimeType="image/png"

    Note:
        - MIME type is auto-detected from file extension
        - Image data is base64-encoded for safe transmission
        - Used for displaying product images or visual content
    """
    image_data, mime_type = get_image(image_path)
    return CallToolResult(isError=False, content=[ImageContent(type="image", data=image_data, mimeType=mime_type)])


@mcp.tool(name="get_audio")
def get_audio_tool(audio_path: str) -> CallToolResult:
    """Load an audio file and return its contents as base64-encoded audio content.

    Reads audio files from the filesystem and returns them in MCP AudioContent format
    with automatic MIME type detection. Supports common audio formats (MP3, WAV, OGG, etc.).

    Parameters:
        audio_path (str): Absolute or relative file path to the audio file

    Returns:
        CallToolResult containing:
        - isError: False
        - content: List with single AudioContent object containing:
          - type: "audio"
          - data: Base64-encoded audio data
          - mimeType: Detected MIME type (e.g., "audio/mpeg", "audio/wav")

    Raises:
        FileNotFoundError if audio file doesn't exist
        IOError if file cannot be read

    Example:
        result = get_audio("/path/to/product-demo.mp3")
        # Returns AudioContent with base64 data and mimeType="audio/mpeg"

    Note:
        - MIME type is auto-detected from file extension
        - Audio data is base64-encoded for safe transmission
        - Used for instructions or audio content
    """
    audio_data, mime_type = get_audio(audio_path)
    return CallToolResult(isError=False, content=[AudioContent(type="audio", data=audio_data, mimeType=mime_type)])


@mcp.tool(name="get_file")
def get_file_tool(file_path: str) -> CallToolResult:
    """Load any file and return its contents as an embedded resource with base64 encoding.

    Reads any file type from the filesystem and returns it as an MCP EmbeddedResource
    with automatic MIME type detection. Use this for general file access (documents,
    data files, etc.) when specific image/audio tools don't apply.

    Parameters:
        file_path (str): Absolute or relative file path to any file

    Returns:
        CallToolResult containing:
        - isError: False
        - content: List with single EmbeddedResource object containing:
          - type: "resource"
          - resource: BlobResourceContents with:
            - uri: File URI (e.g., "file:///path/to/file.pdf")
            - blob: Base64-encoded file contents
            - mimeType: Auto-detected MIME type or "application/octet-stream" if unknown

    Raises:
        FileNotFoundError if file doesn't exist
        IOError if file cannot be read

    Example:
        result = get_file("/path/to/manual.pdf")
        # Returns EmbeddedResource with base64 blob and mimeType="application/pdf"

    Note:
        - Handles any file type (PDFs, spreadsheets, text files, binary files, etc.)
        - MIME type auto-detected from file extension
        - Falls back to "application/octet-stream" for unknown types
        - File contents are base64-encoded for safe transmission
        - For images use get_image, for audio use get_audio (they provide optimized formats)
    """
    with open(file_path, "rb") as file:
        file_data = file.read()
    encoded = base64.b64encode(file_data).decode("utf-8")
    mime_type, _ = mimetypes.guess_type(file_path)
    return CallToolResult(
        isError=False,
        content=[
            EmbeddedResource(
                type="resource",
                resource=BlobResourceContents(
                    uri=f"file://{file_path}",  # type: ignore[arg-type]
                    blob=encoded,
                    mimeType=mime_type or "application/octet-stream",
                ),
            )
        ],
    )


@mcp.tool(name="get_uri_content")
def get_uri_content_tool(content_uri: str) -> CallToolResult:
    """Create a resource link for a content URI without loading the uri contents.

    Returns a ResourceLink reference to remote or local content via URI. Unlike get_file,
    this doesn't load the file contents—it just creates a link reference. Useful for
    referencing remote URLs, large files, or streaming content.

    Parameters:
        content_uri (str): URI to the content (URL, file://, or other URI scheme)

    Returns:
        CallToolResult containing:
        - isError: False
        - content: List with single ResourceLink object containing:
          - type: "resource_link"
          - name: Extracted filename from URI (last path segment)
          - uri: The provided content URI
          - mimeType: Auto-detected from URI extension or "application/octet-stream"

    Example:
        result = get_content_uri("https://example.com/manual.pdf")
        # Returns ResourceLink(name="manual.pdf", uri="https://...", mimeType="application/pdf")

        result = get_content_uri("file:///local/video.mp4")
        # Returns ResourceLink(name="video.mp4", uri="file://...", mimeType="video/mp4")

    Note:
        - Does NOT load file contents (unlike get_file)
        - Creates a reference/link to content
        - MIME type inferred from URI extension
        - Supports any URI scheme (http://, https://, file://, etc.)
        - Useful for remote resources, streaming, or avoiding large file transfers
        - Name is extracted from the last segment of the URI path
    """
    mime_type, _ = mimetypes.guess_type(content_uri)
    return CallToolResult(
        isError=False,
        content=[
            ResourceLink(
                type="resource_link",
                name=content_uri.split("/")[-1],
                uri=content_uri,  # type: ignore[arg-type]
                mimeType=mime_type or "application/octet-stream",
            )
        ],
    )


if __name__ == "__main__":
    print("Starting MCP Tool Server...")
    mcp.run()
