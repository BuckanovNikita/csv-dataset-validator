"""Real console/HTTP/filesystem flow with an explicit in-process SDK substitute."""

import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pandas as pd
import pytest
import yaml
from PIL import Image

SDK_DOUBLE = """
import json
import os
from pathlib import Path

class Child:
    id = "created-id"
    version = "1.0.0"
    def __init__(self):
        self.files = {}
        self.final = False
    def list_files(self):
        return list(self.files)
    def add_files(self, *, path, local_base_folder):
        self.files[Path(path).name] = Path(path).read_text()
    def is_dirty(self):
        return False
    def upload(self, *, retries):
        assert retries == 0
        if os.environ.get("INTERRUPT_STAGE") == "upload":
            raise KeyboardInterrupt
    def finalize(self, *, raise_on_error, auto_upload):
        assert not auto_upload and raise_on_error
        if os.environ.get("INTERRUPT_STAGE") == "finalize":
            raise KeyboardInterrupt
        self.final = True
        Path(os.environ["PUBLICATION_CAPTURE"]).write_text(json.dumps(self.files))
        return True
    def is_final(self):
        return self.final

class Dataset:
    @staticmethod
    def list_datasets(**kwargs):
        assert kwargs["only_completed"] and not kwargs["recursive_project_search"]
        return []
    @staticmethod
    def create(**kwargs):
        assert kwargs == dict(dataset_project="Project", dataset_name="dataset", parent_datasets=[])
        return Child()

class StorageManager:
    @staticmethod
    def list(*, remote_url, return_full_path):
        assert remote_url == "s3://bucket/images/" and return_full_path
        return ["s3://bucket/images/example.png"]
"""


@pytest.mark.parametrize(
    "consent, expected, interrupt",
    [("y", 0, ""), ("n", 1, ""), (None, 1, ""), ("y", 1, "upload"), ("y", 1, "finalize")],
)
def test_packaged_command_real_http_and_reports_before_partial_consent(
    tmp_path, consent, expected, interrupt
):
    (tmp_path / "clearml.py").write_text(SDK_DOUBLE)
    source = tmp_path / "fetch"
    source.mkdir()
    rows = []
    for i, split in enumerate(("train", "val", "test")):
        path = tmp_path / f"{i}.png"
        Image.new("RGB", (32, 32)).save(path)
        rows.append(
            dict(
                image_name=path.name,
                image_path=str(path),
                instance_label="Old" if i == 2 else "New",
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
    payload = json.dumps(
        [
            dict(
                id=4,
                number=93,
                name="New",
                techClass=False,
                isPeriodical=True,
                isCritical=False,
                threshold=1.0,
            )
        ]
    ).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            assert self.path == "/classes"
            assert "Authorization" not in self.headers
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    report = tmp_path / "report"
    capture = tmp_path / "published.json"
    try:
        command = [
            str(Path(sys.executable).with_name("ed-killer-upload")),
            str(source),
            "--project",
            "Project",
            "--dataset-name",
            "dataset",
            "--api-url",
            f"http://127.0.0.1:{server.server_port}/classes",
            "--local-root",
            str(tmp_path),
            "--s3-root",
            "s3://bucket/images",
            "--output-dir",
            str(report),
        ]
        result = subprocess.run(
            command,
            input="n\n" + (f"{consent}\n" if consent is not None else ""),
            text=True,
            capture_output=True,
            cwd=tmp_path,
            timeout=30,
            env={
                **os.environ,
                "PYTHONPATH": str(tmp_path),
                "PUBLICATION_CAPTURE": str(capture),
                "INTERRUPT_STAGE": interrupt,
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert result.returncode == expected, result.stdout + result.stderr
    assert result.stdout.index("broken-images.csv") < result.stdout.index("Upload only the valid portion")
    broken = pd.read_csv(report / "broken-images.csv", dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(broken, frame.iloc[[2]].reset_index(drop=True))
    if expected == 0:
        published = json.loads(capture.read_text())
        assert set(published) == {"dataset.csv", "dataset.yaml", "tasks.yaml"}
        assert yaml.safe_load(published["dataset.yaml"])["classes"]["New"]["prod_id"] == 93
        assert "Finalized dataset created-id" in result.stdout
    else:
        assert not capture.exists()
        if interrupt:
            assert "created-id" in result.stderr
            assert "inspect" in result.stderr.lower()
