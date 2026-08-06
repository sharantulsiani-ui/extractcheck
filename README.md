# ExtractCheck

[![ci](https://github.com/sharantulsiani-ui/extractcheck/actions/workflows/ci.yml/badge.svg)](https://github.com/sharantulsiani-ui/extractcheck/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

> Know what your document extractor missed before you trust your RAG.

ExtractCheck is an offline benchmark for testing document extraction across
PDF, PowerPoint and Excel, with exact source provenance. It also includes a
small Word fixture because mixed archives rarely stop at three formats.

Search terms: document parsing, document extraction, document AI, RAG, PDF,
PPTX, XLSX, benchmark, provenance, offline AI.

## Part I: Why I built this

*Sharan Tulsiani, Architect*

I have more than 15 years of personal industry experience, conference
material, consulting and research, business models, startup pitches,
business-school deal evaluations and notes. It is more than 80 GB across
spreadsheets, slides, PDFs, email and notes.

It is useful. It is not tidy.

Search works when I remember the right filename or phrase. That defeats much
of the point. I wanted to ask broader questions and get the page, slide,
attachment, sheet or cell behind each answer.

My first instinct was to build a smarter index. That was the wrong first move.

If extraction loses a formula, breaks a table or forgets where a number came
from, a better search engine cannot bring it back. It may return the wrong
answer faster.

So I started with extraction. ExtractCheck checks what document tools find,
what they miss and whether they can point back to the source. It runs locally,
keeps source files read only and records failures instead of hiding them.

I designed the system, the safeguards and the tests. Codex wrote the code
under my direction and kept the technical record. I am not a coder. I approach
this as an architect and operator: define the problem, set the boundaries,
test the claims and keep asking awkward questions.

The public project uses only generated synthetic documents. It does not
contain my files, private results or archive data.

## Part II: Technical account by Codex

The brief had five rules:

- Keep source files read only.
- Process everything locally.
- Record where each result came from.
- Check extractors against the source structure.
- Never turn missing evidence into a successful result.

The harness checks spreadsheets, presentations, PDFs and Word documents:

| Format | What we check |
| --- | --- |
| Spreadsheet | sheets, cells, formulas, tables, charts and coordinates |
| Presentation | slides, shapes, tables, charts and reading order |
| PDF | pages, text blocks, ordering and locations |
| Word document | paragraphs, tables and document structure |

It also checks source identity, output confinement, offline behavior,
determinism and resource limits. The controller keeps outputs owner-only,
accepts only opaque manifest fields and supports explicit crash recovery.

The result is not a universal parser ranking. It is a test rig to run before
building a search or RAG system on top of an extractor.

## What you can use or improve

You can use the generated XLSX, PPTX, PDF and DOCX fixtures, the structure-only
census, typed provenance contracts, source SHA-256 checks, offline guard,
restartable controller, resource limits, deterministic reports and release
audit as a small starting point for your own local evaluation.

There is room to improve:

- stronger formula and chart extraction;
- better PowerPoint shape and PDF location support;
- supervised processes for parsers that hang;
- more synthetic documents and hard cases;
- adapters for more extraction tools;
- Windows and Linux testing;
- clearer comparisons and visual reports.

If you work on document parsing, local AI, retrieval or digital archives,
please share feedback or open a focused contribution. Codex wrote the code
under Sharan's direction. Sharan is a non-coder and welcomes help making it
simpler, safer and more efficient.

## Try it

Python 3.11 or newer is required. ExtractCheck has no runtime dependencies.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
extractcheck synthetic --output ./example-output
```

Expected summary:

```json
{"all_passed": true, "network_attempts": 0, "report_sha256": "..."}
```

The command creates four synthetic documents and a hash-only report. Run it
twice and the reports should match byte for byte.

## Bring an extractor

An adapter should emit normalized units that pass
`extractcheck.contracts.validate_unit`. Keep native parser output separate
from normalized units. Compare both against an independent source census. Do
not let a parser grade its own work.

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

The controller rejects manifest keys that may contain paths, subjects,
senders, recipients, bodies, content, values, tokens or email data.

## Important limits

- The Python socket guard is not an operating system network sandbox.
- The built-in PDF check counts page objects. It is not a PDF layout parser.
- The in-process runner cannot kill a parser that hangs. Use a supervised
  process for third-party parsers.
- The package is not a hardened hostile document parser.
- Passing extraction tests does not prove that search or RAG works well.
- The configured CI is not claimed to have passed until a remote repository
  runs it.

Read the [methodology](docs/methodology.md), [threat model](docs/threat-model.md),
[result guide](docs/interpreting-results.md), [public decision and failure
record](docs/public-decision-and-failure-record.md), and
[suggested GitHub topics](docs/github-topics.md).

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python tools/audit_release.py --release
PYTHONPATH=src python -m extractcheck.cli synthetic --output ./example-output
```

The project uses the [Apache License 2.0](LICENSE).

> Bring your own documents. Keep them local. Find out what your extraction
> pipeline forgets before you build the next search system on top of it.
