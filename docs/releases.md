# Local semantic releases

This project follows clearml-yolo's local post-commit workflow, with `main` as its
release branch. Python Semantic Release 10.x reads full Conventional Commit history.
The version in `pyproject.toml` is release-owned; do not edit it manually.

| Change since the last reachable release tag | Version change |
| --- | --- |
| `fix:` or `perf:` | Patch |
| `feat:` | Minor |
| Breaking commit (`!` or `BREAKING CHANGE:`), while below 1.0 | Minor |
| Breaking commit at or above 1.0 | Major |
| Only other types, such as `docs:`, `chore:` or `test:` | No release |

All unreleased reachable history counts, including merged feature branches. Feature
branches and detached HEAD receive no automatic tags. History operations and automatic
amend/cherry-pick/rewrite commits are skipped; explicitly retry after they finish.

## Setup and normal use

Use a complete clone with an `origin` URL, an annotated `vX.Y.Z` baseline tag and a
configured Git identity. PSR needs remote URL metadata even though local releases do
not contact the remote. A new checkout must install hooks; Git does not clone hooks.

```bash
uv sync --dev
uv run --locked --no-sync python scripts/local_release.py --install-hooks
```

The installer preserves unrelated custom post-commit hooks by refusing replacement.
It installs ordinary pre-commit checks and a project-owned post-commit launcher using
`--all-files`, so pre-commit cannot stash away dirty tracked files during a release.
Plain `uv run pre-commit install` installs only the pre-commit hook.

Make and commit task-scoped changes normally. The pre-commit changelog hook regenerates
English `CHANGELOG.md` from committed history, including Unreleased entries and previous
tags, excluding generated release commits. It never stages changes: if it exits 1 after
updating the file, inspect it, stage it and repeat the commit. The pending commit appears
at its release preparation or the next changelog refresh. Do not hand-edit generated notes.

After a qualifying main commit, the post-commit helper:

1. Requires a clean tracked worktree/index, full history and a reachable baseline tag.
2. Acquires a Git-common-directory lock shared by linked worktrees.
3. Uses PSR to select the version and generate version metadata plus changelog.
4. Changes only the root project version token in `uv.lock`, preserving dependency
   entries, sources and all other bytes without dependency resolution.
5. Commits only `pyproject.toml`, `uv.lock` and `CHANGELOG.md` with normal checks enabled.
6. Validates the exact release commit and creates one annotated `vX.Y.Z` tag.

The recursion guard suppresses only nested release/changelog execution; quality checks
still run. Release tooling never imports the validator or consumer applications, and
the installed validator has no release-tool dependency. The supported Python 3.12
and 3.13 interpreters use standard-library `tomllib`.

## Retry and recovery

```bash
uv run --locked --no-sync python scripts/local_release.py
```

Exit 0 means completion or an explained skip/no-op. Exit 1 reports failed preparation,
checks, locks, metadata or tagging and names the retry command. Git itself still reports
a successful contributor commit when its post-commit hook fails; inspect the hook output
and tags rather than treating Git's exit code as proof of a release.

A failed preparation/check leaves its intended files for inspection and a private
Git recovery record. Resolve the cause, review only the three release files, and complete
their commit using the recorded `chore(release): VERSION` subject. The installed hook
then validates that exact release child and tags it; the explicit retry command also
works. It rejects changed changelog contents using the recorded checksum. Tag-only
retries rerun quality checks and do not create another commit. Repeated completed runs
are no-ops. Existing conflicting tags are never moved or replaced.

Dirty tracked or staged changes cause deferral; unrelated untracked files are preserved.
The helper does not stash, reset or discard edits. It refuses shallow history without
fetching. A concurrent lock is not stolen: inspect its `owner.json` and verify no release
process is active before removing a stale task-owned lock. The diagnostics identify its
location. Never bypass hooks or delete recovery metadata to force a tag.

## Publishing Git refs

The local helper never pushes, fetches, creates GitHub Releases, uploads artifacts or
publishes packages. Its PSR calls explicitly disable pushing, hosted releases and builds;
normal quality checks may still build locally. After reviewing the clean release and
passing checks, push the branch and the exact intended version tag together:

```text
git push --atomic origin main refs/tags/vX.Y.Z
```

Replace `vX.Y.Z` with the inspected tag; do not use `--tags` or force-push. Release
commits, tags and their pushes are part of the authorized completion workflow. CI only
verifies commits and tags, with read-only repository permissions. It does not release.

The initial bootstrap tags the already-verified 0.1.0 implementation before enabling
automatic hooks. Do not recreate bootstrap tags in subsequent checkouts. The introduction
and its acceptance are recorded in the [task plan](plans/semantic-releases/plan.md).
The [PSR CLI reference](https://python-semantic-release.readthedocs.io/en/stable/api/commands.html)
documents the upstream commands wrapped by the helper.

## Repository and package rename

The repository and distribution are `ed-killer`; the Python package is `ed_killer`.
Existing Git history and version tags continue in the renamed repository.
The release helper intentionally retains its original private hook marker, environment
guard and Git-directory lock/recovery filenames. These are persistent coordination
identifiers, so changing them would split locks or hide pending recovery records
from existing hooks. They are not installed package or CLI names.
