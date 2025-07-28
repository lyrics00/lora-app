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
    
@register.filter
def get_average_rating(ratings):
    """
    Given a RelatedManager or iterable of rating objects (with a 'rating' attr),
    return the rounded average (0–5).
    """
    qs = ratings.all() if hasattr(ratings, 'all') else ratings
    try:
        count = qs.count()
    except:
        count = len(qs)
    if not count:
        return 0
    total = sum(getattr(r, 'rating', r) for r in qs)
    return round(total / count)