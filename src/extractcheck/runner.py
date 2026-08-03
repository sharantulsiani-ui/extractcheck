"""Small restartable controller for opaque, additive evaluation item runs."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
from typing import Any, Callable, Iterable

from .resources import ResourceSample, sample_resources
from .safety import SafetyViolation, replace_json, require_within, secure_directory


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,96}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PRIVATE_KEY = re.compile(r"path|filename|locator|subject|sender|recipient|body|content|value|text|secret|token|email", re.I)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(items: Iterable[dict[str, Any]]) -> str:
    return hashlib.sha256(
        "".join(canonical_json(item) + "\n" for item in items).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class RunBudget:
    item_timeout_seconds: float = 300.0
    run_timeout_seconds: float = 3600.0
    max_item_output_bytes: int = 64 * 1024 * 1024
    max_run_output_bytes: int = 512 * 1024 * 1024
    min_free_disk_bytes: int = 1024 * 1024 * 1024
    max_rss_bytes: int | None = None


@dataclass(frozen=True)
class WorkerResult:
    units: int = 0
    warnings: tuple[str, ...] = ()


class ItemContext:
    def __init__(self, root: Path, budget: RunBudget) -> None:
        self.root = secure_directory(root)
        self.budget = budget
        self.written = 0

    def write_bytes(self, name: str, payload: bytes) -> Path:
        if not name or "/" in name or name in {".", ".."}:
            raise SafetyViolation("item output name must be a plain filename")
        target = require_within(self.root / name, self.root)
        if target.exists() or target.is_symlink():
            raise SafetyViolation("item outputs are additive")
        if self.written + len(payload) > self.budget.max_item_output_bytes:
            raise SafetyViolation("item output budget exceeded")
        target.write_bytes(payload)
        os.chmod(target, 0o600)
        self.written += len(payload)
        return target

    def write_json(self, name: str, payload: dict[str, Any]) -> Path:
        return self.write_bytes(name, (canonical_json(payload) + "\n").encode("utf-8"))


class RunController:
    def __init__(
        self,
        runtime: Path,
        run_id: str,
        items: Iterable[dict[str, Any]],
        *,
        budget: RunBudget | None = None,
        clock: Callable[[], float] = time.monotonic,
        resource_sampler: Callable[[], ResourceSample] = sample_resources,
    ) -> None:
        if not SAFE_ID.fullmatch(run_id):
            raise ValueError("unsafe run ID")
        self.items = [dict(item) for item in items]
        self._validate_items()
        self.manifest_fingerprint = fingerprint(self.items)
        self.budget = budget or RunBudget()
        self.clock = clock
        self.resource_sampler = resource_sampler
        self.root = secure_directory(runtime / "runs" / run_id)
        self.items_root = secure_directory(self.root / "items")
        self.checkpoint_path = self.root / "checkpoint.json"
        if self.checkpoint_path.exists():
            checkpoint = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
            if checkpoint.get("manifest_fingerprint") != self.manifest_fingerprint:
                raise SafetyViolation("run manifest changed")
        else:
            self._checkpoint("created", 0, {}, None, None)

    def _validate_items(self) -> None:
        seen: set[str] = set()
        for item in self.items:
            if any(PRIVATE_KEY.search(str(key)) for key in item):
                raise ValueError("control manifest contains a private-field key")
            required = {"sample_id", "format", "source_kind", "source_sha256", "source_size_bytes"}
            if set(item) != required:
                raise ValueError("control item fields are not exactly allowlisted")
            sample_id = item["sample_id"]
            if not isinstance(sample_id, str) or not SAFE_ID.fullmatch(sample_id) or sample_id in seen:
                raise ValueError("invalid or duplicate sample ID")
            seen.add(sample_id)
            if not isinstance(item["source_sha256"], str) or not SHA256.fullmatch(item["source_sha256"]):
                raise ValueError("invalid source SHA-256")
            if not isinstance(item["source_size_bytes"], int) or item["source_size_bytes"] < 0:
                raise ValueError("invalid source size")

    def _checkpoint(
        self, state: str, next_index: int, attempts: dict[str, int],
        started: float | None, current: str | None,
    ) -> None:
        payload = {
            "schema_version": 1,
            "state": state,
            "manifest_fingerprint": self.manifest_fingerprint,
            "next_index": next_index,
            "attempts": attempts,
            "started_monotonic": started,
            "current_item_id": current,
        }
        payload["integrity_sha256"] = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
        replace_json(self.checkpoint_path, payload)

    def _read_checkpoint(self) -> dict[str, Any]:
        checkpoint = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        integrity = checkpoint.pop("integrity_sha256", None)
        if integrity != hashlib.sha256(canonical_json(checkpoint).encode("utf-8")).hexdigest():
            raise SafetyViolation("checkpoint integrity failed")
        checkpoint["integrity_sha256"] = integrity
        return checkpoint

    def _guard(self, started: float, run_output: int) -> None:
        if self.clock() - started > self.budget.run_timeout_seconds:
            raise SafetyViolation("run time budget exceeded")
        if shutil.disk_usage(self.root).free < self.budget.min_free_disk_bytes:
            raise SafetyViolation("free disk floor reached")
        if run_output > self.budget.max_run_output_bytes:
            raise SafetyViolation("run output budget exceeded")
        sample = self.resource_sampler()
        if self.budget.max_rss_bytes is not None:
            if sample.rss_bytes is None:
                raise SafetyViolation("RSS unavailable while an RSS limit is configured")
            if sample.rss_bytes > self.budget.max_rss_bytes:
                raise SafetyViolation("RSS limit reached")

    def run(self, worker: Callable[[dict[str, Any], ItemContext], WorkerResult], *, resume: bool = False) -> dict[str, Any]:
        checkpoint = self._read_checkpoint()
        if checkpoint["state"] == "completed":
            return checkpoint
        if checkpoint["state"] == "running" and not resume:
            raise SafetyViolation("an interrupted run requires resume=True")
        if checkpoint["state"] not in {"created", "running"}:
            raise SafetyViolation("run state cannot execute")
        started = checkpoint["started_monotonic"] or self.clock()
        attempts = {str(key): int(value) for key, value in checkpoint["attempts"].items()}
        next_index = int(checkpoint["next_index"])
        run_output = sum(path.stat().st_size for path in self.root.rglob("*") if path.is_file())
        for index in range(next_index, len(self.items)):
            item = self.items[index]
            self._guard(started, run_output)
            sample_id = str(item["sample_id"])
            attempt = attempts.get(sample_id, 0) + 1
            attempts[sample_id] = attempt
            self._checkpoint("running", index, attempts, started, sample_id)
            sample_root = secure_directory(self.items_root / sample_id)
            context = ItemContext(sample_root / f"attempt-{attempt}", self.budget)
            item_started = self.clock()
            result = worker(dict(item), context)
            if self.clock() - item_started > self.budget.item_timeout_seconds:
                raise SafetyViolation("item time budget exceeded")
            context.write_json("result.json", {
                "status": "ok", "units": result.units, "warnings": list(result.warnings),
            })
            run_output += context.written
            self._guard(started, run_output)
            self._checkpoint("running", index + 1, attempts, started, None)
        self._checkpoint("completed", len(self.items), attempts, started, None)
        return self._read_checkpoint()
