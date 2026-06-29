{% macro generate_trailing_weeks(report_year, report_week, num_weeks) %}
{#
  Returns a list of (year, week) tuples for the trailing N weeks
  before the given report week.

  Example: generate_trailing_weeks(2026, 22, 6)
  Returns: [(2026, 16), (2026, 17), (2026, 18), (2026, 19), (2026, 20), (2026, 21)]

  Equivalent to: the trailing-week loop in MartLayer.build_weekly_summary()
#}
    {% set weeks = [] %}
    {% set ns = namespace(year=report_year, week=report_week) %}

    {% for i in range(num_weeks) %}
        {% if ns.week > 1 %}
            {% set ns.week = ns.week - 1 %}
        {% else %}
            {% set ns.year = ns.year - 1 %}
            {% set ns.week = 52 %}
        {% endif %}

        {% do weeks.insert(0, (ns.year, ns.week)) %}
    {% endfor %}

    {{ return(weeks) }}
{% endmacro %}
