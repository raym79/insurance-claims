{{
  config(
    materialized='view',
    tags=['staging']
  )
}}

/*
  Staging Layer: 1:1 source-to-staging transformation.
  No business logic — only type casting, column renaming, and whitespace cleaning.
  Equivalent to: pipeline/staging.py
*/

with source_data as (

    select * from {{ source('raw_claims_status', 'insurance_claims_statu_hist') }}

),

renamed as (

    select
        -- Primary key
        trim(cast(src.claim_number as string))              as claim_number,

        -- Snapshot metadata
        safe_cast(src.snapshot_date as date)                 as snapshot_date,

        -- Dimensions
        trim(cast(src.carrier_name as string))              as carrier_name,
        trim(cast(src.country as string))                   as country,
        trim(cast(src.status as string))                    as status,
        trim(cast(src.reason as string))                    as reason,
        trim(cast(src.results as string))                   as results,
        trim(cast(src.insurance_claims_results as string))  as insurance_claims_results,
        trim(cast(src.source as string))                    as source,
        trim(cast(src.trailer_license_plate as string))     as trailer_license_plate,
        trim(cast(src.trailer_number as string))            as trailer_number,
        trim(cast(src.trailer_vin as string))               as trailer_vin,
        coalesce(
            nullif(upper(trim(cast(src.currency as string))), ''),
            'USD'
        )                                                   as currency,

        -- Dates
        safe_cast(src.submitted as date)                    as submitted_date,
        safe_cast(src.date_of_loss as date)                 as date_of_loss,
        safe_cast(src.dropped_off_date as date)             as dropped_off_date,
        safe_cast(src.case_date_closed as date)             as case_date_closed,
        safe_cast(src.last_seen_date as date)               as last_seen_date,

        -- Numeric
        safe_cast(src.value_of_trailer as numeric)          as value_of_trailer

    from source_data as src
    where nullif(trim(cast(src.claim_number as string)), '') is not null
      and safe_cast(src.snapshot_date as date) is not null

)

select * from renamed
