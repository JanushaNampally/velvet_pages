from django.core.cache import cache


def hit(key, limit, window):
    """Count an attempt; return True when the caller is OVER the limit."""
    if cache.add(key, 1, window):
        return False
    try:
        return cache.incr(key) > limit
    except ValueError:
        cache.set(key, 1, window)
        return False