{{
  config(
    materialized='incremental',
    unique_key='claim_surrogate_key',
    incremental_strategy='merge',
    on_schema_change='append_new_columns',
    dist='claim_number',
    sort='_loaded_at'
  )
}}

/*
  Classification Layer: Applies Tier 1 / Tier 2 / Tier 3 WBR category logic.
  Derives Amazon Week columns for submitted and closed dates.
  Equivalent to: pipeline/intermediate.py
*/

with staged_claims as (

    select * from {{ ref('stg_insurance_claims') }}

    {% if is_incremental() %}
    where _loaded_at > (select max(_loaded_at) from {{ this }})
    {% endif %}

),

reopened_claims as (

    select * from {{ ref('int_claims_reopened') }}

),

classified as (

    select
        {{ dbt_utils.generate_surrogate_key(
            ['sc.claim_number', 'sc.status', 'sc.submitted_date']
        ) }} as claim_surrogate_key,

        sc.*,

        -- Amazon Week for submitted date
        {{ amazon_week_year('sc.submitted_date') }}   as submitted_amazon_year,
        {{ amazon_week_number('sc.submitted_date') }} as submitted_amazon_week,

        -- Amazon Week for case_date_closed
        {{ amazon_week_year('sc.case_date_closed') }}   as closed_amazon_year,
        {{ amazon_week_number('sc.case_date_closed') }} as closed_amazon_week,

        -- Tier 1
        case
            when sc.status = 'Open' and rc.is_reopened = true
                then 'RE-OPEN CLAIMS'
            when sc.status = 'Open'
                then 'ACTIVE CASES'
            when sc.status = 'Closed'
                then 'CLOSED CASES'
            else 'ACTIVE CASES'
        end as wbr_tier1,

        -- Tier 2
        case
            when sc.status = 'Open' and rc.is_reopened = true
                then 'Re-Opened'
            when sc.status = 'Open'
                 and sc.insurance_claims_results = 'Waiting For Reply'
                then 'Waiting For Reply From Insurance'
            when sc.status = 'Open'
                then 'In Process - Investigating'
            when sc.status = 'Closed' and sc.reason = 'Found'
                then 'Found'
            when sc.status = 'Closed'
                then 'Not Found'
            else 'In Process - Investigating'
        end as wbr_tier2,

        -- Tier 3
        case
            when sc.status = 'Open'
                 and sc.insurance_claims_results = 'Waiting For Reply'
                 and sc.reason = 'Found'
                then 'Found'
            when sc.status = 'Open'
                 and sc.insurance_claims_results = 'Waiting For Reply'
                 and sc.reason = 'No Longer In Network'
                then 'Not In Amazon Network'
            when sc.status = 'Open'
                 and sc.insurance_claims_results = 'Waiting For Reply'
                then 'Not Found At Site'
            when sc.status = 'Closed' and sc.reason = 'Found'
                 and sc.results = 'Carrier Has & Picked Up'
                then 'Carrier Picked Up'
            when sc.status = 'Closed' and sc.reason = 'Found'
                 and sc.results = 'Found -Sent To Towing Yard'
                then 'Found -Sent To Towing Yard'
            when sc.status = 'Closed' and sc.reason = 'Found'
                 and sc.results = 'Found & Recovered'
                then 'ROC Team Returned'
            when sc.status = 'Closed' and sc.reason = 'Found'
                 and sc.results = 'No Response From Carrier To 10-Day Closing Letter'
                then 'Amazon Not Liable Due To No Response From Carrier For Disposition'
            when sc.status = 'Closed' and sc.reason = 'Found'
                then 'Carrier Picked Up'
            when sc.status = 'Closed' and sc.reason != 'Found'
                 and sc.insurance_claims_results = 'Amazon Not Liable'
                then 'Amazon Not Liable'
            when sc.status = 'Closed' and sc.reason != 'Found'
                then 'Amazon Liable'
            else null
        end as wbr_tier3,

        -- Currency conversion
        sc.value_of_trailer * coalesce(cr.rate_to_usd, 1.0) as value_usd

    from staged_claims sc
    left join reopened_claims rc
        on sc.claim_number = rc.claim_number
    left join {{ ref('seed_currency_rates') }} cr
        on sc.currency = cr.currency_code

)

select * from classified
