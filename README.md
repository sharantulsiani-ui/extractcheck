# ExtractCheck

[![ci](https://github.com/sharantulsiani-ui/extractcheck/actions/workflows/ci.yml/badge.svg)](https://github.com/sharantulsiani-ui/extractcheck/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

> Check what extraction lost before you trust what retrieval found.

ExtractCheck is a small offline benchmark for document extraction. It creates
synthetic spreadsheets, slides, PDFs and Word files, then checks which source
structures survive extraction and whether each result still points to its source.

It does not rank every parser. Use it to test a parser before you build search
or RAG on top of that parser's output.

## Try it

Python 3.11 or newer is required. The package has no runtime dependencies.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install .
extractcheck synthetic --output ./example-output
```

A passing run prints:

```json
{"all_passed": true, "network_attempts": 0, "report_sha256": "..."}
```

The command creates four synthetic documents and a hash-only report. Run it
twice and the reports should match byte for byte.

## See an adapter comparison

Version 0.2 adds a small reference adapter. It reads the synthetic files,
emits normalized units with typed locators, and compares them with a separate
structure census.

```bash
extractcheck compare --output ./comparison-output
```

Open `comparison-output/comparison.json` to see the expected and recovered
counts for sheets, cells, formulas, tables, charts, slides, shapes, pages and
paragraphs.

The reference adapter is an example, not a parser recommendation. It and the
census use separate code paths. Neither sees private files, and neither writes
an index or graph.

## What it checks

| Format | Structural checks |
| --- | --- |
| Spreadsheet | sheets, cells, formulas, tables, charts and cell coordinates |
| Presentation | slides, shapes, tables, charts and slide locators |
| PDF | page objects and page locators |
| Word | paragraphs, tables and document structure |

ExtractCheck also checks source identity, output confinement, deterministic
reports, Python network attempts and resource limits. Its controller accepts
opaque manifest fields and requires an explicit resume after a crash. On POSIX
systems it sets owner-only output modes. On Windows, use an output folder whose
ACL already limits access to your account.

## Why I built it

I had years of work spread across spreadsheets, slides, PDFs, email and notes.
Search helped only when I remembered the right filename or phrase.

I first thought I needed a better index. The extraction tests changed my mind.
If a parser drops a formula, flattens a table or loses the source location, an
index cannot restore it. It can only search the damaged result.

I designed the problem, safeguards, evaluation method and acceptance gates.
Codex wrote the implementation under those constraints. I test the claims,
record the failures and change the rules when the evidence calls for it.

This public repository contains generated documents only. It contains no
private source files, private benchmark results or archive data.

## Bring another extractor

An adapter turns parser output into units checked by
`extractcheck.contracts.validate_unit`. Store the parser's original output
separately. Compare both forms with an independent source census. Do not let
the parser grade its own work.

The bundled implementation is in
[`reference_adapter.py`](src/extractcheck/reference_adapter.py). Its comparison
runner is in [`compare.py`](src/extractcheck/compare.py).

The restartable controller accepts opaque manifest fields only:

```python
from pathlib import Path
from extractcheck.runner import RunBudget, RunController, WorkerResult

items = [{
    "sample_id": "SYN-001",
    "format": "pdf",
    "source_kind": "synthetic",
    "source_sha256": "a" * 64,
    "source_size_bytes": 10,
}]

controller = RunController(
    Path("./local-runtime"),
    "candidate-run",
    items,
    budget=RunBudget(max_item_output_bytes=64 * 1024 * 1024),
)

def worker(item, context):
    context.write_json("result.json", {"sample_id": item["sample_id"]})
    return WorkerResult(units=1)

controller.run(worker)
```

The controller rejects manifest keys that may contain paths, message fields,
document content, values, tokens or email data.

## Limits

- The Python socket guard is not an operating-system network sandbox.
- The PDF check counts page objects. It is not a PDF layout or text parser.
- The in-process controller cannot kill a parser that hangs. Supervise third-party
  parsers in a separate process.
- The package is not a hardened hostile-document parser.
- Synthetic success does not prove that a parser will work on another corpus.
- Passing extraction tests does not prove that search or RAG works well.

Read the [methodology](docs/methodology.md), [threat model](docs/threat-model.md),
[result guide](docs/interpreting-results.md), and [public decision and failure
record](docs/public-decision-and-failure-record.md).

## Contribute

Send focused bug reports, synthetic failure cases or adapter improvements. Do
not attach private documents or extracted private content. Read
[CONTRIBUTING.md](CONTRIBUTING.md) and the [security policy](SECURITY.md) first.

For local checks:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m extractcheck.cli synthetic --output ./example-output
PYTHONPATH=src python -m extractcheck.cli compare --output ./comparison-output
PYTHONPATH=src python tools/audit_release.py --release
```

Apache-2.0 licensed. Sharan Tulsiani designed and stewards the project. Codex
wrote the implementation under his direction.
