import subprocess
from pathlib import Path


class GitError(Exception):
    """Raised when a git command exits with a non-zero status."""


def _run(source: Path, *args) -> str:
    result = subprocess.run(["git", *args], cwd=source, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitError(result.stderr.strip())
    return result.stdout.strip()


def add_worktree(source: Path, target: Path, branch: str) -> None:
    _run(source, "worktree", "add", str(target), "-b", branch)


def remove_worktree(source: Path, target: Path, force: bool = False) -> None:
    args = ["worktree", "remove"]
    if force:
        args.append("--force")
    args.append(str(target))
    _run(source, *args)


def delete_branch(source: Path, branch: str) -> None:
    _run(source, "branch", "-D", branch)
