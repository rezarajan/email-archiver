# email-archiver

CLI tool to archive IMAP mailboxes (including Gmail) to local Maildir storage, index for fast local search, generate verification reports, and support safe deletion from the remote server.

## Prerequisites

Install system-level dependencies:

```bash
# Arch Linux
sudo pacman -S isync notmuch

# Debian/Ubuntu
sudo apt install isync notmuch
```

Optional: a backup tool such as `restic`, `borg`, or `rsync`.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

This installs the `email-archiver` CLI.

## Quick Start

### 1. Configure mbsync

Copy and edit the template:

```bash
mkdir -p ~/.config/isync
cp examples/mbsyncrc ~/.config/isync/mbsyncrc
chmod 600 ~/.config/isync/mbsyncrc
# Edit: set your IMAP host, user, and PassCmd
```

**Important:** Never store passwords in config files. Use `PassCmd` to fetch credentials from a secret manager (e.g. `pass`).

For Gmail: use an App Password (when 2FA is enabled) and the Gmail profile (sync `[Gmail]/All Mail` only) to avoid duplicates.

### 2. Configure notmuch

```bash
cp examples/notmuch-config ~/.notmuch-config
# Edit: set database path and email
```

### 3. Configure email-archiver

```bash
mkdir -p ~/.config/email-archiver
cp examples/config.toml ~/.config/email-archiver/config.toml
# Edit: set account details, paths, and backup command
```

### 4. Validate setup

```bash
email-archiver doctor
```

### 5. Run the pipeline

```bash
# Individual steps:
email-archiver sync
email-archiver index
email-archiver verify
email-archiver backup

# Or all at once (sync → index → verify → backup):
email-archiver run
```

## Commands

| Command | Description |
|---------|-------------|
| `sync` | Run mbsync to sync IMAP → Maildir |
| `index` | Run notmuch new to index the Maildir |
| `verify` | Run completeness checks, write JSON + text report |
| `backup` | Run the configured backup command |
| `run` | Orchestrated pipeline: sync → index → verify → backup |
| `doctor` | Validate prerequisites, config, and paths |

### Common flags

- `--config PATH` / `-c PATH` — Override config file location
- `--account NAME` / `-a NAME` — Select a specific account
- `--verbose` / `-v` — Verbose output
- `--dry-run` — Print commands without executing

## Scheduling with systemd

Install the user units:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/email-archiver-run.service ~/.config/systemd/user/
cp systemd/email-archiver-run.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now email-archiver-run.timer
```

Check status:

```bash
systemctl --user status email-archiver-run.timer
journalctl --user -u email-archiver-run.service
```

## Verification Reports

Each `verify` run writes:
- A JSON report to `~/.local/state/email-archiver/verification/<account>/`
- A human-readable text summary alongside it

Reports include: timestamp, account, message count, oldest/newest message dates, and PASS/FAIL status.

Verification **fails closed**: if checks cannot run, the status is FAIL.

## Safety Model (Deletion)

Deletion from the remote server is **intentionally not automated**. It is gated behind:

1. A successful sync + index
2. A PASS verification report
3. A successful secondary backup

**Recommended workflow:**
1. Run `email-archiver run` until verification passes consistently
2. Confirm backup exists on secondary storage
3. Delete from the remote server via the provider's UI (Gmail web, etc.)

## Configuration Reference

See `examples/config.toml` for a fully commented example.

Key sections:
- `[account.<name>]` — IMAP account details
- `[paths]` — Maildir root, state/log/verification directories
- `[mbsync]` — Path to mbsyncrc and sync group name
- `[notmuch]` — Path to notmuch config
- `[backup]` — Backup mode and command
- `[orchestration]` — Whether to run backup after verify

## Development

```bash
# Run tests
pytest

# Run linter
ruff check src/ tests/

# Format
ruff format src/ tests/
```

## License

MIT
