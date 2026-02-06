#!/bin/sh
# Scheduler entrypoint for running email-archiver periodically inside a
# container.  Intended to be used as the entrypoint in docker-compose.yml.
#
# Environment variables:
#   SCHEDULE_INTERVAL  – seconds between runs (default: 3600 = 1 hour)
#   ARCHIVER_ARGS      – extra arguments passed to email-archiver run
#                        (e.g. "--verbose" or "--account primary")

set -u

INTERVAL="${SCHEDULE_INTERVAL:-3600}"

echo "email-archiver scheduler starting (interval=${INTERVAL}s)"

while true; do
    echo "--- $(date -Iseconds) --- starting email-archiver run ${ARCHIVER_ARGS:-} ---"
    email-archiver run ${ARCHIVER_ARGS:-}
    rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "email-archiver run exited with code $rc"
    fi
    echo "--- sleeping ${INTERVAL}s until next run ---"
    sleep "$INTERVAL"
done
