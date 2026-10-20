import builtins
import subprocess
import sys

import pytest

from ed_killer.upload import cli
from ed_killer.upload.models import Publication, UploadCancelled, UploadError


@pytest.mark.parametrize("answer, expected", [("", False), ("n", False), ("yes", True), ("Y", True)])
def test_confirmation_defaults_to_no(monkeypatch, answer, expected):
    monkeypatch.setattr(builtins, "input", lambda prompt: answer)
    assert cli.ConsoleInteraction().confirm("Upload?") is expected


def test_eof_never_implies_consent(monkeypatch):
    def eof(prompt):
        raise EOFError

    monkeypatch.setattr(builtins, "input", eof)
    with pytest.raises(UploadCancelled):
        cli.ConsoleInteraction().confirm("Upload?")


@pytest.mark.parametrize(
    "failure, code",
    [(None, 0), (UploadCancelled("declined"), 1), (UploadError("invalid"), 2), (OSError("failed"), 2)],
)
def test_cli_exit_codes_and_arguments(monkeypatch, tmp_path, failure, code):
    seen = []

    def run(request, services):
        seen.append(request)
        if failure:
            raise failure
        return Publication("new", "1")

    monkeypatch.setattr(cli, "_services", lambda: object())
    monkeypatch.setattr(cli, "run_upload", run)
    assert (
        cli.main(
            [
                str(tmp_path),
                "--project",
                "Project",
                "--dataset-name",
                "named",
                "--local-root",
                str(tmp_path),
                "--s3-root",
                "s3://bucket/a",
            ]
        )
        == code
    )
    assert seen[0].project == "Project"
    assert seen[0].local_roots == (str(tmp_path),)
    assert seen[0].s3_roots == ("s3://bucket/a",)


def test_module_help_is_real_cli_without_configuration():
    result = subprocess.run(
        [sys.executable, "-m", "ed_killer.upload.cli", "--help"], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    assert "--project" in result.stdout
    assert "--s3-root" in result.stdout
