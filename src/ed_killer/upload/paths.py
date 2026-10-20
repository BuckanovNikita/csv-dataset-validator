"""Local path coverage and independent S3-reference containment checks."""

from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd

from ed_killer.cells import is_missing
from ed_killer.upload.models import ImageRoots, UploadError


def absolute_image_path(value: object) -> Path:
    """Require an explicit absolute local path before resolving symlinks."""
    if not isinstance(value, str) or not value or "\x00" in value or not Path(value).is_absolute():
        raise UploadError(f"Upload image_path must be an absolute local path: {value!r}")
    try:
        return Path(value).resolve()
    except (OSError, RuntimeError, ValueError) as error:
        raise UploadError(f"Cannot resolve image_path {value!r}: {error}") from error


def _s3_parts(value: str) -> tuple[str, tuple[str, ...]]:
    try:
        parsed = urlsplit(value)
    except ValueError as error:
        raise UploadError(f"Invalid S3 path: {value!r}") from error
    parts = tuple(parsed.path.strip("/").split("/")) if parsed.path.strip("/") else ()
    if (
        parsed.scheme != "s3"
        or not parsed.netloc
        or any(character in parsed.netloc for character in "@: \\")
        or parsed.query
        or parsed.fragment
        or "\x00" in value
        or "\\" in parsed.path
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise UploadError(f"Expected an S3 bucket/prefix without traversal or credentials: {value!r}")
    return parsed.netloc, parts


class LocalRoots:
    """Filesystem checks own canonicalization; S3 checks perform no remote effects."""

    def check_local_root(self, root: str) -> str:
        try:
            if not root or "\x00" in root:
                raise UploadError("Local roots must be nonempty directory paths")
            path = Path(root).expanduser().resolve(strict=True)
            if not path.is_dir():
                raise UploadError(f"Local root is not a directory: {root!r}")
        except (OSError, RuntimeError, ValueError) as error:
            raise UploadError(f"Cannot use local root {root!r}: {error}") from error
        return str(path)

    def uncovered_paths(self, frame: pd.DataFrame, roots: ImageRoots) -> list[str]:
        approved = [Path(self.check_local_root(root)) for root in roots.local_root]
        if "image_path" not in frame or not frame.columns.is_unique:
            raise UploadError("Upload CSV must have a unique image_path column")
        uncovered: dict[str, None] = {}
        for value in frame["image_path"]:
            path = absolute_image_path(value)
            if not any(path.is_relative_to(root) for root in approved):
                uncovered[str(path)] = None
        return list(uncovered)

    def check_s3_paths(self, frame: pd.DataFrame, roots: ImageRoots) -> None:
        approved = [_s3_parts(root) for root in roots.s3_root]
        if not frame.columns.is_unique:
            raise UploadError("Upload CSV columns must be unique")
        if "s3_image_path" not in frame:
            return
        for value in frame["s3_image_path"]:
            if is_missing(value):
                continue
            if not isinstance(value, str):
                raise UploadError(f"S3 image path must be a string: {value!r}")
            bucket, key = _s3_parts(value)
            if not any(bucket == owner and key[: len(prefix)] == prefix for owner, prefix in approved):
                raise UploadError(f"S3 image path is outside approved S3 roots: {value!r}")
