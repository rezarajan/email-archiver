"""Sync command: run mbsync to synchronize IMAP → Maildir."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from email_archiver.config import Config, ProgressBackend
from email_archiver.generate import write_generated_configs
from email_archiver.parsers import MbsyncParser
from email_archiver.progress import ProgressCallback, ProgressPhase, ProgressReporter
from email_archiver.runner import RunResult, run_command
from email_archiver.terminal_ui import (
    FileProgressCallback,
    PrometheusProgressCallback,
    TerminalProgressUI,
)


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
    mbsyncrc_path: Path | None = None,
) -> RunResult:
    """Run mbsync for configured accounts/channels.

    Args:
        config: Validated configuration.
        account: Optional account name filter.
        verbose: Print verbose output.
        dry_run: If True, only print what would be run.
        mbsyncrc_path: Path to generated mbsyncrc (generated if not provided).

    Returns:
        RunResult from mbsync execution.
    """
    if mbsyncrc_path is None:
        mbsyncrc_path, _ = write_generated_configs(config)

    # Determine which group to sync
    target_account = account or next(iter(config.accounts))
    cmd = ["mbsync", "-c", str(mbsyncrc_path)]
    if verbose:
        cmd.append("-V")
    cmd.append(target_account)

    if dry_run:
        print(f"[dry-run] Would execute: {' '.join(cmd)}")
        return RunResult(command=cmd, exit_code=0, stdout="", stderr="", duration_seconds=0.0)

    # Set up progress reporting
    reporter = ProgressReporter()
    assert config.orchestration is not None
    backend = config.orchestration.progress_backend

    # Create appropriate progress callback based on config
    callback: ProgressCallback
    if backend == ProgressBackend.FILE:
        assert config.orchestration.progress_file is not None
        callback = FileProgressCallback(config.orchestration.progress_file)
    elif backend == ProgressBackend.PROM:
        callback = PrometheusProgressCallback()
    else:  # STDOUT (default)
        callback = TerminalProgressUI(enabled=verbose)

    reporter.subscribe(callback)

    # Report start
    reporter.report(
        ProgressPhase.STARTING, f"Starting sync for {target_account}", account=target_account
    )

    # Parse mbsync output for progress tracking
    parser = MbsyncParser(reporter, target_account)

    # Use context manager only for TerminalProgressUI
    if isinstance(callback, TerminalProgressUI):
        with callback.activate():
            result = run_command(
                cmd,
                stream=verbose,
                progress_reporter=reporter,
                line_parser=parser.parse_line,
            )
    else:
        result = run_command(
            cmd,
            stream=verbose,
            progress_reporter=reporter,
            line_parser=parser.parse_line,
        )

    # Write log
    acct_name = account or "default"
    log_path = _write_log(config, result, acct_name)
    if verbose:
        print(f"Log written to {log_path}")

    if result.ok:
        reporter.report(
            ProgressPhase.COMPLETED,
            f"Sync completed ({result.duration_seconds:.1f}s)",
            account=target_account,
        )
        if not verbose:  # Only print summary if not showing progress
            print(f"Sync completed successfully ({result.duration_seconds:.1f}s)")
    else:
        reporter.report(
            ProgressPhase.FAILED, f"Sync failed (exit {result.exit_code})", account=target_account
        )
        print(f"Sync failed (exit {result.exit_code})")
        if result.stderr:
            print(f"stderr: {result.stderr[:500]}")

    # Close file callback after all events have been emitted
    if isinstance(callback, FileProgressCallback):
        callback.close()

    return result
