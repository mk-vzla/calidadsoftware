from django import template

register = template.Library()


@register.filter(name='intdot')
def intdot(value):
    """Format an integer with thousands separated by dots.

    Example: 1234567 -> '1.234.567'
    If value cannot be converted to int, returns it unchanged.
    """
    try:
        n = int(value)
    except Exception:
        return value
    # format with comma thousands then replace by dot
    return format(n, ",d").replace(",", ".")
