# V3 AI-Assisted Executive Insight Architecture

## Design Principle

V3 preserves **trusted facts first, AI interpretation second**. The model does not read raw source extracts, query DuckDB, calculate finance metrics, create issue severity, or override deterministic business rules.

```text
V1/V2 verified marts
        |
        v
Data-quality and reconciliation gate
        |
        v
Stable evidence and entity IDs
        |
        v
Deterministic issue prioritization
        |
        v
Provider-neutral AI service
        |
        v
Pydantic structured-output contract
        |
        v
Semantic business guardrails
        |
        v
Executive presentation with deterministic values
```

## Verified Evidence Package

`finance_ai/evidence.py` derives the latest complete period from `mart_executive_kpis` and reads only verified V2 marts. The package contains:

- executive KPI evidence IDs;
- twelve priority issues selected from the latest issue register;
- customer, margin, forecast, pipeline, OpEx, and regional evidence IDs;
- Base, Upside, and Downside scenario evidence;
- an entity catalog;
- V1/V2 control status; and
- source-to-fact-to-mart reconciliation status.

Each `EvidenceItem` includes a stable ID, metric, numeric value, deterministic display value, unit, source field, period, and entity reference. AI output references the ID only. The application resolves the visible value after validation, so the model is never the numeric source of truth.

## Issue Prioritization

`finance_ai/prioritization.py` scores latest-period issues before any AI call using:

- deterministic severity;
- normalized threshold breach;
- forward-looking relevance for forecast and pipeline;
- company-wide impact;
- trailing-period persistence for structural OpEx; and
- revenue-rank relevance for customer profitability.

Selection first retains the highest-scoring issue from every triggered rule type, then fills remaining slots by score to a default limit of twelve. High deterministic severity sets a `high` minimum priority; Medium sets `medium`. AI cannot downgrade these bounds or elevate a solely Medium issue to High.

## Structured Output

Pydantic models use strict types, required fields, forbidden extra fields, constrained enums, bounded list sizes, and stable reference formats. The AI returns narrative fields plus `issueIds`, `evidenceIds`, and `entityIds`. `knownFacts` contains evidence IDs rather than free-form factual claims.

The OpenAI adapter uses the Responses API structured-output parser with `ExecutiveInsightOutput` as the runtime schema. JSON-shaped prose alone is not accepted.

## Business Guardrails

After schema validation, `finance_ai/guardrails.py` rejects responses with:

- unknown or duplicate issue, evidence, entity, or insight IDs;
- numeric claims in AI-authored prose;
- unsupported causal assertions;
- deterministic priority downgrades;
- unsupported promotion of non-High issues to High; or
- insights when no deterministic priority issues exist.

The prohibition on AI-authored numbers is deliberate. Numeric values are joined from the verified evidence registry during presentation. Terms such as `root cause` may be used to identify an unresolved question, while assertions such as `caused`, `led to`, or `due to` are rejected.

## Trusted Data Gate

Before provider invocation, the service requires:

- all V1 controls to pass;
- all V2 controls to pass;
- every required V2 mart to exist;
- all reconciliation measures to agree within tolerance; and
- a latest complete executive period.

A failed data-quality or reconciliation gate returns a safe `trusted_data_validation_failed` diagnostic and does not call the provider. Provider errors and guardrail failures use separate safe categories.

## Provider Boundary

`AIInsightProvider` defines one operation: generate a typed executive insight response from an `EvidencePackage`. OpenAI-specific SDK usage and credentials exist only in `finance_ai/providers/openai_provider.py`. A future Azure OpenAI or Microsoft Foundry adapter can implement the same interface without changing finance logic, schemas, guardrails, or presentation.

Configuration is centralized through environment variables documented in `.env.example`. `OPENAI_API_KEY` is read server-side only.

## Prompt Injection Boundary

Labels and descriptions are serialized inside a delimited data payload. The provider instructions explicitly classify every package field as untrusted data. More importantly, stable reference allowlists, strict schemas, numeric restrictions, entity validation, and semantic guardrails remain authoritative even if a label resembles an instruction.

## Interface

`app/server.py` uses the Python standard library to serve the executive screen and two endpoints:

- `GET /api/context` returns verified KPIs, priority issues, trust status, and developer context.
- `POST /api/insights` performs one gated provider generation and returns only validated presentation data.

This small app layer preserves the Python/DuckDB workflow and does not duplicate analytical logic in browser code.

## Generated Artifact

`scripts/generate_ai_insights.py` explicitly performs a live call and writes `outputs/ai-executive-insights.md` only after schema and business validation. The artifact is ignored by default and begins with a synthetic-data label. The deterministic `outputs/management-insight-pack.md` remains unchanged.
