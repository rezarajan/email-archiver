FROM python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive

# Core: mbsync (isync), notmuch, TLS certs
# Backup tools: restic, borgbackup, rsync
# Credential helpers: pass, gnupg (for PassCmd in mbsyncrc)
# Utilities: jq (JSON report inspection)
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    isync \
    notmuch \
    ca-certificates \
    jq \
    pass \
    gnupg \
    restic \
    borgbackup \
    rsync \
  && rm -rf /var/lib/apt/lists/*

# Create a non-root user with fixed IDs
# Permission handling is done via entrypoint fixup (see entrypoint.sh)
RUN groupadd -g 1000 archiver \
  && useradd -m -u 1000 -g archiver archiver

COPY . /opt/email-archiver
RUN pip install --no-cache-dir /opt/email-archiver \
  && cp /opt/email-archiver/scripts/scheduler.sh /usr/local/bin/scheduler \
  && chmod +x /usr/local/bin/scheduler \
  && rm -rf /opt/email-archiver

# Run as non-root user
USER archiver
WORKDIR /home/archiver

ENTRYPOINT ["email-archiver"]
CMD ["--help"]
