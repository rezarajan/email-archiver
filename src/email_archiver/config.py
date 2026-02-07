"""Configuration loader and validator for email-archiver."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomllib

DEFAULT_CONFIG_PATH = "~/.config/email-archiver/config.toml"

# Password is ONLY provided via a file at this fixed path.
PASSWORD_FILE = Path("/run/secrets/imap_password")


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""


@dataclass
class AccountConfig:
    name: str
    email: str
    imap_host: str
    imap_user: str
    tls_type: str = "IMAPS"
    folders: list[str] = field(default_factory=lambda: ["INBOX"])


@dataclass
class PathsConfig:
    maildir_root: Path
    state_dir: Path
    logs_dir: Path
    verification_dir: Path
    generated_config_dir: Path = Path()

    def __post_init__(self) -> None:
        if self.generated_config_dir == Path():
            self.generated_config_dir = self.state_dir / "generated"


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
            tls_type=data.get("tls_type", "IMAPS"),
            folders=data.get("folders", ["INBOX"]),
        )
    return accounts


def _parse_paths(raw: dict[str, Any]) -> PathsConfig:
    _require_keys(raw, ["maildir_root"], "paths")
    maildir_root = expand_path(raw["maildir_root"])
    state_dir = expand_path(raw.get("state_dir", "~/.local/state/email-archiver"))
    paths = PathsConfig(
        maildir_root=maildir_root,
        state_dir=state_dir,
        logs_dir=expand_path(raw.get("logs_dir", str(state_dir / "logs"))),
        verification_dir=expand_path(raw.get("verification_dir", str(state_dir / "verification"))),
    )
    if "generated_config_dir" in raw:
        paths.generated_config_dir = expand_path(raw["generated_config_dir"])
    return paths


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

    All IMAP/sync/index settings are derived from [account.*] sections.
    mbsync and notmuch configs are auto-generated at runtime.

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

    if "backup" in raw:
        config.backup = _parse_backup(raw["backup"])
    else:
        config.backup = BackupConfig()

    if "orchestration" in raw:
        config.orchestration = _parse_orchestration(raw["orchestration"])
    else:
        config.orchestration = OrchestrationConfig()

    return config
