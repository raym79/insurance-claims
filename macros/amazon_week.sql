/*
  Amazon Week Calculator macros for Redshift.
  Amazon weeks: Sunday-start, Week 1 = first week containing a Thursday.
  Equivalent to: pipeline/amazon_week.py

  Redshift's extract(dow from date) returns: 0=Sunday, 1=Monday, ..., 6=Saturday
  which conveniently matches our Sun-start convention directly.
*/


{% macro amazon_week_year(date_column) %}
{#
  Returns the Amazon Year for a given date.
  The Thursday of the same Sun-start week determines the year.
#}
    case
        when {{ date_column }} is null then null
        else extract(year from
            dateadd(day, (4 - extract(dow from {{ date_column }})::int), {{ date_column }})
        )::int
    end
{% endmacro %}


{% macro amazon_week_number(date_column) %}
{#
  Returns the Amazon Week Number (1-53) for a given date.
  Steps:
    1. Find Thursday of same Sun-start week
    2. Find first Thursday of that year
    3. week = (thursday - first_thursday) / 7 + 1
#}
    case
        when {{ date_column }} is null then null
        else (
            datediff(day,
                -- First Thursday of the Amazon Year
                dateadd(day,
                    (4 - extract(dow from
                        date_trunc('year',
                            dateadd(day, (4 - extract(dow from {{ date_column }})::int), {{ date_column }})
                        )
                    )::int + 7) % 7,
                    date_trunc('year',
                        dateadd(day, (4 - extract(dow from {{ date_column }})::int), {{ date_column }})
                    )
                ),
                -- Thursday of same week as input date
                dateadd(day, (4 - extract(dow from {{ date_column }})::int), {{ date_column }})
            ) / 7 + 1
        )::int
    end
{% endmacro %}
