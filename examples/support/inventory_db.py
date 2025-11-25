"""Inventory database module for managing products, suppliers, and inventory items."""

# pylint: disable=too-many-lines

import pickle
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)
from uuid import (
    UUID,
    uuid4,
)

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class ItemStatus(str, Enum):
    """Inventory item status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


class Supplier(BaseModel):
    """Supplier entity."""

    id: str = Field(..., max_length=50, description="Supplier identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Supplier name")
    contact_email: Optional[str] = Field(None, max_length=100, description="Contact email")
    contact_phone: Optional[str] = Field(None, max_length=20, description="Contact phone")
    address: Optional[str] = Field(None, max_length=200, description="Supplier address")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class Product(BaseModel):
    """Product master data entity."""

    id: UUID = Field(default_factory=uuid4, description="Unique product identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Product name")
    description: Optional[str] = Field(None, max_length=500, description="Product description")
    category: str = Field(..., description="Product category")
    sku: Optional[str] = Field(None, max_length=50, description="Stock Keeping Unit")
    barcode: Optional[str] = Field(None, max_length=50, description="Product barcode")
    weight: Optional[Decimal] = Field(None, gt=0, description="Weight in kg")
    dimensions: Optional[str] = Field(None, max_length=50, description="Dimensions (LxWxH)")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

    @field_validator("updated_at")
    @classmethod
    def set_updated_at(cls, _: datetime) -> datetime:
        """Always update the updated_at timestamp."""
        return datetime.now()


class SupplierProduct(BaseModel):
    """Product-Supplier relationship entity."""

    id: UUID = Field(default_factory=uuid4, description="Unique relationship identifier")
    product_id: UUID = Field(..., description="Product identifier")
    supplier_id: str = Field(..., description="Supplier identifier")
    supplier_part_number: Optional[str] = Field(None, max_length=50, description="Supplier part number")
    cost: Optional[Decimal] = Field(None, ge=0, description="Supplier cost")
    lead_time_days: Optional[int] = Field(None, ge=0, description="Lead time in days")
    minimum_order_quantity: Optional[int] = Field(None, ge=1, description="Minimum order quantity")
    is_primary_supplier: bool = Field(default=False, description="Is primary supplier for this product")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class InventoryItem(BaseModel):
    """Normalized inventory item - focuses only on inventory tracking."""

    id: UUID = Field(default_factory=uuid4, description="Unique inventory item identifier")
    product_id: UUID = Field(..., description="Reference to product")
    location_id: Optional[str] = Field(None, max_length=50, description="Storage location identifier")
    status: ItemStatus = Field(default=ItemStatus.ACTIVE, description="Inventory status")

    # Pricing (current selling price)
    price: Decimal = Field(..., gt=0, description="Current selling price")

    # Inventory tracking
    quantity_on_hand: int = Field(default=0, ge=0, description="Current stock quantity")
    quantity_reserved: int = Field(default=0, ge=0, description="Reserved quantity")
    quantity_allocated: int = Field(default=0, ge=0, description="Allocated quantity")
    reorder_point: int = Field(default=10, ge=0, description="Reorder threshold")
    max_stock: int = Field(default=1000, gt=0, description="Maximum stock level")

    # Inventory timestamps
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    last_restocked_at: Optional[datetime] = Field(None, description="Last restock timestamp")
    last_counted_at: Optional[datetime] = Field(None, description="Last physical count timestamp")

    # Computed properties
    @property
    def available_quantity(self) -> int:
        """Calculate available quantity (on_hand - reserved - allocated)."""
        return max(0, self.quantity_on_hand - self.quantity_reserved - self.quantity_allocated)

    @property
    def needs_reorder(self) -> bool:
        """Check if item needs to be reordered."""
        return self.available_quantity <= self.reorder_point

    @field_validator("updated_at")
    @classmethod
    def set_updated_at(cls, _: datetime) -> datetime:
        """Always update the updated_at timestamp."""
        return datetime.now()


class EnrichedInventoryItem(BaseModel):
    """Inventory item enriched with product and supplier data for API responses."""

    # Inventory data
    id: UUID
    status: ItemStatus
    price: Decimal
    quantity_on_hand: int
    quantity_reserved: int
    quantity_allocated: int
    available_quantity: int
    reorder_point: int
    max_stock: int
    needs_reorder: bool
    location_id: Optional[str]
    last_restocked_at: Optional[datetime]

    # Product data
    product_id: UUID
    name: str
    description: Optional[str]
    category: str
    sku: Optional[str]
    barcode: Optional[str]
    weight: Optional[Decimal]
    dimensions: Optional[str]

    # Supplier data (from primary supplier)
    supplier_id: Optional[str]
    supplier_name: Optional[str]
    supplier_part_number: Optional[str]
    cost: Optional[Decimal]
    profit_margin: Optional[Decimal]

    # Timestamps
    created_at: datetime
    updated_at: datetime


# Summary and statistics models


class InventoryOverview(BaseModel):
    """Inventory overview summary."""

    total_items: int
    total_value: Decimal
    low_stock_count: int
    category_stats: Dict[str, int]
    category_percentages: Dict[str, float]


class CategoryStatistics(BaseModel):
    """Comprehensive inventory statistics."""

    total_items: int
    total_value: Decimal
    low_stock_count: int
    product_stats: Dict[str, int]
    product_percentages: Dict[str, float]


class DatabaseSchema(BaseModel):
    """Complete database schema definition."""

    entities: Dict[str, Dict[str, str]]
    relationships: List[Dict[str, str]]
    indexes: Dict[str, List[str]]
    normalization_level: str
    description: str


class InventoryDatabase:  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    """Normalized in-memory inventory database with CRUD operations.

    This database maintains referential integrity through automatic index management.
    All CREATE, UPDATE, and DELETE operations maintain index consistency:

    - CREATE operations add entries to all relevant indexes
    - UPDATE operations update indexes when indexed fields change
    - DELETE operations remove all index entries and cascade to dependent entities

    Index Integrity Guarantee:
        All indexes are kept synchronized with entity storage. No orphaned references
        exist after any operation. DELETE operations use cascade deletion to maintain
        referential integrity across related entities.
    """

    def __init__(self, database_file: Optional[str] = "sample_db.pkl") -> None:
        """Initialize inventory database with optional file persistence.

        Args:
            database_file: Path to pickle file for persistence. If file exists, database
                          will be loaded from it. If None, no persistence is used.
                          Defaults to "sample_db.pkl".
        """
        self._database_file = database_file

        # Try to load from file if it exists
        if database_file is not None and Path(database_file).exists():
            self._load_from_file(database_file)
        else:
            # Initialize empty database
            # Core entities
            self._categories: Dict[str, Dict[str, str]] = {}  # category_name -> {name, description}
            self._suppliers: Dict[str, Supplier] = {}  # supplier_id -> Supplier
            self._products: Dict[UUID, Product] = {}  # product_id -> Product
            self._supplier_products: Dict[UUID, SupplierProduct] = {}  # supplier_product_id -> SupplierProduct
            self._inventory_items: Dict[UUID, InventoryItem] = {}  # inventory_id -> InventoryItem

            # Indexes for fast lookups
            self._product_name_index: Dict[str, UUID] = {}  # product_name -> product_id
            self._product_sku_index: Dict[str, UUID] = {}  # sku -> product_id
            self._category_index: Dict[str, List[UUID]] = {}  # category_name -> product_ids
            self._supplier_product_index: Dict[UUID, List[UUID]] = {}  # product_id -> supplier_product ids
            self._inventory_product_index: Dict[UUID, UUID] = {}  # inventory_id -> product_id

    def _load_from_file(self, filepath: str) -> None:
        """Load database state from pickle file.

        Args:
            filepath: Path to the pickle file to load from

        Raises:
            Exception: If loading fails (propagates pickle exceptions)
        """
        # Custom unpickler to handle module name changes
        class RenameUnpickler(pickle.Unpickler):
            def find_class(self, module: str, name: str) -> Any:
                # Handle old module name 'inventory_db' -> 'examples.support.inventory_db'
                if module == "inventory_db":
                    module = "examples.support.inventory_db"
                return super().find_class(module, name)

        with open(filepath, "rb") as f:
            state = RenameUnpickler(f).load()

        # Restore all attributes from saved state
        self._categories = state["categories"]
        self._suppliers = state["suppliers"]
        self._products = state["products"]
        self._supplier_products = state["supplier_products"]
        self._inventory_items = state["inventory_items"]
        self._product_name_index = state["product_name_index"]
        self._product_sku_index = state["product_sku_index"]
        self._category_index = state["category_index"]
        self._supplier_product_index = state["supplier_product_index"]
        self._inventory_product_index = state["inventory_product_index"]

    def _save_to_file(self, filepath: str) -> None:
        """Save database state to pickle file.

        Args:
            filepath: Path to the pickle file to save to

        Raises:
            Exception: If saving fails (propagates pickle exceptions)
        """
        state = {
            "categories": self._categories,
            "suppliers": self._suppliers,
            "products": self._products,
            "supplier_products": self._supplier_products,
            "inventory_items": self._inventory_items,
            "product_name_index": self._product_name_index,
            "product_sku_index": self._product_sku_index,
            "category_index": self._category_index,
            "supplier_product_index": self._supplier_product_index,
            "inventory_product_index": self._inventory_product_index,
        }

        with open(filepath, "wb") as f:
            pickle.dump(state, f)

    def __del__(self) -> None:
        """Save database to file on cleanup."""
        if hasattr(self, "_database_file") and self._database_file is not None:
            try:
                self._save_to_file(self._database_file)
            except Exception:
                # Fail silently in destructor to avoid issues during cleanup
                pass

    # ==============================================================================
    # CREATE Methods - Data Insertion Operations
    # ==============================================================================

    def add_category(self, name: str, description: Optional[str] = None) -> Dict[str, str]:
        """Add a new product category.

        Args:
            name: Category name (case-insensitive, will be stored lowercase)
            description: Optional category description

        Returns:
            Dictionary with category information

        Raises:
            ValueError: If category already exists
        """
        name_lower = name.lower()

        # Check for duplicate categories (case-insensitive)
        if name_lower in self._categories:
            raise ValueError(f"Category '{name}' already exists")

        category_info = {
            "name": name_lower,
            "description": description or "",
        }

        self._categories[name_lower] = category_info
        self._category_index[name_lower] = []

        return category_info

    def add_supplier(self, supplier_obj: Supplier) -> Supplier:
        """Add a new supplier."""
        if supplier_obj.id in self._suppliers:
            raise ValueError(f"Supplier with ID '{supplier_obj.id}' already exists")

        self._suppliers[supplier_obj.id] = supplier_obj
        return supplier_obj

    def add_product(self, product_obj: Product) -> Product:
        """Add a new product."""
        # Validate category exists
        category_lower = product_obj.category.lower()
        if category_lower not in self._categories:
            raise ValueError(
                f"Category '{product_obj.category}' does not exist. " f"Please create it first using add_category()."
            )

        # Check for duplicate names
        if product_obj.name.lower() in {name.lower() for name in self._product_name_index}:
            raise ValueError(f"Product with name '{product_obj.name}' already exists")

        # Check for duplicate SKUs
        if product_obj.sku and product_obj.sku in self._product_sku_index:
            raise ValueError(f"Product with SKU '{product_obj.sku}' already exists")

        # Add to main storage and indexes
        self._products[product_obj.id] = product_obj
        self._product_name_index[product_obj.name] = product_obj.id
        if product_obj.sku:
            self._product_sku_index[product_obj.sku] = product_obj.id

        # Initialize category index if needed and add product
        if category_lower not in self._category_index:
            self._category_index[category_lower] = []
        self._category_index[category_lower].append(product_obj.id)

        self._supplier_product_index[product_obj.id] = []

        return product_obj

    def add_supplier_product(self, supplier_product_obj: SupplierProduct) -> SupplierProduct:
        """Add a supplier-product relationship."""
        if supplier_product_obj.product_id not in self._products:
            raise ValueError(f"Product with ID '{supplier_product_obj.product_id}' does not exist")

        if supplier_product_obj.supplier_id not in self._suppliers:
            raise ValueError(f"Supplier with ID '{supplier_product_obj.supplier_id}' does not exist")

        self._supplier_products[supplier_product_obj.id] = supplier_product_obj
        self._supplier_product_index[supplier_product_obj.product_id].append(supplier_product_obj.id)

        return supplier_product_obj

    def add_inventory_item(self, inventory_item_obj: InventoryItem) -> InventoryItem:
        """Add a new inventory item."""
        if inventory_item_obj.product_id not in self._products:
            raise ValueError(f"Product with ID '{inventory_item_obj.product_id}' does not exist")

        self._inventory_items[inventory_item_obj.id] = inventory_item_obj
        self._inventory_product_index[inventory_item_obj.id] = inventory_item_obj.product_id

        return inventory_item_obj

    # ==============================================================================
    # READ Methods - Query and Retrieval Operations
    # ==============================================================================

    def get_category_by_name(self, category_name: str) -> Optional[Dict[str, str]]:
        """Get category by name (case-insensitive).
        Args:
            category_name: Category name to search for
        Returns:
            Dictionary with category information if found, else None
        """
        return self._categories.get(category_name.lower())

    def list_categories(self) -> List[Dict[str, str]]:
        """List all categories with names and descriptions."""
        return sorted(self._categories.values(), key=lambda x: x["name"])

    def get_products_by_category(self, category: str) -> List[Product]:
        """Get products by product category.
        Args:
            category: Category name (case-insensitive)
        Returns:
            List of Product objects in the specified category
        """
        category_lower = category.lower()
        if category_lower not in self._categories:
            return []
        return sorted(
            [self._products[product_id] for product_id in self._category_index.get(category_lower, [])],
            key=lambda x: x.name,
        )

    def get_category_stats(self) -> Dict[str, int]:
        """Get item count by category."""
        stats: Dict[str, int] = {}
        for inventory_id in self._inventory_items:
            product_obj = self._products[self._inventory_product_index[inventory_id]]
            category_name = product_obj.category.lower()
            stats[category_name] = stats.get(category_name, 0) + 1
        return stats

    def get_supplier_by_id(self, supplier_id: str) -> Optional[Supplier]:
        """Get supplier by ID.
        Args:
            supplier_id: Supplier ID to search for
        Returns:
            Supplier object if found, else None
        """
        return self._suppliers.get(supplier_id)

    def get_supplier_by_name(self, supplier_name: str) -> Optional[Supplier]:
        """Get supplier by name (case-insensitive).
        Args:
            supplier_name: Supplier name to search for
        Returns:
            Supplier object if found, else None
        """
        supplier_name_lower = supplier_name.lower()
        for supplier_obj in self._suppliers.values():
            if supplier_name_lower in supplier_obj.name.lower():
                return supplier_obj
        return None

    def list_suppliers(self) -> List[Supplier]:
        """List all suppliers."""
        return sorted(self._suppliers.values(), key=lambda x: x.name)

    def get_products_by_supplier_name(self, supplier_name: str) -> List[Product]:
        """Get products by supplier name.
        Args:
            supplier_name: Supplier name to search for
        Returns:
            List of Product objects supplied by the specified supplier
        """
        supplier_obj = self.get_supplier_by_name(supplier_name)
        if not supplier_obj:
            return []
        items = []
        for product_id, supplier_product_obj_ids in self._supplier_product_index.items():
            for supplier_product_obj_id in supplier_product_obj_ids:
                supplier_product_obj = self._supplier_products[supplier_product_obj_id]
                if supplier_product_obj.supplier_id == supplier_obj.id:
                    items.append(self._products[product_id])
                    break
        return sorted(items, key=lambda x: x.name)

    def get_supplier_products_by_supplier_id(self, supplier_id: str) -> List[SupplierProduct]:
        """Get all supplier-product relationships for a specific supplier.
        Args:
            supplier_id: Supplier ID to search for
        Returns:
            List of SupplierProduct objects for the specified supplier (empty if none found)
        """
        return [
            supplier_product
            for supplier_product in self._supplier_products.values()
            if supplier_product.supplier_id == supplier_id
        ]

    def get_supplier_products_by_product_id(self, product_id: UUID) -> List[SupplierProduct]:
        """Get all supplier-product relationships for a specific product.
        Args:
            product_id: Product UUID to search for
        Returns:
            List of SupplierProduct objects for the specified product (empty if none found)
        """
        return [
            self._supplier_products[supplier_product_id]
            for supplier_product_id in self._supplier_product_index.get(product_id, [])
        ]

    def list_products(self) -> List[Product]:
        """List all products in the inventory."""
        return sorted(self._products.values(), key=lambda x: x.name)

    def get_enriched_inventory_item(self, inventory_id: UUID) -> Optional[EnrichedInventoryItem]:
        """Get enriched inventory item with product and supplier data.
        Args:
            inventory_id: Inventory item ID
        Returns:
            EnrichedInventoryItem object if found, else None
        """
        inventory_item_obj = self._inventory_items.get(inventory_id)
        if not inventory_item_obj:
            return None

        product_obj = self._products.get(inventory_item_obj.product_id)
        if not product_obj:
            return None

        # Get primary supplier information
        supplier_id = None
        supplier_name = None
        supplier_part_number = None
        cost = None

        supplier_product_ids = self._supplier_product_index.get(product_obj.id, [])
        for supplier_product_id in supplier_product_ids:
            supplier_product_obj = self._supplier_products.get(supplier_product_id)
            if supplier_product_obj and supplier_product_obj.is_primary_supplier:
                supplier_id = supplier_product_obj.supplier_id
                supplier_part_number = supplier_product_obj.supplier_part_number
                cost = supplier_product_obj.cost
                supplier_obj = self._suppliers.get(supplier_id)
                supplier_name = supplier_obj.name if supplier_obj else None
                break

        # Calculate profit margin
        profit_margin = None
        if cost and cost > 0:
            profit_margin = (1 - (cost / inventory_item_obj.price)) * 100

        return EnrichedInventoryItem(
            id=inventory_item_obj.id,
            status=inventory_item_obj.status,
            price=inventory_item_obj.price,
            quantity_on_hand=inventory_item_obj.quantity_on_hand,
            quantity_reserved=inventory_item_obj.quantity_reserved,
            quantity_allocated=inventory_item_obj.quantity_allocated,
            available_quantity=inventory_item_obj.available_quantity,
            reorder_point=inventory_item_obj.reorder_point,
            max_stock=inventory_item_obj.max_stock,
            needs_reorder=inventory_item_obj.needs_reorder,
            location_id=inventory_item_obj.location_id,
            last_restocked_at=inventory_item_obj.last_restocked_at,
            product_id=product_obj.id,
            name=product_obj.name,
            description=product_obj.description,
            category=product_obj.category,
            sku=product_obj.sku,
            barcode=product_obj.barcode,
            weight=product_obj.weight,
            dimensions=product_obj.dimensions,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            supplier_part_number=supplier_part_number,
            cost=cost,
            profit_margin=profit_margin,
            created_at=inventory_item_obj.created_at,
            updated_at=inventory_item_obj.updated_at,
        )

    def get_enriched_items_by_product_id(self, product_id: UUID) -> List[EnrichedInventoryItem]:
        """Get enriched inventory items by product ID.

        Supports Many-to-One relationship: multiple inventory items can reference
        the same product (e.g., same product at different locations).

        Args:
            product_id: Product ID to search for
        Returns:
            List of EnrichedInventoryItem objects (empty list if none found)
        """
        items = []
        # Find all inventory items for this product
        for inventory_id, inv_product_id in self._inventory_product_index.items():
            if inv_product_id == product_id:
                item = self.get_enriched_inventory_item(inventory_id)
                if item:
                    items.append(item)

        return items

    def get_enriched_items_by_name(self, name: str) -> List[EnrichedInventoryItem]:
        """Get enriched inventory items by product name.

        Supports Many-to-One relationship: multiple inventory items can reference
        the same product (e.g., same product at different locations).

        Args:
            name: Product name to search for
        Returns:
            List of EnrichedInventoryItem objects (empty list if none found)
        """
        product_id = self._product_name_index.get(name)
        if not product_id:
            return []

        return self.get_enriched_items_by_product_id(product_id)

    def get_enriched_items_by_sku(self, sku: str) -> List[EnrichedInventoryItem]:
        """Get enriched inventory items by product SKU.

        Supports Many-to-One relationship: multiple inventory items can reference
        the same product (e.g., same product at different locations).

        Args:
            sku: Product SKU to search for
        Returns:
            List of EnrichedInventoryItem objects (empty list if none found)
        """
        product_id = self._product_sku_index.get(sku)
        if not product_id:
            return []

        return self.get_enriched_items_by_product_id(product_id)

    def get_enriched_items_by_category(self, category: str) -> List[EnrichedInventoryItem]:
        """Get enriched inventory items by product category.
        Args:
            category: Category name to search for
        Returns:
            List of EnrichedInventoryItem objects in the specified category
        """
        return self.list_enriched_items(category=category)

    def get_enriched_items_by_supplier_name(self, supplier_name: str) -> List[EnrichedInventoryItem]:
        """Get enriched inventoryitems by supplier name.
        Args:
            supplier_name: Supplier name to search for
        Returns:
            List of EnrichedInventoryItem objects supplied by the specified supplier
        """
        return self.list_enriched_items(supplier_name=supplier_name)

    def get_low_stock_items(self, category: Optional[str] = None) -> List[EnrichedInventoryItem]:
        """Get enriched items that need to be reordered."""
        return self.list_enriched_items(needs_reorder=True, category=category)

    def list_enriched_items(
        self,
        category: Optional[str] = None,
        status: Optional[ItemStatus] = None,
        needs_reorder: Optional[bool] = None,
        supplier_name: Optional[str] = None,
    ) -> List[EnrichedInventoryItem]:
        """List enriched inventory items with optional filters by category, status, reorder status, and supplier name.
        Warning: May contain large data.
        Args:
            category: Optional product category to filter by
            status: Optional inventory item status to filter by
            needs_reorder: Optional flag to filter items that need reorder
            supplier_name: Optional supplier name to filter by
        Returns:
            List of EnrichedInventoryItem objects filtered by the specified criteria and sorted by product name
        """
        items = []

        for inventory_id, inventory_item_obj in self._inventory_items.items():
            # Pre-filter on raw inventory data before expensive enrichment
            if status and inventory_item_obj.status != status:
                continue
            if needs_reorder is not None and inventory_item_obj.needs_reorder != needs_reorder:
                continue

            # Only enrich items that passed pre-filters
            enriched_item = self.get_enriched_inventory_item(inventory_id)
            if not enriched_item:
                continue

            # Filter on enriched data (required for product category or supplier lookup)
            if category and enriched_item.category != category:
                continue
            if supplier_name and (
                not enriched_item.supplier_name or supplier_name.lower() not in enriched_item.supplier_name.lower()
            ):
                continue

            items.append(enriched_item)

        return sorted(items, key=lambda x: x.name)

    def search_enriched_items(self, query: str) -> List[EnrichedInventoryItem]:
        """Search enriched items by product name, description, or SKU.
        Args:
            query: Search query string to match against product name, description, or SKU
        Returns:
            List of EnrichedInventoryItem objects matching the search query and sorted by product name
        """
        query_lower = query.lower()
        results = []

        for inventory_id in self._inventory_items:
            enriched_item = self.get_enriched_inventory_item(inventory_id)
            if not enriched_item:
                continue

            # Check if query matches name, description, or SKU
            name_match = query_lower in enriched_item.name.lower()
            desc_match = enriched_item.description and query_lower in enriched_item.description.lower()
            sku_match = enriched_item.sku and query_lower in enriched_item.sku.lower()

            if name_match or desc_match or sku_match:
                results.append(enriched_item)

        return sorted(results, key=lambda x: x.name)

    def get_product_stats(self, category: str) -> Dict[str, int]:
        """Get item count by product within a specific category."""
        category_lower = category.lower()
        stats: Dict[str, int] = {}
        for inventory_id in self._inventory_items:
            product_obj = self._products[self._inventory_product_index[inventory_id]]
            if category_lower in product_obj.category.lower():
                product_name = product_obj.name
                stats[product_name] = stats.get(product_name, 0) + 1
        return stats

    def get_inventory_value(self, category: Optional[str] = None) -> Decimal:
        """Calculate total inventory value."""
        all_items: Union[List[EnrichedInventoryItem], List[InventoryItem]]
        if category:
            all_items = self.list_enriched_items(category=category)
        else:
            all_items = list(self._inventory_items.values())
        total = sum(item.price * item.quantity_on_hand for item in all_items)
        return Decimal(str(total))

    # ==============================================================================
    # UPDATE Methods - Data Modification Operations
    # ==============================================================================

    def update_category(self, name: str, description: Optional[str] = None) -> Dict[str, str]:
        """Update an existing product category's description.

        The category name cannot be changed as it serves as the primary key.
        Only the description field can be updated.

        Args:
            name: Category name to update (case-insensitive)
            description: New category description (if None, description is cleared)

        Returns:
            Dictionary with updated category information

        Raises:
            ValueError: If category does not exist

        Example:
            db.update_category("electronics", "Updated description for electronics")
        """
        name_lower = name.lower()
        if name_lower not in self._categories:
            raise ValueError(f"Category '{name}' does not exist")

        self._categories[name_lower]["description"] = description or ""
        return self._categories[name_lower]

    def update_supplier(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        supplier_id: str,
        name: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Supplier:
        """Update an existing supplier's information.

        Only provided fields will be updated. Fields not provided will retain their current values.
        The supplier_id cannot be changed. The updated_at timestamp is automatically updated.

        Args:
            supplier_id: Supplier ID to update (required)
            name: New supplier name (optional)
            contact_email: New contact email address (optional)
            contact_phone: New contact phone number (optional)
            address: New supplier address (optional)

        Returns:
            Updated Supplier object with auto-updated timestamp

        Raises:
            ValueError: If supplier does not exist

        Example:
            db.update_supplier("SUP001", name="Acme Corporation", contact_email="new@acme.com")
        """
        if supplier_id not in self._suppliers:
            raise ValueError(f"Supplier with ID '{supplier_id}' does not exist")
        existing_supplier = self._suppliers[supplier_id]

        # Build update dictionary with only provided fields
        updates: Dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if contact_email is not None:
            updates["contact_email"] = contact_email
        if contact_phone is not None:
            updates["contact_phone"] = contact_phone
        if address is not None:
            updates["address"] = address

        # Create updated supplier using Pydantic's model_copy
        # This automatically updates the updated_at field
        updated_supplier = existing_supplier.model_copy(update=updates)

        self._suppliers[supplier_id] = updated_supplier
        return updated_supplier

    def update_product(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-branches
        self,
        product_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        sku: Optional[str] = None,
        barcode: Optional[str] = None,
        weight: Optional[Decimal] = None,
        dimensions: Optional[str] = None,
    ) -> Product:
        """Update an existing product's information.

        Only provided fields will be updated. Fields not provided will retain their current values.
        The product_id cannot be changed. The updated_at timestamp is automatically updated via
        Pydantic field validator.

        This method handles complex index updates when name, SKU, or category changes.

        Args:
            product_id: Product UUID to update (required)
            name: New product name (optional, must be unique case-insensitive)
            description: New product description (optional)
            category: New product category (optional, must exist)
            sku: New SKU code (optional, must be unique if provided)
            barcode: New barcode (optional)
            weight: New weight in kilograms (optional)
            dimensions: New dimensions string (optional)

        Returns:
            Updated Product object with auto-updated timestamp

        Raises:
            ValueError if product does not exist, category doesn't exist, name exists, or SKU exists

        Example:
            db.update_product(
                product_id,
                name="Updated Product Name",
                category="electronics",
                price=Decimal("99.99")
            )

        Notes:
            - Name changes update the product name index
            - SKU changes update the product SKU index
            - Category changes update the category index
            - Use list_categories() to see valid category names
        """
        if product_id not in self._products:
            raise ValueError(f"Product with ID '{product_id}' does not exist")
        existing_product = self._products[product_id]

        # Validate category if being changed
        if category is not None:
            category_lower = category.lower()
            if category_lower not in self._categories:
                raise ValueError(
                    f"Category '{category}' does not exist. " f"Please create it first using add_category()."
                )

        # Validate name uniqueness if being changed
        if name is not None and name != existing_product.name:
            # pylint: disable=consider-using-dict-items
            if name.lower() in {
                n.lower() for n in self._product_name_index if self._product_name_index[n] != product_id
            }:
                raise ValueError(f"Product with name '{name}' already exists")

        # Validate SKU uniqueness if being changed
        if sku is not None and sku != existing_product.sku:
            if sku in self._product_sku_index and self._product_sku_index[sku] != product_id:
                raise ValueError(f"Product with SKU '{sku}' already exists")

        # Build update dictionary with only provided fields
        updates: Dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if category is not None:
            updates["category"] = category
        if sku is not None:
            updates["sku"] = sku
        if barcode is not None:
            updates["barcode"] = barcode
        if weight is not None:
            updates["weight"] = weight
        if dimensions is not None:
            updates["dimensions"] = dimensions

        # Create updated product using Pydantic's model_copy
        # This automatically updates the updated_at field via field validator
        updated_product = existing_product.model_copy(update=updates)

        # Update indexes if name changed
        if name is not None and name != existing_product.name:
            if existing_product.name in self._product_name_index:
                del self._product_name_index[existing_product.name]
            self._product_name_index[name] = product_id

        # Update indexes if SKU changed
        if sku is not None and sku != existing_product.sku:
            if existing_product.sku and existing_product.sku in self._product_sku_index:
                del self._product_sku_index[existing_product.sku]
            if sku:
                self._product_sku_index[sku] = product_id

        # Update category index if category changed
        if category is not None and category.lower() != existing_product.category.lower():
            # Remove from old category index
            old_category_lower = existing_product.category.lower()
            if old_category_lower in self._category_index:
                if product_id in self._category_index[old_category_lower]:
                    self._category_index[old_category_lower].remove(product_id)

            # Add to new category index
            new_category_lower = category.lower()
            if new_category_lower not in self._category_index:
                self._category_index[new_category_lower] = []
            self._category_index[new_category_lower].append(product_id)

        self._products[product_id] = updated_product
        return updated_product

    def update_supplier_product(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        supplier_product_id: UUID,
        supplier_part_number: Optional[str] = None,
        cost: Optional[Decimal] = None,
        lead_time_days: Optional[int] = None,
        minimum_order_quantity: Optional[int] = None,
        is_primary_supplier: Optional[bool] = None,
    ) -> SupplierProduct:
        """Update an existing supplier-product relationship.

        Only provided fields will be updated. Fields not provided will retain their current values.
        The relationship IDs (product_id, supplier_id) cannot be changed as they define the
        relationship. The updated_at timestamp is automatically updated.

        Args:
            supplier_product_id: SupplierProduct UUID to update (required)
            supplier_part_number: New supplier part number (optional)
            cost: New supplier cost (optional, must be >= 0)
            lead_time_days: New lead time in days (optional, must be >= 0)
            minimum_order_quantity: New minimum order quantity (optional, must be >= 1)
            is_primary_supplier: New primary supplier flag (optional)

        Returns:
            Updated SupplierProduct object with auto-updated timestamp

        Raises:
            ValueError: If supplier-product relationship does not exist
            ValueError: If field constraints are violated (via Pydantic validation)

        Example:
            db.update_supplier_product(
                supplier_product_id,
                cost=Decimal("850.00"),
                lead_time_days=5,
                is_primary_supplier=True
            )

        Notes:
            - The product_id and supplier_id are immutable (they define the relationship)
            - Pydantic validates: cost >= 0, lead_time_days >= 0, minimum_order_quantity >= 1
        """
        if supplier_product_id not in self._supplier_products:
            raise ValueError(f"Supplier-Product relationship with ID '{supplier_product_id}' does not exist")
        existing_supplier_product = self._supplier_products[supplier_product_id]

        # Build update dictionary with only provided fields
        updates: Dict[str, Any] = {}
        if supplier_part_number is not None:
            updates["supplier_part_number"] = supplier_part_number
        if cost is not None:
            updates["cost"] = cost
        if lead_time_days is not None:
            updates["lead_time_days"] = lead_time_days
        if minimum_order_quantity is not None:
            updates["minimum_order_quantity"] = minimum_order_quantity
        if is_primary_supplier is not None:
            updates["is_primary_supplier"] = is_primary_supplier

        # Create updated supplier-product using Pydantic's model_copy
        # This automatically updates the updated_at field
        updated_supplier_product = existing_supplier_product.model_copy(update=updates)

        self._supplier_products[supplier_product_id] = updated_supplier_product
        return updated_supplier_product

    def update_inventory_item(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        inventory_item_id: UUID,
        location_id: Optional[str] = None,
        status: Optional[ItemStatus] = None,
        price: Optional[Decimal] = None,
        quantity_on_hand: Optional[int] = None,
        quantity_reserved: Optional[int] = None,
        quantity_allocated: Optional[int] = None,
        reorder_point: Optional[int] = None,
        max_stock: Optional[int] = None,
        last_restocked_at: Optional[datetime] = None,
        last_counted_at: Optional[datetime] = None,
    ) -> InventoryItem:
        """Update an existing inventory item's information.

        Only provided fields will be updated. Fields not provided will retain their current values.
        The inventory_item_id and product_id cannot be changed. The updated_at timestamp is
        automatically updated via Pydantic field validator.

        Args:
            inventory_item_id: InventoryItem UUID to update (required)
            location_id: New storage location identifier (optional)
            status: New inventory status (optional)
            price: New selling price (optional, must be > 0)
            quantity_on_hand: New current stock quantity (optional, must be >= 0)
            quantity_reserved: New reserved quantity (optional, must be >= 0)
            quantity_allocated: New allocated quantity (optional, must be >= 0)
            reorder_point: New reorder threshold (optional, must be >= 0)
            max_stock: New maximum stock level (optional, must be > 0)
            last_restocked_at: New last restock timestamp (optional)
            last_counted_at: New last count timestamp (optional)

        Returns:
            Updated InventoryItem object with auto-updated timestamp

        Raises:
            ValueError: If inventory item does not exist or field constraints are violated (via Pydantic validation)

        Example:
            db.update_inventory_item(
                inventory_item_id,
                quantity_on_hand=100,
                status=ItemStatus.ACTIVE,
                last_restocked_at=datetime.now()
            )

        Notes:
            - The product_id is immutable (defines which product is tracked)
            - Pydantic validates: price > 0, quantities >= 0, max_stock > 0
            - This supports Many-to-One: multiple items can track the same product at different locations
        """
        if inventory_item_id not in self._inventory_items:
            raise ValueError(f"Inventory item with ID '{inventory_item_id}' does not exist")
        existing_inventory_item = self._inventory_items[inventory_item_id]

        # Build update dictionary with only provided fields
        updates: Dict[str, Any] = {}
        if location_id is not None:
            updates["location_id"] = location_id
        if status is not None:
            updates["status"] = status
        if price is not None:
            updates["price"] = price
        if quantity_on_hand is not None:
            updates["quantity_on_hand"] = quantity_on_hand
        if quantity_reserved is not None:
            updates["quantity_reserved"] = quantity_reserved
        if quantity_allocated is not None:
            updates["quantity_allocated"] = quantity_allocated
        if reorder_point is not None:
            updates["reorder_point"] = reorder_point
        if max_stock is not None:
            updates["max_stock"] = max_stock
        if last_restocked_at is not None:
            updates["last_restocked_at"] = last_restocked_at
        if last_counted_at is not None:
            updates["last_counted_at"] = last_counted_at

        # Create updated inventory item using Pydantic's model_copy
        # This automatically updates the updated_at field via field validator
        updated_inventory_item = existing_inventory_item.model_copy(update=updates)

        self._inventory_items[inventory_item_id] = updated_inventory_item
        return updated_inventory_item

    # ==============================================================================
    # DELETE Methods - Data Removal Operations
    # ==============================================================================
    #
    # Note: All DELETE methods maintain index integrity by removing all related
    # index entries when entities are deleted. Cascade deletions automatically
    # remove dependent entities to preserve referential integrity.

    def delete_inventory_item(self, inventory_item_id: UUID) -> bool:
        """Delete an inventory item from the database.

        Args:
            inventory_item_id: Inventory item UUID to delete

        Returns:
            True on successful deletion

        Raises:
            ValueError: If inventory item does not exist

        Example:
            db.delete_inventory_item(item_id)
        """
        if inventory_item_id not in self._inventory_items:
            raise ValueError(f"Inventory item with ID '{inventory_item_id}' does not exist")

        # Remove from main storage
        del self._inventory_items[inventory_item_id]

        # Clean up indexes
        del self._inventory_product_index[inventory_item_id]

        return True

    def delete_supplier_product(self, supplier_product_id: UUID) -> bool:
        """Delete a supplier-product relationship.

        Args:
            supplier_product_id: SupplierProduct UUID to delete

        Returns:
            True on successful deletion

        Raises:
            ValueError: If supplier-product relationship does not exist

        Example:
            db.delete_supplier_product(relationship_id)
        """
        if supplier_product_id not in self._supplier_products:
            raise ValueError(f"Supplier-Product relationship with ID '{supplier_product_id}' does not exist")

        # Get the relationship before deleting
        supplier_product = self._supplier_products[supplier_product_id]

        # Remove from main storage
        del self._supplier_products[supplier_product_id]

        # Clean up indexes - remove from product's supplier list
        if supplier_product.product_id in self._supplier_product_index:
            self._supplier_product_index[supplier_product.product_id].remove(supplier_product_id)

        return True

    def delete_product(self, product_id: UUID) -> Dict[str, int]:
        """Delete a product and all related data (CASCADE).

        This method automatically deletes:
        - All supplier-product relationships for this product
        - All inventory items tracking this product
        - The product itself

        Args:
            product_id: Product UUID to delete

        Returns:
            Dictionary with counts of deleted entities:
            {
                "deleted_supplier_products": int,
                "deleted_inventory_items": int,
                "deleted_product": 1
            }

        Raises:
            ValueError: If product does not exist

        Example:
            result = db.delete_product(product_id)
            print(f"Deleted {result['deleted_inventory_items']} inventory items")
        """
        if product_id not in self._products:
            raise ValueError(f"Product with ID '{product_id}' does not exist")

        product = self._products[product_id]
        deleted_counts = {
            "deleted_supplier_products": 0,
            "deleted_inventory_items": 0,
            "deleted_product": 0,
        }

        # CASCADE: Delete all supplier-product relationships for this product
        # Collect IDs first to avoid modifying dict during iteration
        supplier_product_ids = list(self._supplier_product_index.get(product_id, []))
        for sp_id in supplier_product_ids:
            self.delete_supplier_product(sp_id)
            deleted_counts["deleted_supplier_products"] += 1

        # CASCADE: Delete all inventory items for this product
        # Collect IDs first to avoid modifying dict during iteration
        inventory_item_ids = [
            inv_id for inv_id, prod_id in self._inventory_product_index.items() if prod_id == product_id
        ]
        for inv_id in inventory_item_ids:
            self.delete_inventory_item(inv_id)
            deleted_counts["deleted_inventory_items"] += 1

        # Remove from main storage
        del self._products[product_id]

        # Clean up indexes
        if product.name in self._product_name_index:
            del self._product_name_index[product.name]

        if product.sku and product.sku in self._product_sku_index:
            del self._product_sku_index[product.sku]

        category_lower = product.category.lower()
        if category_lower in self._category_index and product_id in self._category_index[category_lower]:
            self._category_index[category_lower].remove(product_id)

        if product_id in self._supplier_product_index:
            del self._supplier_product_index[product_id]

        deleted_counts["deleted_product"] = 1
        return deleted_counts

    def delete_supplier(self, supplier_id: str) -> Dict[str, int]:
        """Delete a supplier and all related relationships (CASCADE).

        This method automatically deletes:
        - All supplier-product relationships for this supplier
        - The supplier itself

        Args:
            supplier_id: Supplier ID to delete

        Returns:
            Dictionary with counts of deleted entities:
            {
                "deleted_supplier_products": int,
                "deleted_supplier": 1
            }

        Raises:
            ValueError: If supplier does not exist

        Example:
            result = db.delete_supplier("SUP-001")
            print(f"Deleted {result['deleted_supplier_products']} relationships")
        """
        if supplier_id not in self._suppliers:
            raise ValueError(f"Supplier with ID '{supplier_id}' does not exist")

        deleted_counts = {"deleted_supplier_products": 0, "deleted_supplier": 0}

        # CASCADE: Delete all supplier-product relationships for this supplier
        # Collect IDs first to avoid modifying dict during iteration
        supplier_product_ids = [
            sp_id for sp_id, sp in self._supplier_products.items() if sp.supplier_id == supplier_id
        ]
        for sp_id in supplier_product_ids:
            self.delete_supplier_product(sp_id)
            deleted_counts["deleted_supplier_products"] += 1

        # Remove from main storage
        del self._suppliers[supplier_id]

        deleted_counts["deleted_supplier"] = 1
        return deleted_counts

    def delete_category(self, name: str) -> Dict[str, int]:
        """Delete a category and all related data (CASCADE).

        This method automatically deletes:
        - All products in this category
          - Which cascades to all supplier-product relationships
          - Which cascades to all inventory items
        - The category itself

        Args:
            name: Category name to delete (case-insensitive)

        Returns:
            Dictionary with counts of deleted entities:
            {
                "deleted_products": int,
                "deleted_supplier_products": int,
                "deleted_inventory_items": int,
                "deleted_category": 1
            }

        Raises:
            ValueError: If category does not exist

        Example:
            result = db.delete_category("electronics")
            print(f"Deleted {result['deleted_products']} products")
        """
        name_lower = name.lower()
        if name_lower not in self._categories:
            raise ValueError(f"Category '{name}' does not exist")

        deleted_counts = {
            "deleted_products": 0,
            "deleted_supplier_products": 0,
            "deleted_inventory_items": 0,
            "deleted_category": 0,
        }

        # CASCADE: Delete all products in this category (which cascades further)
        # Collect IDs first to avoid modifying dict during iteration
        product_ids = list(self._category_index.get(name_lower, []))
        for product_id in product_ids:
            result = self.delete_product(product_id)
            deleted_counts["deleted_products"] += 1
            deleted_counts["deleted_supplier_products"] += result["deleted_supplier_products"]
            deleted_counts["deleted_inventory_items"] += result["deleted_inventory_items"]

        # Remove from main storage
        del self._categories[name_lower]

        # Clean up indexes
        if name_lower in self._category_index:
            del self._category_index[name_lower]

        deleted_counts["deleted_category"] = 1
        return deleted_counts


# Module-level database instance
# Will load from 'sample_db.pkl' if it exists, otherwise starts empty
db = InventoryDatabase()
