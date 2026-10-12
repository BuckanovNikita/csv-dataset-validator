# Dataset schema

The public `schema_for(profile)` returns a `pandera.pandas.DataFrameSchema` for
`"cveta2"` or `"clearml-yolo"`. It recognizes the producer's complete 30-column
cveta2 format and the clearml-yolo additions below. Metadata headers are optional;
required headers remain required even for an empty dataset. Extra columns are
retained (`strict=False`); validation never coerces cells (`coerce=False`). Duplicate
column labels are invalid (`unique_column_names=True`). The validation API warns
about unknown columns separately from schema validation.

Types in this table describe cell semantics, not pandas dtypes. Numeric cells may
be native numbers or finite numeric strings; booleans are never numbers. Integral
values such as `12`, `12.0`, and `"12.0"` are accepted for integer fields. Boolean
metadata accepts native Python/NumPy booleans, case-insensitive `true`/`false`, and
numeric or lexical `0`/`1`. All checks preserve the original value.

An empty cell means `""`, `None`, `pd.NA`, or floating-point NaN. Whitespace and
literal strings such as `"NA"` and `"null"` are retained as data. No trimming or
replacement occurs. Optional metadata may be empty even for box annotations.

## cveta2 fields

“Required” identifies headers required by the cveta2 profile. The clearml-yolo
profile requires `image_name`, `image_path`, `instance_label`, all four coordinate
headers, and `split`; the other cveta2 fields are optional there.

| Field | Cell type | Empty allowed | Required | Additional semantics |
| --- | --- | --- | --- | --- |
| `image_name` | String | No | Yes | Bare filename; no `/` or `\`, and not `.` or `..`; lexical names and leading zeros are preserved. |
| `image_width` | Finite integer | No in cveta2; yes in clearml-yolo | Yes | Positive for active images; nonnegative for cveta2 deleted images. |
| `image_height` | Finite integer | No in cveta2; yes in clearml-yolo | Yes | Same dimension rules as `image_width`. |
| `instance_shape` | String enum | No in cveta2; yes in clearml-yolo | Yes | cveta2: `box`, `none`, `deleted`; clearml-yolo: `box`, `none`. |
| `instance_label` | String; also finite numeric value in clearml-yolo | Only negative/deleted rows | Yes | Nonempty on boxes; no numeric class restriction for clearml-yolo. |
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
| `split` | String enum | Yes in cveta2; no in clearml-yolo | No | `train`, `val`, `test`. |
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
| `image_path` | String | Yes in cveta2; no in clearml-yolo | No | Nonempty for clearml-yolo; relative and absolute local references are accepted. |
| `attributes` | JSON object string | Yes | No | A JSON map from strings to strings, including `{}`; the cell is preserved as supplied. |

The schema follows the field order in cveta2's `BBoxAnnotation` CSV export;
internal `frame_path` is not a CSV field.

## clearml-yolo additions

| Field | Cell type | Empty allowed | Required | Additional semantics |
| --- | --- | --- | --- | --- |
| `width` | Finite integer | Yes | No | Positive when provided; an alternative image width for local bounds checks. |
| `height` | Finite integer | Yes | No | Positive when provided; an alternative image height for local bounds checks. |
| `source_row_id` | Opaque identifier | Yes | No | Retained provenance; standalone ground-truth validation imposes no consumer-stage uniqueness or numeric format. |

## Conditional annotation checks

cveta2 `box` rows require a label and all four coordinates. `none` and `deleted`
rows require the label and all four coordinates to be empty. Sparse producer
metadata is valid, and any supplied metadata is checked using the same field
rules as box rows. Valid `deleted` rows may use zero image dimensions. They are
rejected by the clearml-yolo profile.

clearml-yolo supports explicit negatives with a completely empty label and all
four coordinates empty. If `instance_shape` is absent or empty, this pattern
identifies the negative; a supplied `none` shape requires that pattern. A supplied
`box` shape requires a populated box. A partial annotation is invalid. Validation
never synthesizes a negative row from removed or malformed annotations.

Boxes must have finite, nonnegative coordinates and positive, finite derived
width, height, and area. Image upper
bounds, repeated dimensions, split ownership, task quarantine, duplicates, and
optional local image inspection are separate validation checks. Schema checks
do not clip boxes or contact remote services.

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
discard extras, or replace the caller's index. Clean and broken outputs remain
subsets of the original rows; numeric parsing and JSON decoding are used only
to decide whether a cell satisfies its contract.

Exact-row comparison supports scalar values and nested lists, tuples, dictionaries,
sets, NumPy arrays, binary buffers, and pandas Series/DataFrame/Index cells. Container
type, labels, names and contents are compared structurally; numeric storage dtypes
do not determine equality. For opaque objects or cyclic structures, a row-level
`exact_comparison_unavailable` warning records the skipped exact comparison. Original
cells remain intact and box IoU checking continues. The row is not rejected merely
because an extra field cannot be compared.
