"""Strict CSV decoding without pandas inference or silent row repair."""

import csv
from pathlib import Path

import pandas as pd

from csv_dataset_validator.models import DatasetInputError, Profile, ValidationOptions, ValidationResult
from csv_dataset_validator.validation import validate_dataframe


def validate_csv(
    path: str | Path,
    *,
    profile: Profile,
    options: ValidationOptions | None = None,
) -> ValidationResult:
    """Read UTF-8 CSV with literal cells, then validate it relative to its directory."""
    source = Path(path)
    selected = options or ValidationOptions()
    try:
        with source.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            header = next(reader, None)
            if not header or any(not value for value in header) or len(header) != len(set(header)):
                raise DatasetInputError("CSV must have a nonempty header with unique, nonempty column names.")
            rows: list[list[str]] = []
            for record, row in enumerate(reader, start=2):
                if len(row) != len(header):
                    raise DatasetInputError(
                        f"CSV record {record} has {len(row)} cells; expected {len(header)}."
                    )
                rows.append(row)
    except (OSError, UnicodeError, csv.Error) as error:
        raise DatasetInputError(f"Cannot read CSV {source}: {error}") from error
    effective = selected.model_copy(update={"base_dir": selected.base_dir or source.absolute().parent})
    return validate_dataframe(
        pd.DataFrame(rows, columns=header, dtype=object), profile=profile, options=effective
    )
