"""Local image checks use real files and preserve positional lineage."""

import builtins
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from PIL import Image

from csv_dataset_validator.media import inspect_images, resolve_image_path
from csv_dataset_validator.models import DatasetInputError, ValidationOptions


def test_relative_paths_use_base_dir_and_blank_paths_use_image_root(tmp_path: Path) -> None:
    options = ValidationOptions(base_dir=tmp_path, image_root=Path("images"))
    assert resolve_image_path("a.png", "nested/a.png", options) == tmp_path / "nested/a.png"
    for missing in (None, "", np.nan, pd.NA):
        assert resolve_image_path("a.png", missing, options) == tmp_path / "images/a.png"
    assert resolve_image_path("a.png", "  ", options) == tmp_path / "  "
    assert resolve_image_path("a.png", None, ValidationOptions()) is None


@pytest.mark.parametrize("path", ["https://example.org/a.png", "s3://bucket/a.png", "file:///a.png"])
def test_uri_paths_are_never_resolved_as_local_files(path: str, tmp_path: Path) -> None:
    assert resolve_image_path("a.png", path, ValidationOptions(image_root=tmp_path)) is None


def test_image_dimensions_use_real_files_and_original_positions(tmp_path: Path) -> None:
    Image.new("RGB", (7, 9)).save(tmp_path / "tiny.png")
    frame = pd.DataFrame(
        {"image_name": ["tiny.png", "tiny.png"], "image_path": ["tiny.png", "./tiny.png"]}, index=[2, 8]
    )
    sizes, issues = inspect_images(
        frame, profile="clearml-yolo", options=ValidationOptions(check_images=True, base_dir=tmp_path)
    )
    assert sizes == {2: (7, 9), 8: (7, 9)}
    assert issues == []


@pytest.mark.parametrize("orientation", [6, 8])
def test_jpeg_exif_orientation_swaps_measured_dimensions(tmp_path: Path, orientation: int) -> None:
    exif = Image.Exif()
    exif[274] = orientation
    Image.new("RGB", (12, 23)).save(tmp_path / "rotated.jpg", exif=exif)
    frame = pd.DataFrame({"image_name": ["rotated.jpg"]}, index=[4])
    sizes, issues = inspect_images(
        frame, profile="cveta2", options=ValidationOptions(check_images=True, image_root=tmp_path)
    )
    assert sizes == {4: (23, 12)}
    assert issues == []


def test_missing_and_corrupt_media_report_each_affected_row(tmp_path: Path) -> None:
    (tmp_path / "corrupt.png").write_bytes(b"not an image")
    frame = pd.DataFrame({"image_name": ["missing.png", "corrupt.png", "corrupt.png"]}, index=[0, 3, 5])
    sizes, issues = inspect_images(
        frame, profile="clearml-yolo", options=ValidationOptions(check_images=True, image_root=tmp_path)
    )
    assert sizes == {}
    assert [(issue.code, issue.row_position, issue.severity) for issue in issues] == [
        ("media_missing", 0, "error"),
        ("media_unreadable", 3, "error"),
        ("media_unreadable", 5, "error"),
    ]


def test_deleted_cveta_rows_do_not_require_readable_media(tmp_path: Path) -> None:
    frame = pd.DataFrame({"image_name": ["absent.png"], "instance_shape": ["deleted"]})
    assert inspect_images(
        frame, profile="cveta2", options=ValidationOptions(check_images=True, image_root=tmp_path)
    ) == ({}, [])


def test_disabled_checks_do_not_import_pillow_or_touch_images(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def without_pillow(name: str, *args: object, **kwargs: object) -> object:
        if name == "PIL" or name.startswith("PIL."):
            raise ModuleNotFoundError("No module named 'PIL'", name="PIL")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_pillow)
    frame = pd.DataFrame({"image_name": ["absent.png"]})
    assert inspect_images(frame, profile="cveta2", options=ValidationOptions()) == ({}, [])
    with pytest.raises(DatasetInputError, match=r"csv-dataset-validator\[images\]"):
        inspect_images(frame, profile="cveta2", options=ValidationOptions(check_images=True))


def test_truncated_jpeg_is_rejected_even_when_header_is_readable(tmp_path: Path) -> None:
    path = tmp_path / "truncated.jpg"
    Image.new("RGB", (30, 40)).save(path)
    path.write_bytes(path.read_bytes()[:-20])
    frame = pd.DataFrame({"image_name": [path.name]})
    sizes, issues = inspect_images(
        frame, profile="clearml-yolo", options=ValidationOptions(check_images=True, image_root=tmp_path)
    )
    assert sizes == {}
    assert [(issue.code, issue.row_position) for issue in issues] == [("media_unreadable", 0)]


def test_canonical_aliases_share_one_real_image_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "image.png"
    Image.new("RGB", (12, 20)).save(path)
    alias = tmp_path / "alias.png"
    alias.symlink_to(path)
    open_image = Image.open
    reads: list[object] = []

    def counted_open(filename: object, *args: object, **kwargs: object) -> object:
        reads.append(filename)
        return open_image(filename, *args, **kwargs)

    monkeypatch.setattr(Image, "open", counted_open)
    frame = pd.DataFrame({"image_name": [path.name, alias.name], "image_path": [str(path), str(alias)]})
    sizes, issues = inspect_images(
        frame, profile="clearml-yolo", options=ValidationOptions(check_images=True)
    )
    assert sizes == {0: (12, 20), 1: (12, 20)}
    assert issues == []
    assert reads == [path]


def test_decompression_bomb_error_is_reported_per_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "large.png"
    Image.new("RGB", (12, 20)).save(path)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)
    frame = pd.DataFrame({"image_name": [path.name]})
    sizes, issues = inspect_images(
        frame, profile="clearml-yolo", options=ValidationOptions(check_images=True, image_root=tmp_path)
    )
    assert sizes == {}
    assert [(issue.code, issue.row_position) for issue in issues] == [("media_unreadable", 0)]


def test_local_resolution_expands_home_and_uses_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert resolve_image_path("a.png", "a.png", ValidationOptions()) == tmp_path / "a.png"
    assert resolve_image_path("a.png", "~/a.png", ValidationOptions()) == Path.home() / "a.png"


def test_uri_image_roots_are_rejected_before_path_resolution() -> None:
    assert resolve_image_path("a.png", None, ValidationOptions(image_root=Path("s3://bucket"))) is None


def test_embedded_nul_path_produces_a_row_issue() -> None:
    frame = pd.DataFrame({"image_name": ["a.png"], "image_path": ["invalid\x00.png"]}, index=[7])
    sizes, issues = inspect_images(
        frame, profile="clearml-yolo", options=ValidationOptions(check_images=True)
    )
    assert sizes == {}
    assert [(issue.code, issue.row_position) for issue in issues] == [("media_unreadable", 7)]
