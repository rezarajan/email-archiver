"""Progress reporting system for email-archiver.

This module provides an event-based progress reporting architecture that can:
1. Display progress bars and status updates in the terminal
2. Emit structured events for future integration with monitoring tools (e.g. Prometheus)

Architecture:
- ProgressEvent: Structured events emitted during operations
- ProgressCallback: Protocol for event subscribers (terminal UI, metrics exporters, etc.)
- ProgressReporter: Manages subscribers and dispatches events
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol


class ProgressPhase(str, Enum):
    """Phases of a long-running operation."""

    STARTING = "starting"
    SYNCING = "syncing"
    INDEXING = "indexing"
    VERIFYING = "verifying"
    BACKING_UP = "backing_up"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressEvent:
    """A single progress event that can be rendered or exported as metrics.

    Attributes:
        timestamp: When the event occurred (UTC)
        phase: Current operation phase
        message: Human-readable message
        progress: Optional progress value (0.0 to 1.0)
        current: Optional current count (e.g. messages synced)
        total: Optional total count (e.g. total messages)
        account: Optional account identifier
        metadata: Optional additional data for metrics/debugging
    """

    timestamp: datetime
    phase: ProgressPhase
    message: str
    progress: float | None = None
    current: int | None = None
    total: int | None = None
    account: str | None = None
    metadata: dict[str, str | int | float] | None = None

    @classmethod
    def create(
        cls,
        phase: ProgressPhase,
        message: str,
        *,
        progress: float | None = None,
        current: int | None = None,
        total: int | None = None,
        account: str | None = None,
        metadata: dict[str, str | int | float] | None = None,
    ) -> ProgressEvent:
        """Create a progress event with current timestamp."""
        return cls(
            timestamp=datetime.now(timezone.utc),
            phase=phase,
            message=message,
            progress=progress,
            current=current,
            total=total,
            account=account,
            metadata=metadata,
        )


class ProgressCallback(Protocol):
    """Protocol for progress event subscribers.

    Implementations:
    - Terminal UI with progress bars (rich)
    - Prometheus metrics exporter (future)
    - Structured logging (future)
    """

    def on_progress(self, event: ProgressEvent) -> None:
        """Handle a progress event."""
        ...


class ProgressReporter:
    """Manages progress event subscribers and dispatches events."""

    def __init__(self) -> None:
        self._callbacks: list[ProgressCallback] = []

    def subscribe(self, callback: ProgressCallback) -> None:
        """Add a progress event subscriber."""
        self._callbacks.append(callback)

    def emit(self, event: ProgressEvent) -> None:
        """Emit a progress event to all subscribers."""
        for callback in self._callbacks:
            callback.on_progress(event)

    def report(
        self,
        phase: ProgressPhase,
        message: str,
        *,
        progress: float | None = None,
        current: int | None = None,
        total: int | None = None,
        account: str | None = None,
        metadata: dict[str, str | int | float] | None = None,
    ) -> None:
        """Convenience method to create and emit an event."""
        event = ProgressEvent.create(
            phase=phase,
            message=message,
            progress=progress,
            current=current,
            total=total,
            account=account,
            metadata=metadata,
        )
        self.emit(event)
