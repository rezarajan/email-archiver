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

## Development environment (container)
A repeatable dev/runtime environment is provided via `Dockerfile.warp-env` (system packages + global tools only).

Current contents:
- base: `warpdotdev/dev-base:1`
- installs: `isync` (mbsync), `notmuch`, `jq`

## Architecture notes (high level)
- IMAP server → `mbsync` → local Maildir
- Maildir → `notmuch new` → local index
- Orchestrator writes logs + verification artifacts to a state directory
- Backup runs only after verification succeeds
- Destructive deletion remains gated and intentionally high-friction

## Build / test commands

All tasks are exposed via the root Makefile:

```bash
# Python checks (runs inside .venv)
make check           # lint + format-check + test (run this before every commit)
make test            # pytest unit tests only
make lint            # ruff linter only
make format-check    # ruff format check only

# Container
make build           # build the email-archiver image
make test-docker     # container smoke tests
make test-all        # everything: Python + container
```

**IMPORTANT**: Always run `make check` after making code changes. This runs lint, format-check, and all 52 unit tests. The CI pipeline runs the same checks on every push.
