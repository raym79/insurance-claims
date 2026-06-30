-- A claim_number + status combination should not appear more than once
-- in the same Amazon week (data quality check).

select
    claim_number,
    status,
    submitted_amazon_year,
    submitted_amazon_week,
    count(*) as occurrence_count
from {{ ref('int_claims_classified') }}
group by 1, 2, 3, 4
having count(*) > 1
