# Initial validation evidence — 2026-10-12

This is dated implementation evidence, not an evergreen performance guarantee.
No consumer application or live CVAT/ClearML service was modified or exercised.

## Checks completed

- Python 3.12.13 and Python 3.10.20: complete suites of 169 tests passed on each
  after the architecture amendment (151 runtime tests and 18 architecture/documentation checks).
- Ruff lint and format checks, strict mypy on both interpreter environments,
  Vulture, import-linter, and lock freshness passed.
- Wheel and source distribution built. Wheel includes `py.typed`; source distribution
  includes the integration draft. Neither includes environments or temporary evidence.
- Installed-wheel API and both console/module entrypoints passed in an isolated
  environment without Pillow. Image inspection requested without the optional
  dependency produced the documented actionable input error.
- Local documentation links were checked. External source links identify the
  inspected revisions; no public access to private repository links is implied.

Python 3.12 resolved pandas 3.0.6 and NumPy 2.5.4; Python 3.10 resolved pandas 2.3.3
and NumPy 2.2.6. Both used Pandera 0.34.1. The lockfile records exact dependencies.
GitHub Actions configuration is supplied but has not been run remotely.

## Architecture adoption and review

The user introduced the architecture-record requirement after runtime implementation.
The original plan was preserved and amended. The planning record was validated before
the added contract configuration and tests. No runtime code changed in this amendment.

Commands executed successfully:

- `uv run lint-imports`: all three contracts kept; all 11 package modules inspected.
- `uv run pytest tests/test_architecture.py`: 18 checks passed. Temporary source copies
  proved the real linter rejects schema-to-CSV, report-to-CSV, model-to-geometry and
  geometry-to-media imports, plus report-to-validation imports. The unmodified control
  copy passed. Facade checks also rejected a CLI import, logging configuration and an
  executable export assignment.
- `uv run --python 3.12 pytest`: 169 passed.
- `UV_PROJECT_ENVIRONMENT=.superpowers/verification/py310 uv run --python 3.10 --frozen pytest`:
  169 passed in a separate task-owned environment.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run vulture`,
  `uv lock --check`, and `uv build`: passed. Strict mypy also passed in Python 3.10.
- The documentation link check is included in the architecture suite; root and docs
  Markdown links to local files resolved within the repository.

The initial import-test harness attempted an unavailable `python -m importlinter`
entrypoint and failed before checking contracts. It was corrected to call the installed
CLI entry function through the current interpreter; all positive and negative controls
then passed. No production changes were needed.

Architecture review returned **fix-first** after showing that report-to-validation imports
and imports of the consuming applications were not covered by the original contracts.
The parent reproduced the missing report boundary with a failing negative test, then
added the scoped prohibition and source-level consumer import checks. The guard covers
module/submodule imports, aliases, ImportFrom, type-only and lazy imports of both
consumer namespaces without requiring either application to be installed. Both checks
now reject their negative controls. The record also now describes validation's opt-in
filesystem path/symlink canonicalization; runtime behavior remains unchanged.

A fresh read-only reviewer (`review_architecture_corrections`, requested GPT-6.1 Sol/high;
runtime settings not independently observable) returned **ship** with no blocking
architecture findings. The reviewer independently ran all 18 architecture checks,
all three import contracts without cache, and the planning-record validator. Review
reconciled all 34 initial task-owned additions and 11 runtime modules with the record,
interfaces, effects and contracts. There are no omitted, unrelated, renamed or deleted
paths. The parent ran the acceptance-record validator successfully before committing.

All configured pre-commit hooks passed during final verification. The development
environment remains available; separate verification environments are task-owned
temporary resources and are removed after use.

Runtime independent review first identified unsupported binary/pandas extras that could
crash duplicate hashing. Structural canonicalization and regression cases fixed that
failure. A fresh reviewer (`review_after_fix`, requested GPT-6.1 Sol/high, runtime settings
not independently observable) returned **ship**, with no blocking findings, after 45
focused tests plus cyclic/nested/opaque-value and retained-representative probes.
Opaque or cyclic extra cells deliberately skip exact comparison with an explicit warning;
IoU still runs. This is a reported limitation, not silent data rejection.

## Scale observation

The in-memory Python 3.12 check below validated 1,100,000 rows, one positive box
per image, in **36.861 seconds**, with **1397.9 MiB** peak process RSS, including
input construction and library imports in the memory high-water mark. All rows
were retained, with no rejected rows. No image files were read.

A separate table of 2,000 disjoint boxes within one image validated in
**0.156 seconds** and retained every box. This probes dense-group comparison;
it does not establish a performance guarantee for arbitrarily crowded images.
IoU comparison remains quadratic in group size in the worst case, with linear
working arrays rather than a full pairwise matrix.

Reproduction (Linux process-RSS reporting):

```python
import resource
import time
import numpy as np
import pandas as pd
from csv_dataset_validator import ValidationOptions, validate_dataframe

n = 1_100_000
names = [f"image_{i}.jpg" for i in range(n)]
frame = pd.DataFrame(
    {
        "image_name": names,
        "image_path": names,
        "instance_label": "object",
        "split": "train",
        "bbox_x_tl": 0,
        "bbox_y_tl": 0,
        "bbox_x_br": 10,
        "bbox_y_br": 10,
        "image_width": 100,
        "image_height": 100,
    }
)
start = time.perf_counter()
result = validate_dataframe(frame, profile="clearml-yolo", options=ValidationOptions(emit_warnings=False))
assert result.is_valid and len(result.clean) == n and result.broken.empty
print(time.perf_counter() - start, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
del frame, result, names

n = 2_000
left = np.arange(n) * 20
frame = pd.DataFrame(
    {
        "image_name": "dense.jpg",
        "image_path": "dense.jpg",
        "instance_label": "object",
        "split": "train",
        "bbox_x_tl": left,
        "bbox_y_tl": 0,
        "bbox_x_br": left + 10,
        "bbox_y_br": 10,
        "image_width": n * 20,
        "image_height": 100,
    }
)
start = time.perf_counter()
result = validate_dataframe(frame, profile="clearml-yolo", options=ValidationOptions(emit_warnings=False))
assert result.is_valid and len(result.clean) == n
print(time.perf_counter() - start)
```

## Boundaries

These are synthetic contract checks, not a production dataset-quality or model-accuracy
assessment. Local optional-image tests cover real temporary image files, corrupt images,
JPEG orientation and missing media. Full consuming-library integration and real-service
verification are deferred to [the integration plan](../integration-plan.md).
