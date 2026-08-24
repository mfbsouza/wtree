import subprocess
from pathlib import Path


class GitError(Exception):
    """Raised when a git command exits with a non-zero status."""


def _run(source: Path, *args) -> str:
    result = subprocess.run(["git", *args], cwd=source, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitError(result.stderr.strip())
    return result.stdout.strip()


def _try_run(source: Path, *args) -> str | None:
    result = subprocess.run(["git", *args], cwd=source, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def add_worktree(source: Path, target: Path, branch: str, start_point: str | None = None) -> None:
    args = ["worktree", "add", str(target), "-b", branch]
    if start_point:
        args.append(start_point)
    _run(source, *args)


def remove_worktree(source: Path, target: Path, force: bool = False) -> None:
    args = ["worktree", "remove"]
    if force:
        args.append("--force")
    args.append(str(target))
    _run(source, *args)


def delete_branch(source: Path, branch: str) -> None:
    _run(source, "branch", "-D", branch)


def _ref_exists(source: Path, ref: str) -> bool:
    return _try_run(source, "show-ref", "--verify", "--quiet", ref) is not None


def _first_remote(source: Path) -> str | None:
    out = _try_run(source, "remote")
    if not out:
        return None
    remotes = out.splitlines()
    if "origin" in remotes:
        return "origin"
    return remotes[0]


def latest_start_point(source: Path) -> str:
    """Detect the repo's default branch and return it freshly fetched.

    Resolution order: the remote's HEAD (e.g. origin/main), then main/master
    on the remote, then local main/master when no remote exists.
    """
    remote = _first_remote(source)
    if remote is None:
        for branch in ("main", "master"):
            if _ref_exists(source, f"refs/heads/{branch}"):
                return branch
        raise GitError("Could not detect a main or master branch")

    symref = _try_run(source, "symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD")
    candidates = []
    if symref and symref.startswith(f"{remote}/"):
        candidates.append(symref[len(remote) + 1 :])
    candidates.extend(b for b in ("main", "master") if b not in candidates)

    last_error = ""
    for branch in candidates:
        try:
            _run(source, "fetch", "--quiet", remote, branch)
        except GitError as e:
            last_error = str(e)
            continue
        if _ref_exists(source, f"refs/remotes/{remote}/{branch}"):
            return f"{remote}/{branch}"
    detail = f": {last_error}" if last_error else ""
    raise GitError(f"Could not fetch a main or master branch from '{remote}'{detail}")
