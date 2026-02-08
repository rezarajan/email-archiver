# ===========================================================================
#  Stage 1: builder — install the Python package into an isolated root
# ===========================================================================
FROM python:3.12-slim AS builder

COPY . /src
RUN pip install --no-cache-dir --root=/install /src

# ===========================================================================
#  Stage 2: runtime — minimal image with only what we need
# ===========================================================================
FROM python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive

# Only the packages email-archiver directly invokes at runtime:
#   isync    — provides mbsync (IMAP → Maildir sync)
#   notmuch  — mail indexing / search
#   ca-certificates — TLS root certs for IMAPS connections
#
# Backup tools (restic, borgbackup, rsync, …) are NOT included to keep the
# image small.  If your [backup] command needs them, extend this image:
#   FROM ghcr.io/<you>/email-archiver
#   RUN apt-get update && apt-get install -y --no-install-recommends restic
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    isync \
    notmuch \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Copy the installed Python package + console script from the builder
COPY --from=builder /install /

# Scheduler helper for the compose "scheduler" service
COPY scripts/scheduler.sh /usr/local/bin/scheduler

# Create a non-root user with fixed IDs
RUN chmod +x /usr/local/bin/scheduler \
  && groupadd -g 1000 archiver \
  && useradd -m -u 1000 -g archiver archiver

USER archiver
WORKDIR /home/archiver

ENTRYPOINT ["email-archiver"]
CMD ["--help"]
