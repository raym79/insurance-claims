/*
  Report Week Calculator macros for BigQuery.
  Report weeks start on Sunday, and Week 1 is the first week containing
  a Thursday.

  BigQuery's extract(dayofweek from date) returns:
  1=Sunday, 2=Monday, ..., 7=Saturday.
*/


{% macro report_week_thursday(date_column) %}
    date_add(
        {{ date_column }},
        interval (5 - extract(dayofweek from {{ date_column }})) day
    )
{% endmacro %}


{% macro report_week_year(date_column) %}
{#
  Returns the report year for a date. The Thursday in the same
  Sunday-start week determines the year.
#}
    case
        when {{ date_column }} is null then null
        else cast(
            extract(year from {{ report_week_thursday(date_column) }})
            as int64
        )
    end
{% endmacro %}


{% macro report_week_number(date_column) %}
{#
  Returns the report week number (1-53):
    1. Find the Thursday in the date's Sunday-start week.
    2. Find the first Thursday of that report year.
    3. Count the complete seven-day intervals between those Thursdays.
#}
    case
        when {{ date_column }} is null then null
        else cast(
            div(
                date_diff(
                    {{ report_week_thursday(date_column) }},
                    date_add(
                        date_trunc(
                            {{ report_week_thursday(date_column) }},
                            year
                        ),
                        interval mod(
                            5 - extract(
                                dayofweek from date_trunc(
                                    {{ report_week_thursday(date_column) }},
                                    year
                                )
                            ) + 7,
                            7
                        ) day
                    ),
                    day
                ),
                7
            ) + 1
            as int64
        )
    end
{% endmacro %}
