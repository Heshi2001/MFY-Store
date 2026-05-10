from django import template
register = template.Library()

@register.filter
def gte(value, arg):
    try:
        return int(value) >= int(arg)
    except (ValueError, TypeError):
        return False