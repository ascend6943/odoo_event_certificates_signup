# -*- coding: utf-8 -*-
"""Shared helpers to render user-provided HTML templates in reports.

Both the company certificate report and the topic signup sheet report allow an
event manager to paste a full HTML template into a plain ``Text`` field. This
module centralises the normalisation of that source so the two reports behave
identically.

The templates are stored in plain ``Text`` fields, which keep HTML/CSS verbatim.
A legacy sanitized ``Html`` field is also supported as a fallback: because the
Odoo sanitizer escapes pasted markup, turns indentation into ``&nbsp;`` and
auto-links bare URLs, that value is cleaned up before use.
"""
import html as html_lib
import re

from markupsafe import Markup, escape

# Matches a complete HTML document (with or without a doctype).
FULL_DOC_RE = re.compile(r'<\s*(?:!doctype|html)\b', re.IGNORECASE)
_BODY_RE = re.compile(r'<\s*body\b[^>]*>(.*)<\s*/\s*body\s*>',
                      re.IGNORECASE | re.DOTALL)
_STYLE_RE = re.compile(r'<\s*style\b[^>]*>(.*?)<\s*/\s*style\s*>',
                       re.IGNORECASE | re.DOTALL)
# Anchor whose text starts with its href, produced by the sanitizer when it
# auto-links bare URLs (which corrupts CSS such as ``url('https://...')``).
_AUTOLINK_RE = re.compile(
    r"""<a\s+[^>]*href=["']([^"']+)["'][^>]*>(\s*\1[^<]*)</a>""",
    re.IGNORECASE)

# Whitespace-only entities. When a template is pasted from Word/Outlook it is
# full of ``&nbsp;``; if that entity is left in the source it is later decoded
# to a non-breaking space, which some PDF renderers show as a stray ``Â``. A
# plain-text HTML template never wants a *literal* ``&nbsp;`` to be visible, so
# it is safe to turn these into ordinary spaces.
_NBSP_ENTITY_RE = re.compile(r'&(?:nbsp|#160|#x0*a0);', re.IGNORECASE)

PLACEHOLDER_RE = re.compile(r'\{\{\s*(\w+)\s*\}\}')
# An attribute value that a placeholder sits inside, e.g. ``src="{{sig}}"``.
# The attribute name is captured so it is preserved on substitution (it would
# otherwise be swallowed together with the placeholder).
_ATTR_VALUE_RE = re.compile(
    r"""(\w+)\s*=\s*(["'])\{\{\s*(\w+)\s*\}\}\2""")


class ResourceValue:
    """A replacement value that is only meaningful inside an attribute.

    The instructor signature expands to a ``data:image/...;base64,...`` URI.
    That is only useful when the placeholder is used as an attribute value
    (typically ``<img src="{{instructor_signature}}"/>``). If the placeholder is
    used as plain text, printing the whole data URI dumps a wall of base64 into
    the document, so in that position the value degrades to an empty string.
    """

    def __init__(self, value):
        self.value = value or ''

    def __bool__(self):
        return bool(self.value)


class _Marker:
    """Placeholder inserted into the source to mark an attribute position.

    A sentinel (not a ``{{name}}`` placeholder) is used so the generic
    substitution pass cannot touch it; it is resolved afterwards.
    """

    __slots__ = ('name',)

    def __init__(self, name):
        self.name = name


def restore_legacy_source(raw_html):
    """Recover the original source stored in a sanitized ``Html`` field.

    The Odoo sanitizer escapes pasted markup (angle brackets become entities)
    and wraps every source line in a ``<div>``. It also emits ``&nbsp;`` for
    indentation and can auto-link URLs found in the source. Undo what can be
    undone so a legacy value still renders.
    """
    source = html_lib.unescape(raw_html or '')
    # Undo the per-line <div> wrappers added by the sanitizer.
    source = re.sub(r'</div>\s*<div[^>]*>', '\n', source)
    source = re.sub(r'^\s*<div[^>]*>', '', source)
    source = re.sub(r'</div>\s*$', '', source)
    # Non-breaking spaces emitted for indentation become plain spaces.
    source = source.replace('\xa0', ' ')
    # Repair URLs the sanitizer wrapped in an anchor tag.
    source = _AUTOLINK_RE.sub(lambda match: match.group(2).lstrip(), source)
    return source


def normalize_template(raw_source, legacy=False):
    """Return usable markup from a stored template value.

    When the source is a full HTML document, only the ``<style>`` blocks and
    the ``<body>`` inner content are kept: injecting a nested
    ``<html>``/``<head>``/``<body>`` into the report body would be invalid and
    would otherwise be rendered as visible text.
    """
    source = restore_legacy_source(raw_source) if legacy else str(raw_source or '')
    source = source.strip()
    if not source:
        return ''

    if FULL_DOC_RE.search(source):
        styles = _STYLE_RE.findall(source)
        body_match = _BODY_RE.search(source)
        inner = body_match.group(1) if body_match else source
        parts = []
        if styles:
            parts.append(
                '<style>%s</style>' % '\n'.join(style.strip() for style in styles)
            )
        parts.append(inner.strip())
        source = '\n'.join(part for part in parts if part)

    # Pasted Word/Outlook HTML is full of whitespace entities; a visible
    # ``&nbsp;`` in the output is never wanted, so normalise it away.
    source = _NBSP_ENTITY_RE.sub(' ', source)
    source = source.replace('\xa0', ' ')
    return source


def render_template(source, replacements):
    """Substitute ``{{placeholder}}`` values and return safe markup.

    ``replacements`` maps placeholder names (without braces) to already
    rendered values. Values wrapped in :class:`Markup` are inserted as HTML;
    :class:`ResourceValue` values (such as the instructor signature) are only
    emitted when the placeholder is used inside an attribute; plain strings are
    escaped.
    """
    if not source:
        return False

    # Replace placeholders that sit inside an attribute value first, so that
    # resource placeholders (data URIs) are only expanded when they are used as
    # an attribute (e.g. ``<img src="{{instructor_signature}}"/>``).
    attr_values = {}

    def _attr_replace(match):
        attr, quote, name = match.group(1), match.group(2), match.group(3)
        value = replacements.get(name)
        if isinstance(value, ResourceValue):
            token = '__OC_ATTR_%d__' % len(attr_values)
            attr_values[token] = str(escape(value.value)) if value.value else ''
            return '%s=%s%s%s' % (attr, quote, token, quote)
        return match.group(0)

    source = _ATTR_VALUE_RE.sub(_attr_replace, source)

    def _replace(match):
        name = match.group(1)
        if name not in replacements:
            return match.group(0)
        value = replacements[name]
        if isinstance(value, ResourceValue):
            # Bare use of an attribute-only value: drop it rather than dump a
            # multi-kilobyte data URI into the document text.
            return ''
        if hasattr(value, '__html__'):
            return str(value)
        return str(escape(value if value is not None else ''))

    rendered = PLACEHOLDER_RE.sub(_replace, source)
    for token, value in attr_values.items():
        rendered = rendered.replace(token, value)
    return Markup(rendered)
