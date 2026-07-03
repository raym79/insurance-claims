{{
  config(
    materialized='table',
    tags=['marts', 'monthly', 'history'],
    partition_by={
      'field': 'month_end_date',
      'data_type': 'date',
      'granularity': 'month'
    },
    cluster_by=['claim_number', 'metric_year', 'metric_month', 'status']
  )
}}

/*
  Latest observed state for each claim in each calendar month.
  Grain: one row per claim_number + metric_year + metric_month.
*/

with observed as (

    select
        claims.*,
        extract(year from snapshot_date) as metric_year,
        extract(month from snapshot_date) as metric_month,
        date_trunc(snapshot_date, month) as month_start_date,
        last_day(snapshot_date, month) as month_end_date
    from {{ ref('int_claims_classified') }} as claims

),

ranked as (

    select
        observed.*,
        row_number() over (
            partition by claim_number, metric_year, metric_month
            order by snapshot_date desc
        ) as snapshot_rank
    from observed

),

monthly as (

    select * except(snapshot_rank)
    from ranked
    where snapshot_rank = 1

),

with_previous_month as (

    select
        monthly.*,
        lag(status) over (
            partition by claim_number
            order by month_start_date
        ) as previous_status,
        lag(wbr_tier1) over (
            partition by claim_number
            order by month_start_date
        ) as previous_wbr_tier1,
        lag(value_usd) over (
            partition by claim_number
            order by month_start_date
        ) as previous_value_usd
    from monthly

)

select
    *,
    previous_status is not null and status != previous_status as status_changed,
    case
        when previous_status is null
            then 'NEW_CLAIM'
        when previous_status = 'Open' and status = 'Closed'
            then 'OPEN_TO_CLOSED'
        when previous_status = 'Closed' and status = 'Open'
            then 'CLOSED_TO_OPEN'
        when previous_status != status
            then 'STATUS_CHANGED'
        else 'NO_CHANGE'
    end as transition_type,
    round(value_usd - previous_value_usd, 2) as month_over_month_value_delta_usd
from with_previous_month
