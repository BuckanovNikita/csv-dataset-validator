"""Injected boundaries; application workflow never constructs concrete effects."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pandas as pd

from ed_killer.upload.models import (
    ApiClass,
    BundleValidation,
    ClassChange,
    DatasetMetadata,
    DatasetParent,
    FetchTables,
    ImageRoots,
    Publication,
    TaskManifest,
)


class ClassApi(Protocol):
    def fetch(self, url: str) -> list[ApiClass]: ...


class DatasetStore(Protocol):
    def names(self, project: str) -> list[str]: ...
    def latest(self, project: str, name: str) -> DatasetParent | None: ...
    def publish(self, project: str, name: str, parent_id: str | None, directory: Path) -> Publication: ...


class S3Storage(Protocol):
    def check_root(self, root: str) -> None: ...


class RootChecks(Protocol):
    def check_local_root(self, root: str) -> str: ...
    def uncovered_paths(self, frame: pd.DataFrame, roots: ImageRoots) -> list[str]: ...
    def check_s3_paths(self, frame: pd.DataFrame, roots: ImageRoots) -> None: ...


class BundleFiles(Protocol):
    def read_fetch(self, source: Path) -> FetchTables: ...
    def read_metadata(self, path: Path) -> DatasetMetadata: ...
    def write_report(
        self,
        directory: Path,
        validation: BundleValidation,
        metadata: DatasetMetadata,
        tasks: TaskManifest,
        changes: Sequence[ClassChange],
    ) -> None: ...


class Interaction(Protocol):
    def tell(self, message: str) -> None: ...
    def text(self, question: str, default: str | None = None) -> str: ...
    def confirm(self, question: str, default: bool = False) -> bool: ...


@dataclass(frozen=True)
class UploadServices:
    api: ClassApi
    datasets: DatasetStore
    s3: S3Storage
    roots: RootChecks
    files: BundleFiles
    interaction: Interaction
