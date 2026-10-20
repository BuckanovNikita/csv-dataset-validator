"""Strict local source loading and separate bundle/rejection report writing."""

import json
import os
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml
from yaml.nodes import MappingNode

from ed_killer.csv_io import read_csv
from ed_killer.reporting import report_dict
from ed_killer.upload.models import (
    BundleValidation,
    ClassChange,
    DatasetMetadata,
    FetchTables,
    TaskManifest,
    UploadError,
)


class _UniqueLoader(yaml.SafeLoader):
    """Safe YAML decoding must not silently replace duplicate class definitions."""

    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[Any, Any]:
        result: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in result
            except TypeError as error:
                raise UploadError("YAML keys must be scalar values") from error
            if duplicate:
                raise UploadError(f"Duplicate YAML key: {key!r}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


class LocalFiles:
    """All output stays in a new directory; original source files are never modified."""

    def read_fetch(self, source: Path) -> FetchTables:
        filenames = ("dataset.csv", "obsolete.csv", "in_progress.csv", "deleted.csv")
        for filename in filenames:
            if not (source / filename).is_file():
                raise UploadError(f"Full cveta2 fetch output requires {filename} in {source}")
        return FetchTables(*(read_csv(source / filename) for filename in filenames))

    def read_metadata(self, path: Path) -> DatasetMetadata:
        try:
            value = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueLoader)
        except (yaml.YAMLError, UnicodeError) as error:
            raise UploadError(f"Cannot parse dataset metadata {path}: {error}") from error
        return DatasetMetadata.model_validate(value)

    def write_report(
        self,
        directory: Path,
        validation: BundleValidation,
        metadata: DatasetMetadata,
        tasks: TaskManifest,
        changes: Sequence[ClassChange],
    ) -> None:
        if directory.exists():
            raise FileExistsError(f"Report directory already exists: {directory}")
        directory.parent.mkdir(parents=True, exist_ok=True)
        report = report_dict(validation.result)
        # This report CSV is the complete original image evidence, without the
        # augmented columns used by the standalone validator's broken.csv.
        del report["metadata_columns"]
        report["blockers"] = list(validation.blockers)
        report["class_changes"] = [asdict(change) for change in changes]
        report["broken_image_rows"] = len(validation.broken_images)
        with TemporaryDirectory(prefix=".ed-killer-upload-", dir=directory.parent) as temporary:
            staging = Path(temporary)
            validation.result.clean.to_csv(staging / "dataset.csv", index=False, encoding="utf-8")
            validation.broken_images.to_csv(staging / "broken-images.csv", index=False, encoding="utf-8")
            for name, value in (
                ("dataset.yaml", metadata.model_dump()),
                ("tasks.yaml", tasks.model_dump()),
            ):
                (staging / name).write_text(
                    yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8"
                )
            (staging / "report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            directory.mkdir(exist_ok=False)
            for path in staging.iterdir():
                os.link(path, directory / path.name)
