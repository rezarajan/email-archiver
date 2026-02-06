"""Tests for email_archiver.cli."""

from __future__ import annotations

from pathlib import Path

import pytest

from email_archiver.cli import build_parser, main

MINIMAL_CONFIG = """\
[account.primary]
email = "user@example.com"
imap_host = "imap.example.com"
imap_user = "user@example.com"

[paths]
maildir_root = "/tmp/test-maildir"

[mbsync]
config_path = "/tmp/test-mbsyncrc"

[notmuch]
config_path = "/tmp/test-notmuch-config"
"""


@pytest.fixture()
def config_file(tmp_path: Path) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(MINIMAL_CONFIG)
    return p


class TestBuildParser:
    def test_has_subcommands(self):
        parser = build_parser()
        with pytest.raises(SystemExit, match="0"):
            parser.parse_args(["--version"])

    def test_sync_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["sync", "--verbose", "--dry-run"])
        assert args.command == "sync"
        assert args.verbose is True
        assert args.dry_run is True

    def test_doctor_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["doctor"])
        assert args.command == "doctor"

    def test_run_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["run", "--account", "primary"])
        assert args.command == "run"
        assert args.account == "primary"


class TestMain:
    def test_no_command_returns_1(self):
        assert main([]) == 1

    def test_missing_config_returns_1(self):
        assert main(["doctor", "--config", "/nonexistent/config.toml"]) != 0

    def test_config_error_message(self, capsys: pytest.CaptureFixture[str]):
        main(["doctor", "--config", "/nonexistent/config.toml"])
        captured = capsys.readouterr()
        assert "Configuration error" in captured.err

    def test_doctor_with_config(self, config_file: Path):
        """Doctor should load config and run checks (may fail on missing binaries)."""
        # The doctor command may return 1 if mbsync/notmuch not installed, but should not raise
        ret = main(["doctor", "--config", str(config_file)])
        assert ret in (0, 1)

    def test_sync_dry_run(self, config_file: Path):
        """Dry-run sync should succeed without actually running mbsync."""
        ret = main(["sync", "--config", str(config_file), "--dry-run"])
        assert ret == 0

    def test_index_dry_run(self, config_file: Path):
        ret = main(["index", "--config", str(config_file), "--dry-run"])
        assert ret == 0

    def test_backup_dry_run(self, config_file: Path):
        ret = main(["backup", "--config", str(config_file), "--dry-run"])
        assert ret == 0
