# PLAN: Build Email Archiver

This plan describes how to build the proposed orchestration tool and supporting artifacts (templates, units, docs) described in `OVERVIEW.md` and specified in `SPEC.md`.

## 0. Decisions (lock these early)
- Implementation language: **Python 3** (see `SPEC.md`)
- Config format: **TOML**
- Packaging: installable CLI (`email-archiver`) via standard Python packaging
- Scheduling: `systemd --user` service + timer templates

## 1. Repository scaffolding
- [ ] Add minimal repo structure (e.g. `src/`, `tests/`, `examples/`, `systemd/`).
- [ ] Add Python packaging (`pyproject.toml`) and an entrypoint script (`email-archiver`).
- [ ] Add a README that explains installation, prerequisites, and safety model.

## 2. Prerequisites and environment checks
- [ ] Implement `email-archiver doctor`.
  - [ ] Check required binaries exist (`mbsync`, `notmuch`, selected backup tool).
  - [ ] Validate config file is readable and parseable.
  - [ ] Validate target paths exist (or can be created).
  - [ ] Validate permissions on sensitive files (warn if too permissive).

## 3. Configuration system
- [ ] Implement config loader for `~/.config/email-archiver/config.toml` with:
  - [ ] `~` expansion and env var expansion.
  - [ ] schema validation with clear error messages.
  - [ ] ability to override config path via `--config`.
- [ ] Document config in `SPEC.md` and provide a sample under `examples/config.toml`.

## 4. Command execution layer
- [ ] Implement a small, testable wrapper around `subprocess`:
  - [ ] capture stdout/stderr, duration, exit code.
  - [ ] optional streaming output for interactive use.
  - [ ] deterministic error formatting.

## 5. Implement core commands
### 5.1 Sync
- [ ] Implement `email-archiver sync`:
  - [ ] run `mbsync` (group or account-specific invocation).
  - [ ] record a run log artifact.

### 5.2 Index
- [ ] Implement `email-archiver index`:
  - [ ] run `notmuch new`.
  - [ ] record counts before/after if available.

### 5.3 Verify
- [ ] Implement `email-archiver verify`:
  - [ ] compute local `notmuch count '*'`.
  - [ ] compute oldest/newest message timestamps (e.g. via `notmuch search --sort=oldest-first` / `--sort=newest-first`).
  - [ ] optionally spot-check a few queries.
  - [ ] write JSON + text summary verification reports.
  - [ ] fail closed: if checks cannot run, verification is FAIL.

### 5.4 Backup
- [ ] Implement `email-archiver backup`:
  - [ ] run configured backup command/tool.
  - [ ] record success/failure and output.

### 5.5 Run (orchestrated)
- [ ] Implement `email-archiver run`:
  - [ ] `sync` → `index` → `verify`.
  - [ ] if verify PASS and configured, run `backup`.
  - [ ] ensure failures short-circuit later steps.

## 6. Template artifacts
- [ ] Add `examples/mbsyncrc` template:
  - [ ] includes canonical folder selection (All Mail + optional special folders).
  - [ ] includes `PassCmd` example (without embedding a secret).
- [ ] Add `examples/notmuch-config` template.
- [ ] Add `systemd/email-archiver-run.service` template.
- [ ] Add `systemd/email-archiver-run.timer` template.

## 7. Documentation and runbooks
- [ ] Update `OVERVIEW.md` if implementation details evolve.
- [ ] Create `README.md`:
  - [ ] prerequisites install instructions.
  - [ ] step-by-step setup.
  - [ ] recommended `systemd --user` enablement.
  - [ ] verification + deletion safety workflow.

## 8. Testing
- [ ] Add unit tests for:
  - [ ] config parsing/validation.
  - [ ] command runner.
  - [ ] verification report formatting.
- [ ] Add mocked integration tests that simulate command outputs.

## 9. Release / operations
- [ ] Add a versioning scheme.
- [ ] Add a changelog.
- [ ] Confirm the tool can be installed and run on a clean Linux machine.

## 10. Explicit non-automation of deletion
- [ ] Document the deletion procedure clearly.
- [ ] If a deletion helper is ever added, require:
  - [ ] explicit `--i-understand-this-deletes-from-server` style confirmation.
  - [ ] a required recent PASS verification artifact.
  - [ ] a required recent successful backup artifact.
