from pathlib import Path

import pytest

from wtree import config


def test_from_dict_parses_repositories():
    cfg = config.WorkspaceConfig.from_dict(
        {
            "workspace_dir": "./.workspaces",
            "repositories": [
                {"name": "frontend", "path": "./repo-frontend"},
                {"name": "backend", "path": "./repo-backend"},
            ],
        }
    )

    assert cfg.workspace_dir == Path("./.workspaces")
    assert [r.name for r in cfg.repositories] == ["frontend", "backend"]
    assert cfg.repositories[0].path == "./repo-frontend"


def test_from_dict_defaults_missing_fields():
    cfg = config.WorkspaceConfig.from_dict({})

    assert cfg.workspace_dir == Path("./.workspaces")
    assert cfg.repositories == []
    assert cfg.setup_script is None


def test_from_dict_parses_setup_scripts():
    cfg = config.WorkspaceConfig.from_dict(
        {
            "workspace_dir": "./.workspaces",
            "setup_script": "./scripts/workspace-setup.sh",
            "repositories": [
                {"name": "frontend", "path": "./repo-frontend", "setup_script": "setup-dev.sh"},
                {"name": "backend", "path": "./repo-backend"},
            ],
        }
    )

    assert cfg.setup_script == "./scripts/workspace-setup.sh"
    assert cfg.repositories[0].setup_script == "setup-dev.sh"
    assert cfg.repositories[1].setup_script is None


def test_load_config_missing_file_raises(tmp_path):
    with pytest.raises(config.ConfigError, match="Config file not found"):
        config.load_config(tmp_path)


def test_load_config_parses_file(tmp_path):
    (tmp_path / config.CONFIG_FILE).write_text(
        'workspace_dir = "./ws"\n[[repositories]]\nname = "app"\npath = "./repo-app"\n'
    )

    cfg = config.load_config(tmp_path)

    assert cfg.workspace_dir == Path("./ws")
    assert len(cfg.repositories) == 1


def test_load_config_parses_setup_script(tmp_path):
    (tmp_path / config.CONFIG_FILE).write_text(
        'workspace_dir = "./ws"\n'
        'setup_script = "./scripts/ws.sh"\n'
        "[[repositories]]\n"
        'name = "app"\n'
        'path = "./repo-app"\n'
        'setup_script = "scripts/app.sh"\n'
    )

    cfg = config.load_config(tmp_path)

    assert cfg.setup_script == "./scripts/ws.sh"
    assert cfg.repositories[0].setup_script == "scripts/app.sh"


def test_ticket_dir_relative_to_cwd(tmp_path):
    cfg = config.WorkspaceConfig.from_dict({"workspace_dir": "./out"})

    assert cfg.ticket_dir(tmp_path, "ticket-1") == (tmp_path / "out" / "ticket-1").resolve()


def test_ticket_dir_absolute_workspace(tmp_path):
    cfg = config.WorkspaceConfig.from_dict({"workspace_dir": str(tmp_path / "abs")})

    assert (
        cfg.ticket_dir(tmp_path / "other", "ticket-1") == (tmp_path / "abs" / "ticket-1").resolve()
    )


def test_resolve_source_path_absolute_and_relative(tmp_path):
    repo = tmp_path / "repo"
    assert config.resolve_source_path("../repo", tmp_path) == (tmp_path / "../repo").resolve()
    assert config.resolve_source_path(str(repo), tmp_path) == repo.resolve()


def test_write_default_creates_file(tmp_path):
    path = config.write_default(tmp_path)

    assert path == tmp_path / config.CONFIG_FILE
    assert path.exists()
    assert 'workspace_dir = "./.workspaces"' in path.read_text()


def test_write_default_refuses_overwrite(tmp_path):
    config.write_default(tmp_path)

    with pytest.raises(config.ConfigError, match="already exists"):
        config.write_default(tmp_path)


def test_write_default_force_overwrites(tmp_path):
    config.write_default(tmp_path)
    path = config.write_default(tmp_path, force=True)

    assert path.exists()
