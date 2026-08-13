from __future__ import annotations

import codecs
import csv
import hashlib
import io
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from types import MappingProxyType
from typing import Literal, Protocol, TypeAlias, cast

from email_validator import EmailNotValidError, validate_email

from insightforge.core.money import MAX_MONEY_MINOR

CSV_TEMPLATE_VERSION = 1

CUSTOMER_HEADERS = (
    "external_id",
    "name",
    "email",
    "company",
    "status",
    "acquired_at",
)
PRODUCT_HEADERS = (
    "external_id",
    "sku",
    "name",
    "category",
    "unit_price",
    "status",
)
ORDER_HEADERS = (
    "external_id",
    "order_number",
    "customer_external_id",
    "status",
    "ordered_at",
    "currency",
    "product_sku",
    "quantity",
    "unit_price",
    "discount",
    "tax",
)

CustomerStatus = Literal["active", "at_risk", "inactive"]
ProductStatus = Literal["active", "archived"]
OrderStatus = Literal["pending", "paid", "processing", "completed", "cancelled", "refunded"]

_CUSTOMER_STATUSES = frozenset({"active", "at_risk", "inactive"})
_PRODUCT_STATUSES = frozenset({"active", "archived"})
_ORDER_STATUSES = frozenset({"pending", "paid", "processing", "completed", "cancelled", "refunded"})
_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_MONEY_PATTERN = re.compile(r"^[0-9]+\.[0-9]{2}$")
_POSITIVE_INTEGER_PATTERN = re.compile(r"^[1-9][0-9]*$")
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
_CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_FORMULA_PREFIXES = frozenset({"=", "+", "-", "@"})
_KNOWN_BOMS = (
    codecs.BOM_UTF32_LE,
    codecs.BOM_UTF32_BE,
    codecs.BOM_UTF8,
    codecs.BOM_UTF16_LE,
    codecs.BOM_UTF16_BE,
)


class CsvImportKind(StrEnum):
    """Supported version 1 CSV templates."""

    CUSTOMERS = "customers"
    PRODUCTS = "products"
    ORDERS = "orders"


CSV_HEADERS: Mapping[CsvImportKind, tuple[str, ...]] = MappingProxyType(
    {
        CsvImportKind.CUSTOMERS: CUSTOMER_HEADERS,
        CsvImportKind.PRODUCTS: PRODUCT_HEADERS,
        CsvImportKind.ORDERS: ORDER_HEADERS,
    }
)


class BinaryReadable(Protocol):
    """Minimal binary file-like input accepted by validate_csv."""

    def read(self, size: int = -1) -> bytes: ...


CsvSource: TypeAlias = bytes | bytearray | memoryview | BinaryReadable


@dataclass(frozen=True, slots=True)
class CsvImportLimits:
    """Hard resource and diagnostic ceilings for one validation pass."""

    max_bytes: int = 10 * 1024 * 1024
    max_rows: int = 50_000
    max_columns: int = 32
    max_field_chars: int = 2_000
    max_errors: int = 100
    max_preview_rows: int = 20
    max_formula_cells: int = 100

    def __post_init__(self) -> None:
        positive_limits = {
            "max_bytes": self.max_bytes,
            "max_rows": self.max_rows,
            "max_columns": self.max_columns,
            "max_field_chars": self.max_field_chars,
            "max_errors": self.max_errors,
            "max_formula_cells": self.max_formula_cells,
        }
        for name, value in positive_limits.items():
            if value < 1:
                raise ValueError(f"{name} must be at least one.")
        if self.max_preview_rows < 0:
            raise ValueError("max_preview_rows cannot be negative.")


class CsvImportRejected(ValueError):
    """A file-level rejection that makes row-level validation unsafe or incomplete."""

    def __init__(self, code: str, message: str, *, row_number: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.row_number = row_number


@dataclass(frozen=True, slots=True)
class CsvRowError:
    """A sanitized validation error that never retains the submitted cell value."""

    row_number: int
    column: str | None
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class CsvFormulaCell:
    """Location of a cell that needs neutralization before a later CSV export."""

    row_number: int
    column: str


@dataclass(frozen=True, slots=True)
class CustomerCsvRow:
    """Typed, normalized customer preview data."""

    row_number: int
    external_id: str
    name: str
    email: str | None
    company: str | None
    status: CustomerStatus
    acquired_at: datetime


@dataclass(frozen=True, slots=True)
class ProductCsvRow:
    """Typed, normalized product preview data."""

    row_number: int
    external_id: str
    sku: str
    name: str
    category: str
    unit_price_minor: int
    status: ProductStatus


@dataclass(frozen=True, slots=True)
class OrderCsvRow:
    """Typed, normalized order-line preview data."""

    row_number: int
    external_id: str
    order_number: str
    customer_external_id: str
    status: OrderStatus
    ordered_at: datetime
    currency: str
    product_sku: str
    quantity: int
    unit_price_minor: int
    discount_minor: int
    tax_minor: int


CsvPreviewRow: TypeAlias = CustomerCsvRow | ProductCsvRow | OrderCsvRow


@dataclass(frozen=True, slots=True)
class CsvValidationResult:
    """Bounded validation output suitable for an import service preview.

    Only max_preview_rows typed rows are retained. A commit worker must read and
    validate the retained source again rather than treating this preview as an
    authoritative or complete copy of the import.
    """

    kind: CsvImportKind
    template_version: int
    content_sha256: str
    byte_count: int
    headers: tuple[str, ...]
    total_rows: int
    valid_rows: int
    invalid_rows: int
    preview_rows: tuple[CsvPreviewRow, ...]
    errors: tuple[CsvRowError, ...]
    error_count: int
    errors_truncated: bool
    formula_cells: tuple[CsvFormulaCell, ...]
    formula_cell_count: int
    formula_cells_truncated: bool

    @property
    def is_valid(self) -> bool:
        return self.invalid_rows == 0


@dataclass(frozen=True, slots=True)
class _PendingError:
    column: str | None
    code: str
    message: str


class _ErrorCollector:
    def __init__(self, maximum: int) -> None:
        self.maximum = maximum
        self.items: list[CsvRowError] = []
        self.total = 0

    def add(self, row_number: int, error: _PendingError) -> None:
        self.total += 1
        if len(self.items) < self.maximum:
            self.items.append(
                CsvRowError(
                    row_number=row_number,
                    column=error.column,
                    code=error.code,
                    message=error.message,
                )
            )


class _FormulaCollector:
    def __init__(self, maximum: int) -> None:
        self.maximum = maximum
        self.items: list[CsvFormulaCell] = []
        self.total = 0

    def add(self, row_number: int, column: str) -> None:
        self.total += 1
        if len(self.items) < self.maximum:
            self.items.append(CsvFormulaCell(row_number=row_number, column=column))


class _CrossRowState:
    def __init__(self) -> None:
        self.customer_external_ids: set[str] = set()
        self.customer_emails: set[str] = set()
        self.product_external_ids: set[str] = set()
        self.product_skus: set[str] = set()
        self.order_headers: dict[str, tuple[object, ...]] = {}
        self.order_numbers: dict[str, str] = {}
        self.order_products: dict[str, set[str]] = {}

    def accept(self, row: CsvPreviewRow) -> list[_PendingError]:
        if isinstance(row, CustomerCsvRow):
            return self._accept_customer(row)
        if isinstance(row, ProductCsvRow):
            return self._accept_product(row)
        return self._accept_order(row)

    def _accept_customer(self, row: CustomerCsvRow) -> list[_PendingError]:
        errors: list[_PendingError] = []
        if row.external_id in self.customer_external_ids:
            errors.append(
                _error(
                    "external_id",
                    "duplicate_identifier",
                    "Customer external IDs must be unique within the file.",
                )
            )
        email_key = row.email.casefold() if row.email else None
        if email_key is not None and email_key in self.customer_emails:
            errors.append(
                _error(
                    "email",
                    "duplicate_identifier",
                    "Customer email addresses must be unique within the file.",
                )
            )
        if errors:
            return errors
        self.customer_external_ids.add(row.external_id)
        if email_key is not None:
            self.customer_emails.add(email_key)
        return []

    def _accept_product(self, row: ProductCsvRow) -> list[_PendingError]:
        errors: list[_PendingError] = []
        if row.external_id in self.product_external_ids:
            errors.append(
                _error(
                    "external_id",
                    "duplicate_identifier",
                    "Product external IDs must be unique within the file.",
                )
            )
        if row.sku in self.product_skus:
            errors.append(
                _error(
                    "sku", "duplicate_identifier", "Product SKUs must be unique within the file."
                )
            )
        if errors:
            return errors
        self.product_external_ids.add(row.external_id)
        self.product_skus.add(row.sku)
        return []

    def _accept_order(self, row: OrderCsvRow) -> list[_PendingError]:
        errors: list[_PendingError] = []
        existing_external_id = self.order_numbers.get(row.order_number)
        if existing_external_id is not None and existing_external_id != row.external_id:
            errors.append(
                _error(
                    "order_number",
                    "inconsistent_order_reference",
                    "An order number cannot refer to multiple external order IDs.",
                )
            )

        header = (
            row.order_number,
            row.customer_external_id,
            row.status,
            row.ordered_at,
            row.currency,
        )
        existing_header = self.order_headers.get(row.external_id)
        if existing_header is not None and existing_header != header:
            errors.append(
                _error(
                    "external_id",
                    "inconsistent_order_group",
                    "Rows for one external order must repeat identical order-level values.",
                )
            )

        products = self.order_products.get(row.external_id)
        if products is not None and row.product_sku in products:
            errors.append(
                _error(
                    "product_sku",
                    "duplicate_order_product",
                    "A product SKU may appear only once within an order group.",
                )
            )
        if errors:
            return errors

        self.order_numbers[row.order_number] = row.external_id
        self.order_headers.setdefault(row.external_id, header)
        self.order_products.setdefault(row.external_id, set()).add(row.product_sku)
        return []


def validate_csv(
    source: CsvSource,
    *,
    kind: CsvImportKind | str,
    limits: CsvImportLimits | None = None,
) -> CsvValidationResult:
    """Validate one version 1 CSV source without writing files or database state."""

    active_limits = limits or CsvImportLimits()
    try:
        import_kind = CsvImportKind(kind)
    except ValueError as exc:
        raise ValueError("Unsupported CSV import kind.") from exc

    payload = _read_bounded(source, active_limits.max_bytes)
    text = _decode_utf8(payload)
    expected_headers = CSV_HEADERS[import_kind]
    errors = _ErrorCollector(active_limits.max_errors)
    formulas = _FormulaCollector(active_limits.max_formula_cells)
    preview_rows: list[CsvPreviewRow] = []
    state = _CrossRowState()
    total_rows = 0
    valid_rows = 0
    invalid_rows = 0

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        try:
            header_row = next(reader)
        except StopIteration as exc:
            raise CsvImportRejected("empty_file", "The CSV file is empty.") from exc
        headers = tuple(header_row)
        _validate_headers(headers, expected_headers, active_limits.max_columns)

        for raw_row in reader:
            if not raw_row:
                continue
            total_rows += 1
            row_number = reader.line_num
            if total_rows > active_limits.max_rows:
                raise CsvImportRejected(
                    "row_limit_exceeded",
                    "The CSV file contains more data rows than allowed.",
                    row_number=row_number,
                )
            if len(raw_row) > active_limits.max_columns:
                raise CsvImportRejected(
                    "column_limit_exceeded",
                    "A CSV row contains more columns than allowed.",
                    row_number=row_number,
                )
            if len(raw_row) != len(expected_headers):
                errors.add(
                    row_number,
                    _error(
                        None,
                        "column_count_mismatch",
                        "The row must contain exactly the documented template columns.",
                    ),
                )
                invalid_rows += 1
                continue

            cells, pending = _sanitize_cells(
                raw_row,
                expected_headers,
                row_number=row_number,
                limits=active_limits,
                formulas=formulas,
            )
            parsed: CsvPreviewRow | None = None
            if not pending:
                parsed, pending = _parse_row(import_kind, cells, row_number)
            if parsed is not None and not pending:
                pending = state.accept(parsed)

            if pending:
                for error in pending:
                    errors.add(row_number, error)
                invalid_rows += 1
                continue

            if parsed is None:
                raise RuntimeError("CSV row parser returned no row and no validation error.")
            valid_rows += 1
            if len(preview_rows) < active_limits.max_preview_rows:
                preview_rows.append(parsed)
    except csv.Error as exc:
        raise CsvImportRejected(
            "malformed_csv",
            "The CSV file is malformed and could not be parsed.",
            row_number=max(reader.line_num, 1),
        ) from exc

    return CsvValidationResult(
        kind=import_kind,
        template_version=CSV_TEMPLATE_VERSION,
        content_sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        headers=expected_headers,
        total_rows=total_rows,
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        preview_rows=tuple(preview_rows),
        errors=tuple(errors.items),
        error_count=errors.total,
        errors_truncated=errors.total > len(errors.items),
        formula_cells=tuple(formulas.items),
        formula_cell_count=formulas.total,
        formula_cells_truncated=formulas.total > len(formulas.items),
    )


def _read_bounded(source: CsvSource, maximum: int) -> bytes:
    if isinstance(source, (bytes, bytearray, memoryview)):
        payload = bytes(source)
        if len(payload) > maximum:
            raise CsvImportRejected(
                "byte_limit_exceeded",
                "The CSV file is larger than the configured byte limit.",
            )
        return payload

    chunks: list[bytes] = []
    total = 0
    while total <= maximum:
        requested = min(64 * 1024, maximum + 1 - total)
        chunk = source.read(requested)
        if not isinstance(chunk, (bytes, bytearray, memoryview)):
            raise CsvImportRejected(
                "binary_input_required",
                "CSV file-like inputs must return bytes.",
            )
        if not chunk:
            break
        binary_chunk = bytes(chunk)
        chunks.append(binary_chunk)
        total += len(binary_chunk)
        if total > maximum:
            raise CsvImportRejected(
                "byte_limit_exceeded",
                "The CSV file is larger than the configured byte limit.",
            )
    return b"".join(chunks)


def _decode_utf8(payload: bytes) -> str:
    if not payload:
        raise CsvImportRejected("empty_file", "The CSV file is empty.")
    if any(payload.startswith(marker) for marker in _KNOWN_BOMS):
        raise CsvImportRejected(
            "bom_not_allowed",
            "CSV files must use UTF-8 without a byte-order mark.",
        )
    if b"\x00" in payload:
        raise CsvImportRejected("nul_byte", "CSV files cannot contain NUL bytes.")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CsvImportRejected("invalid_utf8", "CSV files must use valid UTF-8.") from exc
    if "\ufeff" in text or "\ufffe" in text:
        raise CsvImportRejected(
            "bom_not_allowed",
            "CSV files cannot contain embedded byte-order marks.",
        )
    return text


def _validate_headers(
    headers: tuple[str, ...],
    expected: tuple[str, ...],
    maximum_columns: int,
) -> None:
    if not headers or all(not header for header in headers):
        raise CsvImportRejected("empty_file", "The CSV file does not contain a header row.")
    if len(headers) > maximum_columns:
        raise CsvImportRejected(
            "column_limit_exceeded",
            "The CSV header contains more columns than allowed.",
        )
    if len(set(headers)) != len(headers):
        raise CsvImportRejected(
            "duplicate_headers",
            "CSV header names cannot be duplicated.",
        )
    if headers != expected:
        raise CsvImportRejected(
            "unexpected_headers",
            "CSV headers must exactly match the selected version 1 English template.",
        )


def _sanitize_cells(
    raw_row: list[str],
    headers: tuple[str, ...],
    *,
    row_number: int,
    limits: CsvImportLimits,
    formulas: _FormulaCollector,
) -> tuple[dict[str, str], list[_PendingError]]:
    cells: dict[str, str] = {}
    errors: list[_PendingError] = []
    for column, raw_value in zip(headers, raw_row, strict=True):
        candidate = raw_value.lstrip()
        if candidate and candidate[0] in _FORMULA_PREFIXES:
            formulas.add(row_number, column)
        if len(raw_value) > limits.max_field_chars:
            errors.append(
                _error(
                    column,
                    "field_limit_exceeded",
                    "The field contains more characters than allowed.",
                )
            )
        if _CONTROL_CHARACTER_PATTERN.search(raw_value) is not None:
            errors.append(
                _error(
                    column,
                    "control_character_not_allowed",
                    "The field contains a control character that is not allowed.",
                )
            )
        cells[column] = raw_value.strip()
    return cells, errors


def _parse_row(
    kind: CsvImportKind,
    cells: Mapping[str, str],
    row_number: int,
) -> tuple[CsvPreviewRow | None, list[_PendingError]]:
    if kind is CsvImportKind.CUSTOMERS:
        return _parse_customer(cells, row_number)
    if kind is CsvImportKind.PRODUCTS:
        return _parse_product(cells, row_number)
    return _parse_order(cells, row_number)


def _parse_customer(
    cells: Mapping[str, str], row_number: int
) -> tuple[CustomerCsvRow | None, list[_PendingError]]:
    errors: list[_PendingError] = []
    external_id = _reference(cells, "external_id", errors, maximum=120)
    name = _text(cells, "name", errors, required=True, maximum=160)
    email = _email(cells, "email", errors)
    company = _text(cells, "company", errors, required=False, maximum=160)
    status = _enum(cells, "status", errors, _CUSTOMER_STATUSES)
    acquired_at = _timestamp(cells, "acquired_at", errors)
    if errors:
        return None, errors
    assert external_id is not None
    assert name is not None
    assert status is not None
    assert acquired_at is not None
    return (
        CustomerCsvRow(
            row_number=row_number,
            external_id=external_id,
            name=name,
            email=email,
            company=company,
            status=cast(CustomerStatus, status),
            acquired_at=acquired_at,
        ),
        [],
    )


def _parse_product(
    cells: Mapping[str, str], row_number: int
) -> tuple[ProductCsvRow | None, list[_PendingError]]:
    errors: list[_PendingError] = []
    external_id = _reference(cells, "external_id", errors, maximum=120)
    sku = _reference(cells, "sku", errors, maximum=80, uppercase=True)
    name = _text(cells, "name", errors, required=True, maximum=180)
    category = _text(cells, "category", errors, required=True, maximum=100)
    unit_price_minor = _money(cells, "unit_price", errors)
    status = _enum(cells, "status", errors, _PRODUCT_STATUSES)
    if errors:
        return None, errors
    assert external_id is not None
    assert sku is not None
    assert name is not None
    assert category is not None
    assert unit_price_minor is not None
    assert status is not None
    return (
        ProductCsvRow(
            row_number=row_number,
            external_id=external_id,
            sku=sku,
            name=name,
            category=category,
            unit_price_minor=unit_price_minor,
            status=cast(ProductStatus, status),
        ),
        [],
    )


def _parse_order(
    cells: Mapping[str, str], row_number: int
) -> tuple[OrderCsvRow | None, list[_PendingError]]:
    errors: list[_PendingError] = []
    external_id = _reference(cells, "external_id", errors, maximum=120)
    order_number = _reference(cells, "order_number", errors, maximum=80)
    customer_external_id = _reference(cells, "customer_external_id", errors, maximum=120)
    status = _enum(cells, "status", errors, _ORDER_STATUSES)
    ordered_at = _timestamp(cells, "ordered_at", errors)
    currency = _currency(cells, "currency", errors)
    product_sku = _reference(cells, "product_sku", errors, maximum=80, uppercase=True)
    quantity = _positive_integer(cells, "quantity", errors, maximum=10_000)
    unit_price_minor = _money(cells, "unit_price", errors)
    discount_minor = _money(cells, "discount", errors)
    tax_minor = _money(cells, "tax", errors)
    if errors:
        return None, errors
    assert external_id is not None
    assert order_number is not None
    assert customer_external_id is not None
    assert status is not None
    assert ordered_at is not None
    assert currency is not None
    assert product_sku is not None
    assert quantity is not None
    assert unit_price_minor is not None
    assert discount_minor is not None
    assert tax_minor is not None
    return (
        OrderCsvRow(
            row_number=row_number,
            external_id=external_id,
            order_number=order_number,
            customer_external_id=customer_external_id,
            status=cast(OrderStatus, status),
            ordered_at=ordered_at,
            currency=currency,
            product_sku=product_sku,
            quantity=quantity,
            unit_price_minor=unit_price_minor,
            discount_minor=discount_minor,
            tax_minor=tax_minor,
        ),
        [],
    )


def _text(
    cells: Mapping[str, str],
    column: str,
    errors: list[_PendingError],
    *,
    required: bool,
    maximum: int,
) -> str | None:
    value = cells[column]
    if not value:
        if required:
            errors.append(_error(column, "required", "This field is required."))
        return None
    if len(value) > maximum:
        errors.append(_error(column, "field_too_long", "This field exceeds its documented length."))
        return None
    return " ".join(value.split())


def _reference(
    cells: Mapping[str, str],
    column: str,
    errors: list[_PendingError],
    *,
    maximum: int,
    uppercase: bool = False,
) -> str | None:
    value = _text(cells, column, errors, required=True, maximum=maximum)
    if value is None:
        return None
    normalized = value.upper() if uppercase else value
    if _REFERENCE_PATTERN.fullmatch(normalized) is None:
        errors.append(
            _error(
                column,
                "invalid_reference",
                "References may contain only letters, numbers, dots, underscores, and hyphens.",
            )
        )
        return None
    return normalized


def _email(
    cells: Mapping[str, str],
    column: str,
    errors: list[_PendingError],
) -> str | None:
    value = _text(cells, column, errors, required=False, maximum=320)
    if value is None:
        return None
    try:
        result = validate_email(
            value,
            check_deliverability=False,
            test_environment=True,
        )
    except EmailNotValidError:
        errors.append(_error(column, "invalid_email", "Enter a valid email address."))
        return None
    return str(result.normalized)


def _enum(
    cells: Mapping[str, str],
    column: str,
    errors: list[_PendingError],
    allowed: frozenset[str],
) -> str | None:
    value = _text(cells, column, errors, required=True, maximum=32)
    if value is None:
        return None
    if value not in allowed:
        errors.append(
            _error(column, "invalid_enum", "Choose one of the documented English values.")
        )
        return None
    return value


def _timestamp(
    cells: Mapping[str, str],
    column: str,
    errors: list[_PendingError],
) -> datetime | None:
    value = _text(cells, column, errors, required=True, maximum=64)
    if value is None:
        return None
    if "T" not in value:
        errors.append(
            _error(column, "invalid_timestamp", "Use an ISO 8601 timestamp with a UTC offset.")
        )
        return None
    candidate = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        errors.append(
            _error(column, "invalid_timestamp", "Use an ISO 8601 timestamp with a UTC offset.")
        )
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(_error(column, "timezone_required", "Timestamps must include a UTC offset."))
        return None
    return parsed.astimezone(UTC)


def _money(
    cells: Mapping[str, str],
    column: str,
    errors: list[_PendingError],
) -> int | None:
    value = _text(cells, column, errors, required=True, maximum=32)
    if value is None:
        return None
    if _MONEY_PATTERN.fullmatch(value) is None:
        errors.append(
            _error(
                column,
                "invalid_money",
                "Use a non-negative decimal with exactly two minor-unit digits.",
            )
        )
        return None
    try:
        amount = Decimal(value)
    except InvalidOperation:
        errors.append(_error(column, "invalid_money", "The monetary value is invalid."))
        return None
    minor_units = int(amount * 100)
    if minor_units > MAX_MONEY_MINOR:
        errors.append(
            _error(column, "money_limit_exceeded", "The monetary value exceeds the allowed range.")
        )
        return None
    return minor_units


def _positive_integer(
    cells: Mapping[str, str],
    column: str,
    errors: list[_PendingError],
    *,
    maximum: int,
) -> int | None:
    value = _text(cells, column, errors, required=True, maximum=16)
    if value is None:
        return None
    if _POSITIVE_INTEGER_PATTERN.fullmatch(value) is None:
        errors.append(_error(column, "invalid_integer", "Use a positive whole number."))
        return None
    parsed = int(value)
    if parsed > maximum:
        errors.append(
            _error(column, "integer_limit_exceeded", "The value exceeds the allowed range.")
        )
        return None
    return parsed


def _currency(
    cells: Mapping[str, str],
    column: str,
    errors: list[_PendingError],
) -> str | None:
    value = _text(cells, column, errors, required=True, maximum=3)
    if value is None:
        return None
    if _CURRENCY_PATTERN.fullmatch(value) is None:
        errors.append(
            _error(column, "invalid_currency", "Use a three-letter uppercase currency code.")
        )
        return None
    return value


def _error(column: str | None, code: str, message: str) -> _PendingError:
    return _PendingError(column=column, code=code, message=message)
