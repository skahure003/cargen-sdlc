from django import template


register = template.Library()


@register.filter
def get_item(mapping, key):
    return mapping.get(key, [])


@register.filter
def theme_class(value):
    mapping = {
        "risk": "theme-risk",
        "risks": "theme-risk",
        "build": "theme-build",
        "release": "theme-release",
        "runtime": "theme-runtime",
        "lifecycle": "theme-lifecycle",
        "background": "theme-neutral",
        "area": "theme-neutral",
    }
    return mapping.get(value, "theme-neutral")
