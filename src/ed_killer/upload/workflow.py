"""Bundle orchestration over injected effects, before any remote dataset creation."""

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pandas as pd

from ed_killer.upload.classes import reconcile_classes
from ed_killer.upload.models import (
    ClassInfo,
    ClassUpdate,
    DatasetMetadata,
    ImageRoots,
    Publication,
    TaskManifest,
    UploadCancelled,
    UploadError,
    UploadRequest,
)
from ed_killer.upload.ports import UploadServices
from ed_killer.upload.tasks import derive_tasks
from ed_killer.upload.validation import validate_bundle


def _choose_classes(previous: DatasetMetadata | None, api_url: str, services: UploadServices) -> ClassUpdate:
    update = reconcile_classes(previous.classes if previous else {}, services.api.fetch(api_url))
    classes = dict(update.classes)
    for change in update.changes:
        if previous is not None:
            description = (
                f"Rename {change.old_name!r} to {change.name!r}; retain obsolete names"
                if change.kind == "renamed"
                else f"Add class {change.name!r}"
            )
            if not services.interaction.confirm(f"{description} (API number {change.prod_id})?"):
                raise UploadCancelled("Required class reconciliation was declined.")
        if change.kind == "added":
            empty = services.interaction.confirm(
                f"Mark class {change.name!r} (API number {change.prod_id}) as empty/excluded?"
            )
            classes[change.name] = ClassInfo(prod_id=change.prod_id, empty=empty)
    return ClassUpdate(classes, update.changes)


def _approve_roots(frame: pd.DataFrame, roots: ImageRoots, services: UploadServices) -> ImageRoots:
    local = list(dict.fromkeys(services.roots.check_local_root(root) for root in roots.local_root))
    current = ImageRoots(local_root=local, s3_root=list(dict.fromkeys(roots.s3_root)))
    while uncovered := services.roots.uncovered_paths(frame, current):
        services.interaction.tell("Image paths outside approved local roots:\n" + "\n".join(uncovered))
        proposed = sorted({str(Path(path).parent) for path in uncovered})
        if services.interaction.confirm("Add these local roots?\n" + "\n".join(proposed)):
            additions = proposed
        else:
            root = services.interaction.text("Enter an additional local root, or blank to cancel")
            if not root:
                raise UploadCancelled("Local image root coverage was not approved.")
            additions = [root]
        local = list(dict.fromkeys([*local, *(services.roots.check_local_root(root) for root in additions)]))
        current = ImageRoots(local_root=local, s3_root=current.s3_root)
    services.roots.check_s3_paths(frame, current)
    for root in current.s3_root:
        services.s3.check_root(root)
    return current


def run_upload(request: UploadRequest, services: UploadServices) -> Publication:
    """Write reviewable reports, enforce every blocking check, then publish once."""
    if not request.project.strip():
        raise UploadError("ClearML project must be nonempty.")
    tables = services.files.read_fetch(request.source)
    name = request.dataset_name
    if name is None:
        names = services.datasets.names(request.project)
        services.interaction.tell("Existing datasets: " + (", ".join(names) or "(none)"))
        name = services.interaction.text("Dataset name", default="dataset")
    if not name.strip():
        raise UploadCancelled("No dataset name selected.")
    parent = services.datasets.latest(request.project, name)
    previous = None
    if parent is not None:
        if parent.metadata_path is None:
            raise UploadError(f"Latest finalized dataset {parent.dataset_id} has no dataset.yaml.")
        previous = services.files.read_metadata(parent.metadata_path)
    api_url = request.api_url or (previous.api_url if previous else None)
    if api_url is None:
        api_url = services.interaction.text("Class API URL")
    # Validate URLs before handing them to the HTTP adapter.
    DatasetMetadata(api_url=api_url, classes={})
    if (
        previous
        and previous.api_url != api_url
        and not services.interaction.confirm(f"Change class API URL from {previous.api_url} to {api_url}?")
    ):
        raise UploadCancelled("API URL change was declined.")
    update = _choose_classes(previous, api_url, services)
    old_roots = previous.images if previous else ImageRoots()
    additions = [
        *(root for root in request.local_roots if root not in old_roots.local_root),
        *(root for root in request.s3_roots if root not in old_roots.s3_root),
    ]
    if (
        previous
        and additions
        and not services.interaction.confirm("Extend saved image roots with:\n" + "\n".join(additions))
    ):
        raise UploadCancelled("Image root changes were declined.")
    roots = _approve_roots(
        tables.dataset,
        ImageRoots(
            local_root=[*old_roots.local_root, *request.local_roots],
            s3_root=[*old_roots.s3_root, *request.s3_roots],
        ),
        services,
    )
    metadata = DatasetMetadata(api_url=api_url, classes=update.classes, images=roots)
    validation = validate_bundle(tables.dataset, metadata, request.source)
    try:
        tasks = derive_tasks(tables, validation.result.clean)
    except UploadError as error:
        tasks = TaskManifest(included=[], obsolete=[])
        validation = replace(validation, blockers=(*validation.blockers, str(error)))
    directory = request.output_dir or request.source.parent / (
        f"{request.source.name}-validated-{uuid4().hex[:12]}"
    )
    services.files.write_report(directory, validation, metadata, tasks, update.changes)
    result = validation.result
    services.interaction.tell(
        f"Validation: {len(result.clean)} valid rows, {len(result.broken)} rejected rows; "
        f"{result.clean_image_count} valid images.\n"
        f"Full original rows of affected images: {directory / 'broken-images.csv'}\n"
        f"Detailed report: {directory / 'report.json'}"
    )
    if validation.blockers:
        raise UploadError("\n".join(validation.blockers))
    if result.broken_row_positions and not services.interaction.confirm(
        "Upload only the valid portion shown in these reports?"
    ):
        raise UploadCancelled(f"Partial upload declined. Reports retained in {directory}.")
    publication = services.datasets.publish(
        request.project, name, parent.dataset_id if parent else None, directory
    )
    services.interaction.tell(
        f"Finalized dataset {publication.dataset_id}, version {publication.version or '(server assigned)'}."
    )
    return publication
