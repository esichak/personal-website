"""A small YAML subset for Markdown front matter (stdlib only).

Supported: `key: value` mappings, nested mappings by indentation, `- item` lists (of scalars or mappings),
inline lists `[a, b]`, quoted strings, ints, floats, true/false, null/~, and `#` comments on their own line.
That covers every field the trip files use; anything fancier should stay out of front matter.
"""
import json
import re

_NUM = re.compile(r'^-?\d+(\.\d+)?$')


def split(text):
    """Return (meta dict, body str). A file without front matter gives ({}, text)."""
    if not text.startswith('---'):
        return {}, text
    lines = text.split('\n')
    for i in range(1, len(lines)):
        if lines[i].rstrip() == '---':
            return loads('\n'.join(lines[1:i])), '\n'.join(lines[i + 1:]).lstrip('\n')
    raise ValueError('front matter is not closed with ---')


def _scalar(s):
    s = s.strip()
    if s == '' or s in ('~', 'null'):
        return None
    if s[0] == '"':
        return json.loads(s)
    if s[0] == "'" and s[-1] == "'":
        return s[1:-1].replace("''", "'")
    if s[0] == '[' and s[-1] == ']':
        inner = s[1:-1].strip()
        return [_scalar(x) for x in _split_inline(inner)] if inner else []
    if s in ('true', 'True'):
        return True
    if s in ('false', 'False'):
        return False
    if _NUM.match(s):
        return float(s) if '.' in s else int(s)
    return s


def _split_inline(s):
    out, cur, q = [], '', None
    for ch in s:
        if q:
            cur += ch
            if ch == q:
                q = None
        elif ch in '"\'':
            q = ch
            cur += ch
        elif ch == ',':
            out.append(cur)
            cur = ''
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out]


def _key_split(s):
    """Split 'key: value' on the first ': ' (or trailing ':') outside quotes."""
    q = None
    for i, ch in enumerate(s):
        if q:
            if ch == q:
                q = None
        elif ch in '"\'':
            q = ch
        elif ch == ':' and (i + 1 == len(s) or s[i + 1] == ' '):
            k = s[:i].strip()
            if k[:1] in '"\'':
                k = _scalar(k)
            return k, s[i + 1:].strip()
    return None, None


def loads(text):
    rows = []
    for raw in text.split('\n'):
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        rows.append((len(raw) - len(raw.lstrip(' ')), raw.strip()))
    val, i = _block(rows, 0, rows[0][0] if rows else 0)
    return val if isinstance(val, dict) else {}


def _block(rows, i, ind):
    if i >= len(rows):
        return None, i
    if rows[i][1].startswith('- ') or rows[i][1] == '-':
        out = []
        while i < len(rows) and rows[i][0] == ind and (rows[i][1].startswith('- ') or rows[i][1] == '-'):
            item = rows[i][1][2:].strip()
            k, v = _key_split(item)
            if k is not None:
                # a mapping item: first key on the dash line, the rest indented under it
                sub = [(ind + 2, item)]
                j = i + 1
                while j < len(rows) and rows[j][0] > ind:
                    sub.append(rows[j])
                    j += 1
                val, _ = _block(sub, 0, ind + 2)
                out.append(val)
                i = j
            elif item == '':
                val, i = _block(rows, i + 1, rows[i + 1][0]) if i + 1 < len(rows) and rows[i + 1][0] > ind else (None, i + 1)
                out.append(val)
            else:
                out.append(_scalar(item))
                i += 1
        return out, i
    out = {}
    while i < len(rows) and rows[i][0] == ind:
        k, v = _key_split(rows[i][1])
        if k is None:
            raise ValueError('expected "key: value", got: ' + rows[i][1])
        if v == '':
            if i + 1 < len(rows) and rows[i + 1][0] > ind:
                out[k], i = _block(rows, i + 1, rows[i + 1][0])
            elif i + 1 < len(rows) and rows[i + 1][0] == ind and rows[i + 1][1].startswith('- '):
                out[k], i = _block(rows, i + 1, ind)  # list at the same indent as its key
            else:
                out[k] = None
                i += 1
        else:
            out[k] = _scalar(v)
            i += 1
    return out, i


# ---------------------------------------------------------------- dump

_PLAIN = re.compile(r'^[A-Za-z0-9À-ž][^:#\n\[\]{}"\']*$')


def _dump_scalar(v):
    if v is None:
        return ''
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, (int, float)):
        return repr(v) if isinstance(v, float) else str(v)
    s = str(v)
    if _PLAIN.match(s) and s.strip() == s and s not in ('true', 'false', 'null', '~') and not _NUM.match(s):
        return s
    return json.dumps(s, ensure_ascii=False)


def dumps(obj, ind=0):
    pad = ' ' * ind
    lines = []
    for k, v in obj.items():
        if isinstance(v, dict):
            if not v:
                continue
            lines.append('%s%s:' % (pad, k))
            lines.append(dumps(v, ind + 2))
        elif isinstance(v, list):
            if not v:
                continue
            if all(not isinstance(x, (dict, list)) for x in v) and len(v) <= 8 and sum(len(str(x)) for x in v) < 60:
                lines.append('%s%s: [%s]' % (pad, k, ', '.join(_dump_scalar(x) for x in v)))
                continue
            lines.append('%s%s:' % (pad, k))
            for x in v:
                if isinstance(x, dict):
                    sub = dumps(x, ind + 4).split('\n')
                    lines.append('%s  - %s' % (pad, sub[0].strip()))
                    lines.extend(sub[1:])
                else:
                    lines.append('%s  - %s' % (pad, _dump_scalar(x)))
        else:
            if v is None:
                continue
            lines.append('%s%s: %s' % (pad, k, _dump_scalar(v)))
    return '\n'.join(l for l in lines if l != '')


def render(meta, body):
    return '---\n%s\n---\n\n%s\n' % (dumps(meta), body.strip())


if __name__ == '__main__':
    sample = {'title': "Lover's Leap: Corrugation Corner", 'date': '2026-03-15', 'n': 3, 'x': 1.5, 'ok': True,
              'tags': ['a', 'b c'], 'beta': [{'label': 'Trailhead', 'value': 'Twin Lakes'}, {'label': 'Grade', 'value': '5.7'}],
              'map': {'peaks': ['Matterhorn Peak'], 'zoom': 2},
              'photos': [{'file': 'photos/01.jpg', 'alt': 'Skier: "steep" line, 35°', 'w': 1600}]}
    txt = dumps(sample)
    print(txt)
    back = loads(txt)
    assert back == sample, (back, sample)
    print('roundtrip ok')
