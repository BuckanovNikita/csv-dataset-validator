"""Release tooling boundaries and publication policy, including negative controls."""

import ast
import copy
import re
import shlex
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
RELEASE_PACKAGES = {"python-semantic-release", "tomli", "types-pyyaml"}
QUALITY_HOOKS = {"ruff-format", "ruff-check", "mypy", "vulture", "architecture", "pytest", "uv-lock"}


def prohibited_imports(source: str, forbidden: set[str]) -> list[str]:
    """Walk every scope so lazy imports and TYPE_CHECKING cannot bypass contracts."""
    found = []
    tree = ast.parse(source)
    dynamic_names = {"__import__", "importlib.import_module"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "importlib" and alias.asname:
                    dynamic_names.add(f"{alias.asname}.import_module")
        elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
            dynamic_names.update(
                alias.asname or alias.name for alias in node.names if alias.name == "import_module"
            )
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        elif (
            isinstance(node, ast.Call)
            and ast.unparse(node.func) in dynamic_names
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            names = [node.args[0].value.lstrip(".")]
        found.extend(name for name in names if name.split(".")[0] in forbidden)
    return found


def dependency_violations(config: dict) -> list[str]:
    project = config["project"]
    runtime = list(project.get("dependencies", []))
    for dependencies in project.get("optional-dependencies", {}).values():
        runtime.extend(dependencies)
    names = [re.split(r"[\s\[<>=!~;]", dependency, maxsplit=1)[0] for dependency in runtime]
    violations = [name for name in names if re.sub(r"[-_.]+", "-", name).lower() in RELEASE_PACKAGES]
    dev = config.get("dependency-groups", {}).get("dev", [])
    if not any(
        isinstance(item, str) and item.startswith("python-semantic-release>=10.6.1,<11") for item in dev
    ):
        violations.append("missing bounded dev-only PSR dependency")
    return violations


def release_policy_violations(config: dict) -> list[str]:
    policy = config.get("tool", {}).get("semantic_release", {})
    expected = {
        "commit_parser": "conventional",
        "version_toml": ["pyproject.toml:project.version"],
        "tag_format": "v{version}",
        "allow_zero_version": True,
        "major_on_zero": False,
        "commit_message": "chore(release): {version}",
        "no_git_verify": False,
    }
    violations = [name for name, value in expected.items() if policy.get(name) != value]
    if policy.get("branches") != {"main": {"match": "^main$", "prerelease": False}}:
        violations.append("main-only release branches")
    if policy.get("build_command"):
        violations.append("release build command")
    if policy.get("publish") != {"upload_to_vcs_release": False, "dist_glob_patterns": []}:
        violations.append("disabled release/package uploads")
    templates = policy.get("changelog", {}).get("default_templates", {})
    if templates.get("changelog_file") != "CHANGELOG.md" or templates.get("output_format") != "md":
        violations.append("Markdown changelog destination")
    return violations


def publication_commands(tokens: list[str]) -> list[str]:
    """Recognize forbidden remote effects in literal process command arguments."""
    prohibited = (
        ("git", "push"),
        ("git", "fetch"),
        ("uv", "publish"),
        ("twine", "upload"),
        ("semantic_release", "publish"),
        ("semantic-release", "publish"),
        ("gh", "release", "create"),
        ("gh", "release", "upload"),
        ("gh", "api"),
    )
    # Flatten shell fragments and Python -m entrypoints without running commands.
    words = [word for token in tokens for word in shlex.split(token)]
    return [" ".join(command) for command in prohibited if all(word in words for word in command)]


def helper_policy_violations(source: str) -> list[str]:
    tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    semantic = functions.get("semantic_release")
    flags = (
        {
            node.value
            for node in ast.walk(semantic)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        if semantic
        else set()
    )
    required = {"version", "--skip-build", "--no-commit", "--no-tag", "--no-push", "--no-vcs-release"}
    violations = sorted(required - flags)
    if flags & {"--push", "--vcs-release", "--build"}:
        violations.append("enabled PSR publication/build")
    launcher = functions.get("install_hooks")
    launcher_strings = (
        " ".join(
            node.value
            for node in ast.walk(launcher)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        )
        if launcher
        else ""
    )
    if "--hook-stage post-commit --all-files" not in launcher_strings:
        violations.append("post-commit must inspect all files")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            tokens = [
                value.value
                for arg in node.args
                for value in ast.walk(arg)
                if isinstance(value, ast.Constant) and isinstance(value.value, str)
            ]
            violations.extend(publication_commands(tokens))
    return violations


def hook_policy_violations(config: dict) -> list[str]:
    violations = []
    if config.get("default_stages") != ["pre-commit"]:
        violations.append("default quality stages")
    if config.get("default_install_hook_types") != ["pre-commit"]:
        violations.append("default hook installation")
    hooks = {hook["id"]: hook for repo in config["repos"] for hook in repo["hooks"]}
    violations.extend(sorted((QUALITY_HOOKS | {"changelog", "local-release"}) - hooks.keys()))
    for name, hook in hooks.items():
        stages = hook.get("stages", config.get("default_stages"))
        if stages != (["post-commit"] if name == "local-release" else ["pre-commit"]):
            violations.append(f"{name} stages")
        violations.extend(publication_commands([hook["entry"], *hook.get("args", [])]))
    release = hooks.get("local-release", {})
    if release.get("args") != ["--post-commit"]:
        violations.append("post-commit entrypoint")
    if not release.get("always_run") or release.get("pass_filenames") is not False:
        violations.append("unconditional post-commit invocation")
    changelog = hooks.get("changelog", {})
    if "scripts/local_release.py --changelog" not in changelog.get("entry", ""):
        violations.append("changelog entrypoint")
    return violations


def ci_policy_violations(config: dict) -> list[str]:
    violations = []
    if config.get("permissions") != {"contents": "read"}:
        violations.append("read-only CI permissions")
    for job in config["jobs"].values():
        if "permissions" in job and job["permissions"] != {"contents": "read"}:
            violations.append("read-only job permissions")
        for step in job["steps"]:
            action = step.get("uses", "")
            if action.startswith("actions/checkout@") and step.get("with", {}).get("fetch-depth") != 0:
                violations.append("full Git history")
            if "release" in action.lower() or "upload-artifact" in action.lower():
                violations.append("publication action")
            if "run" in step:
                violations.extend(publication_commands([step["run"]]))
    return violations


def test_release_helper_and_runtime_have_independent_imports():
    helper = (ROOT / "scripts/local_release.py").read_text()
    assert prohibited_imports(helper, {"ed_killer", "cveta2", "clearml_yolo"}) == []
    for source in (ROOT / "src/ed_killer").rglob("*.py"):
        assert prohibited_imports(source.read_text(), {"scripts", "semantic_release"}) == [], source


@pytest.mark.parametrize("module", ["ed_killer", "cveta2", "clearml_yolo", "scripts", "semantic_release"])
@pytest.mark.parametrize(
    "statement",
    [
        "import {module}.models",
        "from {module} import models",
        "if TYPE_CHECKING:\n    import {module}",
        "def lazy():\n    from {module} import models",
        "import importlib as loader\nloader.import_module('{module}.models')",
        "from importlib import import_module as load\nload('{module}')",
        "__import__('{module}')",
    ],
)
def test_import_contract_rejects_prohibited_edges(module, statement):
    assert prohibited_imports(statement.format(module=module), {module})


def test_current_release_dependency_and_policy_contracts():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert dependency_violations(config) == []
    assert release_policy_violations(config) == []
    assert helper_policy_violations((ROOT / "scripts/local_release.py").read_text()) == []
    assert hook_policy_violations(yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())) == []
    assert ci_policy_violations(yaml.safe_load((ROOT / ".github/workflows/check.yml").read_text())) == []


@pytest.mark.parametrize(
    "dependency", ["python-semantic-release>=10", "Python_Semantic_Release>=10", "tomli>=2"]
)
@pytest.mark.parametrize("optional", [False, True])
def test_dependencies_contract_rejects_release_tools_in_runtime(dependency, optional):
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    if optional:
        config["project"].setdefault("optional-dependencies", {})["unsafe"] = [dependency]
    else:
        config["project"]["dependencies"].append(dependency)
    assert dependency_violations(config)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("commit_parser", "angular"),
        ("allow_zero_version", False),
        ("major_on_zero", True),
        ("no_git_verify", True),
        ("branches", {"all": {"match": ".*", "prerelease": False}}),
        ("build_command", "uv build"),
        ("publish", {"upload_to_vcs_release": True, "dist_glob_patterns": ["dist/*"]}),
    ],
)
def test_release_policy_contract_rejects_unsafe_configuration(key, value):
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    config["tool"]["semantic_release"][key] = value
    assert release_policy_violations(config)


@pytest.mark.parametrize("flag", ["--skip-build", "--no-commit", "--no-tag", "--no-push", "--no-vcs-release"])
def test_helper_contract_rejects_missing_psr_guards(flag):
    source = (ROOT / "scripts/local_release.py").read_text().replace(f'"{flag}",', "")
    assert helper_policy_violations(source)


@pytest.mark.parametrize(
    "command",
    [
        'run(root, "git", "push", "origin", "main")',
        'run(root, "git", "fetch", "origin")',
        'run(root, "uv", "publish")',
        'run(root, sys.executable, "-m", "twine", "upload", "dist/*")',
        'run(root, sys.executable, "-m", "semantic_release", "publish")',
        'subprocess.run(["gh", "release", "create", "v1.0.0"])',
        'subprocess.run(["gh", "api", "repos/example/project/releases"])',
    ],
)
def test_helper_contract_rejects_publication_commands(command):
    source = (ROOT / "scripts/local_release.py").read_text() + f"\n{command}\n"
    assert helper_policy_violations(source)


@pytest.mark.parametrize(
    "mutation", ["quality-stage", "release-stage", "default-install", "entrypoint", "publish"]
)
def test_hook_contract_rejects_unsafe_stages_and_commands(mutation):
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    hooks = {hook["id"]: hook for repo in config["repos"] for hook in repo["hooks"]}
    if mutation == "quality-stage":
        config["default_stages"] = ["pre-commit", "post-commit"]
    elif mutation == "release-stage":
        hooks["local-release"]["stages"] = ["pre-commit"]
    elif mutation == "default-install":
        config["default_install_hook_types"] = ["pre-commit", "post-commit"]
    elif mutation == "entrypoint":
        hooks["local-release"]["args"] = []
    else:
        hooks["local-release"]["entry"] = "gh release create v1.0.0"
    assert hook_policy_violations(config)


@pytest.mark.parametrize("mutation", ["permissions", "history", "upload", "publish", "job-permissions"])
def test_ci_contract_rejects_publication_and_incomplete_history(mutation):
    config = copy.deepcopy(yaml.safe_load((ROOT / ".github/workflows/check.yml").read_text()))
    job = next(iter(config["jobs"].values()))
    if mutation == "permissions":
        config["permissions"] = {"contents": "write"}
    elif mutation == "job-permissions":
        job["permissions"] = {"contents": "write"}
    elif mutation == "history":
        checkout = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@"))
        checkout["with"]["fetch-depth"] = 1
    elif mutation == "upload":
        job["steps"].append({"uses": "actions/upload-artifact@v4"})
    else:
        job["steps"].append({"run": "uv publish"})
    assert ci_policy_violations(config)


def test_helper_contract_rejects_stashing_launcher():
    source = (ROOT / "scripts/local_release.py").read_text().replace("--all-files", "")
    assert "post-commit must inspect all files" in helper_policy_violations(source)


def test_dependency_contract_requires_bounded_dev_psr():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    config["dependency-groups"]["dev"] = [
        dependency
        for dependency in config["dependency-groups"]["dev"]
        if not dependency.startswith("python-semantic-release")
    ]
    assert dependency_violations(config)
