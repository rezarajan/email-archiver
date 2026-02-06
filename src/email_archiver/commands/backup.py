"""Backup command: invoke the configured backup tool."""

from __future__ import annotations

import shlex

from email_archiver.config import Config
from email_archiver.runner import RunResult, run_command


def run_backup(
    config: Config,
    *,
    verbose: bool = False,
    dry_run: bool = False,
) -> RunResult:
    """Run the configured backup command.

    Args:
        config: Validated configuration.
        verbose: Print verbose output.
        dry_run: If True, only print what would be run.

    Returns:
        RunResult from the backup execution.
    """
    assert config.backup is not None

    if not config.backup.command:
        print("No backup command configured. Skipping backup.")
        return RunResult(
            command=["(none)"],
            exit_code=0,
            stdout="",
            stderr="No backup command configured",
            duration_seconds=0.0,
        )

    cmd = shlex.split(config.backup.command)

    if dry_run:
        print(f"[dry-run] Would execute: {' '.join(cmd)}")
        return RunResult(
            command=cmd, exit_code=0, stdout="", stderr="", duration_seconds=0.0
        )

    print(f"Running backup: {' '.join(cmd)}")
    result = run_command(cmd, stream=verbose)

    if result.ok:
        print(f"Backup completed successfully ({result.duration_seconds:.1f}s)")
    else:
        print(f"Backup failed (exit {result.exit_code})")
        if result.stderr:
            print(f"stderr: {result.stderr[:500]}")

    return result
