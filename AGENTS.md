# ED Killer

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
`docs/plans/rename-ed-killer/architecture.json`, linked from its implementation plan.
The original `docs/architecture.json` remains historical. Import-linter enforces
exhaustive independent layers and output-only reporting; `tests/test_architecture.py`
exercises prohibited imports in temporary source copies, rejects consumer dependencies
and checks the facade. Validate the architecture record with
the shared module-architecture-planning skill at planning and acceptance checkpoints.

README.md is Russian; other documentation is English. Maintain `docs/schema.md` and
`docs/integration-plan.md` when public behavior changes. Record observations in dated
evidence. For new tasks, keep an adjacent architecture record with the native plan;
preserve the accepted records of completed work.

Follow [the release workflow](docs/releases.md). Install its hooks with
`uv run --locked --no-sync python scripts/local_release.py --install-hooks`.
Conventional Commits on main automatically produce a checked local release commit
and annotated version tag when unreleased history requires a bump. The pre-commit
changelog hook may update CHANGELOG.md: inspect and stage it, then retry normally.
Never bypass checks or manually edit version fields. Post-commit failures retain
the contributor commit; inspect the reported recovery state and use the documented
retry command. Complete authorized releases by pushing main and the explicit version
tags after verification. Publish Git tags only: no GitHub Releases, assets or packages.
The hook itself never pushes. Release tooling stays outside the validator runtime.
