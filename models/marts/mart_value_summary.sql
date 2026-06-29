{{
  config(
    materialized='table',
    tags=['marts', 'weekly'],
    dist='ALL'
  )
}}

/*
  Value Summary: Total USD exposure by tier1, trailing 6 weeks + YTD.
  Simplified aggregation for executive dashboards.
*/

{% set report_year = var('report_year') %}
{% set report_week = var('report_week') %}
{% set trailing_weeks = generate_trailing_weeks(report_year, report_week, 6) %}

with claims as (

    select
        wbr_tier1,
        case
            when wbr_tier1 in ('ACTIVE CASES', 'RE-OPEN CLAIMS')
                then submitted_amazon_year
            else closed_amazon_year
        end as attribution_year,
        case
            when wbr_tier1 in ('ACTIVE CASES', 'RE-OPEN CLAIMS')
                then submitted_amazon_week
            else closed_amazon_week
        end as attribution_week,
        value_usd
    from {{ ref('int_claims_classified') }}

)

select
    wbr_tier1,

    {% for week in trailing_weeks %}
    sum(case when attribution_year = {{ week[0] }}
              and attribution_week = {{ week[1] }}
         then value_usd else 0 end) as wk{{ week[1] }}_value_usd,
    count(case when attribution_year = {{ week[0] }}
               and attribution_week = {{ week[1] }}
          then 1 end) as wk{{ week[1] }}_count,
    {% endfor %}

    sum(case when attribution_year = {{ report_year }}
              and attribution_week < {{ report_week }}
         then value_usd else 0 end) as ytd_value_usd,
    count(case when attribution_year = {{ report_year }}
               and attribution_week < {{ report_week }}
          then 1 end) as ytd_count

from claims
group by 1
