from django.conf import settings
from store.models import Product, Fulfillment
import requests
import uuid
from decimal import Decimal
from django.utils import timezone
from .models import Product, Category, ProductImage
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from store.models import Order  # only used for type checking

# ------------------------
# Hardcoded Sandbox Products
# ------------------------
SANDBOX_PRODUCTS = [
    {
        "sku": "MVnHs-Wh-S",
        "design_code": "iPhoneXR",
        "design_link": "https://sandbox.qikink.com/media/designs/sample_design_1.png",
        "mockup_link": "https://sandbox.qikink.com/media/mockups/sample_mockup_1.png",
        "width_inches": 14,
        "height_inches": 12,
        "print_type_id": 1,
        "price": "1",
    },
    {
        "sku": "ABCD1234",
        "design_code": "iPhoneXR",
        "design_link": "https://sandbox.qikink.com/media/designs/sample_design_2.png",
        "mockup_link": "https://sandbox.qikink.com/media/mockups/sample_mockup_2.png",
        "width_inches": 14,
        "height_inches": 12,
        "print_type_id": 1,
        "price": "1",
    },
]

# ------------------------
# Auth Helpers
# ------------------------
def get_qikink_credentials():
    """Return client_id and client_secret based on mode."""
    if settings.QIKINK_MODE == "sandbox":
        return settings.QIKINK_SANDBOX_CLIENT_ID, settings.QIKINK_SANDBOX_CLIENT_SECRET
    elif settings.QIKINK_MODE == "live":
        return settings.QIKINK_LIVE_CLIENT_ID, settings.QIKINK_LIVE_CLIENT_SECRET
    else:
        raise Exception("Invalid Qikink mode in settings.")

def get_qikink_access_token():
    """Request an access token from Qikink."""
    client_id, client_secret = get_qikink_credentials()
    url = f"{settings.QIKINK_BASE_URL}/api/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
    }
    resp = requests.post(url, data=data)
    if resp.status_code == 200:
        return resp.json().get("Accesstoken")
    raise Exception(f"Failed to get token: {resp.text}")

# ------------------------
# Products
# ------------------------

def sync_qikink_products():
    """Sync sandbox products into Product table under dealer='Qikink'."""
    category, _ = Category.objects.get_or_create(name="Qikink Products")

    products = []
    for item in SANDBOX_PRODUCTS:
        product, created = Product.objects.update_or_create(
            sku=item["sku"],
            defaults={
                "name": item.get("design_code", "Qikink Product"),  # 🟢 use design_code as name
                "price": item.get("price", 0),
                "description": f"Imported from Qikink sandbox ({item.get('design_code')})",
                "stock": 10,
                "dealer": "Qikink",
                "category": category,
            },
        )

        # 🖼️ also save the mockup as ProductImage if not already saved
        if item.get("mockup_link"):
            ProductImage.objects.get_or_create(
                product=product,
                image=item["mockup_link"],
            )

        products.append(product)

    return products

# ------------------------
# Orders
# ------------------------
def create_test_order(order: "Order"):
    """
    Create a test order in Qikink sandbox and attach a Fulfillment record.
    """
    try:
        token = get_qikink_access_token()
    except Exception as e:
        return {"error": f"Token error: {e}"}

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    order_no = "TEST" + uuid.uuid4().hex[:6].upper()
    product = SANDBOX_PRODUCTS[0]

    order_data = {
        "order_number": order_no,
        "qikink_shipping": "1",
        "gateway": "COD",
        "total_order_value": product["price"],
        "shipping_address": {
            "first_name": "John",
            "last_name": "Doe",
            "address1": "123 Test Street",
            "city": "Test City",
            "province": "Tamil Nadu",
            "zip": "12345",
            "country_code": "IN",
            "phone": "971500000000",
            "email": "abc@gmail.com",
        },
        "line_items": [
            {
                "search_from_my_products": 0,
                "quantity": "1",
                "print_type_id": product["print_type_id"],
                "price": product["price"],
                "sku": product["sku"],
                "designs": [
                    {
                        "design_code": product["design_code"],
                        "width_inches": str(product["width_inches"]),
                        "height_inches": str(product["height_inches"]),
                        "placement_sku": "fr",
                        "design_link": product["design_link"],
                        "mockup_link": product["mockup_link"],
                    }
                ],
            }
        ],
    }

    order_url = f"{settings.QIKINK_BASE_URL}/api/order/create"
    resp = requests.post(order_url, json=order_data, headers=headers)

    if resp.status_code in [200, 201]:
        data = resp.json()

        # Save fulfillment record
        Fulfillment.objects.create(
            order=order,
            dealer="Qikink",
            dealer_order_id=data.get("order_id"),
            status="created",
            raw_response=data,
            created_at=timezone.now(),
        )
        return data
    else:
        return {"error": resp.text, "status_code": resp.status_code}

import requests

def send_order_to_qikink(order):
    shipping = order.shipping_address

    payload = {
        "order_id": str(order.id),
        "items": [
            {"sku": item.product.sku, "quantity": item.quantity}
            for item in order.items.all()
        ],
        "shipping_address": {
            "name": order.user.get_full_name(),
            "address": shipping.address_line1 if shipping else "",
            "city": shipping.city if shipping else "",
            "pincode": shipping.postal_code if shipping else "",
            "phone": order.user.userprofile.phone if hasattr(order.user, "userprofile") else "",
        }
    }

    return {"status": "success", "message": "Order sent to Qikink", "payload": payload}
