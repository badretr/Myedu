from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        # Try the key as-is first
        val = dictionary.get(key)
        if val is not None:
            return val
        # If key is int, try string; if key is string, try int
        if isinstance(key, int):
            return dictionary.get(str(key))
        if isinstance(key, str):
            try:
                return dictionary.get(int(key))
            except (ValueError, TypeError):
                pass
        return None
    return None
