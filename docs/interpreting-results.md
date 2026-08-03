# Interpreting Results

## A parser can win one dimension and lose another

A flattened extractor may have high value recall and zero exact cell
provenance. A layout parser may improve reading order while dropping table
cells during normalization. Choose per-format capabilities; avoid a single
unqualified “winner.”

## Value presence is not structure recovery

- A cached spreadsheet result is not a recovered formula expression.
- A number that also appears in chart XML is not a recovered chart.
- Slide text without shape identity is not shape provenance.
- Page attribution without a bounding box is not block-level provenance.

Score these separately.

## Empty is ambiguous

An empty parser output can mean an empty source, unsupported structure,
encrypted content, image-only content, malformed input, missing dependency, or
an extraction failure. The evaluator should retain the distinction.

## Combined systems need a merge contract

Concatenating two parser outputs inflates duplicates and leaves provenance
conflicts unresolved. A combined architecture needs typed locators, deterministic
routing, explicit precedence, duplicate handling, and disagreement evidence.

## Do not generalize a private workload

A private evaluation helps select an architecture for that archive. It is not a
universal parser leaderboard. Compare broader claims against public benchmarks
with published data and evaluation code.
