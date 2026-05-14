#!/usr/bin/env python3
"""
Seed synthetic corporate content into share mount points via docker cp.
Usage: python3 scripts/seed-data.py <profile>
"""
import csv, io, os, random, subprocess, sys, tempfile
from faker import Faker
from dotenv import dotenv_values

fake = Faker("en_US")
PROFILE = sys.argv[1] if len(sys.argv) > 1 else "flat"
env = dotenv_values(".env")

CONTAINER = "samba-nas" if PROFILE == "flat" else "samba-fileserver"
SHARES = {
    "finance":     env.get("SHARE_FINANCE",     "finance"),
    "engineering": env.get("SHARE_ENGINEERING", "engineering"),
    "hr":          env.get("SHARE_HR",          "hr"),
}


def run(cmd: list, **kwargs):
    try:
        return subprocess.run(cmd, check=True, capture_output=True, **kwargs)
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(e.stderr.decode(), file=sys.stderr)
        raise


def write(container: str, share: str, filename: str, content: str):
    with tempfile.NamedTemporaryFile(mode="w", suffix=f"-{filename}", delete=False) as f:
        f.write(content)
        tmp = f.name
    dest = f"/storage/{share}/{filename}"
    run(["docker", "exec", container, "mkdir", "-p", f"/storage/{share}"])
    run(["docker", "cp", tmp, f"{container}:{dest}"])
    os.unlink(tmp)
    print(f"  {container}:{dest}")


def csv_str(rows: list) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def seed_finance(share: str):
    ledger = [{"account_code": f"GL-{random.randint(1000, 9999)}",
               "description": fake.bs(),
               "debit": round(random.uniform(1000, 500000), 2),
               "credit": round(random.uniform(1000, 500000), 2),
               "tax_id": fake.ein(),
               "period": fake.date_this_year().strftime("%Y-%m")}
              for _ in range(50)]
    write(CONTAINER, share, "ledger_entries.csv", csv_str(ledger))

    balance = [{"account": f"ACC-{i:03d}",
                "description": fake.bs(),
                "balance": round(random.uniform(-1e6, 1e6), 2)}
               for i in range(20)]
    write(CONTAINER, share, "balance_sheet.csv", csv_str(balance))


def seed_engineering(share: str):
    env_file = "\n".join([
        "# Application config — INTERNAL USE ONLY",
        f"DATABASE_URL=postgresql://{fake.user_name()}:{fake.password()}@db.{fake.domain_name()}/prod",
        f"API_KEY={fake.uuid4().replace('-', '')}",
        f"SECRET_KEY={fake.sha256()}",
        f"AWS_ACCESS_KEY_ID=AKIA{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ234567', k=16))}",
        f"AWS_SECRET_ACCESS_KEY={fake.sha256()}",
        "ENVIRONMENT=production",
        f"PORT={random.randint(3000, 9000)}",
    ])
    write(CONTAINER, share, "app.env", env_file)

    adr = f"""# ADR-001: {fake.catch_phrase()}

## Status
Accepted

## Context
{fake.paragraph(nb_sentences=4)}

## Decision
{fake.paragraph(nb_sentences=3)}

## Consequences
{fake.paragraph(nb_sentences=3)}
"""
    write(CONTAINER, share, "ADR-001-architecture.md", adr)


def seed_hr(share: str):
    review = f"""EMPLOYEE PERFORMANCE REVIEW — CONFIDENTIAL

Employee:   {fake.name()}
Department: {random.choice(['Engineering', 'Finance', 'Marketing'])}
Reviewer:   {fake.name()}
Period:     {fake.date_this_year().strftime('%Y')} Q{random.randint(1, 4)}

SUMMARY
{fake.paragraph(nb_sentences=5)}

COMPENSATION BAND
Current: £{random.randint(50, 120) * 1000:,}
Recommended adjustment: {random.choice([0, 3, 5, 8])}%

GOALS FOR NEXT PERIOD
1. {fake.bs().capitalize()}
2. {fake.bs().capitalize()}
3. {fake.bs().capitalize()}
"""
    write(CONTAINER, share, f"review_{fake.last_name().lower()}.txt", review)

    sop = (
        f"""STANDARD OPERATING PROCEDURE: {fake.job()}

Version: 1.{random.randint(0, 9)}
Owner: HR
Last reviewed: {fake.date_this_year()}

1. PURPOSE
{fake.paragraph(nb_sentences=2)}

2. SCOPE
{fake.paragraph(nb_sentences=2)}

3. PROCEDURE
"""
        + "\n".join(f"{i + 1}. {fake.sentence()}" for i in range(6))
    )
    write(CONTAINER, share, "SOP-onboarding.txt", sop)


if __name__ == "__main__":
    print(f"Seeding content into {CONTAINER}...")
    seed_finance(SHARES["finance"])
    seed_engineering(SHARES["engineering"])
    seed_hr(SHARES["hr"])
    print("Content seeding complete.")
