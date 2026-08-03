# Methodology

## Purpose

The harness evaluates extraction evidence before retrieval. Its primary
question is not “how much text did the parser emit?” but “which source
structures survived, with what locator and identity evidence?”

## Evaluation layers

1. **Manifest:** select bounded inputs and record only opaque identity, format,
   byte size, and SHA-256 in controller state.
2. **Independent census:** inspect source container structure without retaining
   prose, cell values, or formula expressions.
3. **Native evidence:** preserve a parser's original structured output without
   silently flattening it.
4. **Normalized evidence:** map parser output to typed units with sheet/cell,
   slide/shape, or page/block locators.
5. **Comparison:** score values and structures against the independent census.
6. **Hard cases:** select deterministic strata for formulas, charts, tables,
   ordering, image-only pages, and provenance round-trip.
7. **Retrieval gate:** only after extraction passes, test real questions and
   source-evidence round-trips.

## Why hashes

A private corpus cannot usually be published as a benchmark. Hashing allows a
local evaluator to compare exact normalized values without retaining those
values in the durable scoring record. Hashes do not anonymize low-entropy data;
keep them private when they were derived from private content.

The public synthetic report contains only hashes of generated fixtures. A
private deployment should keep every corpus-derived hash in an ignored,
owner-only runtime.

## Denominators

Use the source structure as the denominator:

- spreadsheet value and locator recall: non-empty source cells;
- formula recall: source formula cells, with expression identification scored
  separately from a cached value at the same coordinate;
- slide ordering: source slides or source text atoms;
- table recall: source table cells;
- PDF text recall: native source blocks on the correct page;
- provenance: units with a locator that round-trips to source structure.

Report weighted and per-item results separately. File-level macro averages can
hide failure in high-cardinality documents.

## Determinism

Rerun a fixed sample with the same locked environment. Compare both native and
normalized uncompressed byte streams by SHA-256 and byte size. A deterministic
gzip wrapper alone is insufficient if the uncompressed parser output changes.

## Failure semantics

“Not emitted” means the extractor did not provide evidence. It never proves the
source lacked that structure. Preserve unsupported, partial, and provenance-
incomplete states rather than converting them to empty success.
