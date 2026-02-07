# SPEC: Email Archiver (IMAP → Local Maildir)

## 1. Overview
This project provides a **CLI-first**, scriptable way to archive an IMAP mailbox to local Linux storage in a portable format, index it for fast local search, and support safe deletion from the remote server after verification.

The solution intentionally composes proven tools:
- `mbsync` (isync) for IMAP → Maildir synchronization
- `notmuch` for local indexing/search
- a backup tool (`restic`/`borg`/`rsync`) for secondary copies

The repo’s job is to provide orchestration, guardrails, templates, and a repeatable workflow.

## 2. Goals and Non-Goals
### 2.1 Goals
- Export IMAP mail to a **local Maildir**.
- Avoid duplicate storage by syncing only canonical sources (provider-dependent; Gmail requires special handling).
- Support **resumable** sync and safe reruns.
- Provide **local full-text search**.
- Provide a **verification gate** that must pass before deletion.
- Provide hooks for **secondary backups**.
- Provide `systemd --user` units to schedule unattended sync/index.

### 2.2 Non-Goals
- Preserving provider-specific label semantics as local folders (e.g. Gmail labels).
- Building a full MUA (mail client).
- Fully automated destructive deletion from Gmail (supported as a workflow, but gated and preferably manual/UI-driven).

## 3. Selected Architecture
### 3.1 Canonical mailbox source
The set of IMAP folders to sync is **configurable**.

Defaults should be conservative:
- For most IMAP providers: sync a user-configured list of folders (often `INBOX`, `Sent`, `Archive`, etc.).
- For Gmail: use the Gmail profile guidance to avoid duplicates.

Gmail profile (dedupe) sync set:
- `[Gmail]/All Mail` (primary)
- optionally `[Gmail]/Drafts`, `[Gmail]/Spam`, `[Gmail]/Trash`

Do not sync `INBOX` or label folders under Gmail.

### 3.2 Data model
- Canonical archive storage: Maildir on disk.
- Index: notmuch database under the user’s notmuch config.
- State: local state directory for the orchestrator (verification reports, run logs, optional snapshots of counts).

## 4. Deliverables
This repo should provide:
- An `email-archiver` CLI.
- Templates/examples:
  - `config.toml` (single unified config; mbsync/notmuch configs are auto-generated)
  - `systemd --user` service + timer
- A verification report format and storage location.
- Documentation for setup and operations.

## 5. Implementation Language
### Recommendation: Python 3
Python is a good fit because it can:
- run external commands reliably (`subprocess`),
- parse/structure verification output,
- manage config files and paths,
- be packaged as a small CLI with low friction.

Alternatives:
- Shell scripts: simplest, but tends to become brittle as verification/reporting grows.
- Go/Rust: very robust binaries, but slower iteration for “glue/orchestration” tasks.

## 6. Interfaces

### 6.1 CLI interface
The CLI MUST be idempotent (safe to re-run) and return non-zero exit codes on failure.

Proposed command surface:
- `email-archiver sync`
  - Runs `mbsync` for configured accounts/channels.
- `email-archiver index`
  - Runs `notmuch new`.
- `email-archiver verify`
  - Runs a set of checks and writes a verification report artifact.
- `email-archiver backup`
  - Invokes the chosen backup tool or a user-provided command.
- `email-archiver run`
  - Convenience: `sync` → `index` → `verify` (and optionally `backup`).
- `email-archiver doctor`
  - Validates prerequisites: binaries installed, permissions, configs readable, maildir exists.

Optional flags (common to multiple commands):
- `--config <path>`
- `--account <name>`
- `--dry-run` (where meaningful; never for destructive operations)
- `--verbose`

### 6.2 Configuration file interface
The project uses a **single** config file. mbsync and notmuch configs are **auto-generated** at runtime from this file — users never maintain separate `mbsyncrc` or `notmuch-config` files.

Recommended format: **TOML** (easy to read, supports nested settings).

Proposed config: `~/.config/email-archiver/config.toml`

#### Password handling
The IMAP password is provided **exclusively** via a file mounted at `/run/secrets/imap_password`. No environment variables or command-line options are used for secrets. In containers, this is a bind mount or Docker/Podman secret; on bare metal, symlink or write the file directly.

#### Auto-generated configs
On each run, the tool writes generated `mbsyncrc` and `notmuch-config` files to `<state_dir>/generated/`. The notmuch database is auto-initialized (via `notmuch new`) if it does not yet exist.

Example:
```toml
[account.primary]
email = "user@example.com"
imap_host = "imap.example.com"
imap_user = "user@example.com"
tls_type = "IMAPS"              # IMAPS, STARTTLS, or None
folders = ["INBOX", "Archive", "Sent"]
# Gmail note: use ["[Gmail]/All Mail"] to avoid duplicates.

[paths]
maildir_root = "~/Mail/imap"
state_dir = "~/.local/state/email-archiver"
# logs_dir, verification_dir, generated_config_dir default to state_dir subdirs

[backup]
# one of: "restic", "borg", "rsync", "command"
mode = "command"
command = "restic backup ~/Mail/imap"

[orchestration]
# if true, `run` will call backup after verify succeeds
backup_after_verify = true
```

### 6.3 Filesystem layout
Within `maildir_root`, the tool SHOULD create a stable structure, for example:
- `~/Mail/imap/<account>/inbox/` (Maildir)
- `~/Mail/imap/<account>/sent/` (Maildir)

For Gmail profile:
- `~/Mail/imap/<account>/all-mail/` (Maildir)
- `~/Mail/imap/<account>/drafts/` (optional)

State/artifacts:
- `~/.local/state/email-archiver/verification/<account>/<timestamp>.json`
- `~/.local/state/email-archiver/logs/<account>/<timestamp>.log`

### 6.4 Verification report interface
The tool SHOULD write a machine-readable report (JSON) and a human-readable summary (text).

Minimum JSON fields:
- `timestamp`
- `account`
- `mbsync`: exit code, stderr summary, last run duration
- `notmuch`: database path/config, total message count
- `coverage`: oldest/newest message dates seen locally
- `status`: `PASS`/`FAIL`

### 6.5 systemd orchestration interface
Provide templates under repo control (installed/linked by the user) for user units:
- `email-archiver-run.service` (runs `email-archiver run`)
- `email-archiver-run.timer` (schedules it)

The service should:
- run as the user,
- set a safe `PATH` (or call absolute paths),
- write logs to journald.

## 7. Security Requirements
- Secrets must not be stored in repo.
- The IMAP password is provided **only** via a file at `/run/secrets/imap_password`.
- No environment variables or CLI flags are used for password passing.
- Prefer IMAPS/TLS.
- Recommend encryption at rest for laptops / removable media.

## 8. Operational Requirements
- All operations must be resumable.
- `sync` and `index` are safe to run repeatedly.
- `verify` must fail closed (if checks can’t run, it should not report PASS).

## 9. Testing / Validation
- Unit tests for config parsing, path expansion, verification report formatting.
- Integration tests (optional) that mock command execution.
- “Doctor” command to validate local prerequisites.
