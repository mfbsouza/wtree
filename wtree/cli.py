import json
from pathlib import Path

import click

from wtree import config, git, setup


def _config_error(message):
    click.secho(f"Error: {message}", fg="red", err=True)
    raise click.exceptions.Exit(1)


@click.group()
def cli():
    """Agile multi-repository git worktree manager."""


@cli.command()
@click.option("--force", is_flag=True, help="Overwrite an existing .workspaces.toml.")
def init(force):
    """Create a default .workspaces.toml in the current directory."""
    try:
        config_path = config.write_default(Path.cwd(), force=force)
    except config.ConfigError as e:
        _config_error(e)

    click.secho(f"Created {config.CONFIG_FILE} at {config_path}", fg="green")


@cli.command()
@click.argument("ticket_id")
def create(ticket_id):
    """Create a multi-repo worktree workspace."""
    try:
        cfg = config.load_config(Path.cwd())
    except config.ConfigError as e:
        _config_error(e)

    ticket_dir = cfg.ticket_dir(Path.cwd(), ticket_id)

    click.secho(f"Creating multi-repo workspace for: {ticket_id}", fg="cyan", bold=True)

    linked = []
    for repo in cfg.repositories:
        source_path = config.resolve_source_path(repo.path, Path.cwd())
        target_path = ticket_dir / repo.name

        if not source_path.exists():
            click.secho(
                f"Warning: Skipping [{repo.name}]: Source path missing at {source_path}",
                fg="yellow",
            )
            continue

        click.echo(f"Processing [{repo.name}]...")

        try:
            git.add_worktree(source_path, target_path, ticket_id)
        except git.GitError as e:
            click.secho(
                f"  Failed to create worktree for {repo.name}.\n  Reason: {e}",
                fg="red",
            )
            continue

        click.secho(f"  Worktree linked at: {target_path}", fg="green")
        linked.append((repo, source_path, target_path))

    if linked:
        _run_setup(cfg, Path.cwd(), ticket_id, ticket_dir, linked)

    click.echo(f"Workspace {ticket_id} created.")
    click.echo(f"cd {ticket_dir}")


def _run_setup(cfg, cwd, ticket_id, ticket_dir, linked):
    base_env = {
        "WTREE_TICKET_ID": ticket_id,
        "WTREE_TICKET_DIR": str(ticket_dir),
    }

    if cfg.setup_script:
        script_path = config.resolve_source_path(cfg.setup_script, cwd)
        click.echo("Running workspace setup script...")
        repos_json = json.dumps(
            [
                {
                    "name": repo.name,
                    "worktree_dir": str(target_path),
                    "source_dir": str(source_path),
                }
                for repo, source_path, target_path in linked
            ]
        )
        env = {**base_env, "WTREE_REPOS": repos_json}
        _report_setup("workspace", script_path, ticket_dir, env)

    for repo, source_path, target_path in linked:
        if not repo.setup_script:
            continue
        script_path = config.resolve_source_path(repo.setup_script, target_path)
        click.echo(f"Running setup script for [{repo.name}]...")
        env = {
            **base_env,
            "WTREE_REPO_NAME": repo.name,
            "WTREE_WORKTREE_DIR": str(target_path),
            "WTREE_SOURCE_DIR": str(source_path),
        }
        _report_setup(f"[{repo.name}]", script_path, target_path, env)


def _report_setup(label, script_path, cwd, env):
    try:
        returncode = setup.run_script(script_path, cwd, env)
    except setup.SetupError as e:
        click.secho(f"  Setup script failed for {label}.\n  Reason: {e}", fg="red")
        return

    if returncode != 0:
        click.secho(
            f"  Setup script failed for {label} (exit code {returncode}).",
            fg="red",
        )
        return

    click.secho(f"  Setup complete for {label}.", fg="green")


@cli.command()
@click.argument("ticket_id")
def clean(ticket_id):
    """Remove a multi-repo worktree workspace safely."""
    try:
        cfg = config.load_config(Path.cwd())
    except config.ConfigError as e:
        _config_error(e)

    ticket_dir = cfg.ticket_dir(Path.cwd(), ticket_id)

    click.secho(f"Cleaning up workspace branches for: {ticket_id}", fg="yellow", bold=True)

    for repo in cfg.repositories:
        source_path = config.resolve_source_path(repo.path, Path.cwd())
        target_path = ticket_dir / repo.name

        if not target_path.exists():
            click.secho(f"  No worktree found for {repo.name}", fg="yellow")
            continue

        try:
            git.remove_worktree(source_path, target_path)
        except git.GitError:
            click.secho(
                f"  Could not remove worktree for {repo.name}. Uncommitted changes may exist.",
                fg="red",
            )
            continue

        click.secho(f"  Removed worktree link for {repo.name}", fg="green")

    if ticket_dir.exists() and not any(ticket_dir.iterdir()):
        ticket_dir.rmdir()
        click.echo("Removed empty ticket workspace root directory.")
