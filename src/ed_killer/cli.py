"""Command-line dataset validation and cleanup."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from loguru import logger
from pydantic import ValidationError

from ed_killer.csv_io import validate_csv
from ed_killer.models import DatasetInputError, Profile, ValidationOptions
from ed_killer.reporting import write_report


def main(argv: Sequence[str] | None = None) -> int:
    """Return 0 for completed cleanup, 1 for strict rejection, 2 for unusable input/output."""
    parser = argparse.ArgumentParser(description="Validate cveta2 or clearml-yolo dataset CSVs.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--profile", choices=("cveta2", "clearml-yolo"), required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--check-images", action="store_true")
    parser.add_argument("--image-root", type=Path)
    parser.add_argument("--iou-threshold", type=float, default=0.99)
    parser.add_argument("--fail-on-invalid", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    logger.remove()
    logger.add(sys.stderr, format="{level}: {message}", colorize=False)
    try:
        options = ValidationOptions(
            check_images=args.check_images,
            image_root=args.image_root,
            iou_threshold=args.iou_threshold,
            emit_warnings=False,
        )
        result = validate_csv(args.input, profile=cast(Profile, args.profile), options=options)
        if args.output_dir:
            write_report(result, args.output_dir, overwrite=args.overwrite, input_path=args.input)
    except (DatasetInputError, ValidationError, OSError, ValueError) as error:
        logger.error("{}", error)
        return 2
    logger.info(
        "{} input rows; {} clean; {} rejected. {} of {} images remain.",
        result.input_row_count,
        len(result.clean),
        len(result.broken),
        result.clean_image_count,
        result.input_image_count,
    )
    for issue in result.warnings:
        logger.warning("{}: {}", issue.code, issue.message)
    if not result.is_valid:
        logger.warning("Rows were rejected; inspect broken.csv and report.json for all reasons.")
        for issue in result.issues[:10]:
            if issue.severity == "error":
                logger.warning("row {}: {}: {}", issue.row_position, issue.code, issue.message)
    if result.structural_errors:
        return 2
    return int(args.fail_on_invalid and not result.is_valid)
