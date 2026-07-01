from __future__ import annotations

import os
import re
from datetime import date, datetime
from typing import Any

import pandas as pd
import streamlit as st
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery


st.set_page_config(
    page_title="Insurance Claims Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


TABLES = {
    "value": "mart_value_summary",
    "weekly": "mart_weekly_summary",
    "active": "mart_breakdown_active",
    "closed": "mart_breakdown_closed",
}

PROJECT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
DATASET_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
WEEK_COUNT_PATTERN = re.compile(r"^wk(\d+)_count$")


def secret_section() -> dict[str, Any]:
    try:
        section = st.secrets.get("bigquery", {})
        return dict(section)
    except (FileNotFoundError, KeyError):
        return {}


def configured_value(name: str, default: str = "") -> str:
    secrets = secret_section()
    env_name = f"BQ_{name.upper()}"
    return str(os.getenv(env_name, secrets.get(name, default)))


def validate_identifier(value: str, pattern: re.Pattern[str], label: str) -> str:
    value = value.strip()
    if not value or not pattern.fullmatch(value):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value


@st.cache_resource
def bigquery_client(project_id: str, location: str) -> bigquery.Client:
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


def demo_data() -> dict[str, pd.DataFrame]:
    value = pd.DataFrame(
        [
            {
                "wbr_tier1": "ACTIVE CASES",
                "wk16_value_usd": 210000,
                "wk16_count": 11,
                "wk17_value_usd": 245000,
                "wk17_count": 13,
                "wk18_value_usd": 198000,
                "wk18_count": 10,
                "wk19_value_usd": 275000,
                "wk19_count": 15,
                "wk20_value_usd": 260000,
                "wk20_count": 14,
                "wk21_value_usd": 310000,
                "wk21_count": 17,
                "ytd_value_usd": 1498000,
                "ytd_count": 80,
            },
            {
                "wbr_tier1": "CLOSED CASES",
                "wk16_value_usd": 80000,
                "wk16_count": 4,
                "wk17_value_usd": 105000,
                "wk17_count": 5,
                "wk18_value_usd": 120000,
                "wk18_count": 6,
                "wk19_value_usd": 95000,
                "wk19_count": 5,
                "wk20_value_usd": 140000,
                "wk20_count": 7,
                "wk21_value_usd": 125000,
                "wk21_count": 6,
                "ytd_value_usd": 665000,
                "ytd_count": 33,
            },
            {
                "wbr_tier1": "RE-OPEN CLAIMS",
                "wk16_value_usd": 18000,
                "wk16_count": 1,
                "wk17_value_usd": 0,
                "wk17_count": 0,
                "wk18_value_usd": 22000,
                "wk18_count": 1,
                "wk19_value_usd": 0,
                "wk19_count": 0,
                "wk20_value_usd": 16000,
                "wk20_count": 1,
                "wk21_value_usd": 24000,
                "wk21_count": 1,
                "ytd_value_usd": 80000,
                "ytd_count": 4,
            },
        ]
    )

    weekly = pd.DataFrame(
        [
            {
                "category": "ACTIVE CASES",
                "sort_order": 1,
                "indent_level": 0,
                "wk20_count": 14,
                "wk20_value_usd": 260000,
                "wk21_count": 17,
                "wk21_value_usd": 310000,
                "ytd_count": 80,
                "ytd_value_usd": 1498000,
            },
            {
                "category": "  In Process - Investigating",
                "sort_order": 2,
                "indent_level": 1,
                "wk20_count": 8,
                "wk20_value_usd": 145000,
                "wk21_count": 9,
                "wk21_value_usd": 165000,
                "ytd_count": 43,
                "ytd_value_usd": 810000,
            },
            {
                "category": "CLOSED CASES",
                "sort_order": 7,
                "indent_level": 0,
                "wk20_count": 7,
                "wk20_value_usd": 140000,
                "wk21_count": 6,
                "wk21_value_usd": 125000,
                "ytd_count": 33,
                "ytd_value_usd": 665000,
            },
            {
                "category": "RE-OPEN CLAIMS",
                "sort_order": 16,
                "indent_level": 0,
                "wk20_count": 1,
                "wk20_value_usd": 16000,
                "wk21_count": 1,
                "wk21_value_usd": 24000,
                "ytd_count": 4,
                "ytd_value_usd": 80000,
            },
        ]
    )

    active = pd.DataFrame(
        [
            {
                "claim_number": "CLM-1001",
                "country": "US",
                "carrier_name": "Northstar",
                "trailer_license_plate": "TR-4821",
                "trailer_number": "T-100",
                "status": "Open",
                "reason": "Found",
                "insurance_claims_results": "Waiting For Reply",
                "source": "Sedgwick",
                "submitted_date": date(2026, 5, 18),
                "date_of_loss": date(2026, 5, 15),
                "value_of_trailer": 28000,
                "value_usd": 28000,
                "currency": "USD",
                "wbr_tier1": "ACTIVE CASES",
                "wbr_tier2": "Waiting For Reply From Insurance",
                "wbr_tier3": "Found",
                "submitted_year": 2026,
                "submitted_week": 21,
                "breakdown_section": "WAITING_FOR_REPLY_FOUND",
            },
            {
                "claim_number": "CLM-1002",
                "country": "CA",
                "carrier_name": "Maple Freight",
                "trailer_license_plate": "ON-9027",
                "trailer_number": "T-204",
                "status": "Open",
                "reason": "No Longer In Network",
                "insurance_claims_results": "Waiting For Reply",
                "source": "Xceedance",
                "submitted_date": date(2026, 5, 20),
                "date_of_loss": date(2026, 5, 17),
                "value_of_trailer": 34000,
                "value_usd": 23800,
                "currency": "CAD",
                "wbr_tier1": "ACTIVE CASES",
                "wbr_tier2": "Waiting For Reply From Insurance",
                "wbr_tier3": "Not In Network",
                "submitted_year": 2026,
                "submitted_week": 21,
                "breakdown_section": "WAITING_FOR_REPLY_NOT_IN_NETWORK",
            },
            {
                "claim_number": "CLM-1003",
                "country": "US",
                "carrier_name": "Blue Road",
                "trailer_license_plate": "TX-3190",
                "trailer_number": "T-331",
                "status": "Open",
                "reason": "",
                "insurance_claims_results": "Investigating",
                "source": "Sedgwick",
                "submitted_date": date(2026, 5, 19),
                "date_of_loss": date(2026, 5, 19),
                "value_of_trailer": 31000,
                "value_usd": 31000,
                "currency": "USD",
                "wbr_tier1": "RE-OPEN CLAIMS",
                "wbr_tier2": "Re-Opened",
                "wbr_tier3": None,
                "submitted_year": 2026,
                "submitted_week": 21,
                "breakdown_section": "RE_OPENED",
            },
        ]
    )

    closed = pd.DataFrame(
        [
            {
                "claim_number": "CLM-0901",
                "country": "US",
                "carrier_name": "Northstar",
                "trailer_license_plate": "IL-1198",
                "trailer_number": "T-077",
                "status": "Closed",
                "reason": "Found",
                "insurance_claims_results": "Resolved",
                "results": "Found & Recovered",
                "source": "Sedgwick",
                "case_date_closed": date(2026, 5, 21),
                "value_of_trailer": 29500,
                "value_usd": 29500,
                "currency": "USD",
                "wbr_tier1": "CLOSED CASES",
                "wbr_tier2": "Found And Returned",
                "wbr_tier3": "Found - Recovered",
                "closed_year": 2026,
                "closed_week": 21,
            },
            {
                "claim_number": "CLM-0902",
                "country": "CA",
                "carrier_name": "Maple Freight",
                "trailer_license_plate": "QC-3301",
                "trailer_number": "T-081",
                "status": "Closed",
                "reason": "Not Found",
                "insurance_claims_results": "Amazon Not Liable",
                "results": "",
                "source": "Xceedance",
                "case_date_closed": date(2026, 5, 20),
                "value_of_trailer": 26000,
                "value_usd": 18200,
                "currency": "CAD",
                "wbr_tier1": "CLOSED CASES",
                "wbr_tier2": "Not Found",
                "wbr_tier3": "Not Liable",
                "closed_year": 2026,
                "closed_week": 21,
            },
        ]
    )

    return {
        "value": value,
        "weekly": weekly,
        "active": active,
        "closed": closed,
    }


def money(value: Any) -> str:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").fillna(0).iloc[0]
    return f"${number:,.0f}"


def integer(value: Any) -> int:
    return int(pd.to_numeric(pd.Series([value]), errors="coerce").fillna(0).iloc[0])


def status_value(frame: pd.DataFrame, status: str, column: str) -> float:
    if (
        frame.empty
        or "wbr_tier1" not in frame.columns
        or column not in frame.columns
    ):
        return 0
    rows = frame.loc[frame["wbr_tier1"] == status, column]
    return float(pd.to_numeric(rows, errors="coerce").fillna(0).sum())


def weekly_trend(value_summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for column in value_summary.columns:
        match = WEEK_COUNT_PATTERN.match(column)
        if not match:
            continue
        week = int(match.group(1))
        value_column = f"wk{week}_value_usd"
        rows.append(
            {
                "week": f"WK{week}",
                "claim_count": integer(value_summary[column].sum()),
                "claim_value_usd": float(
                    pd.to_numeric(
                        value_summary.get(value_column, pd.Series(dtype=float)),
                        errors="coerce",
                    )
                    .fillna(0)
                    .sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def filter_frame(
    frame: pd.DataFrame,
    prefix: str,
    include_section: bool = False,
) -> pd.DataFrame:
    filtered = frame.copy()
    controls = st.columns(3)

    countries = sorted(filtered.get("country", pd.Series(dtype=str)).dropna().unique())
    carriers = sorted(
        filtered.get("carrier_name", pd.Series(dtype=str)).dropna().unique()
    )

    with controls[0]:
        selected_countries = st.multiselect(
            "Country",
            countries,
            key=f"{prefix}_country",
        )
    with controls[1]:
        selected_carriers = st.multiselect(
            "Carrier",
            carriers,
            key=f"{prefix}_carrier",
        )
    with controls[2]:
        claim_search = st.text_input(
            "Claim number contains",
            key=f"{prefix}_claim_search",
        )

    if selected_countries:
        filtered = filtered[filtered["country"].isin(selected_countries)]
    if selected_carriers:
        filtered = filtered[filtered["carrier_name"].isin(selected_carriers)]
    if claim_search:
        filtered = filtered[
            filtered["claim_number"]
            .astype(str)
            .str.contains(claim_search, case=False, na=False)
        ]

    if include_section and "breakdown_section" in filtered.columns:
        sections = sorted(filtered["breakdown_section"].dropna().unique())
        selected_sections = st.multiselect(
            "Breakdown section",
            sections,
            key=f"{prefix}_section",
        )
        if selected_sections:
            filtered = filtered[
                filtered["breakdown_section"].isin(selected_sections)
            ]

    return filtered


def download_csv(frame: pd.DataFrame, filename: str, key: str) -> None:
    st.download_button(
        "Download CSV",
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        key=key,
    )


st.title("Insurance Claims Dashboard")
st.caption("Executive summary and claim-level detail from dbt marts in BigQuery")

default_project = configured_value("project_id", "ray-project-500821")
default_dataset = configured_value("marts_dataset", "")
default_location = configured_value("location", "US")

with st.sidebar:
    st.header("Data source")
    source_options = ["BigQuery", "Demo data"]
    selected_source = st.radio(
        "Choose data source",
        source_options,
        index=0 if default_dataset else 1,
    )
    use_demo = selected_source == "Demo data"
    project_id = st.text_input("BigQuery project", value=default_project)
    marts_dataset = st.text_input("Mart dataset", value=default_dataset)
    location = st.text_input("BigQuery location", value=default_location)
    if st.button("Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

if use_demo:
    data = demo_data()
    st.info("Displaying bundled demo data. Select BigQuery in the sidebar for live data.")
else:
    if not marts_dataset or marts_dataset.startswith("YOUR_"):
        st.error("Set the BigQuery mart dataset in the sidebar or secrets.toml.")
        st.stop()

    try:
        with st.spinner("Loading dbt marts from BigQuery..."):
            data = {
                key: query_mart(project_id, marts_dataset, table, location)
                for key, table in TABLES.items()
            }
    except (DefaultCredentialsError, GoogleAPIError, ValueError) as exc:
        st.error(f"Unable to load BigQuery data: {exc}")
        st.caption(
            "Confirm Application Default Credentials, dataset name, location, "
            "and BigQuery permissions."
        )
        st.stop()

value_summary = data["value"]
weekly_summary = data["weekly"]
active_claims = data["active"]
closed_claims = data["closed"]

count_columns = [
    column for column in value_summary.columns if WEEK_COUNT_PATTERN.match(column)
]
latest_count_column = count_columns[-1] if count_columns else "ytd_count"
latest_week = (
    latest_count_column.removeprefix("wk").removesuffix("_count")
    if latest_count_column.startswith("wk")
    else "YTD"
)

metric_columns = st.columns(4)
metric_columns[0].metric(
    f"Active claims · WK{latest_week}",
    integer(status_value(value_summary, "ACTIVE CASES", latest_count_column)),
)
metric_columns[1].metric(
    f"Closed claims · WK{latest_week}",
    integer(status_value(value_summary, "CLOSED CASES", latest_count_column)),
)
metric_columns[2].metric(
    f"Re-opened · WK{latest_week}",
    integer(status_value(value_summary, "RE-OPEN CLAIMS", latest_count_column)),
)
metric_columns[3].metric(
    "YTD claim value",
    money(
        pd.to_numeric(
            value_summary.get("ytd_value_usd", pd.Series(dtype=float)),
            errors="coerce",
        )
        .fillna(0)
        .sum()
    ),
)

overview_tab, categories_tab, active_tab, closed_tab = st.tabs(
    ["Overview", "Category summary", "Active claims", "Closed claims"]
)

with overview_tab:
    trend = weekly_trend(value_summary)
    left, right = st.columns(2)
    with left:
        st.subheader("Claims by report week")
        if trend.empty:
            st.warning("No weekly count columns were found.")
        else:
            st.line_chart(trend.set_index("week")["claim_count"])
    with right:
        st.subheader("Claim value by report week")
        if trend.empty:
            st.warning("No weekly value columns were found.")
        else:
            st.bar_chart(trend.set_index("week")["claim_value_usd"])

    st.subheader("YTD value by status")
    if {"wbr_tier1", "ytd_value_usd"}.issubset(value_summary.columns):
        ytd = value_summary[["wbr_tier1", "ytd_value_usd"]].copy()
        ytd["ytd_value_usd"] = pd.to_numeric(
            ytd["ytd_value_usd"], errors="coerce"
        ).fillna(0)
        st.bar_chart(ytd.set_index("wbr_tier1")["ytd_value_usd"])

with categories_tab:
    st.subheader("Weekly category hierarchy")
    if "sort_order" in weekly_summary.columns:
        weekly_summary = weekly_summary.sort_values("sort_order")
    st.dataframe(
        weekly_summary,
        hide_index=True,
        use_container_width=True,
    )
    download_csv(
        weekly_summary,
        "weekly_category_summary.csv",
        "download_weekly",
    )

with active_tab:
    st.subheader("Active and re-opened claims")
    filtered_active = filter_frame(
        active_claims,
        "active",
        include_section=True,
    )
    st.caption(f"{len(filtered_active):,} matching claims")

    if "breakdown_section" in filtered_active.columns and not filtered_active.empty:
        section_counts = (
            filtered_active["breakdown_section"]
            .value_counts()
            .rename_axis("section")
            .to_frame("claims")
        )
        st.bar_chart(section_counts)

    st.dataframe(
        filtered_active,
        hide_index=True,
        use_container_width=True,
    )
    download_csv(filtered_active, "active_claims.csv", "download_active")

with closed_tab:
    st.subheader("Closed claims")
    filtered_closed = filter_frame(closed_claims, "closed")
    st.caption(f"{len(filtered_closed):,} matching claims")

    if "wbr_tier3" in filtered_closed.columns and not filtered_closed.empty:
        outcome_counts = (
            filtered_closed["wbr_tier3"]
            .fillna("Unclassified")
            .value_counts()
            .rename_axis("outcome")
            .to_frame("claims")
        )
        st.bar_chart(outcome_counts)

    if "case_date_closed" in filtered_closed.columns:
        filtered_closed = filtered_closed.sort_values(
            "case_date_closed",
            ascending=False,
        )

    st.dataframe(
        filtered_closed,
        hide_index=True,
        use_container_width=True,
    )
    download_csv(filtered_closed, "closed_claims.csv", "download_closed")

st.caption(
    f"Loaded {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · "
    + ("Demo data" if use_demo else f"{project_id}.{marts_dataset}")
)
