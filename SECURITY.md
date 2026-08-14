# Security Policy

## Scope

This project handles local documents and evaluation evidence. Treat every input
document and third-party parser as untrusted.

## Security boundaries

- Source files are accepted only as regular files; source symlinks fail closed.
- Source size, identity, and SHA-256 are checked before and after inspection.
- OOXML member count, expanded size, individual XML size, encryption, and path
  traversal are bounded or rejected.
- Outputs are owner-only and confined below an explicit output root.
- Controller manifests accept only opaque allowlisted fields.
- Common Python DNS and socket entry points can be blocked and recorded.

These controls do **not** create an air gap. Native libraries, subprocesses,
shell commands, child interpreters, or hostile parsers can bypass a Python
socket monkey patch. Use an OS sandbox, network namespace/firewall, container,
or VM when the threat model requires enforcement.

The built-in controller is cooperative. It detects elapsed-time and resource
breaches after a worker returns; it does not kill a hung in-process worker.
Run third-party parsers in a separately supervised process.

## Reporting a vulnerability

Do not attach private documents, extracted text, source paths, email metadata,
or runtime evidence to a public issue. Use GitHub's private vulnerability
reporting with a minimal synthetic reproducer. Private reporting must be enabled
before publication. Private reporting is enabled for this repository.
