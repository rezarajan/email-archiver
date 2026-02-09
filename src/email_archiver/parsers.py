"""Output parsers for external commands (mbsync, notmuch) to track progress."""

from __future__ import annotations

import re

from email_archiver.progress import ProgressPhase, ProgressReporter


class MbsyncParser:
    """Parse mbsync output to track sync progress.

    mbsync output patterns (varies by version and verbosity):
    - Message counts: "near side: 123 messages, 0 recent"
    - Message counts: "far side: 456 messages, 0 recent"
    - Operations: "Channels: 1  Boxes: 1  Far: +10 *2 #1 -0  Near: +5 *1 #0 -0"
    - Legacy pattern: "C: 1/1  B: 123/456  M: +1/0  S: +2/0  *3"

    This parser extracts message counts and sync operations.
    """

    def __init__(self, reporter: ProgressReporter, account: str) -> None:
        self.reporter = reporter
        self.account = account
        self.near_total = 0
        self.far_total = 0
        self.operations_count = 0
        self._started = False
        self._syncing_started = False

    def parse_line(self, line: str) -> None:
        """Parse a single line of mbsync output."""
        if not self._started:
            self._started = True
            self.reporter.report(
                ProgressPhase.SYNCING,
                f"Syncing {self.account}...",
                account=self.account,
            )

        # Pattern: "near side: 123 messages, 0 recent"
        match = re.search(r"near side:\s+(\d+)\s+messages?", line)
        if match:
            self.near_total = int(match.group(1))

        # Pattern: "far side: 456 messages, 0 recent"
        match = re.search(r"far side:\s+(\d+)\s+messages?", line)
        if match:
            self.far_total = int(match.group(1))

        # Pattern: "Synchronizing..."
        if "Synchronizing" in line:
            self._syncing_started = True
            total = max(self.near_total, self.far_total)
            if total > 0:
                self.reporter.report(
                    ProgressPhase.SYNCING,
                    f"Synchronizing {self.account} ({total} messages)",
                    current=0,
                    total=total,
                    account=self.account,
                )

        # Pattern: "Channels: 1  Boxes: 1  Far: +10 *2 #1 -0  Near: +5 *1 #0 -0"
        # This shows operations: +N (new), *N (flags), #N (deleted), -N (expunged)
        if self._syncing_started and "Far:" in line and "Near:" in line:
            # Extract Far operations
            far_match = re.search(r"Far:\s+\+(\d+)\s+\*(\d+)\s+#(\d+)", line)
            near_match = re.search(r"Near:\s+\+(\d+)\s+\*(\d+)\s+#(\d+)", line)

            if far_match and near_match:
                far_new = int(far_match.group(1))
                far_flags = int(far_match.group(2))
                far_deleted = int(far_match.group(3))
                near_new = int(near_match.group(1))
                near_flags = int(near_match.group(2))
                near_deleted = int(near_match.group(3))

                # Count total operations
                total_ops = far_new + far_flags + far_deleted + near_new + near_flags + near_deleted
                self.operations_count += total_ops

                if total_ops > 0:
                    # Build descriptive message
                    parts = []
                    if near_new > 0:
                        parts.append(f"+{near_new} downloaded")
                    if far_new > 0:
                        parts.append(f"+{far_new} uploaded")
                    if near_flags > 0 or far_flags > 0:
                        parts.append(f"*{near_flags + far_flags} updated")
                    if near_deleted > 0 or far_deleted > 0:
                        parts.append(f"#{near_deleted + far_deleted} deleted")

                    message = (
                        f"Syncing {self.account}: {', '.join(parts)}"
                        if parts
                        else f"Syncing {self.account}"
                    )
                    total = max(self.near_total, self.far_total)
                    self.reporter.report(
                        ProgressPhase.SYNCING,
                        message,
                        current=self.operations_count,
                        total=total if total > 0 else None,
                        account=self.account,
                    )

        # Legacy pattern: "C: 1/1  B: 123/456" for older mbsync versions
        match = re.search(r"B:\s+(\d+)/(\d+)", line)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            if total > 0:
                self.reporter.report(
                    ProgressPhase.SYNCING,
                    f"Syncing {self.account}",
                    current=current,
                    total=total,
                    account=self.account,
                )

        # Final completion line (appears after all operations)
        if (
            self._syncing_started
            and line.startswith("Channels:")
            and "Far: +0 *0 #0 -0" in line
            and "Near: +0 *0 #0 -0" in line
        ):
            # This is the final summary line with no operations
            total = max(self.near_total, self.far_total)
            self.reporter.report(
                ProgressPhase.COMPLETED,
                f"Sync completed: {total} messages",
                current=total,
                total=total if total > 0 else None,
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
