{{
  config(
    materialized='table',
    tags=['marts', 'monthly', 'history', 'metrics'],
    partition_by={
      'field': 'month_end_date',
      'data_type': 'date',
      'granularity': 'month'
    },
    cluster_by=['metric_year', 'metric_month', 'wbr_tier1', 'status']
  )
}}

/*
  Dashboard-ready monthly metrics.
  Grain: calendar month + status + WBR classification.
*/

select
    metric_year,
    metric_month,
    month_start_date,
    month_end_date,
    status,
    wbr_tier1,
    wbr_tier2,
    wbr_tier3,
    count(*) as claim_count,
    round(sum(coalesce(value_usd, cast(0 as numeric))), 2) as claim_value_usd,
    countif(transition_type = 'NEW_CLAIM') as new_claim_count,
    countif(transition_type = 'OPEN_TO_CLOSED') as open_to_closed_count,
    countif(transition_type = 'CLOSED_TO_OPEN') as reopened_count,
    countif(status_changed) as status_change_count
from {{ ref('mart_claims_monthly') }}
group by
    metric_year,
    metric_month,
    month_start_date,
    month_end_date,
    status,
    wbr_tier1,
    wbr_tier2,
    wbr_tier3
