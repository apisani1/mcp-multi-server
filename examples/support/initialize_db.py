#!/usr/bin/env python3
"""Initialize the inventory database with sample data and save to pickle file.

This script creates a fully populated sample inventory database with categories,
suppliers, products, supplier-product relationships, and inventory items. The
initialized database is then saved to a pickle file for persistence.

Usage:
    python initialize_db.py [output_file]

Arguments:
    output_file: Path to save the database (default: sample_db.pkl)
"""

import sys
from decimal import Decimal

from inventory_db import (
    InventoryDatabase,
    InventoryItem,
    Product,
    Supplier,
    SupplierProduct,
)


def initialize_sample_database(output_file: str = "sample_db.pkl") -> InventoryDatabase:
    """Initialize a sample database with test data.

    Args:
        output_file: Path to save the initialized database

    Returns:
        InventoryDatabase instance with sample data
    """
    # Create database without loading from file
    db = InventoryDatabase(database_file=None)

    print("Initializing sample inventory database...")
    print()

    # Create categories
    print("Creating categories...")
    categories_data = [
        {"name": "beverages", "description": "Beverages and drinks"},
        {"name": "food", "description": "Food items"},
        {"name": "electronics", "description": "Electronic devices and accessories"},
        {"name": "books", "description": "Books and publications"},
        {"name": "clothing", "description": "Clothing and apparel"},
        {"name": "home_garden", "description": "Home and garden supplies"},
        {"name": "office_supplies", "description": "Office supplies and stationery"},
        {"name": "other", "description": "Other miscellaneous items"},
    ]

    for category_data in categories_data:
        db.add_category(category_data["name"], category_data["description"])
        print(f"  Added category: {category_data['name']}")

    print()

    # Create suppliers
    print("Creating suppliers...")
    suppliers_data = [
        {"id": "SUP-001", "name": "Colombian Coffee Co.", "contact_email": "orders@colombiancoffee.com"},
        {"id": "SUP-002", "name": "Tea Imports Ltd.", "contact_email": "sales@teaimports.com"},
        {"id": "SUP-003", "name": "Local Bakery", "contact_phone": "555-0123"},
        {"id": "SUP-004", "name": "TechSupply Inc.", "contact_email": "wholesale@techsupply.com"},
        {"id": "SUP-005", "name": "Academic Publishers", "contact_email": "orders@academicpub.com"},
    ]

    suppliers = [Supplier.model_validate(data) for data in suppliers_data]

    for supplier in suppliers:
        db.add_supplier(supplier)
        print(f"  Added supplier: {supplier.id} - {supplier.name}")

    print()

    # Create products
    print("Creating products...")
    products_data = [
        {
            "name": "Premium Coffee Beans",
            "description": "High-quality Arabica coffee beans from Colombia",
            "category": "beverages",
            "sku": "COF-001",
            "weight": Decimal("1.0"),
        },
        {
            "name": "Earl Grey Tea",
            "description": "Classic Earl Grey black tea with bergamot",
            "category": "beverages",
            "sku": "TEA-001",
        },
        {
            "name": "Chocolate Chip Cookies",
            "description": "Fresh baked chocolate chip cookies",
            "category": "food",
            "sku": "COOK-001",
        },
        {
            "name": "Wireless Bluetooth Headphones",
            "description": "High-quality wireless headphones with noise cancellation",
            "category": "electronics",
            "sku": "ELEC-001",
            "weight": Decimal("0.3"),
        },
        {
            "name": "Python Programming Guide",
            "description": "Comprehensive guide to Python programming",
            "category": "books",
            "sku": "BOOK-001",
        },
    ]

    products = [Product.model_validate(data) for data in products_data]

    for product in products:
        db.add_product(product)
        print(f"  Added product: {product.name} (SKU: {product.sku})")

    print()

    # Create supplier-product relationships
    print("Creating supplier-product relationships...")
    supplier_products_data = [
        {
            "product_id": products[0].id,
            "supplier_id": "SUP-001",
            "cost": Decimal("6.50"),
            "is_primary_supplier": True,
            "lead_time_days": 14,
            "minimum_order_quantity": 50,
        },
        {
            "product_id": products[1].id,
            "supplier_id": "SUP-002",
            "cost": Decimal("4.25"),
            "is_primary_supplier": True,
            "lead_time_days": 7,
            "minimum_order_quantity": 25,
        },
        {
            "product_id": products[2].id,
            "supplier_id": "SUP-003",
            "cost": Decimal("2.50"),
            "is_primary_supplier": True,
            "lead_time_days": 1,
            "minimum_order_quantity": 12,
        },
        {
            "product_id": products[3].id,
            "supplier_id": "SUP-004",
            "cost": Decimal("120.00"),
            "is_primary_supplier": True,
            "lead_time_days": 21,
            "minimum_order_quantity": 5,
        },
        {
            "product_id": products[4].id,
            "supplier_id": "SUP-005",
            "cost": Decimal("25.00"),
            "is_primary_supplier": True,
            "lead_time_days": 10,
            "minimum_order_quantity": 10,
        },
    ]

    supplier_products = [SupplierProduct.model_validate(data) for data in supplier_products_data]

    for supplier_product in supplier_products:
        db.add_supplier_product(supplier_product)
        print(f"  Added relationship: {supplier_product.supplier_id} -> Product")

    print()

    # Create inventory items
    print("Creating inventory items...")
    inventory_items_data = [
        {"product_id": products[0].id, "price": Decimal("12.99"), "quantity_on_hand": 150, "reorder_point": 20},
        {"product_id": products[1].id, "price": Decimal("8.99"), "quantity_on_hand": 75, "reorder_point": 15},
        {"product_id": products[2].id, "price": Decimal("5.99"), "quantity_on_hand": 25, "reorder_point": 30},
        {"product_id": products[3].id, "price": Decimal("199.99"), "quantity_on_hand": 12, "reorder_point": 5},
        {"product_id": products[4].id, "price": Decimal("39.99"), "quantity_on_hand": 8, "reorder_point": 3},
    ]

    inventory_items = [InventoryItem.model_validate(data) for data in inventory_items_data]

    for idx, inventory_item in enumerate(inventory_items):
        db.add_inventory_item(inventory_item)
        product_name = products[idx].name
        print(f"  Added inventory item: {product_name} (qty: {inventory_item.quantity_on_hand})")

    print()

    # Save to file
    print(f"Saving database to {output_file}...")
    db._save_to_file(output_file)
    print()

    # Print summary
    print("Database initialization complete!")
    print()
    print("Summary:")
    print(f"  Categories: {len(db._categories)}")
    print(f"  Suppliers: {len(db._suppliers)}")
    print(f"  Products: {len(db._products)}")
    print(f"  Supplier-Product relationships: {len(db._supplier_products)}")
    print(f"  Inventory items: {len(db._inventory_items)}")
    print()
    print(f"Database saved to: {output_file}")

    return db


def main() -> None:
    """Main entry point for the script."""
    output_file = sys.argv[1] if len(sys.argv) > 1 else "sample_db.pkl"
    initialize_sample_database(output_file)


if __name__ == "__main__":
    main()
