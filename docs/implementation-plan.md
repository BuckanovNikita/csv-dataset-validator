# Approved implementation plan

Build a standalone Pandera package and CLI; do not modify cveta2 or clearml-yolo.
The reference contracts are cveta2 v0.8.0 (55e56b3) and clearml-yolo (370d321).

## Decisions

- Explicit cveta2 and clearml-yolo profiles; all 30 cveta2 fields recognized, metadata optional.
- Preserve lexical CSV values, extra columns, raw rows and index labels; use positional lineage.
- Warn about unknown fields. Return clean/broken frames and all structured reasons without
  raising for ordinary invalid rows.
- Absolute pixel XYXY geometry. Reject outside-image boxes when dimensions are available.
  Report skipped upper-bounds checks when dimensions are unavailable.
- Optional local image inspection; no network access or mandatory image dependency.
- Malformed annotations quarantine their entire image/task. Duplicates are an exception:
  retain the first valid representative and reject later full-row or class-agnostic IoU >=0.99
  duplicates. Ignore rotation for IoU with a warning. Never synthesize negative images.
- Separate task histories; missing task IDs form an unscoped group within each image.
- In-memory processing above one million rows, with bounded per-group IoU memory.
- CLI optional clean.csv, broken.csv and report.json; default cleanup exit 0, strict invalid
  data exit 1, unusable structure/input exit 2. Explicit overwrite only.
- Python >=3.10, uv/hatchling, Pandera 0.34, strict typing, behavioral tests and documented API.

## Workstreams and acceptance

1. Parent: scaffold and stable issue/options/result interfaces.
2. Parallel bounded ownership: schema and schema tests; geometry/media and their tests.
3. Parent: validation orchestration, CSV reader, report writer, CLI, integration draft.
4. Parent: integrated tests, Python 3.10/3.12 checks, package builds, performance evidence.
5. Fresh independent final review; resolve findings, reverify, then task-scoped commit.

No remote creation, pushes, tags, package publication, or consumer repository modifications.

## Architecture adoption amendment — 2026-10-12

The user added module architecture acceptance requirements after implementation and
the corrected runtime's independent review. Preserve that completed history; the
[architecture record](architecture.json) records inspected, already-applied modules.
The existing import contract protects core validation from CSV, report and CLI I/O.

Remaining acceptance work, in dependency order:

1. Parent: validate the architecture planning record before adding contract checks.
2. Parent: extend import-linter to cover every child module, with independent peers;
   check the public facade separately and exercise prohibited imports in temporary copies.
3. Parent: run architecture, behavioral, packaging and documentation checks; reconcile
   the complete task-owned diff with the record and dated evidence.
4. Fresh read-only reviewer: accept module responsibilities, effects and dependency
   contracts after parent verification; then validate the acceptance record and commit.

Models and cell helpers are independent foundations. Schema, geometry and media are
independent peers; validation composes their explicit interfaces. CSV input and report
output are independent adapters below CLI composition. Media owns optional local image
reads; validation deliberately calls it when requested through options. Validation owns
warning emission, lexical path identity and optional filesystem path/symlink canonicalization;
neither consumer application is a dependency. A source-level import guard enforces consumer
independence, and a separate import-linter contract keeps reporting independent of validation.
The facade only re-exports APIs, and the module entrypoint owns process exit. No network
adapter or service locator is introduced.

## Acceptance

Implementation, documentation, behavioral verification and architecture acceptance are
complete. Fresh independent runtime and architecture reviews returned ship after the
documented corrections. See [dated evidence](evidence/2026-10-12-verification.md) for
executed checks, limitations and review reconciliation. The final repository action is
the authorized task-scoped Conventional Commit; consumer integration remains deferred.
