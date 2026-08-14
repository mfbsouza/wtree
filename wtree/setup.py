import os
import subprocess
from pathlib import Path


class SetupError(Exception):
    """Raised when a setup script cannot be executed."""


def run_script(path: Path, cwd: Path, env: dict[str, str] | None = None) -> int:
    """Run an executable setup script, streaming its output to the terminal.

    Returns the script's exit code. Raises SetupError if the script cannot be
    executed (e.g. it is missing or not executable).
    """
    if not path.exists():
        raise SetupError(f"Setup script not found at {path}")

    try:
        result = subprocess.run([str(path)], cwd=cwd, env=dict(os.environ, **(env or {})))
    except PermissionError:
        raise SetupError(
            f"Setup script is not executable: {path} (run `chmod +x {path}`)"
        ) from None

    return result.returncode
