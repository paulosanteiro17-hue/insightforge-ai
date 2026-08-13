"""Stable public imports for the focused commerce services."""

from insightforge.services.customers import (
    CUSTOMER_UNIQUE_CONSTRAINTS,
    CustomerService,
    customer_view,
)
from insightforge.services.orders import (
    ORDER_TRANSITIONS,
    ORDER_UNIQUE_CONSTRAINTS,
    OrderService,
    order_view,
)
from insightforge.services.products import (
    PRODUCT_UNIQUE_CONSTRAINTS,
    ProductService,
    product_view,
)

__all__ = [
    "CUSTOMER_UNIQUE_CONSTRAINTS",
    "ORDER_TRANSITIONS",
    "ORDER_UNIQUE_CONSTRAINTS",
    "PRODUCT_UNIQUE_CONSTRAINTS",
    "CustomerService",
    "OrderService",
    "ProductService",
    "customer_view",
    "order_view",
    "product_view",
]
