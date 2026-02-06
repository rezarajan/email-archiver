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

# Create a non-root user whose UID/GID can be overridden at build time
# so that bind-mounted files keep the host user's ownership.
ARG UID=1000
ARG GID=1000
RUN groupadd -g "${GID}" archiver \
  && useradd -m -u "${UID}" -g archiver archiver

COPY . /opt/email-archiver
RUN pip install --no-cache-dir /opt/email-archiver \
  && cp /opt/email-archiver/scripts/scheduler.sh /usr/local/bin/scheduler \
  && chmod +x /usr/local/bin/scheduler \
  && rm -rf /opt/email-archiver

USER archiver
WORKDIR /home/archiver

ENTRYPOINT ["email-archiver"]
CMD ["--help"]
