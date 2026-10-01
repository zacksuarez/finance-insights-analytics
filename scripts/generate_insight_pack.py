"""Generate a deterministic management insight pack from trusted V2 marts."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def currency(value: float) -> str:
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    if absolute >= 1_000_000:
        return f"{sign}${absolute / 1_000_000:.1f}M"
    if absolute >= 1_000:
        return f"{sign}${absolute / 1_000:.1f}K"
    return f"{sign}${absolute:,.0f}"


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def generate_insight_pack(database_path: Path, output_path: Path) -> None:
    connection = duckdb.connect(str(database_path.resolve()), read_only=True)
    try:
        latest = connection.execute(
            """
            SELECT period, revenue, revenue_yoy_pct, gross_margin_pct, gross_margin_yoy_bps,
                   operating_expense, operating_contribution, operating_contribution_margin_pct,
                   forecast_accuracy_pct, pipeline_amount, weighted_pipeline, pipeline_coverage,
                   top_10_customer_revenue_pct
            FROM mart_executive_kpis ORDER BY period DESC LIMIT 1
            """
        ).fetchone()
        annual = connection.execute(
            """
            SELECT year, sum(revenue), sum(gross_profit) / sum(revenue), sum(operating_contribution)
            FROM mart_monthly_pnl GROUP BY year ORDER BY year
            """
        ).fetchall()
        customer = connection.execute(
            """
            SELECT customer_name, revenue, gross_margin_pct, margin_change_bps, revenue_rank,
                   support_tickets, implementation_hours
            FROM mart_customer_profitability_v2
            WHERE year = (SELECT max(year) FROM mart_customer_profitability_v2)
            ORDER BY margin_change_bps ASC LIMIT 1
            """
        ).fetchone()
        region = connection.execute(
            """
            SELECT region, forecast_accuracy_pct, revenue_yoy_pct, gross_margin_pct, pipeline_coverage
            FROM mart_regional_performance_v2
            WHERE period = (SELECT max(period) FROM mart_regional_performance_v2)
            ORDER BY forecast_accuracy_pct ASC LIMIT 1
            """
        ).fetchone()
        pipeline_prior = connection.execute(
            """
            SELECT pipeline_coverage FROM mart_executive_kpis
            WHERE period = strftime(strptime((SELECT max(period) FROM mart_executive_kpis), '%Y-%m') - INTERVAL 6 MONTH, '%Y-%m')
            """
        ).fetchone()[0]
        opex = connection.execute(
            """
            SELECT department_name, account_name, forecast_variance,
                   material_unfavorable_months_trailing_6, ytd_forecast_variance
            FROM mart_opex_management_v2
            WHERE period = (SELECT max(period) FROM mart_opex_management_v2)
              AND variance_classification = 'Structural Overrun'
            ORDER BY abs(forecast_variance) DESC LIMIT 1
            """
        ).fetchone()
        issues = connection.execute(
            """
            SELECT severity, issue_type, entity_name, metric, actual_value, threshold
            FROM mart_management_issue_register
            WHERE period = (SELECT max(period) FROM mart_management_issue_register)
            ORDER BY CASE severity WHEN 'High' THEN 1 ELSE 2 END, issue_type, entity_name
            """
        ).fetchall()
        scenarios = connection.execute(
            """
            SELECT scenario_name, scenario_revenue, scenario_gross_margin_pct,
                   scenario_operating_expense, scenario_operating_contribution
            FROM mart_scenario_analysis ORDER BY display_order
            """
        ).fetchall()
        mix = connection.execute(
            """
            SELECT member_name, revenue_mix_change_pct, mix_effect_bps, margin_rate_effect_bps
            FROM mart_margin_analysis
            WHERE year = (SELECT max(year) FROM mart_margin_analysis) AND dimension_type = 'Product'
            ORDER BY revenue_mix_change_pct DESC LIMIT 2
            """
        ).fetchall()
    finally:
        connection.close()

    (
        period,
        revenue,
        revenue_yoy,
        gross_margin,
        margin_bps,
        operating_expense,
        operating_contribution,
        operating_margin,
        forecast_accuracy,
        gross_pipeline,
        weighted_pipeline,
        pipeline_coverage,
        top_10_share,
    ) = latest
    previous_year, previous_revenue, previous_margin, _ = annual[-2]
    current_year, current_revenue, current_margin, current_contribution = annual[-1]
    customer_name, customer_revenue, customer_margin, customer_margin_bps, customer_rank, tickets, hours = customer
    region_name, region_accuracy, region_growth, region_margin, region_pipeline = region
    department, account, opex_variance, persistence, ytd_opex_variance = opex

    lines = [
        "# Management Insight Pack",
        "",
        f"Deterministic executive summary through `{period}`. Every statement is generated from reconciled V2 marts; no AI or scenario prediction is used.",
        "",
        "## Executive KPI Snapshot",
        "",
        "| KPI | Value |",
        "| --- | ---: |",
        f"| Monthly revenue | {currency(float(revenue))} |",
        f"| Revenue YoY | {percent(float(revenue_yoy))} |",
        f"| Gross margin | {percent(float(gross_margin))} |",
        f"| Gross margin YoY | {float(margin_bps):,.0f} bps |",
        f"| Operating contribution | {currency(float(operating_contribution))} |",
        f"| Operating contribution margin | {percent(float(operating_margin))} |",
        f"| Forecast accuracy | {percent(float(forecast_accuracy))} |",
        f"| Weighted pipeline coverage | {float(pipeline_coverage):.2f}x |",
        f"| Top 10 customer revenue | {percent(float(top_10_share))} |",
        "",
        "## Revenue & Margin",
        "",
        f"Full-year revenue increased from {currency(float(previous_revenue))} in {previous_year} to {currency(float(current_revenue))} in {current_year}, while gross margin declined from {percent(float(previous_margin))} to {percent(float(current_margin))}.",
        f"In {period}, revenue increased {percent(float(revenue_yoy))} YoY and gross margin changed {float(margin_bps):,.0f} bps YoY.",
        "",
        "The supported product-mix bridge shows:",
    ]
    for member_name, mix_change, mix_effect, margin_effect in mix:
        lines.append(
            f"- {member_name}: revenue mix changed {float(mix_change) * 100:+.1f} points; mix effect {float(mix_effect):+.0f} bps; margin-rate effect {float(margin_effect):+.0f} bps."
        )

    lines.extend(
        [
            "",
            "## Customer Profitability",
            "",
            f"{customer_name} ranks #{customer_rank} by revenue at {currency(float(customer_revenue))}. Its gross margin is {percent(float(customer_margin))}, a change of {float(customer_margin_bps):,.0f} bps YoY, with {tickets:,} support tickets and {hours:,} implementation hours recorded for the year.",
            "",
            "## Forecast Accuracy",
            "",
            f"{region_name} has the lowest current regional forecast accuracy at {percent(float(region_accuracy))}. Its revenue growth is {percent(float(region_growth))}, gross margin is {percent(float(region_margin))}, and weighted pipeline coverage is {float(region_pipeline):.2f}x.",
            "",
            "## Pipeline",
            "",
            f"Gross pipeline is {currency(float(gross_pipeline))}; probability-weighted pipeline is {currency(float(weighted_pipeline))}. Coverage declined from {float(pipeline_prior):.2f}x six months earlier to {float(pipeline_coverage):.2f}x in {period}.",
            "",
            "## Operating Expense",
            "",
            f"{department} / {account} is classified as a structural overrun after {persistence} material unfavorable months in the trailing six. Current forecast variance is {currency(float(opex_variance))}; YTD variance is {currency(float(ytd_opex_variance))}.",
            f"Total monthly operating expense is {currency(float(operating_expense))}; full-year operating contribution is {currency(float(current_contribution))}.",
            "",
            "## Scenario Analysis",
            "",
            "These are deterministic what-if calculations, not predictions.",
            "",
            "| Scenario | Revenue | Gross Margin | OpEx | Operating Contribution |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for scenario_name, scenario_revenue, scenario_margin, scenario_opex, scenario_contribution in scenarios:
        lines.append(
            f"| {scenario_name} | {currency(float(scenario_revenue))} | {percent(float(scenario_margin))} | {currency(float(scenario_opex))} | {currency(float(scenario_contribution))} |"
        )

    lines.extend(
        [
            "",
            "## Management Issues",
            "",
            f"The latest issue register contains {len(issues)} open or monitored items:",
            "",
        ]
    )
    for severity, issue_type, entity_name, metric, actual_value, threshold in issues:
        lines.append(
            f"- **{severity}: {issue_type} — {entity_name}.** {metric}: {float(actual_value):,.2f}; rule threshold: {float(threshold):,.2f}."
        )

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "The pack identifies measured financial and operational patterns. It does not assert unobserved operational causes, forecast future results, or replace management judgment.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=PROJECT_ROOT / "data" / "curated" / "finance_analytics.duckdb",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "management-insight-pack.md",
    )
    args = parser.parse_args()
    generate_insight_pack(args.database, args.output)
    print(f"Generated {args.output.resolve()}")


if __name__ == "__main__":
    main()
