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

with source as (

    select * from {{ source('raw_claims_status', 'insurance_claims_status') }}

),

renamed as (

    select
        -- Primary key
        trim(claim_number)                              as claim_number,
        cast(submitted as date)                         as submitted_date,
        
        -- Dimensions
        trim(carrier_name)                              as carrier_name,
        trim(country)                                   as country,
        trim(status)                                    as status,
        trim(reason)                                    as reason,
        trim(results)                                   as results,
        trim(insurance_claims_results)                  as insurance_claims_results,
        trim(source)                                    as source,
        trim(trailer_license_plate)                     as trailer_license_plate,
        trim(trailer_number)                            as trailer_number,
        trim(trailer_vin)                               as trailer_vin,
        upper(trim(currency))                          as currency,

        -- Dates
        
        cast(date_of_loss as date)                      as date_of_loss,
        cast(dropped_off_date as date)                  as dropped_off_date,
        cast(case_date_closed as date)                  as case_date_closed,
        cast(last_seen_date as date)                    as last_seen_date,

        -- Numeric
        cast(value_of_trailer as decimal(12,2))         as value_of_trailer,
       
        -- Metadata
        _loaded_at

    from source

)

select * from renamed
