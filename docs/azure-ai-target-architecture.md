# Azure AI Target Architecture

## Portable-to-Microsoft Mapping

```text
Current portable implementation       Microsoft target
--------------------------------       ----------------
DuckDB / Parquet                  ->   Fabric Lakehouse, Warehouse, or Azure SQL
Python analytical pipeline        ->   Fabric notebooks or Data Factory pipelines
Deterministic issue register      ->   Fabric governed analytical tables
Power BI model specification      ->   Power BI semantic model
Verified evidence package         ->   Governed orchestration service
AIInsightProvider                 ->   Azure OpenAI / Microsoft Foundry deployment
Structured validated output       ->   Power BI / Excel / Copilot Studio
```

Target flow:

```text
Fabric / Azure SQL / OneLake
              |
              v
Power BI Semantic Model
              |
              v
Verified Finance Metrics and Issue Register
              |
              v
Evidence Builder and Trusted Data Gate
              |
              v
Microsoft Foundry / Azure OpenAI Deployment
              |
              v
Structured Output and Business Guardrails
              |
              v
Power BI / Excel / Copilot Studio
```

## Provider Portability

The current OpenAI adapter is isolated behind `AIInsightProvider`. An Azure adapter would translate centralized model configuration and identity into the same typed input/output contract. Evidence selection, priority bounds, schema validation, semantic guardrails, and presentation remain provider-neutral.

## Security Target

- **Microsoft Entra ID:** authenticate users and workloads.
- **Managed Identity:** remove long-lived provider credentials from application configuration.
- **Azure RBAC:** restrict data, model deployment, and monitoring access by role.
- **Private networking:** use private endpoints and controlled egress where required.
- **Microsoft Purview:** classify, catalog, and govern finance data and lineage.
- **Audit and monitoring:** retain evidence-package version, issue/evidence references, model deployment, response status, and guardrail diagnostics.

The target architecture exposes compact verified evidence rather than raw finance transactions to the model. Uncontrolled consumer tools should not receive direct raw-system access or permission to redefine governed financial measures.

## Deployment Boundary

V3 documents this Microsoft target but does not deploy Fabric, Azure OpenAI, Foundry, Entra, networking, or Office integrations.
