"""Synthetic-only end-to-end proof for the public package."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .census import census_file
from .fixtures import build_all
from .safety import atomic_json, deny_python_network, secure_directory


PRIVATE_SENTINELS = (
    "SYNTH-XLSX-HEADER", "SYNTH-XLSX-HIDDEN", "SYNTH-PPTX-SLIDE",
    "SYNTH-PPTX-CELL", "SYNTH-PDF-PAGE", "SYNTH-DOCX-PARAGRAPH",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_synthetic_report(output_root: Path) -> dict[str, Any]:
    root = secure_directory(output_root)
    fixtures = secure_directory(root / "fixtures")
    manifest = build_all(fixtures)
    expected = manifest["expected"]
    results: dict[str, dict[str, Any]] = {}
    with deny_python_network() as attempts:
        for kind in ("xlsx", "pptx", "pdf", "docx"):
            result = census_file(fixtures / f"synthetic.{kind}")
            structure = result["structure"]
            checks: dict[str, bool]
            if kind == "xlsx":
                checks = {
                    "sheets": structure["sheet_count"] == expected[kind]["sheets"],
                    "hidden_sheets": structure["hidden_sheet_count"] == expected[kind]["hidden_sheets"],
                    "formula_cells": sum(row["formula_cells"] for row in structure["sheets"]) == expected[kind]["formula_cells"],
                    "tables": structure["table_count"] == expected[kind]["tables"],
                    "charts": structure["chart_count"] == expected[kind]["charts"],
                }
            elif kind == "pptx":
                checks = {
                    "slides": structure["slide_count"] == expected[kind]["slides"],
                    "tables": structure["table_count"] == expected[kind]["tables"],
                    "table_cells": structure["table_cell_count"] == expected[kind]["table_cells"],
                    "charts": structure["chart_count"] == expected[kind]["charts"],
                }
            elif kind == "pdf":
                checks = {"pages": structure["page_count"] == expected[kind]["pages"]}
            else:
                checks = {
                    "paragraphs": structure["paragraph_count"] == expected[kind]["paragraphs"],
                    "table_cells": structure["table_cell_count"] == expected[kind]["table_cells"],
                }
            results[kind] = {
                "source_sha256": result["source_sha256"],
                "source_size_bytes": result["source_size_bytes"],
                "source_identity_unchanged": result["source_identity_unchanged"],
                "checks": checks,
                "status": "pass" if all(checks.values()) else "fail",
            }
    report: dict[str, Any] = {
        "schema_version": 1,
        "mode": "synthetic_only",
        "formats": results,
        "all_passed": all(row["status"] == "pass" for row in results.values()),
        "network_attempts": len(attempts),
        "ocr_runs": 0,
        "index_or_graph_writes": 0,
    }
    serialized = canonical_json(report)
    if any(value in serialized for value in PRIVATE_SENTINELS):
        raise RuntimeError("synthetic content escaped into the hash-only report")
    report["report_sha256"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    atomic_json(root / "report.json", report)
    return report
