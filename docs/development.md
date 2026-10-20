# Native development process

Use one Markdown ledger for the task: `docs/plans/<task>/plan.md`, an adjacent linked
`architecture.json` and dated results in `docs/evidence/`. Existing task artifacts
remain authoritative. Shared `python-project-workflow` and
`module-architecture-planning` skills add requirements inside this process; discover
them through the active host's catalog instead of copying installed skills here.
Explicit user workflow selection governs its task. Do not install a framework,
migrate tooling or create a parallel lifecycle. User scope and active host mode
limit which stages can execute, including writes, hooks, commits and publication.

## Inspect and plan

Inspect instructions, the index/worktree, relevant code/tests, `pyproject.toml`,
`uv.lock`, current contracts, task artifacts and hooks before editing. Plans express
intent; implementation and executed checks establish behavior. Record the outcome,
acceptance behavior, exclusions, stopping point, affected documentation and checks.
Preserve uv/lockfile, Hatchling, Python 3.12 development and
Python >=3.12,<3.14 compatibility.

Record affected module responsibilities, interfaces/invariants, permitted and
forbidden dependencies, effect ownership and executable import coverage in the
task's architecture record. Reuse maintained import-linter and architecture tests;
missing coverage needs scoped contracts with forbidden-edge negative cases.
Runtime fixes have module impact even if imports stay unchanged. Documentation-only
work uses an inspected no-impact reason. Validate the record's plan phase with the
installed shared skill's validator and explicit repository root before implementation.

| Route | Native ledger requirements |
| --- | --- |
| New task | Create a scoped plan and adjacent architecture record; identify implementation, contract, documentation and verification tasks and dependencies. New-project work uses the shared skill's scaffold guidance within this process. |
| Resumed task | Compare current code and owned diff with the active ledger. Append missing work and amendments; preserve completed history and accepted architecture records. Assess old artifacts when their work resumes rather than bulk-retrofitting history. |
| Bug | Capture the failing observation, reproduce when feasible, distinguish hypotheses from static or executed evidence, and plan a check of the original failure path after correction. |
| Documentation only | Record inspected no impact; validate changed Markdown, local links/anchors and examples. No unrelated application suite. |
| Packaging or entrypoints | Preserve metadata, extras, supported Python versions and public imports/commands; plan lock/build and isolated built-wheel installation checks outside the source checkout. |
| Planning or review only | Return the permitted assessment and proposed checks without implementation, persisted artifacts, mutating hooks, installation or release. |

## Implement and verify

The task owner integrates changes, preserves unrelated work and owns final checks.
Use native collaboration where independent work or review is useful. Specify bounded
write ownership, dependencies and acceptance evidence; delegates do not delegate
further. Trivial low-risk edits may stay direct. Do not invent parallel work.
Implementation precedes integration; final verification precedes fresh final review.
Substantive changes require independent review of that final diff and evidence,
including Python compatibility and architecture. Resolve findings and repeat affected
checks/review as warranted within this process; report unavailable review as a gap.

Runtime changes require focused behavior/regression coverage and the established
full gates: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
`uv run mypy`, `uv run vulture`, `uv run lint-imports`, `uv lock --check` and
`uv build`. Verify the original failure path for fixes. Check Python 3.12 and 3.13
behavior when compatibility is affected. Public API/CLI/configuration changes also check
actual imports, commands, exit codes and affected examples. Packaging changes add
an isolated built-wheel install with imports/CLI exercised outside the checkout.
Release tooling changes exercise real temporary Git repositories and recovery paths.
Broaden regression coverage for changes crossing module boundaries.

For upload work, prepare `uv sync --locked --dev --extra clearml`, then use locked
`--no-sync` checks to retain the optional SDK dependencies. Keep adapter-double tests,
real loopback HTTP tests and live ClearML/S3 evidence distinct. A missing authorized
test identity is a live-integration gap, never permission to use another project's
credentials. Upload import contracts cover core isolation, typed workflow ports,
independent adapters and lazy/type-only/dynamic network imports.

For documentation-only work, run
`uv run pytest tests/test_architecture.py::test_local_documentation_links_resolve`,
`git diff --check`, and inspect changed Markdown, anchors and command/config examples.
The existing link test checks local destination existence, not anchor correctness.
Use the established environment; preserve prepared extras and overrides through
an appropriate locked/frozen `--no-sync` recipe, or use a task-owned isolated
environment. Do not refresh dependencies or alter their sources for verification.
Unchanged hook and exact-release checks still apply when committing/releasing;
targeted documentation verification does not waive those gates.

## Accept and complete

Update affected README, schema, integration, command and compatibility guidance,
or record the inspected scope and concrete no-change reason. Keep README Russian
and other documentation English. Validate prose, local links/anchors and changed
examples, and place observed outputs in dated evidence.

Reconcile the complete owned diff, including untracked additions, renames/deletions
and generated files, with task status and architecture. Preserve completed records;
record excluded unrelated work. Run architecture acceptance validation after actual
checks and the applicable final review. Structural validation does not execute
checks or prove review; missing/failed gates remain acceptance gaps.

Follow [the release workflow](releases.md) after acceptance within existing
authorization. Honor explicit stops and active host mode; inspect hooks and generated
changes, stage only owned paths/hunks, and never bypass checks. Release tooling owns
versions/changelog. Documentation-only commits may legitimately produce no version
bump; evaluate the native workflow without inventing a tag. Publish only authorized
Git refs, never GitHub Release objects, release assets or registry packages.
Report actual checks, remaining gaps and commit/tag/push status. Clean up only
task-owned resources; source completion and installed package state are separate.
