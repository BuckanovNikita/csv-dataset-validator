"""Executable upload effect boundaries, including lazy and dynamic imports."""

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def imports(source):
    tree = ast.parse(source)
    dynamic = {"__import__", "importlib.import_module"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            dynamic.update(
                f"{alias.asname}.import_module"
                for alias in node.names
                if alias.name == "importlib" and alias.asname
            )
        elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
            dynamic.update(
                alias.asname or alias.name for alias in node.names if alias.name == "import_module"
            )
    result = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            result.append(node.module or "")
        elif isinstance(node, ast.Call) and ast.unparse(node.func) in dynamic and node.args:
            arg = node.args[0]
            result.append(
                arg.value.lstrip(".")
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                else "<dynamic>"
            )
    return result


def violations(path, source):
    found = []
    network = {"clearml", "boto3", "botocore", "requests", "httpx", "socket", "http.client", "urllib.request"}
    forbidden = {"cveta2", "clearml_yolo", "<dynamic>"}
    if path != "upload/remote.py":
        forbidden |= network
    if not path.startswith("upload/"):
        forbidden.add("ed_killer.upload")
    if path == "upload/workflow.py":
        forbidden |= {"ed_killer.upload.remote", "ed_killer.upload.files"}
    for name in imports(source):
        if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden):
            found.append(name)
    return found


def test_only_remote_adapter_owns_network_imports():
    package = ROOT / "src/ed_killer"
    for source in package.rglob("*.py"):
        assert not violations(source.relative_to(package).as_posix(), source.read_text()), source


@pytest.mark.parametrize(
    "statement",
    [
        "import clearml",
        "from boto3 import client",
        "from urllib.request import urlopen",
        "if TYPE_CHECKING:\n    import requests",
        "def lazy():\n    import http.client",
        "import importlib as loader\nloader.import_module('clearml')",
        "from importlib import import_module as load\nload('cveta2')",
        "__import__('clearml')",
        "__import__(unknown)",
    ],
)
def test_effect_contract_rejects_hidden_imports(statement):
    assert violations("upload/classes.py", statement)


@pytest.mark.parametrize(
    "module, statement",
    [
        ("models", "from ed_killer.upload.models import DatasetMetadata"),
        ("upload/classes", "from ed_killer.upload.remote import ClearMLStore"),
        ("upload/tasks", "from ed_killer.upload.files import LocalFiles"),
        ("upload/workflow", "from ed_killer.upload.remote import ClearMLStore"),
        ("upload/workflow", "from ed_killer.upload.files import LocalFiles"),
        ("upload/ports", "from ed_killer.upload.paths import LocalRoots"),
    ],
)
def test_real_import_contracts_reject_upload_layer_violations(tmp_path, module, statement):
    package = tmp_path / "ed_killer"
    shutil.copytree(ROOT / "src/ed_killer", package, ignore=shutil.ignore_patterns("__pycache__"))
    config = tmp_path / "pyproject.toml"
    shutil.copyfile(ROOT / "pyproject.toml", config)
    with (package / f"{module}.py").open("a") as stream:
        stream.write("\n" + statement + "\n")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from importlinter.cli import lint_imports_command; lint_imports_command()",
            "--config",
            str(config),
            "--no-cache",
            "--no-logo",
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "BROKEN" in result.stdout


def test_upload_initializer_is_inert():
    tree = ast.parse((ROOT / "src/ed_killer/upload/__init__.py").read_text())
    assert all(
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
        for node in tree.body
    )


def test_dynamic_import_cannot_cross_core_or_workflow_boundary():
    assert violations("models.py", "__import__('ed_killer.upload.models')")
    assert violations("upload/workflow.py", "__import__('ed_killer.upload.remote')")
