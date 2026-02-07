"""Doctor command: validate prerequisites, configuration, and paths."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from email_archiver.config import PASSWORD_FILE, Config


def _check_binary(name: str) -> tuple[bool, str]:
    """Check if a binary is available on PATH."""
    path = shutil.which(name)
    if path:
        return True, f"  OK  {name} found at {path}"
    return False, f"  FAIL  {name} not found on PATH"


def _check_file_exists(path: Path, label: str) -> tuple[bool, str]:
    """Check if a file exists."""
    if path.exists():
        return True, f"  OK  {label}: {path}"
    return False, f"  FAIL  {label} not found: {path}"


def _check_dir_exists_or_creatable(path: Path, label: str) -> tuple[bool, str]:
    """Check if a directory exists or its parent exists (so it can be created)."""
    if path.is_dir():
        return True, f"  OK  {label}: {path}"
    if path.parent.is_dir():
        return True, f"  WARN  {label} does not exist yet (parent exists): {path}"
    return False, f"  FAIL  {label} not accessible (parent missing): {path}"


def run_doctor(config: Config, verbose: bool = False) -> bool:
    """Run all prerequisite checks. Returns True if all critical checks pass."""
    results: list[tuple[bool, str]] = []
    all_ok = True

    # 1. Required binaries
    print("Checking prerequisites...")
    for binary in ["mbsync", "notmuch"]:
        ok, msg = _check_binary(binary)
        results.append((ok, msg))
        if not ok:
            all_ok = False

    # Check backup tool if configured
    if config.backup and config.backup.mode != "command":
        ok, msg = _check_binary(config.backup.mode)
        results.append((ok, msg))
        if not ok:
            all_ok = False

    # 2. Password file
    print("Checking secrets...")
    ok, msg = _check_file_exists(PASSWORD_FILE, "password file")
    results.append((ok, msg))
    if not ok:
        # Warn but don't fail — may not be mounted in doctor-only checks
        results.append((True, f"  WARN  {PASSWORD_FILE} not found (required at runtime)"))

    # 3. Paths
    print("Checking paths...")
    assert config.paths is not None
    ok, msg = _check_dir_exists_or_creatable(config.paths.maildir_root, "maildir_root")
    results.append((ok, msg))
    if not ok:
        all_ok = False

    for label, path in [
        ("state_dir", config.paths.state_dir),
        ("logs_dir", config.paths.logs_dir),
        ("verification_dir", config.paths.verification_dir),
        ("generated_config_dir", config.paths.generated_config_dir),
    ]:
        ok, msg = _check_dir_exists_or_creatable(path, label)
        results.append((ok, msg))

    # Print results
    print()
    for ok, msg in results:
        if msg:
            print(msg)

    print()
    if all_ok:
        print("All checks passed.")
    else:
        print("Some checks failed. Please fix the issues above.")
        # Also check if state dirs need creating
        _ensure_state_dirs(config)

    return all_ok


def _ensure_state_dirs(config: Config) -> None:
    """Create state directories if they don't exist."""
    assert config.paths is not None
    for d in [
        config.paths.state_dir,
        config.paths.logs_dir,
        config.paths.verification_dir,
        config.paths.generated_config_dir,
    ]:
        if not d.is_dir() and d.parent.is_dir():
            try:
                d.mkdir(parents=True, exist_ok=True)
                os.chmod(d, 0o700)
                print(f"  Created directory: {d}")
            except OSError as e:
                print(f"  Could not create {d}: {e}")
