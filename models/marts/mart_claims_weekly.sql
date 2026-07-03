{{
  config(
    materialized='table',
    tags=['marts', 'weekly', 'history'],
    partition_by={
      'field': 'week_end_date',
      'data_type': 'date',
      'granularity': 'month'
    },
    cluster_by=['claim_number', 'report_year', 'report_week', 'status']
  )
}}

/*
  Latest observed state for each claim in each report week.
  Grain: one row per claim_number + report_year + report_week.
*/

with observed as (

    select
        claims.*,
        date_sub(
            snapshot_date,
            interval (extract(dayofweek from snapshot_date) - 1) day
        ) as week_start_date
    from {{ ref('int_claims_classified') }} as claims

),

ranked as (

    select
        observed.*,
        date_add(week_start_date, interval 6 day) as week_end_date,
        row_number() over (
            partition by claim_number, report_year, report_week
            order by snapshot_date desc
        ) as snapshot_rank
    from observed

),

weekly as (

    select * except(snapshot_rank)
    from ranked
    where snapshot_rank = 1

),

with_previous_week as (

    select
        weekly.*,
        lag(status) over (
            partition by claim_number
            order by week_start_date
        ) as previous_status,
        lag(wbr_tier1) over (
            partition by claim_number
            order by week_start_date
        ) as previous_wbr_tier1,
        lag(value_usd) over (
            partition by claim_number
            order by week_start_date
        ) as previous_value_usd
    from weekly

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
    round(value_usd - previous_value_usd, 2) as week_over_week_value_delta_usd
from with_previous_week
