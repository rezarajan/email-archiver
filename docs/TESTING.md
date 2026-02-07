# Testing Summary

## Design Principles

1. **No hardcoded UID/GID** - Container runs as archiver (UID 1000) internally
2. **No permission fixing** - Container never runs as root or modifies file ownership
3. **Single config file** - Only `config.toml` is needed; mbsync/notmuch configs are auto-generated
4. **Secret via file** - Password provided exclusively via `/run/secrets/imap_password`
5. **Rootless compatible** - Works with podman's `--userns=keep-id`
6. **Production ready** - Same pattern works in Docker, Podman, and Kubernetes

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

All container tests passing (via `make test-all`):

```
✅ test-version  - Container runs and reports version
✅ test-doctor   - All prerequisite checks pass
✅ test-config   - Config file readable from mounted volume
✅ test-write    - Data and state volumes writable
```

## Container Architecture

- **Image**: Fixed UID 1000 (archiver user), runs non-root
- **Volumes**:
  - `/home/archiver/.config` (read-only) - Only `email-archiver/config.toml`
  - `/home/archiver/Mail/imap` (read-write) - Mail data
  - `/home/archiver/.local/state/email-archiver` (read-write) - State/logs/generated configs
  - `/run/secrets/imap_password` (read-only) - IMAP password file
- **Runtime**: Uses `--userns=keep-id` for proper file ownership mapping

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

Warnings are expected on first run - directories are created automatically.
