"""Populate the database with demo categories, suppliers and products.

Usage:  python -m scripts.seed_demo_data
"""
from decimal import Decimal

from sqlalchemy import func, select

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.category import Category
from app.models.product import Product
from app.models.supplier import Supplier

CATEGORIES = [
    ("Electronics", "Consumer electronics and accessories"),
    ("Stationery", "Office and paper supplies"),
    ("Furniture", "Office furniture"),
    ("Packaging", "Boxes, tape and shipping material"),
]

SUPPLIERS = [
    ("Acme Distribution", "Ravi Kumar", "sales@acme-dist.example", "+91 80 1234 5678"),
    ("Northwind Traders", "Anna Lee", "hello@northwind.example", "+1 206 555 0142"),
    ("Globex Supplies", "Marco Rossi", "orders@globex.example", "+39 02 5550 118"),
]

PRODUCTS = [
    ("ELE-1001", "Wireless Mouse", "Electronics", "Acme Distribution", "18.50", 120, 20),
    ("ELE-1002", "Mechanical Keyboard", "Electronics", "Acme Distribution", "72.00", 45, 10),
    ("ELE-1003", "27\" Monitor", "Electronics", "Northwind Traders", "215.00", 8, 10),
    ("STA-2001", "A4 Paper Ream", "Stationery", "Globex Supplies", "4.20", 500, 100),
    ("STA-2002", "Gel Pen (Box of 12)", "Stationery", "Globex Supplies", "6.75", 60, 25),
    ("FUR-3001", "Ergonomic Chair", "Furniture", "Northwind Traders", "289.00", 12, 5),
    ("FUR-3002", "Standing Desk", "Furniture", "Northwind Traders", "455.00", 3, 5),
    ("PAC-4001", "Shipping Box (Medium)", "Packaging", "Globex Supplies", "1.10", 900, 200),
    ("PAC-4002", "Packing Tape", "Packaging", "Acme Distribution", "2.40", 15, 40),
]


def main() -> None:
    init_db()
    with SessionLocal() as db:
        if db.execute(select(func.count()).select_from(Product)).scalar_one():
            print("Products already exist - nothing seeded.")
            return

        cats = {}
        for name, desc in CATEGORIES:
            obj = Category(name=name, description=desc)
            db.add(obj)
            cats[name] = obj

        sups = {}
        for name, contact, email, phone in SUPPLIERS:
            obj = Supplier(name=name, contact_name=contact, email=email, phone=phone)
            db.add(obj)
            sups[name] = obj

        db.flush()

        for sku, name, cat, sup, price, qty, reorder in PRODUCTS:
            db.add(
                Product(
                    sku=sku,
                    name=name,
                    description=f"{name} supplied by {sup}",
                    unit_price=Decimal(price),
                    quantity=qty,
                    reorder_level=reorder,
                    category_id=cats[cat].id,
                    supplier_id=sups[sup].id,
                )
            )
        db.commit()
        print(f"Seeded {len(CATEGORIES)} categories, {len(SUPPLIERS)} suppliers, {len(PRODUCTS)} products.")


if __name__ == "__main__":
    main()
