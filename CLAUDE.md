# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

An on-demand, deterministic SMB sandbox for testing AI agents (CrewAI, LangGraph, MCP-based) that interact with corporate file shares. It orchestrates Docker containers running Samba in three increasingly complex profiles and provides scripts for seeding synthetic data, probing health, injecting faults, and snapshotting state.

## Setup

```bash
pip install -r requirements.txt   # faker, python-dotenv
cp .env.example .env
# Set ADMIN_PASSWORD at minimum; DOMAIN/DOMAIN_FQDN required for profile-standard
```

## Common Commands

All `make` targets accept `PROFILE=flat` (default) or `PROFILE=standard`. `PROFILE=secure` is not yet implemented and will error immediately.

```bash
make up [PROFILE=<name>]          # Create bridge network if needed, then docker compose up -d --build
make seed [PROFILE=<name>]        # Wait for healthy → create users → seed files
make reset [PROFILE=<name>]       # down + up + seed in one shot
make down [PROFILE=<name>]        # Stop all containers and wipe volumes (-v)
make probe [PROFILE=<name>]       # Scripted pass/fail validation; exits non-zero on any failure
make creds                        # Print .generated-credentials to stdout
make snapshot [PROFILE=<name>]    # Archive named volumes to snapshots/
make restore [PROFILE=<name>]     # Bring down, restore latest snapshot, bring back up
make fault FAULT=<type> [PROFILE=<name>]   # Inject a failure condition
```

Available fault types: `nas-down`, `nas-restore`, `dc-down`, `dc-restore`, `acl-corrupt`, `acl-restore`, `restore-all`.

## Architecture

### Profile System

Profiles are selected via `PROFILE=<name>`. Each profile lives under `env-profiles/profile-<name>/`. The Makefile always composes `base-network.yml` (defines the external `smb_test_bridge` network) with the profile-specific `docker-compose.yml`.

| Profile | Containers | Auth mechanism |
|---|---|---|
| `flat` | `samba-nas` (upstream Samba image) | Local users via `tdbsam`; guests allowed |
| `standard` | `samba-dc` (custom Debian build) + `samba-fileserver` (upstream image) | Active Directory (ADS security mode); DC must be healthy before fileserver starts |
| `secure` | Not implemented | Segmented subnets with nftables router |

**Profile-standard detail:** `samba-dc` runs a custom `dc.Dockerfile` that provisions a full Samba AD domain controller on first boot (idempotent — skips if `/var/lib/samba/private/krb5.conf` already exists). The fileserver joins the domain and resolves DNS via the DC at `192.168.10.2`. The `smb.conf` for standard is generated at `make up` time from `smb.conf.tpl` via `envsubst` using `$DOMAIN` and `$DOMAIN_FQDN` from `.env`.

### Container Naming Convention

Scripts use the container name directly:
- `flat` profile → `samba-nas`
- `standard` profile → `samba-fileserver` (for file ops), `samba-dc` (for user/group management)

### Seeding Pipeline

`make seed` runs three steps in sequence:
1. `scripts/wait-healthy.sh` — polls Docker health status (120s timeout for flat, 360s for standard)
2. `scripts/seed-identity.sh` — creates 4 groups (`hr`, `finance`, `engineering`, `executive`) and 10 users with random passwords; writes `username:password:department` lines to `.generated-credentials`
3. `scripts/seed-data.py` — uses `faker` to generate synthetic CSV/text/env files and copies them into containers via `docker cp`

Credentials are regenerated on every `make seed`. The `.generated-credentials` file is gitignored.

### Share Layout

Each profile exposes three shares on port 445:

| Share | Files seeded | ACL |
|---|---|---|
| `finance` | `ledger_entries.csv`, `balance_sheet.csv` | `@finance`, `@executive` |
| `engineering` | `app.env` (fake secrets), `ADR-001-architecture.md` | `@engineering`, `@executive` |
| `hr` | `review_<name>.txt`, `SOP-onboarding.txt` | `@hr`, `@executive` |

Share names are configurable via `SHARE_FINANCE`, `SHARE_ENGINEERING`, `SHARE_HR` in `.env`.

### Snapshot / Restore

`make snapshot` uses a temporary Alpine container to `tar czf` each named volume into `snapshots/`. `make restore` brings containers down first (important — Samba may hold open file handles), wipes volume contents, then extracts the most recent archive for each volume. Snapshots are named `<profile>-<vol>-<timestamp>.tar.gz`; restore picks the lexicographically latest.

### Connecting External Agent Repos

Agent repos must declare the bridge network as external:

```yaml
networks:
  smb_test_bridge:
    external: true
    name: smb_test_bridge
```

Then connect to `samba-nas` (flat) or `samba-fileserver` (standard) on port 445 using credentials from `make creds`.

## Environment Variables

| Variable | Notes |
|---|---|
| `ADMIN_PASSWORD` | Required for profile-standard; must meet AD complexity requirements |
| `DOMAIN` / `DOMAIN_FQDN` | NetBIOS name and FQDN realm for profile-standard (e.g. `CORP` / `corp.internal`) |
| `SMB_BRIDGE` | Docker bridge network name (default: `smb_test_bridge`) |
| `SAMBA_IMAGE` | Upstream image for flat/standard fileserver (default: `ghcr.io/servercontainers/samba`) |
| `SHARE_FINANCE` / `SHARE_ENGINEERING` / `SHARE_HR` | Share names (defaults match the values) |
| `SUBNET_FINANCE` / `SUBNET_ENGINEERING` | Only used by profile-secure (not yet active) |
