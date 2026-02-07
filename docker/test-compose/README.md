# Test Compose Setup

This directory contains a minimal working configuration for testing email-archiver with Docker Compose.

## Structure

```
test-compose/
├── config/
│   └── email-archiver/
│       └── config.toml          # Single unified config (mbsync/notmuch auto-generated)
├── secrets/
│   └── imap_password            # IMAP password file (mounted at /run/secrets/imap_password)
├── data/                        # Maildir storage (mounted read-write)
├── state/                       # State/logs/verification/generated configs (mounted read-write)
├── .env                         # Environment variables
└── docker-compose.yml           # Compose configuration
```

## Quick Start

### Using Makefile (Recommended)

```bash
# Run all tests
make test-all

# Or run individual tests
make test-doctor    # Check prerequisites
make test-write     # Test write permissions
make test-config    # Test config reading
make test-version   # Test --version

# Clean up
make clean
```

### Using docker-compose (Deprecated due to podman limitations)

The compose file has limitations with rootless podman. Use the Makefile instead.

```bash
# Build the image
docker compose build

# Run doctor check
docker compose run --rm cli doctor
```

## Configuration

All configuration is in `.env`:

- `CONFIG_PATH` - Path to config directory (default: `./config`)
- `DATA_PATH` - Path to mail data (default: `./data`)
- `STATE_PATH` - Path to state/logs (default: `./state`)
- `PASSWORD_FILE` - Path to IMAP password file (default: `./secrets/imap_password`)
- `SCHEDULE_INTERVAL` - Seconds between runs (default: `3600`)

## Notes

- Only `config.toml` is needed — mbsync and notmuch configs are auto-generated
- Password is provided via a file mount at `/run/secrets/imap_password` (never via env vars)
- The image runs as UID/GID 1000 by default
- Config is mounted read-only, data and state are read-write
- This setup works identically in Kubernetes with ConfigMaps, PVCs, and Secrets
