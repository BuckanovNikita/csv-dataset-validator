"""Executable module boundaries and negative checks in isolated source trees."""

import ast
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "ed_killer"


def facade_violations(source: str) -> list[str]:
    """The facade may declare exports, but cannot start application effects."""
    allowed = {f"{PACKAGE}.{name}" for name in ("csv_io", "models", "schema", "validation")}
    violations = []
    for node in ast.parse(source).body:
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            continue
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module in allowed:
            continue
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__all__"
            and isinstance(node.value, (ast.List, ast.Tuple))
            and all(
                isinstance(item, ast.Constant) and isinstance(item.value, str) for item in node.value.elts
            )
        ):
            continue
        violations.append(f"line {node.lineno}: {type(node).__name__}")
    return violations


def test_public_facade_has_no_composition_effects():
    source = (ROOT / "src" / PACKAGE / "__init__.py").read_text(encoding="utf-8")
    assert facade_violations(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "from ed_killer.cli import main",
        "import logging; logging.basicConfig()",
        "__all__ = open('dataset.csv').read()",
    ],
)
def test_facade_contract_rejects_effects_and_cli_imports(source):
    assert facade_violations(source)


@pytest.mark.parametrize(
    ("module", "injected_source"),
    [
        (None, ""),
        ("schema", "from ed_killer.csv_io import validate_csv"),
        ("reporting", "from ed_killer.csv_io import validate_csv"),
        ("reporting", "from ed_killer.validation import validate_dataframe"),
        ("models", "from ed_killer.geometry import find_duplicates"),
        ("geometry", "from ed_killer.media import inspect_images"),
    ],
)
def test_import_contracts_reject_prohibited_edges(tmp_path, module, injected_source):
    package = tmp_path / PACKAGE
    shutil.copytree(ROOT / "src" / PACKAGE, package, ignore=shutil.ignore_patterns("__pycache__"))
    config = tmp_path / "pyproject.toml"
    shutil.copyfile(ROOT / "pyproject.toml", config)
    if module is not None:
        with (package / f"{module}.py").open("a", encoding="utf-8") as stream:
            stream.write(f"\n{injected_source}\n")
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
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = result.stdout + result.stderr
    if module is None:
        assert result.returncode == 0, output
        assert "3 kept, 0 broken" in output
    else:
        assert result.returncode == 1, output
        assert "BROKEN" in output
        assert f"{PACKAGE}.{module}" in output


def consumer_imports(source: str) -> list[str]:
    """Inspect lazy and type-only imports without installing either consumer."""
    forbidden = {"cveta2", "clearml_yolo"}
    found = []
    for node in ast.walk(ast.parse(source)):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        found.extend(name for name in names if name.split(".")[0] in forbidden)
    return found


def test_package_has_no_consumer_dependencies():
    for source in (ROOT / "src" / PACKAGE).rglob("*.py"):
        assert consumer_imports(source.read_text(encoding="utf-8")) == [], source


@pytest.mark.parametrize(
    "source",
    [
        "import cveta2",
        "import clearml_yolo as consumer",
        "from cveta2.models import Record",
        "from clearml_yolo.adapters import storage as storage_adapter",
        "if TYPE_CHECKING:\n    import cveta2.models",
        "def load():\n    from clearml_yolo import pipeline",
    ],
)
def test_consumer_contract_rejects_direct_and_nested_imports(source):
    assert consumer_imports(source)


def test_local_documentation_links_resolve():
    documents = [ROOT / "README.md", ROOT / "AGENTS.md", *sorted((ROOT / "docs").rglob("*.md"))]
    for document in documents:
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            destination = (document.parent / target.split("#")[0]).resolve()
            assert destination.is_relative_to(ROOT), (document, target)
            assert destination.exists(), (document, target)
