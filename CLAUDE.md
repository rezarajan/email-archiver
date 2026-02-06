# CLAUDE.md

You are working in the `email-archiver` repository.

## Read this first (single source of requirements)
- `AGENTS.md` contains the **non-negotiable requirements**, safety constraints, and expected interfaces.

Other canonical docs:
- `OVERVIEW.md`: problem statement, background, and operational/orchestration notes.
- `SPEC.md`: interfaces (CLI/config/templates/systemd) and artifact formats.
- `PLAN.md`: implementation checklist (keep it updated as work lands).

## Project overview
`email-archiver` is a CLI-first tool to archive an **IMAP** mailbox to local storage in **Maildir** format, index it for fast local search, generate verification artifacts, and support a safe workflow for deleting mail from the remote server after verification + backup.

This is designed to work with **any IMAP provider**. Gmail is supported as a first-class *profile* (with Gmail-specific folder semantics and dedupe guidance).

## Tech stack
- Sync engine: `mbsync` (from `isync`) IMAP → Maildir
- Index/search: `notmuch`
- Orchestration wrapper: Python 3 CLI (planned)
- Scheduling: `systemd --user` (templates planned)
- Backup: user-selected (`restic`/`borg`/`rsync` or arbitrary command)

## Architecture notes (high level)
- IMAP server → `mbsync` → local Maildir
- Maildir → `notmuch new` → local index
- Orchestrator writes logs + verification artifacts to a state directory
- Backup runs only after verification succeeds
- Destructive deletion remains gated and intentionally high-friction

## Build / test commands (expected once scaffolding is added)
These are the intended repo-local commands once Python packaging and tests land:
- Create venv + install in editable mode: `python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'`
- Run tests: `pytest`
- Run formatting/linting (if added): `ruff check .` / `ruff format .`

If the repo doesn’t include these yet, add them as part of `PLAN.md` step 1 (scaffolding).
