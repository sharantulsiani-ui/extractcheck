"""Fail-closed allowlist and privacy scan for the public candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT_FILES = {
    ".gitignore", "CONTRIBUTING.md", "LICENSE", "NOTICE.md", "README.md", "SECURITY.md",
    "pyproject.toml",
}
ROOT_DIRS = {".github", "docs", "src", "tests", "tools"}
GENERATED_ROOTS = {".pytest_cache", ".venv", "build", "dist"}
FORBIDDEN_SUFFIXES = {
    ".db", ".sqlite", ".sqlite3", ".mbox", ".eml", ".xls", ".xlsx",
    ".ppt", ".pptx", ".doc", ".docx", ".pdf", ".safetensors", ".bin",
    ".whl", ".dylib", ".so",
}
FORBIDDEN_PARTS = {"runtime", "cache", "models", "private", "evidence", ".git"}


def patterns() -> list[re.Pattern[str]]:
    return [
        re.compile(re.escape("/" + "Users" + "/")),
        re.compile(r"S[01]-(?:DOC|ATT)-[0-9a-f]{8,}"),
        re.compile(r"\b[A-Fa-f0-9]{64}\b"),
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    ]


def audit(root: Path, *, release: bool = False) -> dict[str, object]:
    violations: list[str] = []
    files: list[dict[str, object]] = []
    for child in root.iterdir():
        if child.name in GENERATED_ROOTS or child.name.endswith(".egg-info"):
            continue
        if child.name not in ROOT_FILES | ROOT_DIRS:
            violations.append(f"not_allowlisted:{child.name}")
    if release and not (root / "LICENSE").is_file():
        violations.append("release_requires_license")
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root)
        root_entry = relative.parts[0]
        if (
            root_entry in GENERATED_ROOTS
            or root_entry.endswith(".egg-info")
            or "__pycache__" in relative.parts
            or path.suffix in {".pyc", ".pyo"}
        ):
            continue
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            violations.append(f"forbidden_path_part:{relative.as_posix()}")
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            violations.append(f"forbidden_suffix:{relative.as_posix()}")
            continue
        payload = path.read_bytes()
        if len(payload) > 1024 * 1024:
            violations.append(f"oversize_file:{relative.as_posix()}")
            continue
        if b"\x00" in payload:
            violations.append(f"binary_file:{relative.as_posix()}")
            continue
        text = payload.decode("utf-8")
        if relative.as_posix() != "tools/audit_release.py":
            for expression in patterns():
                if expression.search(text):
                    violations.append(f"sensitive_pattern:{relative.as_posix()}")
                    break
        files.append({
            "path": relative.as_posix(),
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    manifest_payload = "".join(
        f"{row['path']}\0{row['bytes']}\0{row['sha256']}\n" for row in files
    ).encode("utf-8")
    return {
        "status": "pass" if not violations else "fail",
        "files": files,
        "file_count": len(files),
        "manifest_sha256": hashlib.sha256(manifest_payload).hexdigest(),
        "violations": violations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()
    result = audit(args.root.resolve(), release=args.release)
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "pass":
        sys.exit(1)


if __name__ == "__main__":
    main()
