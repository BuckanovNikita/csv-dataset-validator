# Dataset schema

The public `schema_for(profile)` returns a `pandera.pandas.DataFrameSchema` for
`"cveta2"` or `"clearml-yolo"`. It recognizes the producer's complete 30-column
cveta2 format. The clearml-yolo profile validates only its eight required fields and
four optional dimension fields below; every other field is ignored metadata. Required
headers remain required even for an empty dataset. Extra columns are
retained (`strict=False`); validation never coerces cells (`coerce=False`). Duplicate
column labels are invalid (`unique_column_names=True`). The cveta2 validation API warns
about unknown columns separately from schema
validation; clearml-yolo emits no metadata warnings.

Types in this table describe cell semantics, not pandas dtypes. Numeric cells may
be native numbers or finite numeric strings; booleans are never numbers. Integral
values such as `12`, `12.0`, and `"12.0"` are accepted for integer fields. Boolean
metadata accepts native Python/NumPy booleans, case-insensitive `true`/`false`, and
numeric or lexical `0`/`1`. Direct schema checks preserve the original value;
clearml-yolo validation API repairs
are described below.

An empty cell means `""`, `None`, `pd.NA`, or floating-point NaN. Whitespace and
literal strings such as `"NA"` and `"null"` are retained as data. No trimming or
replacement occurs. Optional metadata may be empty even for box annotations.

## cveta2 fields

This table describes cveta2 only. “Required” identifies headers required by that
profile. The separate clearml-yolo contract below replaces these rules for that profile.

| Field | Cell type | Empty allowed | Required | Additional semantics |
| --- | --- | --- | --- | --- |
| `image_name` | String | No | Yes | Bare filename; no `/` or `\`, and not `.` or `..`; lexical names and leading zeros are preserved. |
| `image_width` | Finite integer | No | Yes | Positive for active images; nonnegative for cveta2 deleted images. |
| `image_height` | Finite integer | No | Yes | Same dimension rules as `image_width`. |
| `instance_shape` | String enum | No | Yes | `box`, `none`, `deleted`. |
| `instance_label` | String | Only negative/deleted rows | Yes | Nonempty on boxes. |
| `bbox_x_tl` | Finite number | Only negative/deleted rows | Yes | Absolute pixel left coordinate; nonnegative. |
| `bbox_y_tl` | Finite number | Only negative/deleted rows | Yes | Absolute pixel top coordinate; nonnegative. |
| `bbox_x_br` | Finite number | Only negative/deleted rows | Yes | Right coordinate; greater than `bbox_x_tl`. |
| `bbox_y_br` | Finite number | Only negative/deleted rows | Yes | Bottom coordinate; greater than `bbox_y_tl`. |
| `task_id` | Finite integer | Yes | No | Nonnegative; task grouping is handled by the validation API. |
| `task_name` | String | Yes | No | Informational text. |
| `job_stage` | String enum | Yes | No | `annotation`, `validation`, `acceptance`. |
| `job_state` | String enum | Yes | No | `new`, `in progress`, `completed`, `rejected`. |
| `task_completed` | Boolean | Yes | No | Boolean metadata semantics described above. |
| `task_updated_date` | String | Yes | No | Producer-supplied informational text; no date parsing. |
| `created_by_username` | String | Yes | No | Informational text. |
| `frame_id` | Finite integer | Yes | No | Nonnegative. |
| `split` | String enum | Yes | No | `train`, `val`, `test`. |
| `subset` | String | Yes | No | Free text; distinct from `split`. |
| `occluded` | Boolean | Yes | No | Boolean metadata semantics described above. |
| `z_order` | Finite integer | Yes | No | Integral; negative values are permitted. |
| `rotation` | Finite number | Yes | No | Inclusive range `[0, 360]` degrees. |
| `source` | String | Yes | No | Free text; no restricted source enum. |
| `annotation_id` | Finite integer | Yes | No | Nonnegative. |
| `confidence` | Finite number | Yes | No | Inclusive range `[0, 1]`. |
| `issue_text` | String | Yes | No | Informational text. |
| `issue_state` | String enum | Yes | No | `open`, `resolved`, `open \| resolved`, `resolved \| open`, or upload value `new`. |
| `s3_image_path` | String | Yes | No | Informational reference; no remote access. |
| `image_path` | String | Yes | No | Relative and absolute local references are accepted. |
| `attributes` | JSON object string | Yes | No | A JSON map from strings to strings, including `{}`; the cell is preserved as supplied. |

The schema follows the field order in cveta2's `BBoxAnnotation` CSV export;
internal `frame_path` is not a CSV field.

## clearml-yolo training fields

| Field | Cell type | Empty allowed | Required | Additional semantics |
| --- | --- | --- | --- | --- |
| `image_name` | String | No | Yes | Bare filename, as for cveta2. |
| `image_path` | String | No | Yes | Relative or absolute local reference; URI content is never downloaded. |
| `instance_label` | String or finite numeric value | Only explicit negative rows | Yes | No restriction to numeric classes. |
| `bbox_x_tl`, `bbox_y_tl`, `bbox_x_br`, `bbox_y_br` | Finite number | Only explicit negative rows | Yes | Absolute XYXY coordinates; left/top must be nonnegative after any accepted repair. |
| `split` | String enum | No | Yes | `train`, `val`, `test`. |
| `image_width`, `image_height`, `width`, `height` | Finite integer | Yes | No | Positive when provided; alternative dimension names must agree for the image. |

Every other column is retained but ignored, even when its name occurs in the cveta2
schema. This includes `instance_shape`, `task_id`, `rotation`, `confidence`,
`source_row_id`, `issue_state`, `issue_text`, and their arbitrary combinations. Metadata
cannot reject rows, cause warnings, isolate tasks, or change duplicate decisions.

## Conditional annotation checks

cveta2 `box` rows require a label and all four coordinates. `none` and `deleted`
rows require the label and all four coordinates to be empty. Sparse producer
metadata is valid, and any supplied metadata is checked using the same field
rules as box rows. Valid `deleted` rows may use zero image dimensions. cveta2 boxes
require finite nonnegative coordinates and positive finite width, height and area.
The cveta2 profile never repairs coordinates.

clearml-yolo explicit negatives have a completely empty label and all four coordinates
empty, regardless of ignored shape metadata. Partial annotations are invalid. Box
width must be finite and strictly greater than 2 pixels; height must be finite and
strictly greater than 2 pixels; area must be finite and strictly greater than 2 square
pixels. Validation never synthesizes negatives from removed or malformed annotations.

Direct `schema_for` validation is nonmutating and rejects negative coordinates.
`validate_dataframe` and `validate_csv` can first repair clearml-yolo boxes with known,
trustworthy image dimensions. Each crossed edge must overflow by strictly less than
10 pixels, including negative left/top edges; every edge must meet this limit. The
original box must have finite, correctly ordered coordinates and meet the minimum
geometry. The clipped box must also meet all minimums. Unknown or conflicting dimensions,
nonfinite coordinates, reversed edges and undersized boxes are never repaired. With
`check_images=True`, inspected local image sizes can supply bounds; disagreements with
CSV dimensions prevent repair. These base validation APIs do not contact remote services.

For clearml-yolo, malformed annotations quarantine their entire image, without task
isolation. Cross-class pairs with IoU at or above the configured threshold (default
0.99) receive `class_conflict` at both endpoints and quarantine the image. This check
runs before pruning duplicates. Within each image and class, exact or near duplicates
at or above the threshold keep the earliest input row; later rows are compared only
against retained representatives. Metadata is irrelevant, and accepted repairs are
included in geometry comparisons. cveta2 retains its image/task quarantine and full-row
or class-agnostic IoU duplicate rules.

Image identity, upper bounds, repeated dimensions, split ownership and optional
local image inspection remain inter-row or adapter checks, separate from the direct
field schema. Public API and CLI signatures are unchanged.

## Diagnostics and preservation

Internal `schema_issues` validates a positional `RangeIndex` copy supplied by the
validation API and collects failures lazily, so one row can have several reasons.
Missing headers produce dataset-level `missing_column` issues with no row
position. Row findings use zero-based input positions, never caller index labels.
Repeated Pandera cell failures for one row-level check are collapsed into one
issue with the relevant annotation or dimension columns.

Stable schema reason codes include `invalid_image_name`, `invalid_image_path`,
`invalid_text`, `invalid_shape`, `invalid_label`, `missing_bbox`,
`invalid_coordinate`, `negative_coordinate`, `invalid_box_area`,
`invalid_negative`, `invalid_dimension`, `invalid_integer`, `invalid_boolean`,
`invalid_rotation`, `invalid_confidence`, `invalid_attributes`, `invalid_split`,
`invalid_job_stage`, `invalid_job_state`, and `invalid_issue_state`.

Schema validation does not emit warnings, modify input cells, reorder rows,
discard extras, or replace the caller's index. The validation APIs preserve input and
broken cells exactly. Clean rows preserve untouched cells and contain only accepted
clearml-yolo coordinate repairs. `bbox_clipped` warnings identify changed fields and
old/new coordinates only for retained repaired rows. Repair-only results have
`is_valid=True`; rejected duplicates make `is_valid=False` and retain strict CLI exit 1.
Other numeric parsing and cveta2 JSON decoding do not replace source values.

For cveta2, exact-row comparison supports scalar values and nested lists, tuples,
dictionaries,
sets, NumPy arrays, binary buffers, and pandas Series/DataFrame/Index cells. Container
type, labels, names and contents are compared structurally; numeric storage dtypes
do not determine equality. For opaque objects or cyclic structures, a row-level
`exact_comparison_unavailable` warning records the skipped exact comparison. Original
cells remain intact and box IoU checking continues. The row is not rejected merely
because an extra field cannot be compared.

## Extended ClearML upload bundle

The optional `ed-killer-upload` command wraps this base contract with class metadata,
image-root containment, mandatory local image checks, split/trainability gates and
task provenance. Its `dataset.csv` preserves extra columns but may normalize class
aliases as well as apply accepted coordinate repairs. Its `dataset.yaml` records
API numbers, empty-class flags, historical aliases and independent image roots;
`tasks.yaml` records included and fully superseded completed tasks.
See [the upload schema and workflow](upload.md) for exact fields and blocking rules.
These additional rules do not change the standalone validator's metadata handling.
