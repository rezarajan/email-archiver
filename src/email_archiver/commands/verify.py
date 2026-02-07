"""Verify command: run completeness checks and produce verification reports."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from email_archiver.config import Config
from email_archiver.generate import ensure_notmuch_init, write_generated_configs
from email_archiver.runner import RunResult, run_command

# Verification MUST fail closed: if checks cannot run, status is FAIL.
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"


def _notmuch_env(notmuch_config_path: Path) -> dict[str, str]:
    return {**os.environ, "NOTMUCH_CONFIG": str(notmuch_config_path)}


def _get_message_count(notmuch_config_path: Path) -> tuple[RunResult, int | None]:
    """Get total message count from notmuch."""
    env = _notmuch_env(notmuch_config_path)
    result = run_command(["notmuch", "count", "*"], env=env)
    if result.ok:
        try:
            count = int(result.stdout.strip())
            return result, count
        except ValueError:
            return result, None
    return result, None


def _get_date_boundary(notmuch_config_path: Path, sort: str) -> tuple[RunResult, str | None]:
    """Get oldest or newest message date.

    Args:
        sort: 'oldest-first' or 'newest-first'
    """
    env = _notmuch_env(notmuch_config_path)
    result = run_command(
        ["notmuch", "search", "--format=json", f"--sort={sort}", "--limit=1", "*"],
        env=env,
    )
    if result.ok and result.stdout.strip():
        try:
            messages = json.loads(result.stdout)
            if messages and isinstance(messages, list):
                ts = messages[0].get("timestamp", 0)
                if ts:
                    return result, datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                # Fall back to date_relative
                return result, messages[0].get("date_relative", "unknown")
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
    return result, None


def _build_report(
    config: Config,
    account: str,
    count_result: RunResult,
    message_count: int | None,
    oldest_date: str | None,
    newest_date: str | None,
) -> dict[str, Any]:
    """Build the verification report dict."""
    now = datetime.now(timezone.utc).isoformat()
    status = STATUS_FAIL  # fail closed

    # Determine pass/fail
    checks_ran = count_result.ok and message_count is not None
    if checks_ran and message_count > 0 and oldest_date and newest_date:
        status = STATUS_PASS

    return {
        "timestamp": now,
        "account": account,
        "notmuch": {
            "total_message_count": message_count,
        },
        "coverage": {
            "oldest_message": oldest_date,
            "newest_message": newest_date,
        },
        "status": status,
    }


def _write_report(config: Config, report: dict[str, Any], account: str) -> tuple[Path, Path]:
    """Write JSON and text report files. Returns (json_path, text_path)."""
    assert config.paths is not None
    report_dir = config.paths.verification_dir / account
    report_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    json_path = report_dir / f"verify-{ts}.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    text_path = report_dir / f"verify-{ts}.txt"
    text_lines = [
        f"Verification Report — {report['timestamp']}",
        f"Account:  {report['account']}",
        f"Status:   {report['status']}",
        f"Messages: {report['notmuch']['total_message_count']}",
        f"Oldest:   {report['coverage']['oldest_message']}",
        f"Newest:   {report['coverage']['newest_message']}",
    ]
    text_path.write_text("\n".join(text_lines) + "\n", encoding="utf-8")

    return json_path, text_path


def run_verify(
    config: Config,
    *,
    account: str | None = None,
    verbose: bool = False,
    notmuch_config_path: Path | None = None,
) -> dict[str, Any]:
    """Run verification checks and write a report.

    Returns:
        The verification report dict (with 'status' of PASS or FAIL).
    """
    if notmuch_config_path is None:
        _, notmuch_config_path = write_generated_configs(config)

    # Auto-initialize notmuch database if needed
    ensure_notmuch_init(config, notmuch_config_path)

    acct_name = account or "default"
    print(f"Running verification for account '{acct_name}'...")

    # 1. Get message count
    count_result, message_count = _get_message_count(notmuch_config_path)
    if verbose:
        print(f"  notmuch count: {message_count}")

    # 2. Get date boundaries
    _, oldest_date = _get_date_boundary(notmuch_config_path, "oldest-first")
    _, newest_date = _get_date_boundary(notmuch_config_path, "newest-first")
    if verbose:
        print(f"  oldest message: {oldest_date}")
        print(f"  newest message: {newest_date}")

    # 3. Build report
    report = _build_report(config, acct_name, count_result, message_count, oldest_date, newest_date)

    # 4. Write report
    json_path, text_path = _write_report(config, report, acct_name)
    print("  Report written to:")
    print(f"    JSON: {json_path}")
    print(f"    Text: {text_path}")

    # 5. Print summary
    status = report["status"]
    if status == STATUS_PASS:
        print(f"  Verification: PASS ({message_count} messages, {oldest_date} → {newest_date})")
    else:
        print("  Verification: FAIL")
        if message_count is None:
            print("    Could not determine message count (notmuch may not be configured).")
        elif message_count == 0:
            print("    No messages found in the index.")

    return report
