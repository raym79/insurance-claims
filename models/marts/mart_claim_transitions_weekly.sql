{{
  config(
    materialized='table',
    tags=['marts', 'weekly', 'history', 'transitions'],
    partition_by={
      'field': 'week_end_date',
      'data_type': 'date',
      'granularity': 'month'
    },
    cluster_by=['claim_number', 'transition_type']
  )
}}

/*
  Claim-level week-over-week status transitions.
  NEW_CLAIM and NO_CHANGE rows remain available in mart_claims_weekly but are
  excluded here so this table contains only actual status changes.
*/

select
    claim_snapshot_key,
    claim_number,
    snapshot_date,
    week_start_date,
    week_end_date,
    report_year,
    report_week,
    previous_status,
    status as current_status,
    transition_type,
    previous_wbr_tier1,
    wbr_tier1,
    wbr_tier2,
    wbr_tier3,
    country,
    carrier_name,
    source,
    submitted_date,
    case_date_closed,
    previous_value_usd,
    value_usd,
    week_over_week_value_delta_usd
from {{ ref('mart_claims_weekly') }}
where status_changed
