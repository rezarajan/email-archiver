"""Sync command: run mbsync to synchronize IMAP → Maildir."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from email_archiver.config import Config
from email_archiver.runner import RunResult, run_command


def _write_log(config: Config, result: RunResult, account: str) -> Path:
    """Write a sync run log to the logs directory."""
    assert config.paths is not None
    log_dir = config.paths.logs_dir / account
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"sync-{ts}.log"
    log_path.write_text(
        f"command: {' '.join(result.command)}\n"
        f"exit_code: {result.exit_code}\n"
        f"duration: {result.duration_seconds:.1f}s\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}\n",
        encoding="utf-8",
    )
    return log_path


def run_sync(
    config: Config,
    *,
    account: str | None = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> RunResult:
    """Run mbsync for configured accounts/channels.

    Args:
        config: Validated configuration.
        account: Optional account name filter.
        verbose: Print verbose output.
        dry_run: If True, only print what would be run.

    Returns:
        RunResult from mbsync execution.
    """
    assert config.mbsync is not None

    cmd = ["mbsync", "-c", str(config.mbsync.config_path)]
    if verbose:
        cmd.append("-V")

    # Use the configured group or fall back to -a (all)
    if config.mbsync.group:
        cmd.append(config.mbsync.group)
    else:
        cmd.append("-a")

    if dry_run:
        print(f"[dry-run] Would execute: {' '.join(cmd)}")
        return RunResult(
            command=cmd, exit_code=0, stdout="", stderr="", duration_seconds=0.0
        )

    print(f"Running: {' '.join(cmd)}")
    result = run_command(cmd, stream=verbose)

    # Write log
    acct_name = account or "default"
    log_path = _write_log(config, result, acct_name)
    if verbose:
        print(f"Log written to {log_path}")

    if result.ok:
        print(f"Sync completed successfully ({result.duration_seconds:.1f}s)")
    else:
        print(f"Sync failed (exit {result.exit_code})")
        if result.stderr:
            print(f"stderr: {result.stderr[:500]}")

    return result
