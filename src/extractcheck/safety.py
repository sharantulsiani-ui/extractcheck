"""Local filesystem, source-identity, and Python-network safety primitives."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import sys
from typing import Any, Iterator


class SafetyViolation(RuntimeError):
    """Raised before or immediately after a safety boundary is crossed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def secure_directory(path: Path) -> Path:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            target = current.resolve()
            macos_alias = (
                sys.platform == "darwin"
                and current in {Path("/var"), Path("/tmp")}
                and target == Path("/private") / current.relative_to("/")
            )
            if not macos_alias:
                raise SafetyViolation("output directory contains a symlink")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def require_within(path: Path, root: Path) -> Path:
    resolved_root = root.resolve()
    resolved = path.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise SafetyViolation("path escapes the approved root")
    return resolved


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.part")
    if path.exists() or path.is_symlink() or temporary.exists() or temporary.is_symlink():
        raise SafetyViolation("output already exists")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    with temporary.open("r+b") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def replace_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically create or replace a controller-owned state file."""
    if path.is_symlink():
        raise SafetyViolation("state target is a symlink")
    temporary = path.with_name(f".{path.name}.part")
    if temporary.exists() or temporary.is_symlink():
        raise SafetyViolation("stale state temporary exists")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    with temporary.open("r+b") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    os.chmod(path, 0o600)


@dataclass(frozen=True)
class SourceIdentity:
    size: int
    mtime_ns: int
    inode: int
    mode: int
    sha256: str


def source_identity(path: Path) -> SourceIdentity:
    if path.is_symlink():
        raise SafetyViolation("source symlinks are not accepted")
    value = path.stat()
    if not stat.S_ISREG(value.st_mode):
        raise SafetyViolation("source must be a regular file")
    return SourceIdentity(value.st_size, value.st_mtime_ns, value.st_ino, value.st_mode, sha256_file(path))


@contextmanager
def source_read_guard(path: Path) -> Iterator[SourceIdentity]:
    before = source_identity(path)
    yield before
    after = source_identity(path)
    if before != after:
        raise SafetyViolation("source identity changed during inspection")


@contextmanager
def deny_python_network() -> Iterator[list[str]]:
    """Block common Python socket entry points; this is not an OS sandbox."""
    attempts: list[str] = []
    original_connect = socket.socket.connect
    original_create = socket.create_connection
    original_resolve = socket.getaddrinfo

    def blocked_connect(_sock: socket.socket, address: object) -> None:
        attempts.append(f"connect:{type(address).__name__}")
        raise SafetyViolation("network disabled")

    def blocked_create(address: object, *args: object, **kwargs: object) -> None:
        attempts.append(f"create:{type(address).__name__}")
        raise SafetyViolation("network disabled")

    def blocked_resolve(host: object, *args: object, **kwargs: object) -> None:
        attempts.append(f"resolve:{type(host).__name__}")
        raise SafetyViolation("network disabled")

    socket.socket.connect = blocked_connect  # type: ignore[method-assign]
    socket.create_connection = blocked_create  # type: ignore[assignment]
    socket.getaddrinfo = blocked_resolve  # type: ignore[assignment]
    try:
        yield attempts
    finally:
        socket.socket.connect = original_connect  # type: ignore[method-assign]
        socket.create_connection = original_create
        socket.getaddrinfo = original_resolve
