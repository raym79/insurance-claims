{{
  config(
    materialized='ephemeral'
  )
}}

/*
  Identify whether a claim was previously closed before each snapshot.
  A claim is re-opened when its current snapshot is Open and any earlier
  snapshot was Closed.
*/

with claims as (

    select
        claim_number,
        snapshot_date,
        status,
        max(case when status = 'Closed' then 1 else 0 end) over (
            partition by claim_number
            order by snapshot_date
            rows between unbounded preceding and 1 preceding
        ) as prior_closed_count
    from {{ ref('stg_insurance_claims') }}

)

select
    claim_number,
    snapshot_date,
    status = 'Open' and coalesce(prior_closed_count, 0) > 0 as is_reopened
from claims
