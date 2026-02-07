"""Tests for email_archiver.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from email_archiver.config import ConfigError, expand_path, load_config

MINIMAL_CONFIG = """\
[account.primary]
email = "user@example.com"
imap_host = "imap.example.com"
imap_user = "user@example.com"

[paths]
maildir_root = "/tmp/test-maildir"
"""

FULL_CONFIG = """\
[account.primary]
email = "user@example.com"
imap_host = "imap.example.com"
imap_user = "user@example.com"
tls_type = "STARTTLS"
folders = ["INBOX", "Archive"]

[paths]
maildir_root = "/tmp/test-maildir"
state_dir = "/tmp/test-state"
logs_dir = "/tmp/test-state/logs"
verification_dir = "/tmp/test-state/verification"

[backup]
mode = "command"
command = "echo backup"

[orchestration]
backup_after_verify = false
"""


@pytest.fixture()
def config_file(tmp_path: Path) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(MINIMAL_CONFIG)
    return p


@pytest.fixture()
def full_config_file(tmp_path: Path) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(FULL_CONFIG)
    return p


class TestExpandPath:
    def test_tilde_expansion(self):
        result = expand_path("~/foo")
        assert str(result).startswith("/")
        assert "~" not in str(result)

    def test_env_var_expansion(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_EMAIL_DIR", "/opt/mail")
        result = expand_path("$TEST_EMAIL_DIR/inbox")
        assert result == Path("/opt/mail/inbox")

    def test_plain_path(self):
        result = expand_path("/absolute/path")
        assert result == Path("/absolute/path")


class TestLoadConfig:
    def test_missing_file(self):
        with pytest.raises(ConfigError, match="not found"):
            load_config("/nonexistent/path.toml")

    def test_invalid_toml(self, tmp_path: Path):
        bad = tmp_path / "bad.toml"
        bad.write_text("this is not [valid toml")
        with pytest.raises(ConfigError, match="Invalid TOML"):
            load_config(bad)

    def test_missing_account(self, tmp_path: Path):
        p = tmp_path / "config.toml"
        p.write_text("""\
[paths]
maildir_root = "/tmp/m"
""")
        with pytest.raises(ConfigError, match="account"):
            load_config(p)

    def test_missing_paths(self, tmp_path: Path):
        p = tmp_path / "config.toml"
        p.write_text("""\
[account.primary]
email = "a@b.com"
imap_host = "h"
imap_user = "u"
""")
        with pytest.raises(ConfigError, match="paths"):
            load_config(p)

    def test_minimal_config(self, config_file: Path):
        cfg = load_config(config_file)
        assert "primary" in cfg.accounts
        assert cfg.accounts["primary"].email == "user@example.com"
        assert cfg.accounts["primary"].tls_type == "IMAPS"  # default
        assert cfg.accounts["primary"].folders == ["INBOX"]  # default
        assert cfg.paths is not None
        assert cfg.paths.maildir_root == Path("/tmp/test-maildir")
        # Defaults
        assert cfg.backup is not None
        assert cfg.orchestration is not None
        assert cfg.orchestration.backup_after_verify is True

    def test_full_config(self, full_config_file: Path):
        cfg = load_config(full_config_file)
        assert cfg.accounts["primary"].tls_type == "STARTTLS"
        assert cfg.accounts["primary"].folders == ["INBOX", "Archive"]
        assert cfg.backup is not None
        assert cfg.backup.command == "echo backup"
        assert cfg.orchestration is not None
        assert cfg.orchestration.backup_after_verify is False
        assert cfg.paths is not None
        assert cfg.paths.logs_dir == Path("/tmp/test-state/logs")

    def test_generated_config_dir_defaults(self, config_file: Path):
        cfg = load_config(config_file)
        assert cfg.paths is not None
        assert cfg.paths.generated_config_dir == cfg.paths.state_dir / "generated"

    def test_account_missing_required_key(self, tmp_path: Path):
        p = tmp_path / "config.toml"
        p.write_text("""\
[account.primary]
email = "a@b.com"
# missing imap_host and imap_user
[paths]
maildir_root = "/tmp/m"
""")
        with pytest.raises(ConfigError, match="imap_host"):
            load_config(p)
