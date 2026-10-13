# Rename to ed-killer

The user requests renaming the package and existing public repository to `ed-killer`.
The distribution and console command become `ed-killer`; Python imports and
`python -m` use `ed_killer`. This is an intentional breaking namespace change,
without compatibility aliases. Validation behavior, dependencies and schema stay unchanged.

The [architecture record](architecture.json) carries forward runtime responsibilities
and import contracts with explicit moves from the original namespace. Completed
records remain historical. Release tooling retains its private hook marker, guard,
lock and recovery filenames to remain compatible with existing installations.

1. Parent: record and validate architecture before implementation.
2. Parent: move the package, update packaging, lockfile, tests, import contracts and
   public documentation; verify installed console and module behavior.
3. Parent: run full checks on Python 3.12 and 3.10, build and install the wheel into
   an isolated environment, and reconcile the complete diff.
4. Fresh independent reviewer: review integrated changes, architecture and verification
   evidence read-only. No further delegation; parent addresses actionable findings.
5. Parent: rename the existing public GitHub repository, preserving its repository ID,
   visibility and history, and update origin. Regenerate changelog links and complete
   the automatic local semantic release, then push main and its explicit Git tag.
   Verify hosted CI and repository identity. Do not create GitHub Releases or packages.

Implementation is sequential because the package move and import updates are one
atomic change. Independent review follows integration and parent verification.

Implementation and architecture acceptance are complete; the independent reviewer
returned ship. Parent checks and repository identity preservation are recorded in
[dated evidence](../../evidence/2026-10-13-ed-killer-rename.md). The checked commit
triggers the established release workflow described above.
