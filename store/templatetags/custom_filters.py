from django import template
import re
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def highlight(text, query):
    """Highlight the query inside text with <mark> for SEO and UX"""
    if not query:
        return text

    try:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        highlighted = pattern.sub(
            lambda m: f"<mark class='bg-yellow-100 text-[#006A4E] font-semibold'>{m.group(0)}</mark>",
            text
        )
        return mark_safe(highlighted)  # allows HTML rendering safely
    except Exception:
        return text
