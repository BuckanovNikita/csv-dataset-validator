"""Optional local image inspection without remote access."""

import re
from pathlib import Path

import pandas as pd

from .models import DatasetInputError, Issue, Profile, ValidationOptions

_URI_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def resolve_image_path(image_name: str, image_path: object, options: ValidationOptions) -> Path | None:
    """Resolve an explicitly local path; a root fills only a missing path cell."""
    if isinstance(image_path, (str, Path)) and str(image_path) != "":
        raw_path = str(image_path)
        if _URI_SCHEME.match(raw_path) and not Path(raw_path).drive:
            return None
        path = Path(raw_path).expanduser()
    elif options.image_root is not None:
        if _URI_SCHEME.match(image_name) or (
            _URI_SCHEME.match(str(options.image_root)) and not options.image_root.drive
        ):
            return None
        path = options.image_root.expanduser() / image_name
    else:
        return None
    if not path.is_absolute():
        path = (options.base_dir or Path.cwd()).expanduser() / path
    return path


def inspect_images(
    frame: pd.DataFrame, *, profile: Profile, options: ValidationOptions
) -> tuple[dict[int, tuple[int, int]], list[Issue]]:
    """Verify each canonical file once and attach its result to all input rows."""
    if not options.check_images:
        return {}, []
    try:
        from PIL import Image, UnidentifiedImageError
    except ModuleNotFoundError as error:
        if error.name != "PIL" and not (error.name or "").startswith("PIL."):
            raise
        raise DatasetInputError("Local image checks require Pillow; install 'ed-killer[images]'.") from error

    sizes: dict[int, tuple[int, int]] = {}
    issues: list[Issue] = []
    cache: dict[Path, tuple[int, int] | tuple[str, str]] = {}
    columns = list(frame.columns)
    name_column = columns.index("image_name")
    path_column = columns.index("image_path") if "image_path" in frame else None
    shape_column = columns.index("instance_shape") if "instance_shape" in frame else None
    for row in frame.itertuples(index=True, name=None):
        position = int(row[0])
        cells = row[1:]
        if profile == "cveta2" and shape_column is not None and cells[shape_column] == "deleted":
            continue
        try:
            path = resolve_image_path(
                str(cells[name_column]), cells[path_column] if path_column is not None else None, options
            )
            canonical_path = path.resolve() if path is not None else None
        except (OSError, RuntimeError, ValueError) as error:
            issues.append(
                Issue(
                    code="media_unreadable",
                    message=f"Cannot resolve local image path: {error}",
                    row_position=position,
                    columns=("image_path",),
                )
            )
            continue
        if canonical_path is None:
            result: tuple[int, int] | tuple[str, str] = (
                "media_unreadable",
                "No local image path is available; remote URIs are not read.",
            )
        elif canonical_path in cache:
            result = cache[canonical_path]
        else:
            try:
                with Image.open(canonical_path) as image:
                    width, height = image.size
                    if image.format == "JPEG" and image.getexif().get(274) in (6, 8):
                        width, height = height, width
                    # JPEG.verify() checks headers without decoding and
                    # accepts truncated image data. Decode once instead.
                    image.load()
                if width <= 0 or height <= 0:
                    result = (
                        "media_invalid_dimensions",
                        f"Image dimensions must be positive: {width}x{height}.",
                    )
                else:
                    result = (width, height)
            except FileNotFoundError as error:
                result = ("media_missing", f"Image does not exist: {canonical_path}: {error}")
            except (
                OSError,
                UnidentifiedImageError,
                Image.DecompressionBombError,
                ValueError,
                SyntaxError,
            ) as error:
                result = ("media_unreadable", f"Cannot read image {canonical_path}: {error}")
            cache[canonical_path] = result
        if isinstance(result[0], int):
            sizes[position] = result
        else:
            code, message = result
            issues.append(Issue(code=code, message=message, row_position=position, columns=("image_path",)))
    return sizes, issues
