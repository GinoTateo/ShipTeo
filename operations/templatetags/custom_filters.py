from django import template

register = template.Library()


@register.filter(name='to_int')
def to_int(value):
    """Converts a float value to int if it's a whole number."""
    try:
        return int(value) if value == int(value) else value
    except (ValueError, TypeError):
        return value


@register.filter(name='weeks_of_supply_class')
def weeks_of_supply_class(weeks_of_supply):
    if weeks_of_supply >= 2:
        return 'text-higher'
    else:
        return 'text-lower'
