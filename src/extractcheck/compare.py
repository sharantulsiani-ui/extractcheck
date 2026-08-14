"""Compare the reference adapter with the independent synthetic census."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .census import census_file
from .evaluate import PRIVATE_SENTINELS, canonical_json
from .fixtures import build_all
from .reference_adapter import extract_reference
from .safety import atomic_json, deny_python_network, secure_directory


def _count(units: list[dict[str, Any]], unit_type: str) -> int:
    return sum(unit["unit_type"] == unit_type for unit in units)


def _score(expected: int, recovered: int) -> dict[str, Any]:
    return {
        "expected": expected,
        "recovered": recovered,
        "recall": 1.0 if expected == recovered else recovered / expected if expected else 0.0,
        "status": "pass" if expected == recovered else "fail",
    }


def _metrics(
    kind: str,
    structure: dict[str, Any],
    units: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if kind == "xlsx":
        expected = {
            "sheets": structure["sheet_count"],
            "cells": sum(sheet["cell_nodes"] for sheet in structure["sheets"]),
            "formula_cells": sum(sheet["formula_cells"] for sheet in structure["sheets"]),
            "tables": structure["table_count"],
            "charts": structure["chart_count"],
        }
        recovered = {
            "sheets": _count(units, "sheet"),
            "cells": _count(units, "cell"),
            "formula_cells": sum(
                unit["unit_type"] == "cell" and unit.get("attributes", {}).get("formula") is True
                for unit in units
            ),
            "tables": _count(units, "table"),
            "charts": _count(units, "chart"),
        }
    elif kind == "pptx":
        expected = {
            "slides": structure["slide_count"],
            "shapes": sum(len(slide["shape_ids"]) for slide in structure["slides"]),
            "tables": structure["table_count"],
            "charts": structure["chart_count"],
        }
        recovered = {
            "slides": _count(units, "slide"),
            "shapes": _count(units, "shape"),
            "tables": _count(units, "table"),
            "charts": _count(units, "chart"),
        }
    elif kind == "pdf":
        expected = {"pages": structure["page_count"]}
        recovered = {"pages": _count(units, "page")}
    else:
        expected = {
            "paragraphs": structure["paragraph_count"],
            "tables": structure["table_count"],
        }
        recovered = {
            "paragraphs": _count(units, "paragraph"),
            "tables": _count(units, "table"),
        }
    return {name: _score(value, recovered[name]) for name, value in expected.items()}


def build_reference_comparison(output_root: Path) -> dict[str, Any]:
    root = secure_directory(output_root)
    fixtures = secure_directory(root / "fixtures")
    build_all(fixtures)
    formats: dict[str, Any] = {}
    with deny_python_network() as attempts:
        for kind in ("xlsx", "pptx", "pdf", "docx"):
            path = fixtures / f"synthetic.{kind}"
            census = census_file(path)
            units = extract_reference(
                path,
                run_id="synthetic-reference",
                sample_id=f"SYN-{kind.upper()}",
            )
            metrics = _metrics(kind, census["structure"], units)
            formats[kind] = {
                "source_sha256": census["source_sha256"],
                "source_identity_unchanged": census["source_identity_unchanged"],
                "normalized_units": len(units),
                "metrics": metrics,
                "status": (
                    "pass"
                    if all(row["status"] == "pass" for row in metrics.values())
                    else "fail"
                ),
            }
    report: dict[str, Any] = {
        "schema_version": 1,
        "mode": "synthetic_reference_comparison",
        "adapter": "extractcheck.reference_adapter",
        "formats": formats,
        "all_passed": all(row["status"] == "pass" for row in formats.values()),
        "network_attempts": len(attempts),
        "private_sources_opened": 0,
        "index_or_graph_writes": 0,
    }
    serialized = canonical_json(report)
    if any(value in serialized for value in PRIVATE_SENTINELS):
        raise RuntimeError("synthetic content escaped into the comparison report")
    report["report_sha256"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    atomic_json(root / "comparison.json", report)
    return report
