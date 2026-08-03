"""Dependency-free synthetic OOXML and PDF fixtures."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import zipfile

from .safety import secure_directory


def _zip(path: Path, members: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, members[name].encode("utf-8"))
    os.chmod(path, 0o600)


def _types(overrides: list[tuple[str, str]]) -> str:
    body = "".join(
        f'<Override PartName="/{part}" ContentType="{kind}"/>' for part, kind in overrides
    )
    return (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f"{body}</Types>"
    )


def build_xlsx(path: Path) -> None:
    _zip(path, {
        "[Content_Types].xml": _types([
            ("xl/workbook.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"),
            ("xl/worksheets/sheet1.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"),
            ("xl/worksheets/sheet2.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"),
            ("xl/charts/chart1.xml", "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"),
            ("xl/tables/table1.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"),
        ]),
        "_rels/.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        ),
        "xl/workbook.xml": (
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Visible" sheetId="1" r:id="rId1"/>'
            '<sheet name="Hidden" sheetId="2" state="hidden" r:id="rId2"/></sheets>'
            '<definedNames><definedName name="SYNTH_RANGE">Visible!$A$1:$B$2</definedName></definedNames>'
            "</workbook>"
        ),
        "xl/_rels/workbook.xml.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="worksheet" Target="worksheets/sheet2.xml"/>'
            "</Relationships>"
        ),
        "xl/worksheets/sheet1.xml": (
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<dimension ref="A1:B2"/><sheetData><row r="1">'
            '<c r="A1" t="inlineStr"><is><t>SYNTH-XLSX-HEADER</t></is></c><c r="B1"><v>7</v></c>'
            '</row><row r="2"><c r="A2"><v>3</v></c><c r="B2"><f>A2*2</f><v>6</v></c>'
            '</row></sheetData><mergeCells count="1"><mergeCell ref="A1:B1"/></mergeCells>'
            '<tableParts count="1"><tablePart r:id="rId1"/></tableParts><drawing r:id="rId2"/>'
            "</worksheet>"
        ),
        "xl/worksheets/sheet2.xml": (
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<dimension ref="A1"/><sheetData><row r="1"><c r="A1" t="inlineStr">'
            '<is><t>SYNTH-XLSX-HIDDEN</t></is></c></row></sheetData></worksheet>'
        ),
        "xl/tables/table1.xml": (
            '<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'id="1" name="SYNTH_TABLE" ref="A1:B2"><tableColumns count="2">'
            '<tableColumn id="1" name="Header"/><tableColumn id="2" name="Value"/>'
            "</tableColumns></table>"
        ),
        "xl/charts/chart1.xml": (
            '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart">'
            '<c:chart><c:plotArea><c:barChart><c:ser><c:idx val="0"/><c:val><c:numLit>'
            '<c:pt idx="0"><c:v>6</c:v></c:pt></c:numLit></c:val></c:ser></c:barChart>'
            "</c:plotArea></c:chart></c:chartSpace>"
        ),
    })


def build_pptx(path: Path) -> None:
    slide_one = (
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree>'
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="text"/></p:nvSpPr><p:txBody><a:p><a:r>'
        '<a:t>SYNTH-PPTX-SLIDE-1</a:t></a:r></a:p></p:txBody></p:sp>'
        '<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="3" name="table"/></p:nvGraphicFramePr>'
        '<a:graphic><a:graphicData><a:tbl><a:tr><a:tc><a:txBody><a:p><a:r>'
        '<a:t>SYNTH-PPTX-CELL</a:t></a:r></a:p></a:txBody></a:tc></a:tr></a:tbl>'
        '</a:graphicData></a:graphic></p:graphicFrame></p:spTree></p:cSld></p:sld>'
    )
    slide_two = (
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="4" name="text"/></p:nvSpPr>'
        '<p:txBody><a:p><a:r><a:t>SYNTH-PPTX-SLIDE-2</a:t></a:r></a:p></p:txBody></p:sp>'
        '<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="5" name="chart"/>'
        '</p:nvGraphicFramePr><a:graphic><a:graphicData><c:chart r:id="rId1"/>'
        '</a:graphicData></a:graphic></p:graphicFrame></p:spTree></p:cSld></p:sld>'
    )
    _zip(path, {
        "[Content_Types].xml": _types([
            ("ppt/presentation.xml", "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"),
            ("ppt/slides/slide1.xml", "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"),
            ("ppt/slides/slide2.xml", "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"),
            ("ppt/charts/chart1.xml", "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"),
        ]),
        "ppt/presentation.xml": (
            '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<p:sldIdLst><p:sldId id="256" r:id="rId1"/><p:sldId id="257" r:id="rId2"/>'
            "</p:sldIdLst></p:presentation>"
        ),
        "ppt/_rels/presentation.xml.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="slide" Target="slides/slide1.xml"/>'
            '<Relationship Id="rId2" Type="slide" Target="slides/slide2.xml"/>'
            "</Relationships>"
        ),
        "ppt/slides/slide1.xml": slide_one,
        "ppt/slides/slide2.xml": slide_two,
        "ppt/charts/chart1.xml": (
            '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart">'
            '<c:chart><c:plotArea><c:lineChart><c:ser><c:pt><c:v>42</c:v></c:pt>'
            "</c:ser></c:lineChart></c:plotArea></c:chart></c:chartSpace>"
        ),
    })


def build_docx(path: Path) -> None:
    _zip(path, {
        "[Content_Types].xml": _types([
            ("word/document.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"),
        ]),
        "word/document.xml": (
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
            '<w:p><w:r><w:t>SYNTH-DOCX-PARAGRAPH</w:t></w:r></w:p><w:tbl><w:tr><w:tc>'
            '<w:p><w:r><w:t>SYNTH-DOCX-CELL</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
            "</w:body></w:document>"
        ),
    })


def build_pdf(path: Path) -> None:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>",
        b"<< /Length 24 >>\nstream\n(SYNTH-PDF-PAGE-1)\nendstream",
        b"<< /Producer (Synthetic) >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 7 0 R >>",
        b"<< /Length 0 >>\nstream\n\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode())
        data.extend(obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(data)
    os.chmod(path, 0o600)


def build_all(root: Path) -> dict[str, object]:
    secure_directory(root)
    builders = {"xlsx": build_xlsx, "pptx": build_pptx, "pdf": build_pdf, "docx": build_docx}
    files: dict[str, dict[str, object]] = {}
    for kind, builder in builders.items():
        path = root / f"synthetic.{kind}"
        builder(path)
        payload = path.read_bytes()
        files[kind] = {"name": path.name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    manifest: dict[str, object] = {
        "schema_version": 1,
        "files": files,
        "expected": {
            "xlsx": {"sheets": 2, "hidden_sheets": 1, "formula_cells": 1, "tables": 1, "charts": 1},
            "pptx": {"slides": 2, "tables": 1, "table_cells": 1, "charts": 1},
            "pdf": {"pages": 2},
            "docx": {"paragraphs": 2, "table_cells": 1},
        },
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    os.chmod(manifest_path, 0o600)
    return manifest
