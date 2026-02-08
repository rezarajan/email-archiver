"""Run command: orchestrated sync → index → verify → (optional) backup."""

from __future__ import annotations

from email_archiver.commands.backup import run_backup
from email_archiver.commands.index import run_index
from email_archiver.commands.sync import run_sync
from email_archiver.commands.verify import run_verify
from email_archiver.config import Config
from email_archiver.generate import write_generated_configs


def run_all(
    config: Config,
    *,
    account: str | None = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> int:
    """Run the full orchestration pipeline: sync → index → verify → backup.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    # Generate configs once for the whole pipeline
    mbsyncrc_path, notmuch_config_path = write_generated_configs(config)

    # Step 1: Sync
    print("=" * 60)
    print("Step 1/3: Sync")
    print("=" * 60)
    sync_result = run_sync(
        config,
        account=account,
        verbose=verbose,
        dry_run=dry_run,
        mbsyncrc_path=mbsyncrc_path,
    )
    if not sync_result.ok:
        print("\nSync failed — aborting pipeline.")
        return sync_result.exit_code

    # Step 2: Index
    print()
    print("=" * 60)
    print("Step 2/3: Index")
    print("=" * 60)
    index_result = run_index(
        config,
        verbose=verbose,
        dry_run=dry_run,
        notmuch_config_path=notmuch_config_path,
    )
    if not index_result.ok:
        print("\nIndex failed — aborting pipeline.")
        return index_result.exit_code

    # Step 3: Verify
    print()
    print("=" * 60)
    print("Step 3/3: Verify")
    print("=" * 60)
    report = run_verify(
        config,
        account=account,
        verbose=verbose,
        notmuch_config_path=notmuch_config_path,
    )
    if report["status"] != "PASS":
        print("\nVerification FAILED — skipping backup.")
        return 1

    # Optional Step 4: Backup (only if verify passed and configured)
    assert config.orchestration is not None
    if config.orchestration.backup_after_verify:
        print()
        print("=" * 60)
        print("Bonus: Backup (verify passed)")
        print("=" * 60)
        backup_result = run_backup(config, verbose=verbose, dry_run=dry_run)
        if not backup_result.ok:
            print("\nBackup failed.")
            return backup_result.exit_code

    print()
    print("Pipeline completed successfully.")
    return 0
