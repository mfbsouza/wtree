import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_FILE = ".workspaces.toml"

DEFAULT_CONFIG = """\
# Root directory for all ticket workspaces.
workspace_dir = "./.workspaces"

# Add one [[repositories]] block per repo you want a worktree for.
[[repositories]]
name = "frontend"
path = "./repo-frontend"

[[repositories]]
name = "backend"
path = "./repo-backend"
"""


class ConfigError(Exception):
    """Raised when the workspace config cannot be loaded or written."""


@dataclass(frozen=True)
class Repository:
    name: str
    path: str


@dataclass(frozen=True)
class WorkspaceConfig:
    workspace_dir: Path
    repositories: list[Repository]

    @classmethod
    def from_dict(cls, data):
        workspace_dir = Path(data.get("workspace_dir", "./.workspaces"))
        repositories = [
            Repository(name=repo["name"], path=repo["path"])
            for repo in data.get("repositories", [])
        ]
        return cls(workspace_dir=workspace_dir, repositories=repositories)

    def ticket_dir(self, cwd: Path, ticket_id: str) -> Path:
        if self.workspace_dir.is_absolute():
            base = self.workspace_dir
        else:
            base = cwd / self.workspace_dir
        return (base / ticket_id).resolve()


def load_config(cwd: Path) -> WorkspaceConfig:
    config_path = cwd / CONFIG_FILE
    if not config_path.exists():
        raise ConfigError(f"Config file not found at {config_path}")

    with open(config_path, "rb") as f:
        return WorkspaceConfig.from_dict(tomllib.load(f))


def resolve_source_path(repo_path: str, cwd: Path) -> Path:
    path = Path(repo_path)
    if path.is_absolute():
        return Path(path).resolve()
    return (cwd / path).resolve()


def write_default(cwd: Path, force: bool = False) -> Path:
    config_path = cwd / CONFIG_FILE
    if config_path.exists() and not force:
        raise ConfigError(
            f"{CONFIG_FILE} already exists at {config_path}. Use --force to overwrite."
        )

    config_path.write_text(DEFAULT_CONFIG)
    return config_path
