"""Independent structure-only census for OOXML and PDF inputs."""
from __future__ import annotations

from pathlib import Path
import posixpath
import re
from typing import Any
from xml.etree import ElementTree as ET
import zipfile

from .safety import SafetyViolation, source_read_guard


REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
MAX_ZIP_MEMBERS = 10_000
MAX_ZIP_EXPANDED_BYTES = 512 * 1024 * 1024
MAX_XML_MEMBER_BYTES = 128 * 1024 * 1024


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xml(archive: zipfile.ZipFile, member: str) -> ET.Element:
    if archive.getinfo(member).file_size > MAX_XML_MEMBER_BYTES:
        raise SafetyViolation("OOXML member exceeds the expanded-size limit")
    with archive.open(member) as handle:
        return ET.parse(handle).getroot()


def _relationships(archive: zipfile.ZipFile, member: str) -> dict[str, str]:
    if member not in archive.namelist():
        return {}
    return {
        str(node.get("Id")): str(node.get("Target", ""))
        for node in _xml(archive, member)
        if _local(node.tag) == "Relationship" and node.get("Id")
    }


def _target(base: str, target: str, names: set[str]) -> str:
    member = posixpath.normpath(posixpath.join(posixpath.dirname(base), target.lstrip("/")))
    if member.startswith("../") or member not in names:
        raise SafetyViolation("invalid or missing OOXML relationship target")
    return member


def _validate_zip(archive: zipfile.ZipFile) -> None:
    members = archive.infolist()
    if len(members) > MAX_ZIP_MEMBERS:
        raise SafetyViolation("OOXML member-count limit exceeded")
    if sum(member.file_size for member in members) > MAX_ZIP_EXPANDED_BYTES:
        raise SafetyViolation("OOXML expanded-size limit exceeded")
    for member in members:
        normalized = posixpath.normpath(member.filename)
        if normalized.startswith("../") or normalized.startswith("/") or member.flag_bits & 0x1:
            raise SafetyViolation("unsafe OOXML member")


def census_xlsx(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        _validate_zip(archive)
        names = set(archive.namelist())
        workbook = _xml(archive, "xl/workbook.xml")
        relationships = _relationships(archive, "xl/_rels/workbook.xml.rels")
        sheets: list[dict[str, Any]] = []
        for sheet_index, sheet in enumerate(node for node in workbook.iter() if _local(node.tag) == "sheet"):
            relationship_id = str(sheet.get(f"{{{REL_NS}}}id"))
            member = _target("xl/workbook.xml", relationships.get(relationship_id, ""), names)
            root = _xml(archive, member)
            cells = [node for node in root.iter() if _local(node.tag) == "c"]
            sheets.append({
                "sheet_index": sheet_index,
                "visibility": str(sheet.get("state", "visible")),
                "cell_nodes": len(cells),
                "formula_cells": sum(any(_local(child.tag) == "f" for child in cell) for cell in cells),
                "merged_ranges": sum(_local(node.tag) == "mergeCell" for node in root.iter()),
            })
        return {
            "format": "xlsx",
            "sheet_count": len(sheets),
            "hidden_sheet_count": sum(row["visibility"] != "visible" for row in sheets),
            "sheets": sheets,
            "table_count": sum(bool(re.fullmatch(r"xl/tables/[^/]+\.xml", name)) for name in names),
            "chart_count": sum(bool(re.fullmatch(r"xl/charts/[^/]+\.xml", name)) for name in names),
            "image_count": sum(name.startswith("xl/media/") and not name.endswith("/") for name in names),
            "value_nodes_persisted": 0,
            "formula_text_persisted": 0,
        }


def _shape_id(node: ET.Element) -> int | None:
    for child in node.iter():
        if _local(child.tag) == "cNvPr" and str(child.get("id", "")).isdigit():
            return int(str(child.get("id")))
    return None


def census_pptx(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        _validate_zip(archive)
        names = set(archive.namelist())
        presentation = _xml(archive, "ppt/presentation.xml")
        relationships = _relationships(archive, "ppt/_rels/presentation.xml.rels")
        slides: list[dict[str, Any]] = []
        slide_ids = [node for node in presentation.iter() if _local(node.tag) == "sldId"]
        for slide_number, slide_id in enumerate(slide_ids, 1):
            relationship_id = str(slide_id.get(f"{{{REL_NS}}}id"))
            member = _target("ppt/presentation.xml", relationships.get(relationship_id, ""), names)
            root = _xml(archive, member)
            shapes = [node for node in root.iter() if _local(node.tag) in {"sp", "graphicFrame", "pic", "grpSp"}]
            slides.append({
                "slide_number": slide_number,
                "shape_ids": [_shape_id(node) for node in shapes],
                "text_node_count": sum(_local(node.tag) == "t" for node in root.iter()),
                "table_count": sum(_local(node.tag) == "tbl" for node in root.iter()),
                "table_cell_count": sum(_local(node.tag) == "tc" for node in root.iter()),
            })
        return {
            "format": "pptx",
            "slide_count": len(slides),
            "slides": slides,
            "table_count": sum(row["table_count"] for row in slides),
            "table_cell_count": sum(row["table_cell_count"] for row in slides),
            "chart_count": sum(bool(re.fullmatch(r"ppt/charts/[^/]+\.xml", name)) for name in names),
            "image_count": sum(name.startswith("ppt/media/") and not name.endswith("/") for name in names),
            "text_values_persisted": 0,
            "chart_values_persisted": 0,
        }


def census_docx(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        _validate_zip(archive)
        root = _xml(archive, "word/document.xml")
        return {
            "format": "docx",
            "paragraph_count": sum(_local(node.tag) == "p" for node in root.iter()),
            "table_count": sum(_local(node.tag) == "tbl" for node in root.iter()),
            "table_cell_count": sum(_local(node.tag) == "tc" for node in root.iter()),
            "text_values_persisted": 0,
        }


def census_pdf(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    page_count = len(re.findall(rb"/Type\s*/Page\b", payload))
    if not page_count:
        raise ValueError("no PDF page objects found by the structure-only parser")
    return {
        "format": "pdf",
        "page_count": page_count,
        "page_locators": [{"page_number": number} for number in range(1, page_count + 1)],
        "parser": "dependency_free_page_object_census",
        "warning": "structure_only_pdf_census",
        "text_values_persisted": 0,
    }


def census_file(path: Path, *, max_source_bytes: int = 250 * 1024 * 1024) -> dict[str, Any]:
    with source_read_guard(path) as identity:
        if identity.size > max_source_bytes:
            raise SafetyViolation("source exceeds the configured size limit")
        suffix = path.suffix.lower()
        parsers = {".xlsx": census_xlsx, ".pptx": census_pptx, ".pdf": census_pdf, ".docx": census_docx}
        if suffix not in parsers:
            raise ValueError("unsupported format")
        structure = parsers[suffix](path)
    return {
        "schema_version": 1,
        "source_sha256": identity.sha256,
        "source_size_bytes": identity.size,
        "source_identity_unchanged": True,
        "structure": structure,
    }
