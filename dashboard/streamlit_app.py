from __future__ import annotations

import os
import re
from datetime import date, datetime
from typing import Any

import pandas as pd
import streamlit as st
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError
from google.cloud import bigquery
from google.oauth2 import service_account


st.set_page_config(
    page_title="Insurance Claims Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


TABLES = {
    "current": "mart_claims_current",
    "weekly": "mart_claims_weekly",
    "weekly_transitions": "mart_claim_transitions_weekly",
    "weekly_metrics": "mart_claims_weekly_metrics",
    "monthly": "mart_claims_monthly",
    "monthly_metrics": "mart_claims_monthly_metrics",
}

PROJECT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
DATASET_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def secrets_section(name: str) -> dict[str, Any]:
    try:
        return dict(st.secrets.get(name, {}))
    except (FileNotFoundError, KeyError):
        return {}


def configured_value(name: str, default: str = "") -> str:
    values = secrets_section("bigquery")
    return str(os.getenv(f"BQ_{name.upper()}", values.get(name, default)))


def service_account_info() -> dict[str, Any]:
    values = secrets_section("gcp_service_account")
    private_key = values.get("private_key")
    if isinstance(private_key, str):
        values["private_key"] = private_key.replace("\\n", "\n")
    return values


def validate_identifier(
    value: str,
    pattern: re.Pattern[str],
    label: str,
) -> str:
    value = value.strip()
    if not value or not pattern.fullmatch(value):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value


@st.cache_resource
def bigquery_client(project_id: str, location: str) -> bigquery.Client:
    credentials_info = service_account_info()
    if credentials_info:
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return bigquery.Client(
            project=project_id,
            credentials=credentials,
            location=location,
        )
    return bigquery.Client(project=project_id, location=location)


@st.cache_data(ttl=600, show_spinner=False)
def query_mart(
    project_id: str,
    dataset: str,
    table: str,
    location: str,
) -> pd.DataFrame:
    project_id = validate_identifier(project_id, PROJECT_PATTERN, "project ID")
    dataset = validate_identifier(dataset, DATASET_PATTERN, "dataset")
    if table not in TABLES.values():
        raise ValueError(f"Unexpected mart table: {table!r}")

    sql = f"select * from `{project_id}.{dataset}.{table}`"
    client = bigquery_client(project_id, location)
    return client.query(sql).result().to_dataframe(create_bqstorage_client=False)


def add_transition_columns(frame: pd.DataFrame, delta_name: str) -> pd.DataFrame:
    result = frame.copy()
    result["status_changed"] = (
        result["previous_status"].notna()
        & (result["status"] != result["previous_status"])
    )
    result["transition_type"] = "NO_CHANGE"
    result.loc[result["previous_status"].isna(), "transition_type"] = "NEW_CLAIM"
    result.loc[
        (result["previous_status"] == "Open") & (result["status"] == "Closed"),
        "transition_type",
    ] = "OPEN_TO_CLOSED"
    result.loc[
        (result["previous_status"] == "Closed") & (result["status"] == "Open"),
        "transition_type",
    ] = "CLOSED_TO_OPEN"
    result[delta_name] = result["value_usd"] - result["previous_value_usd"]
    return result


def aggregate_demo(
    frame: pd.DataFrame,
    period_columns: list[str],
) -> pd.DataFrame:
    groups = period_columns + [
        "status",
        "wbr_tier1",
        "wbr_tier2",
        "wbr_tier3",
    ]
    return (
        frame.groupby(groups, dropna=False)
        .agg(
            claim_count=("claim_number", "size"),
            claim_value_usd=("value_usd", "sum"),
            new_claim_count=(
                "transition_type",
                lambda values: (values == "NEW_CLAIM").sum(),
            ),
            open_to_closed_count=(
                "transition_type",
                lambda values: (values == "OPEN_TO_CLOSED").sum(),
            ),
            reopened_count=(
                "transition_type",
                lambda values: (values == "CLOSED_TO_OPEN").sum(),
            ),
            status_change_count=("status_changed", "sum"),
        )
        .reset_index()
    )


def demo_data() -> dict[str, pd.DataFrame]:
    base = {
        "country": "US",
        "carrier_name": "Demo Carrier",
        "source": "Demo",
        "currency": "USD",
        "wbr_tier2": "In Process - Investigating",
        "wbr_tier3": None,
    }
    weekly = pd.DataFrame(
        [
            {
                **base,
                "claim_number": "CLM-1001",
                "snapshot_date": date(2026, 6, 27),
                "report_year": 2026,
                "report_week": 26,
                "week_start_date": date(2026, 6, 21),
                "week_end_date": date(2026, 6, 27),
                "status": "Open",
                "wbr_tier1": "ACTIVE CASES",
                "value_usd": 28000.0,
                "previous_status": None,
                "previous_wbr_tier1": None,
                "previous_value_usd": None,
            },
            {
                **base,
                "claim_number": "CLM-1002",
                "snapshot_date": date(2026, 6, 27),
                "report_year": 2026,
                "report_week": 26,
                "week_start_date": date(2026, 6, 21),
                "week_end_date": date(2026, 6, 27),
                "status": "Closed",
                "wbr_tier1": "CLOSED CASES",
                "wbr_tier2": "Not Found",
                "value_usd": 22000.0,
                "previous_status": None,
                "previous_wbr_tier1": None,
                "previous_value_usd": None,
            },
            {
                **base,
                "claim_number": "CLM-1001",
                "snapshot_date": date(2026, 7, 4),
                "report_year": 2026,
                "report_week": 27,
                "week_start_date": date(2026, 6, 28),
                "week_end_date": date(2026, 7, 4),
                "status": "Closed",
                "wbr_tier1": "CLOSED CASES",
                "wbr_tier2": "Found And Returned",
                "value_usd": 28000.0,
                "previous_status": "Open",
                "previous_wbr_tier1": "ACTIVE CASES",
                "previous_value_usd": 28000.0,
            },
            {
                **base,
                "claim_number": "CLM-1002",
                "snapshot_date": date(2026, 7, 4),
                "report_year": 2026,
                "report_week": 27,
                "week_start_date": date(2026, 6, 28),
                "week_end_date": date(2026, 7, 4),
                "status": "Open",
                "wbr_tier1": "RE-OPEN CLAIMS",
                "wbr_tier2": "Re-Opened",
                "value_usd": 22000.0,
                "previous_status": "Closed",
                "previous_wbr_tier1": "CLOSED CASES",
                "previous_value_usd": 22000.0,
            },
        ]
    )
    weekly = add_transition_columns(
        weekly,
        "week_over_week_value_delta_usd",
    )

    monthly = weekly.copy()
    monthly["metric_year"] = [2026, 2026, 2026, 2026]
    monthly["metric_month"] = [6, 6, 7, 7]
    monthly["month_start_date"] = [
        date(2026, 6, 1),
        date(2026, 6, 1),
        date(2026, 7, 1),
        date(2026, 7, 1),
    ]
    monthly["month_end_date"] = [
        date(2026, 6, 30),
        date(2026, 6, 30),
        date(2026, 7, 31),
        date(2026, 7, 31),
    ]
    monthly["month_over_month_value_delta_usd"] = (
        monthly["value_usd"] - monthly["previous_value_usd"]
    )

    current = (
        weekly.sort_values("snapshot_date")
        .groupby("claim_number", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )
    transitions = weekly[weekly["status_changed"]].copy()

    return {
        "current": current,
        "weekly": weekly,
        "weekly_transitions": transitions,
        "weekly_metrics": aggregate_demo(
            weekly,
            [
                "report_year",
                "report_week",
                "week_start_date",
                "week_end_date",
            ],
        ),
        "monthly": monthly,
        "monthly_metrics": aggregate_demo(
            monthly,
            [
                "metric_year",
                "metric_month",
                "month_start_date",
                "month_end_date",
            ],
        ),
    }


def numeric_sum(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame.columns:
        return 0.0
    return float(pd.to_numeric(frame[column], errors="coerce").fillna(0).sum())


def tier_metric(
    frame: pd.DataFrame,
    tier: str,
    column: str = "claim_count",
) -> float:
    if frame.empty or "wbr_tier1" not in frame.columns:
        return 0.0
    return numeric_sum(frame[frame["wbr_tier1"] == tier], column)


def money(value: float) -> str:
    return f"${value:,.0f}"


def filter_claims(frame: pd.DataFrame, key_prefix: str) -> pd.DataFrame:
    filtered = frame.copy()
    columns = st.columns(4)
    options = {
        "status": sorted(filtered.get("status", pd.Series(dtype=str)).dropna().unique()),
        "country": sorted(filtered.get("country", pd.Series(dtype=str)).dropna().unique()),
        "carrier_name": sorted(
            filtered.get("carrier_name", pd.Series(dtype=str)).dropna().unique()
        ),
    }
    selections: dict[str, list[str]] = {}
    labels = {"status": "Status", "country": "Country", "carrier_name": "Carrier"}
    for index, column in enumerate(("status", "country", "carrier_name")):
        with columns[index]:
            selections[column] = st.multiselect(
                labels[column],
                options[column],
                key=f"{key_prefix}_{column}",
            )
    with columns[3]:
        search = st.text_input(
            "Claim number contains",
            key=f"{key_prefix}_search",
        )

    for column, selected in selections.items():
        if selected:
            filtered = filtered[filtered[column].isin(selected)]
    if search:
        filtered = filtered[
            filtered["claim_number"]
            .astype(str)
            .str.contains(search, case=False, na=False)
        ]
    return filtered


def download_csv(frame: pd.DataFrame, filename: str, key: str) -> None:
    st.download_button(
        "Download CSV",
        frame.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        key=key,
    )


st.title("Insurance Claims Dashboard")
st.caption("Current claim state, historical trends, and status transitions")

default_project = configured_value("project_id", "ray-project-500821")
default_dataset = configured_value("marts_dataset", "")
default_location = configured_value("location", "US")

with st.sidebar:
    st.header("Data source")
    selected_source = st.radio(
        "Choose data source",
        ["BigQuery", "Demo data"],
        index=0 if default_dataset else 1,
    )
    use_demo = selected_source == "Demo data"
    project_id = st.text_input("BigQuery project", value=default_project)
    marts_dataset = st.text_input("Mart dataset", value=default_dataset)
    location = st.text_input("BigQuery location", value=default_location)
    auth_method = (
        "Streamlit service account"
        if service_account_info()
        else "Application Default Credentials"
    )
    st.caption(f"Authentication: {auth_method}")
    if st.button("Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

if use_demo:
    data = demo_data()
    st.info("Displaying demo history. Select BigQuery for live dbt marts.")
else:
    if not marts_dataset or marts_dataset.startswith("YOUR_"):
        st.error("Set the BigQuery mart dataset in the sidebar or secrets.")
        st.stop()
    try:
        with st.spinner("Loading dbt marts from BigQuery..."):
            data = {
                key: query_mart(project_id, marts_dataset, table, location)
                for key, table in TABLES.items()
            }
    except (GoogleAuthError, GoogleAPIError, ValueError) as exc:
        st.error(f"Unable to load BigQuery data ({type(exc).__name__}).")
        st.caption(
            "On Streamlit Cloud, configure [gcp_service_account] in App "
            "settings → Secrets. Also confirm the new marts have been built."
        )
        st.stop()

grain = st.sidebar.radio("Metric granularity", ["Weekly", "Monthly"])
if grain == "Weekly":
    metrics = data["weekly_metrics"].copy()
    states = data["weekly"].copy()
    year_column = "report_year"
    period_column = "report_week"
    start_column = "week_start_date"
    end_column = "week_end_date"
    period_prefix = "WK"
else:
    metrics = data["monthly_metrics"].copy()
    states = data["monthly"].copy()
    year_column = "metric_year"
    period_column = "metric_month"
    start_column = "month_start_date"
    end_column = "month_end_date"
    period_prefix = "M"

if metrics.empty:
    st.warning("No historical metrics exist yet. Build the new dbt marts first.")
    st.stop()

periods = (
    metrics[[year_column, period_column, start_column, end_column]]
    .drop_duplicates()
    .sort_values(start_column)
    .reset_index(drop=True)
)
periods["label"] = periods.apply(
    lambda row: (
        f"{int(row[year_column])}-{period_prefix}{int(row[period_column]):02d}"
    ),
    axis=1,
)

selected_label = st.sidebar.selectbox(
    f"{grain} period",
    periods["label"].tolist(),
    index=len(periods) - 1,
)
selected_index = periods.index[periods["label"] == selected_label][0]
selected_period = periods.loc[selected_index]
previous_period = periods.loc[selected_index - 1] if selected_index > 0 else None

selected_metrics = metrics[
    (metrics[year_column] == selected_period[year_column])
    & (metrics[period_column] == selected_period[period_column])
]
if previous_period is None:
    previous_metrics = pd.DataFrame(columns=metrics.columns)
else:
    previous_metrics = metrics[
        (metrics[year_column] == previous_period[year_column])
        & (metrics[period_column] == previous_period[period_column])
    ]

selected_states = states[
    (states[year_column] == selected_period[year_column])
    & (states[period_column] == selected_period[period_column])
]
period_transitions = selected_states[
    selected_states.get("status_changed", False).fillna(False)
].copy()

kpis = [
    ("Active claims", "ACTIVE CASES"),
    ("Closed claims", "CLOSED CASES"),
    ("Re-opened claims", "RE-OPEN CLAIMS"),
]
metric_columns = st.columns(4)
for column, (label, tier) in zip(metric_columns[:3], kpis):
    current_value = int(tier_metric(selected_metrics, tier))
    previous_value = int(tier_metric(previous_metrics, tier))
    delta = current_value - previous_value if previous_period is not None else None
    column.metric(label, current_value, delta)

current_exposure = numeric_sum(selected_metrics, "claim_value_usd")
previous_exposure = numeric_sum(previous_metrics, "claim_value_usd")
exposure_delta = (
    money(current_exposure - previous_exposure)
    if previous_period is not None
    else None
)
metric_columns[3].metric(
    "Claim value",
    money(current_exposure),
    exposure_delta,
)

overview_tab, metrics_tab, current_tab, history_tab, transitions_tab = st.tabs(
    [
        "Overview",
        f"{grain} metrics",
        "Current claims",
        "Claim history",
        "Transitions",
    ]
)

with overview_tab:
    trend = (
        metrics.groupby([start_column, "wbr_tier1"], dropna=False)["claim_count"]
        .sum()
        .unstack(fill_value=0)
        .sort_index()
    )
    exposure = (
        metrics.groupby([start_column, "wbr_tier1"], dropna=False)[
            "claim_value_usd"
        ]
        .sum()
        .unstack(fill_value=0)
        .sort_index()
    )
    left, right = st.columns(2)
    with left:
        st.subheader(f"{grain} claim count")
        st.line_chart(trend)
    with right:
        st.subheader(f"{grain} claim value")
        st.line_chart(exposure)

    st.subheader(f"Changes in {selected_label}")
    changes = st.columns(3)
    changes[0].metric(
        "Open → Closed",
        int(numeric_sum(selected_metrics, "open_to_closed_count")),
    )
    changes[1].metric(
        "Closed → Open",
        int(numeric_sum(selected_metrics, "reopened_count")),
    )
    changes[2].metric(
        "New claims",
        int(numeric_sum(selected_metrics, "new_claim_count")),
    )

with metrics_tab:
    category_metrics = (
        selected_metrics.groupby(
            ["wbr_tier1", "wbr_tier2", "wbr_tier3"],
            dropna=False,
        )
        .agg(
            claim_count=("claim_count", "sum"),
            claim_value_usd=("claim_value_usd", "sum"),
            status_changes=("status_change_count", "sum"),
        )
        .reset_index()
        .sort_values(["wbr_tier1", "wbr_tier2", "wbr_tier3"])
    )
    st.dataframe(category_metrics, hide_index=True, use_container_width=True)
    download_csv(
        category_metrics,
        f"{grain.lower()}_metrics_{selected_label}.csv",
        "download_metrics",
    )

with current_tab:
    filtered_current = filter_claims(data["current"], "current")
    st.caption(f"{len(filtered_current):,} matching current claims")
    st.dataframe(filtered_current, hide_index=True, use_container_width=True)
    download_csv(filtered_current, "current_claims.csv", "download_current")

with history_tab:
    filtered_history = filter_claims(selected_states, "history")
    st.caption(f"{len(filtered_history):,} claim states in {selected_label}")
    st.dataframe(filtered_history, hide_index=True, use_container_width=True)
    download_csv(
        filtered_history,
        f"claim_history_{selected_label}.csv",
        "download_history",
    )

with transitions_tab:
    if period_transitions.empty:
        st.info(
            "No prior-period status changes are available. With the first "
            "snapshot, every claim is NEW_CLAIM; deltas begin after the next "
            "snapshot period."
        )
    else:
        transition_counts = (
            period_transitions["transition_type"]
            .value_counts()
            .rename_axis("transition")
            .to_frame("claims")
        )
        st.bar_chart(transition_counts)
        st.dataframe(
            period_transitions,
            hide_index=True,
            use_container_width=True,
        )
        download_csv(
            period_transitions,
            f"claim_transitions_{selected_label}.csv",
            "download_transitions",
        )

st.caption(
    f"Loaded {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · "
    + ("Demo data" if use_demo else f"{project_id}.{marts_dataset}")
)
