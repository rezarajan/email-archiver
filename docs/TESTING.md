# Testing Summary

## Design Principles

1. **No hardcoded UID/GID** — Container runs as archiver (UID 1000) internally
2. **No permission fixing** — Container never runs as root or modifies file ownership
3. **Single config file** — Only `config.toml` is needed; mbsync/notmuch configs are auto-generated
4. **Secret via file** — Password provided exclusively via `/run/secrets/imap_password`
5. **Rootless compatible** — Works with podman's `--userns=keep-id`
6. **Minimal image** — Multi-stage build; only core runtime deps shipped
7. **Multi-arch** — Built for `linux/amd64` and `linux/arm64`

## Unit Tests

All 52 unit tests passing:

```
tests/test_config.py     - Config loading, validation, defaults, path expansion
tests/test_runner.py     - Subprocess runner, timeout, error handling
tests/test_verify.py     - Report building, writing, fail-closed semantics
tests/test_cli.py        - Argument parsing, subcommand dispatch, dry-run modes
tests/test_generate.py   - mbsyncrc generation, notmuch config generation, sanitize, idempotency
```

## Container Tests

All container tests passing (via `make test-docker`):

```
✅ test-version  - Container runs and reports version
✅ test-doctor   - All prerequisite checks pass
✅ test-config   - Config file readable from mounted volume
✅ test-write    - Data and state volumes writable
```

## CI Pipeline

Defined in `.github/workflows/ci.yml`. Three jobs:

1. **test** — Runs on every push and PR. Installs Python 3.12, runs `ruff check`, `ruff format --check`, and `pytest`.
2. **build** — Runs on push to `main` or version tags (`v*`), after `test` passes. Uses a matrix strategy with one runner per platform:
   - `linux/amd64` on `ubuntu-latest`
   - `linux/arm64` on `ubuntu-24.04-arm` (native ARM runner)
   Each runner builds the image and pushes a single-platform digest to GHCR.
3. **merge** — Downloads both platform digests and creates a unified multi-arch manifest list on GHCR.

Image tags:
- Push to `main` → `:main`
- Tag `v1.2.3` → `:1.2.3`, `:1.2`

No secrets to configure — the workflow uses `GITHUB_TOKEN` (automatic) to authenticate with GHCR.

## Container Architecture

### Multi-stage build

The Dockerfile uses two stages to keep the runtime image minimal:

1. **builder** (`python:3.12-slim`) — copies source and runs `pip install --root=/install`. This stage is discarded.
2. **runtime** (`python:3.12-slim`) — installs only three system packages (`isync`, `notmuch`, `ca-certificates`), then copies the pre-built Python package from the builder. No pip, setuptools, or source code in the final image.

Backup tools (restic, borgbackup, rsync, …) are **not** included. If your `[backup]` command needs them, extend the image:

```dockerfile
FROM ghcr.io/<owner>/email-archiver
USER root
RUN apt-get update && apt-get install -y --no-install-recommends restic && rm -rf /var/lib/apt/lists/*
USER archiver
```

### Runtime layout

- **User**: `archiver` (UID 1000), non-root
- **Platforms**: `linux/amd64`, `linux/arm64`
- **Volumes**:
  - `/home/archiver/.config` (read-only) — Only `email-archiver/config.toml`
  - `/home/archiver/Mail/imap` (read-write) — Mail data
  - `/home/archiver/.local/state/email-archiver` (read-write) — State/logs/generated configs
  - `/run/secrets/imap_password` (read-only) — IMAP password file
- **Runtime**: Uses `--userns=keep-id` for proper file ownership mapping with Podman

## Kubernetes Compatibility

The compose design translates directly to K8s:

```yaml
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
  volumes:
    - name: config
      configMap:
        name: email-archiver-config
    - name: data
      persistentVolumeClaim:
        claimName: email-archiver-data
    - name: imap-password
      secret:
        secretName: email-archiver-imap-password
```

No changes needed to the container image.

## Doctor Output

```
Checking prerequisites...
Checking secrets...
Checking paths...

  OK  mbsync found at /usr/bin/mbsync
  OK  notmuch found at /usr/bin/notmuch
  OK  password file: /run/secrets/imap_password
  OK  maildir_root: /home/archiver/Mail/imap
  OK  state_dir: /home/archiver/.local/state/email-archiver
  WARN  logs_dir does not exist yet (parent exists): ...
  WARN  verification_dir does not exist yet (parent exists): ...
  WARN  generated_config_dir does not exist yet (parent exists): ...

All checks passed.
```

Warnings are expected on first run — directories are created automatically.
