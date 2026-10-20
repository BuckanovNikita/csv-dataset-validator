# ClearML dataset bundles

`ed-killer-upload` validates a complete cveta2 fetch export and creates a finalized
ClearML dataset version containing exactly `dataset.csv`, `dataset.yaml`, and
`tasks.yaml`. It replaces the annotation snapshot and task manifest, while inheriting
configuration and historical class names from the latest finalized version.
It never imports cveta2 or clearml-yolo. The base library and `ed-killer` stay offline.

## Install and invoke

```bash
uv sync --locked --dev --extra clearml
uv run --locked --no-sync ed-killer-upload ./fetch-output \
  --project 'Quality inspection' \
  --dataset-name dataset \
  --api-url https://classes.example.org/api/classes \
  --local-root /data/images \
  --s3-root s3://inspection-images/production \
  --output-dir ./validated-output
```

The upload extra installs ClearML with S3 support, Pillow and PyYAML. When installing
from a checkout into another environment, use `uv pip install '.[clearml]'`.
Configure the ClearML SDK and S3 access through their normal external configuration;
credentials do not belong in the dataset YAML or CLI URL. The class API is a public,
unauthenticated HTTP(S) GET returning a JSON list of class definitions.

`FETCH_DIR` and `--project` are required. Without `--dataset-name`, the command shows
existing finalized dataset names and prompts, defaulting to `dataset`. It retrieves
configuration from the latest finalized, nonarchived version of that exact project
and dataset name. A parent without `dataset.yaml` blocks the update.

`--api-url` overrides the inherited URL or supplies the initial one; otherwise the
initial URL is prompted. Repeatable `--local-root` and `--s3-root` extend saved roots.
Changes to saved configuration require confirmation. Local roots are canonicalized
to absolute paths. Without `--output-dir`, a unique directory beside the source
directory holds the reports. An existing output directory is always refused.

## Source and resulting files

The source must contain all four valid UTF-8 CSV files:

| File | Use |
| --- | --- |
| `dataset.csv` | Current annotations; the only source of training rows |
| `obsolete.csv` | Historical task/image evidence |
| `in_progress.csv` | Unfinished task evidence |
| `deleted.csv` | Deletion and completion evidence |

An empty partition still needs a valid CSV header. Literal strings, extra columns,
record order and original cells are preserved. CSV quoting errors, duplicate or
empty headers, and rows with the wrong field count block processing. No source file
is overwritten. The producer must already assign valid `train`, `val`, or `test`
splits and absolute local `image_path` values. This command does not generate splits.
The standalone validator still supports its documented relative paths.

Example `dataset.yaml`:

```yaml
api_url: https://classes.example.org/api/classes
classes:
  Периодическая Царапина:
    prod_id: 93
    empty: false
    alt_names:
      - Старое имя царапины
images:
  local_root:
    - /data/images
    - /data/older-images
  s3_root:
    - s3://inspection-images/production
    - s3://archive-images/inspection
```

All YAML keys and value types are validated; duplicate keys are errors. Image root
lists are independent, with no inferred local-to-S3 mapping.

The API record corresponding to that class can be:

```json
{"id":4,"number":93,"name":"Периодическая Царапина","techClass":false,"isPeriodical":true,"isCritical":false,"threshold":1.0}
```

`prod_id` matches **number**, never `id`. Initial class definitions default to
`empty: false`, with a separate prompt to mark each class empty/excluded. On later
versions each new or renamed class requires confirmation. Renames follow the stable
number: the previous canonical name joins `alt_names`, earlier aliases and `empty`
are preserved, and the current canonical name is removed from aliases. Duplicate
numbers/names, missing previous numbers and aliases identifying multiple classes
block publication. Declining reconciliation cancels.

Canonical names replace known aliases before class-conflict and duplicate checks.
Unknown labels and labels marked empty, including their aliases, quarantine the
whole image. Explicit background rows with all five annotation cells empty remain
valid. API policy fields other than `number` and `name` do not imply training flags.

Example `tasks.yaml`:

```yaml
included:
  - 20
  - 21
obsolete:
  - 12
  - 18
```

IDs are sorted, unique, nonnegative integers; integral lexical numbers such as
`12.0` are accepted. `included` comes from the final clean rows. `obsolete` requires
a completed task whose every represented image was superseded by a higher task ID's
completed annotations or deletion in the original four partitions. A higher deletion
can supersede even when its task remains unfinished. Completion uses explicit
`task_completed`, or legacy `job_stage=acceptance` and `job_state=completed` when the
explicit value is missing. Conflicting, unknown or unfinished task evidence fails
closed; membership in `in_progress.csv` disqualifies completion.

Partial supersession, membership in `obsolete.csv` alone, and validation rejection
are insufficient to mark a task obsolete. Removed new annotations never resurrect
old annotations. Task lists are recomputed for this snapshot, not accumulated from
the parent's manifest.

## Checks, consent and publication

Every configured local directory and S3 bucket/prefix is checked. A nonempty S3
prefix must have at least one listed entry under its directory boundary. An empty
accessible bucket is valid. Individual S3 image objects are not probed.

All current input image paths must be covered by local roots before annotation
filtering, including paths on rows that will be rejected. Containment resolves
symlinks and checks directory ancestry. Outside paths are listed with proposed parent
directory additions. Accept them or enter another root and revalidate; unresolved
coverage cannot be bypassed through partial upload. Nonempty `s3_image_path` references
must likewise fall under configured S3 roots.

Local images must exist, decode, use a supported native format and have both sides
at least 10 pixels. Clearml-yolo geometry, cross-class conflict, image quarantine and
bounded clipping rules still apply. Later same-class duplicates are removed without
rejecting the retained representative. Missing or invalid split assignments block
the entire snapshot. After cleanup, train and val must both contain images, and at
least one valid training box must remain.

Before asking to upload a partially valid snapshot, the command writes:

| Local file | Contents |
| --- | --- |
| `dataset.csv` | Clean annotations with canonical class names and accepted repairs |
| `dataset.yaml` | Reconciled class definitions, API URL and approved roots |
| `tasks.yaml` | Task inclusion and supersession evidence |
| `broken-images.csv` | Every original row and column of every image with a rejected record |
| `report.json` | Original row positions, reasons, repairs, class changes, counts and blockers |

The broken-image CSV intentionally overlaps clean output for duplicate-only cases:
the retained row remains part of that image's complete original evidence. Reasons
are in JSON; no columns are added to the original broken-image CSV.
Reports remain after cancellation or publication failure.

Rejected records require an explicit yes to upload only the valid portion; the
default answer is no. EOF and interruption cancel. Structural, class identity,
root, task provenance and trainability errors cannot be overridden with this consent.

Only after checks and consent does the adapter create a child with its parent ID,
clear inherited child file/link entries, add the three bundle files, and verify the
exact manifest. Parent contents remain intact. Images, source partitions and rejection
reports are never uploaded. Upload and finalization are synchronous; failure reports
the created dataset ID when available, retains local reports, and does not silently
retry the mutation. Inspect that ID before rerunning after a network failure.
Interruption after child creation keeps cancellation exit code 1 and reports that
ID with an uncertain remote state; it does not assume the server rolled back.

| Exit code | Meaning |
| --- | --- |
| `0` | New dataset finalized successfully |
| `1` | Cancelled or required consent declined |
| `2` | Input/configuration/check/publication failure |

SDK behavior is documented in the official [Dataset reference](https://clear.ml/docs/latest/docs/references/sdk/dataset/)
and [StorageManager reference](https://clear.ml/docs/latest/docs/references/sdk/storage/).
Implementation decisions and verification scope are recorded in the
[native plan](plans/clearml-dataset-upload/plan.md).
