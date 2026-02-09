"""Terminal UI for progress reporting using rich library."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from email_archiver.progress import ProgressCallback, ProgressEvent, ProgressPhase


class TerminalProgressUI(ProgressCallback):
    """Terminal UI that renders progress bars using rich.

    Features:
    - Progress bars for operations with known total (e.g. syncing N messages)
    - Spinners for operations without known total (e.g. indexing)
    - Status messages and elapsed time
    - Multiple concurrent progress bars (future: parallel accounts)
    """

    def __init__(self, *, enabled: bool = True) -> None:
        """Initialize terminal UI.

        Args:
            enabled: If False, progress bars are disabled (for non-verbose mode).
        """
        self.enabled = enabled
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=self.console,
        )
        self._live: Live | None = None
        self._tasks: dict[str, TaskID] = {}  # phase -> task_id

    @contextmanager
    def activate(self) -> Generator[TerminalProgressUI, None, None]:
        """Context manager to activate the live progress display."""
        if not self.enabled:
            yield self
            return

        with Live(self.progress, console=self.console, refresh_per_second=4) as live:
            self._live = live
            try:
                yield self
            finally:
                self._live = None
                self._tasks.clear()

    def on_progress(self, event: ProgressEvent) -> None:
        """Handle a progress event."""
        if not self.enabled:
            # Fallback: simple text output
            if event.current is not None and event.total is not None:
                msg = f"[{event.phase}] {event.message} ({event.current}/{event.total})"
                self.console.print(msg)
            else:
                self.console.print(f"[{event.phase}] {event.message}")
            return

        phase_key = event.phase.value
        task_id = self._tasks.get(phase_key)

        # Create or update task
        if task_id is None:
            # New task
            if event.total is not None:
                task_id = self.progress.add_task(
                    event.message,
                    total=event.total,
                    completed=event.current or 0,
                )
            else:
                # Indeterminate progress (spinner only)
                task_id = self.progress.add_task(event.message, total=None)
            self._tasks[phase_key] = task_id
        else:
            # Update existing task
            if event.total is not None:
                self.progress.update(
                    task_id,
                    description=event.message,
                    total=event.total,
                    completed=event.current or 0,
                )
            else:
                self.progress.update(task_id, description=event.message)

        # Mark completed or failed tasks as finished
        if event.phase in (ProgressPhase.COMPLETED, ProgressPhase.FAILED):
            if task_id in self._tasks.values():
                if event.total is not None:
                    self.progress.update(task_id, completed=event.total)
                self.progress.stop_task(task_id)


class SimpleProgressUI(ProgressCallback):
    """Simple text-based progress UI without rich formatting.

    Useful for:
    - Logging to files
    - Non-interactive environments
    - Testing
    """

    def __init__(self) -> None:
        self.console = Console()

    def on_progress(self, event: ProgressEvent) -> None:
        """Handle a progress event."""
        if event.current is not None and event.total is not None:
            pct = (event.current / event.total * 100) if event.total > 0 else 0
            self.console.print(
                f"[{event.phase.value}] {event.message} ({event.current}/{event.total}, {pct:.0f}%)"
            )
        else:
            self.console.print(f"[{event.phase.value}] {event.message}")


class FileProgressCallback(ProgressCallback):
    """File-based progress reporter that writes structured JSON events.

    Each event is written as a single JSON line (JSONL format) for easy parsing
    and future integration with log aggregators.
    """

    def __init__(self, file_path: Path) -> None:
        """Initialize file-based progress reporter.

        Args:
            file_path: Path to write progress events (JSONL format).
        """
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        # Open file in append mode
        self._file = open(file_path, "a", encoding="utf-8")

    def on_progress(self, event: ProgressEvent) -> None:
        """Write progress event as JSON line."""
        event_dict = {
            "timestamp": event.timestamp.isoformat(),
            "phase": event.phase.value,
            "message": event.message,
        }
        if event.progress is not None:
            event_dict["progress"] = event.progress
        if event.current is not None:
            event_dict["current"] = event.current
        if event.total is not None:
            event_dict["total"] = event.total
        if event.account is not None:
            event_dict["account"] = event.account
        if event.metadata is not None:
            event_dict["metadata"] = event.metadata

        self._file.write(json.dumps(event_dict) + "\n")
        self._file.flush()

    def close(self) -> None:
        """Close the file handle."""
        self._file.close()

    def __enter__(self) -> FileProgressCallback:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class PrometheusProgressCallback(ProgressCallback):
    """Prometheus metrics exporter for progress events.

    This is a stub implementation that prepares the architecture for future
    Prometheus integration. To complete:
    1. Add prometheus_client dependency
    2. Initialize metrics (Counter, Gauge, Histogram)
    3. Export metrics via HTTP endpoint or pushgateway
    """

    def __init__(self) -> None:
        """Initialize Prometheus progress reporter."""
        # TODO: Initialize prometheus_client metrics
        # Example:
        #   from prometheus_client import Counter, Gauge
        #   self.sync_messages = Counter('email_archiver_sync_messages_total', ...)
        #   self.sync_progress = Gauge('email_archiver_sync_progress', ...)
        self._console = Console()
        self._console.print(
            "[yellow]Warning: Prometheus backend is not yet implemented. "
            "Events will be logged to console.[/yellow]"
        )

    def on_progress(self, event: ProgressEvent) -> None:
        """Handle progress event (stub implementation)."""
        # TODO: Update Prometheus metrics based on event
        # Example:
        #   if event.phase == ProgressPhase.SYNCING and event.current:
        #       self.sync_messages.inc(event.current)
        #       if event.total:
        #           self.sync_progress.set(event.current / event.total)

        # For now, log to console
        if event.current is not None and event.total is not None:
            self._console.print(
                f"[PROM stub] {event.phase.value}: {event.message} ({event.current}/{event.total})"
            )
