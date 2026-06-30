{{
  config(
    materialized='table',
    tags=['marts', 'weekly'],
    partition_by={
      'field': 'submitted_date',
      'data_type': 'date',
      'granularity': 'month'
    },
    cluster_by=['claim_number', 'status']
  )
}}

/*
  Breakdown detail for active claims — WBR Breakdown sheet.
  Equivalent to: MartLayer.build_breakdowns() (active sections)
*/

with claims as (

    select * from {{ ref('int_claims_classified') }}
    where wbr_tier1 in ('ACTIVE CASES', 'RE-OPEN CLAIMS')

)

select
    claim_number,
    country,
    carrier_name,
    trailer_license_plate,
    trailer_number,
    status,
    reason,
    insurance_claims_results,
    source,
    submitted_date,
    date_of_loss,
    value_of_trailer,
    value_usd,
    currency,
    wbr_tier1,
    wbr_tier2,
    wbr_tier3,
    submitted_year,
    submitted_week,

    -- Assign breakdown section for Excel rendering
    case
        when wbr_tier1 = 'RE-OPEN CLAIMS'
            then 'RE_OPENED'
        when wbr_tier2 = 'In Process - Investigating'
            then 'IN_PROCESS'
        when wbr_tier3 = 'Found'
            then 'WAITING_FOR_REPLY_FOUND'
        when wbr_tier3 = 'Not Found / Potential Claim'
            then 'WAITING_FOR_REPLY_NOT_FOUND'
        when wbr_tier3 = 'Not In Network'
            then 'WAITING_FOR_REPLY_NOT_IN_NETWORK'
        else 'OTHER'
    end as breakdown_section

from claims
