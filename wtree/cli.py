import asyncio
import json
import shutil
from pathlib import Path

import click

from wtree import config, git, setup


def _config_error(message):
    click.secho(f"Error: {message}", fg="red", err=True)
    raise click.exceptions.Exit(1)


async def _create_async(ticket_id, latest):
    """Async implementation of the create command with concurrent repo processing."""
    try:
        cfg = config.load_config(Path.cwd())
    except config.ConfigError as e:
        _config_error(e)

    ticket_dir = cfg.ticket_dir(Path.cwd(), ticket_id)

    click.secho(f"Creating multi-repo workspace for: {ticket_id}", fg="cyan", bold=True)

    async def process_repo(repo):
        source_path = config.resolve_source_path(repo.path, Path.cwd())
        target_path = ticket_dir / repo.name

        if not source_path.exists():
            click.secho(
                f"Warning: Skipping [{repo.name}]: Source path missing at {source_path}",
                fg="yellow",
            )
            return None

        click.echo(f"Processing [{repo.name}]...")

        start_point = None
        if latest:
            try:
                start_point = await git.a_latest_start_point(source_path)
                click.secho(f"  Based on latest {start_point}.", fg="green")
            except git.GitError as e:
                click.secho(
                    f"  Warning: Could not base {repo.name} on its latest default branch.\n"
                    f"  Reason: {e}\n"
                    "  Falling back to current HEAD.",
                    fg="yellow",
                )

        try:
            await git.a_add_worktree(source_path, target_path, ticket_id, start_point)
        except git.GitError as e:
            click.secho(
                f"  Failed to create worktree for {repo.name}.\n  Reason: {e}",
                fg="red",
            )
            return None

        click.secho(f"  Worktree linked at: {target_path}", fg="green")
        return (repo, source_path, target_path)

    tasks = [process_repo(repo) for repo in cfg.repositories]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    linked = []
    for repo, result in zip(cfg.repositories, results, strict=True):
        if isinstance(result, Exception):
            click.secho(
                f"  Failed to create worktree for {repo.name}.\n  Reason: {result}",
                fg="red",
            )
        elif result is not None:
            linked.append(result)

    if linked:
        _run_setup(cfg, Path.cwd(), ticket_id, ticket_dir, linked)

    click.echo(f"Workspace {ticket_id} created.")
    click.echo(f"cd {ticket_dir}")


@click.group()
@click.version_option(package_name="wtree")
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
@click.option(
    "--latest",
    is_flag=True,
    help="Base each new branch on the latest main/master (fetches first).",
)
def create(ticket_id, latest):
    """Create a multi-repo worktree workspace."""
    asyncio.run(_create_async(ticket_id, latest))


def _run_setup(cfg, cwd, ticket_id, ticket_dir, linked):
    base_env = {
        "WTREE_TICKET_ID": ticket_id,
        "WTREE_TICKET_DIR": str(ticket_dir),
        "WTREE_ROOT_DIR": str(cwd),
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
@click.option(
    "--force",
    is_flag=True,
    help="Force removal: delete branches and remove workdir even if dirty or non-empty.",
)
def clean(ticket_id, force):
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
            git.remove_worktree(source_path, target_path, force=force)
        except git.GitError:
            click.secho(
                f"  Could not remove worktree for {repo.name}. Uncommitted changes may exist.",
                fg="red",
            )
            continue

        click.secho(f"  Removed worktree link for {repo.name}", fg="green")

        if force:
            try:
                git.delete_branch(source_path, ticket_id)
                click.secho(f"  Deleted branch {ticket_id} for {repo.name}", fg="green")
            except git.GitError:
                click.secho(
                    f"  Could not delete branch {ticket_id} for {repo.name}.",
                    fg="red",
                )

    if force and ticket_dir.exists():
        shutil.rmtree(ticket_dir)
        click.echo("Removed ticket workspace directory.")
    elif ticket_dir.exists() and not any(ticket_dir.iterdir()):
        ticket_dir.rmdir()
        click.echo("Removed empty ticket workspace root directory.")
