from django import template

register = template.Library()

@register.filter
def get_user_rating(ratings, user):
    """
    Returns the rating value for the given user from the ratings queryset.
    Returns None if no rating is found.
    """
    try:
        return ratings.get(user=user).rating
    except Exception:
        return None