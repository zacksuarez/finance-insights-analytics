# AI Insight Consumption

## Power BI Integration Path

No live Power BI connection is implemented in V3. A production implementation could publish validated insight output as a governed table with one row per insight and child tables for issue/evidence references.

Supported future patterns include:

- an executive narrative tile showing the validated summary;
- an insight table filtered by period, category, and priority;
- drill-through from an insight to deterministic issue and evidence IDs;
- issue annotations alongside existing KPI visuals;
- a Fabric semantic-model table refreshed only after guardrails pass; and
- embedded narrative that resolves numeric values from governed measures rather than model prose.

The AI output should not become a second measure layer. Power BI measures and V2 marts remain authoritative.

## Excel Integration Path

Validated insight records could flow to:

- an executive commentary worksheet;
- month-end reporting templates;
- a management action register;
- an exported commentary pack; or
- Analyze in Excel alongside trusted semantic-model measures.

Future Office Scripts or Power Automate flows should move only validated output and should retain period, insight ID, issue IDs, evidence IDs, generation timestamp, model configuration, and validation status for auditability. V3 does not implement Office automation.

## Management Pack Boundary

The deterministic management insight pack remains the reproducible baseline. AI-assisted commentary is a separate, explicitly generated artifact and must never overwrite the deterministic pack.
