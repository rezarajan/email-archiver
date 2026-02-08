"""Index command: run notmuch new to index the Maildir."""

from __future__ import annotations

import os
from pathlib import Path

from email_archiver.config import Config
from email_archiver.generate import ensure_notmuch_init, write_generated_configs
from email_archiver.runner import RunResult, run_command


def run_index(
    config: Config,
    *,
    verbose: bool = False,
    dry_run: bool = False,
    notmuch_config_path: Path | None = None,
) -> RunResult:
    """Run notmuch new to index the local Maildir.

    Args:
        config: Validated configuration.
        verbose: Print verbose output.
        dry_run: If True, only print what would be run.
        notmuch_config_path: Path to generated notmuch config (generated if not provided).

    Returns:
        RunResult from notmuch execution.
    """
    if notmuch_config_path is None:
        _, notmuch_config_path = write_generated_configs(config)

    env = {**os.environ, "NOTMUCH_CONFIG": str(notmuch_config_path)}
    cmd = ["notmuch", "new"]

    if dry_run:
        print(f"[dry-run] Would execute: {' '.join(cmd)}")
        return RunResult(command=cmd, exit_code=0, stdout="", stderr="", duration_seconds=0.0)

    # Auto-initialize notmuch database if needed
    ensure_notmuch_init(config, notmuch_config_path)

    print(f"Running: {' '.join(cmd)}")
    result = run_command(cmd, env=env, stream=verbose)

    if result.ok:
        print(f"Index completed successfully ({result.duration_seconds:.1f}s)")
        if result.stdout.strip():
            print(f"  {result.stdout.strip()}")
    else:
        print(f"Index failed (exit {result.exit_code})")
        if result.stderr:
            print(f"stderr: {result.stderr[:500]}")

    return result
