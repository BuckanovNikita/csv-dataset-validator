# Clearml-yolo validation and cleanup verification — 2026-10-14

## Scope and observations

Started from clean main at 853043e (v0.3.0). No unrelated changes were present.
Read-only consumer inspection at clearml-yolo 7ae9153 confirmed its raw CSV boundary
uses eight training fields; its unrelated modified pyproject.toml was left intact.
No consumer application or shared service was changed.

The original validator rejected valid boxes for issue_state="closed", numeric
issue_text, malformed attributes and out-of-range confidence. It split identical
boxes by task_id and rejected shape="deleted" metadata. Those observations were
reproduced before implementation. The original focused baseline passed 115 tests.

The task implements the approved profile whitelist, strict >2 px dimensions and
>2 square-pixel area, per-edge <10 px clipping, within-class keep-first cleanup and
cross-class image quarantine before pruning. Input and broken rows remain original;
clean contains only accepted repairs. The public API/report structures are unchanged.
The adjacent task plan and architecture record document ownership and contracts.

## Red/green evidence

- New integration cases before implementation: 24 expected failures and 15 passing
  controls. Failures exposed metadata rejection, missing size minimums/clipping,
  task grouping and absent class-conflict handling.
- Geometry delegate: 11 new failing cases before the helper, then 29 geometry tests
  passed after implementation. Focused Ruff and mypy checks passed.
- Integrated schema/validation/geometry regressions: 166 passed after updating the
  obsolete clearml assertions and retaining prior policies as cveta2 coverage.
- An additional duplicate-index preservation test exposed unnecessary StringDtype
  conversion in repaired output. The fix preserves string extension storage and
  avoids coercing untouched numeric cells. Cleanup/CLI verification then passed
  70 tests, including console and module entrypoints.

## Final parent verification before review

| Command | Result |
| --- | --- |
| `uv run pytest` | 350 passed, Python 3.12.13, exit 0 |
| `UV_PROJECT_ENVIRONMENT="$temporary_environment" uv run --python 3.10 --frozen pytest` | 350 passed, Python 3.10.20, exit 0 |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed, 37 files |
| `uv run mypy` | Passed, 12 source files |
| `uv run vulture` | Passed |
| `uv run lint-imports` | 3 contracts kept, 0 broken |
| `uv lock --check` | Passed |
| `uv build` | Source distribution and wheel built locally |
| `git diff --check` | Passed |
| Architecture validator, plan phase | Passed before implementation |
| Release hook installer | Passed; normal hooks enabled |

The full suite includes local documentation links, injected forbidden-import and
facade-effect negative controls, consumer isolation and release-tool separation.
The inherited VIRTUAL_ENV selected another project; commands used the repository's
uv environment, with that inherited variable unset for final runs. No consumer
runtime, package publication or remote image access was used.

## Delegation and review

Geometry: native agent /root/geometry, requested GPT-6.1 Sol/medium, exclusive
geometry.py and test_geometry.py ownership. Documentation: /root/documentation,
requested GPT-6.1 Sol/medium, exclusive README, AGENTS and schema/integration docs.
Both completed; parent inspected their diffs and integrated verification. Runtime
model settings are not independently exposed by the collaboration tool.

The first fresh reviewer, /root/review_clearml (requested GPT-6.1 Sol/high), returned
fix-first: incomplete dimension pairs could hide contradictory widths/heights before
repair. The reviewer independently passed 215 targeted tests, the three import
contracts, planning validation and diff whitespace checks, but reproduced the gap
with aliases, other image rows and measured dimensions. No other findings were reported.

Parent reproduced five failures plus one passing control, then added clearml-only
per-axis consistency checks before repair. The focused cleanup/validation suite
passed 84 tests and mypy passed. Full checks and a new fresh review follow this fix.
Acceptance reconciliation is pending. The temporary
Python 3.10 environment will be removed after acceptance. Release commit/tag and
remote-ref verification remain pending; no deployment is authorized.

## Verification after review correction

Full suites passed again: 356 tests on Python 3.12.13 and 356 on Python 3.10.20.
Ruff check and format check, mypy, Vulture, all three import contracts, lock freshness,
local sdist/wheel build and diff whitespace checks passed again after the correction.
A fresh review of this corrected tree is pending.

## Acceptance

Fresh reviewer /root/review_clearml_final, requested GPT-6.1 Sol/high, returned **ship**
with no actionable findings. Independently ran 295 targeted tests on Python 3.12.13,
six additional boundary/preservation probes, all three import contracts, architecture
planning validation and whitespace checks. Reviewed the parent's Python 3.10 and broader
verification evidence. Runtime model settings are not independently exposed.

The parent reconciled all 17 task paths (13 tracked modifications, four additions) against
clean base 853043e. Changes are limited to schema/validation/geometry behavior, two
result/report docstrings, behavioral tests, documentation/instructions and task records.
Existing architecture contracts and their negative controls remain intact. No dependency
or unrelated source changes exist. Required generated version metadata and subsequent
task/evidence completion updates are within scope. The temporary Python 3.10 environment
was removed after verification. No task-owned processes remain.

Dense cross-class conflicts may produce quadratic numbers of diagnostic findings;
working geometry arrays remain linear per image. No consumer integration was performed.
Release execution follows this accepted source change; generated refs will be recorded
below after they exist and are verified.
