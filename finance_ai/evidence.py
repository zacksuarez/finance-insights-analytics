"""Build a compact verified V3 evidence package from deterministic V2 marts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from finance_ai.models import (
    DataQualityStatus,
    EntityReference,
    EvidenceItem,
    EvidencePackage,
    PriorityIssue,
    ReconciliationStatus,
    ScenarioSummary,
)
from finance_ai.prioritization import entity_id, issue_evidence_id, prioritize_issues


REQUIRED_MARTS = {
    "mart_executive_kpis",
    "mart_customer_profitability_v2",
    "mart_customer_concentration_v2",
    "mart_margin_analysis",
    "mart_forecast_accuracy_v2",
    "mart_pipeline_analysis_v2",
    "mart_opex_management_v2",
    "mart_regional_performance_v2",
    "mart_management_issue_register",
    "mart_scenario_analysis",
}


def _display(value: float, unit: str) -> str:
    if unit == "currency":
        sign = "-" if value < 0 else ""
        magnitude = abs(value)
        if magnitude >= 1_000_000:
            return f"{sign}${magnitude / 1_000_000:.1f}M"
        if magnitude >= 1_000:
            return f"{sign}${magnitude / 1_000:.1f}K"
        return f"{sign}${magnitude:,.0f}"
    if unit == "percentage":
        return f"{value * 100:.1f}%"
    if unit == "basis_points":
        return f"{value:,.0f} bps"
    if unit == "ratio":
        return f"{value:.2f}x"
    return f"{value:,.0f}"


def _evidence(
    evidence_id: str,
    metric: str,
    value: float,
    unit: str,
    source: str,
    period: str,
    entity_id_value: str = "COMPANY_COMPANY_TOTAL",
    entity_name: str = "Company Total",
) -> EvidenceItem:
    numeric = float(value)
    return EvidenceItem(
        evidence_id=evidence_id,
        metric=metric,
        value=numeric,
        display_value=_display(numeric, unit),
        unit=unit,
        source=source,
        period=period,
        entity_id=entity_id_value,
        entity_name=entity_name,
    )


def _dict_rows(connection: duckdb.DuckDBPyConnection, query: str, parameters: list[Any] | None = None) -> list[dict[str, Any]]:
    rows = connection.execute(query, parameters or []).fetchall()
    columns = [item[0] for item in connection.description]
    return [dict(zip(columns, row)) for row in rows]


def _quality_status(connection: duckdb.DuckDBPyConnection) -> tuple[DataQualityStatus, ReconciliationStatus]:
    tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
    required_present = REQUIRED_MARTS.issubset(tables)
    v1 = _dict_rows(connection, "SELECT check_name, failure_count FROM dq_results")
    v2 = _dict_rows(connection, "SELECT check_name, failure_count FROM dq_v2_results")
    failed_controls = [
        f"{layer}:{row['check_name']}"
        for layer, rows in (("V1", v1), ("V2", v2))
        for row in rows
        if row["failure_count"] != 0
    ]
    reconciliations = _dict_rows(connection, "SELECT * FROM mart_reconciliation")
    tolerance = 0.01
    reconciliation_failures: list[str] = []
    for row in reconciliations:
        values = (float(row["source_total"]), float(row["fact_total"]), float(row["mart_total"]))
        if max(values) - min(values) > tolerance:
            reconciliation_failures.append(row["measure"])
    return (
        DataQualityStatus(
            passed=not failed_controls and required_present,
            v1_controls=len(v1),
            v2_controls=len(v2),
            failed_controls=failed_controls,
            required_marts_present=required_present,
        ),
        ReconciliationStatus(
            passed=not reconciliation_failures,
            tolerance=tolerance,
            checked_measures=len(reconciliations),
            failures=reconciliation_failures,
        ),
    )


def build_evidence_package(database_path: Path, issue_limit: int = 12) -> EvidencePackage:
    connection = duckdb.connect(str(database_path.resolve()), read_only=True)
    try:
        quality_status, reconciliation_status = _quality_status(connection)
        period = connection.execute("SELECT max(period) FROM mart_executive_kpis").fetchone()[0]
        if not period:
            raise ValueError("No complete executive period is available")

        kpi = _dict_rows(connection, "SELECT * FROM mart_executive_kpis WHERE period = ?", [period])[0]
        evidence: list[EvidenceItem] = [
            _evidence("REVENUE", "Revenue", kpi["revenue"], "currency", "mart_executive_kpis.revenue", period),
            _evidence("REV_GROWTH_YOY", "Revenue YoY Growth", kpi["revenue_yoy_pct"], "percentage", "mart_executive_kpis.revenue_yoy_pct", period),
            _evidence("GROSS_MARGIN", "Gross Margin", kpi["gross_margin_pct"], "percentage", "mart_executive_kpis.gross_margin_pct", period),
            _evidence("GROSS_MARGIN_YOY_BPS", "Gross Margin YoY Change", kpi["gross_margin_yoy_bps"], "basis_points", "mart_executive_kpis.gross_margin_yoy_bps", period),
            _evidence("OPERATING_CONTRIBUTION", "Operating Contribution", kpi["operating_contribution"], "currency", "mart_executive_kpis.operating_contribution", period),
            _evidence("FORECAST_ACCURACY", "Forecast Accuracy", kpi["forecast_accuracy_pct"], "percentage", "mart_executive_kpis.forecast_accuracy_pct", period),
            _evidence("WEIGHTED_PIPELINE", "Weighted Pipeline", kpi["weighted_pipeline"], "currency", "mart_executive_kpis.weighted_pipeline", period),
            _evidence("PIPELINE_COVERAGE", "Weighted Pipeline Coverage", kpi["pipeline_coverage"], "ratio", "mart_executive_kpis.pipeline_coverage", period),
            _evidence("TOP10_CUSTOMER_CONCENTRATION", "Top 10 Customer Revenue Share", kpi["top_10_customer_revenue_pct"], "percentage", "mart_executive_kpis.top_10_customer_revenue_pct", period),
        ]
        executive_ids = [item.evidence_id for item in evidence]

        issue_rows = _dict_rows(
            connection,
            "SELECT * FROM mart_management_issue_register WHERE period = ?",
            [period],
        )
        prioritized = prioritize_issues(issue_rows, issue_limit)
        priority_issues: list[PriorityIssue] = []
        for issue in prioritized:
            issue_evidence = _evidence(
                issue_evidence_id(issue["issue_id"]),
                issue["metric"],
                issue["actual_value"],
                "currency" if issue["metric"] == "Forecast Variance" else (
                    "basis_points" if "bps" in issue["metric"] else (
                        "ratio" if "Coverage" in issue["metric"] else "percentage"
                    )
                ),
                f"mart_management_issue_register.{issue['issue_id']}",
                issue["period"],
                issue["entity_id"],
                issue["entity_name"],
            )
            evidence.append(issue_evidence)
            issue["threshold"] = float(issue["threshold"])
            issue["actual_value"] = float(issue["actual_value"])
            issue.pop("supporting_metric", None)
            priority_issues.append(PriorityIssue.model_validate(issue))

        latest_year = int(period[:4])
        customer = _dict_rows(
            connection,
            """
            SELECT customer_id, customer_name, margin_change_bps, gross_margin_pct, revenue
            FROM mart_customer_profitability_v2
            WHERE year = ? ORDER BY margin_change_bps, customer_id LIMIT 1
            """,
            [latest_year],
        )[0]
        customer_entity = f"CUSTOMER_{customer['customer_id']}"
        customer_items = [
            _evidence("NORTHSTAR_MARGIN_CHANGE", "Customer Gross Margin Change", customer["margin_change_bps"], "basis_points", "mart_customer_profitability_v2.margin_change_bps", period, customer_entity, customer["customer_name"]),
            _evidence("NORTHSTAR_REVENUE", "Customer Revenue", customer["revenue"], "currency", "mart_customer_profitability_v2.revenue", period, customer_entity, customer["customer_name"]),
        ]
        evidence.extend(customer_items)

        west = _dict_rows(
            connection,
            "SELECT * FROM mart_regional_performance_v2 WHERE period = ? AND region = 'West'",
            [period],
        )[0]
        west_entity = "REGION_WEST"
        regional_items = [
            _evidence("WEST_FORECAST_ACCURACY", "West Forecast Accuracy", west["forecast_accuracy_pct"], "percentage", "mart_regional_performance_v2.forecast_accuracy_pct", period, west_entity, "West"),
            _evidence("WEST_PIPELINE_COVERAGE", "West Pipeline Coverage", west["pipeline_coverage"], "ratio", "mart_regional_performance_v2.pipeline_coverage", period, west_entity, "West"),
        ]
        evidence.extend(regional_items)

        opex = _dict_rows(
            connection,
            """
            SELECT * FROM mart_opex_management_v2
            WHERE period = ? AND variance_classification = 'Structural Overrun'
            ORDER BY abs(forecast_variance) DESC LIMIT 1
            """,
            [period],
        )[0]
        opex_entity = entity_id("Department / Account", f"{opex['department_name']} / {opex['account_name']}")
        opex_items = [
            _evidence("ENG_SOFTWARE_OVERRUN", "Engineering Software Forecast Variance", opex["forecast_variance"], "currency", "mart_opex_management_v2.forecast_variance", period, opex_entity, f"{opex['department_name']} / {opex['account_name']}"),
            _evidence("ENG_SOFTWARE_PERSISTENCE", "Material Months in Trailing Six", opex["material_unfavorable_months_trailing_6"], "count", "mart_opex_management_v2.material_unfavorable_months_trailing_6", period, opex_entity, f"{opex['department_name']} / {opex['account_name']}"),
        ]
        evidence.extend(opex_items)

        margin_rows = _dict_rows(
            connection,
            """
            SELECT member_name, mix_effect_bps, margin_rate_effect_bps
            FROM mart_margin_analysis
            WHERE year = ? AND dimension_type = 'Product'
            ORDER BY abs(mix_effect_bps) + abs(margin_rate_effect_bps) DESC LIMIT 2
            """,
            [latest_year],
        )
        margin_ids: list[str] = []
        for index, row in enumerate(margin_rows, start=1):
            member = row["member_name"]
            member_id = "PRODUCT_" + "_".join(member.upper().split())
            for effect_name, column in (("MIX_EFFECT", "mix_effect_bps"), ("MARGIN_RATE_EFFECT", "margin_rate_effect_bps")):
                evidence_id_value = f"MARGIN_{index}_{effect_name}"
                evidence.append(_evidence(evidence_id_value, f"{member} {effect_name.replace('_', ' ').title()}", row[column], "basis_points", f"mart_margin_analysis.{column}", period, member_id, member))
                margin_ids.append(evidence_id_value)

        scenario_rows = _dict_rows(connection, "SELECT * FROM mart_scenario_analysis ORDER BY display_order")
        scenarios: list[ScenarioSummary] = []
        for row in scenario_rows:
            prefix = "SCENARIO_" + row["scenario_name"].upper()
            revenue_id = prefix + "_REVENUE"
            margin_id = prefix + "_MARGIN"
            contribution_id = prefix + "_CONTRIBUTION"
            evidence.extend([
                _evidence(revenue_id, f"{row['scenario_name']} Scenario Revenue", row["scenario_revenue"], "currency", "mart_scenario_analysis.scenario_revenue", period),
                _evidence(margin_id, f"{row['scenario_name']} Scenario Gross Margin", row["scenario_gross_margin_pct"], "percentage", "mart_scenario_analysis.scenario_gross_margin_pct", period),
                _evidence(contribution_id, f"{row['scenario_name']} Scenario Operating Contribution", row["scenario_operating_contribution"], "currency", "mart_scenario_analysis.scenario_operating_contribution", period),
            ])
            scenarios.append(ScenarioSummary(
                scenario_name=row["scenario_name"],
                revenue_evidence_id=revenue_id,
                margin_evidence_id=margin_id,
                contribution_evidence_id=contribution_id,
            ))

        entities: dict[str, EntityReference] = {}
        for item in evidence:
            entity_type_value = item.entity_id.split("_", 1)[0].title()
            entities[item.entity_id] = EntityReference(entity_id=item.entity_id, entity_type=entity_type_value, entity_name=item.entity_name)
        for issue in priority_issues:
            entities[issue.entity_id] = EntityReference(entity_id=issue.entity_id, entity_type=issue.entity_type, entity_name=issue.entity_name)

        return EvidencePackage(
            period=period,
            executive_kpis=executive_ids,
            priority_issues=priority_issues,
            customer_insights=[item.evidence_id for item in customer_items],
            margin_insights=margin_ids,
            forecast_insights=["FORECAST_ACCURACY", "WEST_FORECAST_ACCURACY"],
            pipeline_insights=["WEIGHTED_PIPELINE", "PIPELINE_COVERAGE", "WEST_PIPELINE_COVERAGE"],
            opex_insights=[item.evidence_id for item in opex_items],
            regional_insights=[item.evidence_id for item in regional_items],
            scenario_summary=scenarios,
            evidence=evidence,
            entity_catalog=sorted(entities.values(), key=lambda item: item.entity_id),
            reconciliation_status=reconciliation_status,
            data_quality_status=quality_status,
        )
    finally:
        connection.close()
