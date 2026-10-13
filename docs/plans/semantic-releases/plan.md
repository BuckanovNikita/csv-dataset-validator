# Automatic local semantic releases

The user selected clearml-yolo's automatic local post-commit workflow and authorized
creating a public GitHub repository. Preserve the standalone validator and its Python
3.10+ contract. Publish only Git commits and version tags.

Use Python Semantic Release 10.x with Conventional Commits: fix/perf patch, feat minor,
breaking changes minor below 1.0, and non-release types alone no release. Release on
main only. Bootstrap the existing 0.1.0 implementation with an annotated baseline tag.
The feature commit enabling this workflow then releases according to that history.

## Architecture and ownership

The [architecture record](architecture.json) covers the development helper, release
policy, hooks, CI composition and executable acceptance checks. It is separate from
the completed validator architecture record. The release helper owns explicit local
Git/file/process effects and cannot import the validator or either consumer. Runtime
must not import release tools. Pydantic/Loguru are shared dependencies, not shared state.

Adapt the inspected clearml-yolo helper and real Git/PSR tests rather than inventing a
different automatic workflow. Keep guarded retries, common-directory locks, unchanged
dependency entries, checksum-protected changelog, path-limited checked release commits,
safe custom-hook preservation and no remote calls from hooks. Add Python3.10 TOML support.

## Dependency-aware tasks

1. Parent: validate planning record, then implement helper/config/hooks/docs.
2. Bounded read-only investigator: verify PSR bootstrap and compatibility behavior.
3. Bounded test owner, after interfaces above are fixed: adapt real-repository tests
   and add release architecture controls. Own only the two new test modules.
4. Parent: integrate and run both interpreter suites, quality/build/install checks;
   reconcile task-owned diff and dated evidence.
5. Fresh independent reviewer: inspect final implementation/architecture and checks.
6. Parent: record acceptance; create the authorized public repository, establish the
   baseline tag, install hooks, commit with checks, inspect the automatic release and
   push main plus explicit version tags. Verify remote refs and CI status. No GitHub
   Release objects, release assets or package registry publication.

The new repository starts clean at 6dc52fa with no tags/remotes. No other repository
is edited. Temporary repositories/environments are task-owned and cleaned afterward.
