"""CSV lexical integrity, CLI outputs and failure boundaries."""

import csv
import json
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

HEADER = [
    "image_name",
    "image_path",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
    "split",
]


def write_csv(path, rows, header=HEADER):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def run_cli(*args, entrypoint="module"):
    if entrypoint == "console":
        suffix = ".exe" if sys.platform == "win32" else ""
        command = [str(Path(sysconfig.get_path("scripts")) / f"ed-killer{suffix}")]
    else:
        command = [sys.executable, "-m", "ed_killer"]
    return subprocess.run(
        [*command, *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("label", ["001", "NA", "None", "null", "1.0", "label\nnext"])
def test_csv_labels_are_preserved_exactly(tmp_path, label):
    from ed_killer import ValidationOptions, validate_csv

    path = tmp_path / "input.csv"
    write_csv(path, [["a.jpg", "a.jpg", label, 0, 0, 10, 10, "train"]])
    result = validate_csv(path, profile="clearml-yolo", options=ValidationOptions(emit_warnings=False))
    assert result.clean.iloc[0]["instance_label"] == label
    assert result.clean.iloc[0]["bbox_x_tl"] == "0"


@pytest.mark.parametrize(
    "text",
    [
        "image_name,image_name\na.jpg,a.jpg\n",
        ",image_name\nx,a.jpg\n",
        "a,b\n1,2,3\n",
        "a,b\n1\n",
        'a,b\n"unclosed,2\n',
        "",
    ],
)
def test_unusable_csv_is_not_silently_repaired(tmp_path, text):
    from ed_killer import DatasetInputError, validate_csv

    path = tmp_path / "broken.csv"
    path.write_text(text)
    with pytest.raises(DatasetInputError):
        validate_csv(path, profile="clearml-yolo")


@pytest.mark.parametrize("entrypoint", ["module", "console"])
def test_cli_writes_clean_broken_and_json_with_reasons(tmp_path, entrypoint):
    source = tmp_path / "input.csv"
    write_csv(source, [["a.jpg", "a.jpg", "cat", 0, 0, 10, 10, "train"]] * 2)
    output = tmp_path / "output"
    result = run_cli(source, "--profile", "clearml-yolo", "--output-dir", output, entrypoint=entrypoint)
    assert result.returncode == 0, result.stderr
    with (output / "clean.csv").open() as stream:
        assert len(list(csv.DictReader(stream))) == 1
    with (output / "broken.csv").open() as stream:
        rejected = list(csv.DictReader(stream))
    report = json.loads((output / "report.json").read_text())
    assert report["counts"]["broken_rows"] == 1
    assert "duplicate_row" in rejected[0][report["metadata_columns"]["reason_codes"]]
    strict = run_cli(source, "--profile", "clearml-yolo", "--fail-on-invalid", entrypoint=entrypoint)
    assert strict.returncode == 1
    refused = run_cli(source, "--profile", "clearml-yolo", "--output-dir", output, entrypoint=entrypoint)
    assert refused.returncode == 2
    overwritten = run_cli(
        source, "--profile", "clearml-yolo", "--output-dir", output, "--overwrite", entrypoint=entrypoint
    )
    assert overwritten.returncode == 0


def test_reporting_column_names_do_not_replace_extra_input_columns(tmp_path):
    source = tmp_path / "input.csv"
    header = [*HEADER, "__validator_row_position", "__validator_reason_codes", "__validator_reasons"]
    write_csv(
        source, [["a.jpg", "a.jpg", "cat", 0, 0, 10, 10, "train", "keep", "keep", "keep"]] * 2, header=header
    )
    output = tmp_path / "output"
    result = run_cli(source, "--profile", "clearml-yolo", "--output-dir", output)
    assert result.returncode == 0, result.stderr
    with (output / "broken.csv").open() as stream:
        rejected = next(csv.DictReader(stream))
    assert rejected["__validator_row_position"] == "keep"
    assert rejected["__validator_reason_codes"] == "keep"
    assert rejected["__validator_reasons"] == "keep"


def test_cli_missing_columns_and_unreadable_input_exit_two(tmp_path):
    assert run_cli(tmp_path / "missing.csv", "--profile", "cveta2").returncode == 2
    source = tmp_path / "partial.csv"
    source.write_text("image_name\na.jpg\n")
    assert run_cli(source, "--profile", "clearml-yolo").returncode == 2


def test_cli_all_rejected_is_completed_cleanup_and_empty_is_valid(tmp_path):
    source = tmp_path / "input.csv"
    write_csv(source, [["a.jpg", "a.jpg", "cat", 0, 0, -1, 10, "train"]])
    assert run_cli(source, "--profile", "clearml-yolo").returncode == 0
    write_csv(source, [])
    assert run_cli(source, "--profile", "clearml-yolo", "--fail-on-invalid").returncode == 0
