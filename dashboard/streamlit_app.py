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

WBR_WATERFALL_ORDER = {
    "ACTIVE CASES": 100,
    "In Process - Investigating": 200,
    "Waiting For Reply From Insurance": 300,
    "Found": 400,
    "Not Found / Potential Claim": 500,
    "Not In Network": 600,
    "CLOSED CASES": 700,
    "Found And Returned": 800,
    "Carrier Picked Up": 900,
    "Found -Sent To Towing Yard": 1000,
    "Found - Recovered": 1100,
    "Not Liable Due To No Response": 1200,
    "Not Found": 1300,
    "Not Liable": 1400,
    "Liable": 1500,
    "RE-OPEN CLAIMS": 1600,
}

WBR_WATERFALL_INDENT = {
    "ACTIVE CASES": 0,
    "In Process - Investigating": 1,
    "Waiting For Reply From Insurance": 1,
    "Found": 2,
    "Not Found / Potential Claim": 2,
    "Not In Network": 2,
    "CLOSED CASES": 0,
    "Found And Returned": 1,
    "Carrier Picked Up": 2,
    "Found -Sent To Towing Yard": 2,
    "Found - Recovered": 2,
    "Not Liable Due To No Response": 2,
    "Not Found": 1,
    "Not Liable": 2,
    "Liable": 2,
    "RE-OPEN CLAIMS": 0,
}


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
        "source",
        "carrier_name",
        "country",
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
    columns = st.columns(5)
    options = {
        "status": sorted(filtered.get("status", pd.Series(dtype=str)).dropna().unique()),
        "source": sorted(filtered.get("source", pd.Series(dtype=str)).dropna().unique()),
        "country": sorted(filtered.get("country", pd.Series(dtype=str)).dropna().unique()),
        "carrier_name": sorted(
            filtered.get("carrier_name", pd.Series(dtype=str)).dropna().unique()
        ),
    }
    selections: dict[str, list[str]] = {}
    labels = {
        "status": "Status",
        "source": "Provider",
        "country": "Country",
        "carrier_name": "Carrier",
    }
    for index, column in enumerate(
        ("country", "status", "source", "carrier_name")
    ):
        with columns[index]:
            selections[column] = st.multiselect(
                labels[column],
                options[column],
                key=f"{key_prefix}_{column}",
            )
    with columns[4]:
        search = st.text_input(
            "Claim Number",
            key=f"{key_prefix}_search",
            placeholder="Contains...",
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


def filter_transitions(frame: pd.DataFrame) -> pd.DataFrame:
    filtered = frame.copy()
    columns = st.columns(6)
    filter_definitions = (
        ("country", "Country"),
        ("current_status", "Status"),
        ("source", "Provider"),
        ("carrier_name", "Carrier"),
        ("transition_type", "Transition Type"),
    )
    selections: dict[str, list[str]] = {}
    for index, (column, label) in enumerate(filter_definitions):
        with columns[index]:
            selections[column] = st.multiselect(
                label,
                sorted(
                    filtered.get(column, pd.Series(dtype=str))
                    .dropna()
                    .astype(str)
                    .unique()
                ),
                key=f"transitions_{column}",
            )
    with columns[5]:
        search = st.text_input(
            "Claim Number",
            key="transitions_search",
            placeholder="Contains...",
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


def display_column_name(column: str) -> str:
    abbreviations = {
        "id": "ID",
        "usd": "USD",
        "vin": "VIN",
        "wbr": "WBR",
    }
    words: list[str] = []
    for word in column.split("_"):
        tier_match = re.fullmatch(r"tier(\d+)", word, flags=re.IGNORECASE)
        if tier_match:
            words.extend(["Tier", tier_match.group(1)])
        else:
            words.append(abbreviations.get(word.lower(), word.title()))
    return " ".join(words)


def title_case_columns(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.rename(
        columns={
            column: display_column_name(str(column))
            for column in frame.columns
        }
    )


def period_dimension(
    metrics: pd.DataFrame,
    year_column: str,
    period_column: str,
    start_column: str,
    end_column: str,
    label_prefix: str,
) -> pd.DataFrame:
    periods = metrics[
        [year_column, period_column, start_column, end_column]
    ].drop_duplicates()
    periods[start_column] = pd.to_datetime(periods[start_column])
    periods[end_column] = pd.to_datetime(periods[end_column])
    periods = periods.sort_values(start_column).reset_index(drop=True)
    periods["period_label"] = periods.apply(
        lambda row: (
            f"{int(row[year_column])}-{label_prefix}"
            f"{int(row[period_column]):02d}"
        ),
        axis=1,
    )
    return periods


def hierarchy_values(
    metrics: pd.DataFrame,
    start_column: str,
    measure: str,
) -> pd.DataFrame:
    source = metrics.copy()
    source[start_column] = pd.to_datetime(source[start_column])
    for column in ("wbr_tier1", "wbr_tier2", "wbr_tier3"):
        source[column] = source[column].fillna("").astype(str).str.strip()

    frames: list[pd.DataFrame] = []
    level_columns = {
        1: ["wbr_tier1"],
        2: ["wbr_tier1", "wbr_tier2"],
        3: ["wbr_tier1", "wbr_tier2", "wbr_tier3"],
    }
    for level, tier_columns in level_columns.items():
        level_source = source[source[tier_columns[-1]] != ""]
        grouped = (
            level_source.groupby(
                [start_column, *tier_columns],
                dropna=False,
            )[measure]
            .sum()
            .reset_index(name="metric_value")
        )
        for column in ("wbr_tier1", "wbr_tier2", "wbr_tier3"):
            if column not in grouped.columns:
                grouped[column] = ""
        grouped["tier_level"] = level
        frames.append(grouped)

    hierarchy = pd.concat(frames, ignore_index=True)
    hierarchy["row_key"] = hierarchy[
        ["wbr_tier1", "wbr_tier2", "wbr_tier3"]
    ].agg("|||".join, axis=1)
    hierarchy["node_name"] = hierarchy.apply(
        lambda row: row[f"wbr_tier{int(row['tier_level'])}"],
        axis=1,
    )
    hierarchy["category"] = hierarchy.apply(
        lambda row: (
            (
                "\u00a0"
                * WBR_WATERFALL_INDENT.get(
                    row["node_name"],
                    int(row["tier_level"]) - 1,
                )
                * 4
            )
            + row["node_name"]
        ),
        axis=1,
    )
    fallback_order = {
        "ACTIVE CASES": 650,
        "CLOSED CASES": 1550,
        "RE-OPEN CLAIMS": 1700,
    }
    hierarchy["sort_key"] = hierarchy.apply(
        lambda row: "|".join(
            [
                f"{WBR_WATERFALL_ORDER.get(
                    row['node_name'],
                    fallback_order.get(row['wbr_tier1'], 9000),
                ):04d}",
                (
                    row["node_name"]
                    if int(row["tier_level"]) > 1
                    else ""
                ),
                f"{int(row['tier_level'])}",
                row["wbr_tier2"],
                row["wbr_tier3"],
            ]
        ),
        axis=1,
    )
    return hierarchy


def comparison_text(current: float, previous: float, measure: str) -> str:
    delta = current - previous
    if previous == 0:
        percent = "new" if current != 0 else "0.0%"
    else:
        percent = f"{delta / previous:+.1%}"
    if measure == "claim_value_usd":
        absolute = f"{'-' if delta < 0 else '+'}${abs(delta):,.0f}"
    else:
        absolute = f"{delta:+,.0f}"
    return f"{absolute} ({percent})"


def build_review_pivot(
    metrics: pd.DataFrame,
    periods: pd.DataFrame,
    selected_periods: pd.DataFrame,
    start_column: str,
    measure: str,
) -> tuple[pd.DataFrame, str | None]:
    hierarchy = hierarchy_values(metrics, start_column, measure)
    labels = periods.set_index(start_column)["period_label"].to_dict()
    selected_starts = selected_periods[start_column].tolist()
    last_start = selected_starts[-1]
    last_index = periods.index[periods[start_column] == last_start][0]
    previous_start = (
        periods.loc[last_index - 1, start_column] if last_index > 0 else None
    )

    comparison_starts = [last_start]
    if previous_start is not None:
        comparison_starts.append(previous_start)
    relevant = hierarchy[
        hierarchy[start_column].isin([*selected_starts, *comparison_starts])
    ]
    row_metadata = (
        relevant[["row_key", "category", "sort_key"]]
        .drop_duplicates()
        .sort_values("sort_key")
    )

    selected_values = hierarchy[hierarchy[start_column].isin(selected_starts)]
    pivot = selected_values.pivot_table(
        index="row_key",
        columns=start_column,
        values="metric_value",
        aggfunc="sum",
        fill_value=0,
    )
    pivot = pivot.reindex(columns=selected_starts, fill_value=0)
    pivot.columns = [labels[column] for column in pivot.columns]
    result = row_metadata.set_index("row_key").join(pivot, how="left").fillna(0)

    if previous_start is not None:
        comparison = hierarchy[
            hierarchy[start_column].isin([previous_start, last_start])
        ].pivot_table(
            index="row_key",
            columns=start_column,
            values="metric_value",
            aggfunc="sum",
            fill_value=0,
        )
        current_values = comparison.get(
            last_start,
            pd.Series(0, index=comparison.index),
        )
        previous_values = comparison.get(
            previous_start,
            pd.Series(0, index=comparison.index),
        )
        result["comparison"] = [
            comparison_text(
                float(current_values.get(row_key, 0)),
                float(previous_values.get(row_key, 0)),
                measure,
            )
            for row_key in result.index
        ]
        comparison_period = labels[previous_start]
    else:
        result["comparison"] = "N/A"
        comparison_period = None

    result = result.sort_values("sort_key").drop(columns="sort_key")
    result = result.rename(columns={"category": "WBR waterfall"})
    return result.reset_index(drop=True), comparison_period


def render_period_review(
    metrics: pd.DataFrame,
    grain: str,
    year_column: str,
    period_column: str,
    start_column: str,
    end_column: str,
    label_prefix: str,
    comparison_label: str,
    default_period_count: int,
) -> None:
    st.subheader(f"{grain} Review")
    if metrics.empty:
        st.info(f"No {grain.lower()} metrics are available yet.")
        return

    filtered_metrics = metrics.copy()
    filter_columns = st.columns(3)
    with filter_columns[0]:
        providers = st.multiselect(
            "Provider",
            sorted(
                filtered_metrics["source"].dropna().astype(str).unique()
            ),
            key=f"{grain.lower()}_providers",
        )
    with filter_columns[1]:
        carriers = st.multiselect(
            "Carrier",
            sorted(
                filtered_metrics["carrier_name"].dropna().astype(str).unique()
            ),
            key=f"{grain.lower()}_carriers",
        )
    with filter_columns[2]:
        countries = st.multiselect(
            "Country",
            sorted(
                filtered_metrics["country"].dropna().astype(str).unique()
            ),
            key=f"{grain.lower()}_countries",
        )
    if providers:
        filtered_metrics = filtered_metrics[
            filtered_metrics["source"].isin(providers)
        ]
    if carriers:
        filtered_metrics = filtered_metrics[
            filtered_metrics["carrier_name"].isin(carriers)
        ]
    if countries:
        filtered_metrics = filtered_metrics[
            filtered_metrics["country"].isin(countries)
        ]
    if filtered_metrics.empty:
        st.warning(
            "No metrics match the selected provider, carrier, and country."
        )
        return

    periods = period_dimension(
        filtered_metrics,
        year_column,
        period_column,
        start_column,
        end_column,
        label_prefix,
    )
    default_start_index = max(0, len(periods) - default_period_count)
    controls = st.columns([2, 1])
    with controls[0]:
        selected_range = st.date_input(
            f"Select {grain.lower()} date range",
            value=(
                periods.loc[default_start_index, start_column].date(),
                periods.iloc[-1][start_column].date(),
            ),
            min_value=periods.iloc[0][start_column].date(),
            max_value=periods.iloc[-1][start_column].date(),
            key=f"{grain.lower()}_range",
        )
    with controls[1]:
        measure_label = st.selectbox(
            "Table metric",
            ["Claim count", "Claim value (USD)"],
            key=f"{grain.lower()}_measure",
        )
    if not isinstance(selected_range, (tuple, list)) or len(selected_range) != 2:
        st.info("Select both a start date and an end date.")
        return

    range_start, range_end = pd.to_datetime(selected_range)
    selected_periods = periods[
        (periods[start_column] >= range_start)
        & (periods[start_column] <= range_end)
    ]
    if selected_periods.empty:
        st.warning("No reporting periods fall within this date range.")
        return

    measure = (
        "claim_count"
        if measure_label == "Claim count"
        else "claim_value_usd"
    )
    pivot, previous_label = build_review_pivot(
        filtered_metrics,
        periods,
        selected_periods,
        start_column,
        measure,
    )
    pivot = pivot.rename(columns={"comparison": comparison_label})
    last_label = selected_periods.iloc[-1]["period_label"]
    if previous_label:
        st.caption(
            f"{comparison_label} compares {last_label} with {previous_label}. "
            "Parent rows are totals; indented rows show Tier 2 and Tier 3."
        )
    else:
        st.caption(
            f"{last_label} is the first available period, so no "
            f"{comparison_label} comparison exists yet."
        )

    period_labels = selected_periods["period_label"].tolist()
    column_config: dict[str, Any] = {
        "WBR waterfall": st.column_config.TextColumn(width="large"),
    }
    number_format = "$%.0f" if measure == "claim_value_usd" else "%.0f"
    for label in period_labels:
        column_config[label] = st.column_config.NumberColumn(
            format=number_format,
        )
    st.dataframe(
        pivot,
        hide_index=True,
        use_container_width=True,
        column_config=column_config,
    )
    download_csv(
        pivot,
        f"{grain.lower()}_review_{last_label}.csv",
        f"download_{grain.lower()}_review",
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

weekly_metrics = data["weekly_metrics"].copy()
if weekly_metrics.empty:
    st.warning("No historical metrics exist yet. Build the new dbt marts first.")
    st.stop()

weekly_periods = period_dimension(
    weekly_metrics,
    "report_year",
    "report_week",
    "week_start_date",
    "week_end_date",
    "W",
)
latest_week = weekly_periods.iloc[-1]
latest_week_metrics = weekly_metrics[
    (weekly_metrics["report_year"] == latest_week["report_year"])
    & (weekly_metrics["report_week"] == latest_week["report_week"])
]
if len(weekly_periods) > 1:
    previous_week = weekly_periods.iloc[-2]
    previous_week_metrics = weekly_metrics[
        (weekly_metrics["report_year"] == previous_week["report_year"])
        & (weekly_metrics["report_week"] == previous_week["report_week"])
    ]
else:
    previous_week = None
    previous_week_metrics = pd.DataFrame(columns=weekly_metrics.columns)

kpis = [
    ("Active claims", "ACTIVE CASES"),
    ("Closed claims", "CLOSED CASES"),
    ("Re-opened claims", "RE-OPEN CLAIMS"),
]
metric_columns = st.columns(4)
for column, (label, tier) in zip(metric_columns[:3], kpis):
    current_value = int(tier_metric(latest_week_metrics, tier))
    previous_value = int(tier_metric(previous_week_metrics, tier))
    delta = current_value - previous_value if previous_week is not None else None
    column.metric(label, current_value, delta)

current_exposure = numeric_sum(latest_week_metrics, "claim_value_usd")
previous_exposure = numeric_sum(previous_week_metrics, "claim_value_usd")
exposure_delta = (
    money(current_exposure - previous_exposure)
    if previous_week is not None
    else None
)
metric_columns[3].metric(
    "Claim value",
    money(current_exposure),
    exposure_delta,
)

weekly_tab, monthly_tab, current_tab, transitions_tab = st.tabs(
    [
        "Weekly Review",
        "Monthly Review",
        "Current Claims",
        "Transitions",
    ]
)

with weekly_tab:
    render_period_review(
        data["weekly_metrics"],
        grain="Weekly",
        year_column="report_year",
        period_column="report_week",
        start_column="week_start_date",
        end_column="week_end_date",
        label_prefix="W",
        comparison_label="WoW",
        default_period_count=8,
    )

with monthly_tab:
    render_period_review(
        data["monthly_metrics"],
        grain="Monthly",
        year_column="metric_year",
        period_column="metric_month",
        start_column="month_start_date",
        end_column="month_end_date",
        label_prefix="M",
        comparison_label="MoM",
        default_period_count=12,
    )

with current_tab:
    filtered_current = filter_claims(data["current"], "current")
    st.caption(f"{len(filtered_current):,} matching current claims")
    current_display = title_case_columns(filtered_current)
    st.dataframe(current_display, hide_index=True, use_container_width=True)
    download_csv(current_display, "current_claims.csv", "download_current")

with transitions_tab:
    transitions = data["weekly_transitions"].copy()
    if transitions.empty:
        st.info(
            "No prior-period status changes are available. With the first "
            "snapshot, every claim is NEW_CLAIM; deltas begin after the next "
            "snapshot period."
        )
    else:
        filtered_transitions = filter_transitions(transitions)
        st.caption(f"{len(filtered_transitions):,} matching transitions")
        transitions_display = title_case_columns(
            filtered_transitions.sort_values(
                "week_end_date",
                ascending=False,
            )
        )
        st.dataframe(
            transitions_display,
            hide_index=True,
            use_container_width=True,
        )
        download_csv(
            transitions_display,
            "claim_transitions.csv",
            "download_transitions",
        )

st.caption(
    f"Loaded {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · "
    + ("Demo data" if use_demo else f"{project_id}.{marts_dataset}")
)
