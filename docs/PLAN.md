# PLAN: Build Email Archiver

This plan describes how to build the proposed orchestration tool and supporting artifacts (templates, units, docs) described in `OVERVIEW.md` and specified in `SPEC.md`.

## 0. Decisions (lock these early)
- Implementation language: **Python 3** (see `SPEC.md`)
- Config format: **TOML**
- Packaging: installable CLI (`email-archiver`) via standard Python packaging
- Scheduling: `systemd --user` service + timer templates

## 1. Repository scaffolding
- [x] Add minimal repo structure (e.g. `src/`, `tests/`, `examples/`, `systemd/`).
- [x] Add Python packaging (`pyproject.toml`) and an entrypoint script (`email-archiver`).
- [x] Add a README that explains installation, prerequisites, and safety model.

## 2. Prerequisites and environment checks
- [x] Implement `email-archiver doctor`.
  - [x] Check required binaries exist (`mbsync`, `notmuch`, selected backup tool).
  - [x] Validate config file is readable and parseable.
  - [x] Validate target paths exist (or can be created).
  - [x] Validate permissions on sensitive files (warn if too permissive).

## 3. Configuration system
- [x] Implement config loader for `~/.config/email-archiver/config.toml` with:
  - [x] `~` expansion and env var expansion.
  - [x] schema validation with clear error messages.
  - [x] ability to override config path via `--config`.
- [x] Document config in `SPEC.md` and provide a sample under `examples/config.toml`.

## 4. Command execution layer
- [x] Implement a small, testable wrapper around `subprocess`:
  - [x] capture stdout/stderr, duration, exit code.
  - [x] optional streaming output for interactive use.
  - [x] deterministic error formatting.

## 5. Implement core commands
### 5.1 Sync
- [x] Implement `email-archiver sync`:
  - [x] run `mbsync` (group or account-specific invocation).
  - [x] record a run log artifact.

### 5.2 Index
- [x] Implement `email-archiver index`:
  - [x] run `notmuch new`.
  - [x] record counts before/after if available.

### 5.3 Verify
- [x] Implement `email-archiver verify`:
  - [x] compute local `notmuch count '*'`.
  - [x] compute oldest/newest message timestamps (e.g. via `notmuch search --sort=oldest-first` / `--sort=newest-first`).
  - [x] optionally spot-check a few queries.
  - [x] write JSON + text summary verification reports.
  - [x] fail closed: if checks cannot run, verification is FAIL.

### 5.4 Backup
- [x] Implement `email-archiver backup`:
  - [x] run configured backup command/tool.
  - [x] record success/failure and output.

### 5.5 Run (orchestrated)
- [x] Implement `email-archiver run`:
  - [x] `sync` → `index` → `verify`.
  - [x] if verify PASS and configured, run `backup`.
  - [x] ensure failures short-circuit later steps.

## 6. Template artifacts
- [x] Add `examples/config.toml` (unified config; mbsync/notmuch configs are auto-generated).
- [x] Add `systemd/email-archiver-run.service` template.
- [x] Add `systemd/email-archiver-run.timer` template.

## 6b. Config consolidation refactor
- [x] Move all IMAP/sync/index settings into `[account.*]` sections (`folders`, `ssl_type`).
- [x] Remove `[mbsync]` and `[notmuch]` config sections.
- [x] Auto-generate `mbsyncrc` and `notmuch-config` at runtime from `config.toml`.
- [x] Auto-initialize notmuch database idempotently before first use.
- [x] Password provided exclusively via file at `/run/secrets/imap_password`.
- [x] Remove `examples/mbsyncrc` and `examples/notmuch-config`.
- [x] Update Docker/compose to use secret file mount instead of env var.
- [x] Update all tests and test fixtures.

## 7. Documentation and runbooks
- [x] Update `OVERVIEW.md` if implementation details evolve.
- [x] Create `README.md`:
  - [x] prerequisites install instructions.
  - [x] step-by-step setup.
  - [x] recommended `systemd --user` enablement.
  - [x] verification + deletion safety workflow.

## 8. Testing
- [x] Add unit tests for:
  - [x] config parsing/validation.
  - [x] command runner.
  - [x] verification report formatting.
- [x] Add mocked integration tests that simulate command outputs.

## 9. Release / operations
- [x] Add a versioning scheme.
- [ ] Add a changelog.
- [x] Confirm the tool can be installed and run on a clean Linux machine.

## 10. Explicit non-automation of deletion
- [x] Document the deletion procedure clearly.
- [ ] If a deletion helper is ever added, require:
  - [ ] explicit `--i-understand-this-deletes-from-server` style confirmation.
  - [ ] a required recent PASS verification artifact.
  - [ ] a required recent successful backup artifact.
