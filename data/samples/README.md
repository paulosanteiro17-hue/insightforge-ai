# CSV sample files

These UTF-8 files demonstrate the version 1 English import templates. The application validates exact headers, field types, byte/row limits, duplicate identifiers, and tenant-scoped references before displaying a preview.

## Import order

1. Import `customers.csv`.
2. Import `products.csv`.
3. Import `orders.csv`.

Order files use one row per line item. Rows with the same `external_id` and `order_number` form one order and must repeat identical header values. Monetary fields use fixed two-decimal values in the declared ISO 4217 currency. The server calculates line and order totals; it does not trust a client-supplied total.

The `.example` email domains are intentionally non-deliverable. All people and organizations are fictional.
