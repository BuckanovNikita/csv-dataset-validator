from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

from ed_killer.upload.files import LocalFiles
from ed_killer.upload.models import (
    ApiClass,
    ClassInfo,
    DatasetMetadata,
    DatasetParent,
    ImageRoots,
    Publication,
    UploadCancelled,
    UploadError,
    UploadRequest,
)
from ed_killer.upload.paths import LocalRoots
from ed_killer.upload.ports import UploadServices
from ed_killer.upload.workflow import run_upload


@dataclass
class Interaction:
    answers: list[bool] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    report: Path | None = None

    def tell(self, message):
        self.messages.append(message)

    def text(self, question, default=None):
        self.questions.append(question)
        return self.texts.pop(0) if self.texts else default or ""

    def confirm(self, question, default=False):
        self.questions.append(question)
        if "valid portion" in question:
            assert self.report is not None and (self.report / "broken-images.csv").is_file()
        return self.answers.pop(0) if self.answers else default


class Store:
    def __init__(self, parent=None):
        self.parent = parent
        self.published = []

    def names(self, project):
        return ["dataset"]

    def latest(self, project, name):
        return self.parent

    def publish(self, project, name, parent_id, directory):
        assert (directory / "dataset.csv").is_file()
        self.published.append((project, name, parent_id, directory))
        return Publication("child", "1.0.1")


class Api:
    def fetch(self, url):
        return [
            ApiClass(
                id=4,
                number=93,
                name="New",
                techClass=False,
                isPeriodical=True,
                isCritical=False,
                threshold=1.0,
            )
        ]


class S3:
    def __init__(self):
        self.checked = []

    def check_root(self, root):
        self.checked.append(root)


@pytest.fixture
def scenario(tmp_path):
    source = tmp_path / "fetch"
    source.mkdir()
    images = tmp_path / "images"
    images.mkdir()
    rows = []
    for i, split in enumerate(("train", "val", "test")):
        path = images / f"{i}.png"
        Image.new("RGB", (32, 32)).save(path)
        rows.append(
            dict(
                image_name=path.name,
                image_path=str(path),
                instance_label="New",
                bbox_x_tl="1",
                bbox_y_tl="1",
                bbox_x_br="20",
                bbox_y_br="20",
                split=split,
                task_id="12",
                task_completed="true",
                extra="NA",
            )
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(source / "dataset.csv", index=False)
    for partition in ("obsolete", "in_progress", "deleted"):
        frame.iloc[:0].to_csv(source / f"{partition}.csv", index=False)
    request = UploadRequest(
        source, "Project", "dataset", "https://example.org/classes", (str(images),), (), tmp_path / "report"
    )
    interaction = Interaction(report=request.output_dir)
    store = Store()
    services = UploadServices(Api(), store, S3(), LocalRoots(), LocalFiles(), interaction)
    return request, services, frame


def test_success_reports_then_publishes_trainable_snapshot(scenario):
    request, services, _ = scenario
    result = run_upload(request, services)
    assert result.dataset_id == "child"
    assert services.datasets.published == [("Project", "dataset", None, request.output_dir)]
    assert (request.output_dir / "tasks.yaml").read_text() == "included:\n- 12\nobsolete: []\n"
    assert any("Finalized" in message for message in services.interaction.messages)


@pytest.mark.parametrize("accept", [False, True])
def test_partial_upload_requires_explicit_consent_after_original_report(scenario, accept):
    request, services, frame = scenario
    frame.loc[2, "instance_label"] = "unknown"
    frame.to_csv(request.source / "dataset.csv", index=False)
    services.interaction.answers = [False, accept]  # new class empty flag; partial consent
    if accept:
        run_upload(request, services)
        assert len(services.datasets.published) == 1
    else:
        with pytest.raises(UploadCancelled):
            run_upload(request, services)
        assert services.datasets.published == []
    broken = pd.read_csv(request.output_dir / "broken-images.csv", dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(broken, frame.iloc[[2]].reset_index(drop=True))


def test_invalid_split_blocks_entire_upload_even_with_yes_answers(scenario):
    request, services, frame = scenario
    frame.loc[2, "split"] = ""
    frame.to_csv(request.source / "dataset.csv", index=False)
    services.interaction.answers = [False, True]
    with pytest.raises(UploadError, match="split"):
        run_upload(request, services)
    assert services.datasets.published == []
    assert (request.output_dir / "report.json").is_file()
    assert not any("valid portion" in q for q in services.interaction.questions)


def test_uncovered_invalid_image_cannot_be_filtered_without_root_approval(scenario, tmp_path):
    request, services, frame = scenario
    other = tmp_path / "other"
    other.mkdir()
    Image.new("RGB", (32, 32)).save(other / "bad.png")
    frame.loc[2, ["image_path", "instance_label"]] = [str(other / "bad.png"), "unknown"]
    frame.to_csv(request.source / "dataset.csv", index=False)
    services.interaction.answers = [False, False]
    with pytest.raises(UploadCancelled):
        run_upload(request, services)
    assert services.datasets.published == []
    assert any(str(other / "bad.png") in msg for msg in services.interaction.messages)


def test_approved_extension_is_rechecked_and_persisted(scenario, tmp_path):
    request, services, frame = scenario
    other = tmp_path / "other"
    other.mkdir()
    Image.new("RGB", (32, 32)).save(other / "2.png")
    frame.loc[2, "image_path"] = str(other / "2.png")
    frame.to_csv(request.source / "dataset.csv", index=False)
    services.interaction.answers = [False, True]
    run_upload(request, services)
    metadata = services.files.read_metadata(request.output_dir / "dataset.yaml")
    assert metadata.images.local_root == [str(tmp_path / "images"), str(other)]


def test_previous_rename_preserves_policy_history_and_parent(scenario, tmp_path):
    request, services, frame = scenario
    prior = tmp_path / "previous.yaml"
    import yaml

    prior.write_text(
        yaml.safe_dump(
            DatasetMetadata(
                api_url=request.api_url,
                classes={"Old": ClassInfo(prod_id=93, alt_names=["Older"])},
                images=ImageRoots(local_root=list(request.local_roots)),
            ).model_dump()
        )
    )
    services.datasets.parent = DatasetParent("parent", "Project", "dataset", "1.0.0", prior)
    frame["instance_label"] = "Older"
    frame.to_csv(request.source / "dataset.csv", index=False)
    services.interaction.answers = [True]
    run_upload(request, services)
    metadata = services.files.read_metadata(request.output_dir / "dataset.yaml")
    assert metadata.classes["New"].alt_names == ["Older", "Old"]
    assert services.datasets.published[0][2] == "parent"
    assert pd.read_csv(request.output_dir / "dataset.csv")["instance_label"].tolist() == ["New"] * 3
    assert "Old" in services.files.read_metadata(prior).classes


def test_declined_required_rename_cancels_before_publication(scenario, tmp_path):
    request, services, _ = scenario
    prior = tmp_path / "previous.yaml"
    import yaml

    prior.write_text(
        yaml.safe_dump(
            DatasetMetadata(
                api_url=request.api_url,
                classes={"Old": ClassInfo(prod_id=93)},
                images=ImageRoots(local_root=list(request.local_roots)),
            ).model_dump()
        )
    )
    services.datasets.parent = DatasetParent("parent", "Project", "dataset", "1.0.0", prior)
    with pytest.raises(UploadCancelled):
        run_upload(request, services)
    assert services.datasets.published == []


def test_all_configured_s3_roots_checked_without_object_probes(scenario):
    request, services, _ = scenario
    from dataclasses import replace

    run_upload(replace(request, s3_roots=("s3://bucket/images", "s3://bucket/other")), services)
    assert services.s3.checked == ["s3://bucket/images", "s3://bucket/other"]
