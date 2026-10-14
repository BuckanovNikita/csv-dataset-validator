# Clearml-yolo training validation and automatic cleanup

Implement the user-approved profile changes; cveta2 behavior and public signatures stay unchanged.

## Behavior

Validate only image_name, image_path, instance_label, four bbox coordinates and split,
plus optional image_width/image_height and width/height. Preserve and ignore all other
metadata, including arbitrary issue_state/issue_text combinations, task IDs and shapes.
Group clearml-yolo rows by image. Explicit negatives have an empty label and all four
coordinates empty. Require finite box width > 2 px, height > 2 px and area > 2 square pixels.

Clip out-of-image coordinates only with reliable dimensions, strictly less than 10 px
overflow independently on every crossed edge, and valid final minimum geometry. Negative
left/top values are eligible. Missing/conflicting dimensions, nonfinite, reversed and
undersized geometry are not repaired. Defer negative-coordinate rejection until repair
has been considered, then validate final geometry. Never synthesize negatives.

Detect all cross-class IoU >= configured threshold pairs (default 0.99) before duplicate
pruning; both endpoints receive class_conflict errors and their whole image is quarantined.
Within the same image/class, compare against retained representatives, keep the earliest
row, and remove later exact or near duplicates. Metadata cannot affect these decisions.

Output accepted repairs in clean only; input and broken retain original cells. Preserve
untouched cells, extras, indices and order. bbox_clipped warnings identify changed fields
and before/after coordinates only for retained repairs. Repaired-only output is valid;
duplicate rejection retains existing strict CLI behavior. Direct Pandera schemas remain
nonmutating validators; validate_dataframe/validate_csv own automatic cleanup.

## Architecture and ownership

The adjacent [architecture record](architecture.json) covers schema policy, validation
orchestration, pure geometry comparisons and existing result/report contracts. Existing
import-linter and negative dependency tests remain authoritative. No new module or runtime
dependency is needed. Source/package inspection starts from clean main at 853043e.

Parent owns schema, validation, result/report docstrings, integration tests, task records,
integration, checks and release. A bounded geometry delegate owns geometry.py and its unit
tests. A documentation delegate owns README, schema/integration docs and AGENTS.md. These
workstreams share the agreed interfaces; final integration, checks and fresh review are
sequential. Delegates may not delegate further or commit.

## Tasks

- [x] Inspect repository and consumer evidence; agree behavior and validate planning record.
- [x] Add failing behavioral tests and implement schema/orchestration changes.
- [x] Implement pure cross-class conflict detection with independent geometry tests.
- [x] Update documentation and preservation instructions.
- [x] Integrate and run pytest, ruff check/format check, mypy, vulture, lint-imports,
      uv lock --check and uv build; check docs links and Python 3.10 compatibility.
- [x] Obtain fresh independent review, reconcile diff and record dated acceptance evidence.
- [ ] Install normal release hooks; commit task-owned changes with Conventional Commits;
      inspect hook-generated release and push main plus the explicit version tag atomically.

## Acceptance cases

Ignored malformed metadata; issue mismatches; strict size boundary and nonfinite geometry;
each edge at <10, 10 and >10 overflow; multi-edge repairs; clipped boxes too small; missing
or conflicting dimensions (including partial pairs); measured sizes; first-row retention, inclusive IoU threshold,
retained-representative chains, repair-created duplicates, cross-class conflicts hidden
behind duplicates; original indices/cells, warnings, CSV/CLI output and idempotence;
unchanged cveta2 behavior. No GitHub Releases or package publishing.

## Review correction

The first independent review found that incomplete dimension pairs could hide conflicts.
Clearml-yolo must compare every supplied axis against aliases, other image rows and
measured dimensions before repair. Five failing regression cases and one passing
control cover the gap; cveta2 retains its prior paired-dimension behavior.
