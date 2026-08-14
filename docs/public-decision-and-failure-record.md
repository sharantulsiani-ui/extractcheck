# Public decision and failure record

## Release decision

The synthetic-only Apache-2.0 repository is public. Its release gate passed
before publication, private vulnerability reporting is enabled, and remote CI
has passed on the published 0.1 line.

Version 0.2 adds a reference adapter and comparison command. A fresh CI result
for each revision remains external evidence in GitHub Actions.

## Decisions

- Use the name ExtractCheck for the repository, Python distribution, import
  package and command line interface.
- Keep the runtime dependency-free and generate all proof documents locally.
- Keep the source census hash-only and structure-only. Do not persist fixture
  text, cell values, chart values or formula expressions in the report.
- Keep source checks read only and outputs confined. Set owner-only modes on
  POSIX systems; require a caller-supplied private ACL on Windows.
- Keep the public scope to deterministic synthetic evidence. Do not publish a
  private corpus score or adapter result.
- Include one dependency-free reference adapter to show the public contract.
  Keep its code path separate from the grading census and make no parser-quality
  claim from its synthetic result.
- Use Apache-2.0 with matching package metadata, license and notice.

## Local verification record

The release gate ran the following checks from this repository candidate:

| Check | Decision evidence |
| --- | --- |
| Unit suite | 13/13 passed under Python 3.11 |
| Compilation | Passed for `src`, `tests` and `tools` |
| Release audit | Passed with 31 files and zero violations |
| Synthetic proof | XLSX, PPTX, PDF and DOCX passed with zero network attempts |
| Determinism | Two reports matched byte for byte |
| Reference comparison | Four formats passed against the independent census with zero network attempts |
| Clean copy | Release copy passed audit, compilation, 13/13 tests and both synthetic commands |
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
- The reference adapter gives contributors a working normalized-unit example
  without adding a parser dependency.
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
- The first remote CI run passed its tests and synthetic proof but audited the
  Git checkout itself. The fail-closed audit correctly rejected `.git`. CI now
  audits a clean `git archive` of the exact commit, so the audit remains strict
  and evaluates only files distributed by the repository.
- The first public release described the adapter contract but gave contributors
  no working adapter. Version 0.2 adds a small reference implementation and
  scores it with the separate census.
- The resource sampler imported a Unix-only module before Windows could report
  that its process metrics were unsupported. The import is now optional, and a
  regression test checks the explicit Windows result.
- Windows rejected `fsync` on a read-only handle. Atomic JSON writers now reopen
  the completed temporary file in read/write mode before syncing it to disk.
- Windows does not enforce POSIX `0700` modes. The test now checks that mode only
  on POSIX systems, and the public boundary requires a private Windows ACL.

## Known limitations

- The Python socket guard is not an operating system network sandbox.
- The in-process controller cannot stop a worker that never returns.
- The PDF implementation counts page objects. It is not a layout or text
  parser.
- Synthetic proof does not establish parser quality on another corpus.
- The reference adapter is a contract example, not a production parser or a
  benchmark winner.
- Remote CI and fresh-clone checks remain external evidence. Their current
  status belongs in GitHub Actions, not in a timeless local claim.
