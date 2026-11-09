.PHONY: all help init setup setup-dev build build-dev run run-dev stop logs logs-frontend \
	logs-backend shell-frontend shell-backend test test-unit test-dev test-web try-tagging \
	install dev web-build

all: help

uid := $(shell id -u)
gid := $(shell id -g)

PROJECT_NAME := watchwhat
export WATCHWHAT_DATA_DIR ?= $(CURDIR)/data

# Create the data dir as the current user; a bind mount of a missing dir
# would otherwise be created by docker as root and be unwritable.
init:
	@mkdir -p "$(WATCHWHAT_DATA_DIR)" backend/data

setup: build
setup-dev: build-dev

build:
	uid=$(uid) gid=$(gid) docker compose -p $(PROJECT_NAME) --profile prod build

build-dev:
	uid=$(uid) gid=$(gid) docker compose -p $(PROJECT_NAME) --profile dev build

run:
	$(MAKE) init
	$(MAKE) stop
	@if [ -z "$$(docker images -q watchwhat-backend)" ]; then $(MAKE) build; fi
	docker compose -p $(PROJECT_NAME) --profile prod up -d

run-dev:
	$(MAKE) init
	$(MAKE) stop
	@if [ -z "$$(docker images -q watchwhat-backend-dev)" ]; then $(MAKE) build-dev; fi
	docker compose -p $(PROJECT_NAME) --profile dev up

stop:
	@docker compose -p $(PROJECT_NAME) --profile dev down 2>/dev/null || true
	@docker compose -p $(PROJECT_NAME) --profile prod down 2>/dev/null || true

logs: logs-frontend logs-backend

logs-frontend:
	@docker logs watchwhat-frontend

logs-backend:
	@docker logs watchwhat-backend

shell-frontend:
	@docker exec -it watchwhat-frontend /bin/sh

shell-backend:
	@docker exec -it watchwhat-backend /bin/sh

# --- Tests (all free: fakes stand in for TMDB and the model) ---

test: test-unit

# Backend tests in the production container.
test-unit:
	docker exec watchwhat-backend python -m pytest -q -p no:cacheprovider

# Backend tests in the running dev container (make run-dev).
test-dev:
	docker exec watchwhat-backend-dev python -m pytest -q -p no:cacheprovider

# Frontend logic tests (needs make install).
test-web:
	cd frontend && npm test

# PAID, a fraction of a cent: tag one movie with the real model and print the
# answer; asks before it calls. TMDB_ID=348, or TITLE="Alien" YEAR=1979.
try-tagging:
	docker exec -it watchwhat-backend python -m scripts.try_tagging \
		$(if $(TMDB_ID),$(TMDB_ID),"$(TITLE)" $(YEAR))

# --- Web without docker ---

install:
	cd frontend && npm install

dev:
	cd frontend && npm run dev

web-build:
	cd frontend && npm run build

help:
	@echo "watchwhat"
	@echo ""
	@echo "  make run-dev       backend (SQLite, logged in as the first member) + web with hot reload on :3000"
	@echo "  make run           production containers (WATCHWHAT_* settings, see README)"
	@echo "  make build[-dev]   build images"
	@echo "  make stop          stop all watchwhat containers"
	@echo "  make logs          container logs"
	@echo "  make test-unit     backend tests in the production container"
	@echo "  make test-dev      backend tests in the dev container"
	@echo "  make test-web      frontend logic tests (after make install)"
	@echo "  make try-tagging   PAID (tiny): tag one movie for real, TMDB_ID=348 or TITLE=... YEAR=..."
	@echo "  make install       npm install in frontend/"
	@echo "  make dev           vite dev server without docker (backend on :8000)"
	@echo "  make web-build     production web build into frontend/dist"
