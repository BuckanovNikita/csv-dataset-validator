from pathlib import Path

import pandas as pd
import pytest

from ed_killer import ValidationOptions, validate_dataframe
from ed_killer.upload.files import LocalFiles
from ed_killer.upload.models import BundleValidation, ClassInfo, DatasetMetadata, ImageRoots, TaskManifest


def test_fetch_requires_complete_partition_and_preserves_literal_cells(tmp_path: Path):
    files = LocalFiles()
    for name in ("dataset", "obsolete", "in_progress"):
        (tmp_path / f"{name}.csv").write_text("image_name,task_id\n001.jpg,007\n")
    with pytest.raises(ValueError, match=r"deleted\.csv"):
        files.read_fetch(tmp_path)
    (tmp_path / "deleted.csv").write_text("image_name,task_id\n")
    tables = files.read_fetch(tmp_path)
    assert tables.dataset.iloc[0].tolist() == ["001.jpg", "007"]
    assert tables.deleted.empty


def test_yaml_duplicate_keys_are_rejected_instead_of_overwriting_classes(tmp_path: Path):
    path = tmp_path / "dataset.yaml"
    path.write_text("api_url: https://example.org\napi_url: https://different.example.org\n")
    with pytest.raises(ValueError, match="Duplicate"):
        LocalFiles().read_metadata(path)


def test_report_bundle_is_separate_from_full_original_broken_images(tmp_path: Path):
    frame = pd.DataFrame(
        [
            dict(
                image_name="001.jpg",
                image_path="/images/001.jpg",
                instance_label="Старое",
                bbox_x_tl="1",
                bbox_y_tl="2",
                bbox_x_br="1",
                bbox_y_br="3",
                split="train",
                extra="NA",
            )
        ]
    )
    result = validate_dataframe(frame, profile="clearml-yolo", options=ValidationOptions(emit_warnings=False))
    metadata = DatasetMetadata(
        api_url="https://example.org/classes",
        classes={"Имя": ClassInfo(prod_id=93)},
        images=ImageRoots(local_root=["/images"]),
    )
    destination = tmp_path / "report"
    LocalFiles().write_report(
        destination,
        BundleValidation(result, frame, ("No train rows",)),
        metadata,
        TaskManifest(included=[], obsolete=[12]),
        (),
    )
    assert {p.name for p in destination.iterdir()} == {
        "dataset.csv",
        "dataset.yaml",
        "tasks.yaml",
        "broken-images.csv",
        "report.json",
    }
    broken = pd.read_csv(destination / "broken-images.csv", dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(frame, broken)
    assert LocalFiles().read_metadata(destination / "dataset.yaml") == metadata
    with pytest.raises(FileExistsError):
        LocalFiles().write_report(
            destination, BundleValidation(result, frame), metadata, TaskManifest(included=[], obsolete=[]), ()
        )
