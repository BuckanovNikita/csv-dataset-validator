"""Portable diagnostics and explicit output-file writing."""

import json
import os
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from ed_killer.models import Issue, ValidationResult


def _metadata_names(columns: list[str]) -> dict[str, str]:
    used = set(columns)
    names = {}
    for key in ("row_position", "reason_codes", "reasons"):
        candidate = f"__validator_{key}"
        while candidate in used:
            candidate += "_"
        names[key] = candidate
        used.add(candidate)
    return names


def report_dict(result: ValidationResult) -> dict[str, Any]:
    """Return JSON-ready data; original cell values stay in the CSV outputs."""
    return {
        "profile": result.profile,
        "is_valid": result.is_valid,
        "structural_errors": result.structural_errors,
        "counts": {
            "input_rows": result.input_row_count,
            "clean_rows": len(result.clean),
            "broken_rows": len(result.broken),
            "input_images": result.input_image_count,
            "clean_images": result.clean_image_count,
        },
        "clean_row_positions": result.clean_row_positions,
        "broken_row_positions": result.broken_row_positions,
        "checked_checks": result.checked_checks,
        "skipped_checks": result.skipped_checks,
        "issues": [issue.model_dump(mode="json") for issue in result.issues],
        "metadata_columns": _metadata_names(list(result.broken.columns)),
    }


def write_report(
    result: ValidationResult,
    directory: str | Path,
    *,
    overwrite: bool = False,
    input_path: Path | None = None,
) -> None:
    """Write clean.csv, broken.csv and report.json, preserving existing outputs by default."""
    destination = Path(directory)
    names = ("clean.csv", "broken.csv", "report.json")
    targets = [destination / name for name in names]
    for target in targets:
        if input_path is not None and target.resolve() == input_path.resolve():
            raise ValueError(f"Output would overwrite the input CSV: {target}")
        if target.exists() and (not overwrite or target.is_dir()):
            raise FileExistsError(f"Output already exists: {target}; use --overwrite for files.")
    destination.mkdir(parents=True, exist_ok=True)
    report = report_dict(result)
    metadata = _metadata_names(list(result.broken.columns))
    by_row: dict[int, list[Issue]] = defaultdict(list)
    for issue in result.issues:
        if issue.row_position is not None:
            by_row[issue.row_position].append(issue)
    structural_issues = (
        [issue for issue in result.issues if issue.row_position is None and issue.severity == "error"]
        if result.structural_errors
        else []
    )
    broken = result.broken.copy()
    broken[metadata["row_position"]] = list(result.broken_row_positions)
    broken[metadata["reason_codes"]] = [
        json.dumps([issue.code for issue in (*by_row[position], *structural_issues)], ensure_ascii=False)
        for position in result.broken_row_positions
    ]
    broken[metadata["reasons"]] = [
        json.dumps([issue.message for issue in (*by_row[position], *structural_issues)], ensure_ascii=False)
        for position in result.broken_row_positions
    ]
    # Finish serialization before touching final paths; failed writes cannot truncate old files.
    with TemporaryDirectory(prefix=".csv-validator-", dir=destination) as temporary:
        staging = Path(temporary)
        result.clean.to_csv(staging / "clean.csv", index=False, encoding="utf-8")
        broken.to_csv(staging / "broken.csv", index=False, encoding="utf-8")
        (staging / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        for target in targets:
            if overwrite:
                os.replace(staging / target.name, target)
            else:
                # Hard linking is atomic and fails if another writer created the target.
                os.link(staging / target.name, target)
