-- A claim should appear at most once in each report week.

select
    claim_number,
    report_year,
    report_week,
    count(*) as occurrence_count
from {{ ref('mart_claims_weekly') }}
group by 1, 2, 3
having count(*) > 1
