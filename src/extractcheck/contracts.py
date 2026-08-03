"""Small normalized-unit contract with typed source provenance."""
from __future__ import annotations

from typing import Any


LANES = frozenset({"baseline", "candidate", "synthetic-control"})
SOURCE_KINDS = frozenset({"document", "attachment", "synthetic"})
UNIT_TYPES = frozenset({
    "document", "sheet", "cell", "row", "table", "chart", "slide",
    "shape", "page", "block", "image", "paragraph",
})
STATUSES = frozenset({"ok", "partial", "unsupported", "failed"})
WARNING_CODES = frozenset({
    "flattened_provenance", "native_locators_retained", "partial_output",
    "structure_only_pdf_census",
})


class ContractError(ValueError):
    """Raised when a normalized unit lacks required typed provenance."""


def validate_unit(unit: dict[str, Any]) -> None:
    required = {
        "schema_version", "run_id", "sample_id", "source_kind",
        "source_sha256", "lane", "unit_id", "unit_type", "locator",
        "content_hashes", "status", "warnings",
    }
    if required.difference(unit):
        raise ContractError("unit is missing required fields")
    if unit["schema_version"] != 1:
        raise ContractError("unsupported schema version")
    if unit["lane"] not in LANES or unit["source_kind"] not in SOURCE_KINDS:
        raise ContractError("unknown lane or source kind")
    if unit["unit_type"] not in UNIT_TYPES or unit["status"] not in STATUSES:
        raise ContractError("unknown unit type or status")
    if not isinstance(unit["locator"], dict) or not isinstance(unit["content_hashes"], dict):
        raise ContractError("locator and content_hashes must be objects")
    if not isinstance(unit["warnings"], list) or any(code not in WARNING_CODES for code in unit["warnings"]):
        raise ContractError("warnings must contain only allowlisted codes")
    source_hash = unit["source_sha256"]
    if not isinstance(source_hash, str) or len(source_hash) != 64:
        raise ContractError("source_sha256 must be a complete SHA-256")
    _validate_locator(unit["unit_type"], unit["locator"], unit["status"])


def _validate_locator(unit_type: str, locator: dict[str, Any], status: str) -> None:
    if status in {"unsupported", "failed"}:
        return
    if unit_type in {"sheet", "cell", "row"}:
        if not isinstance(locator.get("sheet_index"), int):
            raise ContractError("spreadsheet unit requires sheet_index")
        if unit_type == "cell" and not (locator.get("cell") or locator.get("range")):
            raise ContractError("cell unit requires cell or range")
    if unit_type in {"slide", "shape"}:
        if not isinstance(locator.get("slide_number"), int):
            raise ContractError("presentation unit requires slide_number")
        if unit_type == "shape" and locator.get("shape_id") is None:
            raise ContractError("shape unit requires shape_id")
    if unit_type in {"page", "block"}:
        if not isinstance(locator.get("page_number"), int):
            raise ContractError("PDF unit requires page_number")
        if unit_type == "block" and not ({"bbox", "block_index"} & locator.keys()):
            raise ContractError("PDF block requires bbox or block_index")
