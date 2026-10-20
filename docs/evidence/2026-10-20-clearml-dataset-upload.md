# ClearML dataset upload verification — 2026-10-20

## Inspected starting point and scope

Restored ED Killer clone, `main` at `30eeb55`, matching `origin/main`. No newer
ED Killer worktree or local modifications were present. The complete task-owned diff
adds `src/ed_killer/upload`, extracts the existing strict CSV reader without changing
the validation facade, adds upload tests/contracts and an optional dependency extra,
and updates CI and documentation. Other consumer repositories were not modified.

The native task plan and adjacent architecture record govern this work. Architecture
planning validation passed before implementation. Three bounded delegates owned
class/task policy, remote adapters, and bundle validation/root checks respectively;
the parent inspected and integrated their source/tests and owns final acceptance.
Each delegate was requested as `gpt-6.1-sol` at medium effort with fresh context.
Runtime settings were not independently observable.

## Behavior and quality

- Initial policy, model, file and workflow tests failed because their implementation
  modules were absent. Implementations subsequently passed focused checks.
- `uv run --locked --no-sync pytest`: **489 passed** on Python 3.12.13 before the
  three additional subprocess end-to-end tests.
- After adding those tests and changing validators to static methods, focused
  CLI end-to-end, model and remote tests: **45 passed** on Python 3.12.13.
- Full suite with the locked upload/dev dependencies in a separate Python 3.13.14
  environment: **492 passed**.
- Ruff lint and format checks passed. Strict mypy passed for 23 source files.
  Vulture passed. Its Protocol keyword-argument false positives use targeted V107
  annotations; Ruff preserves these external-tool annotations. No lint rules or
  quality hooks were disabled.
- Import-linter: **5 contracts kept, 0 broken**. Negative tests exercise forbidden
  core/upload, workflow/adapter, pure-policy/adapter, lazy/type-only/dynamic SDK and
  consumer imports. The upload initializer stays inert.
- `uv lock --check`, `uv build` and `git diff --check` passed.
- Local documentation-link checks passed within the full suites. Changed headings,
  Markdown, CLI options and YAML examples were inspected separately.

The tests cover canonical/alias collisions, rename chains/reversions, missing API
identities, empty/unknown classes, original broken-image evidence, clean-only
coordinate repairs, duplicate-only overlap, task completion/supersession/deletions,
root ancestry/symlinks/extensions, split and trainability blockers, reports before
consent, cancellation/EOF, exact child manifests, parent preservation and failed
upload/finalization.

## Packaging and external boundaries

Built wheel and source archive locally; nothing was uploaded to a package registry.
Installed the wheel into separate environments outside the checkout:

- Base wheel: import resolves to `site-packages`; ClearML is absent. Both CLI help
  commands work. Invoking upload without its extra returns exit 2 with installation
  guidance.
- Upload extra: import resolves to `site-packages`; ClearML 2.1.12 is installed.
  Public SDK signatures accept every adapter keyword for discovery, creation,
  selective metadata download, upload, finalization and S3 listing.
- Copied subprocess CLI tests outside the checkout and ran them with the installed
  upload wheel: **3 passed**. Real console input, loopback HTTP, local images, CSV,
  YAML and report writing are exercised, including affirmative consent, decline
  and EOF. ClearML/S3 SDK behavior is an explicit test double in these tests.
- HTTP adapter tests additionally use an owned real loopback HTTP listener.
  All listeners are closed by test cleanup.

The SDK source confirms that successful `Dataset.upload` normally returns `None`;
the adapter therefore also requires a clean upload state and exact file manifest.
It confirms child `remove_files("*", recursive=True)` covers inherited regular and
external-link entries. These inspections and doubles are not live server evidence.

## Live integration limitation

The maintained shared-test-stand registry has no ED Killer identity authorized for
ClearML or S3. No other project's credentials were used and no shared services were
changed. Real ClearML publication, retrieval and S3 authentication/access remain
unverified. This is an explicit live-integration acceptance gap, not a passing
service check. A real run requires an authorized test endpoint and project identity.

## Review and completion

Fresh reviewer `/root/upload_final_review` returned **fix-first** with one P2:
Ctrl-C after child creation bypassed the SDK exception boundary, losing the created
ID in the cancellation message. The reviewer ran 136 upload tests, import contracts,
architecture planning validation and whitespace checks, and inspected the installed
SDK implementation.

The parent reproduced four failures: upload/finalize interruption in adapter tests
and both stages through the real subprocess CLI. The remote boundary now translates
an interruption after known child creation into `UploadCancelled` with its ID,
uncertain remote state and inspection-before-retry guidance. It retains exit code 1
and performs no automatic retry. Publication before an available ID is not claimed
to be identifiable.

After the correction:

- Full Python 3.12.13 suite: **496 passed**.
- Affected remote and subprocess tests on Python 3.13.14: **47 passed**.
- Rebuilt and reinstalled the corrected wheel outside the checkout; all **5**
  subprocess upload/decline/EOF/interruption tests passed there.
- Ruff lint/format, mypy, Vulture, five import contracts, lock/build and whitespace
  checks passed again.

Fresh reviewer `/root/upload_release_review` returned **ship** for code readiness
with no remaining actionable findings. It independently ran all upload tests and
documentation links (**141 passed**), five import contracts, architecture planning
validation and whitespace checks. It inspected the complete integrated diff and
preserved the live-integration gap as a residual limitation. Requested reviewer
settings were `gpt-6.1-sol`, medium effort, fresh context; runtime settings were not
independently observable.

The parent reconciled every task-owned source/test/configuration/documentation path,
including untracked additions, with the architecture record. No unrelated changes
were excluded or modified. The architecture acceptance validator passed with the
executed local gates and accepted review. This does not close the separate live
integration gap. Release is pending; temporary environments remain for final
package verification.
