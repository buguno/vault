from django import template
from django.utils.safestring import mark_safe

register = template.Library()

ACTIVE = (
    'bg-emerald-50 font-medium text-emerald-800 '
    'dark:bg-emerald-950 dark:text-emerald-300'
)
IDLE = (
    'text-stone-600 hover:bg-stone-100 dark:text-stone-300 '
    'dark:hover:bg-stone-800'
)


def _is_active(context, prefix) -> bool:
    path = context['request'].path

    return path == '/' if prefix == '/' else path.startswith(prefix)


@register.simple_tag(takes_context=True)
def nav_class(context, prefix):
    return ACTIVE if _is_active(context, prefix) else IDLE


@register.simple_tag(takes_context=True)
def nav_current(context, prefix):
    """`aria-current` for the active link, so it is not told by color alone."""
    return (
        mark_safe('aria-current="page"') if _is_active(context, prefix) else ''
    )
