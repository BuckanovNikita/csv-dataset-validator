# Python workflow alignment

Align project instructions with the available shared Python and module architecture
skills within the selected native Markdown ledger. Preserve domain contracts,
Python 3.10 compatibility, Python 3.12 development, uv/Hatchling tooling, executable
import contracts, completed history and the existing semantic release mechanism.

## Scope and ownership

Documentation only: `AGENTS.md`, new `docs/development.md`, this plan, the adjacent
[architecture record](architecture.json) and
[dated evidence](../../evidence/2026-10-14-python-workflow-alignment.md).
Inspect current configuration, tests, hook/release implementation and accepted records;
change no runtime, dependency, configuration, checker or release-tool code. Native
hooks may refresh `CHANGELOG.md`; inspect that generated output before staging.

The bounded implementer owns these documentation paths and verification, with no
delegation, commits, pushes or hook installation. The parent owns integrated final
acceptance, fresh review and the authorized release workflow. These stages depend
on the complete final diff and executed checks; no independent implementation
workstream is useful for this bounded prose change.

## Architecture

Impact is `none`: instruction and workflow prose changes do not alter module
responsibilities, public interfaces, imports, effects or executable contracts.
Reuse accepted task records without rewriting them. Validate this task's no-impact
record in the plan phase before policy edits; acceptance follows actual
documentation checks, complete-diff reconciliation and parent review.

## Tasks and checks

- [x] Inspect clean base, project instructions, native plans, current Python/tooling
      contracts, architecture tests, hooks and release guidance.
- [x] Validate the adjacent architecture record in the plan phase before policy edits.
- [x] Update concise project guidance and a linked native development ledger procedure.
- [x] Run the existing documentation-link test with uv in an isolated environment or
      an existing environment through `--no-sync`; preserve its dependencies.
- [x] Check changed Markdown, anchors, command examples and `git diff --check`;
      reconcile only the owned documentation diff and record actual dated results.
- [x] Parent: obtain fresh final review, resolve findings and validate architecture
      acceptance against the complete owned diff and actual check evidence.
- [ ] Parent: evaluate/complete the existing release workflow.

The focused repository check is
`uv run --locked --no-sync pytest tests/test_architecture.py::test_local_documentation_links_resolve`.
The corrected project-environment invocation and preliminary inherited-environment
failure are recorded in dated evidence; no prepared dependencies were changed.
The architecture validator is resolved from the installed shared skill and receives
this record, `--phase plan` / `--phase acceptance`, and the explicit repository root.
Do not run unrelated runtime suites for this documentation-only task. Existing
runtime and exact-release gates stay authoritative when their routes apply.

Completion requires documentation evidence and the parent's final acceptance;
the bounded handoff does not claim review, commits, tags or pushes occurred.
