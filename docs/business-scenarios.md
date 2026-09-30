# V1 Synthetic Business Scenario Manifest

This is a developer and reviewer reference for validating the deterministic synthetic dataset. Analytical outputs must derive findings from modeled data; they must not read this document as an answer source.

## Generation Contract

- Fixed seed: `20260930`
- Activity period: January 2024 through December 2025
- Fictional company, customer, vendor, and employee-owner names only
- Source files: ERP, CRM, EPM, sales pipeline, and operational KPI exports

## Embedded Truths

1. **Revenue growth with margin pressure:** 2025 revenue grows through customer expansion and a heavier services mix while product-level cost rates rise, reducing consolidated gross margin.
2. **Large-customer deterioration:** `CUST001`, Northstar Systems, grows revenue but shifts toward services and consumes materially more support and implementation effort. Its gross margin deteriorates.
3. **Regional forecast accuracy:** West-region revenue forecasts become increasingly biased above actuals through 2025; other regions retain low periodic forecast noise.
4. **Pipeline warning:** Probability-weighted pipeline coverage declines progressively in 2025 before year-over-year revenue growth slows materially in the final quarter.
5. **Structural OpEx overrun:** Engineering Software expense exceeds rolling Forecast every month rather than reversing as a timing difference.
6. **Customer concentration:** `CUST001` and four other large Enterprise customers create a meaningful, but not implausibly dominant, top-five revenue concentration.

## Validation Intent

Automated tests assert directional and material thresholds for every story. Thresholds are calculated from generated records and fail when the mechanics no longer produce the intended analytical pattern.
