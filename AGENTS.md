# wtree — Agent Notes

wtree (short for **worktree**) is a configuration-driven CLI that manages git worktrees across a multi-repo project. Given a `.workspaces.toml`, it creates or removes a worktree for a ticket in every repository.

## Stack

- Python >=3.11, Click, built-in `tomllib` (no toml fallback needed)
- Packaging: setuptools via `pyproject.toml`; version is dynamic from `wtree.__version__`
- Tests: pytest
- Lint/format: ruff (via pre-commit hooks)
- Version bumps: bump-my-version (commits + tags `vX.Y.Z`)

## Commands

- Install editable (with dev deps): `pip install -e ".[dev]"`
- Run tests: `pytest`
- Lint: `ruff check .`
- Format: `ruff format .`
- pre-commit (installed at `git init` time): `pre-commit run --all-files`
- Bump version: `bump-my-version bump patch|minor|major`
- CLI entry point: `wtree = wtree.main:cli`

## CI and releases

- `.github/workflows/ci.yml` — job `ci` (lint + format + tests) runs on push/PR; `main` branch protection requires it to pass.
- `.github/workflows/version-bump.yml` — triggered only by a `pull_request` `closed` event on `main` where the PR was merged (direct pushes to `main` do NOT trigger it); runs `bump-my-version bump patch`, pushes the commit + `vX.Y.Z` tag directly to `main` using the `VERSION_BUMP_PAT` secret, and creates a GitHub release.
- The bump workflow's job is guarded by `github.event.pull_request.merged == true` and skips PRs whose title starts with `Bump version:` (defense-in-depth against a bump commit going through a PR; the workflow's own direct push does not re-trigger it).
- Bump level is label-driven: a PR labeled `major` bumps major, labeled `feature` bumps minor, otherwise patch (a missing label safely defaults to patch; `major` wins if both). The repo must have `feature` and `major` labels; apply them to the PR before merging.
- `tag_name = "v{new_version}"` in `pyproject.toml` — at tag time `{current_version}` resolves to the *pre-bump* version, so it must NOT be used for the tag; `{new_version}` is the bumped one.
- Branch protection on `main`: require PR + 1 approval + status checks; admin bypass is intentionally left on so the PAT push works.
- Setup requires a fine-grained PAT (Contents: read/write on this repo) stored as the `VERSION_BUMP_PAT` Actions secret.
- Local `bump-my-version` runs need `git config commit.gpgsign false` and `git config tag.gpgsign false` (headless gpg can't sign; the workflow already sets these).

## Project layout

- `wtree/cli.py` — click group and commands (`init`, `create`, `clean`)
- `wtree/config.py` — config loading/writing, dataclasses, path resolution
- `wtree/git.py` — git worktree subprocess wrappers (raise `GitError`)
- `wtree/main.py` — entry shim re-exporting the `cli` group
- `.workspaces.toml` — runtime config: `workspace_dir` + `[[repositories]]` entries with `name` and `path`
- `tests/test_wtree.py` — acceptance tests; `tests/test_config.py` — config unit tests
- `wtree/__init__.py` — single source of truth for `__version__`

## Conventions and behaviors

- Branch name is always the plain `<ticket-id>` — no `feature/` prefix.
- `init` writes a default `.workspaces.toml`; it refuses to overwrite an existing one unless `--force` is passed.
- The default `workspace_dir` is the hidden `./.workspaces`; the generated template references repos at the root of the working dir (`./repo-*`).
- Config paths are resolved against the current working directory; absolute paths are also accepted.
- Missing `.workspaces.toml` must print an error to stderr and exit with code 1.
- `git worktree add <target> -b <ticket-id>` is run with `cwd` set to the source repo dir.
- Per-repo failures (e.g. existing branch) must be reported but must NOT abort the remaining repos.
- `create` ends by printing `Workspace <ticket-id> created.` followed by a copy-paste `cd <ticket-dir>` hint.
- `clean` runs `git worktree remove <target>` per repo, then removes the ticket root dir only if empty. With `--force`, removes dirty worktrees (`--force`), deletes ticket branches (`git branch -D`), and removes the ticket dir even if non-empty (`shutil.rmtree`).
- Setup scripts (`setup_script` in config) run once per `create`, after the worktree loop: the top-level script in the ticket root dir, and each repo's script in its worktree (only for repos linked in this run). Scripts are any executable with a shebang; relative per-repo paths resolve against the worktree dir, global paths against cwd. Failures warn but do not abort (`wtree/setup.py`).
- Test fixtures must set `git config commit.gpgsign false` — commits fail in headless environments when signing is enabled globally.
- When adding or changing commands, flags, or env variables, update AGENTS.md and README.md to reflect the new behavior.
