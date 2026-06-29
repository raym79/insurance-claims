{{
  config(
    materialized='ephemeral'
  )
}}

/*
  Detect re-opened claims: claim_numbers that appear in BOTH Open and Closed status.
  Equivalent to: IntermediateLayer._detect_reopened()
*/

with open_claims as (

    select distinct claim_number
    from {{ ref('stg_insurance_claims') }}
    where status = 'Open'
      and claim_number is not null

),

closed_claims as (

    select distinct claim_number
    from {{ ref('stg_insurance_claims') }}
    where status = 'Closed'
      and claim_number is not null

)

select
    o.claim_number,
    true as is_reopened
from open_claims o
inner join closed_claims c
    on o.claim_number = c.claim_number
