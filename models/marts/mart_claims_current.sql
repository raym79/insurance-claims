{{
  config(
    materialized='table',
    tags=['marts', 'current'],
    cluster_by=['claim_number', 'status', 'wbr_tier1']
  )
}}

/*
  Latest available snapshot for each claim.
  Grain: one row per claim_number.
*/

select *
from {{ ref('int_claims_classified') }}
qualify row_number() over (
    partition by claim_number
    order by snapshot_date desc
) = 1
