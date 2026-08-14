from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest import mock
import zipfile

from extractcheck.census import census_file
from extractcheck.compare import build_reference_comparison
from extractcheck.contracts import ContractError, validate_unit
from extractcheck.evaluate import PRIVATE_SENTINELS, build_synthetic_report
from extractcheck.fixtures import build_all
from extractcheck.resources import ResourceSample, sample_resources
from extractcheck.reference_adapter import extract_reference
from extractcheck.runner import RunBudget, RunController, WorkerResult
from extractcheck.safety import SafetyViolation, deny_python_network
from tools.audit_release import audit


def sample(sample_id: str = "SYN-001") -> dict[str, object]:
    return {
        "sample_id": sample_id,
        "format": "pdf",
        "source_kind": "synthetic",
        "source_sha256": hashlib.sha256(sample_id.encode()).hexdigest(),
        "source_size_bytes": 10,
    }


def resource_sample() -> ResourceSample:
    return ResourceSample(rss_bytes=1024, free_memory_ratio=0.9, supported=True, unsupported_codes=())


class PublicPackageTests(unittest.TestCase):
    def test_nested_generated_root_is_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "LICENSE").write_text("Apache License 2.0\n")
            marker = "synthetic marker /" + "Users" + "/not-public\n"
            for relative in ("docs/build/marker.md", "src/dist/marker.md"):
                path = root / relative
                path.parent.mkdir(parents=True)
                path.write_text(marker)
            result = audit(root, release=True)
        self.assertEqual("fail", result["status"])
        self.assertEqual(
            {
                "sensitive_pattern:docs/build/marker.md",
                "sensitive_pattern:src/dist/marker.md",
            },
            set(result["violations"]),
        )

    def test_nested_egg_info_is_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "LICENSE").write_text("Apache License 2.0\n")
            path = root / "docs/example.egg-info/marker.md"
            path.parent.mkdir(parents=True)
            path.write_text("synthetic marker /" + "Users" + "/not-public\n")
            result = audit(root, release=True)
        self.assertEqual("fail", result["status"])
        self.assertEqual(
            ["sensitive_pattern:docs/example.egg-info/marker.md"],
            result["violations"],
        )

    def test_four_format_report_is_deterministic_and_hash_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = build_synthetic_report(root / "first")
            second = build_synthetic_report(root / "second")
            payload = (root / "first" / "report.json").read_text()
        self.assertTrue(first["all_passed"])
        self.assertEqual(0, first["network_attempts"])
        self.assertEqual(first["report_sha256"], second["report_sha256"])
        self.assertFalse(any(value in payload for value in PRIVATE_SENTINELS))
        self.assertNotIn(directory, payload)

    def test_reference_comparison_is_deterministic_and_hash_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = build_reference_comparison(root / "first")
            second = build_reference_comparison(root / "second")
            payload = (root / "first" / "comparison.json").read_text()
        self.assertTrue(first["all_passed"])
        self.assertEqual(0, first["network_attempts"])
        self.assertEqual(0, first["private_sources_opened"])
        self.assertEqual(first["report_sha256"], second["report_sha256"])
        self.assertFalse(any(value in payload for value in PRIVATE_SENTINELS))
        self.assertNotIn(directory, payload)

    def test_reference_adapter_emits_valid_units_without_using_census(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_all(root / "fixtures")
            with mock.patch(
                "extractcheck.census.census_file",
                side_effect=AssertionError("adapter called the grading census"),
            ):
                units = extract_reference(
                    root / "fixtures/synthetic.xlsx",
                    run_id="reference-test",
                    sample_id="SYN-XLSX",
                )
        self.assertGreater(len(units), 0)
        self.assertTrue(all(validate_unit(unit) is None for unit in units))

    def test_reference_adapter_refuses_traversing_ooxml_members(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.xlsx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../escape.xml", "unsafe")
                archive.writestr("xl/workbook.xml", "<workbook/>")
            with self.assertRaises(SafetyViolation):
                extract_reference(path, run_id="reference-test", sample_id="SYN-XLSX")

    def test_census_refuses_a_source_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_all(root / "fixtures")
            link = root / "linked.xlsx"
            link.symlink_to(root / "fixtures" / "synthetic.xlsx")
            with self.assertRaises(SafetyViolation):
                census_file(link)

    def test_census_refuses_traversing_ooxml_members(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.xlsx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../escape.xml", "unsafe")
                archive.writestr("xl/workbook.xml", "<workbook/>")
            with self.assertRaises(SafetyViolation):
                census_file(path)

    def test_python_network_guard_records_and_blocks(self) -> None:
        with deny_python_network() as attempts:
            with self.assertRaises(SafetyViolation):
                socket.getaddrinfo("example.invalid", 443)
        self.assertEqual(["resolve:str"], attempts)

    def test_windows_resource_sampling_reports_unsupported_metrics(self) -> None:
        with mock.patch("extractcheck.resources.sys.platform", "win32"):
            result = sample_resources()
        self.assertIsNone(result.rss_bytes)
        self.assertIsNone(result.free_memory_ratio)
        self.assertFalse(result.supported)
        self.assertEqual(
            ("rss_unsupported", "free_memory_ratio_unsupported"),
            result.unsupported_codes,
        )

    def test_contract_requires_typed_cell_locator(self) -> None:
        unit = {
            "schema_version": 1, "run_id": "run", "sample_id": "sample",
            "source_kind": "synthetic", "source_sha256": "a" * 64,
            "lane": "candidate", "unit_id": "unit", "unit_type": "cell",
            "locator": {"sheet_index": 0}, "content_hashes": {},
            "status": "ok", "warnings": [],
        }
        with self.assertRaises(ContractError):
            validate_unit(unit)

    def test_run_controller_requires_explicit_resume_and_preserves_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = RunController(
                root, "synthetic-run", [sample()], budget=RunBudget(min_free_disk_bytes=0),
                resource_sampler=resource_sample,
            )

            def crash(_item: dict[str, object], context: object) -> WorkerResult:
                context.write_json("partial.json", {"status": "partial"})  # type: ignore[attr-defined]
                raise KeyboardInterrupt()

            with self.assertRaises(KeyboardInterrupt):
                controller.run(crash)
            reopened = RunController(
                root, "synthetic-run", [sample()], budget=RunBudget(min_free_disk_bytes=0),
                resource_sampler=resource_sample,
            )
            with self.assertRaises(SafetyViolation):
                reopened.run(lambda _item, _context: WorkerResult())
            result = reopened.run(lambda _item, _context: WorkerResult(units=1), resume=True)
            self.assertEqual("completed", result["state"])
            self.assertEqual(2, result["attempts"]["SYN-001"])
            self.assertTrue((root / "runs/synthetic-run/items/SYN-001/attempt-1/partial.json").exists())
            self.assertTrue((root / "runs/synthetic-run/items/SYN-001/attempt-2/result.json").exists())
            if os.name == "posix":
                mode = (root / "runs/synthetic-run/items/SYN-001").stat().st_mode
                self.assertEqual(0o700, mode & 0o777)

    def test_run_control_manifest_rejects_private_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            item = sample()
            item["source_path"] = "/private/example"
            with self.assertRaises(ValueError):
                RunController(Path(directory), "unsafe", [item])


if __name__ == "__main__":
    unittest.main()
