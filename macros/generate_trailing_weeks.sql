{% macro amazon_weeks_in_year(year) %}
{#
  Amazon week-years use the first-Thursday rule, so they have the same
  52/53-week year pattern as ISO calendars: 53 weeks when January 1 is
  Thursday, or when a leap year starts on Wednesday.
#}
    {% set year = year | int %}
    {% set jan_1_weekday = modules.datetime.date(year, 1, 1).weekday() %}
    {% set is_leap_year =
        (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    %}

    {% if jan_1_weekday == 3 or (jan_1_weekday == 2 and is_leap_year) %}
        {{ return(53) }}
    {% else %}
        {{ return(52) }}
    {% endif %}
{% endmacro %}


{% macro generate_trailing_weeks(report_year, report_week, num_weeks) %}
{#
  Returns a list of (year, week) tuples for the trailing N weeks
  before the given report week.

  Example: generate_trailing_weeks(2026, 22, 6)
  Returns: [(2026, 16), (2026, 17), (2026, 18), (2026, 19), (2026, 20), (2026, 21)]

  Equivalent to: the trailing-week loop in MartLayer.build_weekly_summary()
#}
    {% set report_year = report_year | int %}
    {% set report_week = report_week | int %}
    {% set num_weeks = num_weeks | int %}
    {% set max_report_week = amazon_weeks_in_year(report_year) %}

    {% if report_week < 1 or report_week > max_report_week %}
        {{ exceptions.raise_compiler_error(
            "report_week must be between 1 and "
            ~ max_report_week
            ~ " for Amazon year "
            ~ report_year
        ) }}
    {% endif %}

    {% if num_weeks < 0 %}
        {{ exceptions.raise_compiler_error("num_weeks cannot be negative") }}
    {% endif %}

    {% set weeks = [] %}
    {% set ns = namespace(year=report_year, week=report_week) %}

    {% for i in range(num_weeks) %}
        {% if ns.week > 1 %}
            {% set ns.week = ns.week - 1 %}
        {% else %}
            {% set ns.year = ns.year - 1 %}
            {% set ns.week = amazon_weeks_in_year(ns.year) %}
        {% endif %}

        {% do weeks.insert(0, (ns.year, ns.week)) %}
    {% endfor %}

    {{ return(weeks) }}
{% endmacro %}
