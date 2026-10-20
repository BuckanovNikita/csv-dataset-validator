"""Training-bundle policy around the offline validator, preserving original evidence."""

from collections import defaultdict
from pathlib import Path

import pandas as pd
from PIL import Image

from ed_killer.cells import is_missing
from ed_killer.models import Issue, ValidationOptions, ValidationResult
from ed_killer.upload.classes import class_lookup
from ed_killer.upload.models import BundleValidation, DatasetMetadata
from ed_killer.upload.paths import absolute_image_path
from ed_killer.validation import validate_dataframe

# Portable consumer contract, inspected in clearml-yolo dataset_records.py.
_NATIVE_EXTENSIONS = frozenset(
    {"avif", "bmp", "dng", "heic", "heif", "jp2", "jpeg", "jpg", "mpo", "png", "tif", "tiff", "webp"}
)


def _training_media_issues(frame: pd.DataFrame) -> list[Issue]:
    """Read headers only: the core owns decoding of schema-eligible local images."""
    issues: list[Issue] = []
    cache: dict[Path, tuple[str, str] | None] = {}
    for position, value in enumerate(frame["image_path"]):
        path = absolute_image_path(value)
        if path not in cache:
            result: tuple[str, str] | None = None
            if path.suffix.removeprefix(".").lower() not in _NATIVE_EXTENSIONS:
                result = (
                    "training_image_format",
                    f"Unsupported native training image extension: {path.suffix}",
                )
            else:
                try:
                    with Image.open(path) as image:
                        if (image.format or "").lower() not in _NATIVE_EXTENSIONS | {"jpeg2000"}:
                            result = (
                                "training_image_format",
                                f"Unsupported decoded image format: {image.format}",
                            )
                        elif min(image.size) < 10:
                            result = (
                                "training_image_size",
                                f"Training image sides must be at least 10 pixels: {image.size}",
                            )
                except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
                    # The file may have disappeared or changed since the core read it.
                    result = ("media_unreadable", f"Cannot inspect training image {path}: {error}")
            cache[path] = result
        failure = cache[path]
        if failure is not None:
            issues.append(
                Issue(code=failure[0], message=failure[1], row_position=position, columns=("image_path",))
            )
    return issues


def validate_bundle(frame: pd.DataFrame, metadata: DatasetMetadata, base_dir: Path) -> BundleValidation:
    """Canonicalize accepted labels, quarantine images and block untrainable snapshots."""
    lookup = class_lookup(metadata.classes)
    working = frame.copy(deep=True)
    issues: list[Issue] = []
    blockers: list[str] = []
    groups: dict[str, list[int]] = defaultdict(list)
    if frame.columns.is_unique:
        if "image_path" in frame:
            for value in frame["image_path"]:
                absolute_image_path(value)
        if "split" not in frame or any(
            not isinstance(value, str) or value not in {"train", "val", "test"}
            for value in frame.get("split", [])
        ):
            blockers.append("Every input row must have a valid train, val or test split assignment.")
        if "image_name" in frame:
            for position, name in enumerate(frame["image_name"]):
                key = name if isinstance(name, str) and name else f"\x00unidentified:{position}"
                groups[key].append(position)
        if "instance_label" in frame:
            working["instance_label"] = working["instance_label"].astype(object)
            label_column = list(working.columns).index("instance_label")
            for position, label in enumerate(frame["instance_label"]):
                if is_missing(label):
                    continue  # Core requires all four coordinates empty for explicit negatives.
                canonical = lookup.get(label) if isinstance(label, str) else None
                if canonical is None:
                    issues.append(
                        Issue(
                            code="unknown_class",
                            message=f"Unknown class: {label!r}",
                            row_position=position,
                            columns=("instance_label",),
                        )
                    )
                elif metadata.classes[canonical].empty:
                    issues.append(
                        Issue(
                            code="empty_class",
                            message=f"Class is marked empty: {canonical!r}",
                            row_position=position,
                            columns=("instance_label",),
                        )
                    )
                else:
                    working.iat[position, label_column] = canonical
                    if label != canonical:
                        issues.append(
                            Issue(
                                code="class_canonicalized",
                                message=f"Canonicalized class {label!r} to {canonical!r}.",
                                severity="warning",
                                row_position=position,
                                columns=("instance_label",),
                            )
                        )
    core = validate_dataframe(
        working,
        profile="clearml-yolo",
        options=ValidationOptions(check_images=True, emit_warnings=False, base_dir=base_dir),
    )
    issues.extend(_training_media_issues(working) if not core.structural_errors else [])
    direct = {
        issue.row_position for issue in issues if issue.severity == "error" and issue.row_position is not None
    }
    quarantined: set[int] = set()
    for positions in groups.values():
        triggers = tuple(position for position in positions if position in direct)
        if triggers:
            quarantined.update(positions)
            issues.extend(
                Issue(
                    code="image_quarantined",
                    message="Another rejected record quarantined this image.",
                    row_position=position,
                    related_rows=triggers,
                )
                for position in positions
                if position not in direct
            )
    rejected = set(core.broken_row_positions) | quarantined
    kept_offsets = [
        offset for offset, position in enumerate(core.clean_row_positions) if position not in rejected
    ]
    clean = core.clean.iloc[kept_offsets].copy(deep=True)
    clean_positions = tuple(position for position in core.clean_row_positions if position not in rejected)
    broken_positions = tuple(sorted(rejected))
    broken_image_positions = sorted(
        {
            position
            for positions in groups.values()
            if rejected.intersection(positions)
            for position in positions
        }
        | rejected
    )
    if core.structural_errors:
        blockers.append("Input CSV has structural validation errors.")
    if clean.empty:
        blockers.append("No valid images remain for upload.")
    else:
        for split in ("train", "val"):
            if not clean["split"].eq(split).any():
                blockers.append(f"Required {split} split has no valid images.")
        if not any(
            not is_missing(label) for label in clean.loc[clean["split"].eq("train"), "instance_label"]
        ):
            blockers.append("At least one valid training box is required.")
    result = ValidationResult(
        profile=core.profile,
        clean=clean,
        broken=frame.iloc[list(broken_positions)].copy(deep=True),
        clean_row_positions=clean_positions,
        broken_row_positions=broken_positions,
        issues=tuple(
            sorted(
                (*core.issues, *issues),
                key=lambda issue: -1 if issue.row_position is None else issue.row_position,
            )
        ),
        input_row_count=len(frame),
        checked_checks=(*core.checked_checks, "class_policy", "training_images", "trainability"),
        skipped_checks=core.skipped_checks,
        structural_errors=core.structural_errors,
        input_image_count=core.input_image_count,
        clean_image_count=len(set(clean["image_name"])) if "image_name" in clean else 0,
    )
    return BundleValidation(
        result=result,
        broken_images=frame.iloc[broken_image_positions].copy(deep=True),
        blockers=tuple(blockers),
    )
