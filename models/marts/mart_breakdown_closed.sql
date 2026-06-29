{{
  config(
    materialized='table',
    tags=['marts', 'weekly'],
    dist='claim_number',
    sort='case_date_closed'
  )
}}

/*
  Breakdown detail for closed claims.
  Equivalent to: MartLayer.build_breakdowns() (closed section)
*/

select
    claim_number,
    country,
    carrier_name,
    trailer_license_plate,
    trailer_number,
    status,
    reason,
    insurance_claims_results,
    results,
    source,
    case_date_closed,
    value_of_trailer,
    value_usd,
    currency,
    wbr_tier1,
    wbr_tier2,
    wbr_tier3,
    closed_amazon_year,
    closed_amazon_week

from {{ ref('int_claims_classified') }}
where wbr_tier1 = 'CLOSED CASES'
order by case_date_closed desc
