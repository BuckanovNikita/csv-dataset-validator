"""Network effects for the opt-in upload workflow; importing this module is offline."""

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from http.client import HTTPException, HTTPMessage
from importlib import import_module
from pathlib import Path
from typing import IO, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import TypeAdapter, ValidationError

from ed_killer.upload.models import ApiClass, DatasetParent, Publication, UploadCancelled, UploadError

_PAYLOAD = ("dataset.csv", "dataset.yaml", "tasks.yaml")


def _public_http(url: str) -> None:
    try:
        parsed = urlsplit(url)
        valid = parsed.scheme in {"http", "https"} and parsed.hostname
        credentials = parsed.username is not None or parsed.password is not None
    except ValueError as exc:
        raise UploadError("Class API URL is malformed") from exc
    if not valid or credentials:
        raise UploadError("Class API requires an HTTP(S) URL without embedded credentials")


class _PublicRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: IO[bytes], code: int, msg: str, headers: HTTPMessage, newurl: str
    ) -> Request | None:
        _public_http(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HttpClassApi:
    """Unauthenticated HTTP registry requests, with strict response validation."""

    def __init__(self, timeout: float = 30.0) -> None:
        if timeout <= 0:
            raise ValueError("HTTP timeout must be positive")
        self.timeout = timeout

    def fetch(self, url: str) -> list[ApiClass]:
        _public_http(url)
        request = Request(url, headers={"Accept": "application/json"}, method="GET")
        try:
            with build_opener(_PublicRedirect()).open(request, timeout=self.timeout) as response:
                body = response.read()
        except HTTPError as exc:
            raise UploadError(f"Class API returned HTTP {exc.code}; check the public endpoint") from exc
        except (URLError, OSError, HTTPException, ValueError) as exc:
            raise UploadError("Class API request failed; check its URL, connectivity and timeout") from exc
        try:
            value: object = json.loads(body)
            return TypeAdapter(list[ApiClass]).validate_python(value, strict=True)
        except (ValueError, UnicodeError, ValidationError) as exc:
            raise UploadError("Class API must return a JSON list of valid class definitions") from exc


class _Dataset(Protocol):
    """Preserve SDK keyword names; V107 annotations cover vulture's stub false positives."""

    @property
    def id(self) -> str: ...
    @property
    def project(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def version(self) -> str | None: ...
    def is_final(self) -> bool: ...
    def is_dirty(self) -> bool: ...
    def list_files(self) -> list[str]: ...
    def get_local_copy(
        self,
        *,
        files: list[str],
        use_soft_links: bool,  # noqa: V107
        raise_on_error: bool,  # noqa: V107
    ) -> str: ...
    def remove_files(self, *, dataset_path: str, recursive: bool) -> int: ...  # noqa: V107
    def add_files(self, *, path: str, local_base_folder: str) -> int: ...  # noqa: V107
    def upload(self, *, retries: int) -> bool | None: ...  # noqa: V107
    def finalize(self, *, raise_on_error: bool, auto_upload: bool) -> bool: ...  # noqa: V107


class _DatasetFactory(Protocol):
    def list_datasets(
        self,
        *,
        dataset_project: str,  # noqa: V107
        only_completed: bool,  # noqa: V107
        recursive_project_search: bool,  # noqa: V107
        include_archived: bool,  # noqa: V107
    ) -> list[Mapping[str, object]]: ...
    def get(
        self,
        *,
        dataset_project: str,  # noqa: V107
        dataset_name: str,
        only_completed: bool,  # noqa: V107
        auto_create: bool,  # noqa: V107
        include_archived: bool,  # noqa: V107
    ) -> _Dataset: ...
    def create(
        self,
        *,
        dataset_project: str,  # noqa: V107
        dataset_name: str,
        parent_datasets: list[str],  # noqa: V107
    ) -> _Dataset: ...


class _Storage(Protocol):
    def list(self, *, remote_url: str, return_full_path: bool) -> list[str] | None: ...  # noqa: V107


class _Sdk(Protocol):
    Dataset: _DatasetFactory
    StorageManager: _Storage


def _sdk() -> _Sdk:
    try:
        # The optional third-party SDK is opaque here; typed protocols keep its
        # implementation types and lazy import out of the application contracts.
        return cast(_Sdk, import_module("clearml"))
    except ImportError as exc:
        raise UploadError(
            "Install ed-killer[clearml] and configure the ClearML SDK before uploading"
        ) from exc


@contextmanager
def _sdk_errors(context: str, *, publication_id: str | None = None) -> Iterator[None]:
    try:
        yield
    except KeyboardInterrupt as exc:
        if publication_id is None:
            raise
        # The server may have received the last mutation before interruption.
        # Keep cancellation semantics without claiming that no child was created.
        raise UploadCancelled(
            f"Publication interrupted for ClearML dataset {publication_id}; "
            "its remote state is uncertain. Inspect it before retrying."
        ) from exc
    except UploadError:
        raise
    except Exception as exc:
        # ClearML/storage plugins expose heterogeneous backend/auth/network errors.
        # This adapter boundary can translate them; preserve the cause for diagnosis.
        raise UploadError(
            f"{context}; check ClearML configuration, credentials and connectivity ({exc})"
        ) from exc


class ClearMLStore:
    """Discover finalized datasets and publish an exact replacement child manifest."""

    @staticmethod
    def _listing(factory: _DatasetFactory, project: str) -> list[Mapping[str, object]]:
        return [
            row
            for row in factory.list_datasets(
                dataset_project=project,
                only_completed=True,
                recursive_project_search=False,
                include_archived=False,
            )
            if row.get("project") == project
        ]

    def names(self, project: str) -> list[str]:
        with _sdk_errors("Cannot list ClearML datasets"):
            rows = self._listing(_sdk().Dataset, project)
            return sorted({name for row in rows if isinstance(name := row.get("name"), str)})

    def latest(self, project: str, name: str) -> DatasetParent | None:
        with _sdk_errors("Cannot retrieve the latest finalized ClearML dataset"):
            factory = _sdk().Dataset
            # A successful listing proves absence; never interpret a get/auth/network
            # exception as a missing dataset and accidentally create a new lineage.
            if not any(row.get("name") == name for row in self._listing(factory, project)):
                return None
            dataset = factory.get(
                dataset_project=project,
                dataset_name=name,
                only_completed=True,
                auto_create=False,
                include_archived=False,
            )
            if dataset.project != project or dataset.name != name or not dataset.is_final():
                raise UploadError("ClearML returned a different project/name or an unfinalized parent")
            metadata_path = None
            if "dataset.yaml" in dataset.list_files():
                directory = dataset.get_local_copy(
                    files=["dataset.yaml"],
                    use_soft_links=False,
                    raise_on_error=True,
                )
                metadata_path = Path(directory) / "dataset.yaml"
                if not metadata_path.is_file():
                    raise UploadError("ClearML parent advertised dataset.yaml but its download is missing")
            return DatasetParent(dataset.id, project, name, dataset.version, metadata_path)

    def publish(self, project: str, name: str, parent_id: str | None, directory: Path) -> Publication:
        for filename in _PAYLOAD:
            if not (directory / filename).is_file():
                raise UploadError(f"Required upload file is missing: {filename}")
        child: _Dataset | None = None
        with _sdk_errors("Cannot create ClearML child dataset"):
            child = _sdk().Dataset.create(
                dataset_project=project,
                dataset_name=name,
                parent_datasets=[parent_id] if parent_id is not None else [],
            )
        with _sdk_errors(
            f"Publication failed for created ClearML dataset {child.id}; inspect it before retrying",
            publication_id=child.id,
        ):
            if child.id == parent_id:
                raise UploadError(f"ClearML returned parent {parent_id} as the child; refusing mutation")
            # Public remove_files clears both regular files and external links in
            # this child only. Parent content and parent SDK instances stay intact.
            if child.list_files():
                child.remove_files(dataset_path="*", recursive=True)
            if child.list_files():
                raise UploadError(f"Created ClearML dataset {child.id} retained inherited entries")
            for filename in _PAYLOAD:
                child.add_files(path=str(directory / filename), local_base_folder=str(directory))
            if set(child.list_files()) != set(_PAYLOAD):
                raise UploadError(
                    f"Created ClearML dataset {child.id} does not contain exactly the three bundle files"
                )
            # upload is synchronous in ClearML. Disable SDK retries and finalize's
            # implicit upload to avoid replaying mutation after uncertain failures.
            if child.upload(retries=0) is False or child.is_dirty():
                raise UploadError(f"Upload did not complete for created ClearML dataset {child.id}")
            if set(child.list_files()) != set(_PAYLOAD):
                raise UploadError(f"Upload lost bundle files for created ClearML dataset {child.id}")
            if child.finalize(raise_on_error=True, auto_upload=False) is not True or not child.is_final():
                raise UploadError(f"Finalization did not complete for created ClearML dataset {child.id}")
            if set(child.list_files()) != set(_PAYLOAD):
                raise UploadError(f"Finalized ClearML dataset {child.id} has an unexpected file manifest")
            return Publication(child.id, child.version)


class S3Roots:
    """Check configured S3 bucket/prefix listings without requesting image objects."""

    def check_root(self, root: str) -> None:
        try:
            parsed = urlsplit(root)
        except ValueError as exc:
            raise UploadError("S3 root is malformed") from exc
        if (
            parsed.scheme != "s3"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise UploadError(
                "S3 roots must be s3://bucket/prefix URLs without credentials, query or fragment"
            )
        boundary = root.rstrip("/") + "/"
        with _sdk_errors(f"Cannot access S3 root {root}; configure ClearML S3 storage and list permissions"):
            objects = _sdk().StorageManager.list(remote_url=boundary, return_full_path=True)
            if objects is None:
                raise UploadError(f"S3 listing unavailable for {root}; check ClearML storage configuration")
            # A successful empty bucket listing proves access. A nonempty prefix
            # must have an entry at its directory boundary, not a sibling prefix.
            if parsed.path.strip("/") and not any(path.startswith(boundary) for path in objects):
                raise UploadError(f"S3 root prefix does not exist or is empty: {root}")
