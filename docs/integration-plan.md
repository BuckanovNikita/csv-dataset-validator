# Draft: integration into cveta2 and clearml-yolo

Status: proposed integration only. This package does not modify or import either consumer.

## Contract evidence

The implementation was grounded in cveta2 v0.8.0 at `55e56b3` and clearml-yolo at
`370d321`. These are source observations, not a guarantee about future revisions.

- cveta2: [record models and canonical columns](https://github.com/BuckanovNikita/cveta2/blob/55e56b3/cveta2/models.py),
  [lexical CSV reader](https://github.com/BuckanovNikita/cveta2/blob/55e56b3/cveta2/services/output.py),
  [public API](https://github.com/BuckanovNikita/cveta2/blob/55e56b3/cveta2/api.py).
- clearml-yolo: [CSV validation boundary](https://github.com/BuckanovNikita/clearml-yolo/blob/370d321/src/clearml_yolo/adapters/storage/dataset_records.py),
  [stage schemas](https://github.com/BuckanovNikita/clearml-yolo/blob/370d321/src/clearml_yolo/core/validation/schemas.py),
  [evaluation preparation](https://github.com/BuckanovNikita/clearml-yolo/blob/370d321/src/clearml_yolo/adapters/evaluation/scoring.py).

Python >=3.10 retains cveta2's interpreter floor. Pandera `>=0.34.1,<0.35` and
pandas >=2.1.1 intersect the inspected consumers' requirements. Resolve and test
each consumer's complete dependency graph when adopting; this package's lockfile
does not replace consumer lockfiles.

## Shared API boundary

Use `validate_dataframe(frame, profile=..., options=...)` for an existing DataFrame,
or `validate_csv(path, profile=..., options=...)` for lossless lexical CSV reading.
Both return `ValidationResult` with original clean/broken rows, positional lineage,
and all diagnostics. DataFrames may have duplicated index labels; translate findings
using positional IDs rather than joins on the original index.

No numeric coercion, class remapping, split assignment, latest-task selection,
background synthesis or remote I/O happens here. A consumer must explicitly choose
to proceed with `result.clean`; `is_valid=False` does not raise automatically.
Consumers needing a strict boundary should check `structural_errors` and
`broken_row_positions` and translate `issues` into their existing exception/report types.

For CSV, logical record number is `row_position + 2` (including the header), which
is not necessarily the physical line number for quoted multiline fields. Preserve
the report and input hash together before renumbering or exporting clean data.

## cveta2 adoption

1. Add this package as a dependency, preserving the current optional ClearML extra.
2. Validate `PartitionResult.dataset` after cveta2 has selected the latest eligible
   tasks, and validate `fetch_task()`'s returned DataFrame after assembly. Do not
   combine `dataset`, `obsolete`, `in_progress`, and `deleted` populations first.
3. Keep current task completion, deletion partitioning, upload-label preflight,
   unique image-stem enforcement and conversion eligibility checks in cveta2.
4. Add an explicit user-facing cleanup policy before replacing existing outputs.
   Store the original CSV and rejection report as evidence; write clean data to
   a new path. Upload and conversion currently use different minimum contracts,
   so do not automatically validate minimal upload manifests with the cveta2
   export profile, which requires shape, dimensions and bbox headers.

Example at an already completed fetch boundary (no service calls are required by
the validator):

```python
from ed_killer import ValidationOptions, validate_dataframe

validation = validate_dataframe(
    partition.dataset,
    profile="cveta2",
    options=ValidationOptions(check_images=False),
)
validation.clean.to_csv("dataset.validated.csv", index=False)
```

Fresh exports may leave split/path fields empty; this is valid in the cveta2
profile. `none` and `deleted` records retain their distinct meanings. Historical
tasks are separate duplicate/quarantine groups, and missing task IDs form their
own unscoped group. v0.8.0 polygon envelopes are ordinary `box` records: original
polygons cannot be recovered or validated from those CSV coordinates.

Intentional tightening: cveta2 permits out-of-image polygon envelopes, while the
agreed cleanup policy rejects the whole image/task containing such a box.
Rotated rectangles are compared using stored axis-aligned coordinates with a
warning, matching current conversion geometry rather than rotated polygon IoU.

## clearml-yolo adoption

1. Integrate at `adapters.storage.dataset_records.validate_ground_truth`, before
   constructing `ImageRecord` and `Box`. Supply the original CSV directory as
   `base_dir` for DataFrames, or call `validate_csv` directly.
2. Enable optional image inspection for a training boundary, or retain the
   existing image inspection and supply verified dimensions. Avoid decoding each
   image twice when choosing the final adapter design.
3. Retain native image format/minimum-size checks, required train/val populations,
   training-class coverage, class-map construction, source hashes, and source
   lineage. Do not reinterpret an empty clean frame as a trainable dataset.
4. Map positional findings to the existing `InvalidBox`/dataset diagnostics while
   also retaining original broken rows and quarantine relationships.
5. Keep prediction, evaluation, publication and results schemas in clearml-yolo.
   Their intentional treatment of raw malformed geometry, collapsed prediction
   boxes, reserved labels and unique IDs is not the standalone ground-truth contract.

```python
from ed_killer import ValidationOptions, validate_csv

validation = validate_csv(
    source_csv,
    profile="clearml-yolo",
    options=ValidationOptions(check_images=True, emit_warnings=False),
)
# Consumer-specific training eligibility and record construction follow here.
```

Three changes require explicit migration tests and release notes in the consumer:

| Current behavior | Standalone validator |
|---|---|
| Invalid boxes may leave an image represented as background | Any malformed annotation quarantines its whole image/task; no synthetic negatives |
| Training rejects exact same-label/box duplicates; evaluation uses class-agnostic IoU >0.99 | Keep first; reject later full-row or class-agnostic IoU >=0.99 duplicates |
| Training record conversion loses extra CSV columns | Clean/broken frames preserve extras and warn about unknown fields |

Existing clearml-yolo class vocabulary includes labels found only in dropped boxes.
Choose and document whether the future adapter preserves that vocabulary or derives
it from clean data. This package deliberately does not choose a class vocabulary.
Likewise, keep-first duplicate cleanup does not resolve conflicting labels by confidence.

## Adoption sequence and acceptance

First add fixtures and report-only comparisons in each consumer, with no population
changes. Then add an explicit cleanup path and compare old/new image, annotation,
class and split populations. Finally route the chosen boundaries through the shared
validator while retaining application-specific policy checks.

Fixtures must cover complete/sparse cveta exports; unassigned splits; historical
tasks; polygon envelopes outside images; rotated rectangles; Unicode and numeric-looking
labels; clearml backgrounds; path/split collisions; malformed geometry; duplicate
index labels; same/different-class overlaps below/at/above 0.99; and images whose
annotations all fail. Verify that conversion/training membership matches the
approved cleanup policy, not just that aggregate row counts match.

Before merging either adoption, run that repository's own full relevant tests and
release checks, compare reports on an agreed representative dataset, and record
the inspected revisions and population differences in dated evidence. No integration,
live service operation or consumer release is performed by this initial package task.
