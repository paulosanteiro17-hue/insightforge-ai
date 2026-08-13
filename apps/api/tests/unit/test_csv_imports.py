from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Sequence
from datetime import UTC
from pathlib import Path

import pytest

from insightforge.imports import (
    CUSTOMER_HEADERS,
    ORDER_HEADERS,
    PRODUCT_HEADERS,
    CsvImportKind,
    CsvImportLimits,
    CsvImportRejected,
    CustomerCsvRow,
    OrderCsvRow,
    ProductCsvRow,
    validate_csv,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SAMPLE_DIRECTORY = REPOSITORY_ROOT / "data" / "samples"


def _csv_bytes(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode()


def _customer_row(
    external_id: str = "CUS-1",
    *,
    name: str = "Ada Lovelace",
    email: str = "ada@analytics.example",
    company: str = "Analytical Engines",
    status: str = "active",
    acquired_at: str = "2026-07-01T10:30:00Z",
) -> list[str]:
    return [external_id, name, email, company, status, acquired_at]


def _product_row(
    external_id: str = "PRD-1",
    *,
    sku: str = "ANL-1",
    name: str = "Analytics Plan",
    category: str = "Subscriptions",
    unit_price: str = "249.00",
    status: str = "active",
) -> list[str]:
    return [external_id, sku, name, category, unit_price, status]


def _order_row(
    external_id: str = "ORD-1",
    *,
    order_number: str = "IF-1001",
    customer_external_id: str = "CUS-1",
    status: str = "paid",
    ordered_at: str = "2026-07-02T12:00:00Z",
    currency: str = "USD",
    product_sku: str = "ANL-1",
    quantity: str = "1",
    unit_price: str = "249.00",
    discount: str = "0.00",
    tax: str = "0.00",
) -> list[str]:
    return [
        external_id,
        order_number,
        customer_external_id,
        status,
        ordered_at,
        currency,
        product_sku,
        quantity,
        unit_price,
        discount,
        tax,
    ]


@pytest.mark.parametrize(
    ("kind", "filename", "headers", "row_type"),
    [
        (CsvImportKind.CUSTOMERS, "customers.csv", CUSTOMER_HEADERS, CustomerCsvRow),
        (CsvImportKind.PRODUCTS, "products.csv", PRODUCT_HEADERS, ProductCsvRow),
        (CsvImportKind.ORDERS, "orders.csv", ORDER_HEADERS, OrderCsvRow),
    ],
)
def test_checked_in_samples_match_the_version_one_contract(
    kind: CsvImportKind,
    filename: str,
    headers: tuple[str, ...],
    row_type: type[CustomerCsvRow] | type[ProductCsvRow] | type[OrderCsvRow],
) -> None:
    payload = (SAMPLE_DIRECTORY / filename).read_bytes()

    result = validate_csv(payload, kind=kind)

    assert result.is_valid
    assert result.template_version == 1
    assert result.headers == headers
    assert result.byte_count == len(payload)
    assert result.content_sha256 == hashlib.sha256(payload).hexdigest()
    assert result.total_rows == 8
    assert result.valid_rows == 8
    assert result.invalid_rows == 0
    assert len(result.preview_rows) == 8
    assert all(isinstance(row, row_type) for row in result.preview_rows)
    assert result.errors == ()
    assert result.formula_cells == ()


def test_sample_values_are_normalized_into_typed_preview_rows() -> None:
    customer_result = validate_csv(
        (SAMPLE_DIRECTORY / "customers.csv").read_bytes(),
        kind=CsvImportKind.CUSTOMERS,
    )
    product_result = validate_csv(
        (SAMPLE_DIRECTORY / "products.csv").read_bytes(),
        kind=CsvImportKind.PRODUCTS,
    )
    order_result = validate_csv(
        (SAMPLE_DIRECTORY / "orders.csv").read_bytes(),
        kind=CsvImportKind.ORDERS,
    )

    customer = customer_result.preview_rows[0]
    product = product_result.preview_rows[0]
    order = order_result.preview_rows[0]
    assert isinstance(customer, CustomerCsvRow)
    assert customer.email == "maya.bennett@northstarstudio.example"
    assert customer.acquired_at.tzinfo is UTC
    assert isinstance(product, ProductCsvRow)
    assert product.unit_price_minor == 24_900
    assert isinstance(order, OrderCsvRow)
    assert order.unit_price_minor == 125_000
    assert order.quantity == 1


def test_accepts_binary_file_like_input_without_changing_the_result() -> None:
    payload = _csv_bytes(CUSTOMER_HEADERS, [_customer_row()])

    from_bytes = validate_csv(payload, kind="customers")
    from_stream = validate_csv(io.BytesIO(payload), kind=CsvImportKind.CUSTOMERS)

    assert from_stream == from_bytes


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"\xff\xfeinvalid", "bom_not_allowed"),
        (b"\xef\xbb\xbfexternal_id,name,email,company,status,acquired_at\n", "bom_not_allowed"),
        (b"external_id,name,email,company,status,acquired_at\nCUS-1,\xff", "invalid_utf8"),
        (b"external_id,name,email,company,status,acquired_at\nCUS-1,Ada\x00", "nul_byte"),
        (
            "external_id,name,email,company,status,acquired_at\n"
            "CUS-1,A\ufeffda,,,active,2026-07-01T10:30:00Z\n".encode(),
            "bom_not_allowed",
        ),
    ],
)
def test_rejects_encoding_and_byte_order_mark_surprises(payload: bytes, code: str) -> None:
    with pytest.raises(CsvImportRejected) as caught:
        validate_csv(payload, kind=CsvImportKind.CUSTOMERS)

    assert caught.value.code == code


def test_rejects_malformed_csv_with_a_sanitized_file_error() -> None:
    payload = (
        b"external_id,name,email,company,status,acquired_at\n"
        b'CUS-1,"unterminated field,,,active,2026-07-01T10:30:00Z\n'
    )

    with pytest.raises(CsvImportRejected) as caught:
        validate_csv(payload, kind=CsvImportKind.CUSTOMERS)

    assert caught.value.code == "malformed_csv"
    assert "unterminated field" not in caught.value.message
    assert caught.value.row_number == 2


@pytest.mark.parametrize(
    ("headers", "code"),
    [
        (
            ("external_id", "name", "email", "company", "status", "unexpected"),
            "unexpected_headers",
        ),
        (
            ("external_id", "name", "email", "company", "status", "status"),
            "duplicate_headers",
        ),
        (
            ("name", "external_id", "email", "company", "status", "acquired_at"),
            "unexpected_headers",
        ),
    ],
)
def test_requires_exact_non_duplicate_english_headers(headers: tuple[str, ...], code: str) -> None:
    with pytest.raises(CsvImportRejected) as caught:
        validate_csv(_csv_bytes(headers, []), kind=CsvImportKind.CUSTOMERS)

    assert caught.value.code == code


def test_enforces_byte_row_column_and_preview_caps() -> None:
    payload = _csv_bytes(
        CUSTOMER_HEADERS,
        [_customer_row(), _customer_row("CUS-2", email="grace@analytics.example")],
    )

    with pytest.raises(CsvImportRejected, match="byte limit") as byte_error:
        validate_csv(
            payload,
            kind=CsvImportKind.CUSTOMERS,
            limits=CsvImportLimits(max_bytes=len(payload) - 1),
        )
    assert byte_error.value.code == "byte_limit_exceeded"

    with pytest.raises(CsvImportRejected) as row_error:
        validate_csv(
            payload,
            kind=CsvImportKind.CUSTOMERS,
            limits=CsvImportLimits(max_rows=1),
        )
    assert row_error.value.code == "row_limit_exceeded"
    assert row_error.value.row_number == 3

    with pytest.raises(CsvImportRejected) as column_error:
        validate_csv(
            _csv_bytes(CUSTOMER_HEADERS, [[*_customer_row(), "extra"]]),
            kind=CsvImportKind.CUSTOMERS,
            limits=CsvImportLimits(max_columns=len(CUSTOMER_HEADERS)),
        )
    assert column_error.value.code == "column_limit_exceeded"
    assert column_error.value.row_number == 2

    preview = validate_csv(
        payload,
        kind=CsvImportKind.CUSTOMERS,
        limits=CsvImportLimits(max_preview_rows=1),
    )
    assert preview.total_rows == 2
    assert preview.valid_rows == 2
    assert len(preview.preview_rows) == 1


def test_enforces_field_and_error_caps_without_retaining_submitted_values() -> None:
    secret = "confidential-cell-value"
    payload = _csv_bytes(
        CUSTOMER_HEADERS,
        [_customer_row(name=secret, company=secret)],
    )

    result = validate_csv(
        payload,
        kind=CsvImportKind.CUSTOMERS,
        limits=CsvImportLimits(max_field_chars=4, max_errors=2),
    )

    assert not result.is_valid
    assert result.invalid_rows == 1
    assert result.error_count > len(result.errors) == 2
    assert result.errors_truncated
    assert {error.code for error in result.errors} == {"field_limit_exceeded"}
    assert secret not in repr(result.errors)


def test_reports_a_row_level_column_count_mismatch() -> None:
    result = validate_csv(
        _csv_bytes(CUSTOMER_HEADERS, [["CUS-1", "Ada"]]),
        kind=CsvImportKind.CUSTOMERS,
    )

    assert result.total_rows == 1
    assert result.invalid_rows == 1
    assert result.errors[0].code == "column_count_mismatch"
    assert result.errors[0].column is None
    assert result.errors[0].row_number == 2


def test_validates_required_customer_types_enums_and_timestamps() -> None:
    payload = _csv_bytes(
        CUSTOMER_HEADERS,
        [
            _customer_row(
                "invalid reference",
                name="",
                email="not-an-email",
                status="ACTIVE",
                acquired_at="2026-07-01T10:30:00",
            )
        ],
    )

    result = validate_csv(payload, kind=CsvImportKind.CUSTOMERS)

    assert {error.code for error in result.errors} == {
        "invalid_reference",
        "required",
        "invalid_email",
        "invalid_enum",
        "timezone_required",
    }
    assert result.invalid_rows == 1
    assert result.preview_rows == ()


def test_validates_product_money_precision_and_enums() -> None:
    payload = _csv_bytes(
        PRODUCT_HEADERS,
        [_product_row(sku="invalid sku", unit_price="1.234", status="enabled")],
    )

    result = validate_csv(payload, kind=CsvImportKind.PRODUCTS)

    assert {error.code for error in result.errors} == {
        "invalid_reference",
        "invalid_money",
        "invalid_enum",
    }


def test_validates_order_references_currency_quantity_and_money() -> None:
    payload = _csv_bytes(
        ORDER_HEADERS,
        [
            _order_row(
                customer_external_id="CUS/1",
                currency="usd",
                quantity="0",
                unit_price="-1.00",
                discount="1.2",
            )
        ],
    )

    result = validate_csv(payload, kind=CsvImportKind.ORDERS)

    assert {error.code for error in result.errors} == {
        "invalid_reference",
        "invalid_currency",
        "invalid_integer",
        "invalid_money",
    }
    assert result.formula_cell_count == 1
    assert result.formula_cells[0].column == "unit_price"


def test_rejects_duplicate_customer_and_product_identifiers_after_normalization() -> None:
    customer_result = validate_csv(
        _csv_bytes(
            CUSTOMER_HEADERS,
            [
                _customer_row(email="ADA@analytics.example"),
                _customer_row("CUS-2", email="ada@analytics.example"),
            ],
        ),
        kind=CsvImportKind.CUSTOMERS,
    )
    product_result = validate_csv(
        _csv_bytes(
            PRODUCT_HEADERS,
            [
                _product_row(sku="anl-1"),
                _product_row("PRD-2", sku="ANL-1"),
            ],
        ),
        kind=CsvImportKind.PRODUCTS,
    )

    assert customer_result.valid_rows == 1
    assert customer_result.errors[0].code == "duplicate_identifier"
    assert customer_result.errors[0].column == "email"
    assert product_result.valid_rows == 1
    assert product_result.errors[0].code == "duplicate_identifier"
    assert product_result.errors[0].column == "sku"


def test_validates_grouped_order_reference_shape_and_duplicate_products() -> None:
    payload = _csv_bytes(
        ORDER_HEADERS,
        [
            _order_row(),
            _order_row(product_sku="ANL-2", status="completed"),
            _order_row("ORD-2", order_number="IF-1001", product_sku="ANL-3"),
            _order_row(product_sku="ANL-1", discount="10.00", tax="2.00"),
        ],
    )

    result = validate_csv(payload, kind=CsvImportKind.ORDERS)

    assert result.valid_rows == 1
    assert result.invalid_rows == 3
    assert {error.code for error in result.errors} == {
        "inconsistent_order_group",
        "inconsistent_order_reference",
        "duplicate_order_product",
    }


def test_allows_line_level_order_amounts_to_vary_within_an_order() -> None:
    result = validate_csv(
        _csv_bytes(
            ORDER_HEADERS,
            [
                _order_row(product_sku="ANL-1", discount="10.00", tax="2.00"),
                _order_row(product_sku="ANL-2", discount="0.00", tax="0.00"),
            ],
        ),
        kind=CsvImportKind.ORDERS,
    )

    assert result.is_valid
    assert result.valid_rows == 2


def test_detects_and_caps_formula_leading_cells_without_rejecting_text() -> None:
    payload = _csv_bytes(
        CUSTOMER_HEADERS,
        [_customer_row(name=" =2+2", company="  @operator")],
    )

    result = validate_csv(
        payload,
        kind=CsvImportKind.CUSTOMERS,
        limits=CsvImportLimits(max_formula_cells=1),
    )

    assert result.is_valid
    assert result.formula_cell_count == 2
    assert result.formula_cells_truncated
    assert len(result.formula_cells) == 1
    assert result.formula_cells[0].row_number == 2
    assert result.formula_cells[0].column == "name"
    assert "=2+2" not in repr(result.formula_cells)


def test_rejects_text_returned_by_a_file_like_input() -> None:
    with pytest.raises(CsvImportRejected) as caught:
        validate_csv(io.StringIO("not binary"), kind=CsvImportKind.CUSTOMERS)  # type: ignore[arg-type]

    assert caught.value.code == "binary_input_required"


@pytest.mark.parametrize(
    "limits",
    [
        CsvImportLimits(max_preview_rows=0),
    ],
)
def test_limit_configuration_allows_a_zero_length_preview(limits: CsvImportLimits) -> None:
    result = validate_csv(
        _csv_bytes(CUSTOMER_HEADERS, [_customer_row()]),
        kind=CsvImportKind.CUSTOMERS,
        limits=limits,
    )

    assert result.is_valid
    assert result.preview_rows == ()


@pytest.mark.parametrize(
    "field",
    [
        "max_bytes",
        "max_rows",
        "max_columns",
        "max_field_chars",
        "max_errors",
        "max_formula_cells",
    ],
)
def test_limit_configuration_rejects_non_positive_hard_caps(field: str) -> None:
    with pytest.raises(ValueError, match="must be at least one"):
        CsvImportLimits(**{field: 0})
