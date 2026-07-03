# Insurance Claims Streamlit Dashboard

For a detailed Windows walkthrough, see
[STREAMLIT_GETTING_STARTED.md](STREAMLIT_GETTING_STARTED.md).

The dashboard reads these dbt marts from BigQuery:

- `mart_claims_current`
- `mart_claims_weekly`
- `mart_claim_transitions_weekly`
- `mart_claims_weekly_metrics`
- `mart_claims_monthly`
- `mart_claims_monthly_metrics`

It includes a demo mode, so the interface can be explored before BigQuery
authentication is configured.

The dashboard supports Weekly and Monthly metric granularity. Historical
deltas become available after at least two source snapshot periods exist.

## 1. Install Python

Install Python 3.11 or 3.12 for Windows and enable the installer option that
adds Python to `PATH`.

Verify:

```powershell
python --version
```

## 2. Create the virtual environment

Run these commands from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r dashboard\requirements.txt
```

If PowerShell blocks activation, use the virtual environment executable
directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r dashboard\requirements.txt
```

## 3. Configure BigQuery authentication

For local development, install the Google Cloud CLI and create Application
Default Credentials:

```powershell
gcloud auth application-default login
gcloud config set project ray-project-500821
```

The authenticated identity needs permission to run BigQuery jobs and read the
dbt mart dataset.

Do not commit service-account JSON keys or `secrets.toml`.

## 4. Configure the mart dataset

Copy the example configuration:

```powershell
Copy-Item dashboard\.streamlit\secrets.toml.example dashboard\.streamlit\secrets.toml
```

Edit `dashboard/.streamlit/secrets.toml`:

```toml
[bigquery]
project_id = "ray-project-500821"
marts_dataset = "YOUR_DBT_TARGET_MARTS_DATASET"
location = "US"
```

The dataset usually ends with `_marts`. Use the exact dataset visible in the
BigQuery console after running dbt.

## 5. Start the dashboard

With the virtual environment activated:

```powershell
streamlit run dashboard\streamlit_app.py
```

Without activating it:

```powershell
.\.venv\Scripts\streamlit.exe run dashboard\streamlit_app.py
```

Streamlit normally opens `http://localhost:8501`.

## 6. Switch between demo and BigQuery

Use the sidebar data-source selector:

- **Demo data** displays bundled sample records.
- **BigQuery** queries the configured mart dataset.

BigQuery results are cached for ten minutes. Use **Refresh data** in the
sidebar to clear the cache immediately.

## Streamlit Community Cloud authentication

Local `gcloud auth application-default login` credentials are not available
inside Streamlit Community Cloud.

For the deployed app:

1. Create a dedicated, least-privilege Google Cloud service account.
2. Grant it permission to run BigQuery jobs and read `dbt_rma_marts`.
3. Generate a new key. Do not reuse any previously exposed key.
4. Open the deployed app and select **Manage app**.
5. Open **Settings → Secrets**.
6. Copy the structure from
   `.streamlit/secrets.streamlit-cloud.toml.example`.
7. Replace every placeholder with values from the new service-account JSON.
8. Save the secrets and reboot the app.

Never commit the completed service-account configuration or JSON key to
GitHub.

## Production deployment

Prefer deploying to a Google Cloud runtime such as Cloud Run with an attached
service account. Application Default Credentials allow the same application
code to authenticate locally and in Google Cloud without embedding credentials
in the repository.
