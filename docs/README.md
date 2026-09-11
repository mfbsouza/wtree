# wtree Documentation

wtree (**worktree**) is a configuration-driven CLI that manages git worktrees across a multi-repo project. Given a `.workspaces.toml`, it creates (or removes) a worktree for a ticket in every repository.

This directory contains documentation for **developers and contributors**. For installation and end-user usage, see the [main README](../README.md).

## Table of contents

| Document | Purpose |
| --- | --- |
| [Architecture](./architecture.md) | How the project is structured, module responsibilities, data flow, and the async concurrency model. |
| [CLI Reference](./cli-reference.md) | Every command, option, exit code, and the decision logic behind `--latest` and `clean`. |
| [Configuration Reference](./configuration-reference.md) | The `.workspaces.toml` schema, path-resolution rules, and setup script environment. |
| [Contributing](./contributing.md) | Development setup, tooling, conventions, and how to open a change. |
| [Testing](./testing.md) | What the test suite covers, its fixtures, and how to add new tests. |
| [Releasing](./releasing.md) | The automated version-bump and GitHub release pipeline. |

## Quick facts

- **Language/runtime:** Python >= 3.11
- **CLI framework:** Click
- **Config parsing:** built-in `tomllib` (no third-party TOML dependency)
- **Git interaction:** shelled-out `git` subprocesses (sync and async variants), never a git library
- **Concurrency:** `create` processes repos concurrently with `asyncio.gather`
- **Packaging:** setuptools (version is dynamic from `wtree.__version__`)