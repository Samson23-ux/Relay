from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import inspect, or_, select, text
from sqlalchemy.exc import IntegrityError

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.product_service.app.api.models.product import Product
from shared.models.base import Base
from shared.worker.db import db_engine, db_session

PRODUCTS = [
    {
        "name": "Wireless Mouse",
        "description": "Ergonomic wireless mouse with silent clicks and long battery life.",
        "serial": "WMOUSE001",
        "price": Decimal("29.99"),
        "quantity": 25,
    },
    {
        "name": "Mechanical Keyboard",
        "description": "Compact mechanical keyboard with customizable RGB lighting.",
        "serial": "MKEYBOARD01",
        "price": Decimal("89.50"),
        "quantity": 15,
    },
    {
        "name": "USB-C Hub",
        "description": "Seven-port USB-C hub with HDMI, Ethernet, and fast charging support.",
        "serial": "USBHUB001",
        "price": Decimal("49.99"),
        "quantity": 30,
    },
    {
        "name": "Noise Cancelling Headphones",
        "description": "Over-ear headphones with deep bass and active noise cancellation.",
        "serial": "NCHD001",
        "price": Decimal("129.99"),
        "quantity": 12,
    },
    {
        "name": "Smartphone Stand",
        "description": "Aluminum smartphone stand for desks, beds, and video calls.",
        "serial": "STANDPHONE1",
        "price": Decimal("19.95"),
        "quantity": 40,
    },
    {
        "name": "Laptop Sleeve",
        "description": "Protective sleeve for 13-inch laptops with padded interior.",
        "serial": "LAPSLEEVE1",
        "price": Decimal("34.95"),
        "quantity": 18,
    },
    {
        "name": "Portable SSD",
        "description": "Fast external SSD with USB 3.2 connectivity.",
        "serial": "PSSD001",
        "price": Decimal("109.99"),
        "quantity": 22,
    },
    {
        "name": "Webcam 4K",
        "description": "Ultra HD webcam with autofocus and built-in microphone.",
        "serial": "WEBCAM4K01",
        "price": Decimal("79.90"),
        "quantity": 16,
    },
    {
        "name": "Bluetooth Speaker",
        "description": "Portable speaker with 360-degree sound and water resistance.",
        "serial": "BTSPKR001",
        "price": Decimal("59.99"),
        "quantity": 20,
    },
    {
        "name": "Wireless Charger",
        "description": "Fast wireless charging pad compatible with most smartphones.",
        "serial": "WCHARGER01",
        "price": Decimal("39.50"),
        "quantity": 28,
    },
    {
        "name": "Tablet Case",
        "description": "Slim case with stand function for tablets.",
        "serial": "TBCASE001",
        "price": Decimal("24.99"),
        "quantity": 35,
    },
    {
        "name": "Gaming Mouse",
        "description": "High-precision gaming mouse with customizable DPI settings.",
        "serial": "GMOUSE001",
        "price": Decimal("54.99"),
        "quantity": 17,
    },
    {
        "name": "Monitor Stand",
        "description": "Adjustable aluminum monitor stand for ergonomic setups.",
        "serial": "MONOSTAND1",
        "price": Decimal("44.95"),
        "quantity": 14,
    },
    {
        "name": "USB Lamp",
        "description": "Compact desk lamp with adjustable brightness and USB power.",
        "serial": "USBLAMP001",
        "price": Decimal("22.50"),
        "quantity": 26,
    },
    {
        "name": "Fitness Tracker",
        "description": "Water-resistant fitness tracker with heart rate monitoring.",
        "serial": "FITTRACK01",
        "price": Decimal("69.99"),
        "quantity": 21,
    },
    {
        "name": "Smart Watch",
        "description": "Modern smartwatch with health insights and notifications.",
        "serial": "SMWATCH001",
        "price": Decimal("149.99"),
        "quantity": 13,
    },
    {
        "name": "Desk Organizer",
        "description": "Minimal desk organizer with compartments for cables and accessories.",
        "serial": "DESKORG001",
        "price": Decimal("18.99"),
        "quantity": 24,
    },
    {
        "name": "Printer Paper",
        "description": "Premium A4 paper for office and home printing.",
        "serial": "PRPAPER001",
        "price": Decimal("12.49"),
        "quantity": 45,
    },
    {
        "name": "External Battery",
        "description": "Portable power bank with USB-C fast charging.",
        "serial": "PBANK001",
        "price": Decimal("35.99"),
        "quantity": 19,
    },
    {
        "name": "Noise Reduction Earbuds",
        "description": "True wireless earbuds with active noise cancellation.",
        "serial": "EARBUDS001",
        "price": Decimal("89.99"),
        "quantity": 23,
    },
    {
        "name": "E-Reader",
        "description": "Lightweight e-reader with glare-free display.",
        "serial": "EREADER001",
        "price": Decimal("99.95"),
        "quantity": 11,
    },
    {
        "name": "Office Chair Mat",
        "description": "Durable chair mat for hardwood and carpet floors.",
        "serial": "CHAIRMAT01",
        "price": Decimal("42.50"),
        "quantity": 16,
    },
    {
        "name": "Projector",
        "description": "Portable projector with Full HD resolution and HDMI input.",
        "serial": "PROJECTOR01",
        "price": Decimal("199.99"),
        "quantity": 10,
    },
    {
        "name": "Mic Stand",
        "description": "Sturdy microphone stand for podcasting and streaming.",
        "serial": "MICSTAND01",
        "price": Decimal("27.99"),
        "quantity": 15,
    },
    {
        "name": "Cable Organizer",
        "description": "Neat cable management solution for desks and workstations.",
        "serial": "CABORG001",
        "price": Decimal("14.95"),
        "quantity": 31,
    },
    {
        "name": "Portable Fan",
        "description": "Battery-powered personal fan for travel and desk use.",
        "serial": "PFAN001",
        "price": Decimal("21.99"),
        "quantity": 27,
    },
    {
        "name": "Ring Light",
        "description": "Adjustable LED ring light for video content creation.",
        "serial": "RINGLIGHT01",
        "price": Decimal("32.99"),
        "quantity": 18,
    },
    {
        "name": "Laptop Stand",
        "description": "Aluminum laptop stand for better posture and airflow.",
        "serial": "LAPSTAND01",
        "price": Decimal("29.99"),
        "quantity": 20,
    },
    {
        "name": "Smart Plug",
        "description": "Wi-Fi smart plug for controlling devices remotely.",
        "serial": "SMARTPLUG01",
        "price": Decimal("16.99"),
        "quantity": 33,
    },
    {
        "name": "Bluetooth Keyboard",
        "description": "Slim Bluetooth keyboard with multi-device support.",
        "serial": "BTKEYBOARD1",
        "price": Decimal("49.99"),
        "quantity": 14,
    },
]


def seed_products() -> int:
    inserted_count = 0

    inspector = inspect(db_engine)
    if not inspector.has_table("products"):
        print("Creating products table...")
        Base.metadata.create_all(bind=db_engine)

    with db_session() as session:
        for product_data in PRODUCTS:
            existing_product = session.scalar(
                select(Product).where(
                    or_(
                        Product.name == product_data["name"],
                        Product.serial == product_data["serial"],
                    )
                )
            )

            if existing_product is not None:
                print(f"Skipping existing product: {product_data['name']}")
                continue

            product = Product(
                id=uuid4(),
                name=product_data["name"],
                description=product_data["description"],
                serial=product_data["serial"],
                price=product_data["price"],
                quantity=product_data["quantity"],
            )
            session.add(product)
            inserted_count += 1

        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise RuntimeError(f"Failed to seed products: {exc}") from exc

        print(f"Seeded {inserted_count} product(s) successfully.")


if __name__ == "__main__":
    seed_products()
