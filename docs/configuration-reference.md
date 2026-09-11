# Configuration Reference

wtree is driven by a single `.workspaces.toml` file in the directory where you run the commands. This page documents its schema, path-resolution rules, and the setup-script environment.

## Schema

```toml
workspace_dir = "./.workspaces"

# Optional: run once per ticket after all worktrees are created (cwd = ticket dir).
setup_script = "./scripts/workspace-setup.sh"

[[repositories]]
name = "frontend"
path = "./repo-frontend"
setup_script = "./scripts/setup-dev.sh"   # optional, per-repo

[[repositories]]
name = "backend"
path = "./repo-backend"
```

### Top-level keys

| Key | Type | Required | Description |
| --- | --- | --- | --- |
| `workspace_dir` | string | no (default `"./.workspaces"`) | Root directory holding one subdirectory per ticket. |
| `setup_script` | string | no | A script run **once per ticket**, from the ticket root directory, after all worktrees are created. |
| `repositories` | array of tables | yes | One entry per repo to create a worktree for. |

### `[[repositories]]` keys

| Key | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | string | yes | Used as the worktree subdirectory name (`<workspace_dir>/<ticket>/<name>`) and as the label in logging. Should be unique across entries. |
| `path` | string | yes | Path to the source repository (the repo that owns the worktree). |
| `setup_script` | string | no | A script run **once per ticket** inside that repo's worktree. |

Unknown or missing keys in a repository entry are tolerated; `name` and `path` are required.

## Path resolution

Paths are resolved against the **current working directory** of the wtree process, unless they are absolute.

- `workspace_dir` — if relative, resolved against cwd; if absolute, used as-is.
- `repository.path` — relative to cwd, or absolute.
- top-level `setup_script` — relative paths resolve against the directory containing `.workspaces.toml` (i.e. cwd).
- per-repository `setup_script` — relative paths resolve against **that repo's worktree directory**, so a script committed to the repo works right after checkout without a path prefix.

The ticket directory is:

```text
<resolved workspace_dir>/<ticket-id>/<repo name>/
```

Example on-disk layout after `wtree create ticket-123`:

```text
.
├── .workspaces.toml
├── .workspaces/
│   └── ticket-123/
│       ├── frontend/      # git worktree on branch ticket-123
│       └── backend/       # git worktree on branch ticket-123
├── repo-frontend/
└── repo-backend/
```

## Setup scripts

Scripts are executed as subprocesses from the given working directory. A top-level script runs once with the **ticket root directory** as cwd; a per-repo script runs once inside that repo's **worktree**.

- Scripts must be executable (`chmod +x`). Any interpreter works via the shebang (shell, Python, etc.).
- Output streams directly to your terminal.
- A non-zero exit code is reported as a warning but **does not abort** `create`.
- A missing or non-executable script prints a warning and is skipped.
- Per-repo scripts run only for repos that were successfully linked in the current run.

### Environment variables

| Variable | Global | Per-repo | Meaning |
| --- | :-: | :-: | --- |
| `WTREE_TICKET_ID` | yes | yes | Ticket id being created. |
| `WTREE_TICKET_DIR` | yes | yes | Absolute ticket root directory. |
| `WTREE_ROOT_DIR` | yes | yes | Project root (cwd where wtree ran). |
| `WTREE_REPOS` | yes | | JSON array of `{name, worktree_dir, source_dir}` for every linked repo this run. |
| `WTREE_REPO_NAME` | | yes | Repository name. |
| `WTREE_WORKTREE_DIR` | | yes | Absolute worktree directory for this repo. |
| `WTREE_SOURCE_DIR` | | yes | Absolute source repository directory. |

## Example: workspace setup with env vars

`./scripts/workspace-setup.sh`:

```sh
#!/bin/sh
echo "Ticket: $WTREE_TICKET_ID"
echo "Repos:  $WTREE_REPOS"
```

Per-repo `./scripts/setup-dev.sh` (committed in the source repo):

```sh
#!/bin/sh
cd "$WTREE_WORKTREE_DIR"
python -m venv .venv
```

Because the per-repo path resolves against the worktree, running `wtree create` right after this script is committed to the repo works with no extra configuration.