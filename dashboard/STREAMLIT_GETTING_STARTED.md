# Start the Insurance Claims Streamlit Dashboard Locally

This guide walks through running the dashboard on Windows from a fresh setup.

The dashboard entry point is:

```text
dashboard/streamlit_app.py
```

## 1. Install Python

Install Python 3.11 or 3.12 from:

<https://www.python.org/downloads/windows/>

During installation:

1. Select **Add Python to PATH**.
2. Select **Install launcher for all users**, if available.
3. Finish the installation.
4. Close and reopen PowerShell or VS Code.

Verify the installation:

```powershell
python --version
```

Expected output resembles:

```text
Python 3.12.x
```

If `python` is not recognized, try:

```powershell
py --version
```

## 2. Open the project directory

Open PowerShell and navigate to the repository:

```powershell
cd "C:\Users\wlin9\OneDrive\Documents\dbt project\insurance-claims"
```

Confirm the dashboard files exist:

```powershell
Get-ChildItem dashboard
```

You should see:

```text
streamlit_app.py
requirements.txt
README.md
STREAMLIT_GETTING_STARTED.md
```

## 3. Create a virtual environment

### What is a virtual environment?

A Python virtual environment, commonly called a **venv**, is a project-specific
Python workspace. It contains:

- Its own Python executable.
- Its own `pip` package installer.
- Its own installed packages, such as Streamlit and the BigQuery client.
- Small scripts used to activate the environment.

It does **not** create a virtual machine, container, or second copy of Windows.
It is simply a directory that tells Python where this project's packages live.

For this project, the directory is:

```text
insurance-claims/.venv/
```

### Why use a venv?

Different Python projects often require different package versions. For
example:

```text
Project A needs Streamlit 1.x
Project B needs a different Streamlit or pandas version
```

If everything is installed globally, updating one project can accidentally
break another. A venv prevents that by isolating each project's packages.

Benefits include:

- Package changes affect only this project.
- The global Python installation stays clean.
- `requirements.txt` can reproduce the environment on another computer.
- Removing the environment does not remove your source code.
- VS Code can use the correct Python interpreter for this project.

### What gets committed to Git?

The `.venv` directory should never be committed. It can be large, contains
machine-specific files, and can always be recreated.

This repository's `.gitignore` already excludes:

```gitignore
.venv/
```

The files that describe the environment, such as `requirements.txt`, should be
committed.

### Create the environment once

From the repository root, run:

```powershell
python -m venv .venv
```

If you use the Python launcher:

```powershell
py -m venv .venv
```

The `.venv` directory is already excluded from Git.

Creating the venv is normally a **one-time setup**. Do not run this command
every day. Run it again only when:

- Setting up the project on a different computer.
- Recreating a deleted or damaged environment.
- Intentionally starting over with a clean environment.

## 4. Activate the virtual environment

### What does activation do?

Activation temporarily changes the current terminal's `PATH`. When you type:

```powershell
python
pip
streamlit
```

PowerShell uses the executables inside `.venv` before any globally installed
versions.

Activation does not permanently change Windows. It applies only to the current
terminal window.

Run:

```powershell
.\.venv\Scripts\Activate.ps1
```

After activation, the PowerShell prompt should begin with:

```text
(.venv)
```

Confirm that the venv's Python is being used:

```powershell
Get-Command python
python -m pip --version
```

The displayed paths should include:

```text
insurance-claims\.venv\
```

If PowerShell reports that script execution is disabled, run this once in the
current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the environment again:

```powershell
.\.venv\Scripts\Activate.ps1
```

This execution-policy change applies only to the current PowerShell session.

### How often should it be activated?

Activate the venv whenever you:

- Open a new PowerShell window.
- Open a new VS Code terminal.
- Restart Windows.
- Return to this project after working elsewhere.

You do **not** need to recreate the environment or reinstall packages each
time. The normal routine is:

```powershell
cd "C:\Users\wlin9\OneDrive\Documents\dbt project\insurance-claims"
.\.venv\Scripts\Activate.ps1
streamlit run dashboard\streamlit_app.py
```

### How to leave the environment

When finished, stop Streamlit with `Ctrl+C`, then run:

```powershell
deactivate
```

The `(.venv)` prefix disappears. Closing the terminal also deactivates the
environment automatically.

### Activation is convenient, but optional

Activation only provides shorter commands. You can always call the environment
directly without activating it:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r dashboard\requirements.txt
.\.venv\Scripts\streamlit.exe run dashboard\streamlit_app.py
```

This is useful in scripts, scheduled tasks, or terminals where activation is
blocked.

### Select the venv in VS Code

To make VS Code use this environment:

1. Open the repository in VS Code.
2. Press `Ctrl+Shift+P`.
3. Choose **Python: Select Interpreter**.
4. Select the interpreter under `.venv\Scripts\python.exe`.

After selecting it, new Python terminals usually activate the environment
automatically.

## 5. Install dashboard packages

Upgrade `pip`:

```powershell
python -m pip install --upgrade pip
```

Install the dashboard dependencies:

```powershell
python -m pip install -r dashboard\requirements.txt
```

Verify Streamlit:

```powershell
streamlit version
```

## 6. Start in demo mode first

The dashboard includes sample data, so BigQuery authentication is not required
for the first launch.

Run:

```powershell
streamlit run dashboard\streamlit_app.py
```

Streamlit should open:

<http://localhost:8501>

If the browser does not open automatically, copy that address into a browser.

Select **Demo data** under **Choose data source** in the sidebar. Confirm that
you can see:

- Latest-week KPI cards.
- Weekly Review.
- Monthly Review.
- Current Claims.
- Transitions.
- CSV download buttons.

With only one demo or source period, WoW and MoM comparisons are unavailable.
They appear after at least two periods exist.

## 7. Stop the dashboard

Return to the PowerShell window running Streamlit and press:

```text
Ctrl+C
```

## 8. Install and authenticate the Google Cloud CLI

To read BigQuery locally, install the Google Cloud CLI:

<https://cloud.google.com/sdk/docs/install-sdk#windows>

Close and reopen PowerShell after installation.

Sign in:

```powershell
gcloud auth login
```

Create Application Default Credentials for Python:

```powershell
gcloud auth application-default login
```

Set the default project:

```powershell
gcloud config set project ray-project-500821
```

These credentials are stored outside the repository. Do not download or commit
service-account keys unless your security team specifically requires them.

## 9. Configure the BigQuery mart dataset

Create the local Streamlit secrets file:

```powershell
Copy-Item dashboard\.streamlit\secrets.toml.example dashboard\.streamlit\secrets.toml
```

Open:

```text
dashboard/.streamlit/secrets.toml
```

Set the actual dbt mart dataset:

```toml
[bigquery]
project_id = "ray-project-500821"
marts_dataset = "YOUR_ACTUAL_MARTS_DATASET"
location = "US"
```

For example, if BigQuery shows a dataset named `dbt_wlin_marts`:

```toml
[bigquery]
project_id = "ray-project-500821"
marts_dataset = "dbt_wlin_marts"
location = "US"
```

Use the dataset containing:

- `mart_claims_current`
- `mart_claims_weekly`
- `mart_claim_transitions_weekly`
- `mart_claims_weekly_metrics`
- `mart_claims_monthly`
- `mart_claims_monthly_metrics`

The real `secrets.toml` file is excluded from Git. The example file remains
safe to commit because it contains no credentials.

## 10. Start with BigQuery data

Start Streamlit:

```powershell
streamlit run dashboard\streamlit_app.py
```

In the sidebar:

1. Select **BigQuery** under **Choose data source**.
2. Confirm the project ID.
3. Confirm the mart dataset.
4. Confirm the BigQuery location.
5. Select **Refresh data**.

The app caches query results for ten minutes to reduce repeated BigQuery
queries. Use **Refresh data** whenever dbt rebuilds the marts and you want to
see the new results immediately.

### BigQuery authentication on Streamlit Community Cloud

Your local `gcloud auth application-default login` session does not travel to
Streamlit Community Cloud. The deployed app must receive credentials through
Streamlit's encrypted Secrets settings.

Use a newly generated service-account key. Never reuse a key that was exposed
in a terminal, message, screenshot, or Git commit.

1. Create or select a dedicated service account in Google Cloud.
2. Grant only the permissions required to run BigQuery jobs and read the mart
   dataset.
3. Generate and download a new JSON key.
4. In Streamlit Cloud, open **Manage app → Settings → Secrets**.
5. Open this safe template:

```text
dashboard/.streamlit/secrets.streamlit-cloud.toml.example
```

6. Copy the template into Streamlit Cloud's Secrets field.
7. Replace every `REPLACE_...` placeholder with the corresponding value from
   the new JSON key.
8. Keep the `[bigquery]` values:

```toml
[bigquery]
project_id = "ray-project-500821"
marts_dataset = "dbt_rma_marts"
location = "US"
```

9. Save the secrets and reboot the app.

Do not put the completed cloud configuration in GitHub or in the example file.

## 11. Normal daily startup

Creating the venv and installing packages are one-time setup steps. On future
days, use:

```powershell
cd "C:\Users\wlin9\OneDrive\Documents\dbt project\insurance-claims"
.\.venv\Scripts\Activate.ps1
streamlit run dashboard\streamlit_app.py
```

You do not need to reinstall packages each time.

When finished:

```text
Ctrl+C
```

```powershell
deactivate
```

## 12. Run without activating the environment

You can start Streamlit directly from the virtual environment:

```powershell
.\.venv\Scripts\streamlit.exe run dashboard\streamlit_app.py
```

## 13. Update packages after requirements change

Activate the environment, then run:

```powershell
python -m pip install -r dashboard\requirements.txt
```

Use `python -m pip` instead of a bare `pip` command when possible. This makes
it explicit that packages are being installed for the currently selected
Python interpreter.

### Recreate the venv when necessary

If the environment becomes corrupted, it is safe to delete `.venv` and rebuild
it. Your application code and BigQuery data are not stored there.

After removing the old `.venv` directory, recreate it:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r dashboard\requirements.txt
```

Do not delete `.venv` as a normal daily step. Recreate it only to repair the
environment or perform a deliberately clean installation.

## 14. Dashboard reference

### KPI cards

The cards above the tabs use the latest available weekly period:

- **Active Claims**: Open claims that have never been Closed.
- **Closed Claims**: Claims currently Closed.
- **Re-opened Claims**: Open claims that were Closed in an earlier snapshot.
- **Claim Value**: Total USD value across all three groups.

The smaller KPI value is the latest week minus the previous available week.
Tab filters do not change these cards.

### Weekly Review and Monthly Review

Use Provider, Carrier, and Country filters to limit the waterfall. Provider is
the mart's `source` field. Select Claim Count or Claim Value and choose a date
range. The rightmost column compares the last selected period with its
previous available period.

### Current Claims

Filters are Country, Status, Provider, Carrier, and Claim Number. Table and CSV
headers use Title Case. Claim Snapshot Key and Snapshot Date are intentionally
hidden.

### Transitions

This tab contains only actual weekly status changes. It excludes new and
unchanged claims. Filters are Country, Status, Provider, Carrier, Transition
Type, and Claim Number. Claim Snapshot Key and Snapshot Date are intentionally
hidden.

## 15. Troubleshooting

### `python` is not recognized

Close and reopen PowerShell after installing Python. If needed, reinstall
Python and select **Add Python to PATH**.

### `streamlit` is not recognized

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then reinstall the requirements:

```powershell
python -m pip install -r dashboard\requirements.txt
```

### PowerShell blocks `Activate.ps1`

Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### BigQuery authentication error

Refresh Application Default Credentials:

```powershell
gcloud auth application-default login
```

Confirm your identity can run BigQuery jobs and read the mart dataset.

### BigQuery table was not found

Check the `marts_dataset` value. It must be a dataset name, not a table name or
the source dataset.

Confirm these tables exist inside it:

```text
mart_claims_current
mart_claims_weekly
mart_claim_transitions_weekly
mart_claims_weekly_metrics
mart_claims_monthly
mart_claims_monthly_metrics
```

### BigQuery location mismatch

Set `location` in `secrets.toml` to the same location as the mart dataset, such
as `US`, `EU`, or a regional location.

### The dashboard shows old data

Select **Refresh data** in the sidebar, or restart Streamlit:

```text
Ctrl+C
```

```powershell
streamlit run dashboard\streamlit_app.py
```

### Port 8501 is already in use

Use another port:

```powershell
streamlit run dashboard\streamlit_app.py --server.port 8502
```

Then open:

<http://localhost:8502>

## 16. Recommended workflow after dbt changes

Rebuild the marts:

```powershell
dbt build --select path:models/marts --full-refresh
```

Then refresh the Streamlit data from the sidebar.

The complete flow is:

```text
BigQuery source (`insurance_claims_statu_history`)
    -> dbt staging models
    -> dbt intermediate models
    -> dbt mart tables
    -> Streamlit dashboard
```
