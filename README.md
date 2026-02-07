# email-archiver

Archive IMAP mailboxes (including Gmail) to local Maildir, index for full-text search, and verify before deleting from the server.

You only need **one config file** (`config.toml`). mbsync and notmuch configs are generated automatically. The IMAP password is provided via a file at `/run/secrets/imap_password` — no env vars, no GPG.

## Quick Start (Docker / Podman)

This is the recommended way to run email-archiver.

### 1. Create directories and config

```bash
mkdir -p ~/.config/email-archiver ~/Mail/imap ~/.local/state/email-archiver
cp examples/config.toml ~/.config/email-archiver/config.toml
```

Edit `~/.config/email-archiver/config.toml`:

```toml
[account.primary]
email = "you@example.com"
imap_host = "imap.example.com"
imap_user = "you@example.com"
tls_type = "IMAPS"
folders = ["INBOX", "Archive", "Sent"]
# Gmail: use folders = ["[Gmail]/All Mail"] to avoid duplicates

[paths]
maildir_root = "/home/archiver/Mail/imap"      # container path
state_dir = "/home/archiver/.local/state/email-archiver"

[backup]
command = "restic backup /home/archiver/Mail/imap"

[orchestration]
backup_after_verify = true
```

### 2. Create the password file

```bash
echo -n 'your-app-password' > ~/.config/email-archiver/imap_password
chmod 600 ~/.config/email-archiver/imap_password
```

### 3. Build and run

```bash
# Build
docker build -t email-archiver .

# Check prerequisites
docker run --rm \
  -v ~/.config/email-archiver:/home/archiver/.config/email-archiver:ro \
  -v ~/.config/email-archiver/imap_password:/run/secrets/imap_password:ro \
  -v ~/Mail/imap:/home/archiver/Mail/imap \
  -v ~/.local/state/email-archiver:/home/archiver/.local/state/email-archiver \
  email-archiver doctor

# Full pipeline
docker run --rm \
  -v ~/.config/email-archiver:/home/archiver/.config/email-archiver:ro \
  -v ~/.config/email-archiver/imap_password:/run/secrets/imap_password:ro \
  -v ~/Mail/imap:/home/archiver/Mail/imap \
  -v ~/.local/state/email-archiver:/home/archiver/.local/state/email-archiver \
  email-archiver run
```

> Replace `docker` with `podman` for rootless containers. Add `--userns=keep-id` with Podman.

### Shell alias (optional)

```bash
alias email-archiver='docker run --rm \
  -v ~/.config/email-archiver:/home/archiver/.config/email-archiver:ro \
  -v ~/.config/email-archiver/imap_password:/run/secrets/imap_password:ro \
  -v ~/Mail/imap:/home/archiver/Mail/imap \
  -v ~/.local/state/email-archiver:/home/archiver/.local/state/email-archiver \
  email-archiver'
```

Then: `email-archiver run`, `email-archiver verify`, etc.

### Docker Compose

A compose file is at `docker/docker-compose.yml` with two services:

- **cli** — one-shot commands (`docker compose run --rm cli doctor`)
- **scheduler** — runs `email-archiver run` on a timer (default: hourly)

Set paths in a `.env` file:

```bash
CONFIG_PATH=~/.config/email-archiver
DATA_PATH=~/Mail/imap
STATE_PATH=~/.local/state/email-archiver
PASSWORD_FILE=~/.config/email-archiver/imap_password
SCHEDULE_INTERVAL=3600
```

```bash
docker compose -f docker/docker-compose.yml run --rm cli doctor
docker compose -f docker/docker-compose.yml up -d scheduler
```

## Quick Start (native install)

### Prerequisites

```bash
# Arch Linux
sudo pacman -S isync notmuch

# Debian/Ubuntu
sudo apt install isync notmuch
```

Optional backup tool: `restic`, `borg`, or `rsync`.

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Configure

```bash
mkdir -p ~/.config/email-archiver
cp examples/config.toml ~/.config/email-archiver/config.toml
# Edit: account details, folders, paths, backup command
```

Create the password file:

```bash
echo -n 'your-app-password' > /run/secrets/imap_password
# Or symlink: ln -s ~/.config/email-archiver/imap_password /run/secrets/imap_password
```

### Run

```bash
email-archiver doctor   # validate setup
email-archiver run      # sync → index → verify → backup
```

## Commands

- **`sync`** — Run mbsync to download IMAP → Maildir
- **`index`** — Run `notmuch new` to index the Maildir (auto-initializes on first run)
- **`verify`** — Check message counts and date coverage, write JSON + text report
- **`backup`** — Run the configured backup command
- **`run`** — Orchestrated pipeline: sync → index → verify → (optional) backup
- **`doctor`** — Validate prerequisites, config, paths, and password file

### Flags

- `--config PATH` / `-c` — Override config file
- `--account NAME` / `-a` — Target a specific account
- `--verbose` / `-v` — Verbose output
- `--dry-run` — Show what would run without executing

## Configuration

Everything is in a single `config.toml`. See [`examples/config.toml`](examples/config.toml) for the full reference.

```toml
[account.primary]
email = "you@example.com"
imap_host = "imap.example.com"
imap_user = "you@example.com"
tls_type = "IMAPS"                     # IMAPS, STARTTLS, or None
folders = ["INBOX", "Archive", "Sent"]  # which IMAP folders to sync

[paths]
maildir_root = "~/Mail/imap"
state_dir = "~/.local/state/email-archiver"

[backup]
command = "restic backup ~/Mail/imap"

[orchestration]
backup_after_verify = true
```

**What gets auto-generated:** mbsync config, notmuch config, and the notmuch database (on first run). These are written to `<state_dir>/generated/`.

**Password:** Always read from `/run/secrets/imap_password`. In containers this is a bind mount; on bare metal, write or symlink the file.

## Scheduling

### systemd (native)

```bash
cp systemd/email-archiver-run.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now email-archiver-run.timer
```

### Docker Compose (container)

The `scheduler` service in `docker/docker-compose.yml` runs on a loop. Set `SCHEDULE_INTERVAL` in your `.env`.

## Verification & Safety

Each `verify` writes a JSON and text report to `<state_dir>/verification/<account>/`. Reports include timestamp, message count, date coverage, and PASS/FAIL status. Verification **fails closed** — if checks can't run, the result is FAIL.

Deletion from the remote server is **not automated**. The recommended workflow:

1. Run `email-archiver run` until verification consistently passes
2. Confirm backup on secondary storage
3. Delete from the provider UI (Gmail web, etc.)

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
```

All tasks use the Makefile:

```bash
make test            # pytest
make lint            # ruff
make check           # lint + test
make build           # build container image
make test-docker     # container integration tests
make test-all        # everything
make help            # full list
```

## License

MIT
