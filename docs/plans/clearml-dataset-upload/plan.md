# ClearML dataset upload

Status: implemented, reviewed, locally verified and released as v0.6.0. Live ClearML/S3 unverified.
Approved conversational design, resumed 2026-10-20.

## Contract

Add `ed-killer-upload FETCH_DIR --project PROJECT`. Input is the complete cveta2
fetch partition (`dataset.csv`, `obsolete.csv`, `in_progress.csv`, `deleted.csv`).
The incoming snapshot replaces annotations and task lists. Select the dataset
interactively, defaulting to `dataset`, or accept `--dataset-name`. Inherit the latest
finalized version's configuration and alias history. The new version contains only
`dataset.csv`, `dataset.yaml`, and `tasks.yaml`; parent contents remain unchanged.
This exact three-file default resolves the final unanswered design choice.

`dataset.yaml` contains `api_url`, `classes: {name: {prod_id, empty, alt_names}}`,
and `images: {local_root: [...], s3_root: [...]}`. Fetch the class API without
authentication. Class identity is API `number`, never `id`. Generate initial
definitions with `empty: false`; let the user identify empty classes. On later
uploads explain and confirm each changed definition. Renames append the old name
to aliases, preserve historical aliases and the empty flag, and remove the new
canonical name from aliases. Missing API numbers and ambiguous names/aliases block
upload. Canonicalize labels before geometry conflicts/deduplication. Unknown or
empty classes quarantine whole images; explicit negatives remain supported.

Roots are independent, never inferred mirrors. Check all local/S3 roots by default,
but not individual S3 objects. All input image paths must be under approved local
roots after symlink resolution; offer specific extensions and recheck. Unresolved
coverage blocks the whole upload, including when those rows would be rejected.
Check supplied S3 references against S3 roots. Preserve absolute cveta2 image paths;
reject relative upload paths, since moving the CSV would change their meaning.
Local files are checked for readable image content, native supported extensions
and minimum side 10 pixels. Missing split assignments block upload; no split
generation. Require train and val populations and at least one training box after
cleanup. Keep established coordinate repairs and duplicate-only cleanup.

Reports are local and written before partial-upload consent. `broken-images.csv`
contains all original rows and columns for any image with a rejected record.
`report.json` records positional reasons, changes, counts, and blockers.
No remote dataset is created until all questions/checks and explicit partial-upload
consent succeed. EOF/decline is cancellation, never implied consent. Do not upload
an empty or untrainable remainder. Exit 0 means finalized, 1 cancelled, 2 blocked/error.

`tasks.yaml` lists sorted unique `included` IDs from final clean rows and `obsolete`
completed task IDs whose every represented image is superseded by a higher task
ID's annotations or deletion in the original fetch evidence. Partially superseded,
unfinished and validation-only excluded tasks are not obsolete. Never resurrect
older annotations after the newest annotations fail.

## Architecture

See [architecture.json](architecture.json). The existing validator and facade stay
offline and compatible. New `ed_killer.upload` owns typed records, pure class/task
policy, bundle validation, a workflow over typed ports, and outer adapters.
Only remote adapters import HTTP/ClearML/S3 clients. Filesystem adapters own YAML,
root resolution and reports; existing optional local media inspection remains
owned by `ed_killer.media`. CLI constructs dependencies and owns prompts.
No consumer application imports. Extend exhaustive import rules and mutation tests.
An optional `clearml` dependency extra supplies upload dependencies. Permit PyYAML
for this feature without weakening release tooling isolation.

## Work and ownership

- [x] Inspect clone, remote, existing changes, source and native process.
- [x] Record and validate architecture planning gate.
- [x] Parent: shared models/ports and behavioral contract tests.
- [x] Policy delegate: classes/tasks and their focused tests.
- [x] Remote delegate: HTTP/ClearML/S3 adapters and focused adapter tests.
- [x] Validation delegate: training bundle validation and local-root checks/tests.
- [x] Parent: files, workflow, interactive CLI, packaging and import contracts.
- [x] Parent: documentation and complete integrated verification.
- [x] Fresh independent review after integration and successful checks.
- [x] Reconcile architecture acceptance and dated evidence.
- [x] Native release, explicit branch/tag pushes and task-resource cleanup.

Shared interfaces precede the three independent implementation workstreams.
Delegates have exclusive file ownership and cannot delegate further. Parent owns
integration, all shared metadata, final checks and release.

## Acceptance

Use Python 3.12 development and retain Python >=3.12,<3.14, uv/lockfile and Hatchling.
Run pytest, ruff check/format-check, strict mypy, vulture, import-linter, lock-check
and build. Exercise real CLI and isolated wheels without/with upload dependencies,
and both supported Python minors. Test rename chains/reversions, class collisions,
empty aliases, missing API records, task supersession/deletion/validation exclusion,
root boundaries/symlinks/extensions, no default S3 object probes, preserved reports,
duplicates, trainability, cancellation, exact child file manifests and parent
preservation, and upload/finalization failure. Use controlled real HTTP and owned
ClearML/S3 integration resources where available; mocked tests do not prove remote
upload. Missing live evidence remains an explicit acceptance gap.

Update Russian README and English schema/integration/development instructions.
Validate Markdown, local links and executable examples. Record dated results in
`docs/evidence/2026-10-20-clearml-dataset-upload.md`. No version edits by hand;
the installed native release hooks own versions/tags and do not push automatically.

## Integration observations

The local test-stand registry has no authorized ED Killer ClearML/S3 identity.
Live publication remains unverified; recorded checks cover real local/HTTP/package
boundaries and explicit SDK doubles. See [dated evidence](../../evidence/2026-10-20-clearml-dataset-upload.md).
The upload validator directly owns supplemental image-header checks; the existing
media module still owns pixel decoding. `validation -> paths` is an explicit local
filesystem dependency. CI prepares the upload extra and retains it with no-sync.

The native hooks created feature commit `99f9918`, release commit `8448478` and
annotated tag `v0.6.0`. The branch and explicit tag were pushed atomically. Temporary
verification environments were removed; no live service datasets were created.
