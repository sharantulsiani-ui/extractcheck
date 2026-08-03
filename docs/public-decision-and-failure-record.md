# Public decision and failure record

## Release decision

The local ExtractCheck candidate is ready for human review as a standalone,
synthetic-only Apache-2.0 repository. Publication remains on hold until a
GitHub repository exists, private vulnerability reporting is enabled, remote
CI runs, and Sharan gives final approval.

No remote CI pass is claimed here.

## Decisions

- Use the name ExtractCheck for the repository, Python distribution, import
  package and command line interface.
- Keep the runtime dependency-free and generate all proof documents locally.
- Keep the source census hash-only and structure-only. Do not persist fixture
  text, cell values, chart values or formula expressions in the report.
- Keep source checks read only, outputs confined and owner-only.
- Keep the public scope to deterministic synthetic evidence. Do not publish a
  private corpus score or adapter result.
- Use Apache-2.0 with matching package metadata, license and notice.

## Local verification record

The release gate ran the following checks from this repository candidate:

| Check | Decision evidence |
| --- | --- |
| Unit suite | 9/9 passed under Python 3.11 |
| Compilation | Passed for `src`, `tests` and `tools` |
| Release audit | Passed with 24 files and zero violations |
| Synthetic proof | XLSX, PPTX, PDF and DOCX passed with zero network attempts |
| Determinism | Two reports matched byte for byte |
| Clean copy | 24-file copy passed audit, compilation, 9/9 tests and synthetic proof |
| Packaging | Wheel built without build isolation or dependency acquisition |
| CLI smoke test | No-index, no-deps install passed two identical CLI reports |

The exact command output, hashes and environment limitations are in the build
report outside this candidate. This file is the public decision record and
contains no machine paths, private identifiers, source values or
corpus-derived hashes.

## Wins

- All four synthetic formats have deterministic, dependency-free fixtures.
- Source identity is checked before and after inspection.
- OOXML traversal, encryption, member-count and expanded-size boundaries fail
  closed.
- Typed locators distinguish spreadsheet cells, presentation shapes and PDF
  pages or blocks.
- The runner preserves interrupted attempts and requires explicit resume.
- Public audit rules reject unexpected roots, private-looking fields, binary
  artifacts and oversized files.

## Failures found and repaired

- Exact macOS `/var` and `/tmp` aliases were distinguished from unsafe project
  or user symlinks in the output confinement check.
- Generated cache, build and egg-info trees were excluded only at their exact
  generated locations so unexpected source entries still fail the audit.
- Synthetic Office ZIP members use fixed timestamps and permissions so report
  bytes remain deterministic.
- OOXML census limits and traversal checks have regression coverage.

## Known limitations

- The Python socket guard is not an operating system network sandbox.
- The in-process controller cannot stop a worker that never returns.
- The PDF implementation counts page objects. It is not a layout or text
  parser.
- Synthetic proof does not establish parser quality on another corpus.
- Remote CI, fresh clone verification and GitHub vulnerability reporting are
  publication steps, not local evidence.
