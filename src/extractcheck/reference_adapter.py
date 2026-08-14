"""Small, dependency-free adapter used to demonstrate the public contract."""
from __future__ import annotations

from pathlib import Path
import posixpath
import re
from typing import Any
from xml.etree import ElementTree as ET
import zipfile

from .contracts import validate_unit
from .safety import SafetyViolation, source_read_guard


REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
MAX_ZIP_MEMBERS = 10_000
MAX_ZIP_EXPANDED_BYTES = 512 * 1024 * 1024
MAX_XML_MEMBER_BYTES = 128 * 1024 * 1024


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _safe_archive(path: Path) -> zipfile.ZipFile:
    archive = zipfile.ZipFile(path)
    members = archive.infolist()
    unsafe = any(
        posixpath.normpath(member.filename).startswith("../")
        or member.filename.startswith("/")
        or member.flag_bits & 0x1
        for member in members
    )
    if unsafe or len(members) > MAX_ZIP_MEMBERS:
        archive.close()
        raise SafetyViolation("unsafe OOXML archive")
    if sum(member.file_size for member in members) > MAX_ZIP_EXPANDED_BYTES:
        archive.close()
        raise SafetyViolation("OOXML expanded-size limit exceeded")
    return archive


def _xml(archive: zipfile.ZipFile, member: str) -> ET.Element:
    try:
        if archive.getinfo(member).file_size > MAX_XML_MEMBER_BYTES:
            raise SafetyViolation("OOXML member exceeds the expanded-size limit")
        return ET.fromstring(archive.read(member))
    except KeyError as error:
        raise SafetyViolation("required OOXML member is missing") from error


def _relationships(archive: zipfile.ZipFile, member: str) -> dict[str, str]:
    return {
        str(node.get("Id")): str(node.get("Target", ""))
        for node in _xml(archive, member)
        if _local(node.tag) == "Relationship" and node.get("Id")
    }


def _target(base: str, target: str, names: set[str]) -> str:
    member = posixpath.normpath(posixpath.join(posixpath.dirname(base), target.lstrip("/")))
    if member.startswith("../") or member not in names:
        raise SafetyViolation("invalid OOXML relationship target")
    return member


def _shape_id(node: ET.Element) -> int | None:
    for child in node.iter():
        if _local(child.tag) == "cNvPr" and str(child.get("id", "")).isdigit():
            return int(str(child.get("id")))
    return None


def _unit(
    *,
    run_id: str,
    sample_id: str,
    source_sha256: str,
    index: int,
    unit_type: str,
    locator: dict[str, Any],
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    unit: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "sample_id": sample_id,
        "source_kind": "synthetic",
        "source_sha256": source_sha256,
        "lane": "baseline",
        "unit_id": f"{unit_type}:{index}",
        "unit_type": unit_type,
        "locator": locator,
        "content_hashes": {},
        "status": "ok",
        "warnings": [],
    }
    if attributes:
        unit["attributes"] = attributes
    validate_unit(unit)
    return unit


def _xlsx_units(
    path: Path, run_id: str, sample_id: str, source_sha256: str
) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    with _safe_archive(path) as archive:
        names = set(archive.namelist())
        workbook = _xml(archive, "xl/workbook.xml")
        relationships = _relationships(archive, "xl/_rels/workbook.xml.rels")
        for sheet_index, sheet in enumerate(
            node for node in workbook.iter() if _local(node.tag) == "sheet"
        ):
            relationship_id = str(sheet.get(f"{{{REL_NS}}}id"))
            member = _target(
                "xl/workbook.xml", relationships.get(relationship_id, ""), names
            )
            units.append(_unit(
                run_id=run_id,
                sample_id=sample_id,
                source_sha256=source_sha256,
                index=len(units),
                unit_type="sheet",
                locator={"sheet_index": sheet_index},
                attributes={"visibility": str(sheet.get("state", "visible"))},
            ))
            root = _xml(archive, member)
            for cell in (node for node in root.iter() if _local(node.tag) == "c"):
                units.append(_unit(
                    run_id=run_id,
                    sample_id=sample_id,
                    source_sha256=source_sha256,
                    index=len(units),
                    unit_type="cell",
                    locator={"sheet_index": sheet_index, "cell": str(cell.get("r", ""))},
                    attributes={
                        "formula": any(_local(child.tag) == "f" for child in cell)
                    },
                ))
        for unit_type, pattern in (
            ("table", r"xl/tables/[^/]+\.xml"),
            ("chart", r"xl/charts/[^/]+\.xml"),
        ):
            for member_index, _member in enumerate(
                sorted(name for name in names if re.fullmatch(pattern, name))
            ):
                units.append(_unit(
                    run_id=run_id,
                    sample_id=sample_id,
                    source_sha256=source_sha256,
                    index=len(units),
                    unit_type=unit_type,
                    locator={"member_index": member_index},
                ))
    return units


def _pptx_units(
    path: Path, run_id: str, sample_id: str, source_sha256: str
) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    with _safe_archive(path) as archive:
        names = set(archive.namelist())
        presentation = _xml(archive, "ppt/presentation.xml")
        relationships = _relationships(archive, "ppt/_rels/presentation.xml.rels")
        slide_ids = [node for node in presentation.iter() if _local(node.tag) == "sldId"]
        for slide_number, slide_id in enumerate(slide_ids, 1):
            relationship_id = str(slide_id.get(f"{{{REL_NS}}}id"))
            member = _target(
                "ppt/presentation.xml", relationships.get(relationship_id, ""), names
            )
            units.append(_unit(
                run_id=run_id,
                sample_id=sample_id,
                source_sha256=source_sha256,
                index=len(units),
                unit_type="slide",
                locator={"slide_number": slide_number},
            ))
            root = _xml(archive, member)
            shapes = [
                node for node in root.iter()
                if _local(node.tag) in {"sp", "graphicFrame", "pic", "grpSp"}
            ]
            for shape in shapes:
                shape_id = _shape_id(shape)
                if shape_id is None:
                    continue
                units.append(_unit(
                    run_id=run_id,
                    sample_id=sample_id,
                    source_sha256=source_sha256,
                    index=len(units),
                    unit_type="shape",
                    locator={"slide_number": slide_number, "shape_id": shape_id},
                ))
            for _table in (node for node in root.iter() if _local(node.tag) == "tbl"):
                units.append(_unit(
                    run_id=run_id,
                    sample_id=sample_id,
                    source_sha256=source_sha256,
                    index=len(units),
                    unit_type="table",
                    locator={"slide_number": slide_number},
                ))
        for member_index, _member in enumerate(
            sorted(name for name in names if re.fullmatch(r"ppt/charts/[^/]+\.xml", name))
        ):
            units.append(_unit(
                run_id=run_id,
                sample_id=sample_id,
                source_sha256=source_sha256,
                index=len(units),
                unit_type="chart",
                locator={"member_index": member_index},
            ))
    return units


def _docx_units(
    path: Path, run_id: str, sample_id: str, source_sha256: str
) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    with _safe_archive(path) as archive:
        root = _xml(archive, "word/document.xml")
        for paragraph_index, _paragraph in enumerate(
            node for node in root.iter() if _local(node.tag) == "p"
        ):
            units.append(_unit(
                run_id=run_id,
                sample_id=sample_id,
                source_sha256=source_sha256,
                index=len(units),
                unit_type="paragraph",
                locator={"paragraph_index": paragraph_index},
            ))
        for table_index, _table in enumerate(
            node for node in root.iter() if _local(node.tag) == "tbl"
        ):
            units.append(_unit(
                run_id=run_id,
                sample_id=sample_id,
                source_sha256=source_sha256,
                index=len(units),
                unit_type="table",
                locator={"table_index": table_index},
            ))
    return units


def _pdf_units(
    path: Path, run_id: str, sample_id: str, source_sha256: str
) -> list[dict[str, Any]]:
    page_count = len(re.findall(rb"/Type\s*/Page\b", path.read_bytes()))
    if not page_count:
        raise ValueError("no PDF page objects found by the reference adapter")
    return [
        _unit(
            run_id=run_id,
            sample_id=sample_id,
            source_sha256=source_sha256,
            index=page_number - 1,
            unit_type="page",
            locator={"page_number": page_number},
        )
        for page_number in range(1, page_count + 1)
    ]


def extract_reference(
    path: Path,
    *,
    run_id: str,
    sample_id: str,
    max_source_bytes: int = 250 * 1024 * 1024,
) -> list[dict[str, Any]]:
    """Return normalized structural units without retaining source text or values."""
    with source_read_guard(path) as identity:
        if identity.size > max_source_bytes:
            raise SafetyViolation("source exceeds the configured size limit")
        parsers = {
            ".xlsx": _xlsx_units,
            ".pptx": _pptx_units,
            ".docx": _docx_units,
            ".pdf": _pdf_units,
        }
        try:
            parser = parsers[path.suffix.lower()]
        except KeyError as error:
            raise ValueError("unsupported format") from error
        return parser(path, run_id, sample_id, identity.sha256)
