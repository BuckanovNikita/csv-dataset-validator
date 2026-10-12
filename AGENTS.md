# CSV Dataset Validator

Portable Python library and CLI for cveta2 and clearml-yolo annotation CSVs.
Use uv and the checked-in lockfile. Develop on Python 3.12; preserve Python 3.10 compatibility.
Do not use `from __future__ import annotations`.

Keep source values, extra columns, row order and caller indices intact. Validation uses
positional lineage. Malformed annotations quarantine their image/task; duplicates only
remove later rows. Never synthesize negatives, clip boxes, or access remote services.

Use Pydantic for configuration and issue models, Pandera for the complete field schema,
and Loguru for CLI diagnostics. The core must not depend on either consuming application.

Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
`uv run mypy`, `uv run vulture`, `uv run lint-imports`, `uv lock --check`, and
`uv build` before completion. Test CLI and installed-package behavior for packaging changes.
Use meaningful behavioral tests; preserve unrelated work.

Maintain the module responsibilities and dependency/effect ownership recorded in
`docs/architecture.json`, linked from the implementation plan. Import-linter enforces
exhaustive independent layers and output-only reporting; `tests/test_architecture.py`
exercises prohibited imports in temporary source copies, rejects consumer dependencies
and checks the facade. Validate the architecture record with
the shared module-architecture-planning skill at planning and acceptance checkpoints.

README.md is Russian; other documentation is English. Maintain `docs/schema.md` and
`docs/integration-plan.md` when public behavior changes. Record performance observations
in dated evidence, not these instructions. No automated release or publishing workflow
is established: finish authorized repository work with a task-scoped Conventional Commit.
