"""Index command: run notmuch new to index the Maildir."""

from __future__ import annotations

import os
from pathlib import Path

from email_archiver.config import Config, ProgressBackend
from email_archiver.generate import ensure_notmuch_init, write_generated_configs
from email_archiver.parsers import NotmuchParser
from email_archiver.progress import ProgressCallback, ProgressPhase, ProgressReporter
from email_archiver.runner import RunResult, run_command
from email_archiver.terminal_ui import (
    FileProgressCallback,
    PrometheusProgressCallback,
    TerminalProgressUI,
)


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
    reporter.report(ProgressPhase.STARTING, "Starting indexing")

    # Parse notmuch output for progress tracking
    parser = NotmuchParser(reporter)

    # Use context manager only for TerminalProgressUI
    if isinstance(callback, TerminalProgressUI):
        with callback.activate():
            result = run_command(
                cmd,
                env=env,
                stream=verbose,
                progress_reporter=reporter,
                line_parser=parser.parse_line,
            )
    else:
        result = run_command(
            cmd,
            env=env,
            stream=verbose,
            progress_reporter=reporter,
            line_parser=parser.parse_line,
        )
        # Close file callback if needed
        if isinstance(callback, FileProgressCallback):
            callback.close()

    if result.ok:
        if not verbose:  # Only print summary if not showing progress
            print(f"Index completed successfully ({result.duration_seconds:.1f}s)")
            if result.stdout.strip():
                print(f"  {result.stdout.strip()}")
    else:
        reporter.report(ProgressPhase.FAILED, f"Index failed (exit {result.exit_code})")
        print(f"Index failed (exit {result.exit_code})")
        if result.stderr:
            print(f"stderr: {result.stderr[:500]}")

    return result
