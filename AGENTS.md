# AGENTS.md

This repository is the start of a small “email archiver” system intended to export an **IMAP** mailbox (Gmail included) to local Linux storage, index it for fast search, and support safe deletion from the remote server after verification.

If you are an automated coding agent working in this repo, use this as your operating context.

## Canonical project docs
- `OVERVIEW.md`: requirements, selected approach, and operational/orchestration expectations.
- `SPEC.md`: interfaces (CLI/config/filesystem/systemd/templates), security requirements.
- `PLAN.md`: build steps checklist for implementation.

## Problem statement (from OVERVIEW)
- Export **all emails** from an IMAP account.
- Store locally in a **portable, open** format.
- Avoid duplicates where provider semantics can create them.
- Support **resumable** sync.
- Provide **local full-text search**.
- Only delete from the remote server after **verification** and **backup**.

## Selected approach
- IMAP → **Maildir** using `mbsync` (isync)
- Index/search using `notmuch`
- Secondary backup via `restic`/`borg`/`rsync` (user choice)

### Provider folder semantics (dedupe)
IMAP servers differ:
- Many providers store a message in exactly one folder.
- Some providers (notably Gmail) expose labels as IMAP folders, which can cause duplicates if multiple folders are synced.

Gmail profile guidance (dedupe):
- Sync `[Gmail]/All Mail` as canonical
- Do NOT sync `INBOX` or label folders
- Optionally sync `[Gmail]/Drafts`, `[Gmail]/Spam`, `[Gmail]/Trash`

## Safety model (critical)
- Deletion is **gated** behind:
  1) successful sync + index
  2) a PASS verification report
  3) a successful secondary backup
- Prefer deleting via the provider UI for initial destructive operations.
- Do not introduce automation that can delete from the server without explicit, high-friction confirmation.

## Orchestration expectations
The repo should provide a CLI wrapper that orchestrates:
- `sync`: run `mbsync`
- `index`: run `notmuch new`
- `verify`: produce an auditable verification artifact (JSON + text)
- `backup`: run configured backup command
- `run`: `sync` → `index` → `verify` → (optional) `backup`
- `doctor`: validate prerequisites and config/paths

Scheduling target:
- Provide `systemd --user` unit templates (`.service` + `.timer`) to run `run` periodically.

## Interfaces (from SPEC)
- CLI name: `email-archiver`
- Orchestration config: `~/.config/email-archiver/config.toml` (TOML)
- Suggested implementation language: **Python 3**
- State artifacts under `~/.local/state/email-archiver/` (logs + verification reports)

Verification reports MUST:
- be machine readable (JSON)
- record timestamp, account, command exit codes, message counts, and oldest/newest coverage
- fail closed (if checks cannot run, status is FAIL)

## Contribution guidelines for agents
- Keep changes aligned with `PLAN.md`.
- Prefer small, testable modules (config parsing, subprocess runner, report generation).
- Never hardcode or commit secrets. Encourage `mbsync` `PassCmd` patterns.
- Maintain idempotency: `sync`, `index`, `verify`, `backup` are safe to re-run.
- Do not change the Gmail profile dedupe strategy (All Mail only) unless explicitly requested.
