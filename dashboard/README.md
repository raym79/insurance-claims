# Insurance Claims Streamlit Dashboard

The dashboard entry point is `dashboard/streamlit_app.py`. For a detailed
Windows and virtual-environment walkthrough, see the local
`STREAMLIT_GETTING_STARTED.md` guide.

**Live dashboard:** [Insurance Claims Dashboard](https://insurance-claims-gkcp4jjuwyqfra8pgbwezj.streamlit.app/)

## Dashboard behavior

The KPI cards above the tabs use the latest available report week:

- **Active Claims**: Open claims that have never previously been closed.
- **Closed Claims**: Claims whose latest weekly status is Closed.
- **Re-opened Claims**: Open claims with at least one earlier Closed snapshot.
- **Claim Value**: Total USD trailer value across Active, Closed, and
  Re-opened claims in the latest week.

When a prior week exists, the small KPI delta is:

```text
latest available week - previous available week
```

The cards are not affected by filters inside the tabs.

## Tabs

### Weekly Review

- Select a report-week date range.
- Filter by Provider (`source`), Carrier (`carrier_name`), and Country.
- Choose Claim Count or Claim Value (USD).
- Review the maintained WBR waterfall across week columns.
- The rightmost WoW column compares the last selected week with its previous
  available week.

### Monthly Review

The Monthly Review has the same filters and waterfall. Month columns replace
week columns, and the rightmost MoM column compares the last selected month
with its previous available month.

### WBR waterfall

Both review tabs use this fixed order and indentation:

```text
ACTIVE CASES
    In Process - Investigating
    Waiting For Reply From Insurance
        Found
        Not Found / Potential Claim
        Not In Network
CLOSED CASES
    Found And Returned
        Carrier Picked Up
        Found -Sent To Towing Yard
        Found - Recovered
        Not Liable Due To No Response
    Not Found
        Not Liable
        Liable
RE-OPEN CLAIMS
```

### Current Claims

Shows the latest available state for every claim. Filters appear in this
order:

1. Country
2. Status
3. Provider
4. Carrier
5. Claim Number

Headers use Title Case. Internal `claim_snapshot_key` and `snapshot_date`
columns are omitted from the table and CSV download.

### Transitions

Shows claim-level changes between available weekly observations. New and
unchanged claims are excluded. Filters are Country, Status, Provider, Carrier,
Transition Type, and Claim Number.

Possible transition types are:

- `OPEN_TO_CLOSED`
- `CLOSED_TO_OPEN`
- `STATUS_CHANGED`

Headers use Title Case. Internal `claim_snapshot_key` and `snapshot_date`
columns are omitted from the table and CSV download.

## Required BigQuery marts

- `mart_claims_current`
- `mart_claims_weekly`
- `mart_claim_transitions_weekly`
- `mart_claims_weekly_metrics`
- `mart_claims_monthly`
- `mart_claims_monthly_metrics`

WoW requires two distinct weekly periods. MoM requires two distinct monthly
periods.

## Local installation

Install Python 3.11 or 3.12, then run from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r dashboard\requirements.txt
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Activation is optional. Commands can use executables inside `.venv` directly.

## Local BigQuery authentication

Install the Google Cloud CLI and create Application Default Credentials:

```powershell
gcloud auth application-default login
gcloud config set project ray-project-500821
```

The authenticated identity must be able to create BigQuery jobs and read the
mart dataset.

## Local configuration

Copy the safe example:

```powershell
Copy-Item dashboard\.streamlit\secrets.toml.example dashboard\.streamlit\secrets.toml
```

Configure the local file:

```toml
[bigquery]
project_id = "ray-project-500821"
marts_dataset = "dbt_rma_marts"
location = "US"
```

`dashboard/.streamlit/secrets.toml` is excluded from Git.

## Start the dashboard

With the virtual environment activated:

```powershell
streamlit run dashboard\streamlit_app.py
```

Without activation:

```powershell
.\.venv\Scripts\streamlit.exe run dashboard\streamlit_app.py
```

Streamlit normally opens `http://localhost:8501`.

The sidebar can switch between BigQuery and bundled Demo data. BigQuery
results are cached for ten minutes; use **Refresh data** after rebuilding dbt
models.

## Streamlit Community Cloud

Local Application Default Credentials are not available in Streamlit Cloud.
In **Manage app -> Settings -> Secrets**, configure:

- `[bigquery]` with project, mart dataset, and location.
- `[gcp_service_account]` using a dedicated least-privilege service account.

Use `.streamlit/secrets.streamlit-cloud.toml.example` as the safe template.
Never commit the completed secret configuration or a service-account JSON
key.

## Rebuild after model changes

If metric dimensions or schemas change:

```powershell
dbt build --full-refresh --select mart_claims_weekly_metrics mart_claims_monthly_metrics
```

For a complete rebuild:

```powershell
dbt build --full-refresh
```
