COMPOSE_PROJECT_NAME := smb-mockups
export COMPOSE_PROJECT_NAME

-include .env
export

PROFILE   ?= flat
COMPOSE_F  = -f env-profiles/base-network.yml \
             -f env-profiles/profile-$(PROFILE)/docker-compose.yml

.PHONY: up down seed reset snapshot restore creds fault probe init-network check-env check-profile generate-conf

check-env:
	@test -f .env || { echo "ERROR: .env not found. Copy .env.example to .env and fill in values."; exit 1; }

check-profile:
	@if [ "$(PROFILE)" = "secure" ]; then \
	  echo "ERROR: profile-secure is not yet implemented. Use PROFILE=flat or PROFILE=standard."; \
	  exit 1; \
	fi

generate-conf:
	@if [ "$(PROFILE)" = "standard" ]; then \
	  command -v envsubst >/dev/null 2>&1 || { echo "ERROR: envsubst not found. Install gettext-base (apt) or gettext (brew)."; exit 1; }; \
	  DOMAIN="$(DOMAIN)" DOMAIN_FQDN="$(DOMAIN_FQDN)" \
	    envsubst '$$DOMAIN $$DOMAIN_FQDN' \
	    < env-profiles/profile-standard/smb.conf.tpl \
	    > env-profiles/profile-standard/smb.conf; \
	  echo "Generated env-profiles/profile-standard/smb.conf (domain=$(DOMAIN) realm=$(DOMAIN_FQDN))"; \
	fi

init-network:
	@docker network inspect $(SMB_BRIDGE) >/dev/null 2>&1 || \
	  docker network create $(SMB_BRIDGE)

up: check-env check-profile generate-conf init-network
	docker compose $(COMPOSE_F) up -d --build

down:
	docker compose $(COMPOSE_F) down -v

seed:
	@bash scripts/wait-healthy.sh $(PROFILE)
	@bash scripts/seed-identity.sh $(PROFILE)
	@python3 scripts/seed-data.py $(PROFILE)

reset: down up seed

restore:
	docker compose $(COMPOSE_F) down
	@bash scripts/snapshot.sh restore $(PROFILE)
	docker compose $(COMPOSE_F) up -d

snapshot:
	@bash scripts/snapshot.sh save $(PROFILE)

creds:
	@bash scripts/creds.sh

fault:
	@bash scripts/fault-inject.sh $(FAULT) $(PROFILE)

probe:
	@bash scripts/probe.sh $(PROFILE)
