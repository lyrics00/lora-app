from django import template

register = template.Library()

@register.filter
def simplify_duration(duration):
    """
    Convert a timedelta duration into a string like 'Xd Yh'
    """
    if not duration:
        return ""
    total_seconds = int(duration.total_seconds())
    days = total_seconds // (3600 * 24)
    hours = (total_seconds % (3600 * 24)) // 3600
    return f"{days}d {hours}h"