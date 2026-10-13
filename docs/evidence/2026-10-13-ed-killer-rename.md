# ed-killer rename verification — 2026-10-13

Base: `230e69c` (`v0.2.0`). User requested renaming the package and existing public
repository. Distribution and executable become `ed-killer`; imports and module
execution become `ed_killer`, without compatibility aliases. No validation behavior
or third-party dependency versions change.

## Parent verification

- Planning architecture validator passed before runtime changes.
- `uv lock` and `uv sync --dev --extra images` passed. uv removed the old editable
  distribution and installed `ed-killer`. Parsed lockfile comparison confirms that
  only the root project name changed; reordered package entries contain identical data.
- Python 3.12.13: `uv run --locked --no-sync pytest` — **286 passed**.
- Python 3.10.20: `UV_PROJECT_ENVIRONMENT=.superpowers/rename-py310 uv run
  --python 3.10 --frozen --extra images pytest` — **286 passed**.
- Both runs include runtime and release architecture negative controls and local
  documentation links. The CLI report/exit-status integration test now exercises
  both `python -m ed_killer` and the installed `ed-killer` executable.
- Ruff check/format, strict mypy, Vulture, import-linter, `uv lock --check` and
  `uv build` passed. Import-linter reports all three contracts kept. The initial
  formatting check requested wrapping changes after shortening two names; formatting
  was applied and the complete quality sequence passed on the final code.
- Build produced `ed_killer-0.2.0.tar.gz` and a wheel built from that source archive.
  In a fresh Python 3.12 environment, the wheel installed successfully without dev
  dependencies. From outside the checkout using isolated Python (`-I`), verified
  distribution metadata, `py.typed`, public API, the module and console entrypoints,
  clean/broken CSV and duplicate reasons, and strict rejection status 1. The old
  distribution/import/executable and release tooling are absent from that environment.
  The version is still the base version until the normal commit-triggered release.
- AST comparison with the base commit confirms every moved runtime module is
  unchanged after substituting package names and the optional Pillow installation hint.
  The typing marker is preserved. The former source directory is absent.
- `git diff --check` passed. Remaining old names are explicit migration guidance,
  completed historical evidence/plans, or intentional private release coordination IDs.

The release helper itself is unchanged. Its stable guard, hook marker and Git-private
lock/recovery names preserve compatibility with already-installed hooks. Existing
release behavior and negative policy tests passed on both supported interpreters.
The [task record](../plans/rename-ed-killer/architecture.json) owns current paths;
prior accepted architecture records remain historical.

## Review and publication

Fresh read-only reviewer `review_ed_killer_rename_retry` returned **ship** with no
findings after inspecting all 30 staged paths. Requested model: GPT-6 Sol/high;
runtime settings are not independently observable. The first requested GPT-6.1 Sol
reviewer failed at capacity before reviewing. The successful reviewer independently
ran 109 focused architecture/release/CLI tests, import-linter (three contracts kept)
and staged diff whitespace checks; all passed. Full-suite and wheel evidence was
reviewed rather than rerun by that reviewer.

Architecture responsibility/interface/dependency/effect ownership and the task-owned
diff were reconciled. The architecture acceptance validator passed after recording
this review. The parent reran the documentation link check after final evidence updates;
it passed.

The existing public repository was renamed to `BuckanovNikita/ed-killer`, retaining
repository ID `1416563571`, public visibility and default branch `main`. The SSH origin
now uses `git@github.com:BuckanovNikita/ed-killer.git`. Remote inspection confirmed
that both existing version tags and the previous main commit were retained. The
changelog helper regenerated only the historical commit URLs for the new repository;
its update-and-restage exit 1 is expected. No GitHub Release objects exist.

This evidence is committed with the breaking namespace change. The existing release
hook then selects the version and creates its separate checked release commit/tag;
publication and hosted CI are verified against those resulting refs in the completion
report. No package registry or GitHub Release publication is part of this workflow.
