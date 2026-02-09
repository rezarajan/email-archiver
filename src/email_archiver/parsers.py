"""Output parsers for external commands (mbsync, notmuch) to track progress."""

from __future__ import annotations

import re

from email_archiver.progress import ProgressPhase, ProgressReporter


class MbsyncParser:
    """Parse mbsync output to track sync progress.

    mbsync output patterns (varies by version and verbosity):
    - Channel patterns: "C: 1/1  B: 123/456  M: +1/0  S: +2/0  *3"
    - Message operations: "Pulling...", "Pushing...", "Syncing..."
    - Completion: "Complete", "Done"

    This parser extracts message counts and emits progress events.
    """

    def __init__(self, reporter: ProgressReporter, account: str) -> None:
        self.reporter = reporter
        self.account = account
        self.current_total = 0
        self.current_synced = 0
        self._started = False

    def parse_line(self, line: str) -> None:
        """Parse a single line of mbsync output."""
        if not self._started:
            self._started = True
            self.reporter.report(
                ProgressPhase.SYNCING,
                f"Syncing {self.account}...",
                account=self.account,
            )

        # Pattern: "C: 1/1  B: 123/456" - extracting message counts
        # B: shows messages being processed (current/total)
        match = re.search(r"B:\s+(\d+)/(\d+)", line)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            if total > 0:
                self.current_total = max(self.current_total, total)
                self.current_synced = current
                self.reporter.report(
                    ProgressPhase.SYNCING,
                    f"Syncing {self.account}",
                    current=current,
                    total=total,
                    account=self.account,
                )

        # Look for completion messages
        if "Complete" in line or "Done" in line or line.startswith("C: "):
            # Extract channel completion pattern "C: 1/1"
            channel_match = re.search(r"C:\s+(\d+)/(\d+)", line)
            if channel_match:
                current = int(channel_match.group(1))
                total = int(channel_match.group(2))
                if current == total:
                    self.reporter.report(
                        ProgressPhase.COMPLETED,
                        f"Sync completed for {self.account}",
                        current=self.current_synced,
                        total=self.current_total if self.current_total > 0 else None,
                        account=self.account,
                    )


class NotmuchParser:
    """Parse notmuch output to track indexing progress.

    notmuch new output patterns:
    - "Processed 123 total files in 1m 23s (123 messages added)"
    - "Added 123 new messages to the database"
    - "No new mail"
    """

    def __init__(self, reporter: ProgressReporter, account: str | None = None) -> None:
        self.reporter = reporter
        self.account = account
        self._started = False
        self._files_processed = 0

    def parse_line(self, line: str) -> None:
        """Parse a single line of notmuch output."""
        if not self._started:
            self._started = True
            self.reporter.report(
                ProgressPhase.INDEXING,
                "Indexing mailbox...",
                account=self.account,
            )

        # Pattern: "Processed 123 total files"
        match = re.search(r"Processed\s+(\d+)\s+total files", line)
        if match:
            files = int(match.group(1))
            self._files_processed = files
            # Extract messages if available
            msg_match = re.search(r"(\d+)\s+messages? added", line)
            if msg_match:
                messages = int(msg_match.group(1))
                self.reporter.report(
                    ProgressPhase.COMPLETED,
                    f"Indexed {messages} new messages",
                    current=messages,
                    account=self.account,
                )
            else:
                self.reporter.report(
                    ProgressPhase.INDEXING,
                    f"Processed {files} files",
                    account=self.account,
                )

        # Pattern: "Added 123 new messages"
        match = re.search(r"Added\s+(\d+)\s+new messages", line)
        if match:
            messages = int(match.group(1))
            self.reporter.report(
                ProgressPhase.COMPLETED,
                f"Indexed {messages} new messages",
                current=messages,
                account=self.account,
            )

        # Pattern: "No new mail"
        if "No new mail" in line:
            self.reporter.report(
                ProgressPhase.COMPLETED,
                "No new mail to index",
                account=self.account,
            )
