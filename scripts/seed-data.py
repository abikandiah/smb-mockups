#!/usr/bin/env python3
"""
Seed synthetic corporate content into share mount points via docker cp.
Usage: python3 scripts/seed-data.py <profile>
"""
import csv, io, pathlib, random, subprocess, sys, tempfile
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


def csv_str(rows: list) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def bulk_write(container: str, share: str, file_tree: dict):
    """Copy an entire {rel_path: content} tree into the container in one docker cp."""
    with tempfile.TemporaryDirectory() as tmp:
        for rel_path, content in file_tree.items():
            dest = pathlib.Path(tmp) / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)
        run(["docker", "exec", container, "mkdir", "-p", f"/storage/{share}"])
        run(["docker", "cp", f"{tmp}/.", f"{container}:/storage/{share}"])
    print(f"  {container}:/storage/{share}/ ({len(file_tree)} files)")


# --- Finance ---

def _ledger_rows(period: str) -> list:
    return [
        {"account_code": f"GL-{random.randint(1000, 9999)}",
         "description": fake.bs(),
         "debit": round(random.uniform(1000, 500000), 2),
         "credit": round(random.uniform(1000, 500000), 2),
         "tax_id": fake.ein(),
         "period": period}
        for _ in range(50)
    ]


def _expense_rows(period: str) -> list:
    return [
        {"employee": fake.name(),
         "department": random.choice(["Finance", "Engineering", "HR", "Executive"]),
         "category": random.choice(["Travel", "Software", "Hardware", "Training", "Office"]),
         "amount": round(random.uniform(10, 5000), 2),
         "approved": random.choice(["Yes", "No"]),
         "period": period}
        for _ in range(30)
    ]


def seed_finance(share: str):
    files = {}

    for year in [2023, 2024]:
        for month in range(1, 13):
            quarter = f"Q{(month - 1) // 3 + 1}"
            period = f"{year}-{month:02d}"
            files[f"{year}/{quarter}/ledger_{period}.csv"] = csv_str(_ledger_rows(period))
            files[f"{year}/{quarter}/expenses_{period}.csv"] = csv_str(_expense_rows(period))

    vendors = [
        {"vendor_id": f"V-{i:04d}", "name": fake.company(), "contact": fake.name(),
         "email": fake.company_email(), "country": fake.country(),
         "payment_terms": random.choice(["Net30", "Net60", "Net90"]),
         "approved": random.choice(["Yes", "No"])}
        for i in range(1, 31)
    ]
    files["vendors/vendor_list.csv"] = csv_str(vendors)

    payments = [
        {"payment_id": f"PAY-{random.randint(10000, 99999)}",
         "vendor_id": f"V-{random.randint(1, 30):04d}",
         "amount": round(random.uniform(500, 100000), 2),
         "currency": random.choice(["USD", "GBP", "EUR"]),
         "date": fake.date_between(start_date="-2y", end_date="today").isoformat(),
         "status": random.choice(["Paid", "Pending", "Overdue"])}
        for _ in range(60)
    ]
    files["vendors/payment_history.csv"] = csv_str(payments)

    depts = ["Engineering", "HR", "Finance", "Marketing", "Sales"]
    cats = ["Headcount", "Software", "Hardware", "Travel", "Training"]
    for year in [2023, 2024]:
        budget = [
            {"department": d, "category": c,
             "allocated": round(random.uniform(10000, 500000), 2),
             "spent":     round(random.uniform(5000,  450000), 2),
             "year": year}
            for d in depts for c in cats
        ]
        files[f"budgets/budget_{year}.csv"] = csv_str(budget)

    forecast = [
        {"department": d,
         "q1": round(random.uniform(50000, 500000), 2),
         "q2": round(random.uniform(50000, 500000), 2),
         "q3": round(random.uniform(50000, 500000), 2),
         "q4": round(random.uniform(50000, 500000), 2)}
        for d in depts
    ]
    files["budgets/forecast_2025.csv"] = csv_str(forecast)

    bulk_write(CONTAINER, share, files)


# --- Engineering ---

def seed_engineering(share: str):
    files = {}

    project_names = [fake.slug() for _ in range(3)]
    all_services = ["api", "worker", "scheduler", "gateway", "cache"]

    for project in project_names:
        base = f"projects/{project}"
        files[f"{base}/README.md"] = "\n".join([
            f"# {project.replace('-', ' ').title()}",
            "",
            fake.paragraph(nb_sentences=3),
            "",
            "## Getting Started",
            fake.paragraph(nb_sentences=2),
            "",
            "## Architecture",
            fake.paragraph(nb_sentences=2),
            "",
            "## Contributing",
            fake.paragraph(nb_sentences=2),
        ])
        for n in range(1, 3):
            slug = fake.slug()
            files[f"{base}/ADR-{n:03d}-{slug}.md"] = "\n".join([
                f"# ADR-{n:03d}: {fake.catch_phrase()}",
                "",
                "## Status",
                random.choice(["Accepted", "Proposed", "Deprecated", "Superseded"]),
                "",
                "## Context",
                fake.paragraph(nb_sentences=4),
                "",
                "## Decision",
                fake.paragraph(nb_sentences=3),
                "",
                "## Consequences",
                fake.paragraph(nb_sentences=3),
            ])
        files[f"{base}/config.yml"] = "\n".join([
            f"service: {project}",
            "environment: production",
            f"replicas: {random.randint(2, 8)}",
            "resources:",
            f"  cpu: {random.choice(['250m', '500m', '1000m'])}",
            f"  memory: {random.choice(['256Mi', '512Mi', '1Gi'])}",
            "logging:",
            f"  level: {random.choice(['INFO', 'WARN', 'DEBUG'])}",
            "  format: json",
        ])
        db_name = project.replace("-", "_")
        files[f"{base}/.env.sample"] = "\n".join([
            f"# {project} — sample env (do not commit real values)",
            f"DATABASE_URL=postgresql://user:password@localhost/{db_name}",
            "REDIS_URL=redis://localhost:6379",
            "API_KEY=<your-api-key>",
            "SECRET_KEY=<your-secret-key>",
            f"PORT={random.randint(3000, 9000)}",
            "ENVIRONMENT=development",
        ])

    for svc in random.sample(all_services, 4):
        files[f"runbooks/deploy_{svc}.md"] = "\n".join([
            f"# Deploy Runbook: {svc}",
            "",
            "## Prerequisites",
            fake.paragraph(nb_sentences=2),
            "",
            "## Steps",
        ] + [f"{i+1}. {fake.sentence()}" for i in range(5)] + [
            "",
            "## Rollback",
            fake.paragraph(nb_sentences=2),
            "",
            "## Contacts",
            f"On-call: {fake.name()} ({fake.company_email()})",
        ])

    for date in ["2023-09-12", "2024-01-05", "2024-03-20", "2024-07-14"]:
        files[f"incidents/incident_{date}.md"] = "\n".join([
            f"# Incident Report — {date}",
            "",
            "## Summary",
            fake.paragraph(nb_sentences=2),
            "",
            "## Timeline",
            f"- {fake.time()}: {fake.sentence()}",
            f"- {fake.time()}: {fake.sentence()}",
            f"- {fake.time()}: {fake.sentence()}",
            "",
            "## Root Cause",
            fake.paragraph(nb_sentences=2),
            "",
            "## Action Items",
        ] + [f"{i+1}. {fake.sentence()}" for i in range(3)])

    files["architecture/system-design.md"] = "\n".join([
        "# System Design",
        "",
        "## Overview",
        fake.paragraph(nb_sentences=4),
        "",
        "## Components",
        fake.paragraph(nb_sentences=3),
        "",
        "## Scalability Considerations",
        fake.paragraph(nb_sentences=3),
    ])
    files["architecture/data-flow.md"] = "\n".join([
        "# Data Flow Architecture",
        "",
        fake.paragraph(nb_sentences=3),
        "",
        "## Ingestion",
        fake.paragraph(nb_sentences=2),
        "",
        "## Processing",
        fake.paragraph(nb_sentences=2),
        "",
        "## Storage",
        fake.paragraph(nb_sentences=2),
    ])
    files["architecture/tech-radar.md"] = "\n".join([
        "# Technology Radar",
        "",
        "## Adopt",
    ] + [f"- {fake.bs()}" for _ in range(4)] + [
        "",
        "## Trial",
    ] + [f"- {fake.bs()}" for _ in range(3)] + [
        "",
        "## Assess",
    ] + [f"- {fake.bs()}" for _ in range(3)] + [
        "",
        "## Hold",
    ] + [f"- {fake.bs()}" for _ in range(2)])

    bulk_write(CONTAINER, share, files)


# --- HR ---

def seed_hr(share: str):
    files = {}

    review_names = [fake.last_name() for _ in range(8)]
    for year in [2023, 2024]:
        for name in review_names:
            files[f"reviews/{year}/review_{name.lower()}.txt"] = "\n".join([
                "EMPLOYEE PERFORMANCE REVIEW — CONFIDENTIAL",
                "",
                f"Employee:   {fake.name()}",
                f"Department: {random.choice(['Engineering', 'Finance', 'Marketing', 'HR'])}",
                f"Reviewer:   {fake.name()}",
                f"Period:     {year} Q{random.randint(1, 4)}",
                "",
                "SUMMARY",
                fake.paragraph(nb_sentences=5),
                "",
                "COMPENSATION BAND",
                f"Current: £{random.randint(50, 120) * 1000:,}",
                f"Recommended adjustment: {random.choice([0, 3, 5, 8])}%",
                "",
                "GOALS FOR NEXT PERIOD",
                f"1. {fake.bs().capitalize()}",
                f"2. {fake.bs().capitalize()}",
                f"3. {fake.bs().capitalize()}",
            ])

    files["policies/SOP-onboarding.txt"] = "\n".join([
        "STANDARD OPERATING PROCEDURE: Onboarding",
        "",
        f"Version: 1.{random.randint(0, 9)}",
        "Owner: HR",
        f"Last reviewed: {fake.date_this_year()}",
        "",
        "1. PURPOSE",
        fake.paragraph(nb_sentences=2),
        "",
        "2. SCOPE",
        fake.paragraph(nb_sentences=2),
        "",
        "3. PROCEDURE",
    ] + [f"{i+1}. {fake.sentence()}" for i in range(6)])

    files["policies/SOP-offboarding.txt"] = "\n".join([
        "STANDARD OPERATING PROCEDURE: Offboarding",
        "",
        f"Version: 1.{random.randint(0, 9)}",
        "Owner: HR",
        f"Last reviewed: {fake.date_this_year()}",
        "",
        "1. PURPOSE",
        fake.paragraph(nb_sentences=2),
        "",
        "2. PROCEDURE",
    ] + [f"{i+1}. {fake.sentence()}" for i in range(8)])

    files["policies/code-of-conduct.txt"] = "\n".join([
        "CODE OF CONDUCT",
        "",
        f"Effective: {fake.date_this_year()}",
        "",
        "1. PROFESSIONAL CONDUCT",
        fake.paragraph(nb_sentences=3),
        "",
        "2. RESPECT AND INCLUSION",
        fake.paragraph(nb_sentences=3),
        "",
        "3. CONFIDENTIALITY",
        fake.paragraph(nb_sentences=2),
        "",
        "4. REPORTING VIOLATIONS",
        fake.paragraph(nb_sentences=2),
    ])

    files["policies/expense-policy.txt"] = "\n".join([
        "EXPENSE REIMBURSEMENT POLICY",
        "",
        f"Version: {random.randint(1, 5)}.{random.randint(0, 9)}",
        f"Approved by: {fake.name()}, CFO",
        "",
        "1. ELIGIBLE EXPENSES",
        fake.paragraph(nb_sentences=3),
        "",
        "2. SUBMISSION PROCESS",
        fake.paragraph(nb_sentences=2),
        "",
        "3. LIMITS",
        f"- Meals (per diem): £{random.randint(30, 60)}",
        f"- Hotel: £{random.randint(120, 250)} per night",
        "- Air travel: Economy class only (exceptions require VP approval)",
        "",
        "4. NON-REIMBURSABLE",
        fake.paragraph(nb_sentences=2),
    ])

    roles = [
        ("Senior Software Engineer", "Engineering"),
        ("Data Analyst", "Finance"),
        ("Product Manager", "Product"),
        ("HR Business Partner", "HR"),
        ("DevOps Engineer", "Engineering"),
    ]
    for role, dept in roles:
        slug = role.lower().replace(" ", "_")
        files[f"job-descriptions/{slug}.txt"] = "\n".join([
            role.upper(),
            "",
            f"Department: {dept}",
            f"Location: {fake.city()}, {fake.country()}",
            "Type: Full-time",
            "",
            "ABOUT THE ROLE",
            fake.paragraph(nb_sentences=3),
            "",
            "RESPONSIBILITIES",
        ] + [f"- {fake.bs().capitalize()}" for _ in range(5)] + [
            "",
            "REQUIREMENTS",
            f"- {random.randint(3, 8)}+ years of relevant experience",
        ] + [f"- {fake.bs().capitalize()}" for _ in range(4)])

    files["org-chart.txt"] = "\n".join([
        "ORGANISATIONAL CHART",
        "",
        f"CEO: {fake.name()}",
        "  |",
        f"  +-- CTO: {fake.name()}",
        "  |     |",
        f"  |     +-- VP Engineering: {fake.name()}",
        f"  |     |     +-- Engineering Manager: {fake.name()}",
        f"  |     |     +-- Engineering Manager: {fake.name()}",
        f"  |     +-- VP Product: {fake.name()}",
        "  |",
        f"  +-- CFO: {fake.name()}",
        "  |     |",
        f"  |     +-- Finance Director: {fake.name()}",
        f"  |     +-- Controller: {fake.name()}",
        "  |",
        f"  +-- CHRO: {fake.name()}",
        "        |",
        f"        +-- HR Business Partner: {fake.name()}",
        f"        +-- Talent Acquisition Lead: {fake.name()}",
    ])

    bulk_write(CONTAINER, share, files)


if __name__ == "__main__":
    print(f"Seeding content into {CONTAINER}...")
    seed_finance(SHARES["finance"])
    seed_engineering(SHARES["engineering"])
    seed_hr(SHARES["hr"])
    print("Content seeding complete.")
