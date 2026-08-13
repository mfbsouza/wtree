from pathlib import Path

import click

from wtree import config, git


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

    click.echo(f"Workspace {ticket_id} created.")
    click.echo(f"cd {ticket_dir}")


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
