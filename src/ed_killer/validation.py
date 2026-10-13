"""Validation, image quarantine and deterministic cleanup orchestration."""

import os
import warnings
from collections import Counter, defaultdict
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

import pandas as pd

from ed_killer.cells import is_missing, number
from ed_killer.geometry import find_duplicates
from ed_killer.media import inspect_images, resolve_image_path
from ed_killer.models import (
    DatasetWarning,
    Issue,
    Profile,
    ValidationOptions,
    ValidationResult,
)
from ed_killer.schema import BOX_COLUMNS, KNOWN_COLUMNS, schema_issues


def _group_rows(frame: pd.DataFrame) -> tuple[list[tuple[int, ...]], list[Issue]]:
    groups: dict[tuple[str, int | None], list[int]] = defaultdict(list)
    scope_states: dict[str, set[bool]] = defaultdict(set)
    tasks: Sequence[object] = frame["task_id"].tolist() if "task_id" in frame else [None] * len(frame)
    for position, (name, task) in enumerate(zip(frame["image_name"], tasks, strict=True)):
        # Unidentifiable rows cannot be joined to a known image by guesswork.
        key = name if isinstance(name, str) and name else f"\x00unidentified:{position}"
        task_id = None
        if not is_missing(task) and number(task) is not None:
            try:
                parsed = Decimal(str(task))
                if parsed.is_finite() and parsed >= 0 and parsed == parsed.to_integral_value():
                    task_id = int(parsed)
            except InvalidOperation:
                pass  # The schema reports malformed task IDs; group them as unscoped evidence.
        groups[key, task_id].append(position)
        scope_states[key].add(task_id is not None)
    mixed = sum(len(states) > 1 for states in scope_states.values())
    issues = []
    if mixed:
        issues.append(
            Issue(
                code="unscoped_task",
                severity="warning",
                columns=("task_id",),
                message=f"{mixed} image(s) mix task IDs and missing IDs; unscoped rows stay separate.",
            )
        )
    return [tuple(rows) for rows in groups.values()], issues


def _kind(label: object, shape: object) -> str:
    if shape == "deleted":
        return "deleted"
    return "none" if is_missing(label) else "box"


def _local_path(
    name: str,
    value: object,
    options: ValidationOptions,
) -> tuple[str | None, str | None, str | None]:
    try:
        path = resolve_image_path(name, value, options)
        if path is None:
            if not is_missing(value):
                return None, "invalid_local_path", "image_path must be a local path, not a remote URI."
            return None, None, None
        if "\x00" in str(path):
            return None, "invalid_local_path", "Image paths cannot contain NUL characters."
        # Filesystem identity is checked only when media access was requested.
        path = path.resolve() if options.check_images else Path(os.path.abspath(path))
        if path.name != name:
            return str(path), "path_name_mismatch", "Image name does not match the resolved path basename."
        return str(path), None, None
    except (OSError, RuntimeError, ValueError) as error:
        return None, "invalid_local_path", f"Cannot resolve local image path: {error}"


def _identity_issues(
    frame: pd.DataFrame,
    groups: list[tuple[int, ...]],
    profile: Profile,
    options: ValidationOptions,
) -> list[Issue]:
    issues: list[Issue] = []
    # Values used in consistency checks have already passed individual schema checks.
    positions_to_group = {position: index for index, rows in enumerate(groups) for position in rows}
    columns = ("image_name", "image_path", "split", "instance_label", "instance_shape")
    name_paths: dict[object, tuple[str, int]] = {}
    name_splits: dict[object, tuple[object, int]] = {}
    paths: dict[str, tuple[str, int]] = {}
    kinds: dict[int, tuple[str, int]] = {}

    def conflict(code: str, positions: tuple[int, int], column: str, message: str) -> None:
        for position, other in (positions, positions[::-1]):
            issues.append(
                Issue(
                    code=code,
                    message=message,
                    row_position=position,
                    columns=(column,),
                    related_rows=(other,),
                )
            )

    path_cache: dict[tuple[str, str], tuple[str | None, str | None, str | None]] = {}
    for raw in frame.reindex(columns=columns).itertuples(index=True, name=None):
        position, name, image_path, split, label, shape = raw
        pos = int(position)
        image_name = cast(str, name)
        group = positions_to_group[pos]
        kind = _kind(label, None if is_missing(shape) else shape)
        previous_kind = kinds.setdefault(group, (kind, pos))
        if previous_kind[0] != kind:
            conflict(
                "mixed_image_kinds",
                (previous_kind[1], pos),
                "instance_label",
                "The image/task mixes annotations, empty-image or deleted records.",
            )
        cache_key = (image_name, str(image_path) if not is_missing(image_path) else "")
        if cache_key not in path_cache:
            path_cache[cache_key] = _local_path(image_name, image_path, options)
        resolved, path_error, message = path_cache[cache_key]
        if path_error is not None:
            issues.append(
                Issue(code=path_error, row_position=pos, columns=("image_path",), message=cast(str, message))
            )
        # cveta2 historical tasks may carry different assignments; training ownership is global.
        owner_key: object = image_name if profile == "clearml-yolo" else group
        if resolved is not None:
            name_path = name_paths.setdefault(owner_key, (resolved, pos))
            if name_path[0] != resolved:
                conflict(
                    "path_conflict",
                    (name_path[1], pos),
                    "image_path",
                    "One image has conflicting local paths.",
                )
        if not is_missing(split):
            name_split = name_splits.setdefault(owner_key, (split, pos))
            if name_split[0] != split:
                conflict(
                    "split_conflict", (name_split[1], pos), "split", "One image belongs to multiple splits."
                )
        if resolved is not None:
            path_owner = paths.setdefault(resolved, (image_name, pos))
            if path_owner[0] != image_name:
                conflict(
                    "path_conflict",
                    (path_owner[1], pos),
                    "image_path",
                    "One canonical image path belongs to multiple image names.",
                )
    return issues


def _bounds_issues(
    frame: pd.DataFrame,
    groups: list[tuple[int, ...]],
    sizes: dict[int, tuple[int, int]],
) -> tuple[list[Issue], bool, bool]:
    issues: list[Issue] = []
    positions_to_group = {position: index for index, rows in enumerate(groups) for position in rows}
    owners: dict[int, tuple[tuple[float, float], int]] = {}
    columns = (
        *BOX_COLUMNS,
        "instance_label",
        "instance_shape",
        "image_width",
        "image_height",
        "width",
        "height",
        "rotation",
    )
    checked = False
    unchecked = 0
    rotated = 0
    for values in frame.reindex(columns=columns).itertuples(index=True, name=None):
        position, x1, y1, x2, y2, label, shape, iw, ih, width, height, rotation = values
        pos = int(position)
        if not is_missing(shape) and shape == "deleted":
            continue
        dimensions: list[tuple[float, float]] = []
        for w, h in ((iw, ih), (width, height)):
            parsed_w, parsed_h = number(w), number(h)
            if parsed_w is not None and parsed_h is not None:
                dimensions.append((parsed_w, parsed_h))
        if len(set(dimensions)) > 1:
            issues.append(
                Issue(
                    code="dimension_conflict",
                    row_position=pos,
                    message="The supplied dimension column pairs disagree.",
                )
            )
        declared = dimensions[0] if dimensions else None
        if declared is not None:
            owner = owners.setdefault(positions_to_group[pos], (declared, pos))
            if owner[0] != declared:
                for current, other in ((pos, owner[1]), (owner[1], pos)):
                    issues.append(
                        Issue(
                            code="dimension_conflict",
                            row_position=current,
                            related_rows=(other,),
                            message="Image/task dimensions disagree.",
                        )
                    )
        measured = sizes.get(pos)
        if measured is not None and any(d != measured for d in dimensions):
            issues.append(
                Issue(
                    code="image_dimension_mismatch",
                    row_position=pos,
                    message=f"Declared image dimensions disagree with measured size {measured}.",
                )
            )
        effective = measured if measured is not None else declared
        if is_missing(label):
            continue
        if number(rotation) not in (None, 0):
            rotated += 1
        if effective is None:
            unchecked += 1
            continue
        checked = True
        coords = (number(x1), number(y1), number(x2), number(y2))
        if all(value is not None for value in coords):
            left, top, right, bottom = cast(tuple[float, float, float, float], coords)
            if left < 0 or top < 0 or right > effective[0] or bottom > effective[1]:
                issues.append(
                    Issue(
                        code="out_of_bounds",
                        row_position=pos,
                        columns=tuple(BOX_COLUMNS),
                        message=f"Box extends outside image bounds 0..{effective[0]:g} x "
                        f"0..{effective[1]:g}; image/task is rejected.",
                    )
                )
    if unchecked:
        issues.append(
            Issue(
                code="bounds_unchecked",
                severity="warning",
                message=f"Upper image bounds unavailable for {unchecked} box(es); "
                "supply dimensions or enable image inspection.",
            )
        )
    if rotated:
        issues.append(
            Issue(
                code="rotation_ignored",
                severity="warning",
                columns=("rotation",),
                message=f"IoU uses stored axis-aligned coordinates for {rotated} rotated box(es).",
            )
        )
    return issues, checked, bool(unchecked)


def _quarantine(groups: list[tuple[int, ...]], issues: list[Issue]) -> tuple[set[int], list[Issue]]:
    directly_broken = {i.row_position for i in issues if i.severity == "error" and i.row_position is not None}
    rejected: set[int] = set()
    additions = []
    for group in groups:
        triggers = tuple(position for position in group if position in directly_broken)
        if not triggers:
            continue
        rejected.update(group)
        for position in group:
            if position not in directly_broken:
                additions.append(
                    Issue(
                        code="image_quarantined",
                        row_position=position,
                        related_rows=triggers,
                        message="Another malformed record quarantined this entire image/task.",
                    )
                )
    return rejected, additions


def _finish(
    frame: pd.DataFrame,
    profile: Profile,
    options: ValidationOptions,
    issues: list[Issue],
    rejected: set[int],
    checked: list[str],
    skipped: list[str],
    *,
    structural: bool = False,
) -> ValidationResult:
    clean_positions = tuple(position for position in range(len(frame)) if position not in rejected)
    broken_positions = tuple(sorted(rejected))
    clean = frame.iloc[list(clean_positions)].copy(deep=True)
    broken = frame.iloc[list(broken_positions)].copy(deep=True)
    issues.sort(key=lambda i: -1 if i.row_position is None else i.row_position)
    if options.emit_warnings:
        summary = Counter(i.code for i in issues if i.severity == "warning")
        for code in summary:
            message = next(i.message for i in issues if i.code == code)
            warnings.warn(message, DatasetWarning, stacklevel=3)
        if rejected or structural:
            warnings.warn(
                f"Validation rejected {len(rejected)} of {len(frame)} row(s); inspect result.issues "
                "and result.broken for reasons.",
                DatasetWarning,
                stacklevel=3,
            )
    names = frame["image_name"] if "image_name" in frame and frame.columns.is_unique else pd.Series(dtype=str)
    clean_names = (
        clean["image_name"] if "image_name" in clean and clean.columns.is_unique else pd.Series(dtype=str)
    )
    return ValidationResult(
        profile=profile,
        clean=clean,
        broken=broken,
        clean_row_positions=clean_positions,
        broken_row_positions=broken_positions,
        issues=tuple(issues),
        input_row_count=len(frame),
        checked_checks=tuple(checked),
        skipped_checks=tuple(skipped),
        structural_errors=structural,
        input_image_count=len({v for v in names if isinstance(v, str) and v}),
        clean_image_count=len({v for v in clean_names if isinstance(v, str) and v}),
    )


def validate_dataframe(
    frame: pd.DataFrame,
    *,
    profile: Profile,
    options: ValidationOptions | None = None,
) -> ValidationResult:
    """Validate a table and return original rows partitioned into clean and broken.

    Ordinary data errors never raise. Invalid configuration and missing optional
    dependencies remain explicit caller errors. Indices may be duplicated.
    """
    if profile not in ("cveta2", "clearml-yolo"):
        raise ValueError(f"Unknown validation profile: {profile!r}")
    selected = options or ValidationOptions()
    working = frame.reset_index(drop=True).copy(deep=True)
    checked = ["schema"]
    skipped: list[str] = []
    if not frame.columns.is_unique or any(not isinstance(c, str) or not c for c in frame.columns):
        issues = [Issue(code="invalid_header", message="Column names must be unique nonempty strings.")]
        return _finish(
            frame, profile, selected, issues, set(range(len(frame))), checked, skipped, structural=True
        )
    issues = schema_issues(working, profile)
    extras = sorted(set(frame.columns) - set(KNOWN_COLUMNS))
    if extras:
        issues.append(
            Issue(
                code="unknown_columns",
                severity="warning",
                columns=tuple(extras),
                message=f"Unknown columns are preserved without field validation: {', '.join(extras)}.",
            )
        )
    if any(issue.severity == "error" and issue.row_position is None for issue in issues):
        return _finish(
            frame, profile, selected, issues, set(range(len(frame))), checked, skipped, structural=True
        )
    if frame.empty:
        issues.append(Issue(code="empty_dataset", severity="warning", message="The dataset is empty."))
        return _finish(frame, profile, selected, issues, set(), checked, skipped)
    groups, grouping_issues = _group_rows(working)
    issues.extend(grouping_issues)
    initially_rejected, _ = _quarantine(groups, issues)
    eligible_groups = [group for group in groups if group[0] not in initially_rejected]
    eligible = working.drop(index=list(initially_rejected))
    issues.extend(_identity_issues(eligible, eligible_groups, profile, selected))
    checked.append("image_identity")
    sizes: dict[int, tuple[int, int]] = {}
    if selected.check_images:
        sizes, image_issues = inspect_images(eligible, profile=profile, options=selected)
        issues.extend(image_issues)
        checked.append("image_files")
    else:
        skipped.append("image_files")
    bounds, did_check, did_skip = _bounds_issues(eligible, eligible_groups, sizes)
    issues.extend(bounds)
    if did_check:
        checked.append("upper_image_bounds")
    if did_skip:
        skipped.append("upper_image_bounds")
    rejected, quarantine_issues = _quarantine(groups, issues)
    issues.extend(quarantine_issues)
    retained_groups = [group for group in groups if group[0] not in rejected]
    duplicate_issues = find_duplicates(
        working.drop(index=list(rejected)), retained_groups, iou_threshold=selected.iou_threshold
    )
    issues.extend(duplicate_issues)
    rejected.update(
        issue.row_position
        for issue in duplicate_issues
        if issue.row_position is not None and issue.severity == "error"
    )
    if any(issue.code == "exact_comparison_unavailable" for issue in duplicate_issues):
        skipped.append("full_row_duplicates")
    checked.extend(("full_row_duplicates", "high_iou"))
    return _finish(frame, profile, selected, issues, rejected, checked, skipped)
