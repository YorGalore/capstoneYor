import re

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from apps.analytics.briefs import DRAFT_BANNER

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, "")


@register.filter
def strip_draft_banner(content):
    """Drop the leading '**[DRAF …]**' banner so the template can render it as a
    proper callout instead of literal asterisks in the body text."""
    if not content:
        return ""
    if content.startswith(DRAFT_BANNER):
        return content[len(DRAFT_BANNER):].lstrip("\n")
    return content


@register.filter
def has_draft_banner(content):
    return bool(content) and content.startswith(DRAFT_BANNER)


_BOLD = re.compile(r"\*\*(.+?)\*\*")


def _inline(text):
    """Escape, then apply the only inline mark the composer emits: **bold**."""
    escaped = conditional_escape(text)
    return _BOLD.sub(r"<strong>\1</strong>", escaped)


@register.filter
def incident_body(content):
    """Render the deterministic markdown our composers produce — `## heading`,
    `### subheading`, `- bullet`, `**bold**`, blank-line paragraphs — as clean,
    escaped HTML. Intentionally tiny: it handles exactly what `incidents.py` and
    `briefs.py` write and nothing more, so it can never render untrusted markup."""
    body = strip_draft_banner(content)
    if not body:
        return ""

    html = []
    list_open = False

    def close_list():
        nonlocal list_open
        if list_open:
            html.append("</ul>")
            list_open = False

    for raw in body.split("\n"):
        line = raw.strip()
        if not line:
            close_list()
            continue
        if line.startswith("### "):
            close_list()
            html.append(f"<h5 class=\"incident-narrative-subsub\">{_inline(line[4:])}</h5>")
        elif line.startswith("## "):
            close_list()
            html.append(f"<h4 class=\"incident-narrative-sub\">{_inline(line[3:])}</h4>")
        elif line.startswith("- "):
            if not list_open:
                html.append("<ul class=\"incident-narrative-list\">")
                list_open = True
            html.append(f"<li>{_inline(line[2:])}</li>")
        else:
            close_list()
            html.append(f"<p>{_inline(line)}</p>")

    close_list()
    return mark_safe("".join(html))


@register.filter
def brief_body(content):
    """Same renderer, for brief sections. A brief section already prints its own
    numbered title and risk chip, so the `## title` the composer repeats as the
    first body line is dropped to avoid showing the title twice."""
    body = strip_draft_banner(content)
    lines = body.split("\n")
    if lines and lines[0].strip().startswith("## "):
        lines = lines[1:]
    return incident_body("\n".join(lines).lstrip("\n"))


# Contextual glyph for an incident, matched on issue keywords. Decorative only —
# the severity border and chip carry the real signal — but a recognisable icon
# helps an operator find the right card faster than reading every title.
_ICON_RULES = [
    (("jalan", "aspal", "jembatan", "lubang"), "🛣️"),
    (("air", "pdam", "banjir", "drainase"), "💧"),
    (("sampah", "tps", "kebersihan", "limbah"), "🗑️"),
    (("listrik", "lampu", "pln"), "💡"),
    (("sekolah", "pendidikan", "guru"), "🏫"),
    (("kesehatan", "rumah sakit", "puskesmas", "posyandu"), "🏥"),
    (("pungli", "korupsi", "integritas", "adminduk", "pelayanan"), "🏛️"),
]


@register.filter
def incident_icon(title):
    lowered = (title or "").lower()
    for keywords, icon in _ICON_RULES:
        if any(word in lowered for word in keywords):
            return icon
    return "📋"
