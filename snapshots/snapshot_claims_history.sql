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
    claim_number,
    carrier_name,
    country,
    status,
    reason,
    results,
    insurance_claims_results,
    case_date_closed,
    value_of_trailer,
    currency,
    source,
    submitted_date,
    _loaded_at as updated_at

from {{ ref('stg_insurance_claims') }}

{% endsnapshot %}
