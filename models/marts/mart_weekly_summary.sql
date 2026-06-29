{{
  config(
    materialized='table',
    tags=['marts', 'weekly'],
    dist='ALL',
    sort='sort_order'
  )
}}

/*
  Weekly Summary: Trailing 6 weeks + YTD counts and USD values per category.
  Driven by seed_category_hierarchy for display order.

  Run with: dbt run --vars '{report_year: 2026, report_week: 22}'
  Equivalent to: MartLayer.build_combined_summary()
*/

{% set report_year = var('report_year') %}
{% set report_week = var('report_week') %}
{% set trailing_weeks = generate_trailing_weeks(report_year, report_week, 6) %}

with claims as (

    select
        wbr_tier1,
        wbr_tier2,
        wbr_tier3,
        -- Attribution: Active uses submitted, Closed uses closed date
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

),

categories as (

    select * from {{ ref('seed_category_hierarchy') }}

),

summary as (

    select
        cat.display_label   as category,
        cat.sort_order,
        cat.indent_level,

        {% for week in trailing_weeks %}
        -- WK{{ week[1] }} counts and values
        coalesce(sum(
            case when c.attribution_year = {{ week[0] }}
                  and c.attribution_week = {{ week[1] }}
                  and (
                      -- Section header: match tier1
                      (cat.tier_match_value is null and c.wbr_tier1 = cat.tier1_filter)
                      or
                      -- Category row: match tier2 or tier3
                      (cat.tier_match_value is not null
                       and c.wbr_tier1 = cat.tier1_filter
                       and (c.wbr_tier2 = cat.tier_match_value
                            or c.wbr_tier3 = cat.tier_match_value))
                  )
            then 1 end
        ), 0) as wk{{ week[1] }}_count,

        coalesce(sum(
            case when c.attribution_year = {{ week[0] }}
                  and c.attribution_week = {{ week[1] }}
                  and (
                      (cat.tier_match_value is null and c.wbr_tier1 = cat.tier1_filter)
                      or
                      (cat.tier_match_value is not null
                       and c.wbr_tier1 = cat.tier1_filter
                       and (c.wbr_tier2 = cat.tier_match_value
                            or c.wbr_tier3 = cat.tier_match_value))
                  )
            then c.value_usd end
        ), 0)::decimal(12,2) as wk{{ week[1] }}_value_usd,
        {% endfor %}

        -- YTD
        coalesce(sum(
            case when c.attribution_year = {{ report_year }}
                  and c.attribution_week < {{ report_week }}
                  and (
                      (cat.tier_match_value is null and c.wbr_tier1 = cat.tier1_filter)
                      or
                      (cat.tier_match_value is not null
                       and c.wbr_tier1 = cat.tier1_filter
                       and (c.wbr_tier2 = cat.tier_match_value
                            or c.wbr_tier3 = cat.tier_match_value))
                  )
            then 1 end
        ), 0) as ytd_count,

        coalesce(sum(
            case when c.attribution_year = {{ report_year }}
                  and c.attribution_week < {{ report_week }}
                  and (
                      (cat.tier_match_value is null and c.wbr_tier1 = cat.tier1_filter)
                      or
                      (cat.tier_match_value is not null
                       and c.wbr_tier1 = cat.tier1_filter
                       and (c.wbr_tier2 = cat.tier_match_value
                            or c.wbr_tier3 = cat.tier_match_value))
                  )
            then c.value_usd end
        ), 0)::decimal(12,2) as ytd_value_usd

    from categories cat
    cross join claims c
    group by 1, 2, 3

)

select * from summary
order by sort_order
