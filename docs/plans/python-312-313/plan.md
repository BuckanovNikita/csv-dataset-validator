# Python 3.12 and 3.13 support

The user explicitly requests `>=3.12,<3.14`; dropping Python 3.10/3.11 is intentional.
Retain Python 3.12 development, uv/Hatchling, all runtime contracts, approved dependency
versions and release tooling behavior. The parent owns integration, independent final
review, acceptance and release; this bounded work stops before commits.

Architecture and checks: [record](architecture.json).
Results: [dated evidence](../../evidence/2026-10-15-python-312-313.md).

- [x] Inspect clean worktree, Python metadata/lock, CI, docs, release tooling and contracts.
- [x] Record architecture responsibilities and checks before implementation.
- [x] Update range, lint/type targets, CI and maintained compatibility guidance.
- [x] Re-lock without unrelated upgrades; inspect resolved version changes.
- [x] Verify full quality and both Python interpreters; build and isolated wheel CLI/import.
- [x] Reconcile owned diff, documentation and evidence for parent review.
- [x] Parent: fresh independent final review, architecture acceptance and authorized release.

No new runtime modules or imports are introduced. Existing runtime and release
architecture contracts retain their negative forbidden-edge tests. No additional
subagent work is needed within this bounded repository assignment.

The Python 3.12 mypy target exposes a union for `Index.get_loc` that the prior
3.10 target accepted. Add an explicit static `cast(int, ...)` for the repair column
lookup after existing unique-header validation; preserve runtime behavior.

## Accepted review and delivery continuation

Parent integrated and reran the full suite; the fresh independent final reviewer
returned ship with no findings. Parent authorized this owner to complete acceptance
and native release delivery after that review, superseding the initial bounded
stopping point. Existing `main` remains canonical. Generated changelog/version
changes stay owned by the established release helper.

- [x] Fresh independent final review and parent integration verification.
- [x] Architecture acceptance record reconciled with reviewed scope and generated release paths.
- [x] Complete normal commit/hooks, release tag, atomic branch/tag push and remote verification.
