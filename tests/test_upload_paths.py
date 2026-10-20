from pathlib import Path

import pandas as pd
import pytest

from ed_killer.upload.models import ImageRoots, UploadError
from ed_killer.upload.paths import LocalRoots


def test_roots_resolve_symlinks_and_use_path_boundaries(tmp_path: Path) -> None:
    root = tmp_path / "images"
    root.mkdir()
    outside = tmp_path / "images-other"
    outside.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)
    paths = [str(root / "ok.png"), str(root / "escape" / "bad.png"), str(outside / "bad.png")]
    roots = LocalRoots()
    assert roots.check_local_root(str(root)) == str(root.resolve())
    assert roots.uncovered_paths(pd.DataFrame({"image_path": paths}), ImageRoots(local_root=[str(root)])) == [
        str(outside / "bad.png")
    ]


@pytest.mark.parametrize("value", ["relative.png", "", None, "s3://bucket/a.png", "bad\x00path"])
def test_malformed_or_relative_image_paths_block(value: object, tmp_path: Path) -> None:
    with pytest.raises(UploadError):
        LocalRoots().uncovered_paths(pd.DataFrame({"image_path": [value]}), ImageRoots())


def test_every_root_is_checked(tmp_path: Path) -> None:
    with pytest.raises(UploadError):
        LocalRoots().uncovered_paths(
            pd.DataFrame({"image_path": [str(tmp_path / "image.png")]}),
            ImageRoots(local_root=[str(tmp_path), str(tmp_path / "missing")]),
        )


def test_s3_roots_are_independent_and_boundary_checked() -> None:
    checks = LocalRoots()
    roots = ImageRoots(s3_root=["s3://bucket/prefix"])
    checks.check_s3_paths(pd.DataFrame({"s3_image_path": ["", None, "s3://bucket/prefix/a.png"]}), roots)
    for value in ["s3://bucket/prefix-other/a.png", "s3://other/prefix/a.png", "https://bucket/prefix/a"]:
        with pytest.raises(UploadError):
            checks.check_s3_paths(pd.DataFrame({"s3_image_path": [value]}), roots)


@pytest.mark.parametrize("root", ["https://bucket/a", "s3:///a", "s3://bucket/a/../b"])
def test_invalid_s3_root_blocks_even_without_references(root: str) -> None:
    with pytest.raises(UploadError):
        LocalRoots().check_s3_paths(pd.DataFrame(), ImageRoots(s3_root=[root]))
