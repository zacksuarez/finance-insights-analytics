"""Generate deterministic, business-shaped source-system extracts for V1."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable


SEED = 20260930
START_MONTH = date(2024, 1, 1)
MONTH_COUNT = 24

REGIONS = ("East", "Central", "West")
SEGMENTS = ("Enterprise", "Mid-Market", "SMB")
DEPARTMENTS = ("Sales", "Marketing", "Customer Success", "Engineering", "G&A")
PRODUCTS = {
    "PROD-PLATFORM": ("Platform Subscription", "Recurring Revenue"),
    "PROD-ANALYTICS": ("Analytics Module", "Recurring Revenue"),
    "PROD-PRO_SERVICES": ("Professional Services", "Services Revenue"),
    "PROD-IMPLEMENTATION": ("Implementation Services", "Services Revenue"),
}

ERP_FIELDS = (
    "transaction_id",
    "date",
    "period",
    "account",
    "account_category",
    "department",
    "customer_id",
    "product_id",
    "vendor",
    "amount",
)
CRM_FIELDS = (
    "customer_id",
    "customer_name",
    "segment",
    "region",
    "industry",
    "account_owner",
    "contract_start",
    "contract_end",
    "status",
)
PLAN_FIELDS = (
    "period",
    "account",
    "department",
    "customer_id",
    "product_id",
    "forecast_amount",
    "scenario_version",
)
PIPELINE_FIELDS = (
    "opportunity_id",
    "customer_id",
    "created_date",
    "expected_close_date",
    "stage",
    "pipeline_amount",
    "probability",
    "product_id",
    "region",
)
KPI_FIELDS = (
    "period",
    "record_type",
    "customer_id",
    "department",
    "active_users",
    "support_tickets",
    "implementation_hours",
    "usage_metric",
    "headcount",
)


def month_sequence(start: date = START_MONTH, count: int = MONTH_COUNT) -> list[date]:
    months: list[date] = []
    year, month = start.year, start.month
    for _ in range(count):
        months.append(date(year, month, 1))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return months


def add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, month_zero = divmod(month_index, 12)
    return date(year, month_zero + 1, 1)


def month_end(value: date) -> date:
    return add_months(value, 1) - timedelta(days=1)


def money(value: float) -> str:
    return f"{value:.2f}"


def write_csv(path: Path, fields: Iterable[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_customers(rng: random.Random) -> list[dict[str, str]]:
    featured_names = [
        "Northstar Systems",
        "Aster Ridge Technologies",
        "Cobalt Harbor Group",
        "Juniper Peak Networks",
        "Meridian Forge Labs",
        "Silverline Data Works",
        "Arcfield Commerce",
        "Brightpath Logistics",
        "Evercrest Health Tech",
        "Redwood Signal Partners",
    ]
    prefixes = (
        "Alto",
        "Beacon",
        "Cedar",
        "Delta",
        "Ember",
        "Foundry",
        "Granite",
        "Helix",
        "Indigo",
        "Kinetic",
        "Lattice",
        "Mosaic",
        "Nova",
        "Orchid",
        "Pioneer",
        "Quartz",
        "Rivet",
        "Summit",
        "Tandem",
        "Vertex",
    )
    suffixes = (
        "Advisory",
        "Cloud",
        "Digital",
        "Dynamics",
        "Industries",
        "Labs",
        "Networks",
        "Operations",
        "Solutions",
        "Works",
    )
    industries = ("Technology", "Healthcare", "Financial Services", "Manufacturing", "Business Services")
    customers: list[dict[str, str]] = []

    for index in range(1, 151):
        if index <= len(featured_names):
            name = featured_names[index - 1]
        else:
            name = f"{prefixes[(index - 1) % len(prefixes)]} {suffixes[((index - 1) // len(prefixes)) % len(suffixes)]} {index:03d}"

        if index <= 50:
            segment = "Enterprise"
        elif index <= 110:
            segment = "Mid-Market"
        else:
            segment = "SMB"

        region = REGIONS[(index - 1) % len(REGIONS)]
        if index == 1:
            region = "West"
        start = date(2022 + (index % 2), (index % 12) + 1, 1)
        end = date(2026 + (index % 3), ((index + 5) % 12) + 1, 1)
        customers.append(
            {
                "customer_id": f"CUST{index:03d}",
                "customer_name": name,
                "segment": segment,
                "region": region,
                "industry": industries[(index - 1) % len(industries)],
                "account_owner": f"Portfolio Owner {(index - 1) % 18 + 1:02d}",
                "contract_start": start.isoformat(),
                "contract_end": end.isoformat(),
                "status": "Active" if index <= 144 else rng.choice(("Churned", "Inactive")),
            }
        )
    return customers


def customer_weight(customer_number: int, segment: str) -> float:
    if customer_number == 1:
        return 12.0
    if customer_number <= 5:
        return 5.0
    return {"Enterprise": 1.5, "Mid-Market": 0.8, "SMB": 0.35}[segment]


def product_mix(customer_number: int, year: int) -> dict[str, float]:
    if customer_number == 1:
        return {
            "PROD-PLATFORM": 0.48 if year == 2024 else 0.42,
            "PROD-ANALYTICS": 0.12,
            "PROD-PRO_SERVICES": 0.25 if year == 2024 else 0.29,
            "PROD-IMPLEMENTATION": 0.15 if year == 2024 else 0.17,
        }
    if year == 2024:
        return {
            "PROD-PLATFORM": 0.65,
            "PROD-ANALYTICS": 0.15,
            "PROD-PRO_SERVICES": 0.12,
            "PROD-IMPLEMENTATION": 0.08,
        }
    return {
        "PROD-PLATFORM": 0.60,
        "PROD-ANALYTICS": 0.15,
        "PROD-PRO_SERVICES": 0.15,
        "PROD-IMPLEMENTATION": 0.10,
    }


def generate_dataset(output_dir: Path, seed: int = SEED) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    months = month_sequence()
    customers = build_customers(rng)
    customer_lookup = {row["customer_id"]: row for row in customers}

    erp_rows: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []
    kpi_rows: list[dict[str, Any]] = []
    monthly_revenue: dict[str, float] = defaultdict(float)
    transaction_number = 1

    cogs_rates_2024 = {
        "PROD-PLATFORM": 0.22,
        "PROD-ANALYTICS": 0.25,
        "PROD-PRO_SERVICES": 0.55,
        "PROD-IMPLEMENTATION": 0.62,
    }
    cogs_rates_2025 = {
        "PROD-PLATFORM": 0.25,
        "PROD-ANALYTICS": 0.28,
        "PROD-PRO_SERVICES": 0.63,
        "PROD-IMPLEMENTATION": 0.72,
    }

    for month_index, month in enumerate(months):
        period = month.strftime("%Y-%m")
        if month.year == 2024:
            year_growth = 1.0
        elif month.month <= 8:
            year_growth = 1.17
        else:
            year_growth = 1.17 - 0.035 * (month.month - 8)
        seasonality = 1 + 0.055 * math.sin((month.month - 1) / 12 * math.tau)

        for customer_number, customer in enumerate(customers, start=1):
            if customer["status"] != "Active":
                continue
            base = customer_weight(customer_number, customer["segment"]) * 55_000
            customer_growth = year_growth * (1.18 if customer_number == 1 and month.year == 2025 else 1.0)
            total_customer_revenue = base * customer_growth * seasonality * rng.uniform(0.965, 1.035)
            mix = product_mix(customer_number, month.year)

            customer_support = 0
            customer_hours = 0
            customer_users = 0
            customer_usage = 0.0

            for product_id, share in mix.items():
                revenue = round(total_customer_revenue * share, 2)
                cogs_rate = (cogs_rates_2024 if month.year == 2024 else cogs_rates_2025)[product_id]
                if customer_number == 1:
                    cogs_rate += 0.05 if month.year == 2024 else 0.13
                cogs = round(-revenue * cogs_rate * rng.uniform(0.985, 1.015), 2)
                account = "Subscription Revenue" if product_id in ("PROD-PLATFORM", "PROD-ANALYTICS") else "Services Revenue"
                revenue_department = "Sales" if "SUBSCRIPTION" in account.upper() else "Customer Success"

                for account_name, category, department, amount in (
                    (account, "Revenue", revenue_department, revenue),
                    ("Cost of Revenue", "COGS", "Customer Success", cogs),
                ):
                    erp_rows.append(
                        {
                            "transaction_id": f"TXN{transaction_number:07d}",
                            "date": month_end(month).isoformat(),
                            "period": period,
                            "account": account_name,
                            "account_category": category,
                            "department": department,
                            "customer_id": customer["customer_id"],
                            "product_id": product_id,
                            "vendor": "",
                            "amount": money(amount),
                        }
                    )
                    transaction_number += 1

                    region_bias = 0.0
                    if customer["region"] == "West" and month.year == 2025:
                        region_bias = 0.025 * month.month
                    normal_bias = 0.015 * math.sin((customer_number + month.month) / 4)
                    forecast_multiplier = 1 + region_bias + normal_bias
                    if category == "COGS":
                        forecast_multiplier = 0.98 + region_bias * 0.35 + normal_bias

                    for scenario, multiplier in (
                        ("Budget", 1.02 if category == "Revenue" else 0.96),
                        ("Forecast", forecast_multiplier),
                    ):
                        plan_rows.append(
                            {
                                "period": period,
                                "account": account_name,
                                "department": department,
                                "customer_id": customer["customer_id"],
                                "product_id": product_id,
                                "forecast_amount": money(amount * multiplier),
                                "scenario_version": scenario,
                            }
                        )

                monthly_revenue[period] += revenue
                customer_users += int(revenue / 1_350)
                customer_usage += revenue / 115
                if product_id in ("PROD-PRO_SERVICES", "PROD-IMPLEMENTATION"):
                    customer_hours += int(revenue / (145 if product_id == "PROD-PRO_SERVICES" else 125))

            customer_support = max(1, int(customer_users * 0.035 * rng.uniform(0.8, 1.2)))
            if customer_number == 1:
                customer_support = int(customer_support * (1.65 if month.year == 2024 else 2.35))
                customer_hours = int(customer_hours * (1.25 if month.year == 2024 else 1.55))

            kpi_rows.append(
                {
                    "period": period,
                    "record_type": "Customer",
                    "customer_id": customer["customer_id"],
                    "department": "",
                    "active_users": customer_users,
                    "support_tickets": customer_support,
                    "implementation_hours": customer_hours,
                    "usage_metric": f"{customer_usage:.2f}",
                    "headcount": "",
                }
            )

        department_headcount = {
            "Sales": 88 + month_index // 4,
            "Marketing": 34 + month_index // 8,
            "Customer Success": 72 + month_index // 4,
            "Engineering": 118 + month_index // 3,
            "G&A": 43 + month_index // 10,
        }
        expense_accounts = (
            "Payroll",
            "Software",
            "Marketing",
            "Travel",
            "Professional Services",
            "Facilities",
            "Other OpEx",
        )
        account_factors = {
            "Payroll": 1.0,
            "Software": 0.115,
            "Marketing": 0.15,
            "Travel": 0.035,
            "Professional Services": 0.07,
            "Facilities": 0.045,
            "Other OpEx": 0.055,
        }
        department_salary = {
            "Sales": 13_500,
            "Marketing": 12_000,
            "Customer Success": 11_500,
            "Engineering": 15_500,
            "G&A": 13_000,
        }
        vendors = {
            "Software": "Nimbus Stack LLC",
            "Marketing": "SignalCraft Media",
            "Travel": "Waypoint Travel Desk",
            "Professional Services": "Axiom Advisory Group",
            "Facilities": "Civic Square Properties",
        }

        for department in DEPARTMENTS:
            headcount = department_headcount[department]
            payroll = headcount * department_salary[department] * rng.uniform(0.99, 1.01)
            for account in expense_accounts:
                relevance = 1.0
                if account == "Marketing" and department != "Marketing":
                    relevance = 0.08
                if account == "Travel" and department not in ("Sales", "Customer Success"):
                    relevance = 0.35
                actual = -payroll * account_factors[account] * relevance * rng.uniform(0.96, 1.04)
                if account == "Software" and department == "Engineering":
                    actual *= 1.19

                erp_rows.append(
                    {
                        "transaction_id": f"TXN{transaction_number:07d}",
                        "date": month_end(month).isoformat(),
                        "period": period,
                        "account": account,
                        "account_category": "OpEx",
                        "department": department,
                        "customer_id": "",
                        "product_id": "",
                        "vendor": vendors.get(account, "Various"),
                        "amount": money(actual),
                    }
                )
                transaction_number += 1

                forecast_factor = 1.0
                if account == "Software" and department == "Engineering":
                    forecast_factor = 1 / 1.19
                else:
                    forecast_factor = rng.uniform(0.985, 1.015)
                for scenario, amount in (
                    ("Budget", actual * rng.uniform(0.94, 0.99)),
                    ("Forecast", actual * forecast_factor),
                ):
                    plan_rows.append(
                        {
                            "period": period,
                            "account": account,
                            "department": department,
                            "customer_id": "",
                            "product_id": "",
                            "forecast_amount": money(amount),
                            "scenario_version": scenario,
                        }
                    )

            kpi_rows.append(
                {
                    "period": period,
                    "record_type": "Department",
                    "customer_id": "",
                    "department": department,
                    "active_users": "",
                    "support_tickets": "",
                    "implementation_hours": "",
                    "usage_metric": "",
                    "headcount": headcount,
                }
            )

    pipeline_rows: list[dict[str, Any]] = []
    stages = (("Discovery", 0.15), ("Qualified", 0.35), ("Proposal", 0.60), ("Negotiation", 0.80))
    opportunity_number = 1
    active_customers = [row for row in customers if row["status"] == "Active"]
    for month_index, month in enumerate(months):
        period = month.strftime("%Y-%m")
        coverage_factor = 3.3 if month.year == 2024 else max(1.35, 3.05 - 0.15 * month.month)
        target_unweighted = monthly_revenue[period] * coverage_factor
        weights = [rng.uniform(0.6, 1.4) for _ in range(32)]
        weight_total = sum(weights)
        for index, weight in enumerate(weights):
            customer = active_customers[(month_index * 7 + index * 11) % len(active_customers)]
            stage, probability = stages[(index + month_index) % len(stages)]
            expected = month + timedelta(days=min(27, (index * 3) % 28))
            created = expected - timedelta(days=35 + (index * 13) % 120)
            product_id = tuple(PRODUCTS)[(index + month_index) % len(PRODUCTS)]
            pipeline_rows.append(
                {
                    "opportunity_id": f"OPP{opportunity_number:06d}",
                    "customer_id": customer["customer_id"],
                    "created_date": created.isoformat(),
                    "expected_close_date": expected.isoformat(),
                    "stage": stage,
                    "pipeline_amount": money(target_unweighted * weight / weight_total),
                    "probability": f"{probability:.2f}",
                    "product_id": product_id,
                    "region": customer["region"],
                }
            )
            opportunity_number += 1

    files = {
        "crm_customers.csv": (CRM_FIELDS, customers),
        "erp_transactions.csv": (ERP_FIELDS, erp_rows),
        "epm_plan.csv": (PLAN_FIELDS, plan_rows),
        "sales_pipeline.csv": (PIPELINE_FIELDS, pipeline_rows),
        "operational_kpis.csv": (KPI_FIELDS, kpi_rows),
    }
    for filename, (fields, rows) in files.items():
        write_csv(output_dir / filename, fields, rows)

    manifest = {
        "seed": seed,
        "period_start": months[0].strftime("%Y-%m"),
        "period_end": months[-1].strftime("%Y-%m"),
        "source_systems": 5,
        "row_counts": {filename: len(rows) for filename, (_, rows) in files.items()},
        "sha256": {filename: file_hash(output_dir / filename) for filename in files},
        "designated_story_entities": {
            "profitability_customer_id": "CUST001",
            "forecast_accuracy_region": "West",
            "structural_opex_department": "Engineering",
            "structural_opex_account": "Software",
        },
    }
    with (output_dir / "manifest.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "raw",
    )
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    manifest = generate_dataset(args.output_dir, args.seed)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
