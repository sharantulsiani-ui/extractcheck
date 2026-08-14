# Interpreting Results

## A parser can win one dimension and lose another

A flat-text extractor may recover many values but lose every cell address. A
layout parser may improve reading order while dropping table cells. Judge each
format on its own. Do not name one winner without qualifications.

## Value presence is not structure recovery

- A cached spreadsheet result is not a recovered formula expression.
- A number that also appears in chart XML is not a recovered chart.
- Slide text without shape identity is not shape provenance.
- Page attribution without a bounding box is not block-level provenance.

Score these separately.

## Empty is ambiguous

An empty parser output has several possible causes. The source may be empty,
encrypted, malformed or made only of images. The parser may not support the
structure, may lack a dependency or may have failed. Keep those cases separate.

## Combined systems need a merge contract

Concatenating two parser outputs inflates duplicates and leaves provenance
conflicts unresolved. A combined architecture needs typed locators, deterministic
routing, explicit precedence, duplicate handling, and disagreement evidence.

## Do not generalize a private workload

A private evaluation helps select an architecture for that archive. It is not a
universal parser leaderboard. Compare broader claims against public benchmarks
with published data and evaluation code.
