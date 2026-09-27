"""Minimal Markdown to HTML (stdlib only) for trip write-ups.

Block: paragraphs (blank-line separated; single newlines become <br>), # to #### headings (shifted so a
write-up's `#` renders as <h3>), `-`/`*`/`1.` lists, `>` blockquotes, `---` rules.
Inline: **bold**, *italic*, `code`, [text](url), bare http(s) URLs, and HTML escaping of everything else.
"""
import html
import re

_LINK = re.compile(r'\[([^\]]+)\]\(([^)\s]+)\)')
_URL = re.compile(r'(?<![\w"=/])(https?://[^\s<]+[^\s<.,;:!?)\]])')
_BOLD = re.compile(r'\*\*(.+?)\*\*')
_ITAL = re.compile(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])')
_CODE = re.compile(r'`([^`]+)`')


def inline(s):
    codes = []

    def keep_code(m):
        codes.append('<code>%s</code>' % html.escape(m.group(1)))
        return '\x00%d\x00' % (len(codes) - 1)
    s = _CODE.sub(keep_code, s)
    links = []

    def keep_link(m):
        url = m.group(2)
        ext = url.startswith('http')
        links.append('<a href="%s"%s>%s</a>' % (html.escape(url, quote=True), ' rel="noopener"' if ext else '',
                                               _emph(html.escape(m.group(1)))))
        return '\x01%d\x01' % (len(links) - 1)
    s = _LINK.sub(keep_link, s)

    def keep_url(m):
        url = m.group(1)
        links.append('<a href="%s" rel="noopener">%s</a>' % (html.escape(url, quote=True), html.escape(url)))
        return '\x01%d\x01' % (len(links) - 1)
    s = _URL.sub(keep_url, s)
    s = _emph(html.escape(s, quote=False))
    s = re.sub(r'\x01(\d+)\x01', lambda m: links[int(m.group(1))], s)
    s = re.sub(r'\x00(\d+)\x00', lambda m: codes[int(m.group(1))], s)
    return s


def _emph(s):
    s = _BOLD.sub(r'<strong>\1</strong>', s)
    return _ITAL.sub(r'<em>\1</em>', s)


def to_html(text, heading_shift=2):
    lines = text.replace('\r\n', '\n').split('\n')
    out, para, i = [], [], 0

    def flush():
        if para:
            out.append('<p>%s</p>' % '<br>\n'.join(inline(l.strip()) for l in para))
            para.clear()
    while i < len(lines):
        ln = lines[i]
        st = ln.strip()
        if not st:
            flush()
            i += 1
            continue
        m = re.match(r'^(#{1,4})\s+(.*)$', st)
        if m:
            flush()
            lvl = min(6, len(m.group(1)) + heading_shift)
            out.append('<h%d>%s</h%d>' % (lvl, inline(m.group(2)), lvl))
            i += 1
            continue
        if re.match(r'^(-{3,}|\*{3,})$', st):
            flush()
            out.append('<hr>')
            i += 1
            continue
        if st.startswith('>'):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote.append(lines[i].strip()[1:].lstrip())
                i += 1
            out.append('<blockquote>%s</blockquote>' % to_html('\n'.join(quote), heading_shift))
            continue
        lm = re.match(r'^([-*]|\d+[.)])\s+', st)
        if lm:
            flush()
            ordered = lm.group(1)[0].isdigit()
            items = []
            while i < len(lines):
                s2 = lines[i].strip()
                m2 = re.match(r'^([-*]|\d+[.)])\s+(.*)$', s2)
                if m2:
                    items.append(m2.group(2))
                elif s2 and items and lines[i].startswith(' '):
                    items[-1] += ' ' + s2
                else:
                    break
                i += 1
            tag = 'ol' if ordered else 'ul'
            out.append('<%s>%s</%s>' % (tag, ''.join('<li>%s</li>' % inline(x) for x in items), tag))
            continue
        para.append(ln)
        i += 1
    flush()
    return '\n'.join(out)


def plain(text, limit=None):
    """Plain-text version (for excerpts and meta descriptions)."""
    t = _LINK.sub(r'\1', text)
    t = re.sub(r'[*`#>]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    if limit and len(t) > limit:
        cut = t[:limit].rsplit(' ', 1)[0].rstrip(',;:')
        return cut + '…'
    return t


if __name__ == '__main__':
    print(to_html('Hello *there* **bold** & <tag>\nline two https://example.com/x.\n\n# Head\n- a\n- b [link](https://a.b)\n\n> quote'))
