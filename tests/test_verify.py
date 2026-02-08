"""Tests for email_archiver.commands.verify."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from email_archiver.commands.verify import (
    STATUS_FAIL,
    STATUS_PASS,
    _build_report,
    _write_report,
)
from email_archiver.config import (
    AccountConfig,
    BackupConfig,
    Config,
    OrchestrationConfig,
    PathsConfig,
)
from email_archiver.runner import RunResult


@pytest.fixture()
def mock_config(tmp_path: Path) -> Config:
    return Config(
        accounts={"test": AccountConfig("test", "a@b.com", "imap.b.com", "a@b.com")},
        paths=PathsConfig(
            maildir_root=tmp_path / "mail",
            state_dir=tmp_path / "state",
            logs_dir=tmp_path / "state" / "logs",
            verification_dir=tmp_path / "state" / "verification",
        ),
        backup=BackupConfig(),
        orchestration=OrchestrationConfig(),
    )


class TestBuildReport:
    def test_pass_when_all_checks_ok(self, mock_config: Config):
        count_result = RunResult(["notmuch", "count"], 0, "42\n", "", 0.1)
        report = _build_report(
            mock_config,
            "test",
            count_result,
            42,
            "2020-01-01T00:00:00+00:00",
            "2024-12-31T00:00:00+00:00",
        )
        assert report["status"] == STATUS_PASS
        assert report["notmuch"]["total_message_count"] == 42
        assert report["account"] == "test"

    def test_fail_when_count_is_none(self, mock_config: Config):
        count_result = RunResult(["notmuch", "count"], 1, "", "error", 0.1)
        report = _build_report(mock_config, "test", count_result, None, None, None)
        assert report["status"] == STATUS_FAIL

    def test_fail_when_count_is_zero(self, mock_config: Config):
        count_result = RunResult(["notmuch", "count"], 0, "0\n", "", 0.1)
        report = _build_report(mock_config, "test", count_result, 0, None, None)
        assert report["status"] == STATUS_FAIL

    def test_fail_when_missing_dates(self, mock_config: Config):
        count_result = RunResult(["notmuch", "count"], 0, "10\n", "", 0.1)
        report = _build_report(
            mock_config,
            "test",
            count_result,
            10,
            None,
            "2024-01-01T00:00:00+00:00",
        )
        assert report["status"] == STATUS_FAIL

    def test_fail_closed_on_command_failure(self, mock_config: Config):
        """Fail closed: if notmuch count fails, status must be FAIL."""
        count_result = RunResult(["notmuch", "count"], 1, "", "db error", 0.1)
        report = _build_report(mock_config, "test", count_result, None, None, None)
        assert report["status"] == STATUS_FAIL


class TestWriteReport:
    def test_writes_json_and_text(self, mock_config: Config):
        report = {
            "timestamp": "2024-01-01T00:00:00+00:00",
            "account": "test",
            "notmuch": {"total_message_count": 100},
            "coverage": {"oldest_message": "2020-01-01", "newest_message": "2024-01-01"},
            "status": "PASS",
        }
        json_path, text_path = _write_report(mock_config, report, "test")

        assert json_path.exists()
        assert text_path.exists()
        assert json_path.suffix == ".json"
        assert text_path.suffix == ".txt"

        data = json.loads(json_path.read_text())
        assert data["status"] == "PASS"
        assert data["notmuch"]["total_message_count"] == 100

        text = text_path.read_text()
        assert "PASS" in text
        assert "100" in text
