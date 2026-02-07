"""Tests for email_archiver.generate."""

from __future__ import annotations

from pathlib import Path

import pytest

from email_archiver.config import (
    PASSWORD_FILE,
    AccountConfig,
    BackupConfig,
    Config,
    OrchestrationConfig,
    PathsConfig,
)
from email_archiver.generate import (
    _sanitize_name,
    generate_mbsyncrc,
    generate_notmuch_config,
    write_generated_configs,
)


@pytest.fixture()
def config(tmp_path: Path) -> Config:
    return Config(
        accounts={
            "primary": AccountConfig(
                name="primary",
                email="user@example.com",
                imap_host="imap.example.com",
                imap_user="user@example.com",
                tls_type="IMAPS",
                folders=["INBOX", "Archive"],
            ),
        },
        paths=PathsConfig(
            maildir_root=tmp_path / "mail",
            state_dir=tmp_path / "state",
            logs_dir=tmp_path / "state" / "logs",
            verification_dir=tmp_path / "state" / "verification",
        ),
        backup=BackupConfig(),
        orchestration=OrchestrationConfig(),
    )


class TestSanitizeName:
    def test_simple(self):
        assert _sanitize_name("INBOX") == "INBOX"

    def test_brackets_and_slashes(self):
        assert _sanitize_name("[Gmail]/All Mail") == "Gmail--All-Mail"

    def test_special_chars(self):
        assert _sanitize_name("foo bar!baz") == "foo-bar-baz"


class TestGenerateMbsyncrc:
    def test_contains_account_block(self, config: Config):
        rc = generate_mbsyncrc(config)
        assert "IMAPAccount primary" in rc
        assert "Host imap.example.com" in rc
        assert "User user@example.com" in rc
        assert f'PassCmd "cat {PASSWORD_FILE}"' in rc
        assert "TLSType IMAPS" in rc

    def test_contains_stores(self, config: Config):
        rc = generate_mbsyncrc(config)
        assert "IMAPStore primary-remote" in rc
        assert "MaildirStore primary-local" in rc
        assert str(config.paths.maildir_root / "primary") in rc

    def test_contains_channels_per_folder(self, config: Config):
        rc = generate_mbsyncrc(config)
        assert "Channel primary-INBOX" in rc
        assert "Channel primary-Archive" in rc
        assert 'Far :primary-remote:"INBOX"' in rc
        assert 'Far :primary-remote:"Archive"' in rc

    def test_contains_group(self, config: Config):
        rc = generate_mbsyncrc(config)
        assert "Group primary" in rc

    def test_multi_account(self, config: Config):
        config.accounts["secondary"] = AccountConfig(
            name="secondary",
            email="other@example.com",
            imap_host="imap2.example.com",
            imap_user="other@example.com",
            folders=["INBOX"],
        )
        rc = generate_mbsyncrc(config)
        assert "IMAPAccount primary" in rc
        assert "IMAPAccount secondary" in rc
        assert "Group secondary" in rc


class TestGenerateNotmuchConfig:
    def test_database_path(self, config: Config):
        nm = generate_notmuch_config(config)
        assert f"path={config.paths.maildir_root}" in nm

    def test_user_section(self, config: Config):
        nm = generate_notmuch_config(config)
        assert "primary_email=user@example.com" in nm

    def test_sections_present(self, config: Config):
        nm = generate_notmuch_config(config)
        for section in ["[database]", "[user]", "[new]", "[search]", "[maildir]"]:
            assert section in nm


class TestWriteGeneratedConfigs:
    def test_writes_files(self, config: Config):
        mbsyncrc, notmuch_cfg = write_generated_configs(config)
        assert mbsyncrc.exists()
        assert notmuch_cfg.exists()
        assert mbsyncrc.name == "mbsyncrc"
        assert notmuch_cfg.name == "notmuch-config"

    def test_written_to_generated_dir(self, config: Config):
        mbsyncrc, notmuch_cfg = write_generated_configs(config)
        assert config.paths is not None
        assert mbsyncrc.parent == config.paths.generated_config_dir
        assert notmuch_cfg.parent == config.paths.generated_config_dir

    def test_idempotent(self, config: Config):
        p1 = write_generated_configs(config)
        p2 = write_generated_configs(config)
        assert p1 == p2
