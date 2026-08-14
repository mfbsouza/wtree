# wtree

wtree stands for **worktree**. It is a CLI tool developed to help manage git worktrees across a multi-repo project.

## What it does

Given a `.workspaces.toml` config that lists your repositories, `wtree` creates (or cleans up) a git worktree for a ticket in every repo, so you can open one IDE window and work on the same feature across all repositories.

## Configuration

Create a `.workspaces.toml` in the directory where you run `wtree`:

```toml
workspace_dir = "./.workspaces"

[[repositories]]
name = "frontend"
path = "./repo-frontend"

[[repositories]]
name = "backend"
path = "./repo-backend"
```

## Usage

```sh
# generate a starter .workspaces.toml in the current directory
wtree init

# create a branch + worktree for the ticket in every repo (prints a cd hint)
wtree create <ticket-id>

# remove the worktrees and clean up the workspace
wtree clean <ticket-id>
```

After `wtree create ticket-123`, the directory looks like this:

```text
.
├── .workspaces.toml
├── .workspaces/                  # workspace_dir = "./.workspaces"
│   └── ticket-123/               # one directory per ticket
│       ├── frontend/             # worktree on branch ticket-123
│       └── backend/              # worktree on branch ticket-123
├── repo-frontend/                # main repo (main/master or bare)
└── repo-backend/                 # main repo (main/master or bare)
```

## Setup scripts

`wtree` can run scripts to automate per-ticket setup (installing dependencies,
creating env files, etc.) each time you `create` a workspace.

- A top-level `setup_script` runs **once** per ticket, with the ticket
  directory as the working directory (it can see every worktree).
- A per-repository `setup_script` runs once in that repository's worktree
  directory.

```toml
workspace_dir = "./.workspaces"

# Runs once per ticket, from the ticket root directory.
setup_script = "./scripts/workspace-setup.sh"

[[repositories]]
name = "frontend"
path = "./repo-frontend"
setup_script = "./scripts/setup-dev.sh"   # runs in frontend's worktree

[[repositories]]
name = "backend"
path = "./repo-backend"
```

- Paths: relative top-level `setup_script` paths resolve against the directory
  with `.workspaces.toml`; per-repository paths resolve against that repo's
  worktree, so a script committed to the repo works right after checkout.
- Scripts must be executable (`chmod +x`). Any language works — the shebang
  decides (shell, Python, etc.). Output streams to your terminal.
- A non-zero exit is reported as a warning but does not abort `create`.
- Scripts receive context via environment variables:

| Variable            | Global | Per-repo | Meaning                          |
| ------------------- | :----: | :------: | -------------------------------- |
| `WTREE_TICKET_ID`   |  yes   |   yes    | Ticket id being created          |
| `WTREE_TICKET_DIR`  |  yes   |   yes    | Ticket root directory            |
| `WTREE_REPOS`       |  yes   |          | JSON list of created worktrees   |
| `WTREE_REPO_NAME`   |        |   yes    | Repository name                  |
| `WTREE_WORKTREE_DIR`|        |   yes    | Repository's worktree directory  |
| `WTREE_SOURCE_DIR`  |        |   yes    | Source repository directory      |

## Install

You can install `wtree` with `pipx`, `pip`, or `uv`. Each supports installing from a specific release tag, the latest `main` branch, or a local clone.

### pipx

```sh
# specific release tag
pipx install "git+https://github.com/mfbsouza/wtree.git@v0.1.0"

# latest main branch
pipx install "git+https://github.com/mfbsouza/wtree.git"

# local clone
pipx install --editable /path/to/wtree
```

### pip

```sh
# specific release tag
pip install "git+https://github.com/mfbsouza/wtree.git@v0.1.0"

# latest main branch
pip install "git+https://github.com/mfbsouza/wtree.git"

# local clone
pip install -e /path/to/wtree
```

### uv

```sh
# specific release tag
uv tool install "git+https://github.com/mfbsouza/wtree.git@v0.1.0"

# latest main branch
uv tool install "git+https://github.com/mfbsouza/wtree.git"

# local clone
uv tool install --editable /path/to/wtree
```

## Disclaimer

This project was developed with the assistance of AI tools. It is provided as-is, without warranty of any kind. Licensed under the MIT License.
