"""Configuration loader and validator for email-archiver."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomllib

DEFAULT_CONFIG_PATH = "~/.config/email-archiver/config.toml"


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""


@dataclass
class AccountConfig:
    name: str
    email: str
    imap_host: str
    imap_user: str


@dataclass
class PathsConfig:
    maildir_root: Path
    state_dir: Path
    logs_dir: Path
    verification_dir: Path


@dataclass
class MbsyncConfig:
    config_path: Path
    group: str = ""


@dataclass
class NotmuchConfig:
    config_path: Path


@dataclass
class BackupConfig:
    mode: str = "command"
    command: str = ""


@dataclass
class OrchestrationConfig:
    backup_after_verify: bool = True


@dataclass
class Config:
    accounts: dict[str, AccountConfig] = field(default_factory=dict)
    paths: PathsConfig | None = None
    mbsync: MbsyncConfig | None = None
    notmuch: NotmuchConfig | None = None
    backup: BackupConfig | None = None
    orchestration: OrchestrationConfig | None = None


def expand_path(p: str) -> Path:
    """Expand ~ and environment variables in a path string."""
    return Path(os.path.expandvars(os.path.expanduser(p)))


def _require_keys(section: dict[str, Any], keys: list[str], section_name: str) -> None:
    """Raise ConfigError if any required keys are missing."""
    for k in keys:
        if k not in section:
            raise ConfigError(f"Missing required key '{k}' in [{section_name}]")


def _parse_accounts(raw: dict[str, Any]) -> dict[str, AccountConfig]:
    accounts: dict[str, AccountConfig] = {}
    for name, data in raw.items():
        if not isinstance(data, dict):
            raise ConfigError(f"Account '{name}' must be a table")
        _require_keys(data, ["email", "imap_host", "imap_user"], f"account.{name}")
        accounts[name] = AccountConfig(
            name=name,
            email=data["email"],
            imap_host=data["imap_host"],
            imap_user=data["imap_user"],
        )
    return accounts


def _parse_paths(raw: dict[str, Any]) -> PathsConfig:
    _require_keys(raw, ["maildir_root"], "paths")
    maildir_root = expand_path(raw["maildir_root"])
    state_dir = expand_path(raw.get("state_dir", "~/.local/state/email-archiver"))
    return PathsConfig(
        maildir_root=maildir_root,
        state_dir=state_dir,
        logs_dir=expand_path(raw.get("logs_dir", str(state_dir / "logs"))),
        verification_dir=expand_path(
            raw.get("verification_dir", str(state_dir / "verification"))
        ),
    )


def _parse_mbsync(raw: dict[str, Any]) -> MbsyncConfig:
    _require_keys(raw, ["config_path"], "mbsync")
    return MbsyncConfig(
        config_path=expand_path(raw["config_path"]),
        group=raw.get("group", ""),
    )


def _parse_notmuch(raw: dict[str, Any]) -> NotmuchConfig:
    _require_keys(raw, ["config_path"], "notmuch")
    return NotmuchConfig(config_path=expand_path(raw["config_path"]))


def _parse_backup(raw: dict[str, Any]) -> BackupConfig:
    return BackupConfig(
        mode=raw.get("mode", "command"),
        command=raw.get("command", ""),
    )


def _parse_orchestration(raw: dict[str, Any]) -> OrchestrationConfig:
    return OrchestrationConfig(
        backup_after_verify=raw.get("backup_after_verify", True),
    )


def load_config(path: str | Path | None = None) -> Config:
    """Load and validate the email-archiver configuration file.

    Args:
        path: Path to config file. Defaults to ~/.config/email-archiver/config.toml.

    Returns:
        A validated Config object.

    Raises:
        ConfigError: If the file is missing, unreadable, or invalid.
    """
    config_path = expand_path(str(path)) if path else expand_path(DEFAULT_CONFIG_PATH)

    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")
    if not config_path.is_file():
        raise ConfigError(f"Config path is not a file: {config_path}")

    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Invalid TOML in {config_path}: {e}") from e

    config = Config()

    if "account" in raw:
        config.accounts = _parse_accounts(raw["account"])
    if not config.accounts:
        raise ConfigError("At least one [account.<name>] section is required")

    if "paths" not in raw:
        raise ConfigError("[paths] section is required")
    config.paths = _parse_paths(raw["paths"])

    if "mbsync" in raw:
        config.mbsync = _parse_mbsync(raw["mbsync"])
    else:
        raise ConfigError("[mbsync] section is required")

    if "notmuch" in raw:
        config.notmuch = _parse_notmuch(raw["notmuch"])
    else:
        raise ConfigError("[notmuch] section is required")

    if "backup" in raw:
        config.backup = _parse_backup(raw["backup"])
    else:
        config.backup = BackupConfig()

    if "orchestration" in raw:
        config.orchestration = _parse_orchestration(raw["orchestration"])
    else:
        config.orchestration = OrchestrationConfig()

    return config
