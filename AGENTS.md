# ED Killer

Portable Python library and CLI for cveta2 and clearml-yolo annotation CSVs.
Use uv and the checked-in lockfile. Develop on Python 3.12; support Python >=3.12,<3.14.
Do not use `from __future__ import annotations`.

Keep extra columns, untouched source values, row order and caller indices intact.
Validation uses positional lineage. Malformed annotations quarantine their image/task
for cveta2 and their whole image for clearml-yolo. Duplicates only remove later rows.
Only clearml-yolo may clip crossed edges strictly below 10 px with trustworthy dimensions
and valid original/final minimum geometry; accepted coordinate repairs belong in clean
only, while input and broken remain original. Never synthesize negatives or access remote
services. Clearml-yolo ignores all metadata outside its eight required fields and optional
dimensions; cross-class conflicts quarantine images before same-class duplicate cleanup.

Use Pydantic for configuration and issue models, Pandera for the complete field schema,
and Loguru for CLI diagnostics. The core must not depend on either consuming application.

Use the available shared `python-project-workflow` and
`module-architecture-planning` skills, discovered through the active host's skill
catalog. If a required skill is unavailable, report its missing gate and continue
independent inspection without claiming acceptance. The selected
[native Markdown process](docs/development.md) owns roles, stages and artifacts;
shared skills add Python conventions, architecture decisions and evidence within
that process. Do not introduce another lifecycle or migrate workflow tooling.
Follow its routes for new, resumed, bug, documentation and packaging work, honoring
explicit user selection and active host mode. Preserve unrelated changes.

Select checks by affected contracts using the development procedure. Runtime changes
retain the full quality gates; documentation-only work uses documentation checks.
Packaging changes also require real CLI and isolated built-package checks. Use
meaningful behavioral tests and verify a bug's original failure path after correction.

Maintain the module responsibilities and dependency/effect ownership recorded in
`docs/plans/rename-ed-killer/architecture.json`, linked from its implementation plan.
The [clearml-yolo task plan](docs/plans/clearml-training-validation/plan.md) links its
[current architecture record](docs/plans/clearml-training-validation/architecture.json).
Preserve the accepted records of completed tasks. The original `docs/architecture.json`
remains historical. Import-linter enforces
exhaustive independent layers and output-only reporting; `tests/test_architecture.py`
exercises prohibited imports in temporary source copies, rejects consumer dependencies
and checks the facade. Validate each task's architecture record with the shared skill
before implementation and at acceptance, reconciling the complete task-owned diff,
actual check evidence and applicable final review. Documentation-only work records
an inspected no-impact reason and targeted documentation checks.

README.md is Russian; other documentation is English. Maintain `docs/schema.md` and
`docs/integration-plan.md` when public behavior changes. Record observations in dated
evidence. For new tasks, keep an adjacent architecture record with the native plan;
preserve the accepted records of completed work. Resume by appending remaining work
based on inspected implementation. Complete affected documentation and its checks
before acceptance. Use proportionate collaboration; substantive changes require
fresh independent final review after integration and verification within the native
process. Report missing checks or review as acceptance gaps.

Follow [the release workflow](docs/releases.md). Install its hooks with
`uv run --locked --no-sync python scripts/local_release.py --install-hooks`.
Conventional Commits on main automatically produce a checked local release commit
and annotated version tag when unreleased history requires a bump. The pre-commit
changelog hook may update CHANGELOG.md: inspect and stage it, then retry normally.
Never bypass checks or manually edit version fields. Post-commit failures retain
the contributor commit; inspect the reported recovery state and use the documented
retry command. Complete authorized releases by pushing main and the explicit version
tags after verification. Standing authorization covers the required release commits,
tags and pushes; explicit stopping points and active host mode take precedence.
Publish Git tags only: no GitHub Releases, assets or packages.
The hook itself never pushes. Release tooling stays outside the validator runtime.
