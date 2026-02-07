# Test Compose Setup

This directory contains a minimal working configuration for testing email-archiver with Docker Compose.

## Structure

```
test-compose/
├── config/
│   ├── email-archiver/
│   │   └── config.toml          # App configuration
│   ├── isync/
│   │   └── mbsyncrc             # mbsync configuration
│   └── notmuch-config           # notmuch configuration
├── data/                        # Maildir storage (mounted read-write)
├── state/                       # State/logs/verification (mounted read-write)
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
- `IMAP_PASSWORD` - IMAP password (default: `test-password-12345`)
- `PUID/PGID` - User/group ID for file ownership (default: `1000`)
- `SCHEDULE_INTERVAL` - Seconds between runs (default: `3600`)

## Testing Permissions

```bash
# Test write access
docker compose run --rm cli --entrypoint /bin/sh -c "touch /home/archiver/Mail/imap/test && rm /home/archiver/Mail/imap/test && echo OK"

# Test config read
docker compose run --rm cli --entrypoint /bin/sh -c "cat /home/archiver/.config/email-archiver/config.toml | head -3"
```

## Notes

- The image runs as UID/GID 1000 by default (configurable via `PUID/PGID`)
- Config is mounted read-only, data and state are read-write
- All paths are externalized via environment variables
- This setup works identically in Kubernetes with ConfigMaps and PersistentVolumeClaims
