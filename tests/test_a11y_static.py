"""Phase 4: static checks of the accessibility fixes of contract-phase4.md section 6, on the sources under assets/ and
on the markup a fixture site generates. No browser, no node: everything here reads text.

What is checked, and how far a static check can go:

  D1  focus under a second sticky bar    series.css / multiday.css: every control inside the day log / the day body gets
                                         a scroll margin built on the bar's own height variable (cascade, on real markup)
  D2  no JavaScript: the header          base.css has the (scripting: none) block; with scripting off the menu button,
  D3                                     every units switch (the About page's too) and the Search link are not displayed
                                         and the links are (cascade, on the generated header: a rule that is there but
                                         loses to another rule is a control that still shows); the links wrap, nothing
                                         in the header scrolls or clips, and under 480 px the header does not stick,
                                         reserves no height and leaves room for a focus ring. With scripting on, none
                                         of it applies
  D4  map cluster markers                base.js gives focus listeners to map pins and to no .mk-cluster element
  D5  short viewports                    multiday.css: the day nav is not sticky under a max-height query
  D6  the copy fallback field            base.js closes it when focus goes somewhere outside .copy (not on a focusout
                                         that goes nowhere), and on Escape from anywhere; Escape in the field focuses the
                                         button before closing; closeCopy lets go of the focus first and removes only
                                         what is still in the page
  D7  44 px targets                      the All radio and its chips (cascade); and, with no box of the page changed, by
                                         a hit area of the control's own (a ::before whose reach is worked out from
                                         the cascade): the year and region browse links, the view switch, the ski
                                         season (and other filter band) radios, the footer brand, the breadcrumbs
  --  card covers in <picture>           picture.cover-pic has no box; no rule asks for an <img> as a direct child
  --  role=radiogroup off the <nav>      section.js builds a <div> for the role; the generated <nav> carries none; a
                                         link that had the focus gets it back after the move
  --  forced colours                     the unselected units buttons of the header draw no bars
  --  a report without a phone bar       its footer keeps no room for one
  --  every page type                    one h1, the skip link first and pointing at #main, alt on every img, no
                                         interactive element inside another

The CSS side uses a small reader written for this file (parse_css, matches, computed): selector -> declarations with
the rules inside @media blocks, a selector matcher over the helpers.Doc tree, specificity and source order, and media
queries evaluated for a viewport and for scripting on or off. It reads the stylesheet build.css_bundle() publishes, in
bundle order. It is not a browser: it knows the selectors and media features these stylesheets use (ReaderTests pins
that it can read every selector in them), it does not inherit, and it reports declared values, not used ones.

The JavaScript side is a block-level reading, not an interpreter: a scanner that knows comments, strings and regular
expression literals finds the callback wired over the marker selector (and the one over [data-filter-nav]) by matching
braces, then looks at each addEventListener / setAttribute call in it and at the `if` conditions around that call.
The shapes it accepts are listed at marker_focus() and Script.guards(); a rewrite into another shape fails the test and
has to be read by a person, which is the intent.

The fixture site is synthetic (slugs start with PREFIX, sentences are made up), written to a temp dir with
tests/helpers.py and built with the page modules' own build() functions. core.ROOT, content.RENDERED and core's copy of
rendered/site/meta.json point into the temp dir while it is built, so nothing under content/ or rendered/ is read and
the region maps, glyphs and charts the pages inline are placeholders made here.
"""
import collections
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, Node, photo, LANDSCAPE, PORTRAIT, SQUARE  # noqa: E402

CSS_DIR = os.path.join(ROOT, 'assets', 'css')
JS_DIR = os.path.join(ROOT, 'assets', 'js')


def source(*parts):
    with open(os.path.join(ROOT, 'assets', *parts), encoding='utf-8') as fh:
        return fh.read()


# ---------------------------------------------------------------- a small CSS reader

class Unreadable(ValueError):
    """A selector this reader does not understand (it says so instead of guessing)."""


def _string_end(text, i):
    """The index after the string literal that opens at text[i]."""
    quote, j, n = text[i], i + 1, len(text)
    while j < n and text[j] != quote:
        j += 2 if text[j] == '\\' else 1
    return min(j + 1, n)


def _scan(text, i, stops):
    """The index of the first of `stops` at or after i outside strings, (...) and [...]; len(text) when there is none."""
    depth, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in '"\'':
            i = _string_end(text, i)
            continue
        if c in '([':
            depth += 1
        elif c in ')]':
            depth -= 1
        elif depth <= 0 and c in stops:
            return i
        i += 1
    return n


def split_top(text, sep):
    """text split at `sep` where it is not inside a string, (...) or [...]."""
    out, i = [], 0
    while True:
        j = _scan(text, i, sep)
        out.append(text[i:j])
        if j >= len(text):
            return out
        i = j + 1


def strip_css_comments(css):
    out, i, n = [], 0, len(css)
    while i < n:
        if css[i] in '"\'':
            j = _string_end(css, i)
            out.append(css[i:j])
            i = j
        elif css.startswith('/*', i):
            j = css.find('*/', i + 2)
            i = n if j < 0 else j + 2
            out.append(' ')
        else:
            out.append(css[i])
            i += 1
    return ''.join(out)


def _block_end(css, i):
    """The index of the '}' that closes the '{' at css[i]."""
    depth, n = 0, len(css)
    while i < n:
        c = css[i]
        if c in '"\'':
            i = _string_end(css, i)
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return n


def parse_decls(body):
    """'a: b; c: d !important' -> {'a': ('b', False), 'c': ('d', True)}; the last declaration of a property wins."""
    out = {}
    for part in split_top(body, ';'):
        name, colon, value = part.partition(':')
        name = name.strip()
        if not colon or not name or '{' in part:
            continue
        if not name.startswith('--'):
            name = name.lower()
        value = ' '.join(value.split())
        m = re.search(r'\s*!\s*important$', value, re.I)
        out[name] = (value[:m.start()], True) if m else (value, False)
    return out


# selector: the text as written; parts / spec: parse_selector() and specificity() of it (None when unreadable);
# decls: parse_decls(); media: the @media conditions around the rule, outermost first; order: its place in the sheet
Rule = collections.namedtuple('Rule', 'selector parts spec decls media order')


class Sheet(list):
    """The rules of a stylesheet in source order, with an index of which rules declare a property (built when first
    asked for: most cascade questions are about one property of one element)."""

    def declaring(self, prop):
        if not hasattr(self, '_by_prop'):
            self._by_prop = {}
            for r in self:
                for name in r.decls:
                    self._by_prop.setdefault(name, []).append(r)
        return self._by_prop.get(prop, ())


def parse_css(css):
    """(rules, unreadable): one Rule per selector of every style rule, in source order, the rules inside @media (and
    @supports) blocks included; @keyframes, @font-face and the like are not rules for elements and are left out.
    unreadable: the selectors parse_selector could not read (their rules are kept, and never match)."""
    css = strip_css_comments(css)
    rules, unreadable, count = Sheet(), [], [0]

    def walk(i, end, media):
        while i < end:
            j = _scan(css, i, '{;}')
            if j >= end:
                return
            if css[j] != '{':
                i = j + 1
                continue
            head, close = ' '.join(css[i:j].split()), min(_block_end(css, j), end)
            if head.startswith('@'):
                name = re.match(r'@([\w-]*)', head).group(1).lower()
                if name == 'media':
                    walk(j + 1, close, media + (head[len('@media'):].strip(),))
                elif name in ('supports', 'layer'):
                    walk(j + 1, close, media)
            else:
                decls = parse_decls(css[j + 1:close])
                count[0] += 1
                for sel in split_top(head, ','):
                    sel = sel.strip()
                    if not sel:
                        continue
                    try:
                        parts = parse_selector(sel)
                        spec = specificity(parts)
                    except Unreadable:
                        parts = spec = None
                        unreadable.append(sel)
                    rules.append(Rule(sel, parts, spec, decls, media, count[0]))
            i = close + 1

    walk(0, len(css), ())
    return rules, unreadable


# ---------------------------------------------------------------- media queries

# the viewport and the settings a rule is tried under; a feature that is not listed here matches nothing
ENV = {'type': 'screen', 'width': 390, 'height': 844, 'scripting': 'enabled', 'hover': 'hover', 'forced-colors': 'none',
       'prefers-reduced-motion': 'no-preference'}


def env(width=390, height=844, scripting='enabled'):
    return dict(ENV, width=width, height=height, scripting=scripting)


def px(value):
    m = re.match(r'^(-?\d+(?:\.\d+)?)px$', (value or '').strip())
    return float(m.group(1)) if m else None


def _feature(text, e):
    name, colon, value = text.partition(':')
    name, value = name.strip().lower(), value.strip().lower()
    m = re.match(r'^(min|max)-(width|height)$', name)
    if m:
        limit = px(value)
        if limit is None:
            return False
        return e[m.group(2)] >= limit if m.group(1) == 'min' else e[m.group(2)] <= limit
    if name in ('width', 'height'):
        return px(value) == e[name]
    if not colon:
        return e.get(name) not in (None, 'none')
    return e.get(name) == value


_MEDIA = {}


def media_matches(query, e):
    """True when the media query list holds for the environment e (see ENV)."""
    key = (query, tuple(sorted(e.items())))
    if key not in _MEDIA:
        _MEDIA[key] = _media_matches(query, e)
    return _MEDIA[key]


def _media_matches(query, e):
    for alt in split_top(query, ','):
        alt = alt.strip().lower()
        negate = alt.startswith('not ')
        alt = re.sub(r'^(not|only)\s+', '', alt)
        ok = True
        for term in re.split(r'\s+and\s+', alt):
            term = term.strip()
            ok = ok and (_feature(term[1:-1], e) if term.startswith('(') else term in ('all', e['type']))
        if ok != negate:
            return True
    return False


# ---------------------------------------------------------------- selectors

_IDENT = re.compile(r'-?[_a-zA-Z -￿][\w -￿-]*')
_ATTR = re.compile(r'''^\s*([\w-]+)\s*(?:([~|^$*]?=)\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|([^\s\]]+))\s*[iIsS]?\s*)?$''')
_NTH = re.compile(r'^(?:([+-]?\d*)n([+-]\d+)?|([+-]?\d+))$')
LEGACY_PSEUDO_ELEMENTS = frozenset('before after first-line first-letter'.split())
# pseudo-classes that are states of a page in use; in the page as it loads none of them holds
STATE_PSEUDO = frozenset('hover focus focus-visible focus-within active visited target'.split())
NTH_PSEUDO = frozenset('nth-child nth-last-child nth-of-type nth-last-of-type'.split())
LIST_PSEUDO = frozenset('is where not has'.split())
KNOWN_PSEUDO = STATE_PSEUDO | NTH_PSEUDO | LIST_PSEUDO | frozenset(
    'root empty checked disabled first-child last-child only-child first-of-type last-of-type only-of-type'.split())


def _paren_end(text, i):
    """The index of the ')' that closes the '(' at text[i]."""
    depth, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in '"\'':
            i = _string_end(text, i)
            continue
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise Unreadable(text)


def _nth(arg, sel):
    arg = arg.strip().lower().replace(' ', '')
    if arg in ('odd', 'even'):
        return (2, 1 if arg == 'odd' else 0)
    m = _NTH.match(arg)
    if not m:
        raise Unreadable(sel)
    if m.group(3) is not None:
        return (0, int(m.group(3)))
    a = m.group(1)
    return (1 if a in ('', '+') else -1 if a == '-' else int(a), int(m.group(2) or 0))


def parse_selector(sel):
    """One complex selector -> [(combinator, [simple, ...]), ...] left to right. combinator: None for the first compound
    (or the leading one of a relative selector inside :has), else ' ', '>', '+' or '~'. simple: ('tag', name),
    ('cls', name), ('id', name), ('attr', name, op, value), ('pe', name) for a pseudo-element, or ('pc', name, arg) for a
    pseudo-class, arg being the parsed selector list of :is / :where / :not / :has and (a, b) of :nth-*."""
    parts, cur, comb, i, n = [], None, None, 0, len(sel)
    while i < n:
        c = sel[i]
        if c.isspace():
            if cur is not None:
                cur, comb = None, ' '
            i += 1
            continue
        if c in '>+~':
            cur, comb = None, c
            i += 1
            continue
        if cur is None:
            cur = []
            parts.append((comb, cur))
            comb = None
        if c == '*':
            cur.append(('tag', '*'))
            i += 1
        elif c in '.#':
            m = _IDENT.match(sel, i + 1)
            if not m:
                raise Unreadable(sel)
            cur.append(('cls' if c == '.' else 'id', m.group(0)))
            i = m.end()
        elif c == '[':
            j = i + 1
            while j < n and sel[j] != ']':
                j = _string_end(sel, j) if sel[j] in '"\'' else j + 1
            m = _ATTR.match(sel[i + 1:j])
            if j >= n or not m:
                raise Unreadable(sel)
            value = next((g for g in m.groups()[2:] if g is not None), None)
            cur.append(('attr', m.group(1).lower(), m.group(2), value))
            i = j + 1
        elif c == ':':
            element = sel.startswith('::', i)
            m = _IDENT.match(sel, i + (2 if element else 1))
            if not m:
                raise Unreadable(sel)
            name, i, arg = m.group(0).lower(), m.end(), None
            if i < n and sel[i] == '(':
                j = _paren_end(sel, i)
                arg, i = sel[i + 1:j], j + 1
            if element or name in LEGACY_PSEUDO_ELEMENTS:
                cur.append(('pe', name))
            elif name not in KNOWN_PSEUDO:
                raise Unreadable('%s (the pseudo-class :%s)' % (sel, name))
            elif name in LIST_PSEUDO:
                cur.append(('pc', name, [parse_selector(x.strip()) for x in split_top(arg or '', ',')]))
            elif name in NTH_PSEUDO:
                cur.append(('pc', name, _nth(arg or '', sel)))
            else:
                cur.append(('pc', name, None))
        else:
            m = _IDENT.match(sel, i)
            if not m:
                raise Unreadable(sel)
            cur.append(('tag', m.group(0).lower()))
            i = m.end()
    if not parts:
        raise Unreadable(sel)
    return parts


def specificity(parts):
    a = b = c = 0
    for _comb, simples in parts:
        for s in simples:
            if s[0] == 'id':
                a += 1
            elif s[0] in ('cls', 'attr'):
                b += 1
            elif s[0] == 'pe' or (s[0] == 'tag' and s[1] != '*'):
                c += 1
            elif s[0] == 'pc' and s[1] in ('is', 'not', 'has'):
                x, y, z = max(specificity(alt) for alt in s[2])
                a, b, c = a + x, b + y, c + z
            elif s[0] == 'pc' and s[1] != 'where':
                b += 1
    return (a, b, c)


def _elements(node):
    return [x for x in node.children if isinstance(x, Node)]


def _place(node, of_type=False, from_end=False):
    """(1-based position among its sibling elements, how many there are)."""
    sibs = _elements(node.parent) if node.parent is not None else [node]
    if of_type:
        sibs = [s for s in sibs if s.tag == node.tag]
    if from_end:
        sibs = sibs[::-1]
    return next(k for k, s in enumerate(sibs, 1) if s is node), len(sibs)


def _attr_ok(have, op, value):
    if op is None:
        return True
    if op == '=':
        return have == value
    if op == '~=':
        return value in have.split()
    if op == '|=':
        return have == value or have.startswith(value + '-')
    if not value:
        return False
    return {'^=': have.startswith, '$=': have.endswith, '*=': have.__contains__}[op](value)


def _simple(node, s):
    kind = s[0]
    if kind == 'tag':
        return s[1] == '*' or node.tag == s[1]
    if kind == 'cls':
        return s[1] in node.classes
    if kind == 'id':
        return node.attrs.get('id') == s[1]
    if kind == 'attr':
        return s[1] in node.attrs and _attr_ok(node.attrs[s[1]], s[2], s[3])
    if kind == 'pe':
        return False                                  # the rule styles a pseudo-element, not the element
    name, arg = s[1], s[2]
    if name in ('is', 'where'):
        return any(matches(node, alt) for alt in arg)
    if name == 'not':
        return not any(matches(node, alt) for alt in arg)
    if name == 'has':
        return any(_has(node, alt) for alt in arg)
    if name in STATE_PSEUDO:
        return False
    if name == 'root':
        return node.tag == 'html'
    if name == 'empty':
        return not node.children
    if name in ('checked', 'disabled'):
        return name in node.attrs
    if name in NTH_PSEUDO:
        a, b = arg
        k = _place(node, 'of-type' in name, 'last' in name)[0] - b
        return k == 0 if a == 0 else (k % a == 0 and k // a >= 0)
    of_type = name.endswith('of-type')
    if name.startswith('first'):
        return _place(node, of_type)[0] == 1
    if name.startswith('last'):
        return _place(node, of_type, True)[0] == 1
    return _place(node, of_type)[1] == 1              # only-child, only-of-type


def _step(node, parts, i, test):
    """The elements the combinator in front of compound i leads back to from node, tried with test(element, i - 1)."""
    comb = parts[i][0]
    if comb in (' ', '>'):
        a = node.parent
        while a is not None and a.tag != '#root':
            if test(a, i - 1):
                return True
            if comb == '>':
                return False
            a = a.parent
        return False
    sibs = _elements(node.parent) if node.parent is not None else [node]
    before = sibs[:next(k for k, s in enumerate(sibs) if s is node)]
    if comb == '+':
        return bool(before) and test(before[-1], i - 1)
    return any(test(x, i - 1) for x in before)


def matches(node, parts, i=None):
    """True when the element (a helpers.Node inside a helpers.Doc tree) matches the parsed complex selector."""
    i = len(parts) - 1 if i is None else i
    if not all(_simple(node, s) for s in parts[i][1]):
        return False
    return i == 0 or _step(node, parts, i, lambda a, k: matches(a, parts, k))


def _has(scope, parts):
    """:has(parts) on scope: some element reached from scope by the relative selector."""
    lead = parts[0][0] or ' '

    def anchored(node, i):
        if not all(_simple(node, s) for s in parts[i][1]):
            return False
        if i > 0:
            return _step(node, parts, i, anchored)
        if lead == '>':
            return node.parent is scope
        if lead == ' ':
            a = node.parent
            while a is not None and a is not scope:
                a = a.parent
            return a is scope
        sibs = _elements(scope.parent) if scope.parent is not None else []
        after = sibs[next((k for k, s in enumerate(sibs) if s is scope), len(sibs)) + 1:]
        return any(node is s for s in (after[:1] if lead == '+' else after))

    pool = scope.walk() if lead in (' ', '>') else (x for s in _elements(scope.parent) for x in [s] + list(s.walk()))
    return any(anchored(x, len(parts) - 1) for x in pool)


def winner(node, prop, rules, e):
    """The rule whose declaration of `prop` wins the cascade for the element in environment e, or None."""
    best = None
    for r in (rules.declaring(prop) if isinstance(rules, Sheet) else rules):
        if prop not in r.decls or r.parts is None:
            continue
        if not all(media_matches(q, e) for q in r.media) or not matches(node, r.parts):
            continue
        key = (r.decls[prop][1], r.spec, r.order)
        if best is None or key >= best[0]:
            best = (key, r)
    return best[1] if best else None


def computed(node, prop, rules, e):
    """The declared value of `prop` that wins the cascade for the element (importance, then specificity, then source
    order), None when no matching rule declares it. Declared, not used: 'inline-flex' stays 'inline-flex', and nothing
    is inherited."""
    r = winner(node, prop, rules, e)
    return r.decls[prop][0] if r else None


def why(node, prop, rules, e):
    """'display: flex from ".nav a"' for a failure message."""
    r = winner(node, prop, rules, e)
    if r is None:
        return '%s is not declared for %r' % (prop, node)
    return '%s: %s from "%s"%s' % (prop, r.decls[prop][0], r.selector, (' in @media %s' % ' and '.join(r.media)) if r.media else '')


def hidden_by(node, rules, e):
    """The outermost of the element and its ancestors that has display: none (or the hidden attribute and no display of
    its own): what takes the element off the page. None when it is displayed."""
    chain = []
    while node is not None and node.tag != '#root':
        chain.append(node)
        node = node.parent
    for x in reversed(chain):
        value = computed(x, 'display', rules, e)
        if value == 'none' or (value is None and 'hidden' in x):
            return x
    return None


def displayed(node, rules, e):
    """False when the element or one of its ancestors has display: none: it is not rendered, cannot be focused and is
    not read out."""
    return hidden_by(node, rules, e) is None


def _edges(value):
    """The px of a border / padding shorthand as (top, bottom); None when it is not plain px."""
    vals = [px(v) if v != '0' else 0.0 for v in (value or '').split()]
    if not vals or any(v is None for v in vals):
        return None
    return (vals[0], vals[2] if len(vals) > 2 else vals[0])


def min_block(node, rules, e):
    """The least height in px the stylesheet promises the element: its min-height or height when one is a px length;
    for height: 100% the parent's stated height less the parent's own border and padding. None when it promises none."""
    sizes = [px(computed(node, p, rules, e)) for p in ('min-height', 'height')]
    sizes = [v for v in sizes if v is not None]
    if sizes:
        return max(sizes)
    parent = node.parent
    if (computed(node, 'height', rules, e) or '') != '100%' or parent is None:
        return None
    outer = px(computed(parent, 'height', rules, e))
    if outer is None or computed(parent, 'box-sizing', rules, e) != 'border-box':
        return outer
    border = re.match(r'^(\d+(?:\.\d+)?)px\b', computed(parent, 'border', rules, e) or '0px')
    pad = _edges(computed(parent, 'padding', rules, e) or '0px')
    if border is None or pad is None:
        return None
    return outer - 2 * float(border.group(1)) - sum(pad)


def min_inline(node, rules, e):
    sizes = [px(computed(node, p, rules, e)) for p in ('min-width', 'width')]
    sizes = [v for v in sizes if v is not None]
    return max(sizes) if sizes else None


def _key(rule, prop):
    """Where a rule's declaration of `prop` stands in the cascade: importance, then specificity, then source order."""
    return (rule.decls[prop][1], rule.spec, rule.order)


def computed_pseudo(node, pseudo, prop, rules, e):
    """The declared value of `prop` that wins the cascade for the element's pseudo-element (`before`, `after`): among
    the rules whose subject carries that pseudo-element and, without it, matches the element. None when none does."""
    best = None
    for r in (rules.declaring(prop) if isinstance(rules, Sheet) else rules):
        if prop not in r.decls or r.parts is None or ('pe', pseudo) not in r.parts[-1][1]:
            continue
        own = r.parts[:-1] + [(r.parts[-1][0], [x for x in r.parts[-1][1] if x[0] != 'pe'])]
        if not all(media_matches(q, e) for q in r.media) or not matches(node, own):
            continue
        if best is None or _key(r, prop) >= _key(best, prop):
            best = r
    return best.decls[prop][0] if best else None


_GROW = re.compile(r'^min\(\s*0(?:px)?\s*,\s*(?:\(\s*100%\s*-\s*(\d+(?:\.\d+)?)px\s*\)\s*/\s*2|100%\s*-\s*(\d+(?:\.\d+)?)px)\s*\)$')


def side(value, base=None):
    """One side of an inset (or of a margin, a padding) in px; a negative inset reaches outside the box. A px length or
    0; or, for a box `base` px across, one of the two ways these stylesheets grow a hit area to a least size:
    `min(0px, (100% - Npx) / 2)` (half of what the box lacks of N, on this side) and `min(0px, 100% - Npx)` (all of it).
    None for anything else, and for those two forms when no base is given."""
    value = (value or '').strip()
    if value == '0':
        return 0.0
    if px(value) is not None:
        return px(value)
    m = _GROW.match(value)
    if m is None or base is None:
        return None
    if m.group(1) is not None:
        return min(0.0, (base - float(m.group(1))) / 2)
    return min(0.0, base - float(m.group(2)))


def sides(value, base=None):
    """(top, right, bottom, left) in px of a one to four value shorthand (inset, margin, padding), each read by side();
    None when one of them cannot be read."""
    vals = [side(v, base) for v in split_top(value or '', ' ') if v.strip()]
    if not 1 <= len(vals) <= 4 or any(v is None for v in vals):
        return None
    top = vals[0]
    right = vals[1] if len(vals) > 1 else top
    return (top, right, vals[2] if len(vals) > 2 else top, vals[3] if len(vals) > 3 else right)


def line_height(node, rules, e):
    """The px line height the stylesheet gives the element itself: its `line-height`, or the one in its `font`
    shorthand ('400 12px/16px var(--mono)'), whichever of the two declarations wins the cascade. None when the winner
    is not a px length (nothing is inherited: ask the element the rule is written for)."""
    lh, font = winner(node, 'line-height', rules, e), winner(node, 'font', rules, e)
    if lh is not None and (font is None or _key(lh, 'line-height') > _key(font, 'font')):
        return px(lh.decls['line-height'][0])
    m = re.search(r'/\s*(\d+(?:\.\d+)?)px(?![\w.])', font.decls['font'][0]) if font is not None else None
    return float(m.group(1)) if m else None


# ---------------------------------------------------------------- reading a script

_JS_KEYWORDS = frozenset('return typeof case in of delete void throw new else do instanceof'.split())


def js_mask(src):
    """One letter per character of a script: 'c' code, 's' inside a string or a regular expression literal (its quotes
    or slashes included), 'x' inside a comment. A '/' opens a regular expression when what stands before it cannot end
    an expression (an operator, an opening bracket, a keyword such as return)."""
    out, tail, i, n = [], '', 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith('//', i):
            j = src.find('\n', i)
            j = n if j < 0 else j
            kind = 'x'
        elif src.startswith('/*', i):
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            kind = 'x'
        elif c in '"\'`':
            j, kind = _string_end(src, i), 's'
        elif c == '/' and _regex_may_start(tail):
            j, in_class = i + 1, False
            while j < n and src[j] != '\n' and (src[j] != '/' or in_class):
                if src[j] == '\\':
                    j += 1
                elif src[j] in '[]':
                    in_class = src[j] == '['
                j += 1
            j = min(j + 1, n)
            while j < n and src[j].isalpha():
                j += 1
            kind = 's'
        else:
            out.append('c')
            tail = (tail + c)[-24:]
            i += 1
            continue
        out.append(kind * (j - i))
        if kind == 's':
            tail += '0'                                   # a literal ends an expression, like a number
        i = j
    return ''.join(out)


def _regex_may_start(tail):
    m = re.search(r'([A-Za-z_$][\w$]*|[^\s\w$])\s*$', tail)
    if not m:
        return not tail.strip()
    tok = m.group(1)
    if tok in _JS_KEYWORDS:
        return True
    return not (tok[0].isalnum() or tok[0] in '_$)]}')


class Script:
    """A script's text with its comments blanked (strings kept), and brace / parenthesis matching that ignores what is
    inside strings, regular expressions and comments."""

    def __init__(self, src):
        self.mask = js_mask(src)
        self.text = ''.join(ch if m != 'x' or ch == '\n' else ' ' for ch, m in zip(src, self.mask))

    def code(self, i):
        return self.mask[i] == 'c'

    def close(self, i):
        """The index of the bracket that closes the opening bracket at i."""
        pairs = {'{': '}', '(': ')', '[': ']'}
        want, depth = pairs[self.text[i]], 0
        for j in range(i, len(self.text)):
            if self.code(j):
                if self.text[j] == self.text[i]:
                    depth += 1
                elif self.text[j] == want:
                    depth -= 1
                    if depth == 0:
                        return j
        raise ValueError('unbalanced %s at %d' % (self.text[i], i))

    def open(self, j):
        """The index of the bracket that the closing bracket at j closes."""
        pairs = {'}': '{', ')': '(', ']': '['}
        want, depth = pairs[self.text[j]], 0
        for i in range(j, -1, -1):
            if self.code(i):
                if self.text[i] == self.text[j]:
                    depth += 1
                elif self.text[i] == want:
                    depth -= 1
                    if depth == 0:
                        return i
        raise ValueError('unbalanced %s at %d' % (self.text[j], j))

    def before(self, i):
        """The index of the last character before i that is not white space (-1 when there is none)."""
        i -= 1
        while i >= 0 and self.text[i].isspace():
            i -= 1
        return i

    def each_callbacks(self, selector_test):
        """[(selector string, parameter name, body start, body end)] of every
        `querySelectorAll('<selector>').forEach(function (<parameter>) { <body> })` whose selector string passes the
        test; an arrow function with one parameter and a braced body is read as well."""
        out = []
        pattern = re.compile(r'''querySelectorAll\(\s*(['"])((?:(?!\1).)*)\1\s*\)\s*\.forEach\(\s*'''
                             r'''(?:function\s*\(\s*([\w$]+)[^)]*\)|\(?\s*([\w$]+)\s*\)?\s*=>)\s*\{''')
        for m in pattern.finditer(self.text):
            if self.code(m.start()) and selector_test(m.group(2)):
                brace = m.end() - 1
                out.append((m.group(2), m.group(3) or m.group(4), brace + 1, self.close(brace)))
        return out

    def guards(self, pos, start):
        """The `if` conditions that have to hold for the statement at `pos` to run, looking outwards as far as the block
        that opens just before `start`: ('if', condition) for an enclosing `if (...) {` block or an `if (...)` in front
        of the statement itself, ('else', condition) for the else block of an `if (condition)`. Loops, functions and
        other blocks add nothing."""
        out = []
        # an `if (...)` in front of the statement, without braces
        i, depth = pos - 1, 0
        while i >= start:
            if self.code(i):
                ch = self.text[i]
                if ch in ')]':
                    depth += 1
                elif ch in '([':
                    depth -= 1
                elif depth == 0 and ch in ';{}':
                    break
            i -= 1
        m = re.match(r'^\s*if\s*\(', self.text[i + 1:pos])
        if m:
            opening = i + 1 + m.end() - 1
            closing = self.close(opening)
            if not self.text[closing + 1:pos].strip():
                out.append(('if', self.text[opening + 1:closing]))
        # the blocks around it
        stack = []
        for j in range(start, pos):
            if self.code(j):
                if self.text[j] == '{':
                    stack.append(j)
                elif self.text[j] == '}' and stack:
                    stack.pop()
        for brace in stack:
            k = self.before(brace)
            if k >= 0 and self.text[k] == ')' and self.code(k):
                opening = self.open(k)
                if re.search(r'\bif\s*$', self.text[:opening]):
                    out.append(('if', self.text[opening + 1:k]))
            elif re.search(r'\belse\s*$', self.text[:brace]):
                k = self.before(brace - len(re.search(r'else\s*$', self.text[:brace]).group(0)))
                if k >= 0 and self.text[k] == '}':
                    k = self.before(self.open(k))
                    if k >= 0 and self.text[k] == ')':
                        opening = self.open(k)
                        if re.search(r'\bif\s*$', self.text[:opening]):
                            out.append(('else', self.text[opening + 1:k]))
        return out

    def listeners(self, target, start, end):
        """[(event name, position)] of every `<target>.addEventListener('<event>', ...)` between start and end."""
        pattern = re.compile(r'''(?<![\w$.])%s\.addEventListener\(\s*(['"])([\w-]+)\1''' % re.escape(target))
        return [(m.group(2), m.start()) for m in pattern.finditer(self.text, start, end) if self.code(m.start())]


def conjuncts(cond):
    """The terms of a condition that is one `a && b && c` chain, split at each `&&` that is outside every bracket and
    string. None when an `||` stands outside every bracket: the condition is then not a plain chain, and no one term
    of it has to hold."""
    out, depth, i, start, n = [], 0, 0, 0, len(cond)
    while i < n:
        c = cond[i]
        if c in '"\'':
            i = _string_end(cond, i)
            continue
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif depth == 0 and cond.startswith('||', i):
            return None
        elif depth == 0 and cond.startswith('&&', i):
            out.append(cond[start:i].strip())
            i = start = i + 2
            continue
        i += 1
    out.append(cond[start:].strip())
    return out


FOCUS_EVENTS = ('focus', 'blur', 'focusin', 'focusout')


def _is_cluster(cond, el):
    """The condition holds only for a cluster marker: an un-negated <el>.classList.contains('mk-cluster'), no `||`."""
    return '||' not in cond and re.search(r'''(?<![!\w$.])%s\.classList\.contains\(\s*['"]mk-cluster['"]\s*\)''' % re.escape(el), cond) is not None


def _is_not_cluster(cond, el):
    """The condition holds for no cluster marker: !<el>.classList.contains('mk-cluster'), or a positive test for a pin
    (<el>.classList.contains('mk-pin'), <el>.matches('.mk-pin...')), and no `||`."""
    e = re.escape(el)
    return '||' not in cond and (
        re.search(r'''!\s*%s\.classList\.contains\(\s*['"]mk-cluster['"]\s*\)''' % e, cond) is not None
        or re.search(r'''(?<![!\w$.])%s\.classList\.contains\(\s*['"]mk-pin['"]\s*\)''' % e, cond) is not None
        or re.search(r'''(?<![!\w$.])%s\.matches\(\s*['"]\.mk-pin\b''' % e, cond) is not None)


def marker_focus(src):
    """Who gets focus listeners among the map markers of a script: {'pin': set of events, 'cluster': set of events}.

    It reads every `querySelectorAll('<selector naming .mk-pin or .mk-cluster>').forEach(function (el) { ... })` and, in
    it, every `el.addEventListener('focus' | 'blur' | 'focusin' | 'focusout', ...)`. A listener reaches the pins when
    the selector names .mk-pin and no condition around the call holds for clusters only; it reaches the clusters when
    the selector names .mk-cluster and no condition around the call rules them out (see _is_cluster / _is_not_cluster;
    the else block of a clusters-only `if` rules them out as well)."""
    js = Script(src)
    got = {'pin': set(), 'cluster': set()}
    for selector, el, start, end in js.each_callbacks(lambda s: '.mk-pin' in s or '.mk-cluster' in s):
        for event, pos in js.listeners(el, start, end):
            if event not in FOCUS_EVENTS:
                continue
            conds = js.guards(pos, start)
            only_clusters = any(k == 'if' and _is_cluster(c, el) for k, c in conds)
            no_clusters = any((k == 'if' and _is_not_cluster(c, el)) or (k == 'else' and _is_cluster(c, el)) for k, c in conds)
            if '.mk-pin' in selector and not only_clusters:
                got['pin'].add(event)
            if '.mk-cluster' in selector and not no_clusters:
                got['cluster'].add(event)
    return got


def radiogroup_setters(src):
    """Every place a script gives an element role="radiogroup": [(variable, loop parameter or None, how the variable was
    made or None, True when the loop's element is replaced by the variable before the role is set)]. Read inside the
    `querySelectorAll('...[data-filter-nav]...').forEach(function (param) { ... })` callback when the call is in one."""
    js = Script(src)
    loops = js.each_callbacks(lambda s: 'data-filter-nav' in s)
    out = []
    for m in re.finditer(r'''([\w$.]+)\.setAttribute\(\s*(['"])role\2\s*,\s*(['"])radiogroup\3\s*\)''', js.text):
        if not js.code(m.start()):
            continue
        var = m.group(1)
        loop = next((x for x in loops if x[2] <= m.start() < x[3]), None)
        param = made = None
        replaced = False
        if loop:
            param, body = loop[1], js.text[loop[2]:m.start()]
            mk = re.search(r'''(?:var|let|const)\s+%s\s*=\s*document\.createElement\(\s*(['"])([\w-]+)\1\s*\)''' % re.escape(var), body)
            made = mk.group(2).lower() if mk else None
            replaced = re.search(r'replaceChild\(\s*%s\s*,\s*%s\s*\)|(?<![\w$.])%s\.replaceWith\(\s*%s\s*\)'
                                 % (re.escape(var), re.escape(param), re.escape(param), re.escape(var)), body) is not None
        out.append((var, param, made, replaced))
    return out


# ---------------------------------------------------------------- the reader itself

SHEET = '''
/* a comment with a brace { and a quote ' in it */
.a, .b > .c { display: none; color: red !important; }
.x[data-k="1,2}"] { content: "}"; height: 44px; }
@media (min-width: 760px) { .a { display: flex; } @media (scripting: none) { .a { display: grid; } } }
@keyframes spin { from { opacity: 0; } to { opacity: 1; } }
@supports (display: grid) { .g { display: grid; } }
ul li:nth-child(2n+1)::before, a:hover { color: blue; }
'''


class ReaderTests(unittest.TestCase):
    """The reader is only worth trusting on the stylesheets and scripts it is given if it reads them as a browser does."""

    def doc(self, html_):
        return Doc(html_)

    def test_rules_are_read_with_their_media_and_in_order(self):
        rules, unreadable = parse_css(SHEET)
        self.assertEqual(unreadable, [])
        got = [(r.selector, r.media, r.order) for r in rules]
        self.assertEqual(got, [
            ('.a', (), 1), ('.b > .c', (), 1), ('.x[data-k="1,2}"]', (), 2),
            ('.a', ('(min-width: 760px)',), 3), ('.a', ('(min-width: 760px)', '(scripting: none)'), 4),
            ('.g', (), 5), ('ul li:nth-child(2n+1)::before', (), 6), ('a:hover', (), 6)])
        self.assertEqual(rules[0].decls, {'display': ('none', False), 'color': ('red', True)})
        self.assertEqual(rules[2].decls, {'content': ('"}"', False), 'height': ('44px', False)})
        self.assertNotIn('spin', ' '.join(r.selector for r in rules))       # @keyframes steps are not rules for elements

    def test_an_unknown_pseudo_class_is_reported_not_guessed(self):
        rules, unreadable = parse_css('.a:future-thing { display: none; } .b { display: block; }')
        self.assertEqual(len(unreadable), 1)
        self.assertIn(':future-thing', unreadable[0])
        d = self.doc('<p class="a b">x</p>')
        self.assertEqual(computed(d.find('p'), 'display', rules, env()), 'block')      # the unread rule never matches

    def test_specificity(self):
        for sel, want in (('.a', (0, 1, 0)), ('a', (0, 0, 1)), ('.nav a', (0, 1, 1)), ('#x .y z', (1, 1, 1)), ('*', (0, 0, 0)),
                          ('a[href]', (0, 1, 1)), ('a:hover', (0, 1, 1)), ('li::before', (0, 0, 2)), (':where(.a, #b) c', (0, 0, 1)),
                          (':is(.a, #b) c', (1, 0, 1)), ('.a:not(.b)', (0, 2, 0)), ('.a:nth-child(2)', (0, 2, 0)),
                          ('.f-brand a.brand-n', (0, 2, 1)), ('body.p-series', (0, 1, 1)), ('.x:has(> .y)', (0, 2, 0))):
            with self.subTest(selector=sel):
                self.assertEqual(specificity(parse_selector(sel)), want)

    def test_selectors_match_as_in_a_browser(self):
        d = self.doc('<html><body class="p"><nav class="nav" aria-label="Main"><div class="l"><a class="s" href="#">One</a>'
                     '<a href="#" aria-current="page">Two</a><span></span><b> </b></div></nav>'
                     '<ul><li>1</li><li class="on">2</li><li>3</li></ul><input type="checkbox" checked></body></html>')
        nav, first, second = d.find('nav'), d.find_all('a')[0], d.find_all('a')[1]
        li = d.find_all('li')
        cases = [
            (nav, '.nav', True), (nav, 'nav.nav', True), (nav, 'div.nav', False), (first, '.nav a', True), (first, '.nav > a', False),
            (first, '.nav > .l > a', True), (first, 'body.p a.s', True), (first, 'body.q a', False), (second, '.s + a', True),
            (first, '.s + a', False), (second, 'a ~ a', True), (second, '.nav a[aria-current]', True),
            (second, 'a[aria-current="page"]', True), (second, 'a[aria-current=true]', False), (first, 'a[href^="#"]', True),
            (first, ':is(a, button)', True), (first, '.nav :is(button, input)', False), (first, 'a:not(.s)', False),
            (second, 'a:not(.s)', True), (first, 'a:hover', False), (first, 'a:focus-visible', False), (first, 'a::after', False),
            (first, 'a:before', False), (first, '*', True), (first, ':where(.nav) a', True), (li[0], 'li:first-child', True),
            (li[2], 'li:last-child', True), (li[1], 'li:nth-child(2)', True), (li[1], 'li:nth-child(odd)', False),
            (li[2], 'li:nth-child(2n+1)', True), (li[2], 'li:nth-child(-n+2)', False), (li[1], 'li:nth-child(-n+2)', True),
            (li[1], '.on:not(:first-child)', True), (nav, ':has(> .l)', True), (nav, ':has(> a)', False), (nav, ':has(a.s)', True),
            (d.find('body'), 'body:has(.on)', True), (d.find('body'), 'body:not(:has(.off))', True), (d.find('html'), ':root', True),
            (d.find('span'), 'span:empty', True), (d.find('b'), 'b:empty', False), (d.find('input'), 'input:checked', True),
            (d.find('ul'), 'nav + ul', True), (li[0], 'nav + ul > li', True), (li[0], 'html > body > ul > li:only-child', False),
            (nav, '[aria-label="Main"]', True), (nav, "[aria-label='Main']", True), (nav, '[aria-label~="Main"]', True),
        ]
        for node, sel, want in cases:
            with self.subTest(selector=sel, node=repr(node)):
                self.assertEqual(matches(node, parse_selector(sel)), want)

    def test_media_queries(self):
        phone, desk, off = env(390, 844), env(1300, 900), env(390, 844, 'none')
        for query, e, want in (('(min-width: 760px)', phone, False), ('(min-width: 760px)', desk, True),
                               ('(max-width: 759.98px)', phone, True), ('(min-width: 560px) and (max-width: 1199.98px)', desk, False),
                               ('(max-width: 559.98px), (min-width: 760px) and (max-width: 1399.98px)', desk, True),
                               ('(max-height: 480px)', phone, False), ('(max-height: 480px)', env(844, 390), True),
                               ('(scripting: none)', phone, False), ('(scripting: none)', off, True), ('print', phone, False),
                               ('screen and (min-width: 300px)', phone, True), ('(forced-colors: active)', phone, False),
                               ('(prefers-reduced-motion: reduce)', phone, False), ('(hover: none)', phone, False),
                               ('(some-new-feature: yes)', phone, False), ('not print', phone, True)):
            with self.subTest(query=query, width=e['width'], height=e['height'], scripting=e['scripting']):
                self.assertEqual(media_matches(query, e), want)

    def test_the_cascade_is_importance_then_specificity_then_order(self):
        d = self.doc('<nav class="nav"><a class="s" href="#">One</a></nav>')
        a = d.find('a')

        def shown(css, e=None):
            return computed(a, 'display', parse_css(css)[0], e or env())

        self.assertEqual(shown('.s { display: none; } .s { display: flex; }'), 'flex')              # the later rule
        self.assertEqual(shown('.nav a { display: flex; } .s { display: none; }'), 'flex')          # the more specific rule
        self.assertEqual(shown('.nav a { display: flex; } .s { display: none !important; }'), 'none')
        self.assertEqual(shown('.s { display: none; }'), 'none')
        self.assertIsNone(shown('.t { display: none; }'))
        # a rule in a media block weighs no more than one outside it: the block has to come later, or be more specific
        hide = '@media (scripting: none) { .s { display: none; } }'
        self.assertEqual(shown(hide + ' .s { display: inline-flex; }', env(scripting='none')), 'inline-flex')
        self.assertEqual(shown('.s { display: inline-flex; } ' + hide, env(scripting='none')), 'none')
        self.assertEqual(shown('.s { display: inline-flex; } ' + hide, env()), 'inline-flex')
        self.assertEqual(shown('.nav a { display: flex; } ' + hide, env(scripting='none')), 'flex')
        self.assertIn('display: flex from ".nav a"', why(a, 'display', parse_css('.nav a { display: flex; } ' + hide)[0], env()))

    def test_displayed_looks_at_the_element_and_at_everything_around_it(self):
        d = self.doc('<div class="row"><a class="s" href="#">One</a></div><div class="menu" hidden><a class="m" href="#">Two</a></div>')
        s, m = d.find('a', cls='s'), d.find('a', cls='m')
        rules = parse_css('.s { display: flex; } @media (scripting: none) { .row { display: none; } } .menu.is-open { display: block; }')[0]
        self.assertTrue(displayed(s, rules, env()))
        self.assertFalse(displayed(s, rules, env(scripting='none')))          # its row is gone, whatever its own display says
        self.assertIs(hidden_by(s, rules, env(scripting='none')), d.find('div', cls='row'))
        self.assertIsNone(hidden_by(s, rules, env()))
        self.assertFalse(displayed(m, rules, env()))                           # the hidden attribute, with no rule against it
        self.assertTrue(displayed(m, parse_css('.menu { display: grid; }')[0], env()))

    def test_least_sizes(self):
        d = self.doc('<div class="v"><button class="k">A</button></div><a class="c">B</a><a class="m">C</a>')
        rules = parse_css('*, *::before { box-sizing: border-box; } .v { height: 46px; border: 1px solid red; } .k { height: 100%; }'
                          ' .c { height: 44px; min-width: 44px; } .m { min-height: 42px; }'
                          ' @media (min-width: 760px) { .c { height: 40px; } .v { padding: 4px 0; } }')[0]
        k, c, m = d.find('button'), d.find('a', cls='c'), d.find('a', cls='m')
        self.assertEqual(min_block(k, rules, env()), 44.0)            # 46 px less the 1 px border above and below
        self.assertEqual(min_block(k, rules, env(800)), 36.0)         # and less the padding a wider viewport adds
        self.assertEqual((min_block(c, rules, env()), min_inline(c, rules, env())), (44.0, 44.0))
        self.assertEqual(min_block(c, rules, env(800)), 40.0)
        self.assertEqual(min_block(m, rules, env()), 42.0)
        self.assertIsNone(min_inline(m, rules, env()))

    def test_pseudo_elements_sides_and_line_heights(self):
        d = self.doc('<nav class="c t"><a href="#">One</a><b>x</b></nav>')
        nav, a, b = d.find('nav'), d.find('a'), d.find('b')
        rules = parse_css('.c { font: 400 12px/16px var(--mono); } .t { font: 400 12px/20px x; } .c a::before { content: ""; inset: -12px -4px; }'
                          ' .c a:before { inset: -14px -4px -6px; } .c b::before { inset: -1px; } a::after { inset: 0 1px 2px 3px; }'
                          ' @media (min-width: 760px) { .c { font-size: 13px; line-height: 18px; } .c a::before { inset: -9px; } }')[0]
        self.assertEqual(computed_pseudo(a, 'before', 'inset', rules, env()), '-14px -4px -6px')     # the later of two equal rules
        self.assertEqual(computed_pseudo(a, 'before', 'inset', rules, env(800)), '-9px')
        self.assertEqual(computed_pseudo(a, 'after', 'inset', rules, env()), '0 1px 2px 3px')
        self.assertEqual(computed_pseudo(b, 'before', 'inset', rules, env()), '-1px')
        self.assertIsNone(computed_pseudo(nav, 'before', 'inset', rules, env()))
        self.assertIsNone(computed(a, 'inset', rules, env()))                 # a pseudo-element's rule is not the element's
        for value, want in (('-14px -4px -6px', (-14.0, -4.0, -6.0, -4.0)), ('-9px', (-9.0,) * 4), ('0 1px 2px 3px', (0.0, 1.0, 2.0, 3.0)),
                            ('-12px -4px', (-12.0, -4.0, -12.0, -4.0)), ('1em', None), ('', None), ('1px 2px 3px 4px 5px', None)):
            with self.subTest(value=value):
                self.assertEqual(sides(value), want)
        self.assertEqual(line_height(nav, rules, env()), 20.0)        # .t is the later font shorthand
        self.assertEqual(line_height(nav, rules, env(800)), 18.0)     # the longhand in the media block comes after both
        self.assertIsNone(line_height(a, rules, env()))               # nothing is inherited
        # a font shorthand after a line-height resets it
        self.assertEqual(line_height(nav, parse_css('.c { line-height: 18px; } .c { font: 400 12px/16px x; }')[0], env()), 16.0)

    def test_sides_that_grow_a_box_to_a_least_size(self):
        half, whole = 'min(0px, (100% - 44px) / 2)', 'min(0px, 100% - 44px)'
        for base, want_half, want_whole in ((32.0, -6.0, -12.0), (37.5, -3.25, -6.5), (44.0, 0.0, 0.0), (120.0, 0.0, 0.0)):
            with self.subTest(base=base):
                self.assertEqual(side(half, base), want_half)
                self.assertEqual(side(whole, base), want_whole)
                # the box and what is added on both sides, or on one: never under 44, never more than the box itself
                self.assertEqual(base - 2 * side(half, base), max(base, 44.0))
                self.assertEqual(base - side(whole, base), max(base, 44.0))
        self.assertEqual(sides('0 ' + half, 32.0), (0.0, -6.0, 0.0, -6.0))
        self.assertEqual(sides('-1px 0 -1px ' + whole, 37.5), (-1.0, 0.0, -1.0, -6.5))
        self.assertEqual(sides('-1px 0'), (-1.0, 0.0, -1.0, 0.0))
        self.assertIsNone(side(half))                      # a percentage of nothing
        self.assertIsNone(sides('0 ' + half))
        for other in ('min(0px, 100% - 2em)', 'max(0px, 100% - 44px)', 'calc(100% - 44px)', 'min(4px, 100% - 44px)', '50%', 'auto'):
            self.assertIsNone(side(other, 32.0), other)

    def test_conjuncts_splits_a_condition_at_its_top_level_ands(self):
        self.assertEqual(conjuncts("box && box.querySelector('.copy-pop') && e.relatedTarget && !box.contains(e.relatedTarget)"),
                         ['box', "box.querySelector('.copy-pop')", 'e.relatedTarget', '!box.contains(e.relatedTarget)'])
        self.assertEqual(conjuncts("box && box.querySelector('.copy-pop') && !(e.relatedTarget && box.contains(e.relatedTarget))"),
                         ['box', "box.querySelector('.copy-pop')", '!(e.relatedTarget && box.contains(e.relatedTarget))'])
        self.assertEqual(conjuncts('a'), ['a'])
        self.assertEqual(conjuncts("s === '&&' && t"), ["s === '&&'", 't'])
        self.assertEqual(conjuncts('(a || b) && c'), ['(a || b)', 'c'])
        self.assertIsNone(conjuncts('a && b || c'))
        self.assertIsNone(conjuncts('a || b'))

    def test_the_reader_reads_every_selector_of_the_published_stylesheet(self):
        # A selector the reader cannot read is skipped, and a check that leans on the cascade could then pass or fail
        # for the wrong reason. If this fails after a stylesheet change: teach parse_selector / _simple the new
        # pseudo-class (or add it to STATE_PSEUDO when it is a state no page has while it loads).
        rules, unreadable = published_rules()
        self.assertEqual(unreadable, [])
        self.assertGreater(len(rules), 1000)
        for name in sorted(os.listdir(os.path.join(CSS_DIR, 'pages'))) + ['../base.css']:
            with self.subTest(file=name):
                self.assertEqual(parse_css(source('css', 'pages', name))[1], [])

    def test_a_script_is_read_past_its_comments_strings_and_regular_expressions(self):
        src = ("var a = s.replace(/\"/g, ''); // a quote ' in a comment {\n"
               "/* another { */ var b = '}' + \"{\" + x / 2 / y; if (/[/{]/.test(a)) { go(); }\n")
        js = Script(src)
        self.assertNotIn('quote', js.text)
        self.assertNotIn('another', js.text)
        brace = src.index('{ go')
        self.assertTrue(js.code(brace))
        self.assertEqual(js.close(brace), src.rindex('}'))
        self.assertEqual(js.open(src.rindex('}')), brace)
        self.assertEqual([i for i, ch in enumerate(src) if ch in '{}' and js.code(i)], [brace, src.rindex('}')])
        self.assertTrue(js.code(src.index('/ 2')))                     # a division, not the start of a regular expression

    def test_marker_focus_reads_each_way_the_listeners_can_be_wired(self):
        loop = "document.querySelectorAll('.mk-pin[data-key], .mk-cluster').forEach(function (el) { %s });"
        both = {'focusin', 'focusout'}
        cases = [
            # the listeners on every marker, as before the fix
            (loop % "el.addEventListener('focusin', on); el.addEventListener('focusout', off);", both, both),
            (loop % "el.addEventListener('mouseenter', on);", set(), set()),
            # guarded by a braced if, a brace-less if, an else, and a positive test for a pin
            (loop % ("if (!el.classList.contains('mk-cluster')) { el.addEventListener('focusin', on);"
                     " el.addEventListener('focusout', off); }"), both, set()),
            (loop % "if (!el.classList.contains('mk-cluster')) el.addEventListener('focusin', on);", {'focusin'}, set()),
            (loop % "if (el.classList.contains('mk-cluster')) { link(el); } else { el.addEventListener('focusin', on); }", {'focusin'}, set()),
            (loop % "if (el.matches('.mk-pin')) { el.addEventListener('focusout', off); }", {'focusout'}, set()),
            # the wrong way round, a guard that lets clusters through, and a guard on something else
            (loop % "if (el.classList.contains('mk-cluster')) { el.addEventListener('focusin', on); }", set(), {'focusin'}),
            (loop % "if (!el.classList.contains('mk-cluster') || wide) { el.addEventListener('focusin', on); }", {'focusin'}, {'focusin'}),
            (loop % "if (map) { el.addEventListener('focus', on); }", {'focus'}, {'focus'}),
            # commented out is not wired; another element's listener is not the marker's
            (loop % "// el.addEventListener('focusin', on);\n row.addEventListener('focusin', on);", set(), set()),
            # two loops
            ("document.querySelectorAll('.mk-pin[data-key]').forEach(function (p) { p.addEventListener('focusin', on); });"
             "document.querySelectorAll('.mk-cluster').forEach(function (c) { c.addEventListener('click', go); });", {'focusin'}, set()),
            ("document.querySelectorAll('.mk-cluster').forEach((c) => { c.addEventListener('blur', off); });", set(), {'blur'}),
        ]
        for src, pin, cluster in cases:
            with self.subTest(src=src[60:150]):
                self.assertEqual(marker_focus(src), {'pin': pin, 'cluster': cluster})

    def test_radiogroup_setters_reads_who_gets_the_role(self):
        loop = "document.querySelectorAll('[data-filter-nav]').forEach(function (el) { %s });"
        self.assertEqual(radiogroup_setters(loop % "el.setAttribute('role', 'radiogroup');"), [('el', 'el', None, False)])
        self.assertEqual(radiogroup_setters(loop % ("var box = document.createElement('div'); el.parentNode.replaceChild(box, el);"
                                                    " box.setAttribute(\"role\", \"radiogroup\");")), [('box', 'el', 'div', True)])
        self.assertEqual(radiogroup_setters(loop % "var box = document.createElement('div'); box.setAttribute('role', 'radiogroup');"),
                         [('box', 'el', 'div', False)])
        self.assertEqual(radiogroup_setters("nav.setAttribute('role', 'radiogroup');"), [('nav', None, None, False)])
        self.assertEqual(radiogroup_setters(loop % "// el.setAttribute('role', 'radiogroup');\n"), [])


# ---------------------------------------------------------------- the published stylesheet and the fixture site

_PUBLISHED = []


def published_rules():
    """(rules, unreadable) of the stylesheet the build publishes (build.css_bundle(): base.css, the map rules, then the
    page stylesheets, comments stripped), parsed once."""
    if not _PUBLISHED:
        _PUBLISHED.append(parse_css(importlib.import_module('build').css_bundle()))
    return _PUBLISHED[0]


PREFIX = 'syn-ay-'           # every fixture slug starts with it; no real trip's slug does
REGION, COAST = 'Synthetic Range', 'Synthetic Coast'      # a region with maps, and one with too few reports for a map
RS = 'synthetic-range'
WRITEUP = ('Synthetic write-up for a test, long enough to stand as a written report in every sense of the word.\n\n'
           'Second synthetic paragraph, with *emphasis* and a [synthetic link](https://example.test/).')
SLUGS = dict((k, PREFIX + k) for k in ('story', 'lap', 'spring', 'crag', 'ride', 'photos', 'paddle', 'walk', 'undated', 'goal', 'idea',
                                       'tour', 'journal'))
SINGLE = ('story', 'lap', 'spring', 'crag', 'ride', 'photos', 'paddle', 'walk', 'undated')      # single-day reports


def _svg(w, h, inner=''):
    return '<svg width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>' % (w, h, w, h, inner)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def _render(rendered, slug, names, chart=False):
    """A placeholder render folder for one trip: meta.json with the maps `names` (and a profile chart), the fragment of
    each, and the tile and the two glyphs every list draws."""
    folder = os.path.join(rendered, 'trips', slug)
    meta = {'maps': {}, 'charts': {}}
    sizes = {'wide': (1440, 640), 'col': (718, 400), 'phone': (390, 336), 'tall': (560, 860)}
    for name in names:
        w, h = sizes[name.rsplit('-', 1)[1]]
        meta['maps'][name] = {'w': w, 'h': h, 'png': name + '.webp', 'base': name + '.base.svg'}
        _write(os.path.join(folder, name + '.svg.html'), _svg(w, h, '<path class="mk-trk" d="M1 1L9 9"/>'))
    if chart:
        for size, w in (('wide', 1248), ('col', 718), ('phone', 358)):
            name = 'profile-' + size
            meta['charts'][name] = {'w': w, 'h': 160, 'kind': 'profile', 'gps_max_ft': 9514.0, 'min_ft': 6890.0, 'vx': 2.0}
            _write(os.path.join(folder, name + '.svg.html'), _svg(w, 160))
    for name, (w, h) in core.GLYPH_SIZES.items():
        _write(os.path.join(folder, name + '.svg.html'), _svg(w, h, '<path class="gl-trk" d="M1 1L9 9"/>'))
    _write(os.path.join(folder, 'meta.json'), json.dumps(meta))


def _site_maps(rendered, pins, cluster):
    """rendered/site/: one region map and one ski region map for REGION, as tools/render.py names them, each a fragment
    with a track, a pin per trip (a link, as tools/lib/mapkit.py writes it) and one cluster marker."""
    meta = {'hash': '', 'regions': [REGION], 'all_regions': [COAST, REGION], 'maps': {}}
    marks = ''.join('<g class="mk-cat" data-key="%s"><path d="M1 1L9 9"/></g>'
                    '<a class="mk-pin" href="@@ROOT@@trips/%s/" data-key="%s" aria-label="%s"><title>%s</title>'
                    '<circle class="mk-hit" cx="9" cy="9" r="12" style="fill: transparent"/></a>' % (s, s, s, title, title)
                    for s, title in pins)
    marks += ('<g class="mk-cluster" aria-hidden="true" data-keys="%s"><title>2 reports</title>'
              '<circle class="mk-hit" cx="40" cy="40" r="14" style="fill: transparent"/><text x="40" y="40">2</text></g>' % ' '.join(cluster))
    for kind in ('region', 'ski'):
        for size, (w, h) in (('desktop', (718, 620)), ('phone', (390, 480))):
            name = '%s-%s-%s' % (kind, RS, size)
            meta['maps'][name] = {'w': w, 'h': h, 'png': name + '.webp', 'base': name + '.base.svg', 'region': REGION,
                                  'trips': [s for s, _t in pins], 'clusters': [{'x': 40, 'y': 40, 'n': 2, 'keys': list(cluster)}]}
            _write(os.path.join(rendered, 'site', name + '.svg.html'), _svg(w, h, marks))
    _write(os.path.join(rendered, 'site', 'meta.json'), json.dumps(meta))
    return meta


def _write_trips(trips_dir):
    mk, s = helpers.make_trip, SLUGS
    beta = [{'label': 'Trailhead', 'value': 'Synthetic Lot'}]
    mk(trips_dir, s['story'], title='Synthetic Story', activity='hike', date='2026-06-01', region=REGION, place='Synthetic Basin',
       track=True, body=WRITEUP, beta=beta, featured=True, stats={'distance_km': 12.0, 'gain_m': 800, 'high_m': 2900, 'low_m': 2100},
       photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic photo one'),
               photo('photos/02.webp', LANDSCAPE, alt='Synthetic photo two', caption='Synthetic caption.', sm=True),
               photo('photos/03.webp', LANDSCAPE, alt='Synthetic photo three'), photo('photos/04.webp', SQUARE, alt='')])
    mk(trips_dir, s['lap'], title='Synthetic Lap', activity='ski', date='2025-12-20', region=REGION, track=True)
    mk(trips_dir, s['spring'], title='Synthetic Spring Tour', activity='ski', date='2024-03-09', region=REGION, track=True, body=WRITEUP,
       photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one')])
    mk(trips_dir, s['crag'], title='Synthetic Crag', activity='climb', date='2025-08-02', region=REGION, track=True, body=WRITEUP,
       photos=[photo('photos/01.webp', PORTRAIT, alt='Synthetic photo one'), photo('photos/02.webp', PORTRAIT, alt='Synthetic photo two')])
    mk(trips_dir, s['ride'], title='Synthetic Ride', activity='mtb', date='2025-07-04', region=COAST, track=True)
    mk(trips_dir, s['photos'], title='Synthetic Photos Only', activity='mtb', date='2024-09-14', region=REGION, track=True,
       photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one'), photo('photos/02.webp', None, alt='Synthetic photo two')])
    mk(trips_dir, s['paddle'], title='Synthetic Paddle', activity='other', subtype='SUP', date='2025-09-01', region=REGION, track=True)
    mk(trips_dir, s['walk'], title='Synthetic Walk Without A Track', activity='hike', date='2025-05-05', region=REGION, body=WRITEUP)
    mk(trips_dir, s['undated'], title='Synthetic Undated Track', activity='hike', region=REGION, track=True)
    goals = importlib.import_module('goals')
    for key, extra, sidecar in (('goal', {'track': True, 'body': 'Synthetic planning notes for a test.',
                                         'photos': [photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one')]},
                                 {'status': 'shortlisted', 'priority': 'high', 'added_at': '2026-01-01', 'target_months': [7, 8],
                                  'outings': [{'outcome': 'attempted', 'date': '2026-06-01', 'report_slug': SLUGS['story'], 'note': ''}]}),
                                ('idea', {}, {'status': 'idea', 'added_at': '2026-02-01'})):
        folder = mk(trips_dir, s[key], title='Synthetic ' + key.title(), activity='hike', kind='planned', region=REGION, **extra)
        _write(os.path.join(folder, 'goal.json'), json.dumps(dict(goals.defaults(), **sidecar)))
    mk(trips_dir, s['tour'], title='Synthetic Tour', activity='ski', kind='multi-day', date='2026-03-10', end_date='2026-03-11',
       region=REGION, body=WRITEUP, photos=[photo('photos/01.webp', LANDSCAPE, alt='Synthetic photo one', sm=True)],
       days=[{'title': 'Synthetic Day One', 'date': '2026-03-10', 'body': WRITEUP, 'hut': 'Synthetic Hut',
              'photos': [photo('photos/d01-01.webp', LANDSCAPE, alt='Synthetic day photo'), photo('photos/d01-02.webp', PORTRAIT, alt='')]},
             {'title': 'Synthetic Day Two', 'date': '2026-03-11', 'track': False}])
    helpers.make_series(trips_dir, slug=s['journal'], title='Synthetic Journal', region=REGION, body=WRITEUP,
                        tracks=(True, True, False, True))
    # the card-size copy beside each .sm copy, so that every card of those covers carries the phone-only <picture>
    # wrapper and the page tests below meet it (contract-phase4.md 10.5)
    for key, name in (('story', '02'), ('tour', '01')):
        helpers.touch(os.path.join(trips_dir, s[key], 'photos', name + '.th.webp'))


def _snapshot(mod):
    """The module's private lists and dicts with a copy of each, so that what a build registers in them can be undone."""
    return [(v, v.copy()) for k, v in vars(mod).items() if k.startswith('_') and isinstance(v, (list, dict))]


def _restore(snap):
    for obj, copy in snap:
        if isinstance(obj, dict):
            obj.clear()
            obj.update(copy)
        else:
            obj[:] = copy


_SITE = []


def site_pages():
    """{url: html} of every HTML page the page modules build for the fixture site, built once per test run. core's
    registered site (and every other private list or dict of core) is put back as it was afterwards."""
    if _SITE:
        return _SITE[0]
    build = importlib.import_module('build')
    home = importlib.import_module('sitegen.pages.home')
    tmp = tempfile.mkdtemp()
    state = _snapshot(core)
    try:
        trips_dir, rendered = os.path.join(tmp, 'trips'), os.path.join(tmp, 'rendered')
        os.makedirs(trips_dir)
        _write_trips(trips_dir)
        for key in SINGLE + ('goal',):
            if key != 'walk':                      # a report without a track has nothing to render
                _render(rendered, SLUGS[key], ['map-wide', 'map-col', 'map-phone'], chart=key == 'story')
        _render(rendered, SLUGS['tour'], ['overview-wide', 'overview-col', 'overview-phone'])
        _render(rendered, SLUGS['journal'], ['overview-tall', 'overview-phone'])
        pins = [(SLUGS[k], 'Synthetic ' + k.title()) for k in ('story', 'lap', 'spring', 'crag')]
        meta = _site_maps(rendered, pins, (SLUGS['lap'], SLUGS['spring']))
        with mock.patch.object(core, 'ROOT', tmp), mock.patch.object(core, '_SITE_META', [meta]), \
                mock.patch.object(content, 'RENDERED', rendered), mock.patch.object(home, 'HOME_REGIONS', (REGION,)):
            trips = helpers.load_dir(trips_dir)
            for t in trips:
                if not (t['slug'].startswith(PREFIX) and t['rendered'].startswith(rendered)):
                    raise AssertionError('%s would read outside the temp dir' % t['slug'])
            site = build.site_of(helpers.newest_first(trips))
            site['featured'] = [site['by_slug'][SLUGS[k]] for k in ('story', 'tour', 'journal')]
            core.register_site(site)
            pages = {}
            for name in build.PAGE_MODULES:
                for p in importlib.import_module('sitegen.pages.' + name).build(site):
                    if not p.url.endswith('.json'):
                        if p.url in pages:
                            raise AssertionError('two pages at %r' % p.url)
                        pages[p.url] = p.html
    finally:
        _restore(state)
        getattr(importlib.import_module('sitegen.pages.report'), '_TITLE_COUNTS', {}).clear()
        shutil.rmtree(tmp, ignore_errors=True)
    _SITE.append(pages)
    return pages


_DOCS = {}


def page_doc(url):
    if url not in _DOCS:
        _DOCS[url] = Doc(site_pages()[url])
    return _DOCS[url]


def trip_url(key, sub=''):
    return 'trips/%s/%s' % (SLUGS[key], sub)


def inside(node, cls):
    """True when the node or one of its ancestors carries the class."""
    while node is not None:
        if cls in node.classes:
            return True
        node = node.parent
    return False


def focusable(node):
    """An element the Tab key stops at, or that a script or a click can focus: a link with an href, a form control,
    a summary, anything with a tabindex (a negative one included: it is still focusable, and still interactive)."""
    if node.tag in ('a', 'area'):
        return 'href' in node or 'tabindex' in node
    if node.tag == 'input':
        return node['type'] != 'hidden'
    return node.tag in ('button', 'select', 'textarea', 'summary', 'iframe') or 'tabindex' in node or 'contenteditable' in node


def tab_stop(node):
    return focusable(node) and node['tabindex'] != '-1' and 'disabled' not in node


WIDTHS = (360, 390, 600, 800, 1024, 1300)      # a small phone, a phone, each band between the breakpoints, a desktop


class SiteFixture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pages = site_pages()
        cls.rules = published_rules()[0]

    def nodes(self, url, cls=None, tag=None, within=None):
        """The elements of a built page with this class (and tag), inside an element of class `within` when given; the
        test fails when the page has none, so no check passes by finding nothing to check."""
        got = [n for n in page_doc(url).find_all(tag, cls=cls) if within is None or inside(n.parent, within)]
        self.assertTrue(got, '%s has no %s%s' % (url or 'the home page', tag or '', ('.' + cls) if cls else ''))
        return got


# ---------------------------------------------------------------- every page type: headings, skip link, images, nesting

class PageTests(SiteFixture):

    def test_the_fixture_builds_every_page_type(self):
        urls = set(self.pages)
        want = {'', 'trips/', 'tick-list/', 'map/', 'about/', '404.html'} | {core.section_url(a) for a in core.ACT}
        want |= {trip_url(k) for k in SLUGS}                                           # reports, goals, the tour, the journal
        # their full-screen map pages: one per report with a track, the rendered goal, the tour and the journal. The walk
        # has no track.gpx, so it has no map section and no map page (contract-phase4.md 10.2); the idea has no route
        with_map = [k for k in SINGLE if k != 'walk'] + ['goal', 'tour', 'journal']
        self.assertEqual(len(with_map), len(SINGLE) + 2)
        want |= {trip_url(k, 'map/') for k in with_map}
        self.assertNotIn(trip_url('walk', 'map/'), urls)
        self.assertNotIn(trip_url('idea', 'map/'), urls)
        self.assertEqual(urls, want)
        for url, html_ in self.pages.items():
            self.assertTrue(html_.startswith('<!doctype html>'), url)
        # the two report layouts, the goal page with and without a route, and the pages with a second sticky bar
        kinds = {key: page_doc(trip_url(key)).find('body')['class'] for key in SLUGS}
        self.assertIn('p-report--story', kinds['story'])
        self.assertNotIn('p-report--story', kinds['lap'])
        self.assertIn('p-goal', kinds['goal'])
        self.assertIn('p-goal', kinds['idea'])
        self.assertIn('p-multiday', kinds['tour'])
        self.assertIn('p-series', kinds['journal'])
        # and card covers with the phone-only wrapper are among what these tests walk
        self.assertGreaterEqual(sum(h.count('<picture class="cover-pic">') for h in self.pages.values()), 4)

    def test_the_report_without_a_track_is_a_whole_page_without_a_map(self):
        # contract-phase4.md 10.2: no track.gpx, no route: the page has no map section, no link to one and no download,
        # and what it still links to on itself is there (a phone bar item or a title action that led to a missing
        # section would be a control that does nothing)
        url = trip_url('walk')
        doc = page_doc(url)
        self.assertIsNone(doc.by_id('map'))
        hrefs = [a['href'] or '' for a in doc.find_all('a')]
        self.assertNotIn('#map', hrefs)
        self.assertEqual([h for h in hrefs if h == 'map/' or h.startswith('map/') or '.gpx' in h.lower()], [])
        self.assertEqual([n for n in doc.find('body').walk() if 'download' in n], [])
        # The phone bar names the sections the page has, in page order, and nothing else. Without a track the walk has
        # no map and no GPX; a Stats item only when the page has a stats strip (it has none when nothing was measured
        # or typed). Fewer than two items is not navigation: report.bottom_bar then writes no bar at all.
        self.assertIsNotNone(doc.by_id('report'))
        sections = [(word, '#' + id_) for word, id_ in (('Stats', 'stats'), ('Report', 'report')) if doc.by_id(id_) is not None]
        bar = doc.find('nav', cls='bbar')
        if len(sections) < 2:
            self.assertIsNone(bar, 'a phone bar with a single item')
        else:
            self.assertIsNotNone(bar, 'the walk has %d sections to jump to and no phone bar' % len(sections))
            self.assertEqual([(a.find('span').text(), a['href']) for a in bar.find_all('a')], sections)
            self.assertEqual(bar['style'], '--n:%d' % len(sections))
        self.assertEqual([(a.text(), a['href']) for a in doc.find('div', cls='rep-actions').find_all('a')], [('Read the report', '#report')])
        # the reports beside it keep their map section, their two controls and their map page
        lap = page_doc(trip_url('lap'))
        self.assertIsNotNone(lap.by_id('map'))
        self.assertEqual([a.find('span').text() for a in lap.find('nav', cls='bbar').find_all('a')], ['Map', 'Stats', 'GPX'])
        self.assertIn(trip_url('lap', 'map/'), self.pages)

    def test_every_link_into_its_own_page_has_a_target(self):
        # a skip link, a section row, a phone bar item or a filter that jumps to an id the page lacks moves no focus and
        # scrolls nowhere; checked on every page type, the report without a track among them
        checked = 0
        for url in sorted(self.pages):
            with self.subTest(page=url):
                doc = page_doc(url)
                ids = {n['id'] for n in doc.root.walk() if n['id']}
                for a in doc.find_all('a'):
                    href = a['href'] or ''
                    if href.startswith('#') and len(href) > 1:
                        checked += 1
                        self.assertIn(href[1:], ids, '%s links %s, which is not an id on the page' % (url or 'the home page', href))
        self.assertGreater(checked, 100)

    def test_every_page_has_exactly_one_h1_with_text(self):
        for url in sorted(self.pages):
            with self.subTest(page=url):
                h1 = page_doc(url).find_all('h1')
                self.assertEqual(len(h1), 1, [h.text() for h in h1])
                self.assertTrue(h1[0].text())
                main = page_doc(url).by_id('main')
                self.assertTrue(any(n is h1[0] for n in main.walk()), 'the h1 is outside <main>')

    def test_the_skip_link_is_the_first_focusable_element_and_points_at_main(self):
        for url in sorted(self.pages):
            with self.subTest(page=url):
                doc = page_doc(url)
                first = next((n for n in doc.find('body').walk() if focusable(n)), None)
                self.assertIsNotNone(first)
                self.assertEqual((first.tag, first['href']), ('a', '#main'), repr(first))
                self.assertIn('skip', first.classes)
                self.assertTrue(first.text())
                self.assertTrue(tab_stop(first))
                self.assertIs(first, doc.find('body').elements()[0])          # nothing at all stands before it
                # its target: the one <main>, and the only element with that id
                targets = doc.find_all(attrs={'id': 'main'})
                self.assertEqual([t.tag for t in targets], ['main'])
                self.assertEqual(len(doc.find_all('main')), 1)
                self.assertEqual(len(doc.find_all('a', attrs={'href': '#main'})), 1)

    def test_every_img_has_an_alt_attribute(self):
        seen = described = 0
        for url in sorted(self.pages):
            with self.subTest(page=url):
                for img in page_doc(url).find_all('img'):
                    seen += 1
                    self.assertIn('alt', img, 'no alt attribute on %r' % img)
                    described += bool(img['alt'])
                    if not img['alt']:
                        continue
                    # a described image is a photo, and its description is the one recorded for it, not a file name
                    self.assertRegex(img['alt'], r'^(Synthetic [a-z ]+|(Trail sign|Ridge view), day \d)$')
        self.assertGreater(seen, 150)            # photos, covers, map layers, glyphs and tiles all came through
        self.assertGreater(described, 30)

    def test_no_interactive_element_is_nested_in_another(self):
        # the content model of <a> and <button> has no interactive content: a browser's parser repairs such nesting
        # in its own way, and what a screen reader then meets is not what the generator wrote
        interactive = ('a', 'button', 'input', 'select', 'textarea', 'summary', 'details', 'label', 'iframe')
        roles = ('button', 'link', 'tab', 'radio', 'checkbox', 'switch', 'menuitem')
        checked = 0
        for url in sorted(self.pages):
            with self.subTest(page=url):
                for node in page_doc(url).find('body').walk():
                    if not (node.tag in interactive or node['role'] in roles or 'tabindex' in node):
                        continue
                    checked += 1
                    a = node.parent
                    while a is not None:
                        self.assertFalse(a.tag in ('a', 'button') or a['role'] in ('button', 'link'), '%r is inside %r' % (node, a))
                        a = a.parent
        self.assertGreater(checked, 1000)

    def test_every_link_and_button_has_a_name(self):
        for url in sorted(self.pages):
            with self.subTest(page=url):
                for node in page_doc(url).find('body').walk():
                    if node.tag not in ('a', 'button') or node['aria-hidden'] == 'true' or 'hidden' in node:
                        continue        # (a button that ships hidden is named by the script that shows it)
                    name = node['aria-label'] or node.text() or ' '.join(i['alt'] or '' for i in node.find_all('img')).strip()
                    name = name or ' '.join(t.text() for t in node.find_all('title')).strip() or node['aria-labelledby']
                    self.assertTrue(name, '%r has no accessible name' % node)

    def test_a_link_hidden_from_assistive_technology_is_not_a_tab_stop(self):
        for url in sorted(self.pages):
            with self.subTest(page=url):
                for node in page_doc(url).find('body').walk():
                    if tab_stop(node):
                        a = node
                        while a is not None:
                            self.assertNotEqual(a['aria-hidden'], 'true', '%r can be tabbed to inside aria-hidden %r' % (node, a))
                            a = a.parent


# ---------------------------------------------------------------- section pages: the filter band's role (section.js)

class FilterBandTests(SiteFixture):

    def bands(self):
        out = []
        for act in core.ACT:
            url = core.section_url(act)
            out += [(url, n) for n in page_doc(url).find('body').walk() if 'data-filter-nav' in n]
        return out

    def test_the_generated_band_is_a_nav_of_links_without_a_role(self):
        bands = self.bands()
        self.assertEqual(sorted(url for url, _n in bands), ['other/', 'ski/'])        # the fixture's two seasons, and Other's types
        for url, band in bands:
            with self.subTest(page=url):
                self.assertEqual(band.tag, 'nav')
                self.assertNotIn('role', band)
                self.assertIn('sec-seg', band.classes)
                self.assertTrue(band['aria-label'])
                self.assertEqual(band['data-filter-nav'], 'reports')
                self.assertIsNotNone(page_doc(url).by_id('reports'))
                links = band.find_all('a', cls='sec-seg-a')
                self.assertGreaterEqual(len(links), 2)
                self.assertEqual([a for a in band.elements()], links)
                for a in links:
                    self.assertNotIn(a['role'], ('radio', 'radiogroup'))             # the script's roles, not the page's

    def test_no_generated_nav_carries_a_role(self):
        # a role on <nav> replaces its navigation landmark; role=radiogroup on it was the reported case
        for url in sorted(self.pages):
            with self.subTest(page=url):
                self.assertEqual([n for n in page_doc(url).find_all('nav') if 'role' in n], [])

    def test_section_js_gives_the_role_to_a_div_it_puts_in_the_navs_place(self):
        setters = radiogroup_setters(source('js', 'pages', 'section.js'))
        self.assertEqual(len(setters), 1, setters)
        var, param, made, replaced = setters[0]
        self.assertIsNotNone(param, 'role="radiogroup" is set outside the [data-filter-nav] loop')
        self.assertNotEqual(var, param, 'role="radiogroup" is set on the [data-filter-nav] element itself, which is a <nav>')
        self.assertEqual(made, 'div', 'the element given role="radiogroup" is not a <div> made by the script')
        self.assertTrue(replaced, 'the <nav> is not replaced by the new element before the role is set')

    def test_the_new_element_takes_over_the_navs_attributes_and_children(self):
        # the band's label, class and data-filter-nav are what names the group, styles it and wires the filter
        js = Script(source('js', 'pages', 'section.js'))
        (_sel, param, start, end), = js.each_callbacks(lambda s: 'data-filter-nav' in s)
        body = js.text[start:end]
        var = radiogroup_setters(source('js', 'pages', 'section.js'))[0][0]
        self.assertRegex(body, r'%s\.attributes' % re.escape(param))
        self.assertRegex(body, r'%s\.setAttribute\(\s*\w+\.name\s*,\s*\w+\.value\s*\)' % re.escape(var))
        self.assertRegex(body, r'%s\.appendChild\(\s*%s\.firstChild\s*\)' % (re.escape(var), re.escape(param)))

    def test_a_link_that_had_the_focus_gets_it_back_after_the_move(self):
        # The band is an early Tab stop and the bundle is deferred: a visitor can be on one of its links when the script
        # runs. appendChild takes the focus off a link it moves, so the loop has to note the link first and focus it
        # again once it is in the <div>.
        src = source('js', 'pages', 'section.js')
        js = Script(src)
        (_sel, param, start, end), = js.each_callbacks(lambda s: 'data-filter-nav' in s)
        body = js.text[start:end]
        var = radiogroup_setters(src)[0][0]
        noted = re.search(r'(?:var|let|const)\s+([\w$]+)\s*=\s*%s\.contains\(\s*document\.activeElement\s*\)\s*\?\s*document\.activeElement\s*:\s*null\s*;'
                          % re.escape(param), body)
        self.assertIsNotNone(noted, 'the loop does not note which link of the band has the focus')
        had = noted.group(1)
        move = re.search(r'%s\.appendChild\(\s*%s\.firstChild\s*\)' % (re.escape(var), re.escape(param)), body)
        swap = re.search(r'replaceChild\(\s*%s\s*,\s*%s\s*\)' % (re.escape(var), re.escape(param)), body)
        self.assertIsNotNone(move)
        self.assertIsNotNone(swap)
        self.assertLess(noted.start(), move.start(), 'the focused link is looked for after the links have been moved: by then none of them has the focus')
        back = list(re.finditer(r'(?<![\w$.])%s\.focus\(([^)]*)\)' % re.escape(had), body))
        self.assertEqual(len(back), 1, 'the link that had the focus is not focused again (or more than once)')
        self.assertGreater(back[0].start(), swap.start(), 'the link is focused before it is back in the page')
        self.assertEqual(js.guards(start + back[0].start(), start), [('if', had)])          # only when there was one
        self.assertRegex(back[0].group(1), r'^\{\s*preventScroll\s*:\s*true\s*\}$')          # nothing on the page moves
        # after the roles are set, so that a screen reader reads the link as the radio it has become
        roles = [m.start() for m in re.finditer(r'''setAttribute\(\s*['"]role['"]''', body)]
        self.assertEqual(len(roles), 2)
        self.assertGreater(back[0].start(), max(roles))
        # and nothing else in the script moves the focus on its own (the ski region tabs focus on a key press)
        self.assertEqual(len(re.findall(r'\.focus\(', body)), 1)

    def test_no_other_script_sets_the_role(self):
        names = ['base.js'] + [os.path.join('pages', n) for n in sorted(os.listdir(os.path.join(JS_DIR, 'pages'))) if n.endswith('.js')]
        self.assertIn(os.path.join('pages', 'section.js'), names)
        for name in names:
            with self.subTest(script=name):
                self.assertEqual(len(radiogroup_setters(source('js', name))), 1 if name.endswith('section.js') else 0)
                self.assertNotRegex(Script(source('js', name)).text, r'''\.role\s*=\s*['"]radiogroup''')


# ---------------------------------------------------------------- D4, D6: base.js

class ScriptTests(unittest.TestCase):

    def setUp(self):
        self.src = source('js', 'base.js')
        self.js = Script(self.src)

    def test_map_pins_get_focus_listeners_and_cluster_markers_get_none(self):
        got = marker_focus(self.src)
        # a pin is a link: focusing it highlights its track and its row, leaving it clears them
        self.assertEqual(got['pin'], {'focusin', 'focusout'})
        # a cluster marker is an aria-hidden <g>: a focus listener makes it a Tab stop in Chrome
        self.assertEqual(got['cluster'], set())

    def test_the_marker_loop_still_wires_both_kinds_for_the_pointer(self):
        # of the loops over the markers, the one that gives them listeners (the others only toggle classes)
        loops = [x for x in self.js.each_callbacks(lambda s: '.mk-pin' in s or '.mk-cluster' in s) if self.js.listeners(x[1], x[2], x[3])]
        self.assertEqual(len(loops), 1, [x[0] for x in loops])
        selector, el, start, end = loops[0]
        self.assertEqual([s.strip() for s in selector.split(',')], ['.mk-pin[data-key]', '.mk-cluster'])
        events = [event for event, _pos in self.js.listeners(el, start, end)]
        self.assertEqual(sorted(e for e in events if e.startswith('mouse')), ['mouseenter', 'mouseleave'])
        for event, pos in self.js.listeners(el, start, end):
            if event.startswith('mouse'):
                self.assertEqual(self.js.guards(pos, start), [], event)        # pins and clusters alike

    def test_no_script_makes_a_cluster_marker_focusable(self):
        names = ['base.js'] + [os.path.join('pages', n) for n in sorted(os.listdir(os.path.join(JS_DIR, 'pages'))) if n.endswith('.js')]
        for name in names:
            with self.subTest(script=name):
                src = source('js', name)
                self.assertEqual(marker_focus(src)['cluster'], set())
                js = Script(src)
                for _selector, el, start, end in js.each_callbacks(lambda s: '.mk-cluster' in s):
                    body = js.text[start:end]
                    self.assertNotRegex(body, r'''(?<![\w$.])%s\.(tabIndex\s*=|setAttribute\(\s*['"]tabindex['"])''' % re.escape(el))

    def document_listeners(self, event):
        """The bodies of every document.addEventListener('<event>', function (e) { ... }) in base.js."""
        out = []
        for m in re.finditer(r'''document\.addEventListener\(\s*(['"])%s\1\s*,\s*function\s*\([^)]*\)\s*\{''' % event, self.js.text):
            if self.js.code(m.start()):
                out.append(self.js.text[m.end():self.js.close(m.end() - 1)])
        return out

    def test_the_copy_field_closes_when_focus_leaves_its_control(self):
        bodies = [b for b in self.document_listeners('focusout') if 'closeCopy(' in b]
        self.assertEqual(len(bodies), 1, 'no focusout listener on the document closes the copy field')
        body = bodies[0]
        self.assertRegex(body, r'''closest\(\s*['"]\.copy['"]\s*\)''')         # focus was inside a copy control
        self.assertIn('relatedTarget', body)                                    # and is going somewhere outside it
        self.assertRegex(body, r'\.contains\(\s*\w+\.relatedTarget\s*\)')
        self.assertRegex(body, r'''['"]\.copy-pop['"]''')                      # and a field is open

    def test_escape_closes_the_copy_field_from_anywhere(self):
        bodies = [b for b in self.document_listeners('keydown') if 'closeCopy(' in b]
        self.assertEqual(len(bodies), 1, 'no keydown listener on the document closes the copy field')
        self.assertRegex(bodies[0], r'''\.key\s*===?\s*['"]Escape['"]''')
        self.assertRegex(bodies[0], r'''['"]\.copy-pop['"]''')

    def test_close_copy_removes_the_field(self):
        m = re.search(r'(?:var|let|const)\s+closeCopy\s*=\s*function\s*\([^)]*\)\s*\{', self.js.text)
        self.assertIsNotNone(m, 'base.js has no closeCopy function')
        body = self.js.text[m.end():self.js.close(m.end() - 1)]
        self.assertRegex(body, r'''['"]\.copy-pop['"]''')
        self.assertRegex(body, r'removeChild\(|\.remove\(\)')

    def listener_spans(self, event):
        """[(target, body start, body end)] of every `<target>.addEventListener('<event>', function (...) { ... })`."""
        out = []
        for m in re.finditer(r'''(?<![\w$.])([\w$.]+)\.addEventListener\(\s*(['"])%s\2\s*,\s*function\s*\([^)]*\)\s*\{''' % event, self.js.text):
            if self.js.code(m.start()):
                out.append((m.group(1), m.end(), self.js.close(m.end() - 1)))
        return out

    def test_only_focus_going_somewhere_else_closes_the_copy_field(self):
        # A focusout that goes nowhere (no relatedTarget) is the window losing the focus, the field itself being taken
        # out of the page, or a press on something that takes no focus. Closing on it made Escape in the field throw:
        # Chromium sends that focusout from inside the removeChild that closes the field, and the listener removed the
        # field a second time. The condition has to ask for a relatedTarget, and for it to be outside the control.
        spans = [(s, e) for target, s, e in self.listener_spans('focusout') if target == 'document' and 'closeCopy(' in self.js.text[s:e]]
        self.assertEqual(len(spans), 1)
        start, end = spans[0]
        param = re.search(r'function\s*\(\s*([\w$]+)\s*\)\s*\{$', self.js.text[:start]).group(1)
        calls = [m.start() for m in re.finditer(r'(?<![\w$.])closeCopy\(', self.js.text[start:end])]
        self.assertEqual(len(calls), 1)
        conds = self.js.guards(start + calls[0], start)
        self.assertEqual([kind for kind, _c in conds], ['if'], 'closeCopy() is not under exactly one if in the focusout listener')
        terms = conjuncts(conds[0][1])
        self.assertIsNotNone(terms, 'the condition has an || in it: %s' % conds[0][1])
        self.assertIn('%s.relatedTarget' % param, terms, 'a focusout without a relatedTarget still closes the field: %s' % conds[0][1])
        outside = [t for t in terms if re.match(r'^!\s*([\w$]+)\.contains\(\s*%s\.relatedTarget\s*\)$' % re.escape(param), t)]
        self.assertEqual(len(outside), 1, 'the condition does not ask for the relatedTarget to be outside the control: %s' % conds[0][1])
        box = re.match(r'^!\s*([\w$]+)\.', outside[0]).group(1)
        self.assertRegex(self.js.text[start:start + calls[0]], r'''(?:var|let|const)\s+%s\s*=[^;]*closest\(\s*['"]\.copy['"]\s*\)''' % re.escape(box))
        self.assertTrue(any(re.match(r'''^%s\.querySelector\(\s*['"]\.copy-pop['"]\s*\)$''' % re.escape(box), t) for t in terms), terms)

    def test_escape_in_the_copy_field_focuses_the_button_before_the_field_goes(self):
        # closing first left the focus on <body> (and, with a listener that reacts to the field's focusout, never reached
        # the line that returned it): the button takes the focus, then the field, no longer focused, is removed
        spans = [(s, e) for target, s, e in self.listener_spans('keydown') if target != 'document' and 'closeCopy(' in self.js.text[s:e]]
        self.assertEqual(len(spans), 1, 'the copy field has no keydown listener of its own that closes it')
        body = self.js.text[spans[0][0]:spans[0][1]]
        self.assertRegex(body, r'''\.key\s*!==?\s*['"]Escape['"]|\.key\s*===?\s*['"]Escape['"]''')
        focus = list(re.finditer(r'(?<![\w$.])([\w$]+)\.focus\(\s*\)', body))
        close = list(re.finditer(r'(?<![\w$.])closeCopy\(\s*\)', body))
        self.assertEqual((len(focus), len(close)), (1, 1))
        self.assertLess(focus[0].start(), close[0].start(), 'the field is closed while the focus is still in it')
        # what takes the focus is the Copy link button the click listener found
        clicks = [b for b in self.document_listeners('click') if '.copy-btn' in b]
        self.assertEqual(len(clicks), 1)
        self.assertRegex(clicks[0], r'''(?:var|let|const)\s+%s\s*=[^;]*closest\(\s*['"]\.copy-btn['"]\s*\)''' % re.escape(focus[0].group(1)))

    def close_copy(self):
        m = re.search(r'(?:var|let|const)\s+closeCopy\s*=\s*function\s*\([^)]*\)\s*\{', self.js.text)
        self.assertIsNotNone(m, 'base.js has no closeCopy function')
        return m.end(), self.js.close(m.end() - 1)

    def test_close_copy_lets_go_of_the_focus_first_and_removes_only_what_is_still_in_the_page(self):
        # closeCopy has to be safe to call twice, and from a listener that runs while it is at work: removing the focused
        # field makes Chromium fire focusout from inside removeChild, and a second removal there makes the first throw
        start, end = self.close_copy()
        body = self.js.text[start:end]
        removals = list(re.finditer(r'(?<![\w$.])([\w$]+)\.parentNode\.removeChild\(\s*\1\s*\)', body))
        self.assertEqual(len(removals), 1, 'closeCopy does not remove the field with <field>.parentNode.removeChild(<field>)')
        field = removals[0].group(1)
        conds = [c for kind, c in self.js.guards(start + removals[0].start(), start) if kind == 'if']
        self.assertIn('%s.parentNode' % field, [t for c in conds for t in (conjuncts(c) or [])],
                      'a field that is no longer in the page is removed again: %s' % conds)
        blurs = list(re.finditer(r'(?<![\w$.])document\.activeElement\.blur\(\s*\)', body))
        self.assertEqual(len(blurs), 1, 'closeCopy does not take the focus off the field before removing it')
        self.assertLess(blurs[0].start(), removals[0].start(), 'the field is removed before it has given up the focus')
        self.assertEqual(self.js.guards(start + blurs[0].start(), start), [('if', '%s.contains(document.activeElement)' % field)])
        # the field the press was in is still left alone
        self.assertRegex(body, r'if\s*\(\s*%s\s*===\s*keep\s*\)\s*return\s*;' % re.escape(field))


# ---------------------------------------------------------------- D2, D3: without JavaScript

def scripting_none(rules):
    return [r for r in rules if any(re.sub(r'\s+', '', q.lower()) == '(scripting:none)' for q in r.media)]


def subject_class(rule):
    """The class a rule is about when its subject is one bare class ('.units', '.site-h .units'), else None."""
    if rule.parts is None:
        return None
    simples = rule.parts[-1][1]
    return simples[0][1] if len(simples) == 1 and simples[0][0] == 'cls' else None


class NoScriptTests(SiteFixture):

    def header(self, url):
        doc = page_doc(url)
        head = doc.find('header', cls='site-h')
        self.assertIsNotNone(head, url)
        return head

    def displays(self, rules):
        """{class: declared display} of the (scripting: none) rules whose subject is one bare class."""
        out = {}
        for r in scripting_none(rules):
            if subject_class(r) and 'display' in r.decls:
                out[subject_class(r)] = r.decls['display'][0]
        return out

    def test_base_css_has_the_scripting_none_block(self):
        got = self.displays(parse_css(source('css', 'base.css'))[0])
        for cls in ('menu-btn', 'units', 'nav-search'):
            with self.subTest(hidden=cls):
                self.assertEqual(got.get(cls), 'none')
        self.assertIn(got.get('nav'), ('flex', 'block', 'grid', 'inline-flex'))

    def test_report_css_still_hides_the_copy_control_and_the_share_row(self):
        got = self.displays(parse_css(source('css', 'pages', 'report.css'))[0])
        self.assertEqual(got.get('copy'), 'none')
        self.assertEqual(got.get('rep-share'), 'none')

    def test_the_published_stylesheet_keeps_both_blocks(self):
        got = self.displays(self.rules)
        self.assertEqual({k: got.get(k) for k in ('menu-btn', 'units', 'nav-search', 'copy', 'rep-share')},
                         dict.fromkeys(('menu-btn', 'units', 'nav-search', 'copy', 'rep-share'), 'none'))
        self.assertNotEqual(got.get('nav'), 'none')

    # the header as it is generated, and what the published stylesheet makes of it with scripting off

    def header_parts(self, url):
        head = self.header(url)
        nav = head.find('nav', cls='nav')
        btn = head.find('button', cls='menu-btn')
        self.assertIsNotNone(nav)
        self.assertIsNotNone(btn)
        units, search = nav.find(cls='units'), nav.find('a', cls='nav-search')
        self.assertIsNotNone(units, 'no units switch in the header nav')
        self.assertIsNotNone(search, 'no Search link in the header nav')
        return nav, btn, units, search

    def assertNotDisplayed(self, pick, what):
        """With scripting off the header element pick(header_parts(url)) is not displayed (display: none on it or on an
        element around it) on every page and at every width. One failure says where it is, and which rule shows it."""
        shown, tried = collections.OrderedDict(), 0
        for url in ('', 'trips/', trip_url('story'), 'about/'):
            node = pick(self.header_parts(url))
            for width in WIDTHS:
                e = env(width, scripting='none')
                tried += 1
                if displayed(node, self.rules, e):       # neither it nor anything around it has display: none
                    shown.setdefault(why(node, 'display', self.rules, e), []).append('%s at %d px' % (url or 'the home page', width))
        if shown:
            self.fail('without JavaScript %s is still displayed: %s'
                      % (what, '; '.join('%s (%d of %d page and width combinations, first on %s)' % (rule, len(at), tried, at[0])
                                         for rule, at in shown.items())))

    def test_without_scripting_the_menu_button_is_not_displayed(self):
        self.assertNotDisplayed(lambda parts: parts[1], 'the Menu button')

    def test_without_scripting_the_units_switch_is_not_displayed(self):
        self.assertNotDisplayed(lambda parts: parts[2], 'the units switch')

    def test_without_scripting_the_search_link_is_not_displayed(self):
        self.assertNotDisplayed(lambda parts: parts[3], 'the header Search link')

    def test_without_scripting_the_primary_links_are_displayed_at_every_width(self):
        for url in ('', 'trips/', trip_url('story'), 'about/'):
            nav = self.header_parts(url)[0]
            links = [a for a in nav.find_all('a') if 'nav-search' not in a.classes]
            self.assertGreaterEqual(len(links), 4)        # Trips, Tick list, Map, About
            for width in WIDTHS:
                with self.subTest(page=url, width=width):
                    e = env(width, scripting='none')
                    for a in links:
                        gone = hidden_by(a, self.rules, e)
                        self.assertIsNone(gone, '%r is not displayed: %s' % (a, gone and why(gone, 'display', self.rules, e)))
                    self.assertIn(computed(nav, 'display', self.rules, e), ('flex', 'block', 'grid'))

    def test_with_scripting_the_header_is_as_before(self):
        nav, btn, units, search = self.header_parts('')
        for width, nav_display, btn_display in ((390, 'none', 'flex'), (800, 'none', 'flex'), (1139, 'none', 'flex'),
                                                (1140, 'flex', 'none'), (1300, 'flex', 'none')):
            with self.subTest(width=width):
                e = env(width)
                self.assertEqual(computed(nav, 'display', self.rules, e), nav_display)
                self.assertEqual(computed(btn, 'display', self.rules, e), btn_display)
                # the units switch and the Search link come and go with the row they are in, and with nothing else
                self.assertEqual(displayed(units, self.rules, e), nav_display == 'flex')
                self.assertEqual(displayed(search, self.rules, e), nav_display == 'flex')
                self.assertNotEqual(computed(units, 'display', self.rules, e), 'none')
                self.assertNotEqual(computed(search, 'display', self.rules, e), 'none')

    def test_without_scripting_no_copy_control_and_no_share_row_is_displayed(self):
        seen = 0
        for key in ('story', 'lap', 'goal', 'tour', 'journal'):
            url = trip_url(key)
            copies = self.nodes(url, cls='copy')
            rows = page_doc(url).find_all(cls='rep-share')
            seen += len(rows)
            for width in WIDTHS:
                with self.subTest(page=url, width=width):
                    e = env(width, scripting='none')
                    for node in copies + rows:
                        self.assertFalse(displayed(node, self.rules, e), '%r: %s' % (node, why(node, 'display', self.rules, e)))
        self.assertGreaterEqual(seen, 3)

    def test_with_scripting_the_copy_control_is_displayed(self):
        url = trip_url('story')
        row = self.nodes(url, cls='rep-share')[0]
        in_row = [n for n in self.nodes(url, cls='copy') if inside(n, 'rep-share')]
        in_title = [n for n in self.nodes(url, cls='copy') if inside(n, 'rep-actions')]
        self.assertEqual((len(in_row), len(in_title)), (1, 1))
        self.assertTrue(displayed(row, self.rules, env(390)))            # the phone's share row
        self.assertTrue(displayed(in_row[0], self.rules, env(390)))
        self.assertFalse(displayed(row, self.rules, env(800)))           # from 760 px the title has the button
        self.assertTrue(displayed(in_title[0], self.rules, env(800)))

    # the header without JavaScript at every width a visitor meets: links that wrap, nothing that scrolls or clips

    # 320 is a phone, or a desktop window zoomed to 400 %; 479 / 480 is where the no-script header starts to stick again,
    # 1139 / 1140 where the links take the menu's place when there is JavaScript
    NS_WIDTHS = (320, 360, 390, 479, 480, 760, 1139, 1140, 1280)
    NS_PAGES = ('', 'trips/', 'about/', 'ski/', trip_url('story'), trip_url('journal'), trip_url('tour'))

    def header_boxes(self, url):
        """(html, header, its inner row, nav, the row of links, the row that holds Search) of a page."""
        head = self.header(url)
        inner = head.find('div', cls='site-h-in')
        nav, _btn, _units, search = self.header_parts(url)
        rows = [n for n in nav.elements() if 'nav-l' in n.classes]
        self.assertEqual(len(rows), 2, 'the header nav no longer has its two .nav-l rows')
        self.assertEqual(rows[1].find_all('a'), [search])                    # the second row holds the Search link, alone
        self.assertEqual([n for n in nav.elements() if 'nav-sep' in n.classes], [nav.elements()[1]])     # between the two
        self.assertIs(nav.elements()[2], rows[1])
        self.assertGreaterEqual(len(rows[0].find_all('a')), 4)
        return page_doc(url).find('html'), head, inner, nav, rows[0], rows[1]

    def test_without_scripting_the_links_wrap_and_nothing_in_the_header_scrolls(self):
        # one row that scrolled sideways hid two or three of the five links on a phone with nothing to show for it
        for url in self.NS_PAGES:
            _root, head, inner, nav, links, search_row = self.header_boxes(url)
            for width in self.NS_WIDTHS:
                with self.subTest(page=url, width=width):
                    e = env(width, scripting='none')
                    self.assertEqual(computed(links, 'display', self.rules, e), 'flex')
                    self.assertEqual(computed(links, 'flex-wrap', self.rules, e), 'wrap', why(links, 'flex-wrap', self.rules, e))
                    # the row and the nav may be narrower than the links side by side, so the row wraps where they do
                    # not fit instead of pushing the page wide
                    self.assertEqual(computed(links, 'min-width', self.rules, e), '0')
                    self.assertEqual(computed(nav, 'min-width', self.rules, e), '0')
                    # nothing between a link and the page scrolls or clips: no link out of sight, no focus ring cut
                    for box in (links, nav, inner, head):
                        for prop in ('overflow', 'overflow-x', 'overflow-y', 'clip-path', 'contain'):
                            self.assertIn(computed(box, prop, self.rules, e), (None, 'visible'), why(box, prop, self.rules, e))
                    # the header grows with its rows
                    self.assertEqual(computed(inner, 'height', self.rules, e), 'auto', why(inner, 'height', self.rules, e))
                    # the row that held nothing but Search takes no room, and no gap, at the end of the links
                    self.assertFalse(displayed(search_row, self.rules, e), why(search_row, 'display', self.rules, e))
                    # every link is still a 44 px target on one line
                    for a in links.find_all('a'):
                        self.assertEqual(min_block(a, self.rules, e), 44.0)
                        self.assertEqual(computed(a, 'white-space', self.rules, e), 'nowrap')

    def test_without_scripting_a_phone_header_does_not_stick_and_reserves_no_height(self):
        # two rows of links are too tall to follow the page down. Once the header stays at the top, nothing may keep
        # room for it: --header-h is the scroll padding, and the `top` of the journal's month bar and the day bar
        for url in self.NS_PAGES:
            root, head, inner, _nav, _links, _search = self.header_boxes(url)
            for width in self.NS_WIDTHS:
                with self.subTest(page=url, width=width):
                    e = env(width, scripting='none')
                    phone = width < 480
                    self.assertEqual(computed(head, 'position', self.rules, e), 'static' if phone else 'sticky', why(head, 'position', self.rules, e))
                    self.assertEqual(computed(root, '--header-h', self.rules, e), '0px' if phone else '72px' if width >= 1200 else '56px')
                    # never lower than the header with JavaScript: 56 px, 72 px from 1200
                    self.assertEqual(computed(inner, 'min-height', self.rules, e), '56px' if phone else 'var(--header-h)')
                    self.assertEqual(computed(root, 'scroll-padding-top', self.rules, e), 'calc(var(--header-h) + var(--sticky-extra, 0px) + 16px)')
        for key, bar_cls in (('journal', 'ser-mnav'), ('tour', 'mul-dnav')):
            bar = self.nodes(trip_url(key), cls=bar_cls)[0]
            for width in self.NS_WIDTHS:
                with self.subTest(bar=bar_cls, width=width):
                    self.assertEqual(computed(bar, 'top', self.rules, env(width, scripting='none')), 'var(--header-h)')

    def test_without_scripting_a_header_links_focus_ring_has_room_on_every_side(self):
        ring = [r for r in self.rules if r.selector == ':focus-visible' and not r.media]
        self.assertEqual(len(ring), 1)
        width_ = re.match(r'^(\d+(?:\.\d+)?)px solid\b', ring[0].decls['outline'][0])
        self.assertIsNotNone(width_)
        need = float(width_.group(1)) + px(ring[0].decls['outline-offset'][0])
        self.assertEqual(need, 4.0)                      # 2 px, 2 px away from the link
        # no rule draws the header links' ring anywhere else, or removes it
        for r in self.rules:
            if ':focus' in r.selector and re.search(r'\.(nav|site-h|brand)\b', r.selector):
                self.fail('a focus rule of the header: %s' % r.selector)
        for url in self.NS_PAGES:
            root, _head, inner, _nav, links, _search = self.header_boxes(url)
            for width in self.NS_WIDTHS:
                with self.subTest(page=url, width=width):
                    e = env(width, scripting='none')
                    if width < 480:
                        # the links may be in two rows that fill the header from top to bottom: its own padding is the room
                        pad = sides(computed(inner, 'padding-block', self.rules, e))
                        self.assertIsNotNone(pad, why(inner, 'padding-block', self.rules, e))
                        self.assertGreaterEqual(min(pad), need)
                        self.assertEqual(computed(inner, 'box-sizing', self.rules, e), 'border-box')    # so one row is still 56 px
                    else:
                        # one row of 44 px links, centred in a header of --header-h
                        self.assertIsNone(computed(inner, 'padding-block', self.rules, e))
                        self.assertEqual(computed(inner, 'align-items', self.rules, e), 'center')
                        self.assertGreaterEqual((px(computed(root, '--header-h', self.rules, e)) - 44) / 2, need)
                    # sideways: the gap to the name on the left, the page margin on the right; between two links, their gap
                    self.assertGreaterEqual(px(computed(inner, 'gap', self.rules, e)), need)
                    self.assertGreaterEqual(px(computed(root, '--m', self.rules, e)), need)
                    self.assertGreaterEqual(px(computed(links, 'gap', self.rules, e)), 2 * need)
                    self.assertEqual(computed(links, 'row-gap', self.rules, e), '0')      # two rows touch: a ring lies over the row beside it

    def test_without_scripting_every_units_switch_is_gone_the_about_pages_own_too(self):
        # the About page's switch sits in the text ('The MI | KM switch changes every page ...'), outside the header
        doc = page_doc('about/')
        switches = doc.find_all(cls='units')
        own = [u for u in switches if 'abo-units' in u.classes]
        self.assertEqual((len(switches), len(own)), (3, 1))          # the header's, the menu's, the page's own
        self.assertFalse(inside(own[0], 'site-h'))
        self.assertEqual([b['data-units'] for b in own[0].find_all('button')], ['mi', 'km'])
        for width in self.NS_WIDTHS:
            with self.subTest(width=width):
                off, on = env(width, scripting='none'), env(width)
                for u in switches:
                    self.assertFalse(displayed(u, self.rules, off), '%r: %s' % (u, why(u, 'display', self.rules, off)))
                    for b in u.find_all('button'):
                        self.assertFalse(displayed(b, self.rules, off))
                # with JavaScript it is there as before, at every width
                self.assertTrue(displayed(own[0], self.rules, on))
                self.assertEqual(computed(own[0], 'display', self.rules, on), 'inline-flex')
        # every other page has the header's two and no third
        for url in ('', 'trips/', trip_url('story')):
            self.assertEqual(len(page_doc(url).find_all(cls='units')), 2, url)

    def test_with_scripting_none_of_this_touches_the_header(self):
        # every rule above sits in a (scripting: none) query: with JavaScript the header is what it was at every width
        for url in self.NS_PAGES:
            root, head, inner, nav, links, search_row = self.header_boxes(url)
            for width in self.NS_WIDTHS:
                with self.subTest(page=url, width=width):
                    e = env(width)
                    self.assertEqual(computed(head, 'position', self.rules, e), 'sticky')
                    self.assertEqual(computed(head, 'top', self.rules, e), '0')
                    self.assertEqual(computed(root, '--header-h', self.rules, e), '72px' if width >= 1200 else '56px')
                    self.assertEqual(computed(inner, 'height', self.rules, e), 'var(--header-h)')
                    for prop in ('min-height', 'padding-block', 'padding', 'flex-wrap'):
                        self.assertIsNone(computed(inner, prop, self.rules, e), why(inner, prop, self.rules, e))
                    for row in (links, search_row):
                        self.assertEqual(computed(row, 'display', self.rules, e), 'flex')
                        self.assertEqual(computed(row, 'gap', self.rules, e), '28px')
                        for prop in ('flex-wrap', 'row-gap', 'min-width', 'overflow-x', 'overflow'):
                            self.assertIsNone(computed(row, prop, self.rules, e), why(row, prop, self.rules, e))
                    self.assertIsNone(computed(nav, 'min-width', self.rules, e))
                    self.assertEqual(computed(nav, 'display', self.rules, e), 'flex' if width >= 1140 else 'none')

    def test_the_no_script_header_rules_are_all_inside_scripting_queries(self):
        # the same from the stylesheet's side: base.css states each of these only where scripting is off
        rules = parse_css(source('css', 'base.css'))[0]

        def off(r):
            return any('scripting' in q and 'none' in q for q in r.media)

        for selector, prop in (('.nav-l', 'flex-wrap'), ('.nav-l', 'row-gap'), ('.nav-l', 'min-width'), ('.nav', 'min-width'),
                               ('.site-h-in', 'min-height'), ('.site-h-in', 'padding-block'), ('.nav-sep + .nav-l', 'display'),
                               ('.units.abo-units', 'display'), ('.site-h .units', 'display'), ('.menu-btn', 'width')):
            with self.subTest(selector=selector, prop=prop):
                stated = [r for r in rules if r.selector == selector and prop in r.decls]
                if prop == 'width':                      # a control: the menu button's own rule is still there, untouched
                    self.assertEqual([off(r) for r in stated], [False])
                    continue
                self.assertTrue(stated, 'no rule states %s for %s' % (prop, selector))
                self.assertEqual([r.selector for r in stated if not off(r)], [])
        for selector, prop, values in (('.site-h', 'position', ['sticky', 'static']), ('.site-h-in', 'height', ['var(--header-h)', 'auto']),
                                       (':root', '--header-h', ['56px', '72px', '0px'])):
            with self.subTest(selector=selector, prop=prop):
                stated = [r for r in rules if r.selector == selector and prop in r.decls]
                self.assertEqual([r.decls[prop][0] for r in stated], values)
                self.assertEqual([off(r) for r in stated], [False] * (len(values) - 1) + [True])
        # the phone block is narrower than the width at which five links fit beside the name (about 452 px)
        phone = [r for r in rules if r.selector == '.site-h' and r.decls.get('position', ('',))[0] == 'static']
        self.assertEqual(len(phone), 1)
        self.assertEqual(len(phone[0].media), 1)
        limit = re.search(r'\(\s*max-width\s*:\s*([\d.]+)px\s*\)', phone[0].media[0])
        self.assertIsNotNone(limit, phone[0].media)
        self.assertTrue(460 <= float(limit.group(1)) < 560, phone[0].media)
        # no rule in base.css scrolls the links sideways any more
        self.assertEqual([r.selector for r in rules if r.selector.startswith('.nav') and any(p.startswith('overflow') or p == 'scrollbar-width' for p in r.decls)], [])


# ---------------------------------------------------------------- D1: focus under the second sticky bar

class StickyBarTests(SiteFixture):

    # page, the element the controls are in, the sticky bar, the bar's height variable
    BARS = (('journal', 'ser-log', 'ser-mnav', '--ser-nav-h'), ('tour', 'mul-body', 'mul-dnav', '--dnav-h'))

    def test_the_bar_is_sticky_under_the_header_and_as_tall_as_its_variable(self):
        for key, _scope, bar_cls, var in self.BARS:
            url = trip_url(key)
            bar = self.nodes(url, cls=bar_cls)[0]
            body = page_doc(url).find('body')
            for width in WIDTHS:
                with self.subTest(page=key, width=width):
                    e = env(width)
                    self.assertEqual(computed(bar, 'position', self.rules, e), 'sticky')
                    self.assertEqual(computed(bar, 'top', self.rules, e), 'var(--header-h)')
                    self.assertIsNotNone(px(computed(body, var, self.rules, e)), '%s is not a px length on <body>' % var)
                    tall = [n for n in [bar] + list(bar.walk()) if 'var(%s)' % var in (computed(n, 'height', self.rules, e) or '')]
                    self.assertTrue(tall, 'nothing in .%s has a height of var(%s)' % (bar_cls, var))

    def test_every_control_under_the_bar_gets_a_scroll_margin_of_the_bars_height(self):
        for key, scope_cls, bar_cls, var in self.BARS:
            url = trip_url(key)
            scope = self.nodes(url, cls=scope_cls)[0]
            self.assertTrue(inside(self.nodes(url, cls=bar_cls)[0], scope_cls))          # the bar sits in the block it covers
            controls = [n for n in scope.walk() if focusable(n) and not inside(n, bar_cls)]
            self.assertGreaterEqual(len(controls), 10, '%s has too few controls to check' % url)
            self.assertIn('a', {n.tag for n in controls})
            if key == 'journal':
                self.assertEqual({n.tag for n in controls}, {'a', 'button', 'input'})    # day links, Copy link, the write-ups switch
            for width in (390, 800, 1300):
                e = env(width)
                for node in controls:
                    with self.subTest(page=key, width=width, node=repr(node)[:80]):
                        value = computed(node, 'scroll-margin-top', self.rules, e) or ''
                        self.assertIn('var(%s)' % var, value, why(node, 'scroll-margin-top', self.rules, e))
                        # the bar's height, or that and a little more: never less
                        self.assertRegex(value, r'^(var\(%s\)|calc\(\s*(var\(%s\)\s*\+\s*\d+px|\d+px\s*\+\s*var\(%s\))\s*\))$' % (var, var, var))

    def test_the_rule_names_links_and_buttons_at_least(self):
        # the same on the sources, file by file: the selector may be written any way that reaches links and buttons
        for name, scope_cls, var in (('series.css', 'ser-log', '--ser-nav-h'), ('multiday.css', 'mul-body', '--dnav-h')):
            rules = parse_css(source('css', 'pages', name))[0]
            for tag in ('a', 'button'):
                with self.subTest(file=name, tag=tag):
                    probe = Doc('<div class="%s"><p><%s href="#">x</%s></p></div>' % (scope_cls, tag, tag)).find(tag)
                    self.assertIn('var(%s)' % var, computed(probe, 'scroll-margin-top', rules, env()) or '')

    def test_the_bars_own_controls_keep_no_margin(self):
        # a link inside the bar is not under it
        for key, _scope, bar_cls, _var in self.BARS:
            url = trip_url(key)
            for node in [n for n in self.nodes(url, cls=bar_cls)[0].walk() if focusable(n)]:
                with self.subTest(page=key, node=repr(node)[:80]):
                    self.assertIn(computed(node, 'scroll-margin-top', self.rules, env()), ('0', '0px'))

    def test_html_scroll_padding_still_clears_the_header(self):
        html_ = page_doc(trip_url('journal')).find('html')
        value = computed(html_, 'scroll-padding-top', self.rules, env())
        self.assertIn('var(--header-h)', value or '')


# ---------------------------------------------------------------- D5: a short viewport

class ShortViewportTests(SiteFixture):

    def test_the_day_nav_is_not_sticky_on_a_viewport_under_480_px_high(self):
        bar = self.nodes(trip_url('tour'), cls='mul-dnav')[0]
        for width, height, want in ((390, 844, 'sticky'), (1300, 900, 'sticky'), (844, 481, 'sticky'), (844, 480, 'static'),
                                    (844, 390, 'static'), (667, 375, 'static'), (1300, 400, 'static')):
            with self.subTest(width=width, height=height):
                self.assertEqual(computed(bar, 'position', self.rules, env(width, height)), want)

    def test_multiday_css_unsticks_it_in_a_max_height_query(self):
        rules = parse_css(source('css', 'pages', 'multiday.css'))[0]
        short = [r for r in rules if r.selector == '.mul-dnav' and 'position' in r.decls and any('max-height' in q for q in r.media)]
        self.assertEqual(len(short), 1)
        self.assertEqual(short[0].decls['position'][0], 'static')
        self.assertEqual(len(short[0].media), 1)
        limit = px(re.match(r'^\(\s*max-height\s*:\s*([^)]+)\)$', short[0].media[0]).group(1))
        self.assertTrue(470 <= limit <= 480, short[0].media)
        base = [r for r in rules if r.selector == '.mul-dnav' and 'position' in r.decls and not r.media]
        self.assertEqual([r.decls['position'][0] for r in base], ['sticky'])
        self.assertGreater(short[0].order, base[0].order)        # equal weight: the later rule is the one that holds

    def test_the_journals_month_bar_is_not_touched(self):
        bar = self.nodes(trip_url('journal'), cls='ser-mnav')[0]
        for height in (844, 480, 375):
            self.assertEqual(computed(bar, 'position', self.rules, env(844, height)), 'sticky')


# ---------------------------------------------------------------- D7: 44 px targets

class TargetSizeTests(SiteFixture):

    def assertTargets(self, url, nodes, block=True, inline=False, widths=WIDTHS):
        self.assertTrue(nodes, 'nothing to measure on %s' % url)
        for width in widths:
            e = env(width)
            for node in nodes:
                with self.subTest(page=url, width=width, node=repr(node)[:80]):
                    if block:
                        high = min_block(node, self.rules, e)
                        self.assertIsNotNone(high, 'no height or min-height for %r (%s; %s)'
                                             % (node, why(node, 'height', self.rules, e), why(node, 'min-height', self.rules, e)))
                        self.assertGreaterEqual(high, 44, '%r is %g px high' % (node, high))
                    if inline:
                        wide = min_inline(node, self.rules, e)
                        self.assertIsNotNone(wide, 'no width or min-width for %r' % node)
                        self.assertGreaterEqual(wide, 44, '%r is %g px wide' % (node, wide))

    def test_filter_chips_the_all_radio_among_them(self):
        # 'All' is the short one: 14 px of padding each side of three letters came to under 44 px
        for url, within, least in (('trips/', 'trx-acts', 4), ('tick-list/', 'trx-acts', 6), ('map/', 'arc-filt', 4)):
            chips = self.nodes(url, cls='fchip', tag='button', within=within)
            self.assertGreaterEqual(len(chips), least, url)
            self.assertEqual(len([c for c in chips if c['data-filter'] == 'all']), 1, url)
            self.assertTargets(url, chips, inline=True)

    # Targets that reach 44 x 44 px without a box of the page changing: the control keeps the size it had before the
    # phase, and a pseudo-element of it, transparent and out of the layout, answers the presses around it. What the
    # reader can check is the arithmetic of each one; that nothing moved was measured in a browser against screenshots
    # taken before the phase.

    def hit_box(self, node, base_w, base_h, e):
        """(width, height, reach left, right, up, down) of the element's absolutely positioned ::before hit area, for an
        element base_w x base_h px. The element has to be its containing block (position: relative)."""
        self.assertEqual(computed(node, 'position', self.rules, e), 'relative', why(node, 'position', self.rules, e))
        self.assertEqual(computed_pseudo(node, 'before', 'position', self.rules, e), 'absolute')
        self.assertEqual(computed_pseudo(node, 'before', 'content', self.rules, e), '""')
        for prop in ('background', 'background-color', 'border', 'width', 'height', 'display', 'pointer-events', 'z-index'):
            self.assertIsNone(computed_pseudo(node, 'before', prop, self.rules, e), '%s on the hit area of %r' % (prop, node))
        raw = [v for v in split_top(computed_pseudo(node, 'before', 'inset', self.rules, e) or '', ' ') if v.strip()]
        self.assertIn(len(raw), (1, 2, 3, 4), 'no inset on the hit area of %r' % node)
        top, right = raw[0], raw[1] if len(raw) > 1 else raw[0]
        bottom, left = raw[2] if len(raw) > 2 else top, raw[3] if len(raw) > 3 else right
        # a longhand that wins over the shorthand (the first segment's `left`)
        short = [r for r in self.rules if 'inset' in r.decls and r.parts is not None and ('pe', 'before') in r.parts[-1][1]
                 and all(media_matches(q, e) for q in r.media)
                 and matches(node, r.parts[:-1] + [(r.parts[-1][0], [x for x in r.parts[-1][1] if x[0] != 'pe'])])]
        best = max(short, key=lambda r: _key(r, 'inset'))
        for name in ('top', 'right', 'bottom', 'left'):
            longs = [r for r in self.rules if name in r.decls and r.parts is not None and ('pe', 'before') in r.parts[-1][1]
                     and all(media_matches(q, e) for q in r.media)
                     and matches(node, r.parts[:-1] + [(r.parts[-1][0], [x for x in r.parts[-1][1] if x[0] != 'pe'])])]
            if longs:
                long_ = max(longs, key=lambda r: _key(r, name))
                self.assertGreater(_key(long_, name), _key(best, 'inset'), 'the `%s` of %s loses to the inset of %s' % (name, long_.selector, best.selector))
                if name == 'top':
                    top = long_.decls[name][0]
                elif name == 'right':
                    right = long_.decls[name][0]
                elif name == 'bottom':
                    bottom = long_.decls[name][0]
                else:
                    left = long_.decls[name][0]
        up, down = side(top, base_h), side(bottom, base_h)
        to_right, to_left = side(right, base_w), side(left, base_w)
        for v in (up, down, to_right, to_left):
            self.assertIsNotNone(v, 'an inset of the hit area of %r is not a length this file can read: %s' % (node, (top, right, bottom, left)))
            self.assertLessEqual(v, 0, 'the hit area of %r is smaller than the control' % node)
        return base_w - to_left - to_right, base_h - up - down, -to_left, -to_right, -up, -down

    def assertSizeUntouched(self, node, e, allowed=()):
        """The control's own rule gives it no size beyond what it had: nothing that would move its neighbours."""
        for prop in ('min-width', 'width', 'max-width', 'margin', 'margin-inline', 'margin-left', 'margin-right', 'border', 'border-block'):
            if prop not in allowed:
                # nothing, or the reset every <button> gets (margin: 0; border: 0)
                self.assertIn(computed(node, prop, self.rules, e), (None, '0'), why(node, prop, self.rules, e))

    def test_year_and_region_browse_links(self):
        # 44 px high as before. Not 44 px wide by min-width: that moved the years from a pitch of 48 px (50 from 760) to 60.
        # A link under 44 px wide gets a hit area wider than itself by the same amount on each side.
        links = self.nodes('trips/', tag='a', within='trx-bgroup')
        hrefs = [a['href'] for a in links]
        years = [a for a in links if (a['href'] or '').startswith('#y')]
        self.assertGreaterEqual(len(years), 2, hrefs)
        self.assertTrue(any('map/#region-' in h for h in hrefs), hrefs)                # a region
        self.assertTargets('trips/', links, widths=(320,) + WIDTHS)                     # the height: a real box, as it always was
        for width in (320,) + WIDTHS:
            e = env(width)
            lists = {id(a.parent.parent): a.parent.parent for a in links}
            gaps = {computed(ul, 'column-gap', self.rules, e) for ul in lists.values()}
            self.assertEqual(gaps, {'16px'})
            for a in links:
                with self.subTest(width=width, link=a.text()):
                    self.assertEqual(a.parent.tag, 'li')
                    self.assertSizeUntouched(a, e)
                    self.assertIsNone(computed(a, 'padding', self.rules, e))
                    self.assertIsNone(computed(a, 'justify-content', self.rules, e))
                    # whatever the words are wide, the area is 44 px or the link itself, and as high as the link
                    for words in (20.0, 28.0, 32.1, 34.4, 43.8, 44.0, 130.6):
                        wide, high, left, right, up, down = self.hit_box(a, words, 44.0, e)
                        self.assertAlmostEqual(wide, max(words, 44.0))
                        self.assertEqual((high, up, down), (44.0, 0.0, 0.0))
                        self.assertAlmostEqual(left, right)
                    # A year is the narrowest link: four digits, 32.1 px at 14 px and 34.4 px at 15 px (measured in
                    # Chrome). Two of them side by side reach 6 px each into the 16 px between them: no overlap.
                    # That holds for any two links of 28 px or more.
                    for words in (28.0, 32.1, 34.4):
                        reach = self.hit_box(a, words, 44.0, e)[2]
                        self.assertLessEqual(2 * reach, 16.0)

    def test_the_also_links_of_the_home_page(self):
        # The same rule as the browse links: 44 px high as a real box, and never 44 px wide by min-width (that widened a
        # short link and pushed the ones after it). A link under 44 px gets a hit area wider than itself on both sides.
        links = self.nodes('', tag='a', within='hom-also')
        self.assertTrue(links)
        self.assertTargets('', links, widths=(320,) + WIDTHS)
        for width in (320,) + WIDTHS:
            e = env(width)
            lists = {id(a.parent.parent): a.parent.parent for a in links}
            gaps = {computed(ul, 'column-gap', self.rules, e) for ul in lists.values()}
            self.assertEqual(gaps, {'20px'})
            for a in links:
                with self.subTest(width=width, link=a.text()):
                    self.assertEqual(a.parent.tag, 'li')
                    self.assertSizeUntouched(a, e)
                    for words in (20.0, 30.0, 41.7, 44.0, 130.6):
                        wide, high, left, right, up, down = self.hit_box(a, words, 44.0, e)
                        self.assertAlmostEqual(wide, max(words, 44.0))
                        self.assertEqual((high, up, down), (44.0, 0.0, 0.0))
                        self.assertAlmostEqual(left, right)
                    # two links of 24 px or more, side by side, stop short of each other in the 20 px between them
                    self.assertLessEqual(2 * self.hit_box(a, 24.0, 44.0, e)[2], 20.0)

    def test_the_view_switch(self):
        # The switch is 44 px high with its border, like the chips and selects in its row (46 px pushed the row and all
        # under it down), so a button is 42 px: its hit area takes in the 1 px line above and below.
        for url in ('trips/', 'tick-list/'):
            buttons = self.nodes(url, tag='button', within='trx-view')
            self.assertEqual([b['data-view'] for b in buttons], ['cards', 'list'])
            box = buttons[0].parent
            self.assertIn('trx-view', box.classes)
            beside = self.nodes(url, cls='fchip', tag='button') + self.nodes(url, tag='select')
            for width in (320,) + WIDTHS:
                e = env(width)
                with self.subTest(page=url, width=width):
                    self.assertEqual(computed(box, 'height', self.rules, e), '44px', why(box, 'height', self.rules, e))
                    self.assertEqual(computed(box, 'border', self.rules, e).split()[0], '1px')
                    self.assertIsNone(computed(box, 'padding', self.rules, e))
                    self.assertIsNone(computed(box, 'overflow', self.rules, e))               # the area over the border is not clipped
                    for node in beside:
                        self.assertEqual(computed(node, 'height', self.rules, e), '44px')
                    for b in buttons:
                        self.assertEqual(min_block(b, self.rules, e), 42.0)                   # 44 less the two lines
                        self.assertEqual(computed(b, 'height', self.rules, e), '100%')
                        self.assertSizeUntouched(b, e)
                        for words in (69.7, 84.0):
                            wide, high, left, right, up, down = self.hit_box(b, words, 42.0, e)
                            self.assertEqual((wide, high), (words, 44.0))
                            self.assertEqual((left, right, up, down), (0.0, 0.0, 1.0, 1.0))  # the lines of the frame, no further

    def test_season_and_type_radios_of_the_section_pages(self):
        # A segment is 42 px high inside the frame's 1 px lines, as before the phase (44 px made the strip 46 px, 1 px
        # proud of its band each way and 2 px taller on a phone): its hit area takes in the two lines. 'All' is 37.6 px
        # wide on a phone: its area also reaches left, over the frame's line and into the page margin, to 44 px.
        for url in ('ski/', 'other/'):
            segs = [a for a in self.nodes(url, cls='sec-seg-a', tag='a')]
            self.assertGreaterEqual(len(segs), 3)
            strip = segs[0].parent
            self.assertEqual((segs[0]['data-filter'], strip.elements()[0] is segs[0]), ('all', True))
            self.assertEqual(len([a for a in segs if a['data-filter'] == 'all']), 1, url)
            for width in (320,) + WIDTHS:
                e = env(width)
                with self.subTest(page=url, width=width):
                    self.assertEqual(computed(strip, 'border', self.rules, e).split()[0], '1px')
                    self.assertIsNone(computed(strip, 'overflow', self.rules, e))
                    # the band has room for the strip and no more: 64 px, less its padding, is 42 px and the two lines
                    band = strip.parent
                    self.assertIn('sec-band-in', band.classes)
                    self.assertEqual(computed(band, 'min-height', self.rules, e), '64px')
                    for a in segs:
                        self.assertEqual(computed(a, 'min-height', self.rules, e), '42px', why(a, 'min-height', self.rules, e))
                        self.assertSizeUntouched(a, e)
                        self.assertEqual(computed(a, 'justify-content', self.rules, e), 'center' if width < 760 else None)
                        first = a is segs[0]
                        for words in (37.6, 49.6, 70.6, 103.6):
                            wide, high, left, right, up, down = self.hit_box(a, words, 42.0, e)
                            self.assertEqual((high, up, down), (44.0, 1.0, 1.0))
                            self.assertEqual(right, 0.0)                                       # never into the next segment
                            self.assertAlmostEqual(wide, max(words, 44.0) if first else words)
                            self.assertAlmostEqual(left, max(0.0, 44.0 - words) if first else 0.0)
                    # on a phone the page margin is the room 'All' reaches into: 6.4 px of 16
                    if width < 760:
                        self.assertEqual(computed(band, 'padding-inline', self.rules, e), 'var(--m)')
                        self.assertGreaterEqual(px(computed(page_doc(url).find('html'), '--m', self.rules, e)), 44.0 - 37.6 + 1)

    def test_the_footer_brand(self):
        # The name is one 24 px line that fills its column, as before the phase (min-height: 44px made every footer 20 px
        # taller). Its hit area is a block of the link itself whose margins take its height back, so nothing is
        # positioned (position: relative on this link redraws the name's edges at 1x) and no box changes.
        for url in sorted(self.pages):
            foot = page_doc(url).find('footer', cls='site-f')
            self.assertIsNotNone(foot, url)
            brand = [a for a in foot.find_all('a') if inside(a, 'f-brand')]
            self.assertEqual(len(brand), 1, url)
            if url not in ('', 'trips/', trip_url('story'), '404.html'):
                continue
            a = brand[0]
            holder = a.parent
            self.assertEqual((holder.elements()[0] is a, len(holder.elements())), (True, 2))          # the name, then one line
            under = holder.elements()[1]
            self.assertFalse(focusable(under))                    # a line of text: nothing of its own to press
            self.assertEqual([n for n in under.walk() if focusable(n)], [])
            for width in (320,) + WIDTHS:
                e = env(width)
                with self.subTest(page=url, width=width):
                    # the link is the box it was: a stretched item of a flex column, one line high
                    self.assertEqual((computed(holder, 'display', self.rules, e), computed(holder, 'flex-direction', self.rules, e)), ('flex', 'column'))
                    for prop in ('min-height', 'height', 'display', 'align-self', 'position', 'padding', 'padding-block'):
                        self.assertIsNone(computed(a, prop, self.rules, e), why(a, prop, self.rules, e))
                    self.assertSizeUntouched(a, e)
                    line = line_height(a, self.rules, e)
                    self.assertEqual(line, 24.0)
                    # the hit area: an in-flow block of the link, 44 px high, that adds nothing to the link's height
                    self.assertEqual(computed_pseudo(a, 'before', 'content', self.rules, e), '""')
                    self.assertEqual(computed_pseudo(a, 'before', 'display', self.rules, e), 'block')
                    for prop in ('position', 'float', 'background', 'width', 'inset'):
                        self.assertIsNone(computed_pseudo(a, 'before', prop, self.rules, e))
                    high = px(computed_pseudo(a, 'before', 'height', self.rules, e))
                    up, right, down, left = (-v for v in sides(computed_pseudo(a, 'before', 'margin', self.rules, e)))
                    self.assertGreaterEqual(high, 44)
                    self.assertEqual((left, right), (0.0, 0.0))
                    self.assertEqual(up + down, high, 'the margins do not take back the height: the name would move')
                    # above: inside the footer's own padding. Below: the name's line, then no further than the gap to
                    # the line under it, so a press on that line is not the link's
                    below = high - up - line
                    self.assertGreater(up, 0)
                    self.assertGreaterEqual(below, 0)
                    inner = holder.parent
                    self.assertIn('site-f-in', inner.classes)
                    self.assertLessEqual(up, sides(computed(inner, 'padding', self.rules, e))[0])
                    self.assertLessEqual(below, px(computed(holder, 'gap', self.rules, e)))

    def test_a_card_covers_picture_wrapper_has_no_box(self):
        # core.cover_img may put a card's cover inside <picture class="cover-pic"> (a phone-only <source>). The rules that
        # size the cover are written for an <img> in its link; with display: contents the picture has no box, so they
        # still hold. A rule that asked for the image as a direct child of something would stop matching.
        base = parse_css(source('css', 'base.css'))[0]
        rule = [r for r in base if r.selector == 'picture.cover-pic']
        self.assertEqual([(r.decls, r.media) for r in rule], [({'display': ('contents', False)}, ())])
        for holder, cls in (('tcard-img', 'cover-img'), ('hom-card-img', 'cover-img')):
            d = Doc('<a class="%s" href="#"><picture class="cover-pic"><source media="(max-width: 559.98px)" srcset="x.th.webp 600w">'
                    '<img class="%s" src="x.webp" alt=""></picture></a>' % (holder, cls))
            pic, img = d.find('picture'), d.find('img')
            for width in (390, 800, 1300):
                e = env(width)
                self.assertEqual(computed(pic, 'display', self.rules, e), 'contents')
                self.assertEqual(computed(img, 'display', self.rules, e), 'block')              # the cover's own rule still reaches it
                self.assertEqual(computed(img, 'width', self.rules, e), '100%')
                self.assertEqual(computed(img, 'object-fit', self.rules, e), 'cover')

        def direct(rule):
            """True when the selector asks for an <img> (or .cover-img) as the direct child of something."""
            def names(simples):
                out = []
                for s in simples:
                    if s[0] in ('tag', 'cls'):
                        out.append(s[1])
                    elif s[0] == 'pc' and s[1] in ('is', 'where'):
                        out += [n for alt in s[2] for n in names(alt[-1][1])]
                return out
            return any(comb == '>' and ({'img', 'cover-img', 'picture'} & set(names(simples))) for comb, simples in rule.parts or [])

        found = sorted({r.selector for r in self.rules if direct(r)})
        # the one there is: the track glyph of a phone row (core.glyph, never a cover, never in a <picture>)
        self.assertEqual(found, ['.prow a > :is(svg, img):first-child'])
        self.assertEqual([r.selector for r in self.rules if re.search(r'cover-img\s*[+~]|[+~]\s*\.?(?:cover-img|img)\b', r.selector)], [])
        for url in sorted(self.pages):
            for pic in page_doc(url).find_all('picture'):
                self.assertEqual(pic['class'], 'cover-pic', url)
                self.assertEqual([n.tag for n in pic.elements()][-1], 'img')
                self.assertFalse(inside(pic, 'prow'))

    def test_the_other_footer_and_header_links_were_44_px_already(self):
        foot = page_doc('').find('footer', cls='site-f')
        self.assertTargets('', [a for a in foot.find_all('a') if inside(a, 'f-nav')])
        head = page_doc('').find('header', cls='site-h')
        self.assertTargets('', head.find_all('button', cls='menu-btn'), inline=True)

    def test_a_breadcrumb_links_hit_area_is_44_px_high_and_moves_nothing(self):
        # The link is a 16 px line of text (18 px from 760). Its ::before is the hit area: out of the flow, so the text
        # stays where it is. It may not reach into the next crumb's area (half the gap each side at most), not under
        # the header (the padding above the crumbs), and not into the hit area of the chip link under it on a report.
        seen = 0
        for url, holder in (('ski/', 'sec-head'), ('other/', 'sec-head'), (trip_url('story'), 'rep-title'), (trip_url('goal'), 'rep-title'),
                            (trip_url('tour'), 'rep-title'), (trip_url('journal'), 'rep-title')):
            crumbs = self.nodes(url, cls='crumbs', tag='nav')[0]
            links = crumbs.find_all('a')
            self.assertTrue(links, url)
            box = crumbs.parent
            self.assertIn(holder, box.classes)
            self.assertIs(box.elements()[0], crumbs)                 # nothing between the crumbs and the top of their block
            for width in (320,) + WIDTHS:
                e = env(width)
                if not displayed(crumbs, self.rules, e):
                    self.assertEqual((holder, width < 760), ('rep-title', True))       # a report's crumbs are off on a phone
                    continue
                for a in links:
                    with self.subTest(page=url, width=width, link=a.text()):
                        seen += 1
                        self.assertEqual(computed(a, 'position', self.rules, e), 'relative')
                        self.assertEqual(computed_pseudo(a, 'before', 'position', self.rules, e), 'absolute')
                        self.assertEqual(computed_pseudo(a, 'before', 'content', self.rules, e), '""')
                        reach = sides(computed_pseudo(a, 'before', 'inset', self.rules, e))
                        self.assertIsNotNone(reach, computed_pseudo(a, 'before', 'inset', self.rules, e))
                        up, right, down, left = (-v for v in reach)
                        line = line_height(crumbs, self.rules, e)
                        self.assertIn(line, (16.0, 18.0))
                        self.assertGreaterEqual(up + line + down, 44, 'the hit area is %g px high' % (up + line + down))
                        # the visible text is where it was: the link itself gets no size, padding or margin
                        for prop in ('padding', 'padding-block', 'margin', 'margin-block', 'min-height', 'height', 'display', 'line-height', 'font'):
                            self.assertIsNone(computed(a, prop, self.rules, e), why(a, prop, self.rules, e))
                        # two crumbs' areas do not overlap
                        self.assertEqual(computed(crumbs, 'display', self.rules, e), 'flex')
                        self.assertLessEqual(left + right, px(computed(crumbs, 'gap', self.rules, e)))
                        self.assertGreaterEqual(min(left, right), 0)
                        # it stays below the header: the block's own padding is above the crumbs
                        self.assertLessEqual(up, px(computed(box, 'padding-top', self.rules, e)), why(box, 'padding-top', self.rules, e))
                        # and above the hit area of the link under it
                        after = box.elements()[1]
                        chip = after.find('a', cls='chip--title') if 'rep-chips' in after.classes else None
                        if holder == 'rep-title':
                            self.assertIsNotNone(chip, '%s has no chip link under its crumbs' % url)
                            chip_up = -sides(computed_pseudo(chip, 'before', 'inset', self.rules, e))[0]
                            space = px(computed(after, 'margin-top', self.rules, e))
                            self.assertLessEqual(down + chip_up, space, 'the crumb reaches %g px down, the chip %g px up, %g px apart' % (down, chip_up, space))
                        else:
                            self.assertEqual([n for n in [after] + list(after.walk()) if focusable(n)], [])     # a heading: nothing to press
        self.assertGreater(seen, 40)

    def test_the_search_placeholder_is_cut_with_an_ellipsis(self):
        rules = parse_css(source('css', 'pages', 'trips.css'))[0]
        box = Doc('<form><input class="trx-q" type="search" placeholder="x"></form>').find('input')
        self.assertEqual(computed(box, 'text-overflow', rules, env(320)), 'ellipsis')
        ph = [r for r in rules if r.selector.replace(' ', '') == '.trx-q::placeholder' and 'text-overflow' in r.decls]
        self.assertEqual([r.decls['text-overflow'][0] for r in ph], ['ellipsis'])
        for url in ('trips/', 'tick-list/'):
            self.assertEqual(len(self.nodes(url, cls='trx-q', tag='input')), 1)

# ---------------------------------------------------------------- forced colours: the units switch

class ForcedColoursTests(SiteFixture):

    def forced(self, width):
        return dict(env(width), **{'forced-colors': 'active'})

    def buttons(self, url):
        """[(where, button)] of every units button of a page: 'header' (the nav's), 'menu', 'page' (the About page's own)."""
        out = []
        for b in page_doc(url).find_all('button'):
            if b['data-units'] and inside(b, 'units'):
                out.append(('page' if inside(b, 'abo-units') else 'menu' if inside(b, 'menu') else 'header', b))
        return out

    def test_the_fixture_has_each_switch_in_both_states(self):
        got = sorted((where, b['aria-checked']) for where, b in self.buttons('about/'))
        self.assertEqual(got, [(w, c) for w in ('header', 'menu', 'page') for c in ('false', 'true')])
        self.assertTrue(media_matches('(forced-colors: active)', self.forced(390)))
        self.assertFalse(media_matches('(forced-colors: active)', env(390)))

    def test_the_unselected_header_buttons_draw_no_bars(self):
        # Their 6 px transparent top and bottom borders (what makes a 32 px switch a 44 px target) are drawn in a system
        # colour in forced colours: two bars. Canvas is the colour of what they lie on.
        for url in ('', 'about/'):
            for where, b in self.buttons(url):
                for width in (390, 1300):
                    with self.subTest(page=url, where=where, checked=b['aria-checked'], width=width):
                        e, plain = self.forced(width), env(width)
                        self.assertIsNone(computed(b, 'border-block-color', self.rules, plain))       # nothing outside forced colours
                        own = where == 'page'
                        self.assertEqual(sides(computed(b, 'border-block', self.rules, e).split(' solid ')[0]), (1.0,) * 4 if own else (6.0,) * 4)
                        self.assertTrue(computed(b, 'border-block', self.rules, e).endswith(' solid transparent'))
                        if b['aria-checked'] == 'true':
                            # the selected one opts out of forced colours and is drawn in Highlight, as before
                            self.assertIsNone(computed(b, 'border-block-color', self.rules, e))
                            self.assertEqual(computed(b, 'forced-color-adjust', self.rules, e), 'none')
                            self.assertEqual(computed(b, 'background', self.rules, e), 'Highlight')
                            self.assertEqual(computed(b, 'color', self.rules, e), 'HighlightText')
                        elif own:
                            # the About page's 1 px borders lie on the frame's own lines: painting them over would cut it
                            self.assertIsNone(computed(b, 'border-block-color', self.rules, e))
                            self.assertIsNone(computed(b, 'forced-color-adjust', self.rules, e))
                        else:
                            self.assertEqual(computed(b, 'border-block-color', self.rules, e), 'Canvas', why(b, 'border-block-color', self.rules, e))
                            self.assertIsNone(computed(b, 'forced-color-adjust', self.rules, e))       # its text keeps the system colours
                            # the colour is the one that holds: no later or stronger `border-block` shorthand resets it
                            colour, short = winner(b, 'border-block-color', self.rules, e), winner(b, 'border-block', self.rules, e)
                            self.assertGreater(_key(colour, 'border-block-color'), _key(short, 'border-block'))

    def test_the_rule_follows_the_state_not_the_markup_as_shipped(self):
        # base.js flips aria-checked when the visitor switches: the other button is then the unselected one
        d = Doc('<header class="site-h"><div class="units"><button role="radio" aria-checked="false" data-units="mi">MI</button>'
                '<button role="radio" aria-checked="true" data-units="km">KM</button></div></header>')
        mi, km = d.find_all('button')
        e = self.forced(1300)
        self.assertEqual(computed(mi, 'border-block-color', self.rules, e), 'Canvas')
        self.assertIsNone(computed(km, 'border-block-color', self.rules, e))
        self.assertEqual(computed(km, 'background', self.rules, e), 'Highlight')


# ---------------------------------------------------------------- a report without a phone bar: no room kept for one

class FooterRoomTests(SiteFixture):

    PAGE = '<html><body class="%s"><main id="main"><p>x</p></main>%s<footer class="site-f"><div class="site-f-in">y</div></footer></body></html>'
    BAR = '<nav class="bbar" aria-label="Report sections" style="--n:2"><a href="#a">A</a><a href="#b">B</a></nav>'

    def room(self, body_cls, bar, width):
        foot = Doc(self.PAGE % (body_cls, self.BAR if bar else '')).find('footer')
        return computed(foot, 'padding-bottom', self.rules, env(width))

    def test_the_footer_keeps_room_for_the_bar_only_when_the_page_has_one(self):
        for body_cls in ('p-report', 'p-report p-report--story', 'p-report p-goal'):
            with self.subTest(body=body_cls):
                self.assertEqual(self.room(body_cls, True, 390), '72px')
                self.assertEqual(self.room(body_cls, True, 759), '72px')
                self.assertEqual(self.room(body_cls, False, 390), '0')        # report.bottom_bar wrote no bar: fewer than two items
                self.assertEqual(self.room(body_cls, False, 759), '0')
                for bar in (True, False):
                    self.assertEqual(self.room(body_cls, bar, 760), '0')      # the bar is a phone's
                    self.assertEqual(self.room(body_cls, bar, 1300), '0')
        for body_cls in ('p-trips', 'p-home', 'p-section'):                    # report.css says nothing about other pages
            self.assertIsNone(self.room(body_cls, False, 390))

    def test_every_report_and_goal_page_of_the_fixture(self):
        with_bar = without = 0
        for url in sorted(self.pages):
            doc = page_doc(url)
            body = doc.find('body')
            if 'p-report' not in body.classes:
                continue
            bar = doc.find('nav', cls='bbar')
            foot = doc.find('footer', cls='site-f')
            with self.subTest(page=url):
                self.assertEqual(computed(foot, 'padding-bottom', self.rules, env(390)), '72px' if bar is not None else '0',
                                 why(foot, 'padding-bottom', self.rules, env(390)))
                self.assertEqual(computed(foot, 'padding-bottom', self.rules, env(800)), '0')
                if bar is not None:
                    self.assertGreaterEqual(len(bar.find_all('a')), 2)       # one link is not navigation
            with_bar += bar is not None
            without += bar is None
        self.assertGreaterEqual(with_bar, 6)
        self.assertGreaterEqual(without, 1)          # the idea: a goal with nothing to jump to

    def test_a_browser_without_has_keeps_the_room(self):
        # :has() in a selector list would take the whole rule with it in a browser that cannot read it: the rule that
        # clears the room stands alone, and the 72 px rule does not use :has()
        rules = parse_css(source('css', 'pages', 'report.css'))[0]
        room = [r for r in rules if r.selector.endswith('.site-f') and 'padding-bottom' in r.decls]
        self.assertEqual([(r.selector, r.decls['padding-bottom'][0], r.media) for r in room],
                         [('body.p-report .site-f', '72px', ()),
                          ('body.p-report:not(:has(.bbar)) .site-f', '0', ()),
                          ('body.p-report .site-f', '0', ('(min-width: 760px)',))])
        clearing = room[1]
        self.assertEqual([r.selector for r in rules if r.order == clearing.order], [clearing.selector])
        self.assertEqual(clearing.decls, {'padding-bottom': ('0', False)})
        self.assertGreater(clearing.spec, room[0].spec)                # it wins wherever it stands in the file
        self.assertNotIn('p-goal', ' '.join(r.selector for r in room))      # one rule for reports and goals: a goal page is p-report too


if __name__ == '__main__':
    unittest.main()
