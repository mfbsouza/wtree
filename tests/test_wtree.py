import os
import subprocess

import pytest
from click.testing import CliRunner

from wtree.main import cli


def run_git(repo, *args):
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def branch_exists(repo, branch):
    return run_git(repo, "branch", "--list", "--format=%(refname:short)", branch) == branch


@pytest.fixture
def source_repos(tmp_path):
    repos = {}
    for name in ("frontend", "backend"):
        repo = tmp_path / "source" / f"repo-{name}"
        repo.mkdir(parents=True)
        run_git(repo, "init", "-q", "-b", "main")
        run_git(repo, "config", "user.email", "test@example.com")
        run_git(repo, "config", "user.name", "Test")
        run_git(repo, "config", "commit.gpgsign", "false")
        (repo / "README.md").write_text(f"# {name}\n")
        run_git(repo, "add", ".")
        run_git(repo, "commit", "-q", "-m", "initial commit")
        repos[name] = repo
    return repos


@pytest.fixture
def workspaces_config(tmp_path, source_repos):
    config = (
        'workspace_dir = "{ws}"\n'
        "\n"
        "[[repositories]]\n"
        'name = "frontend"\n'
        'path = "{frontend}"\n'
        "\n"
        "[[repositories]]\n"
        'name = "backend"\n'
        'path = "{backend}"\n'
    ).format(
        ws=tmp_path / "workspaces",
        frontend=source_repos["frontend"],
        backend=source_repos["backend"],
    )
    config_file = tmp_path / "cwd" / ".workspaces.toml"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(config)
    return config_file


@pytest.fixture
def runner():
    return CliRunner()


def invoke(runner, cwd, *args):
    with runner.isolated_filesystem():
        os.chdir(cwd)
        return runner.invoke(cli, args)


def test_missing_config_exits_with_message(runner, tmp_path):
    result = invoke(runner, tmp_path, "create", "ticket-foo")
    assert result.exit_code == 1
    assert "Config file not found" in result.output


def test_init_creates_default_config(runner, tmp_path):
    import tomllib

    result = invoke(runner, tmp_path, "init")

    assert result.exit_code == 0
    config_path = tmp_path / ".workspaces.toml"
    assert config_path.exists()

    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    assert config["workspace_dir"] == "./.workspaces"
    assert len(config["repositories"]) == 2
    assert config["repositories"][0]["path"] == "./repo-frontend"
    assert config["repositories"][1]["path"] == "./repo-backend"


def test_init_refuses_overwrite_without_force(runner, tmp_path):
    config_path = tmp_path / ".workspaces.toml"
    config_path.write_text('workspace_dir = "./custom"\n')

    result = invoke(runner, tmp_path, "init")

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert config_path.read_text() == 'workspace_dir = "./custom"\n'


def test_init_force_overwrites_existing_config(runner, tmp_path):
    config_path = tmp_path / ".workspaces.toml"
    config_path.write_text('workspace_dir = "./custom"\n')

    result = invoke(runner, tmp_path, "init", "--force")

    assert result.exit_code == 0
    assert 'workspace_dir = "./.workspaces"' in config_path.read_text()


def test_create_links_worktrees_and_branches(runner, tmp_path, workspaces_config, source_repos):
    cwd = workspaces_config.parent
    result = invoke(runner, cwd, "create", "ticket-123")

    assert result.exit_code == 0
    assert "Creating multi-repo workspace for: ticket-123" in result.output
    assert "Workspace ticket-123 created." in result.output
    assert f"cd {tmp_path / 'workspaces' / 'ticket-123'}" in result.output

    for name, repo in source_repos.items():
        worktree = tmp_path / "workspaces" / "ticket-123" / name
        assert worktree.is_dir()
        assert run_git(repo, "worktree", "list") != ""
        assert branch_exists(repo, "ticket-123")
        assert (worktree / "README.md").exists()


def test_create_continues_when_one_repo_fails(runner, tmp_path, workspaces_config, source_repos):
    cwd = workspaces_config.parent
    run_git(source_repos["frontend"], "branch", "ticket-123")

    result = invoke(runner, cwd, "create", "ticket-123")

    assert result.exit_code == 0
    assert "Failed to create worktree for frontend" in result.output
    backend = tmp_path / "workspaces" / "ticket-123" / "backend"
    assert backend.is_dir()
    assert branch_exists(source_repos["backend"], "ticket-123")


def test_clean_removes_worktrees_and_ticket_root(runner, tmp_path, workspaces_config, source_repos):
    cwd = workspaces_config.parent
    invoke(runner, cwd, "create", "ticket-123")

    result = invoke(runner, cwd, "clean", "ticket-123")

    assert result.exit_code == 0
    assert "Removed worktree link for frontend" in result.output
    assert "Removed worktree link for backend" in result.output
    assert not (tmp_path / "workspaces" / "ticket-123").exists()
    for _, repo in source_repos.items():
        assert branch_exists(repo, "ticket-123")


def test_create_with_absolute_and_relative_paths(runner, tmp_path):
    base = tmp_path
    repo = base / "source" / "repo-app"
    repo.mkdir(parents=True)
    run_git(repo, "init", "-q", "-b", "main")
    run_git(repo, "config", "user.email", "test@example.com")
    run_git(repo, "config", "user.name", "Test")
    run_git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("# app\n")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-q", "-m", "initial commit")

    cwd = base / "cwd"
    cwd.mkdir()
    config = (
        'workspace_dir = "./out/workspaces"\n'
        "\n"
        "[[repositories]]\n"
        'name = "app"\n'
        'path = "../source/repo-app"\n'
    )
    (cwd / ".workspaces.toml").write_text(config)

    result = invoke(runner, cwd, "create", "ticket-456")

    assert result.exit_code == 0
    worktree = cwd / "out" / "workspaces" / "ticket-456" / "app"
    assert worktree.is_dir()
    assert branch_exists(repo, "ticket-456")
