.PHONY: build test test-docker test-doctor test-write test-config test-version \
	test-help test-all lint check clean help

# -- Python / venv ---------------------------------------------------------
VENV := .venv
PYTHON := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff

# -- Container -------------------------------------------------------------
IMAGE := email-archiver:latest
CONFIG := $(PWD)/docker/test-compose/config
DATA := $(PWD)/docker/test-compose/data
STATE := $(PWD)/docker/test-compose/state
SECRET := $(PWD)/docker/test-compose/secrets/imap_password

PODMAN_RUN := podman run --rm \
	--userns=keep-id \
	-v $(CONFIG):/home/archiver/.config:ro,z \
	-v $(DATA):/home/archiver/Mail/imap:rw,z \
	-v $(STATE):/home/archiver/.local/state/email-archiver:rw,z \
	-v $(SECRET):/run/secrets/imap_password:ro,z \
	$(IMAGE)

# ==========================================================================
#  Python targets
# ==========================================================================

## Run Python unit tests (pytest)
test:
	$(PYTEST) tests/ -v

## Run ruff linter
lint:
	$(RUFF) check src/ tests/

## Run ruff formatter check (no changes)
format-check:
	$(RUFF) format --check src/ tests/

## Lint + tests (quick pre-commit check)
check: lint test

# ==========================================================================
#  Container targets
# ==========================================================================

build:
	@echo "Building image..."
	podman build -t $(IMAGE) .

test-doctor: build
	@echo "\n=== Testing doctor command ==="
	$(PODMAN_RUN) doctor

test-write: build
	@echo "\n=== Testing write permissions ==="
	podman run --rm \
		--userns=keep-id \
		-v $(DATA):/home/archiver/Mail/imap:rw,z \
		--entrypoint /bin/bash \
		$(IMAGE) \
		-c "touch /home/archiver/Mail/imap/test && rm /home/archiver/Mail/imap/test && echo 'Write test: OK'"

test-config: build
	@echo "\n=== Testing config read ==="
	podman run --rm \
		--userns=keep-id \
		-v $(CONFIG):/home/archiver/.config:ro,z \
		--entrypoint /bin/bash \
		$(IMAGE) \
		-c "cat /home/archiver/.config/email-archiver/config.toml | head -3"

test-version: build
	@echo "\n=== Testing version ==="
	$(PODMAN_RUN) --version

test-help: build
	@echo "\n=== Testing help ==="
	$(PODMAN_RUN) --help

## Run all container integration tests
test-docker: test-version test-doctor test-config test-write
	@echo "\n✅ All container tests passed!"

## Run everything: Python tests + lint + container tests
test-all: check test-docker
	@echo "\n✅ All tests passed!"

# ==========================================================================
#  Housekeeping
# ==========================================================================

clean:
	@echo "Removing test artifacts..."
	rm -f $(DATA)/* $(STATE)/*
	podman rmi $(IMAGE) 2>/dev/null || true

help:
	@echo "Makefile targets:"
	@echo ""
	@echo "  Python:"
	@echo "    test           - Run pytest unit tests"
	@echo "    lint           - Run ruff linter"
	@echo "    format-check   - Check ruff formatting (no changes)"
	@echo "    check          - lint + test"
	@echo ""
	@echo "  Container:"
	@echo "    build          - Build the email-archiver image"
	@echo "    test-doctor    - Run doctor command in container"
	@echo "    test-write     - Test write permissions on data volume"
	@echo "    test-config    - Test reading config in container"
	@echo "    test-version   - Test --version in container"
	@echo "    test-help      - Test --help in container"
	@echo "    test-docker    - Run all container tests"
	@echo ""
	@echo "  Combined:"
	@echo "    test-all       - Run everything (Python + container)"
	@echo "    clean          - Remove test artifacts and image"
