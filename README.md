# Insurance Claims Analytics

An end-to-end Business Intelligence and Analytics Engineering portfolio
project that transforms historical insurance-claim snapshots in BigQuery into
tested analytical marts and an interactive Streamlit dashboard.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://insurance-claims-gkcp4jjuwyqfra8pgbwezj.streamlit.app/)

## Business problem

Operations teams need more than a current claim list. They need to understand:

- How many claims are active, closed, or reopened.
- How the claim portfolio changes week over week and month over month.
- Which provider, carrier, country, and WBR category drive the results.
- Which individual claims transitioned from Open to Closed or Closed to Open.
- How much trailer value is associated with the claim portfolio.

This project converts append-only operational snapshots into current-state,
historical-trend, and claim-transition datasets suitable for recurring
business reviews.

## Architecture

```text
BigQuery historical source
    -> dbt staging models
    -> dbt intermediate business logic
    -> tested current, weekly, monthly, and transition marts
    -> Streamlit dashboard
```

Physical source:

```text
ray-project-500821.trailer_claims.insurance_claims_statu_history
```

The source grain is one row per `snapshot_date` and `claim_number`. Historical
snapshots are preserved so the project can calculate point-in-time state,
WoW/MoM movement, and claim-level status transitions.

## Tools and technologies

| Area | Tools | How they are used |
|---|---|---|
| Cloud data warehouse | Google BigQuery | Stores the append-only source and partitioned analytical marts |
| Transformation | dbt, SQL, Jinja | Builds modular staging, intermediate, weekly, monthly, and transition models |
| BigQuery optimization | Partitioning and clustering | Organizes historical tables for period and claim-level access |
| Data quality | dbt tests, `dbt_utils`, `dbt_expectations` | Validates keys, accepted values, date ranges, and model grain |
| Business intelligence | Streamlit | Delivers KPI cards, review waterfalls, filters, detail tables, and CSV exports |
| Application development | Python, pandas | Queries BigQuery and constructs interactive pivots and filtered tables |
| Cloud authentication | Google Cloud ADC and service accounts | Supports secure local and Streamlit Cloud access without committed credentials |
| Version control and deployment | Git, GitHub, Streamlit Community Cloud | Tracks changes and deploys the dashboard from the repository |

## Data modeling

The project follows a layered dbt design:

### Staging

`stg_insurance_claims` standardizes the raw BigQuery table:

- Cleans string dimensions.
- Safely converts dates and numeric values.
- Requires valid claim and snapshot identifiers.
- Preserves Provider (`source`), Carrier, and Country.

### Intermediate

The intermediate layer contains reusable business logic:

- WBR Tier 1, Tier 2, and Tier 3 classification.
- Sunday-through-Saturday report-week calculations.
- Reopened-claim detection using earlier snapshots.
- Currency conversion to USD.
- Surrogate claim-snapshot keys.

### Marts

The dashboard consumes six purpose-built marts:

- `mart_claims_current`
- `mart_claims_weekly`
- `mart_claim_transitions_weekly`
- `mart_claims_weekly_metrics`
- `mart_claims_monthly`
- `mart_claims_monthly_metrics`

The metric marts include Provider, Carrier, Country, status, and WBR
dimensions so dashboard filters are applied before aggregation.

## Dashboard capabilities

- Latest-week KPIs for Active, Closed, and Re-opened claims and total USD
  claim value.
- Weekly Review with date-range, Provider, Carrier, and Country filters.
- Monthly Review using the same controlled WBR hierarchy.
- WoW and MoM comparisons for the last selected period.
- Claim-count and claim-value views.
- Current Claims detail with business-friendly Title Case headers.
- Claim-level status transitions with Transition Type filtering.
- Downloadable CSV outputs.
- Demo mode for exploring the application without BigQuery credentials.

## Data quality and governance

The project tests:

- Unique `(snapshot_date, claim_number)` source grain.
- Unique and non-null claim-snapshot keys.
- One claim state per weekly and monthly period.
- Accepted claim status, transition, and WBR values.
- Valid report-week and calendar-month ranges.
- Nonnegative monetary values.
- Metric-table uniqueness across period and dashboard dimensions.

Secrets, service-account keys, virtual environments, and generated dbt
artifacts are excluded from Git. Safe placeholder templates are committed for
local and Streamlit Cloud configuration.
