# Threat Model

## Assets

- original documents and attachment payloads;
- private filenames, paths, identities, and message metadata;
- extracted prose, values, formulas, images, and embeddings;
- corpus-derived hashes and evaluation results;
- local machine availability and disk capacity.

## In-scope failures

- accidental source modification;
- output escaping the approved runtime;
- symlink and OOXML traversal;
- unbounded archive expansion;
- accidental Python network access;
- private fields entering checkpoints or reports;
- partial results being treated as success;
- nondeterministic or tampered controller state;
- output, disk, time, or RSS limits being ignored.

## Out of scope for the built-in controls

- a malicious native dependency or parser subprocess;
- kernel, filesystem, or administrator compromise;
- network enforcement outside Python socket entry points;
- denial of service by a hung in-process worker;
- cryptographic authentication against an attacker who can rewrite all files;
- complete safe parsing of adversarial Office/PDF documents.
- creation or repair of private Windows directory ACLs.

Use a process supervisor plus an OS sandbox, firewall/network namespace,
container, or VM when those threats matter.

## Privacy rules

- Public fixtures must be generated and obvious.
- Public reports must contain no private hashes; private hashes can be identifying.
- Control state must use opaque sample IDs and allowlisted status codes.
- Raw exception text from third-party parsers must not enter durable public
  evidence without sanitization.
- Runtime trees, model caches, native outputs, and source locators must remain
  untracked by default.
