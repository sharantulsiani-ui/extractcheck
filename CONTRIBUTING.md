# Contributing

ExtractCheck accepts small changes that make document extraction easier to
test, reproduce or challenge.

## Keep the evidence public and synthetic

Do not commit source documents, private hashes, machine paths, email, extracted
private content, model files, parser caches or runtime output. A bug report or
test must use a generated fixture or the smallest safe synthetic reproducer.

## Make one claim at a time

A useful change has a narrow question and a test that can disprove it. State
what the change checks, what it does not check and which source locator proves
the result.

For an adapter change:

1. Keep native parser output apart from normalized units.
2. Validate every unit with `extractcheck.contracts.validate_unit`.
3. Compare the adapter with an independent source census.
4. Preserve unsupported, partial and failed states.
5. Add a regression test for every safety or scoring change.

## Run the checks

Use Python 3.11 or newer.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m extractcheck.cli synthetic --output ./example-output
PYTHONPATH=src python -m extractcheck.cli compare --output ./comparison-output
PYTHONPATH=src python tools/audit_release.py --release
python -m compileall -q src tests tools
```

The release audit is fail-closed. Run it from a clean source copy or a
`git archive`; a live checkout contains `.git`, which the audit rejects on
purpose.

## Open the change

Use the pull-request template. Keep the patch focused, name the evidence and
say what remains unproven. By participating, you agree to follow the
[code of conduct](CODE_OF_CONDUCT.md).
