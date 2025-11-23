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
        # Beverage suppliers
        {"id": "SUP-001", "name": "Colombian Coffee Co.", "contact_email": "orders@colombiancoffee.com"},
        {"id": "SUP-002", "name": "Tea Imports Ltd.", "contact_email": "sales@teaimports.com"},
        {"id": "SUP-003", "name": "Global Beverages Inc.", "contact_email": "wholesale@globalbev.com"},
        # Food suppliers
        {"id": "SUP-004", "name": "Local Bakery", "contact_phone": "555-0123"},
        {"id": "SUP-005", "name": "Fresh Foods Distributor", "contact_email": "orders@freshfoods.com"},
        # Electronics suppliers
        {"id": "SUP-006", "name": "TechSupply Inc.", "contact_email": "wholesale@techsupply.com"},
        {"id": "SUP-007", "name": "ElectroWorld Wholesale", "contact_email": "sales@electroworld.com"},
        # Book suppliers
        {"id": "SUP-008", "name": "Academic Publishers", "contact_email": "orders@academicpub.com"},
        {"id": "SUP-009", "name": "Book Distributors LLC", "contact_email": "sales@bookdist.com"},
        # Clothing suppliers
        {"id": "SUP-010", "name": "Fashion Wholesale Co.", "contact_email": "orders@fashionwholesale.com"},
        {"id": "SUP-011", "name": "Apparel Direct", "contact_email": "sales@appareldirect.com"},
        # Home & Garden suppliers
        {"id": "SUP-012", "name": "Home Essentials Inc.", "contact_email": "orders@homeessentials.com"},
        {"id": "SUP-013", "name": "Garden Supply Pro", "contact_email": "sales@gardensupplypro.com"},
        # Office suppliers
        {"id": "SUP-014", "name": "Office Depot Wholesale", "contact_email": "wholesale@officedepot.com"},
        {"id": "SUP-015", "name": "Stationery Direct", "contact_email": "orders@stationerydirect.com"},
    ]

    suppliers = [Supplier.model_validate(data) for data in suppliers_data]

    for supplier in suppliers:
        db.add_supplier(supplier)
        print(f"  Added supplier: {supplier.id} - {supplier.name}")

    print()

    # Create products
    print("Creating products...")
    products_data = [
        # BEVERAGES (5+ products)
        {
            "name": "Premium Coffee Beans",
            "description": "High-quality Arabica coffee beans from Colombia",
            "category": "beverages",
            "sku": "BEV-001",
            "barcode": "736211209849",
            "weight": Decimal("1.0"),
        },
        {
            "name": "Earl Grey Tea",
            "description": "Classic Earl Grey black tea with bergamot",
            "category": "beverages",
            "sku": "BEV-002",
            "barcode": "736211209856",
            "weight": Decimal("0.25"),
        },
        {
            "name": "Orange Juice",
            "description": "Fresh squeezed orange juice, no preservatives",
            "category": "beverages",
            "sku": "BEV-003",
            "barcode": "736211209863",
            "weight": Decimal("2.0"),
        },
        {
            "name": "Cola Soda 12-Pack",
            "description": "Classic cola soda, 12 cans per pack",
            "category": "beverages",
            "sku": "BEV-004",
            "barcode": "736211209870",
            "weight": Decimal("5.0"),
        },
        {
            "name": "Energy Drink",
            "description": "High-caffeine energy drink with vitamins",
            "category": "beverages",
            "sku": "BEV-005",
            "barcode": "736211209887",
            "weight": Decimal("0.5"),
        },
        {
            "name": "Green Tea Organic",
            "description": "Organic green tea leaves, premium quality",
            "category": "beverages",
            "sku": "BEV-006",
            "barcode": "736211209894",
            "weight": Decimal("0.2"),
        },
        # FOOD (5+ products)
        {
            "name": "Chocolate Chip Cookies",
            "description": "Fresh baked chocolate chip cookies, 12 count",
            "category": "food",
            "sku": "FOOD-001",
            "barcode": "736211210849",
        },
        {
            "name": "Organic Pasta",
            "description": "Whole wheat organic pasta, 1 lb package",
            "category": "food",
            "sku": "FOOD-002",
            "barcode": "736211210856",
            "weight": Decimal("1.0"),
        },
        {
            "name": "Tomato Sauce",
            "description": "Italian-style tomato sauce with herbs",
            "category": "food",
            "sku": "FOOD-003",
            "barcode": "736211210863",
            "weight": Decimal("0.68"),
        },
        {
            "name": "Mixed Nuts Snack Pack",
            "description": "Roasted and salted mixed nuts, 8 oz",
            "category": "food",
            "sku": "FOOD-004",
            "barcode": "736211210870",
            "weight": Decimal("0.5"),
        },
        {
            "name": "Canned Tuna",
            "description": "Wild-caught tuna in water, 5 oz can",
            "category": "food",
            "sku": "FOOD-005",
            "barcode": "736211210887",
            "weight": Decimal("0.31"),
        },
        {
            "name": "Granola Bars Box",
            "description": "Healthy granola bars, 12-count variety pack",
            "category": "food",
            "sku": "FOOD-006",
            "barcode": "736211210894",
            "weight": Decimal("0.75"),
        },
        # ELECTRONICS (5+ products)
        {
            "name": "Wireless Bluetooth Headphones",
            "description": "High-quality wireless headphones with noise cancellation",
            "category": "electronics",
            "sku": "ELEC-001",
            "barcode": "736211220849",
            "weight": Decimal("0.3"),
        },
        {
            "name": "Mechanical Keyboard",
            "description": "RGB mechanical gaming keyboard with Cherry MX switches",
            "category": "electronics",
            "sku": "ELEC-002",
            "barcode": "736211220856",
            "weight": Decimal("1.2"),
        },
        {
            "name": "Wireless Mouse",
            "description": "Ergonomic wireless mouse with 6 buttons",
            "category": "electronics",
            "sku": "ELEC-003",
            "barcode": "736211220863",
            "weight": Decimal("0.15"),
        },
        {
            "name": "USB-C Cable 6ft",
            "description": "High-speed USB-C charging and data cable",
            "category": "electronics",
            "sku": "ELEC-004",
            "barcode": "736211220870",
            "weight": Decimal("0.08"),
        },
        {
            "name": "Portable Power Bank",
            "description": "20000mAh portable battery charger with fast charging",
            "category": "electronics",
            "sku": "ELEC-005",
            "barcode": "736211220887",
            "weight": Decimal("0.45"),
        },
        {
            "name": "LED Monitor 24-inch",
            "description": "Full HD 1080p LED monitor with IPS panel",
            "category": "electronics",
            "sku": "ELEC-006",
            "barcode": "736211220894",
            "weight": Decimal("4.5"),
        },
        # BOOKS (5+ products)
        {
            "name": "Python Programming Guide",
            "description": "Comprehensive guide to Python programming for beginners",
            "category": "books",
            "sku": "BOOK-001",
            "barcode": "978-0134692005",
        },
        {
            "name": "The Great Novel",
            "description": "Bestselling fiction novel, paperback edition",
            "category": "books",
            "sku": "BOOK-002",
            "barcode": "978-0451524935",
        },
        {
            "name": "Business Strategy Handbook",
            "description": "Modern business strategies for entrepreneurs",
            "category": "books",
            "sku": "BOOK-003",
            "barcode": "978-0062873984",
        },
        {
            "name": "Self-Help Mastery",
            "description": "Transform your life with proven techniques",
            "category": "books",
            "sku": "BOOK-004",
            "barcode": "978-1501135910",
        },
        {
            "name": "The Ultimate Cookbook",
            "description": "500+ recipes for home cooks, hardcover",
            "category": "books",
            "sku": "BOOK-005",
            "barcode": "978-0316769174",
        },
        {
            "name": "Web Development Bootcamp",
            "description": "Complete guide to modern web development",
            "category": "books",
            "sku": "BOOK-006",
            "barcode": "978-1491952023",
        },
        # CLOTHING (5+ products)
        {
            "name": "Cotton T-Shirt",
            "description": "100% cotton basic t-shirt, multiple colors available",
            "category": "clothing",
            "sku": "CLO-001",
            "barcode": "736211230849",
        },
        {
            "name": "Denim Jeans",
            "description": "Classic fit denim jeans, various sizes",
            "category": "clothing",
            "sku": "CLO-002",
            "barcode": "736211230856",
            "weight": Decimal("0.6"),
        },
        {
            "name": "Running Shoes",
            "description": "Lightweight athletic running shoes with cushioning",
            "category": "clothing",
            "sku": "CLO-003",
            "barcode": "736211230863",
            "weight": Decimal("0.8"),
        },
        {
            "name": "Winter Jacket",
            "description": "Insulated winter jacket, waterproof material",
            "category": "clothing",
            "sku": "CLO-004",
            "barcode": "736211230870",
            "weight": Decimal("1.5"),
        },
        {
            "name": "Baseball Cap",
            "description": "Adjustable cotton baseball cap with embroidered logo",
            "category": "clothing",
            "sku": "CLO-005",
            "barcode": "736211230887",
            "weight": Decimal("0.12"),
        },
        {
            "name": "Wool Socks 3-Pack",
            "description": "Warm wool blend socks, pack of 3 pairs",
            "category": "clothing",
            "sku": "CLO-006",
            "barcode": "736211230894",
            "weight": Decimal("0.25"),
        },
        # HOME & GARDEN (5+ products)
        {
            "name": "Hand Tool Set",
            "description": "20-piece hand tool set with carrying case",
            "category": "home_garden",
            "sku": "HOME-001",
            "barcode": "736211240849",
            "weight": Decimal("3.5"),
        },
        {
            "name": "Potted Plant - Succulent",
            "description": "Low-maintenance succulent in decorative pot",
            "category": "home_garden",
            "sku": "HOME-002",
            "barcode": "736211240856",
            "weight": Decimal("0.5"),
        },
        {
            "name": "Throw Pillow",
            "description": "Decorative throw pillow with removable cover",
            "category": "home_garden",
            "sku": "HOME-003",
            "barcode": "736211240863",
            "weight": Decimal("0.4"),
        },
        {
            "name": "Garden Hose 50ft",
            "description": "Heavy-duty rubber garden hose with spray nozzle",
            "category": "home_garden",
            "sku": "HOME-004",
            "barcode": "736211240870",
            "weight": Decimal("4.0"),
        },
        {
            "name": "Cleaning Spray Multi-Purpose",
            "description": "All-purpose cleaning spray, 32 oz bottle",
            "category": "home_garden",
            "sku": "HOME-005",
            "barcode": "736211240887",
            "weight": Decimal("1.0"),
        },
        {
            "name": "LED Light Bulbs 4-Pack",
            "description": "Energy-efficient LED bulbs, 60W equivalent",
            "category": "home_garden",
            "sku": "HOME-006",
            "barcode": "736211240894",
            "weight": Decimal("0.3"),
        },
        # OFFICE SUPPLIES (5+ products)
        {
            "name": "Ballpoint Pens 12-Pack",
            "description": "Black ink ballpoint pens, pack of 12",
            "category": "office_supplies",
            "sku": "OFF-001",
            "barcode": "736211250849",
            "weight": Decimal("0.15"),
        },
        {
            "name": "Printer Paper Ream",
            "description": "White copy paper, 500 sheets, 8.5x11 inches",
            "category": "office_supplies",
            "sku": "OFF-002",
            "barcode": "736211250856",
            "weight": Decimal("2.3"),
        },
        {
            "name": "File Folders Box",
            "description": "Manila file folders, letter size, box of 100",
            "category": "office_supplies",
            "sku": "OFF-003",
            "barcode": "736211250863",
            "weight": Decimal("1.8"),
        },
        {
            "name": "Desktop Stapler",
            "description": "Heavy-duty desktop stapler with staples included",
            "category": "office_supplies",
            "sku": "OFF-004",
            "barcode": "736211250870",
            "weight": Decimal("0.5"),
        },
        {
            "name": "Sticky Notes Pack",
            "description": "Colorful sticky notes, 6 pads per pack",
            "category": "office_supplies",
            "sku": "OFF-005",
            "barcode": "736211250887",
            "weight": Decimal("0.2"),
        },
        {
            "name": "Desk Organizer",
            "description": "Multi-compartment desk organizer with drawer",
            "category": "office_supplies",
            "sku": "OFF-006",
            "barcode": "736211250894",
            "weight": Decimal("0.75"),
        },
        # OTHER (5+ products)
        {
            "name": "Reusable Water Bottle",
            "description": "Stainless steel insulated water bottle, 32 oz",
            "category": "other",
            "sku": "OTH-001",
            "barcode": "736211260849",
            "weight": Decimal("0.35"),
        },
        {
            "name": "Phone Case Universal",
            "description": "Protective silicone phone case, fits most models",
            "category": "other",
            "sku": "OTH-002",
            "barcode": "736211260856",
            "weight": Decimal("0.05"),
        },
        {
            "name": "Backpack",
            "description": "Durable backpack with laptop compartment",
            "category": "other",
            "sku": "OTH-003",
            "barcode": "736211260863",
            "weight": Decimal("0.9"),
        },
        {
            "name": "Umbrella Compact",
            "description": "Compact folding umbrella with auto-open",
            "category": "other",
            "sku": "OTH-004",
            "barcode": "736211260870",
            "weight": Decimal("0.4"),
        },
        {
            "name": "Flashlight LED",
            "description": "Rechargeable LED flashlight, 1000 lumens",
            "category": "other",
            "sku": "OTH-005",
            "barcode": "736211260887",
            "weight": Decimal("0.25"),
        },
        {
            "name": "First Aid Kit",
            "description": "Complete first aid kit, 100-piece set",
            "category": "other",
            "sku": "OTH-006",
            "barcode": "736211260894",
            "weight": Decimal("0.6"),
        },
    ]

    products = [Product.model_validate(data) for data in products_data]

    for product in products:
        db.add_product(product)
        print(f"  Added product: {product.name} (SKU: {product.sku})")

    print()

    # Create supplier-product relationships
    # Note: Some products have multiple suppliers (primary + alternatives)
    print("Creating supplier-product relationships...")
    supplier_products_data = [
        # BEVERAGES - suppliers
        # Coffee Beans - HAS MULTIPLE SUPPLIERS
        {"product_id": products[0].id, "supplier_id": "SUP-001", "cost": Decimal("6.50"),
         "is_primary_supplier": True, "lead_time_days": 14, "minimum_order_quantity": 50},
        {"product_id": products[0].id, "supplier_id": "SUP-003", "cost": Decimal("7.00"),
         "is_primary_supplier": False, "lead_time_days": 10, "minimum_order_quantity": 30},
        # Earl Grey Tea
        {"product_id": products[1].id, "supplier_id": "SUP-002", "cost": Decimal("4.25"),
         "is_primary_supplier": True, "lead_time_days": 7, "minimum_order_quantity": 25},
        # Orange Juice
        {"product_id": products[2].id, "supplier_id": "SUP-003", "cost": Decimal("2.50"),
         "is_primary_supplier": True, "lead_time_days": 5, "minimum_order_quantity": 20},
        # Cola Soda - HAS MULTIPLE SUPPLIERS
        {"product_id": products[3].id, "supplier_id": "SUP-003", "cost": Decimal("8.00"),
         "is_primary_supplier": True, "lead_time_days": 3, "minimum_order_quantity": 50},
        {"product_id": products[3].id, "supplier_id": "SUP-001", "cost": Decimal("8.50"),
         "is_primary_supplier": False, "lead_time_days": 7, "minimum_order_quantity": 40},
        # Energy Drink
        {"product_id": products[4].id, "supplier_id": "SUP-003", "cost": Decimal("1.75"),
         "is_primary_supplier": True, "lead_time_days": 5, "minimum_order_quantity": 100},
        # Green Tea
        {"product_id": products[5].id, "supplier_id": "SUP-002", "cost": Decimal("3.50"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 20},

        # FOOD - suppliers
        # Cookies
        {"product_id": products[6].id, "supplier_id": "SUP-004", "cost": Decimal("2.50"),
         "is_primary_supplier": True, "lead_time_days": 1, "minimum_order_quantity": 12},
        # Pasta - HAS MULTIPLE SUPPLIERS
        {"product_id": products[7].id, "supplier_id": "SUP-005", "cost": Decimal("1.25"),
         "is_primary_supplier": True, "lead_time_days": 7, "minimum_order_quantity": 50},
        {"product_id": products[7].id, "supplier_id": "SUP-004", "cost": Decimal("1.40"),
         "is_primary_supplier": False, "lead_time_days": 3, "minimum_order_quantity": 30},
        # Tomato Sauce
        {"product_id": products[8].id, "supplier_id": "SUP-005", "cost": Decimal("1.80"),
         "is_primary_supplier": True, "lead_time_days": 7, "minimum_order_quantity": 40},
        # Mixed Nuts
        {"product_id": products[9].id, "supplier_id": "SUP-005", "cost": Decimal("4.00"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 25},
        # Canned Tuna
        {"product_id": products[10].id, "supplier_id": "SUP-005", "cost": Decimal("1.50"),
         "is_primary_supplier": True, "lead_time_days": 14, "minimum_order_quantity": 60},
        # Granola Bars
        {"product_id": products[11].id, "supplier_id": "SUP-005", "cost": Decimal("3.25"),
         "is_primary_supplier": True, "lead_time_days": 7, "minimum_order_quantity": 30},

        # ELECTRONICS - suppliers
        # Headphones - HAS MULTIPLE SUPPLIERS
        {"product_id": products[12].id, "supplier_id": "SUP-006", "cost": Decimal("120.00"),
         "is_primary_supplier": True, "lead_time_days": 21, "minimum_order_quantity": 5},
        {"product_id": products[12].id, "supplier_id": "SUP-007", "cost": Decimal("115.00"),
         "is_primary_supplier": False, "lead_time_days": 14, "minimum_order_quantity": 10},
        # Mechanical Keyboard
        {"product_id": products[13].id, "supplier_id": "SUP-006", "cost": Decimal("75.00"),
         "is_primary_supplier": True, "lead_time_days": 14, "minimum_order_quantity": 5},
        # Wireless Mouse - HAS MULTIPLE SUPPLIERS
        {"product_id": products[14].id, "supplier_id": "SUP-006", "cost": Decimal("18.00"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 10},
        {"product_id": products[14].id, "supplier_id": "SUP-007", "cost": Decimal("17.00"),
         "is_primary_supplier": False, "lead_time_days": 7, "minimum_order_quantity": 15},
        # USB-C Cable
        {"product_id": products[15].id, "supplier_id": "SUP-007", "cost": Decimal("5.50"),
         "is_primary_supplier": True, "lead_time_days": 5, "minimum_order_quantity": 20},
        # Power Bank
        {"product_id": products[16].id, "supplier_id": "SUP-006", "cost": Decimal("22.00"),
         "is_primary_supplier": True, "lead_time_days": 14, "minimum_order_quantity": 10},
        # LED Monitor
        {"product_id": products[17].id, "supplier_id": "SUP-006", "cost": Decimal("135.00"),
         "is_primary_supplier": True, "lead_time_days": 21, "minimum_order_quantity": 3},

        # BOOKS - suppliers
        # Python Programming Guide
        {"product_id": products[18].id, "supplier_id": "SUP-008", "cost": Decimal("25.00"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 10},
        # The Great Novel - HAS MULTIPLE SUPPLIERS
        {"product_id": products[19].id, "supplier_id": "SUP-009", "cost": Decimal("8.00"),
         "is_primary_supplier": True, "lead_time_days": 5, "minimum_order_quantity": 20},
        {"product_id": products[19].id, "supplier_id": "SUP-008", "cost": Decimal("8.50"),
         "is_primary_supplier": False, "lead_time_days": 7, "minimum_order_quantity": 15},
        # Business Strategy
        {"product_id": products[20].id, "supplier_id": "SUP-008", "cost": Decimal("18.00"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 10},
        # Self-Help Mastery
        {"product_id": products[21].id, "supplier_id": "SUP-009", "cost": Decimal("12.00"),
         "is_primary_supplier": True, "lead_time_days": 7, "minimum_order_quantity": 15},
        # Cookbook
        {"product_id": products[22].id, "supplier_id": "SUP-008", "cost": Decimal("20.00"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 8},
        # Web Development
        {"product_id": products[23].id, "supplier_id": "SUP-008", "cost": Decimal("28.00"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 10},

        # CLOTHING - suppliers
        # T-Shirt - HAS MULTIPLE SUPPLIERS
        {"product_id": products[24].id, "supplier_id": "SUP-010", "cost": Decimal("5.00"),
         "is_primary_supplier": True, "lead_time_days": 14, "minimum_order_quantity": 50},
        {"product_id": products[24].id, "supplier_id": "SUP-011", "cost": Decimal("4.75"),
         "is_primary_supplier": False, "lead_time_days": 10, "minimum_order_quantity": 60},
        # Denim Jeans
        {"product_id": products[25].id, "supplier_id": "SUP-010", "cost": Decimal("22.00"),
         "is_primary_supplier": True, "lead_time_days": 21, "minimum_order_quantity": 20},
        # Running Shoes
        {"product_id": products[26].id, "supplier_id": "SUP-011", "cost": Decimal("35.00"),
         "is_primary_supplier": True, "lead_time_days": 21, "minimum_order_quantity": 10},
        # Winter Jacket - HAS MULTIPLE SUPPLIERS
        {"product_id": products[27].id, "supplier_id": "SUP-010", "cost": Decimal("45.00"),
         "is_primary_supplier": True, "lead_time_days": 28, "minimum_order_quantity": 15},
        {"product_id": products[27].id, "supplier_id": "SUP-011", "cost": Decimal("43.00"),
         "is_primary_supplier": False, "lead_time_days": 21, "minimum_order_quantity": 20},
        # Baseball Cap
        {"product_id": products[28].id, "supplier_id": "SUP-011", "cost": Decimal("6.50"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 40},
        # Wool Socks
        {"product_id": products[29].id, "supplier_id": "SUP-010", "cost": Decimal("8.00"),
         "is_primary_supplier": True, "lead_time_days": 14, "minimum_order_quantity": 30},

        # HOME & GARDEN - suppliers
        # Tool Set
        {"product_id": products[30].id, "supplier_id": "SUP-012", "cost": Decimal("35.00"),
         "is_primary_supplier": True, "lead_time_days": 14, "minimum_order_quantity": 5},
        # Potted Plant
        {"product_id": products[31].id, "supplier_id": "SUP-013", "cost": Decimal("8.00"),
         "is_primary_supplier": True, "lead_time_days": 7, "minimum_order_quantity": 15},
        # Throw Pillow - HAS MULTIPLE SUPPLIERS
        {"product_id": products[32].id, "supplier_id": "SUP-012", "cost": Decimal("12.00"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 20},
        {"product_id": products[32].id, "supplier_id": "SUP-013", "cost": Decimal("11.50"),
         "is_primary_supplier": False, "lead_time_days": 14, "minimum_order_quantity": 25},
        # Garden Hose
        {"product_id": products[33].id, "supplier_id": "SUP-013", "cost": Decimal("18.00"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 10},
        # Cleaning Spray
        {"product_id": products[34].id, "supplier_id": "SUP-012", "cost": Decimal("3.50"),
         "is_primary_supplier": True, "lead_time_days": 7, "minimum_order_quantity": 40},
        # LED Bulbs
        {"product_id": products[35].id, "supplier_id": "SUP-012", "cost": Decimal("8.00"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 25},

        # OFFICE SUPPLIES - suppliers
        # Pens
        {"product_id": products[36].id, "supplier_id": "SUP-014", "cost": Decimal("4.50"),
         "is_primary_supplier": True, "lead_time_days": 5, "minimum_order_quantity": 30},
        # Printer Paper - HAS MULTIPLE SUPPLIERS
        {"product_id": products[37].id, "supplier_id": "SUP-014", "cost": Decimal("6.00"),
         "is_primary_supplier": True, "lead_time_days": 3, "minimum_order_quantity": 50},
        {"product_id": products[37].id, "supplier_id": "SUP-015", "cost": Decimal("5.75"),
         "is_primary_supplier": False, "lead_time_days": 5, "minimum_order_quantity": 60},
        # File Folders
        {"product_id": products[38].id, "supplier_id": "SUP-015", "cost": Decimal("12.00"),
         "is_primary_supplier": True, "lead_time_days": 7, "minimum_order_quantity": 20},
        # Stapler
        {"product_id": products[39].id, "supplier_id": "SUP-014", "cost": Decimal("8.50"),
         "is_primary_supplier": True, "lead_time_days": 5, "minimum_order_quantity": 15},
        # Sticky Notes
        {"product_id": products[40].id, "supplier_id": "SUP-015", "cost": Decimal("5.00"),
         "is_primary_supplier": True, "lead_time_days": 5, "minimum_order_quantity": 40},
        # Desk Organizer
        {"product_id": products[41].id, "supplier_id": "SUP-014", "cost": Decimal("12.00"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 10},

        # OTHER - suppliers
        # Water Bottle
        {"product_id": products[42].id, "supplier_id": "SUP-012", "cost": Decimal("10.00"),
         "is_primary_supplier": True, "lead_time_days": 14, "minimum_order_quantity": 20},
        # Phone Case
        {"product_id": products[43].id, "supplier_id": "SUP-007", "cost": Decimal("3.00"),
         "is_primary_supplier": True, "lead_time_days": 7, "minimum_order_quantity": 50},
        # Backpack - HAS MULTIPLE SUPPLIERS
        {"product_id": products[44].id, "supplier_id": "SUP-011", "cost": Decimal("25.00"),
         "is_primary_supplier": True, "lead_time_days": 14, "minimum_order_quantity": 15},
        {"product_id": products[44].id, "supplier_id": "SUP-010", "cost": Decimal("26.00"),
         "is_primary_supplier": False, "lead_time_days": 21, "minimum_order_quantity": 12},
        # Umbrella
        {"product_id": products[45].id, "supplier_id": "SUP-012", "cost": Decimal("8.00"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 25},
        # Flashlight
        {"product_id": products[46].id, "supplier_id": "SUP-007", "cost": Decimal("12.00"),
         "is_primary_supplier": True, "lead_time_days": 14, "minimum_order_quantity": 15},
        # First Aid Kit
        {"product_id": products[47].id, "supplier_id": "SUP-012", "cost": Decimal("15.00"),
         "is_primary_supplier": True, "lead_time_days": 10, "minimum_order_quantity": 10},
    ]

    supplier_products = [SupplierProduct.model_validate(data) for data in supplier_products_data]

    for supplier_product in supplier_products:
        db.add_supplier_product(supplier_product)
        print(f"  Added relationship: {supplier_product.supplier_id} -> Product")

    print()

    # Create inventory items
    # Note: Some products have multiple inventory items at different locations
    print("Creating inventory items...")
    from inventory_db import ItemStatus

    inventory_items_data = [
        # BEVERAGES
        # Coffee Beans - MULTIPLE LOCATIONS
        {"product_id": products[0].id, "location_id": "WH-01", "price": Decimal("12.99"),
         "quantity_on_hand": 150, "reorder_point": 20, "status": ItemStatus.ACTIVE},
        {"product_id": products[0].id, "location_id": "STORE-01", "price": Decimal("14.99"),
         "quantity_on_hand": 30, "reorder_point": 10, "status": ItemStatus.ACTIVE},
        # Earl Grey Tea
        {"product_id": products[1].id, "location_id": "WH-01", "price": Decimal("8.99"),
         "quantity_on_hand": 75, "reorder_point": 15, "status": ItemStatus.ACTIVE},
        # Orange Juice
        {"product_id": products[2].id, "location_id": "WH-01", "price": Decimal("5.99"),
         "quantity_on_hand": 45, "reorder_point": 20, "status": ItemStatus.ACTIVE},
        # Cola Soda - MULTIPLE LOCATIONS
        {"product_id": products[3].id, "location_id": "WH-01", "price": Decimal("16.99"),
         "quantity_on_hand": 200, "reorder_point": 50, "status": ItemStatus.ACTIVE},
        {"product_id": products[3].id, "location_id": "STORE-01", "price": Decimal("18.99"),
         "quantity_on_hand": 40, "reorder_point": 15, "status": ItemStatus.ACTIVE},
        # Energy Drink
        {"product_id": products[4].id, "location_id": "WH-01", "price": Decimal("3.49"),
         "quantity_on_hand": 120, "reorder_point": 30, "status": ItemStatus.ACTIVE},
        # Green Tea
        {"product_id": products[5].id, "location_id": "WH-01", "price": Decimal("7.99"),
         "quantity_on_hand": 60, "reorder_point": 15, "status": ItemStatus.ACTIVE},

        # FOOD
        # Cookies
        {"product_id": products[6].id, "location_id": "WH-01", "price": Decimal("5.99"),
         "quantity_on_hand": 25, "reorder_point": 30, "status": ItemStatus.OUT_OF_STOCK},
        # Pasta - MULTIPLE LOCATIONS
        {"product_id": products[7].id, "location_id": "WH-01", "price": Decimal("2.99"),
         "quantity_on_hand": 180, "reorder_point": 40, "status": ItemStatus.ACTIVE},
        {"product_id": products[7].id, "location_id": "STORE-02", "price": Decimal("3.49"),
         "quantity_on_hand": 50, "reorder_point": 20, "status": ItemStatus.ACTIVE},
        # Tomato Sauce
        {"product_id": products[8].id, "location_id": "WH-01", "price": Decimal("3.99"),
         "quantity_on_hand": 90, "reorder_point": 25, "status": ItemStatus.ACTIVE},
        # Mixed Nuts
        {"product_id": products[9].id, "location_id": "WH-01", "price": Decimal("8.99"),
         "quantity_on_hand": 60, "reorder_point": 15, "status": ItemStatus.ACTIVE},
        # Canned Tuna
        {"product_id": products[10].id, "location_id": "WH-01", "price": Decimal("2.99"),
         "quantity_on_hand": 200, "reorder_point": 60, "status": ItemStatus.ACTIVE},
        # Granola Bars
        {"product_id": products[11].id, "location_id": "WH-01", "price": Decimal("6.99"),
         "quantity_on_hand": 70, "reorder_point": 20, "status": ItemStatus.ACTIVE},

        # ELECTRONICS
        # Headphones - MULTIPLE LOCATIONS
        {"product_id": products[12].id, "location_id": "WH-01", "price": Decimal("199.99"),
         "quantity_on_hand": 12, "reorder_point": 5, "status": ItemStatus.ACTIVE},
        {"product_id": products[12].id, "location_id": "STORE-01", "price": Decimal("219.99"),
         "quantity_on_hand": 3, "reorder_point": 2, "status": ItemStatus.ACTIVE},
        # Mechanical Keyboard
        {"product_id": products[13].id, "location_id": "WH-01", "price": Decimal("129.99"),
         "quantity_on_hand": 15, "reorder_point": 5, "status": ItemStatus.ACTIVE},
        # Wireless Mouse - MULTIPLE LOCATIONS
        {"product_id": products[14].id, "location_id": "WH-01", "price": Decimal("29.99"),
         "quantity_on_hand": 35, "reorder_point": 10, "status": ItemStatus.ACTIVE},
        {"product_id": products[14].id, "location_id": "STORE-02", "price": Decimal("32.99"),
         "quantity_on_hand": 8, "reorder_point": 5, "status": ItemStatus.ACTIVE},
        # USB-C Cable
        {"product_id": products[15].id, "location_id": "WH-01", "price": Decimal("12.99"),
         "quantity_on_hand": 80, "reorder_point": 20, "status": ItemStatus.ACTIVE},
        # Power Bank
        {"product_id": products[16].id, "location_id": "WH-01", "price": Decimal("39.99"),
         "quantity_on_hand": 25, "reorder_point": 10, "status": ItemStatus.ACTIVE},
        # LED Monitor
        {"product_id": products[17].id, "location_id": "WH-01", "price": Decimal("249.99"),
         "quantity_on_hand": 8, "reorder_point": 3, "status": ItemStatus.ACTIVE},

        # BOOKS
        # Python Programming Guide
        {"product_id": products[18].id, "location_id": "WH-01", "price": Decimal("39.99"),
         "quantity_on_hand": 20, "reorder_point": 5, "status": ItemStatus.ACTIVE},
        # The Great Novel - MULTIPLE LOCATIONS
        {"product_id": products[19].id, "location_id": "WH-01", "price": Decimal("14.99"),
         "quantity_on_hand": 50, "reorder_point": 15, "status": ItemStatus.ACTIVE},
        {"product_id": products[19].id, "location_id": "STORE-01", "price": Decimal("16.99"),
         "quantity_on_hand": 12, "reorder_point": 5, "status": ItemStatus.ACTIVE},
        # Business Strategy
        {"product_id": products[20].id, "location_id": "WH-01", "price": Decimal("29.99"),
         "quantity_on_hand": 30, "reorder_point": 8, "status": ItemStatus.ACTIVE},
        # Self-Help Mastery
        {"product_id": products[21].id, "location_id": "WH-01", "price": Decimal("19.99"),
         "quantity_on_hand": 40, "reorder_point": 10, "status": ItemStatus.ACTIVE},
        # Cookbook
        {"product_id": products[22].id, "location_id": "WH-01", "price": Decimal("34.99"),
         "quantity_on_hand": 25, "reorder_point": 6, "status": ItemStatus.ACTIVE},
        # Web Development
        {"product_id": products[23].id, "location_id": "WH-01", "price": Decimal("44.99"),
         "quantity_on_hand": 18, "reorder_point": 5, "status": ItemStatus.ACTIVE},

        # CLOTHING
        # T-Shirt - MULTIPLE LOCATIONS
        {"product_id": products[24].id, "location_id": "WH-01", "price": Decimal("12.99"),
         "quantity_on_hand": 150, "reorder_point": 40, "status": ItemStatus.ACTIVE},
        {"product_id": products[24].id, "location_id": "STORE-02", "price": Decimal("14.99"),
         "quantity_on_hand": 35, "reorder_point": 15, "status": ItemStatus.ACTIVE},
        # Denim Jeans
        {"product_id": products[25].id, "location_id": "WH-01", "price": Decimal("39.99"),
         "quantity_on_hand": 60, "reorder_point": 15, "status": ItemStatus.ACTIVE},
        # Running Shoes
        {"product_id": products[26].id, "location_id": "WH-01", "price": Decimal("69.99"),
         "quantity_on_hand": 30, "reorder_point": 8, "status": ItemStatus.ACTIVE},
        # Winter Jacket - MULTIPLE LOCATIONS
        {"product_id": products[27].id, "location_id": "WH-01", "price": Decimal("89.99"),
         "quantity_on_hand": 40, "reorder_point": 10, "status": ItemStatus.ACTIVE},
        {"product_id": products[27].id, "location_id": "STORE-01", "price": Decimal("99.99"),
         "quantity_on_hand": 8, "reorder_point": 3, "status": ItemStatus.ACTIVE},
        # Baseball Cap
        {"product_id": products[28].id, "location_id": "WH-01", "price": Decimal("14.99"),
         "quantity_on_hand": 80, "reorder_point": 25, "status": ItemStatus.ACTIVE},
        # Wool Socks
        {"product_id": products[29].id, "location_id": "WH-01", "price": Decimal("16.99"),
         "quantity_on_hand": 100, "reorder_point": 30, "status": ItemStatus.ACTIVE},

        # HOME & GARDEN
        # Tool Set
        {"product_id": products[30].id, "location_id": "WH-01", "price": Decimal("59.99"),
         "quantity_on_hand": 15, "reorder_point": 5, "status": ItemStatus.ACTIVE},
        # Potted Plant
        {"product_id": products[31].id, "location_id": "STORE-01", "price": Decimal("14.99"),
         "quantity_on_hand": 25, "reorder_point": 10, "status": ItemStatus.ACTIVE},
        # Throw Pillow - MULTIPLE LOCATIONS
        {"product_id": products[32].id, "location_id": "WH-01", "price": Decimal("19.99"),
         "quantity_on_hand": 50, "reorder_point": 15, "status": ItemStatus.ACTIVE},
        {"product_id": products[32].id, "location_id": "STORE-02", "price": Decimal("22.99"),
         "quantity_on_hand": 12, "reorder_point": 5, "status": ItemStatus.ACTIVE},
        # Garden Hose
        {"product_id": products[33].id, "location_id": "WH-01", "price": Decimal("29.99"),
         "quantity_on_hand": 20, "reorder_point": 8, "status": ItemStatus.ACTIVE},
        # Cleaning Spray
        {"product_id": products[34].id, "location_id": "WH-01", "price": Decimal("6.99"),
         "quantity_on_hand": 90, "reorder_point": 30, "status": ItemStatus.ACTIVE},
        # LED Bulbs
        {"product_id": products[35].id, "location_id": "WH-01", "price": Decimal("14.99"),
         "quantity_on_hand": 60, "reorder_point": 20, "status": ItemStatus.ACTIVE},

        # OFFICE SUPPLIES
        # Pens
        {"product_id": products[36].id, "location_id": "WH-01", "price": Decimal("8.99"),
         "quantity_on_hand": 100, "reorder_point": 30, "status": ItemStatus.ACTIVE},
        # Printer Paper - MULTIPLE LOCATIONS
        {"product_id": products[37].id, "location_id": "WH-01", "price": Decimal("9.99"),
         "quantity_on_hand": 150, "reorder_point": 50, "status": ItemStatus.ACTIVE},
        {"product_id": products[37].id, "location_id": "STORE-02", "price": Decimal("11.99"),
         "quantity_on_hand": 30, "reorder_point": 15, "status": ItemStatus.ACTIVE},
        # File Folders
        {"product_id": products[38].id, "location_id": "WH-01", "price": Decimal("19.99"),
         "quantity_on_hand": 40, "reorder_point": 15, "status": ItemStatus.ACTIVE},
        # Stapler
        {"product_id": products[39].id, "location_id": "WH-01", "price": Decimal("14.99"),
         "quantity_on_hand": 35, "reorder_point": 10, "status": ItemStatus.ACTIVE},
        # Sticky Notes
        {"product_id": products[40].id, "location_id": "WH-01", "price": Decimal("9.99"),
         "quantity_on_hand": 80, "reorder_point": 30, "status": ItemStatus.ACTIVE},
        # Desk Organizer
        {"product_id": products[41].id, "location_id": "WH-01", "price": Decimal("19.99"),
         "quantity_on_hand": 25, "reorder_point": 8, "status": ItemStatus.ACTIVE},

        # OTHER
        # Water Bottle
        {"product_id": products[42].id, "location_id": "WH-01", "price": Decimal("17.99"),
         "quantity_on_hand": 45, "reorder_point": 15, "status": ItemStatus.ACTIVE},
        # Phone Case
        {"product_id": products[43].id, "location_id": "WH-01", "price": Decimal("7.99"),
         "quantity_on_hand": 120, "reorder_point": 40, "status": ItemStatus.ACTIVE},
        # Backpack - MULTIPLE LOCATIONS
        {"product_id": products[44].id, "location_id": "WH-01", "price": Decimal("49.99"),
         "quantity_on_hand": 30, "reorder_point": 10, "status": ItemStatus.ACTIVE},
        {"product_id": products[44].id, "location_id": "STORE-01", "price": Decimal("54.99"),
         "quantity_on_hand": 8, "reorder_point": 3, "status": ItemStatus.ACTIVE},
        # Umbrella
        {"product_id": products[45].id, "location_id": "WH-01", "price": Decimal("14.99"),
         "quantity_on_hand": 40, "reorder_point": 12, "status": ItemStatus.ACTIVE},
        # Flashlight
        {"product_id": products[46].id, "location_id": "WH-01", "price": Decimal("19.99"),
         "quantity_on_hand": 35, "reorder_point": 10, "status": ItemStatus.ACTIVE},
        # First Aid Kit
        {"product_id": products[47].id, "location_id": "WH-01", "price": Decimal("24.99"),
         "quantity_on_hand": 20, "reorder_point": 8, "status": ItemStatus.ACTIVE},
    ]

    inventory_items = [InventoryItem.model_validate(data) for data in inventory_items_data]

    for inventory_item in inventory_items:
        db.add_inventory_item(inventory_item)
        # Find product name by ID
        product = next(p for p in products if p.id == inventory_item.product_id)
        location = inventory_item.location_id or "MAIN"
        print(f"  Added inventory: {product.name} @ {location} (qty: {inventory_item.quantity_on_hand})")

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
