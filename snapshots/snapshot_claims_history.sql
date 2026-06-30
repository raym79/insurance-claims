{% snapshot snapshot_claims_history %}

{{
  config(
    target_schema='snapshots',
    unique_key='claim_number',
    strategy='check',
    check_cols=['status', 'reason', 'results', 'insurance_claims_results', 'case_date_closed'],
    invalidate_hard_deletes=True
  )
}}

/*
  SCD Type-2 snapshot: Captures historical changes to claim status.
  Enables trend analysis (e.g., "How long do claims stay open before closing?")
*/

select
    claims.claim_number,
    claims.carrier_name,
    claims.country,
    claims.status,
    claims.reason,
    claims.results,
    claims.insurance_claims_results,
    claims.case_date_closed,
    claims.value_of_trailer,
    claims.currency,
    claims.source,
    claims.submitted_date

from {{ ref('stg_insurance_claims') }} as claims

{% endsnapshot %}
