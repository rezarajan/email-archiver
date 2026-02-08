"""CLI entrypoint for email-archiver."""

from __future__ import annotations

import argparse
import sys

from email_archiver import __version__
from email_archiver.config import ConfigError, load_config


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    """Add flags shared by multiple subcommands."""
    parser.add_argument(
        "--config",
        "-c",
        metavar="PATH",
        help="Path to config file (default: ~/.config/email-archiver/config.toml)",
    )
    parser.add_argument("--account", "-a", metavar="NAME", help="Account name from config")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="email-archiver",
        description="Archive IMAP mailboxes to local Maildir, index, verify, and backup.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # sync
    p_sync = sub.add_parser("sync", help="Run mbsync to sync IMAP → Maildir")
    _add_common_flags(p_sync)

    # index
    p_index = sub.add_parser("index", help="Run notmuch new to index the Maildir")
    _add_common_flags(p_index)

    # verify
    p_verify = sub.add_parser("verify", help="Run verification checks and write a report")
    _add_common_flags(p_verify)

    # backup
    p_backup = sub.add_parser("backup", help="Run the configured backup command")
    _add_common_flags(p_backup)

    # run
    p_run = sub.add_parser("run", help="Orchestrated: sync → index → verify → backup")
    _add_common_flags(p_run)

    # doctor
    p_doctor = sub.add_parser("doctor", help="Validate prerequisites, config, and paths")
    _add_common_flags(p_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    # Load config
    try:
        config = load_config(args.config)
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    # Dispatch
    if args.command == "doctor":
        from email_archiver.commands.doctor import run_doctor

        ok = run_doctor(config, verbose=args.verbose)
        return 0 if ok else 1

    elif args.command == "sync":
        from email_archiver.commands.sync import run_sync

        result = run_sync(config, account=args.account, verbose=args.verbose, dry_run=args.dry_run)
        return 0 if result.ok else result.exit_code

    elif args.command == "index":
        from email_archiver.commands.index import run_index

        result = run_index(config, verbose=args.verbose, dry_run=args.dry_run)
        return 0 if result.ok else result.exit_code

    elif args.command == "verify":
        from email_archiver.commands.verify import run_verify

        report = run_verify(config, account=args.account, verbose=args.verbose)
        return 0 if report["status"] == "PASS" else 1

    elif args.command == "backup":
        from email_archiver.commands.backup import run_backup

        result = run_backup(config, verbose=args.verbose, dry_run=args.dry_run)
        return 0 if result.ok else result.exit_code

    elif args.command == "run":
        from email_archiver.commands.run import run_all

        return run_all(config, account=args.account, verbose=args.verbose, dry_run=args.dry_run)

    else:
        parser.print_help()
        return 1


def cli_main() -> None:
    """Wrapper that calls sys.exit with the return code."""
    sys.exit(main())


if __name__ == "__main__":
    cli_main()
