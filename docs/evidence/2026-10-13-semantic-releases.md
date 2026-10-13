# Semantic release verification — 2026-10-13

## Scope and source

The user selected automatic local post-commit releases and a public GitHub repository.
The starting checkout was clean at `6dc52fa`, version 0.1.0, without tags or remotes.
No consumer repository was changed. Runtime source under `src/` is unchanged.

The release helper and real-Git acceptance tests adapt clearml-yolo's workflow inspected
at revision `99befeafb3dbff05e1206a4b008ae48d00269bf8`, using main instead of master,
project-specific Git metadata and guard names, Python 3.10 TOML support, and this
project's existing quality gates. No framework or release service was added.

An independent bounded investigator used PSR 10.7.0 with isolated repositories to verify
that tags determine the baseline: untagged feat/fix/chore histories predicted 0.1.0,
0.0.1 and 0.0.0 respectively despite a 0.1.0 metadata version. A v0.1.0 tag followed
by a fix predicted 0.1.1. The adopted bootstrap tags the existing verified implementation.
PSR also requires origin URL metadata even with local-only flags; fixture origins use
non-contacted example URLs and the project origin names its authorized GitHub repository.

## Parent verification before review and publication

- `uv run --frozen pytest`: **285 passed** on Python 3.12.13.
- `UV_PROJECT_ENVIRONMENT=.superpowers/semantic-release-py310 uv run --python 3.10 --frozen pytest`:
  **285 passed** on Python 3.10.20 in a separate task-owned environment.
- The release-specific suites contain **116 tests**, independently run by the bounded
  test owner on both interpreters. They exercise real Git, PSR and installed hooks,
  failure/recovery paths, unrelated work preservation and architecture negative controls.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
  `uv run vulture`, `uv run lint-imports`, `uv lock --check` and `uv build` passed.
  Strict mypy includes the release script and passed in both interpreter environments.
  All three existing runtime import contracts remain kept.
- `uv run pytest tests/test_architecture.py -k documentation`: passed.
- The architecture planning-record validator passed before implementation and again
  after reconciliation with the integrated source/configuration.
- The built wheel installed in an isolated environment containing no PSR, release scripts
  or Pillow. Its API validated a CSV and its console entrypoint showed help successfully.
  The wheel excludes the development script; the source distribution includes it and
  hook configuration. The interpreter used `-I` to exclude the source checkout from
  import discovery; the first non-isolated probe could see the checkout's scripts directory.

Resolved PSR is 10.7.0. The lockfile records exact dependency versions. Its added packages
are development dependencies; application requirements remain unchanged. TOML fallback
`tomli` is installed on all development interpreters so strict mypy targeting 3.10 can
resolve that branch even when run under 3.12.

## Acceptance boundary

Release tests run in temporary repositories, strip inherited Git index/release guard
variables, and use no remote operations. They prove patch/minor/breaking behavior,
tag idempotency, checked release commits, preserved lockfile dependency bytes,
changelog integrity, failed-check and tag-only recovery, dirty/index/untracked work
preservation, branch/history skips and lock ownership. Static checks cover tooling/runtime
isolation and explicit no-publication policy with prohibited-edge and policy mutations.

Local release hooks never publish. Creating the authorized public repository and pushing
reviewed commits/tags are explicit parent completion actions. This checkpoint records
local verification, not a remote CI result or an already-published release.

## Independent acceptance

The fresh read-only reviewer `review_semantic_releases` (requested GPT-6.1 Sol/high;
runtime settings not independently observable) returned **ship**, with no actionable
correctness or release-safety blockers. Review reconciled all 14 task-owned paths against
the clean base, module/effect boundaries, explicit publication restrictions, checked
path-limited release commits and recovery invariants. It independently reran the 116
release tests on Python 3.12.13, the architecture planning validator and staged/unstaged
diff whitespace checks; all passed. Other checks were assessed from parent evidence.

The parent also ran all configured pre-commit hooks successfully. The accepted
architecture record is validated before bootstrap/publication. Static command policy
tests cover the explicit commands and tested mutations, not arbitrary hypothetical
dynamic programs. Temporary verification environments are removed after final use.
