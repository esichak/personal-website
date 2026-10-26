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
  D4  map cluster markers                base.js gives focus listeners to map pins, and to a .mk-cluster element only
                                         under a flag that names it first (aria-hidden off, role=button, aria-label) and
                                         holds only beside a list with rows (Phase 12, qa-02); an unnamed cluster (the
                                         home page's) gets none and no tab stop
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
  P5  region pages (contract-phase5.md   the fixture builds two; with scripting off the links into the Trips explorer
      section 5, as revised in round 2)  (.reg-x) are not displayed and nothing else of the page goes; the region name on
                                         the home page (.hom-reg-n a) is a 44 px inline-block of its own (padding taken
                                         back by margins, Phase 13C), so no box changes, and lies above the count
                                         line (z-index); the Map page's panel link (.arc-reg-a) and the 'Other regions'
                                         links are 44 px; the breadcrumb has its room, and the short 'Map' crumb answers
                                         over 44 px of width (10.5 px each side at most, 4 px for a crumb of 44 px or
                                         more); the list's 'Show all' button (.arc-all-btn) is hidden as generated,
                                         44 px high once shown, with its two margins; the Featured cards keep the
                                         cover rules and their phone source declares 106 px
  R3  region pages, round 3              from 1200 px, where the caption of a home page map is one line, the region
                                         name's hit area sits 2 px higher (16 px above, 12 px below, 44 px as before)
                                         and ends inside the caption's own padding, above the map; a place in a region
                                         page's head may break inside a word too long for a line (.reg-stats .mi-w)
                                         and still wraps at its spaces first (base.css); base.js dims a map (is-hl)
                                         only when a track, a pin or a cluster marker matched the keys, so a list row
                                         the map does not draw leaves it alone; archive.js scrolls the 'Show fewer'
                                         button into view when its list closes, and only then, and opening a list
                                         still focuses the first row it reveals

The CSS side uses a small reader written for this file (parse_css, matches, computed): selector -> declarations with
the rules inside @media blocks, a selector matcher over the helpers.Doc tree, specificity and source order, and media
queries evaluated for a viewport and for scripting on or off. It reads the stylesheet build.css_bundle() publishes, in
bundle order. It is not a browser: it knows the selectors and media features these stylesheets use (ReaderTests pins
that it can read every selector in them), it does not inherit, and it reports declared values, not used ones.

The JavaScript side is a block-level reading, not an interpreter: a scanner that knows comments, strings and regular
expression literals finds the callback wired over the marker selector (and the one over [data-filter-nav]) by matching
braces, then looks at each addEventListener / setAttribute call in it and at the `if` conditions around that call.
The shapes it accepts are listed at marker_focus(), map_dimming(), show_all_press() and Script.guards(); a rewrite into
another shape fails the test and has to be read by a person, which is the intent.

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

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

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


def pseudo_winner(node, pseudo, prop, rules, e):
    """The rule whose declaration of `prop` wins the cascade for the element's pseudo-element (see computed_pseudo), or
    None: for comparing two declarations of one pseudo-element in the cascade (_key)."""
    best = None
    for r in (rules.declaring(prop) if isinstance(rules, Sheet) else rules):
        if prop not in r.decls or r.parts is None or ('pe', pseudo) not in r.parts[-1][1]:
            continue
        own = r.parts[:-1] + [(r.parts[-1][0], [x for x in r.parts[-1][1] if x[0] != 'pe'])]
        if not all(media_matches(q, e) for q in r.media) or not matches(node, own):
            continue
        if best is None or _key(r, prop) >= _key(best, prop):
            best = r
    return best


_WIDEN = re.compile(r'^min\(\s*(-\d+(?:\.\d+)?)px\s*,\s*\(\s*100%\s*-\s*(\d+(?:\.\d+)?)px\s*\)\s*/\s*2\s*\)$')


def widen(value, base):
    """One inline side of a hit area declared as `min(-Apx, (100% - Npx) / 2)`, for a box `base` px across, in px (a
    negative inset reaches outside the box): half of what the box lacks of N, and at least A px whatever the box is.
    None for any other value (side() reads the forms without a floor)."""
    m = _WIDEN.match((value or '').strip())
    if m is None:
        return None
    return min(float(m.group(1)), (base - float(m.group(2))) / 2)


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
        of the statement itself, ('else', condition) for the else block of an `if (condition)`, and for a statement that
        stands right after the `else` of an `if (condition) { ... }` without braces of its own. Loops, functions and
        other blocks add nothing; an `else` after an `if` that has no braces is not read."""
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
        elif i >= start and self.text[i] == '}' and re.match(r'^\s*else\s*$', self.text[i + 1:pos]):
            # `if (condition) { ... } else <statement>`: the else branch, without braces
            k = self.before(self.open(i))
            if k >= 0 and self.text[k] == ')' and self.code(k):
                opening = self.open(k)
                if re.search(r'\bif\s*$', self.text[:opening]):
                    out.append(('else', self.text[opening + 1:k]))
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


def disjuncts(cond):
    """The terms of a condition split at each `||` outside every bracket and string (one term when it has none)."""
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
            out.append(cond[start:i].strip())
            i = start = i + 2
            continue
        i += 1
    out.append(cond[start:].strip())
    return out


def naming_flag(js, el, flag, start, end):
    """Rule D4 as revised in Phase 12 (qa-02): the expression a flag that names a cluster marker is declared with, or None
    when `flag` is not such a flag. In the loop body [start, end) the flag is a plain variable declared once
    (`var|let|const <flag> = <expr>;`) and never assigned again, and its own `if (<flag>) { ... }` block, with no other
    condition around the calls, takes aria-hidden off the marker and names it as a button:
    <el>.removeAttribute('aria-hidden'), <el>.setAttribute('role', 'button') and <el>.setAttribute('aria-label', ...)."""
    if not re.match(r'^[A-Za-z_$][\w$]*$', flag):
        return None
    f, e, body = re.escape(flag), re.escape(el), js.text[start:end]
    decl = [m for m in re.finditer(r'(?<![\w$.])(?:var|let|const)\s+%s\s*=\s*([^;]+);' % f, body) if js.code(start + m.start())]
    assigned = [m for m in re.finditer(r'(?<![\w$.])%s\s*(?:\|\||&&|[-+*/%%|&^])?=(?!=)' % f, body) if js.code(start + m.start())]
    if len(decl) != 1 or len(assigned) != 1:          # the declaration's own '=' is the one assignment
        return None
    for pattern in (r'''(?<![\w$.])%s\.removeAttribute\(\s*['"]aria-hidden['"]\s*\)''' % e,
                    r'''(?<![\w$.])%s\.setAttribute\(\s*['"]role['"]\s*,\s*['"]button['"]\s*\)''' % e,
                    r'''(?<![\w$.])%s\.setAttribute\(\s*['"]aria-label['"]\s*,''' % e):
        if not any(js.code(start + m.start()) and [(k, c.strip()) for k, c in js.guards(start + m.start(), start)] == [('if', flag)]
                   for m in re.finditer(pattern, body)):
            return None
    return decl[0].group(1).strip()


def marker_focus_flags(src):
    """marker_focus(src), and the set of (loop parameter, expression) of every flag (naming_flag) that lets a focus
    listener reach the cluster markers it names."""
    js = Script(src)
    got = {'pin': set(), 'cluster': set(), 'named': set()}
    flags = set()
    for selector, el, start, end in js.each_callbacks(lambda s: '.mk-pin' in s or '.mk-cluster' in s):
        for event, pos in js.listeners(el, start, end):
            if event not in FOCUS_EVENTS:
                continue
            conds = js.guards(pos, start)
            only_clusters = any(k == 'if' and _is_cluster(c, el) for k, c in conds)
            no_clusters = any((k == 'if' and _is_not_cluster(c, el)) or (k == 'else' and _is_cluster(c, el)) for k, c in conds)
            # an `if (a || b)` around the call: the terms that can hold for a cluster marker. When none can, the call
            # rules the clusters out; when each of them is a flag that names the marker, the call reaches named ones only
            named = None
            for k, c in conds:
                if k != 'if':
                    continue
                terms = [t for t in disjuncts(c) if not _is_not_cluster(t, el)]
                if not terms:
                    no_clusters = True
                    continue
                exprs = [naming_flag(js, el, t, start, end) for t in terms]
                if all(x is not None for x in exprs):
                    named = exprs
            if '.mk-pin' in selector and not only_clusters:
                got['pin'].add(event)
            if '.mk-cluster' in selector and not no_clusters:
                got['named' if named else 'cluster'].add(event)
                flags.update((el, x) for x in (named or []))
    return got, flags


def marker_focus(src):
    """Who gets focus listeners among the map markers of a script: {'pin': set of events, 'cluster': set of events,
    'named': set of events}.

    It reads every `querySelectorAll('<selector naming .mk-pin or .mk-cluster>').forEach(function (el) { ... })` and, in
    it, every `el.addEventListener('focus' | 'blur' | 'focusin' | 'focusout', ...)`. A listener reaches the pins when
    the selector names .mk-pin and no condition around the call holds for clusters only; it reaches the clusters when
    the selector names .mk-cluster and no condition around the call rules them out (see _is_cluster / _is_not_cluster;
    the else block of a clusters-only `if` rules them out as well). Of those, it reaches only the clusters the loop names
    ('named', not 'cluster') when an `if` around it holds for a cluster only through flags that name the marker
    (naming_flag: aria-hidden off, role=button, aria-label, in the flag's own block)."""
    return marker_focus_flags(src)[0]


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


def map_dimming(src):
    """What decides, in a script's `function highlight(map, keys) { ... }`, whether the map gets the class is-hl (the
    class that dims every track and pin the keys do not pick out). None when the script has not exactly one such
    function, or the function does not toggle the class exactly once; otherwise a dict:

      arg      the second argument of `<map>.classList.toggle('is-hl', <arg>)`, as written
      flag     that argument when it is a variable the function declares as `var <flag> = false;` before its loops and
               the call stands after every loop (it then sees the flag as the loops left it); else None
      raised   one tuple of selectors per `<map>.querySelectorAll('<selectors>').forEach(function (el) { ... })` loop
               that raises the flag for an element the keys matched, in source order. Such a loop gives the element
               its own highlight with a variable, `el.classList.toggle('hl', <on>)`, and raises the flag with that same
               variable: `<flag> = <flag> || <on>;`, `<flag> = <on> || <flag>;` or `if (<on>) <flag> = true;`
      tests    {the tuple of selectors: the expression <on> is declared with}, for those loops
      other    every other assignment to the flag in the function, up to its semicolon: a place where something else
               than a match could set it
    """
    js = Script(src)
    heads = [m for m in re.finditer(r'(?<![\w$.])function\s+highlight\s*\(\s*([\w$]+)[^)]*\)\s*\{', js.text) if js.code(m.start())]
    if len(heads) != 1:
        return None
    map_ = re.escape(heads[0].group(1))
    start, end = heads[0].end(), js.close(heads[0].end() - 1)
    body = js.text[start:end]
    calls = [m for m in re.finditer(r'''(?<![\w$.])%s\.classList\.toggle\(\s*(['"])is-hl\1\s*,''' % map_, body) if js.code(start + m.start())]
    if len(calls) != 1:
        return None
    call = start + calls[0].start()
    arg = js.text[start + calls[0].end():js.close(js.text.index('(', call))].strip()
    out = {'arg': arg, 'flag': None, 'raised': [], 'tests': {}, 'other': []}
    if not re.match(r'^[A-Za-z_$][\w$]*$', arg):
        return out
    flag = re.escape(arg)
    loops = []
    for m in re.finditer(r'''(?<![\w$.])%s\.querySelectorAll\(\s*(['"])((?:(?!\1).)*)\1\s*\)\s*\.forEach\(\s*function\s*\(\s*([\w$]+)[^)]*\)\s*\{'''
                         % map_, body):
        if js.code(start + m.start()):
            loops.append((tuple(s.strip() for s in split_top(m.group(2), ',')), m.group(3), start + m.end(), js.close(start + m.end() - 1)))
    declared = re.search(r'(?<![\w$.])(?:var|let)\s+%s\s*=\s*false\s*;' % flag, js.text[start:min([s for _sel, _el, s, _e in loops] + [call])])
    known = [(start + declared.start(), start + declared.end())] if declared else []
    for selectors, el, s, e in loops:
        inner = js.text[s:e]
        own = re.search(r'''(?<![\w$.])%s\.classList\.toggle\(\s*(['"])hl\1\s*,\s*([A-Za-z_$][\w$]*)\s*\)''' % re.escape(el), inner)
        if own is None:
            continue
        on = re.escape(own.group(2))
        up = re.search(r'(?<![\w$.])(?:%s\s*=\s*%s\s*\|\|\s*%s|%s\s*=\s*%s\s*\|\|\s*%s|if\s*\(\s*%s\s*\)\s*%s\s*=\s*true)\s*;'
                       % (flag, flag, on, flag, on, flag, on, flag), inner)
        if up is None:
            continue
        known.append((s + up.start(), s + up.end()))
        made = re.search(r'(?<![\w$.])(?:var|let|const)\s+%s\s*=\s*([^;]+);' % on, inner)
        out['raised'].append(selectors)
        out['tests'][selectors] = made.group(1).strip() if made else None
    for m in re.finditer(r'(?<![\w$.])%s\s*(?:\|\||&&|[-+*/%%|&^])?=(?!=)' % flag, body):
        pos = start + m.start()
        if js.code(pos) and not any(a <= pos < b for a, b in known):
            stop = js.text.find(';', pos, end)
            out['other'].append(js.text[pos:(stop + 1) if stop >= 0 else end].strip())
    if declared and all(e < call for _sel, _el, _s, e in loops):
        out['flag'] = arg
    return out


def show_all_press(src):
    """What a press of a 'Show all' button does in a script, read from its
    `querySelectorAll('.arc-all-btn').forEach(function (b) { ... b.addEventListener('click', function () { ... }); })`.
    None when the script has not exactly one such loop with exactly one click listener on the loop's element; otherwise
    a dict:

      button   the loop's parameter: the button
      list     the variable the loop declares as document.getElementById(<button>.getAttribute('aria-controls')), or None
      open     (variable, expression) of the listener's declaration that toggles a class of the list: what the press
               did to the list (None when the listener has none)
      scrolls  [(target, argument, guards)] of every `<target>.scrollIntoView(<argument>)` in the listener
      focuses  [(target, the expression the listener declares the target with or None, guards)] of every
               `<target>.focus(...)` in it

    guards: Script.guards() from the listener's own block, so the `if` and the `else` a call stands under in it."""
    js = Script(src)
    loops = js.each_callbacks(lambda s: s.strip() == '.arc-all-btn')
    if len(loops) != 1:
        return None
    _selector, button, start, end = loops[0]
    clicks = [m for m in re.finditer(r'''(?<![\w$.])%s\.addEventListener\(\s*(['"])click\1\s*,\s*function\s*\([^)]*\)\s*\{''' % re.escape(button),
                                     js.text[start:end]) if js.code(start + m.start())]
    if len(clicks) != 1:
        return None
    s = start + clicks[0].end()
    e = js.close(s - 1)
    body = js.text[s:e]

    def declared(name, text):
        m = re.search(r'(?<![\w$.])(?:var|let|const)\s+%s\s*=\s*([^;]+);' % re.escape(name), text)
        return m.group(1).strip() if m else None

    made = re.search(r'''(?<![\w$.])(?:var|let|const)\s+([\w$]+)\s*=\s*document\.getElementById\(\s*%s\.getAttribute\(\s*(['"])aria-controls\2\s*\)\s*\)\s*;'''
                     % re.escape(button), js.text[start:s])
    list_ = made.group(1) if made else None
    opened = re.search(r'(?<![\w$.])(?:var|let|const)\s+([\w$]+)\s*=\s*(%s\.classList\.toggle\([^;]*);' % re.escape(list_), body) if list_ else None
    scrolls, focuses = [], []
    for m in re.finditer(r'(?<![\w$.])([\w$]+)\.scrollIntoView\(', body):
        if js.code(s + m.start()):
            scrolls.append((m.group(1), js.text[s + m.end():js.close(s + m.end() - 1)].strip(), js.guards(s + m.start(), s)))
    for m in re.finditer(r'(?<![\w$.])([\w$]+)\.focus\(', body):
        if js.code(s + m.start()):
            focuses.append((m.group(1), declared(m.group(1), body), js.guards(s + m.start(), s)))
    return {'button': button, 'list': list_, 'open': (opened.group(1), opened.group(2).strip()) if opened else None,
            'scrolls': scrolls, 'focuses': focuses}


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

    def test_a_side_widened_to_a_least_size_with_a_floor(self):
        value = 'min(-4px, (100% - 44px) / 2)'
        for base, want in ((20.0, -12.0), (23.0, -10.5), (25.0, -9.5), (36.0, -4.0), (40.0, -4.0), (44.0, -4.0), (120.0, -4.0)):
            with self.subTest(base=base):
                self.assertEqual(widen(value, base), want)
                self.assertGreaterEqual(base - 2 * widen(value, base), 44.0)          # never under 44 px across
                self.assertEqual(base - 2 * widen(value, base), max(base + 8.0, 44.0))    # 44, or the box and the floor on both sides
        self.assertEqual(widen('min(-2.5px,(100% - 30px)/2)', 20.0), -5.0)
        self.assertEqual(widen('min(-2.5px,(100% - 30px)/2)', 28.0), -2.5)
        for other in ('min(0px, (100% - 44px) / 2)', 'min(4px, (100% - 44px) / 2)', 'max(-4px, (100% - 44px) / 2)', 'min(-4px, 100% - 44px)',
                      'min(-4px, (100% - 2em) / 2)', '-4px', '', None, 'calc((100% - 44px) / 2)'):
            self.assertIsNone(widen(other, 23.0), other)
        # pseudo_winner is the rule computed_pseudo reads the value from
        d = self.doc('<div class="h"><nav class="c"><a href="#">One</a></nav></div><nav class="c"><a href="#">Two</a></nav>')
        one, two = d.find_all('a')
        rules = parse_css('.c a::before { content: ""; inset: -21px -4px -7px; } .h .c a::before { inset-inline: %s; }'
                          ' @media (min-width: 760px) { .c a::before { inset-inline: -1px; } }' % value)[0]
        self.assertEqual(pseudo_winner(one, 'before', 'inset-inline', rules, env()).selector, '.h .c a::before')
        self.assertEqual(pseudo_winner(one, 'before', 'inset-inline', rules, env(800)).selector, '.h .c a::before')      # the more specific rule
        self.assertEqual(pseudo_winner(one, 'before', 'inset', rules, env()).selector, '.c a::before')
        self.assertIsNone(pseudo_winner(two, 'before', 'inset-inline', rules, env()))
        self.assertEqual(pseudo_winner(two, 'before', 'inset-inline', rules, env(800)).decls['inset-inline'][0], '-1px')
        self.assertEqual(computed_pseudo(one, 'before', 'inset-inline', rules, env()), value)
        self.assertGreater(_key(pseudo_winner(one, 'before', 'inset-inline', rules, env()), 'inset-inline'),
                           _key(pseudo_winner(one, 'before', 'inset', rules, env()), 'inset'))
        self.assertIsNone(pseudo_winner(one, 'after', 'inset', rules, env()))

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
            # a guard of pins only, written as a chain of `||`
            (loop % "if (!el.classList.contains('mk-cluster') || el.matches('.mk-pin')) { el.addEventListener('focusin', on); }", {'focusin'}, set()),
        ]
        for src, pin, cluster in cases:
            with self.subTest(src=src[60:150]):
                self.assertEqual(marker_focus(src), {'pin': pin, 'cluster': cluster, 'named': set()})
        # rule D4 revised (Phase 12, qa-02): a cluster marker that the loop names (aria-hidden off, role=button and an
        # aria-label, under one flag) may have focus listeners under that flag; any other cluster may not
        flag = "var linked = el.classList.contains('mk-cluster') && rowsFor(map).length; "
        listen = "if (!el.classList.contains('mk-cluster') || linked) { el.addEventListener('focusin', on); el.addEventListener('focusout', off); } "
        name = ("if (linked) { el.removeAttribute('aria-hidden'); el.setAttribute('role', 'button'); el.setAttribute('tabindex', '0');"
                " el.setAttribute('aria-label', n + ' reports start here'); } ")
        named = [
            # as base.js has it; the naming block before the listeners, and a brace-less `if (linked)` listener
            (loop % (flag + listen + name), both, set(), both),
            (loop % (flag + name + listen), both, set(), both),
            (loop % (flag + "if (linked) el.addEventListener('focusin', on); " + name), {'focusin'}, set(), {'focusin'}),
            # not named: no label, aria-hidden left on, a role that is not a button, the naming under a second condition
            (loop % (flag + listen + name.replace(" el.setAttribute('aria-label', n + ' reports start here');", '')), both, both, set()),
            (loop % (flag + listen + name.replace("el.removeAttribute('aria-hidden'); ", '')), both, both, set()),
            (loop % (flag + listen + name.replace("'role', 'button'", "'role', 'img'")), both, both, set()),
            (loop % (flag + listen + "if (linked) { if (wide) { el.removeAttribute('aria-hidden'); el.setAttribute('role', 'button');"
                                     " el.setAttribute('aria-label', n + ' reports start here'); } } "), both, both, set()),
            # the flag set again after it was declared, or another variable named than the one the listener waits for
            (loop % (flag + listen + name + "linked = true; "), both, both, set()),
            (loop % (flag + "var ok = true; " + listen.replace('|| linked', '|| ok') + name), both, both, set()),
            # a listener with no guard reaches every cluster, named or not
            (loop % (flag + name + "el.addEventListener('focusin', on); "), {'focusin'}, {'focusin'}, set()),
        ]
        for src, pin, cluster, by_name in named:
            with self.subTest(src=src[90:260]):
                self.assertEqual(marker_focus(src), {'pin': pin, 'cluster': cluster, 'named': by_name})
        _got, flags = marker_focus_flags(loop % (flag + listen + name))
        self.assertEqual(flags, {('el', "el.classList.contains('mk-cluster') && rowsFor(map).length")})

    def test_radiogroup_setters_reads_who_gets_the_role(self):
        loop = "document.querySelectorAll('[data-filter-nav]').forEach(function (el) { %s });"
        self.assertEqual(radiogroup_setters(loop % "el.setAttribute('role', 'radiogroup');"), [('el', 'el', None, False)])
        self.assertEqual(radiogroup_setters(loop % ("var box = document.createElement('div'); el.parentNode.replaceChild(box, el);"
                                                    " box.setAttribute(\"role\", \"radiogroup\");")), [('box', 'el', 'div', True)])
        self.assertEqual(radiogroup_setters(loop % "var box = document.createElement('div'); box.setAttribute('role', 'radiogroup');"),
                         [('box', 'el', 'div', False)])
        self.assertEqual(radiogroup_setters("nav.setAttribute('role', 'radiogroup');"), [('nav', None, None, False)])
        self.assertEqual(radiogroup_setters(loop % "// el.setAttribute('role', 'radiogroup');\n"), [])

    def test_guards_reads_an_else_branch_with_and_without_braces(self):
        src = ("function f() { if (open) { a(); }\n // closing: a comment between the block and its else\n else b.go();"
               " if (x) c(); else d(); if (y) { e(); } else { g(); } if (z) { if (w) h(); } }")
        js = Script(src)
        start = src.index('{') + 1
        want = {'a()': [('if', 'open')], 'b.go': [('else', 'open')], 'c()': [('if', 'x')], 'e()': [('if', 'y')], 'g()': [('else', 'y')],
                'h()': [('if', 'w'), ('if', 'z')],
                'd()': []}           # after an if without braces: not read, so nothing is taken to guard it
        for call, guards in want.items():
            with self.subTest(call=call):
                self.assertEqual(js.guards(src.index(call), start), guards)

    def test_map_dimming_reads_what_the_is_hl_class_follows(self):
        fn = "function highlight(map, keys) { keys = keys || []; var has = function (k) { return keys.indexOf(k) !== -1; }; %s }"
        tracks = "map.querySelectorAll('.mk-cat[data-key], .mk-pin[data-key]').forEach(function (g) { %s });"
        clusters = 'map.querySelectorAll(".mk-cluster").forEach(function (c) { %s });'
        T, C = ('.mk-cat[data-key]', '.mk-pin[data-key]'), ('.mk-cluster',)
        t_on = "var on = has(g.dataset.key); g.classList.toggle('hl', on);"
        c_on = "var on = (c.dataset.keys || '').split(' ').some(has); c.classList.toggle('hl', on);"
        dim = " map.classList.toggle('is-hl', hit);"

        def read(*parts):
            return map_dimming(fn % ' '.join(parts))

        # a flag that both loops raise for an element that matched, read by the toggle after them
        got = read('var hit = false;', tracks % (t_on + ' hit = hit || on;'), clusters % (c_on + ' hit = hit || on;'), dim)
        self.assertEqual(got, {'arg': 'hit', 'flag': 'hit', 'raised': [T, C], 'other': [],
                               'tests': {T: 'has(g.dataset.key)', C: "(c.dataset.keys || '').split(' ').some(has)"}})
        # the other two ways to raise it
        got = read('let any = false;', tracks % (t_on + ' any = on || any;'), clusters % (c_on + ' if (on) any = true;'),
                   'map.classList.toggle("is-hl", any);')
        self.assertEqual((got['arg'], got['flag'], got['raised'], got['other']), ('any', 'any', [T, C], []))
        # as it was before round 3: any key at all dimmed the map, whether or not the map draws its trip
        old = read("map.classList.toggle('is-hl', keys.length > 0);", tracks % "g.classList.toggle('hl', has(g.dataset.key));",
                   clusters % "c.classList.toggle('hl', (c.dataset.keys || '').split(' ').some(has));")
        self.assertEqual(old, {'arg': 'keys.length > 0', 'flag': None, 'raised': [], 'tests': {}, 'other': []})
        both = (tracks % (t_on + ' hit = hit || on;'), clusters % (c_on + ' hit = hit || on;'))
        cases = [
            # (what is wrong, the function's statements, flag, raised, other)
            ('the clusters do not raise it', ('var hit = false;', both[0], clusters % c_on, dim), 'hit', [T], []),
            ('the tracks and pins do not', ('var hit = false;', tracks % t_on, both[1], dim), 'hit', [C], []),
            ('raised whether or not it matched', ('var hit = false;', tracks % (t_on + ' hit = true;'), both[1], dim), 'hit', [C], ['hit = true;']),
            ('lowered by an element that did not match', ('var hit = false;', tracks % (t_on + ' hit = hit && on;'), both[1], dim), 'hit', [C],
             ['hit = hit && on;']),
            ('raised with another value than the highlight', ('var hit = false;', tracks % (t_on + ' hit = hit || keys.length;'), both[1], dim),
             'hit', [C], ['hit = hit || keys.length;']),
            ('the raise is commented out', ('var hit = false;', tracks % (t_on + ' // hit = hit || on;\n'), both[1], dim), 'hit', [C], []),
            ('the flag starts raised', ('var hit = true;',) + both + (dim,), None, [T, C], ['hit = true;']),
            ('the flag starts as the old rule', ('var hit = keys.length > 0;',) + both + (dim,), None, [T, C], ['hit = keys.length > 0;']),
            ('the class is toggled before the loops ran', ('var hit = false;', dim) + both, None, [T, C], []),
            ('the flag is overwritten after the loops', ('var hit = false;',) + both + ('hit = keys.length > 0;', dim), 'hit', [T, C],
             ['hit = keys.length > 0;']),
            ('the class follows something else', ('var hit = false;',) + both + ("map.classList.toggle('is-hl', !hit);",), None, [], []),
            ('the class follows the flag or the keys', ('var hit = false;',) + both + ("map.classList.toggle('is-hl', hit || keys.length > 0);",),
             None, [], []),
        ]
        for what, parts, flag, raised, other in cases:
            with self.subTest(case=what):
                got = read(*parts)
                self.assertEqual((got['flag'], got['raised'], got['other']), (flag, raised, other))
        # a loop over another element's markers is not the map's; no function, or a class toggled twice, is not read at all
        got = read('var hit = false;', both[0], "other.querySelectorAll('.mk-cluster').forEach(function (c) { %s });" % (c_on + ' hit = hit || on;'), dim)
        self.assertEqual((got['raised'], got['other']), ([T], ['hit = hit || on;']))
        self.assertIsNone(map_dimming("map.classList.toggle('is-hl', true);"))
        self.assertIsNone(map_dimming(fn % (dim + dim)))
        self.assertIsNone(map_dimming(fn % "// map.classList.toggle('is-hl', hit);\n"))

    def test_show_all_press_reads_what_a_press_does(self):
        loop = ("document.querySelectorAll('.arc-all-btn').forEach(function (b) { var ol = document.getElementById(b.getAttribute('aria-controls'));"
                " b.addEventListener('click', function () { var open = ol.classList.toggle('arc-collapsed') === false; %s }); });")
        focus = "if (open) { var f = ol.querySelector('.arc-more a'); if (f) f.focus(); }"
        near = "{ block: 'nearest' }"
        got = show_all_press(loop % (focus + "\n // closing: keep the button in view\n else b.scrollIntoView({ block: 'nearest' });"))
        self.assertEqual(got, {'button': 'b', 'list': 'ol', 'open': ('open', "ol.classList.toggle('arc-collapsed') === false"),
                               'scrolls': [('b', near, [('else', 'open')])],
                               'focuses': [('f', "ol.querySelector('.arc-more a')", [('if', 'f'), ('if', 'open')])]})

        def scrolls(rest):
            return show_all_press(loop % (focus + rest))['scrolls']

        self.assertEqual(scrolls(" else { b.scrollIntoView({ block: 'nearest' }); }"), [('b', near, [('else', 'open')])])     # with braces
        self.assertEqual(scrolls(" if (!open) b.scrollIntoView({ block: 'nearest' });"), [('b', near, [('if', '!open')])])
        self.assertEqual(scrolls(''), [])                                                              # before round 3
        self.assertEqual(scrolls(" // else b.scrollIntoView({ block: 'nearest' });\n"), [])           # commented out
        self.assertEqual(scrolls(" b.scrollIntoView({ block: 'nearest' });"), [('b', near, [])])       # on every press
        self.assertEqual(scrolls(" else ol.scrollIntoView();"), [('ol', '', [('else', 'open')])])      # the list, to its top
        # the focus: on every press, or on something the listener did not look up
        got = show_all_press(loop % "var f = ol.querySelector('.arc-more a'); if (f) f.focus(); b.focus();")
        self.assertEqual(got['focuses'], [('f', "ol.querySelector('.arc-more a')", [('if', 'f')]), ('b', None, [])])
        # no loop, two loops, a loop without a press, or with two: not read
        self.assertIsNone(show_all_press('var x = 1;'))
        self.assertIsNone(show_all_press(loop % focus + loop % focus))
        self.assertIsNone(show_all_press("document.querySelectorAll('.arc-all-btn').forEach(function (b) { b.hidden = false; });"))
        self.assertIsNone(show_all_press("document.querySelectorAll('.arc-all-btn').forEach(function (b) {"
                                         " b.addEventListener('click', function () { a(); }); b.addEventListener('click', function () { c(); }); });"))
        # a loop over other buttons is not this one, and a list that is not looked up by aria-controls is not known
        self.assertIsNone(show_all_press(loop.replace('.arc-all-btn', '.arc-all-btn, .x') % focus))
        got = show_all_press(loop.replace("document.getElementById(b.getAttribute('aria-controls'))", 'b.previousElementSibling') % focus)
        self.assertEqual((got['list'], got['open']), (None, None))


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
# a second region with a region map (one report), so that each of the two region pages (contract-phase5.md) has another
# to list under 'Other regions' and the home page's Also row has a region with a page of its own
MESA, MS = 'Synthetic Mesa', 'synthetic-mesa'
REGION_PAGES = ('regions/%s/' % RS, 'regions/%s/' % MS)
WRITEUP = ('Synthetic write-up for a test, long enough to stand as a written report in every sense of the word.\n\n'
           'Second synthetic paragraph, with *emphasis* and a [synthetic link](https://example.test/).')
SLUGS = dict((k, PREFIX + k) for k in ('story', 'lap', 'spring', 'crag', 'ride', 'photos', 'paddle', 'walk', 'undated', 'mesa', 'goal',
                                       'idea', 'tour', 'journal'))
SINGLE = ('story', 'lap', 'spring', 'crag', 'ride', 'photos', 'paddle', 'walk', 'undated', 'mesa')      # single-day reports


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
    with a track, a pin per trip (a link, as tools/lib/mapkit.py writes it) and one cluster marker; and a region map
    for MESA with the pin of its one report."""
    meta = {'hash': '', 'regions': [REGION, MESA], 'all_regions': [COAST, MESA, REGION], 'maps': {}}
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
    mesa = ('<a class="mk-pin" href="@@ROOT@@trips/%s/" data-key="%s" aria-label="Synthetic Mesa"><title>Synthetic Mesa</title>'
            '<circle class="mk-hit" cx="9" cy="9" r="12" style="fill: transparent"/></a>' % (SLUGS['mesa'], SLUGS['mesa']))
    for size, (w, h) in (('desktop', (718, 620)), ('phone', (390, 480))):
        name = 'region-%s-%s' % (MS, size)
        meta['maps'][name] = {'w': w, 'h': h, 'png': name + '.webp', 'base': name + '.base.svg', 'region': MESA, 'trips': [SLUGS['mesa']]}
        _write(os.path.join(rendered, 'site', name + '.svg.html'), _svg(w, h, mesa))
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
    mk(trips_dir, s['mesa'], title='Synthetic Mesa', activity='hike', date='2023-10-07', region=MESA, track=True)
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
    ticklist = importlib.import_module('sitegen.pages.ticklist')
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
                mock.patch.object(content, 'RENDERED', rendered), mock.patch.object(home, 'HOME_REGIONS', (REGION,)), \
                mock.patch.object(ticklist, 'FILTERS_FROM', 1):     # the fixture has fewer goals than the form needs: it is checked here
            trips = helpers.load_dir(trips_dir)
            for t in trips:
                if not (t['slug'].startswith(PREFIX) and t['rendered'].startswith(rendered)):
                    raise AssertionError('%s would read outside the temp dir' % t['slug'])
            site = build.site_of(helpers.newest_first(trips))
            site['featured'] = [site['by_slug'][SLUGS[k]] for k in ('story', 'tour', 'journal')]
            # Phase 9: the first region page carries an introduction (content/regions/<slug>.md), so its block is
            # checked with the rest of the page
            site['region_intros'] = {RS: {'title': None, 'meta': {}, 'file': 'content/regions/%s.md' % RS,
                                          'body_md': 'A synthetic introduction to the region, written for a test.'}}
            # with the site meta as it is on disk (the temp dir's), as tools/build.py does: the two regions with a
            # region map get their pages (registered without a meta, no region would have one)
            if core.read_site_meta() != meta:
                raise AssertionError('the site meta on disk is not the fixture\'s')
            core.register_site(site, core.read_site_meta())
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
    """A built page as a browser holds it once the head's inline script has run: <html> carries 'js' (Phase 13A,
    resilience-01; without it the html:not(.js) twins of the no-script rules apply, as when the bundle fails to load:
    script_failed_doc). Without scripting the (scripting: none) queries apply whatever the class says."""
    if url not in _DOCS:
        html_ = site_pages()[url]
        assert html_.count('<html lang="en">') == 1, url
        _DOCS[url] = Doc(html_.replace('<html lang="en">', '<html lang="en" class="js">', 1))
    return _DOCS[url]


def script_failed_doc(url):
    """A built page as the browser holds it when site.js did not load: the inline script ran, then the bundle's onerror
    took 'js' back off (and with scripting off it is never there)."""
    return Doc(site_pages()[url])


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

    def test_every_search_landmark_has_a_name_of_its_own(self):
        # Phase 7: the header's box, the menu's, the 404 page's and the explorers' forms are role="search" landmarks; a
        # landmark list names each, as it names the navs. The menu's box repeats the header's name: the two are never
        # shown at once (the header's row from 1000 px, the menu below it)
        seen = 0
        for url in self.pages:
            if url.endswith('.json'):
                continue
            doc = page_doc(url)
            forms = [f for f in doc.root.walk() if f['role'] == 'search']
            seen += len(forms)
            for f in forms:
                self.assertTrue((f['aria-label'] or '').strip(), '%r on %s has no name' % (f, url or 'the home page'))
            outside_menu = [f['aria-label'] for f in forms if not inside(f, 'menu')]
            self.assertEqual(len(outside_menu), len(set(outside_menu)), url)
        self.assertGreater(seen, 20)
        self.assertEqual([f['aria-label'] for f in page_doc('404.html').root.walk() if f['role'] == 'search' and not inside(f, 'menu')],
                         ['Search trips', 'Find a trip report'])

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
        # contract-phase5.md: one page for each region with a region map and a published report (REGION and MESA); none
        # for the region without a region map, and no index of them
        want |= set(REGION_PAGES)
        self.assertEqual(REGION_PAGES, ('regions/synthetic-range/', 'regions/synthetic-mesa/'))
        # Phase 12 (qa-06): a full-screen page for each region map
        want |= {'map/synthetic-range/', 'map/synthetic-mesa/'}
        self.assertNotIn('regions/synthetic-coast/', urls)
        self.assertNotIn('regions/', urls)
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
        for url in REGION_PAGES:
            self.assertEqual(page_doc(url).find('body')['class'], 'p-region')
        # and card covers with the phone-only wrapper are among what these tests walk
        self.assertGreaterEqual(sum(h.count('<picture class="cover-pic">') for h in self.pages.values()), 4)

    def test_a_region_page_has_every_block_the_static_checks_walk(self):
        # the big region's page: the breadcrumb, the Map page's list beside the map (every trip filed under the region:
        # twelve rows, four of them behind the hidden 'Show all' button), three Featured cards (two of them with the
        # phone-only <picture> wrapper), both links into the explorer, the table with its filter row, and the link to
        # the other region page; the small region's page has what one bare track gives it
        doc = page_doc(REGION_PAGES[0])
        main = doc.by_id('main')
        self.assertEqual([h.text() for h in doc.find_all('h1')], [REGION])
        self.assertEqual([(a.text(), a['href']) for a in main.find('nav', cls='crumbs').find_all('a')], [('Reports', '../../'), ('Map', '../../map/')])
        rows = main.find('ol', cls='arc-rows').find_all('li')
        # contract-phase5.md section 1 as revised: what the content files under the region (the walk without a track,
        # the tour, the journal and the two goals with the rest), not the four trips the map's entry names
        self.assertEqual([li['data-key'] for li in rows],
                         [SLUGS[k] for k in ('story', 'tour', 'lap', 'paddle', 'crag', 'walk', 'photos', 'journal', 'spring', 'undated', 'goal', 'idea')])
        self.assertEqual([li['data-key'] for li in rows if 'arc-more' in li.classes], [SLUGS[k] for k in ('spring', 'undated', 'goal', 'idea')])
        buttons = main.find('div', cls='arc-inreg').find_all('button')
        self.assertEqual([(b.classes, b.text(), 'hidden' in b, b['aria-controls']) for b in buttons],
                         [(['alink', 'arc-all-btn'], 'Show all 10', True, 'arc-rows-' + RS)])
        self.assertEqual(main.find('div', cls='arc-inreg').find('h3').text(), 'In this region')
        self.assertEqual(main.find_all('a', cls='arc-reg-a'), [])                    # no link to the page it is on
        # the map's cluster marker names a row that is shown and one behind the button: both are rows of the list
        clusters = {g['data-keys'] for g in main.find_all('g', cls='mk-cluster')}
        self.assertEqual(clusters, {'%s %s' % (SLUGS['lap'], SLUGS['spring'])})
        cards = main.find('ul', cls='reg-cards').find_all('li', cls='tcard')
        self.assertEqual([li['data-slug'] for li in cards], [SLUGS['story'], SLUGS['tour'], SLUGS['crag']])
        self.assertEqual(len(main.find('ul', cls='reg-cards').find_all('picture', cls='cover-pic')), 2)
        self.assertEqual([n['class'] for n in main.find_all(cls='reg-x')], ['t-mono-s reg-acts reg-x', 'reg-more reg-x', 'reg-find reg-x wrap'])
        self.assertGreaterEqual(len(main.find('div', cls='arc-filt').find_all('button', cls='fchip')), 3)
        self.assertEqual([a['href'] for a in main.find('nav', cls='reg-others').find_all('a')], ['../../regions/synthetic-mesa/', '../../map/'])
        small = page_doc(REGION_PAGES[1]).by_id('main')
        self.assertEqual([a['href'] for a in small.find('nav', cls='reg-others').find_all('a')], ['../../regions/synthetic-range/', '../../map/'])
        self.assertIsNone(small.find('section', cls='reg-feat'))
        self.assertEqual([n['class'] for n in small.find_all(cls='reg-x')], ['t-mono-s reg-acts reg-x', 'reg-find reg-x wrap'])
        self.assertEqual(([li['data-key'] for li in small.find('ol', cls='arc-rows').find_all('li')], small.find_all('button')), ([SLUGS['mesa']], []))
        # the pages that link to them: the home page's region block and Also row, the Map page's panels, the browse row
        home = page_doc('')
        self.assertEqual([a['href'] for a in home.find_all('a') if inside(a, 'hom-reg-n')], ['regions/synthetic-range/'])
        self.assertIn('regions/synthetic-mesa/', [a['href'] for a in home.find_all('a') if inside(a, 'hom-also')])
        self.assertEqual([a['href'] for a in page_doc('map/').find_all('a', cls='arc-reg-a')], ['../regions/synthetic-range/', '../regions/synthetic-mesa/'])
        # the Map page's panel for the big region keeps the four trips its map was drawn with
        panel = page_doc('map/').by_id('region-' + RS)
        self.assertEqual([li['data-key'] for li in panel.find('ol', cls='arc-rows').find_all('li')],
                         [SLUGS[k] for k in ('story', 'lap', 'crag', 'spring')])
    def test_building_the_fixture_left_no_region_page_registered(self):
        # site_pages() registered the fixture's site with its meta (the pages link to regions/<slug>/, so it did) and
        # put core back: the two regions are not registered as having a page once the pages are built
        self.assertIn('regions/%s/' % RS, self.pages[''])
        self.assertIn('../regions/%s/' % MS, self.pages['map/'])
        for name in (REGION, MESA):
            self.assertNotIn(name, core._REGION_PAGES)
            self.assertIsNone(core.region_page_href('', name))
        self.assertFalse(any(url.startswith('trips/' + PREFIX) for url in core._TRIPS_BY_URL))

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
        # Phase 10 (report-01): its write-up clears the 100-character floor and has no photo, so it leads the page and no
        # title action needs to jump to it
        self.assertEqual([(a.text(), a['href']) for a in doc.find('div', cls='rep-actions').find_all('a')], [])
        # the reports beside it keep their map section, their two controls and their map page
        lap = page_doc(trip_url('lap'))
        self.assertIsNotNone(lap.by_id('map'))
        self.assertEqual([a.find('span').text() for a in lap.find('nav', cls='bbar').find_all('a')], ['Stats', 'Map', 'GPX'])   # page order
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

    def test_headings_nest_without_skipping_a_level(self):
        # Phase 13C (a11y-08): a heading is at most one level under the one before it in <main>, so a year's rows (H4 under
        # the year's H3 on Hiking and Mountain biking) no longer read as the year's siblings
        for url in sorted(self.pages):
            with self.subTest(page=url):
                levels = [int(n.tag[1]) for n in page_doc(url).by_id('main').walk() if n.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')]
                skips = [(a, b) for a, b in zip(levels, levels[1:]) if b > a + 1]
                self.assertEqual(skips, [], levels)
        # the fixture's lists are too short to be grouped by year: the H4 rows under a year are tests/test_section_page.py's

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

    def test_map_pins_get_focus_listeners_and_only_named_cluster_markers_do(self):
        got, flags = marker_focus_flags(self.src)
        # a pin is a link: focusing it highlights its track and its row, leaving it clears them
        self.assertEqual(got['pin'], {'focusin', 'focusout'})
        # a cluster marker as mapkit draws it is an aria-hidden <g>: a focus listener makes it a Tab stop in Chrome, and
        # an unnamed one is a dead stop (14 of them on the home page before the fix)
        self.assertEqual(got['cluster'], set())
        # rule D4 revised (Phase 12, qa-02): beside a list the marker is a toggle that selects its rows, so it is named
        # first (aria-hidden off, role=button, an aria-label) and then gets the focus listeners, under the same flag
        self.assertEqual(got['named'], {'focusin', 'focusout'})
        # ... a flag that holds only for a cluster marker of a map with a region list beside it (map/, the region pages):
        # the home page's maps have no list and the Ski panel's list is no region list, so their clusters stay unnamed
        # and out of the Tab order (run under node: tests/maplist_js_harness.js, 'clusters' and 'review fix 2')
        self.assertEqual(len(flags), 1, flags)
        (el, expr), = flags
        terms = conjuncts(expr)
        self.assertIsNotNone(terms, expr)
        self.assertTrue(any(_is_cluster(t, el) for t in terms), expr)
        self.assertTrue(any(re.match(r'^panelList\(\s*[\w$]+\s*\)$', t) for t in terms), expr)
        self.assertIn('''document.querySelector('ol.arc-rows[data-map-target="' + map.id + '"]')''', self.src)

    def test_the_marker_loop_still_wires_both_kinds_for_the_pointer(self):
        # of the loops over the markers, the one that gives them listeners (the others only toggle classes)
        loops = [x for x in self.js.each_callbacks(lambda s: '.mk-pin' in s or '.mk-cluster' in s) if self.js.listeners(x[1], x[2], x[3])]
        self.assertEqual(len(loops), 1, [x[0] for x in loops])
        selector, el, start, end = loops[0]
        # a line that is a link (a journal's days on a region map, which have no pin) is wired as a pin is
        self.assertEqual([s.strip() for s in selector.split(',')], ['.mk-pin[data-key]', '.mk-cluster', '.mk-line[data-key]'])
        events = [event for event, _pos in self.js.listeners(el, start, end)]
        self.assertEqual(sorted(e for e in events if e.startswith('mouse')), ['mouseenter', 'mouseleave'])
        for event, pos in self.js.listeners(el, start, end):
            if event.startswith('mouse'):
                self.assertEqual(self.js.guards(pos, start), [], event)        # pins and clusters alike

    def test_no_script_makes_an_unnamed_cluster_marker_focusable(self):
        names = ['base.js'] + [os.path.join('pages', n) for n in sorted(os.listdir(os.path.join(JS_DIR, 'pages'))) if n.endswith('.js')]
        for name in names:
            with self.subTest(script=name):
                src = source('js', name)
                got = marker_focus(src)
                self.assertEqual(got['cluster'], set())
                if name != 'base.js':
                    self.assertEqual(got['named'], set())           # the cluster's selection is base.js's alone
                js = Script(src)
                # a tab stop only inside the block that names the marker (naming_flag)
                for _selector, el, start, end in js.each_callbacks(lambda s: '.mk-cluster' in s):
                    body = js.text[start:end]
                    for m in re.finditer(r'''(?<![\w$.])%s\.(tabIndex\s*=|setAttribute\(\s*['"]tabindex['"])''' % re.escape(el), body):
                        if not js.code(start + m.start()):
                            continue
                        conds = [(k, c.strip()) for k, c in js.guards(start + m.start(), start)]
                        self.assertTrue(len(conds) == 1 and conds[0][0] == 'if' and naming_flag(js, el, conds[0][1], start, end) is not None,
                                        '%s makes a cluster marker a tab stop outside the block that names it: %r' % (name, conds))

    def test_a_focused_journal_line_shows_its_halo_without_a_script(self):
        # Phase 12: a.mk-line (a journal's days on a region map) has no outline of its own (.mk-line:focus-visible
        # { outline: none; }); its halo is the wide hit path under the lines, drawn by CSS alone, and in Highlight under
        # forced colours. The legend's discs keep their colours there too (archive.js moves them into its buttons).
        # Since Phase 15 the hit path's own stroke is MAP_CSS's '.mk-line .mk-hit' rule, not an inline style, so the halo
        # wins on specificity and carries no !important
        rules, _unreadable = parse_css(source('css', 'base.css'))
        halo = {r.media: r.decls for r in rules if r.selector == '.mk-line:focus-visible .mk-hit'}
        self.assertEqual(halo, {(): {'stroke': ('var(--ink)', False), 'stroke-opacity': ('.35', False)},
                                ('(forced-colors: active)',): {'stroke': ('Highlight', False), 'stroke-opacity': ('1', False)}})
        rules, _unreadable = parse_css(source('css', 'pages', 'archive.css'))
        discs = [(r.media, r.decls) for r in rules if r.selector == '.arc-legend .disc']
        self.assertIn((('(forced-colors: active)',), {'forced-color-adjust': ('none', False)}), discs)
        # no script draws it: neither base.js nor a page script touches .mk-hit
        for name in ['base.js'] + [os.path.join('pages', n) for n in sorted(os.listdir(os.path.join(JS_DIR, 'pages'))) if n.endswith('.js')]:
            self.assertNotIn('mk-hit', Script(source('js', name)).text, name)

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


# ---------------------------------------------------------------- R3: the list beside a region map (base.js, archive.js)

def page_scripts():
    return ['base.js'] + [os.path.join('pages', n) for n in sorted(os.listdir(os.path.join(JS_DIR, 'pages'))) if n.endswith('.js')]


class MapListScriptTests(unittest.TestCase):
    """Round 3 of the region pages, read from the two scripts (the same two behaviours are run under node, against a
    stand-in page, in tests/test_maplist_js.py).

    A region page lists what the content says, so the list beside its map has rows the map does not draw: a report
    without a track, a journal, a report newer than the last render. base.js: highlight(map, keys) gave the map the class
    is-hl, which dims every track and pin that is not picked out, as soon as there was a key; pointing at such a row
    dimmed the whole map and picked out nothing. Now the class follows a flag that only an element that matched raises.

    archive.js: 'Show fewer' closes a long list above the reader and the page under it moves up; the button they
    pressed, which keeps the focus, is scrolled back into view. Opening is as it was: the focus goes to the first row
    that came into view."""

    def setUp(self):
        self.base = source('js', 'base.js')
        self.archive = source('js', 'pages', 'archive.js')

    def test_the_map_is_dimmed_only_when_a_track_a_pin_or_a_cluster_marker_matched(self):
        got = map_dimming(self.base)
        self.assertIsNotNone(got, 'base.js has no highlight(map, keys) that toggles is-hl once')
        self.assertEqual(got['flag'], got['arg'], 'is-hl follows `%s`, which is not a flag that starts false and is read after the loops' % got['arg'])
        self.assertNotIn('keys', got['arg'])                             # the old rule: `keys.length > 0`
        # every kind of mark a key can pick out raises it: a track (.mk-cat, the planned line included), a pin, a cluster
        tracks_and_pins, clusters = ('.mk-cat[data-key]', '.mk-pin[data-key]'), ('.mk-cluster',)
        self.assertEqual(got['raised'], [tracks_and_pins, clusters])
        self.assertEqual(got['other'], [], 'the flag is also set by something that is not a match')
        # ... with the very value that gives the element its own highlight: its key is one of the keys; for a cluster
        # marker, one of the keys it stands for is
        self.assertRegex(got['tests'][tracks_and_pins], r'^has\(\s*[\w$]+\.dataset\.key\s*\)$')
        self.assertRegex(got['tests'][clusters], r'''^\(\s*[\w$]+\.dataset\.keys\s*\|\|\s*(['"])\1\s*\)\.split\(\s*(['"]) \2\s*\)\.some\(\s*has\s*\)$''')

    def test_the_number_of_keys_decides_nothing_in_highlight(self):
        js = Script(self.base)
        (head,) = [m for m in re.finditer(r'(?<![\w$.])function\s+highlight\s*\(\s*([\w$]+)\s*,\s*([\w$]+)\s*\)\s*\{', js.text) if js.code(m.start())]
        body = js.text[head.end():js.close(head.end() - 1)]
        keys = re.escape(head.group(2))
        self.assertNotRegex(body, r'(?<![\w$.])%s\.length' % keys)
        # the keys are asked one way only: is this key among them (null and undefined count as none)
        self.assertRegex(body, r'(?<![\w$.])%s\s*=\s*%s\s*\|\|\s*\[\s*\]\s*;' % (keys, keys))
        self.assertRegex(body, r'(?:var|let|const)\s+has\s*=\s*function\s*\(\s*([\w$]+)\s*\)\s*\{\s*return\s+%s\.indexOf\(\s*\1\s*\)\s*!==\s*-1\s*;\s*\}' % keys)
        self.assertEqual(len(re.findall(r'(?<![\w$.])%s(?![\w$])' % keys, body)), 3)       # those two lines and nothing else

    def test_no_other_line_of_any_script_gives_a_map_the_class(self):
        for name in page_scripts():
            with self.subTest(script=name):
                js = Script(source('js', name))
                hits = [m.start() for m in re.finditer(r'''(['"])is-hl\1''', js.text) if js.mask[m.start()] == 's']
                self.assertEqual(len(hits), 1 if name == 'base.js' else 0)
        self.assertEqual(len(re.findall(r'''classList\.toggle\(\s*['"]is-hl['"]''', Script(self.base).text)), 1)

    def test_a_list_row_still_asks_for_its_own_key_and_clears_the_map_when_left(self):
        # unchanged by round 3, and what the change leans on: a row hands highlight() its one key, drawn or not, and
        # null when the pointer or the focus leaves it (the flag then stays down and the class goes)
        js = Script(self.base)
        (_sel, list_, start, end), = js.each_callbacks(lambda s: s.strip() == '[data-map-target]')
        rows = [x for x in js.each_callbacks(lambda s: s.strip() == '[data-key]') if start <= x[2] and x[3] <= end]
        self.assertEqual(len(rows), 1)
        _sel, row, s, e = rows[0]
        body = js.text[s:e]
        on = re.search(r'(?:var|let|const)\s+([\w$]+)\s*=\s*function\s*\(\s*\)\s*\{\s*highlight\(\s*([\w$]+)\s*,\s*\[\s*%s\.dataset\.key\s*\]\s*\)\s*;\s*\}'
                       % re.escape(row), body)
        self.assertIsNotNone(on, 'a row no longer calls highlight(map, [its key])')
        # Phase 12 (qa-02): back to a cluster's selection when there is one, else cleared
        m = re.escape(on.group(2))
        off = re.search(r'(?:var|let|const)\s+([\w$]+)\s*=\s*function\s*\(\s*\)\s*\{\s*highlight\(\s*%s\s*,\s*(?:null|\(\s*%s\s*&&\s*%s\._sel\s*\)\s*\|\|\s*null)\s*\)\s*;'
                        % (m, m, m), body)
        self.assertIsNotNone(off, 'leaving a row no longer calls highlight(map, null) (or the selection)')
        wired = dict(re.findall(r'''(?<![\w$.])%s\.addEventListener\(\s*['"]([\w-]+)['"]\s*,\s*([\w$]+)\s*\)''' % re.escape(row), body))
        self.assertEqual(wired, {'mouseenter': on.group(1), 'focusin': on.group(1), 'mouseleave': off.group(1), 'focusout': off.group(1)})
        # the map is the one the list names
        self.assertRegex(js.text[start:s], r'(?:var|let|const)\s+%s\s*=\s*document\.getElementById\(\s*%s\.dataset\.mapTarget\s*\)'
                         % (re.escape(on.group(2)), re.escape(list_)))

    def test_show_fewer_scrolls_the_button_into_view_and_only_when_the_list_closes(self):
        got = show_all_press(self.archive)
        self.assertIsNotNone(got, "archive.js has no loop over the 'Show all' buttons with one click listener")
        button, list_ = got['button'], got['list']
        self.assertIsNotNone(list_, 'the list is not looked up by the aria-controls of its button')
        self.assertIsNotNone(got['open'], 'the press does not toggle a class of the list')
        opened, how = got['open']
        # open: the class that hides the rows beyond the first eight has just been taken off
        self.assertRegex(how, r'''^%s\.classList\.toggle\(\s*(['"])arc-collapsed\1\s*\)\s*===\s*false$''' % re.escape(list_))
        self.assertEqual(len(got['scrolls']), 1, 'the press does not scroll once: %r' % (got['scrolls'],))
        target, how, guards = got['scrolls'][0]
        self.assertEqual(target, button)                           # the button the reader pressed, not the list or its first row
        self.assertRegex(how, r'''^\{\s*block\s*:\s*(['"])nearest\1\s*\}$''')        # by the least movement, and not at all when it is in view
        self.assertEqual(guards, [('else', opened)])               # when the list closed, and only then

    def test_show_all_still_moves_the_focus_to_the_first_row_it_reveals(self):
        got = show_all_press(self.archive)
        opened = got['open'][0]
        self.assertEqual(len(got['focuses']), 1, got['focuses'])
        target, how, guards = got['focuses'][0]
        self.assertNotEqual(target, got['button'])
        # querySelector: the first of the rows that were hidden (li.arc-more), its link
        self.assertRegex(how or '', r'''^%s\.querySelector\(\s*(['"])\.arc-more a\1\s*\)$''' % re.escape(got['list']))
        self.assertEqual(guards, [('if', target), ('if', opened)])  # when the list opened, and it has such a row

    def test_no_other_script_wires_the_show_all_buttons(self):
        for name in page_scripts():
            with self.subTest(script=name):
                src = source('js', name)
                if name.endswith('archive.js'):
                    self.assertIsNotNone(show_all_press(src))
                elif name == 'base.js':
                    # Phase 12 (the review): base.js listens to the button only to end a cluster's selection before
                    # archive.js folds or opens the list (run under node: tests/maplist_js_harness.js, 'review fix 5')
                    text = Script(src).text
                    self.assertEqual(text.count('arc-all-btn'), 1)
                    self.assertIn("btn.addEventListener('click', function () { if (map._sel && !opening) unselect(map); });", text)
                else:
                    self.assertNotIn('arc-all-btn', Script(src).text)


# ---------------------------------------------------------------- D2, D3: without JavaScript

def scripting_none(rules):
    return [r for r in rules if any(re.sub(r'\s+', '', q.lower()) == '(scripting:none)' for q in r.media)]


def subject_class(rule):
    """The class a rule is about when its subject is one bare class ('.units', '.site-h .units'), else None."""
    if rule.parts is None:
        return None
    simples = rule.parts[-1][1]
    return simples[0][1] if len(simples) == 1 and simples[0][0] == 'cls' else None


def header_h(width):
    """--header-h with JavaScript at a width (Phase 16, Alpine: 56 px, 64 from 760, 72 from 1200)."""
    return '72px' if width >= 1200 else '64px' if width >= 760 else '56px'


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

    # contract-phase5.md section 5: a region page's links into the Trips explorer carry its filters in the address, which
    # only trips.js reads; region.css takes them off the page when scripting is off, and nothing else

    def test_region_css_hides_the_links_that_need_the_explorers_script(self):
        rules = parse_css(source('css', 'pages', 'region.css'))[0]
        self.assertEqual(self.displays(rules), {'reg-x': 'none'})
        self.assertEqual([r.selector for r in scripting_none(rules)], ['.reg-x'])           # the block holds that one rule
        self.assertEqual(self.displays(self.rules).get('reg-x'), 'none')                    # and the published stylesheet keeps it
        # no rule outside the scripting query hides or shows the class, but its twin for a bundle that did not run
        self.assertEqual([r.selector for r in self.rules if 'reg-x' in r.selector and not scripting_none([r])], [':where(html:not(.js)) .reg-x'])

    def explorer_links(self, url):
        marked = self.nodes(url, cls='reg-x')
        links = [a for n in marked for a in n.find_all('a')]
        # one link in each, but the activities line (Phase 12, ia-10): one per activity of the region
        self.assertEqual(len(links), len(marked) - 1 + len(page_doc(url).find('p', cls='reg-acts').find_all('a')))
        for a in links:
            self.assertIn('trips/?region=', a['href'])
        return marked, links

    def test_without_scripting_no_explorer_link_of_a_region_page_is_displayed(self):
        seen = 0
        for url in REGION_PAGES:
            marked, links = self.explorer_links(url)
            for width in (320,) + WIDTHS:
                e = env(width, scripting='none')
                with self.subTest(page=url, width=width):
                    for node in marked + links:
                        seen += 1
                        self.assertFalse(displayed(node, self.rules, e), '%r: %s' % (node, why(node, 'display', self.rules, e)))
        # two links on the big region's page, one on the small one's, and the activities line on each (with its links)
        want = sum(len(self.explorer_links(url)[0]) + len(self.explorer_links(url)[1]) for url in REGION_PAGES)
        self.assertEqual(seen, want * 7)
        self.assertGreater(want, 2 + 2 + 1 + 1)
        # every link of the page that carries a query for trips.js is one of them
        for url in REGION_PAGES:
            queried = [a for a in page_doc(url).by_id('main').find_all('a') if '?' in (a['href'] or '')]
            self.assertEqual([a for a in queried if not inside(a, 'reg-x')], [])
            self.assertEqual(len(queried), len(self.explorer_links(url)[1]))

    def test_with_scripting_the_explorer_links_are_displayed(self):
        for url in REGION_PAGES:
            marked, links = self.explorer_links(url)
            for width in (320,) + WIDTHS:
                e = env(width)
                for node in marked + links:
                    self.assertTrue(displayed(node, self.rules, e), '%r at %d px: %s' % (node, width, why(node, 'display', self.rules, e)))
                for node in marked:
                    self.assertIsNone(computed(node, 'display', self.rules, e))

    def test_without_scripting_nothing_else_of_a_region_page_goes(self):
        # the breadcrumb, the rows beside the map, the cards, the table and the other regions are plain links: each is
        # displayed without scripting exactly where it is displayed with it (a map pin of the render a width does not
        # show stays hidden either way)
        checked = 0
        for url in REGION_PAGES:
            main = page_doc(url).by_id('main')
            rest = [a for a in main.find_all('a') if not inside(a, 'reg-x')]
            self.assertGreater(len(rest), 7)
            for width in (320,) + WIDTHS:
                with_, without = env(width), env(width, scripting='none')
                for a in rest:
                    checked += 1
                    self.assertEqual(displayed(a, self.rules, without), displayed(a, self.rules, with_), '%r at %d px' % (a, width))
                for cls in ('reg-head', 'arc-map', 'arc-all', 'reg-others'):
                    for node in main.find_all(cls=cls):
                        self.assertTrue(displayed(node, self.rules, without), '%r at %d px' % (node, width))
                for a in main.find('nav', cls='reg-others').find_all('a') + main.find('nav', cls='crumbs').find_all('a'):
                    self.assertTrue(displayed(a, self.rules, without))
        self.assertGreater(checked, 250)

    # the header as it is generated, and what the published stylesheet makes of it with scripting off

    def header_parts(self, url):
        head = self.header(url)
        nav = head.find('nav', cls='nav')
        btn = head.find('button', cls='menu-btn')
        self.assertIsNotNone(nav)
        self.assertIsNotNone(btn)
        # Search: a box that lands on trips/ (core.search_form), and on trips/ itself a link to the page's own box
        units, search = nav.find(cls='units'), nav.find(cls='nav-search')
        self.assertIsNotNone(units, 'no units switch in the header nav')
        self.assertIsNotNone(search, 'no Search box or link in the header nav')
        self.assertEqual(search.tag, 'a' if url == 'trips/' else 'form', url)
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
        # the box too: without scripting trips/ lists every trip and does not read ?q=
        self.assertNotDisplayed(lambda parts: parts[3], 'the header Search box or link')

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
        # the row from 1000 px (Phase 13A, visual-17; 1140 before)
        for width, nav_display, btn_display in ((390, 'none', 'flex'), (800, 'none', 'flex'), (999, 'none', 'flex'),
                                                (1000, 'flex', 'none'), (1139, 'flex', 'none'), (1300, 'flex', 'none')):
            with self.subTest(width=width):
                e = env(width)
                self.assertEqual(computed(nav, 'display', self.rules, e), nav_display)
                self.assertEqual(computed(btn, 'display', self.rules, e), btn_display)
                # the units switch and the Search link come and go with the row they are in, and with nothing else
                self.assertEqual(displayed(units, self.rules, e), nav_display == 'flex')
                self.assertEqual(displayed(search, self.rules, e), nav_display == 'flex')
                self.assertNotEqual(computed(units, 'display', self.rules, e), 'none')
                self.assertNotEqual(computed(search, 'display', self.rules, e), 'none')
                # the phone's units tabs (Phase 16) beside the menu button: shown exactly where the row is not
                phone = self.header('').find('div', cls='site-h-u')
                self.assertEqual(displayed(phone.find(cls='units'), self.rules, e), nav_display == 'none')
                self.assertFalse(displayed(phone.find(cls='units'), self.rules, env(width, scripting='none')))
                # ... and its empty holder goes too: left in the row, its margin-left: auto pushed the links to the name
                self.assertFalse(displayed(phone, self.rules, env(width, scripting='none')), why(phone, 'display', self.rules, env(width, scripting='none')))

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
    # 999 / 1000 where the links take the menu's place when there is JavaScript (1140 before Phase 13A)
    NS_WIDTHS = (320, 360, 390, 479, 480, 760, 999, 1000, 1280)
    NS_PAGES = ('', 'trips/', 'about/', 'ski/', trip_url('story'), trip_url('journal'), trip_url('tour'))

    def header_boxes(self, url):
        """(html, header, its inner row, nav, the row of links, the row that holds Search) of a page."""
        head = self.header(url)
        inner = head.find('div', cls='site-h-in')
        nav, _btn, _units, search = self.header_parts(url)
        rows = [n for n in nav.elements() if 'nav-l' in n.classes]
        self.assertEqual(len(rows), 2, 'the header nav no longer has its two .nav-l rows')
        self.assertEqual(rows[1].elements(), [search])                       # the second row holds the Search box or link, alone
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
                    self.assertEqual(computed(root, '--header-h', self.rules, e), '0px' if phone else header_h(width))
                    # never lower than the header with JavaScript: 56 px, 64 from 760, 72 from 1200
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
        # no rule draws the header links' ring anywhere else, or removes it. The search box is not a link: it draws its
        # ring on its own border, as every text box does (.trx-q, .nf-q), and is not shown without scripting
        for r in self.rules:
            if r.selector == '.nav-q:focus-visible':
                self.assertEqual(r.decls['outline-offset'][0], '0')
                continue
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
        # the header's two (the row's, from 1000 px, and the phone's beside the menu button: Phase 16), the menu's, the page's own
        self.assertEqual((len(switches), len(own)), (4, 1))
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
        # every other page has the header's three and no fourth
        for url in ('', 'trips/', trip_url('story')):
            self.assertEqual(len(page_doc(url).find_all(cls='units')), 3, url)

    def test_with_scripting_none_of_this_touches_the_header(self):
        # every rule above sits in a (scripting: none) query: with JavaScript the header is what it was at every width
        for url in self.NS_PAGES:
            root, head, inner, nav, links, search_row = self.header_boxes(url)
            for width in self.NS_WIDTHS:
                with self.subTest(page=url, width=width):
                    e = env(width)
                    self.assertEqual(computed(head, 'position', self.rules, e), 'sticky')
                    self.assertEqual(computed(head, 'top', self.rules, e), '0')
                    self.assertEqual(computed(root, '--header-h', self.rules, e), header_h(width))
                    self.assertEqual(computed(inner, 'height', self.rules, e), 'var(--header-h)')
                    for prop in ('min-height', 'padding-block', 'padding', 'flex-wrap'):
                        self.assertIsNone(computed(inner, prop, self.rules, e), why(inner, prop, self.rules, e))
                    for row in (links, search_row):
                        self.assertEqual(computed(row, 'display', self.rules, e), 'flex')
                        self.assertEqual(computed(row, 'gap', self.rules, e), '32px')
                        for prop in ('flex-wrap', 'row-gap', 'min-width', 'overflow-x', 'overflow'):
                            self.assertIsNone(computed(row, prop, self.rules, e), why(row, prop, self.rules, e))
                    self.assertIsNone(computed(nav, 'min-width', self.rules, e))
                    self.assertEqual(computed(nav, 'display', self.rules, e), 'flex' if width >= 1000 else 'none')

    def test_every_no_script_rule_has_its_twin_for_a_bundle_that_did_not_run(self):
        # Phase 13A (resilience-01): (scripting: none) matches only with scripting off, and only in browsers that know the
        # query; a page whose site.js failed to load still had scripting. The head's script puts 'js' on <html> and
        # site.js's onerror takes it off, so each rule's twin, ':where(html:not(.js)) <selector>' with the same
        # declarations under the same other conditions, covers that page. :where() keeps the twin's weight; the
        # custom property's twin is ':root:not(.js)', heavier than the ':root' rules it must beat
        seen = 0
        sheets = [('base.css',)] + [('pages', f) for f in sorted(os.listdir(os.path.join(ROOT, 'assets', 'css', 'pages'))) if f.endswith('.css')]
        twin_of = lambda sel: sel.startswith((':where(html:not(.js)) ', ':root:not(.js)'))  # noqa: E731
        for path in sheets:
            rules = parse_css(source('css', *path))[0]
            for r in scripting_none(rules):
                # the same conditions without the scripting one: '(scripting: none) and (max-width: 479.98px)' gives
                # '(max-width: 479.98px)', a bare '(scripting: none)' gives none
                media = tuple(q.replace('(scripting: none) and ', '') for q in r.media)
                media = tuple(q for q in media if re.sub(r'\s+', '', q.lower()) != '(scripting:none)')
                twin = ':root:not(.js)' if r.selector == ':root' else ':where(html:not(.js)) ' + r.selector
                with self.subTest(sheet='/'.join(path), selector=r.selector):
                    got = [t for t in rules if t.selector == twin and tuple(t.media) == media and t.decls == r.decls]
                    self.assertEqual(len(got), 1, (twin, media))
                    self.assertGreater(got[0].order, r.order)
                    # right after its block: nothing but no-script rules and other twins between the two
                    between = [t for t in rules if r.order < t.order < got[0].order]
                    self.assertEqual([t.selector for t in between if not scripting_none([t]) and not twin_of(t.selector)], [])
                    if r.selector != ':root':
                        self.assertEqual(got[0].spec, r.spec)
                    seen += 1
        self.assertGreaterEqual(seen, 13)
        # the markup's half: the head's script adds the class before the page paints, and the bundle's onerror removes it
        html_ = site_pages()['']
        self.assertIn('<script>' + core.PREPAINT + '</script>', html_)
        self.assertIn('d.classList.add("js")', core.PREPAINT)
        # ... and 'km' with it: the switch is hidden then, and the page says miles (the review of Phase 13A)
        self.assertIn('<script src="assets/site.js" defer onerror="document.documentElement.classList.remove(\'js\', \'km\')"></script>', html_)

    def test_when_the_bundle_did_not_run_the_header_is_the_no_script_one(self):
        # scripting on, no 'js' on <html> (site.js failed to load): the links take the menu's place below 1000 px, the
        # controls that need the script are not shown, as with scripting off
        doc = script_failed_doc('')
        nav, btn = doc.find('nav', cls='nav'), doc.find('button', cls='menu-btn')
        units = [u for u in doc.find_all(cls='units') if inside(u, 'site-h')]
        for width in (320, 390, 760, 999, 1280):
            e = env(width)
            with self.subTest(width=width):
                self.assertEqual(computed(nav, 'display', self.rules, e), 'flex')
                self.assertFalse(displayed(btn, self.rules, e), why(btn, 'display', self.rules, e))
                for u in units:
                    self.assertFalse(displayed(u, self.rules, e))
                self.assertEqual(computed(doc.find('html'), '--header-h', self.rules, e), '0px' if width < 480 else header_h(width))
        # with the class, the header is the scripted one
        nav = page_doc('').find('nav', cls='nav')
        self.assertEqual(computed(nav, 'display', self.rules, env(390)), 'none')

    def test_the_no_script_header_rules_are_all_inside_scripting_queries(self):
        # the same from the stylesheet's side: base.css states each of these only where scripting is off
        rules = parse_css(source('css', 'base.css'))[0]

        def off(r):
            return any('scripting' in q and 'none' in q for q in r.media)

        def short(r):           # a short or sideways phone (Phase 13A, phone-10): the same header, with or without a script
            return any('max-height: 500px' in q for q in r.media)

        for selector, prop in (('.nav-l', 'flex-wrap'), ('.nav-l', 'row-gap'), ('.nav-l', 'min-width'), ('.nav', 'min-width'),
                               ('.site-h-in', 'min-height'), ('.site-h-in', 'padding-block'), ('.nav-sep + .nav-l', 'display'),
                               ('.units.abo-units', 'display'), ('.site-h .units', 'display'), ('.menu-btn', 'width')):
            with self.subTest(selector=selector, prop=prop):
                stated = [r for r in rules if r.selector == selector and prop in r.decls]
                if prop == 'width':                      # a control: the menu button's own rule is still there, untouched
                    self.assertEqual([off(r) for r in stated], [False])
                    continue
                self.assertTrue(stated, 'no rule states %s for %s' % (prop, selector))
                self.assertEqual([r.selector for r in stated if not off(r) and not short(r)], [])
        for selector, prop, values in (('.site-h', 'position', ['sticky', 'static', 'static']),
                                       ('.site-h-in', 'height', ['var(--header-h)', 'auto']),
                                       (':root', '--header-h', ['56px', '64px', '72px', '0px', '0px'])):
            with self.subTest(selector=selector, prop=prop):
                stated = [r for r in rules if r.selector == selector and prop in r.decls]
                self.assertEqual([r.decls[prop][0] for r in stated], values)
                # the last of each is the short phone's (phone-10), stated with and without a script
                n = len(values) - (1 if selector == '.site-h-in' else 2)
                self.assertEqual([off(r) for r in stated][:n + 1], [False] * n + [True])
                self.assertTrue(all(short(r) for r in stated[n + 1:]))
        # the phone block is narrower than the width at which five links fit beside the name (about 452 px)
        phone = [r for r in rules if r.selector == '.site-h' and r.decls.get('position', ('',))[0] == 'static' and off(r)]
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

    def test_the_day_nav_is_not_sticky_on_a_viewport_under_500_px_high(self):
        # 500 since Phase 13A (phone-10, where a phone's header goes static too); 480 before
        bar = self.nodes(trip_url('tour'), cls='mul-dnav')[0]
        for width, height, want in ((390, 844, 'sticky'), (1300, 900, 'sticky'), (844, 501, 'sticky'), (844, 500, 'static'),
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
        self.assertTrue(490 <= limit <= 500, short[0].media)
        base = [r for r in rules if r.selector == '.mul-dnav' and 'position' in r.decls and not r.media]
        self.assertEqual([r.decls['position'][0] for r in base], ['sticky'])
        self.assertGreater(short[0].order, base[0].order)        # equal weight: the later rule is the one that holds

    def test_the_journals_month_bar_releases_under_500_px_high(self):
        # Phase 12 (gap2-05): the day bar's rule, which the month bar was left out of until then (500 since Phase 13A)
        bar = self.nodes(trip_url('journal'), cls='ser-mnav')[0]
        for height, want in ((844, 'sticky'), (501, 'sticky'), (500, 'static'), (375, 'static')):
            with self.subTest(height=height):
                self.assertEqual(computed(bar, 'position', self.rules, env(844, height)), want)

    def test_a_short_or_sideways_phone_lets_the_header_scroll_away_and_keeps_it_while_the_menu_is_open(self):
        # Phase 13A (phone-10): under 760 px wide and 500 px high the header is static (no room is kept for it), the bottom
        # bar is one 40 px row; with the menu open the header sticks again and the menu opens under its 56 px
        url = trip_url('story')
        doc = page_doc(url)
        root, head, inner = doc.find('html'), doc.find('header', cls='site-h'), doc.find('div', cls='site-h-in')
        link = doc.find('nav', cls='bbar').find('a')
        for (w, h), static in (((390, 844), False), ((667, 375), True), ((390, 500), True), ((390, 501), False), ((800, 375), False),
                               ((1280, 400), False)):
            e = env(w, h)
            with self.subTest(size='%dx%d' % (w, h)):
                self.assertEqual(computed(head, 'position', self.rules, e), 'static' if static else 'sticky')
                self.assertEqual(computed(root, '--header-h', self.rules, e), '0px' if static else header_h(w))
                if static:
                    self.assertEqual(computed(inner, 'min-height', self.rules, e), '56px')
                if w < 760:
                    self.assertEqual((computed(link, 'height', self.rules, e), computed(link, 'flex-direction', self.rules, e)),
                                     ('40px', 'row') if static else ('56px', 'column'))
        body = doc.find('body')
        body.attrs['class'] = body.attrs.get('class', '') + ' menu-open'
        try:
            e = env(667, 375)
            self.assertEqual(computed(head, 'position', self.rules, e), 'sticky')
            self.assertEqual(computed(body, '--header-h', self.rules, e), '56px')
        finally:
            body.attrs['class'] = body.attrs['class'].replace(' menu-open', '')

    def test_a_phones_selects_and_copy_field_are_16_px_so_ios_does_not_zoom(self):
        # Phase 13A (phone-09)
        # (from 760 px the font shorthand's 15 px and 13 px stand: no font-size of their own)
        sel = page_doc('trips/').find('label', cls='trx-sel').find('select')
        copy = Doc('<div class="copy-pop"><input type="text" class="copy-url"></div>').find('input')    # base.js makes it
        for w, want in ((390, '16px'), (759, '16px'), (760, None), (1280, None)):
            e = env(w)
            with self.subTest(width=w):
                self.assertEqual(computed(sel, 'font-size', self.rules, e), want)
                self.assertEqual(computed(copy, 'font-size', self.rules, e), want)
        # a phone on its side is wider than 760 px: a touch screen gets 16 px at any width (the review of Phase 13A)
        for w, h in ((844, 390), (932, 430), (1180, 820)):
            e = dict(env(w, h), hover='none', pointer='coarse')
            with self.subTest(touch='%dx%d' % (w, h)):
                self.assertEqual((computed(sel, 'font-size', self.rules, e), computed(copy, 'font-size', self.rules, e)), ('16px', '16px'))
        self.assertIn("inp.type = 'text'; inp.readOnly = true; inp.className = 'copy-url';", source('js', 'base.js'))

    def test_a_short_desktop_window_shows_the_ski_panels_phone_render(self):
        # Phase 12 (gap2-02): from 1200 px and under 760 px of height the 390 x 480 render stands in for the 506 x 680 one
        maps = self.nodes('ski/', cls='sec-maps')[0]
        wide, tall = [n for n in maps.walk() if 'mv--desktop' in n.classes][0], [n for n in maps.walk() if 'mv--phone' in n.classes][0]
        for (w, h), want in (((1366, 683), (False, True)), ((1280, 620), (False, True)), ((1366, 900), (True, False)),
                             ((1440, 760), (True, False)), ((1100, 683), (False, True))):
            e = env(w, h)
            with self.subTest(size='%dx%d' % (w, h)):
                self.assertEqual((displayed(wide, self.rules, e), displayed(tall, self.rules, e)), want,
                                 (why(wide, 'display', self.rules, e), why(tall, 'display', self.rules, e)))

    def test_every_sticky_part_follows_the_one_rule(self):
        # Phase 12 (gap2-07, docs/DEVELOPING.md 'Sticky parts'): a stuck part fits the header + 24 + its content in 100svh
        # on a 683 px tall viewport, or scales, or releases (bars under 500 px of height, columns under 600). The evaluator
        # does not compute calc(): a fitted part is asserted by its declaration (100svh in the width or the max-height)
        parts = [
            # (page, class, the fitted element's class and property, or None)
            ('map/', 'arc-mapcol', ('mv', 'width', 'arc-mapv')),
            (trip_url('tour'), 'mul-dnav', None),
            (trip_url('tour'), 'mul-rail', None),
            (trip_url('journal'), 'ser-mnav', None),
            ('about/', 'abo-nums', None),
            ('ski/', 'sec-panel-in', ('mv', 'width', 'sec-maps')),
        ]
        want = {
            # width, height: position of arc-mapcol, mul-dnav, mul-rail, ser-mnav, abo-nums, sec-panel-in
            (1366, 683): ('sticky', 'sticky', 'sticky', 'sticky', 'static', 'sticky'),
            (1280, 620): ('sticky', 'sticky', 'sticky', 'sticky', 'static', 'sticky'),
            (1152, 630): ('sticky', 'sticky', 'sticky', 'sticky', 'static', 'sticky'),
            (1440, 790): ('sticky', 'sticky', 'sticky', 'sticky', 'static', 'sticky'),
            (667, 375): ('static', 'static', 'static', 'static', 'static', 'static'),
            (1300, 599): ('static', 'sticky', 'static', 'sticky', 'static', 'static'),          # columns release under 600
        }
        # the full-screen map's box is not sticky: it fits the screen, and a landscape phone gives it all but 68 px
        box = self.nodes(trip_url('story', 'map/'), cls='fs-map')[0]
        for (w, h) in want:
            with self.subTest(size='%dx%d' % (w, h), part='fs-map'):
                self.assertEqual(computed(box, 'max-height', self.rules, env(w, h)),
                                 'calc(100svh - 68px)' if h <= 480 else 'calc(100svh - 168px)', why(box, 'max-height', self.rules, env(w, h)))
        for (w, h), positions in sorted(want.items()):
            e = env(w, h)
            for (url, cls, fitted), pos in zip(parts, positions):
                node = self.nodes(url, cls=cls)[0]
                with self.subTest(size='%dx%d' % (w, h), part=cls):
                    self.assertEqual(computed(node, 'position', self.rules, e) or 'static', pos, why(node, 'position', self.rules, e))
                    if fitted and pos == 'sticky':
                        inner = [n for n in node.walk() if fitted[0] in n.classes and inside(n, fitted[2])]
                        self.assertTrue(inner)
                        self.assertIn('100svh', computed(inner[0], fitted[1], self.rules, e) or '', why(inner[0], fitted[1], self.rules, e))
        # the Ski panel (section.css) and the full-screen box: their fits are declarations of 100svh
        ski = source('css', 'pages', 'section.css')
        self.assertEqual(ski.count('100vh'), 0)
        self.assertGreaterEqual(ski.count('100svh'), 3)
        self.assertIn('@media (min-width: 1200px) and (max-height: 759.98px)', ski)
        self.assertIn('@media (min-width: 960px) and (max-height: 599.98px) { .sec-panel-in { position: static; } }', ski)
        base = source('css', 'base.css')
        self.assertIn('max-height: calc(100svh - 168px)', base)
        self.assertIn('.p-fsmap .fs-map { max-height: calc(100svh - 68px); }', base)
        self.assertIn('@media (min-width: 1000px) and (max-height: 599.98px) { .mul-rail { position: static; } }', source('css', 'pages', 'multiday.css'))


# ---------------------------------------------------------------- D7: 44 px targets

class Phase12ReviewCssTests(unittest.TestCase):
    """What Phase 12's review found in the stylesheets, read from the source."""

    def rules(self, *path):
        return parse_css(source('css', *path))[0]

    def one(self, rules, selector, media=()):
        got = [r for r in rules if r.selector == selector and list(r.media) == list(media)]
        self.assertEqual(len(got), 1, (selector, media))
        return got[0]

    def test_a_meta_lines_clip_reaches_past_it_so_a_links_44_px_hit_area_is_not_cut(self):
        # .ml's clip hides the dot before each line's first item (its left inset); a .mi-a or .arc-sel-clear ::before
        # reaches 14 px above and below and 4 to 6 px to the right, and a clip at the line's own box cut it to 16 px
        r = self.one(self.rules('base.css'), '.ml')
        top, right, bottom, left = re.match(r'^inset\((\S+) (\S+) (\S+) (.+)\)$', r.decls['clip-path'][0]).groups()
        self.assertEqual(left, 'var(--ml-sep)')
        self.assertTrue(px(top) <= -14 and px(bottom) <= -14 and px(right) <= -6, r.decls['clip-path'][0])
        for sel, css in (('.mi-a::before', 'base.css'), ('.arc-sel-clear::before', 'pages/archive.css')):
            inset = self.one(self.rules(*css.split('/')), sel).decls['inset'][0].split()
            self.assertTrue(-px(inset[0]) <= -px(top) and -px(inset[1]) <= -px(right), (sel, inset))

    def test_a_focused_cluster_is_not_dimmed_with_the_tracks_it_picks_out(self):
        rules = self.rules('base.css')
        dim = self.one(rules, '.map.is-hl .mk-cluster.hl')
        self.assertEqual(dim.decls['opacity'][0], '.2')
        for sel in ('.map.is-hl .mk-cluster.is-linked[aria-pressed="true"]', '.map.is-hl .mk-cluster.is-linked:focus-visible'):
            r = self.one(rules, sel)
            self.assertEqual(r.decls['opacity'][0], '1')
            self.assertGreater(r.order, dim.order)
        self.assertEqual(self.one(rules, '.mk-pin.is-sel > circle:nth-of-type(2)').decls['stroke-width'][0], '3px')

    def test_the_ski_labels_take_a_44_px_hit_area_and_the_region_activities_read_with_their_counts(self):
        # the label (shown without JavaScript) takes the 44 px ::before of .mi-a; an activity link of a region's head
        # reads 'HIKING: 4 reports', not 'HIKING4 reports'
        labels = [a for p in page_doc('ski/').find_all('p', cls='sec-rp-l') for a in p.find_all('a')]
        self.assertTrue(labels)
        self.assertEqual({tuple(a.classes) for a in labels}, {('mi-a',)})
        for url in REGION_PAGES:
            for a in page_doc(url).find('p', cls='reg-acts').find_all('a'):
                self.assertRegex(a.text(), r'^[A-Z ]+: \d+ reports?$')

    def test_stacked_legend_buttons_take_44_px_each(self):
        # 20 px items 24 px apart: each button's 44 px box (margin -12px 0) meets the next, never covers it
        rules = self.rules('pages', 'archive.css')
        b = self.one(rules, '.arc-lg-b')
        self.assertEqual((b.decls['min-height'][0], b.decls['margin'][0]), ('44px', '-12px 0'))
        self.assertEqual(self.one(rules, '.arc-legend li').decls['min-height'][0], '20px')
        self.assertEqual(self.one(rules, '.arc-legend ul.arc-lg-ul', ['(max-width: 999.98px)']).decls['gap'][0], '24px')


class Phase13bCssTests(SiteFixture):
    """Phase 13B: legibility, touch and the stylesheet, read from the published bundle."""

    def font_px(self, node, e):
        """The element's font size in px from its font-size or font shorthand (None when neither applies)."""
        size = computed(node, 'font-size', self.rules, e)
        if size:
            return px(size)
        m = re.search(r'(\d+(?:\.\d+)?)px\s*/', computed(node, 'font', self.rules, e) or '')
        return float(m.group(1)) if m else None

    def test_no_text_rule_under_12_px_applies_on_a_phone_but_the_maps_own_and_two_kept(self):
        # phone-15: 12/16 is the floor of every label, key row, tag, credit tag, day ruler and table head
        e = env(390)
        small = sorted({r.selector for r in self.rules if all(media_matches(q, e) for q in r.media)
                        and any(re.search(r'(^|\s)(1[01]|[0-9])(\.\d+)?px', r.decls.get(p, ('',))[0]) for p in ('font', 'font-size'))})
        # SVG text drawn on a map or a chart (mapkit's .mk-* and .pf-ax, the full-screen scale, the hut numbers), the
        # journal's column heads (not shown on a phone), and the day bar's photo count, which an 80 px chip already cuts
        # off at 11 px (listed in the log)
        self.assertEqual([x for x in small if not x.startswith(('.mk-', '.pf-'))], ['.fs-sc-t', '.mul-dn-c', '.mul-hut text', '.ser-cols'])
        for url, cls in (('', 't-label'), (trip_url('story'), 'keyrow'), (trip_url('story'), 'eltab')):
            for n in page_doc(url).find_all(cls=cls)[:3]:
                self.assertGreaterEqual(self.font_px(n, e) or 12, 12, (url, cls))

    def test_every_hover_rule_waits_for_a_pointer_that_hovers(self):
        # gap1-06: a touch screen keeps :hover after a tap; every :hover rule is inside @media (hover: hover), and the
        # states it used to share a selector list with (.is-map-hl, aria-checked / aria-current) stand outside it
        hov = [r for r in self.rules if ':hover' in r.selector]
        self.assertGreater(len(hov), 50)
        self.assertEqual([r.selector for r in hov if '(hover: hover)' not in r.media], [])
        outside = {r.selector for r in self.rules if '(hover: hover)' not in r.media}
        self.assertIn('.arc-row.is-map-hl a', outside)
        self.assertIn('.sec-seg-a:is([aria-checked="true"], [aria-current="true"])', outside)
        touch = dict(env(390), hover='none')
        seg = Doc('<nav class="sec-seg"><a class="sec-seg-a" href="#x">x</a></nav>').find('a')
        self.assertIsNone(self.hovered_value(seg, 'background', touch))

    def hovered_value(self, node, prop, e):
        for r in self.rules.declaring(prop):
            if ':hover' not in r.selector or r.parts is None or not all(media_matches(q, e) for q in r.media):
                continue
            parts = [(comb, [x for x in simples if x[:2] != ('pc', 'hover')]) for comb, simples in r.parts]
            if matches(node, parts):
                return r.decls[prop][0]
        return None

    def test_route_red_stays_on_the_route(self):
        # visual-09: no hover turns a link route red; plain text links hover in ink with a 1 px underline 3 px down
        self.assertEqual([r.selector for r in self.rules if ':hover' in r.selector
                          and any('route-ink' in v for v, _imp in r.decls.values())], [])
        plain = [r for r in self.rules if r.selector.startswith(':is(.prose, .hom-also') and r.selector.endswith(' a:hover')]
        self.assertEqual(len(plain), 1)
        self.assertEqual({k: v[0] for k, v in plain[0].decls.items()},
                         {'color': 'var(--ink)', 'text-decoration': 'underline', 'text-decoration-thickness': '1px', 'text-underline-offset': '4px'})

    def test_chips_and_tags_grow_with_their_words(self):
        # a11y-10: min-height, never a fixed height, so a text-only zoom does not spill the words
        for sel in ('.chip--title', '.tag', '.tcard-act .tag', '.gcard-tags .tag', '.arc-table .tag', '.trx-chip'):
            stated = [r for r in self.rules if r.selector == sel]
            with self.subTest(sel):
                self.assertTrue(stated)
                self.assertEqual([r.decls['height'][0] for r in stated if 'height' in r.decls], [])
                self.assertTrue(any('min-height' in r.decls for r in stated))

    def test_the_year_heads_of_trips_and_the_map_page_are_heads_and_the_tick_lists_stay_labels(self):
        # visual-04
        year = page_doc('trips/').find('section', cls='trx-yr').find('h2')
        for w, size in ((390, '22px/28px'), (800, '24px')):
            e = env(w)
            got = computed(year, 'font', self.rules, e) if w < 760 else computed(year, 'font-size', self.rules, e)
            self.assertIn(size, got)
            self.assertEqual(computed(year, 'text-transform', self.rules, e), 'none')
        tick = page_doc('tick-list/').find('div', cls='trx-yr-h').find('h2')
        self.assertEqual(computed(tick, 'font', self.rules, env(390)), '500 12px/16px var(--sans)')
        self.assertEqual(computed(tick, 'text-transform', self.rules, env(390)), 'uppercase')
        arc = page_doc('map/').find('div', cls='arc-yr-h').find('h3')
        self.assertIn('22px/28px', computed(arc, 'font', self.rules, env(390)))

    def test_a_card_without_a_photo_fills_its_slot_with_its_tile(self):
        # visual-01, step 1
        tiles = [a for url in ('trips/', '') for a in page_doc(url).find_all('a', cls='tcard-img--tile')]
        e = env(1280)
        if tiles:
            a = tiles[0]
            self.assertEqual((computed(a, 'background', self.rules, e), computed(a, 'border', self.rules, e)), ('var(--map-paper)', '0'))
            gl = a.find('img')
            self.assertEqual([computed(gl, p, self.rules, e) for p in ('width', 'height', 'object-fit')], ['100%', '100%', 'contain'])
        stated = {r.selector: r.decls for r in self.rules if r.selector in ('.tcard-img--tile', '.hom-card-img--tile')}
        self.assertEqual(stated['.tcard-img--tile']['background'][0], 'var(--map-paper)')
        self.assertEqual(stated['.hom-card-img--tile']['background'][0], 'var(--map-paper)')

    def test_the_dead_rules_are_gone_and_about_uses_the_leader_list(self):
        # visual-10
        self.assertEqual([r.selector for r in self.rules if re.search(r'\.(t-h4|photos|prow|abo-dl)\b', r.selector)], [])
        self.assertIsNone(getattr(core, 'phone_row', None))
        self.assertEqual(len(page_doc('about/').find_all('dl', cls='dl-leader')), 1)
        lede = [r for r in self.rules if r.selector == '.t-lede']
        self.assertEqual(lede[0].decls['font'][0], '400 26px/1.25 var(--serif)')

    def test_the_print_sheet_comes_last_and_hides_the_chrome(self):
        # visual-13
        css = importlib.import_module('build').css_bundle()
        self.assertTrue(css.rstrip().endswith('.prose a[href^="http"]::after { content: " (" attr(href) ")"; }\n}'), css[-200:])
        printed = [r for r in self.rules if r.media and 'print' in r.media[0]]
        hidden = {r.selector for r in printed if r.decls.get('display', ('',))[0] == 'none'}
        for sel in ('.site-h', '.site-f', '.bbar', '.menu', '.skip', '.rep-actions', '.rep-toc', '.rep-share', '.rep-related', '.pager', '.copy'):
            self.assertIn(sel, hidden)
        self.assertEqual(max(r.order for r in self.rules), max(r.order for r in printed))

    def test_links_in_ink_keep_a_hover_and_the_viewers_file_link_stays_light(self):
        # the review of Phase 13B: an .alink, the site's name and a title chip had only the route-red hover; the
        # viewer's 'Open the file' would have turned ink on its dark backdrop
        hov = {r.selector: {k: v[0] for k, v in r.decls.items()} for r in self.rules if ':hover' in r.selector}
        self.assertEqual(hov['.alink:hover']['text-decoration'], 'underline')
        self.assertEqual(hov['.site-h .brand:hover .brand-n']['text-decoration'], 'underline')
        self.assertEqual(hov['a.chip--title:hover']['border-color'], 'var(--ink)')
        self.assertEqual(hov['.lb-file:hover']['color'], '#fff')

    def test_under_360_px_the_credit_tag_wraps_clear_of_the_scale(self):
        tag = Doc('<div class="mv mv--phone"><span class="mv-attrib">© OSM · Not for navigation</span></div>').find('span')
        self.assertEqual(computed(tag, 'max-width', self.rules, env(320)), '150px')
        self.assertEqual(computed(tag, 'white-space', self.rules, env(320)), 'normal')
        self.assertEqual(computed(tag, 'height', self.rules, env(360)), '20px')

    def test_the_print_sheet_leaves_out_the_controls_and_keeps_a_day_whole(self):
        printed = {}
        for r in self.rules:
            if r.media and 'print' in r.media[0]:
                printed.setdefault(r.selector, {}).update({k: v[0] for k, v in r.decls.items()})
        for sel in ('.mul-dnav', '.mul-dgpx', '.ser-mnav', '.map-full', '.mv-fs'):
            self.assertEqual(printed[sel]['display'], 'none', sel)
        for sel in ('.mul-rail', '.mul-ds', '.jrow', '.map'):
            self.assertEqual(printed[sel]['break-inside'], 'avoid', sel)
        self.assertEqual(printed['.jph img']['max-height'], '3.4in')
        self.assertEqual(printed['h2']['break-after'], 'avoid')

    def test_a_filter_band_fades_at_its_edge_and_scrolls_its_choice_into_the_row(self):
        # qa-10
        def decl(sel, prop):
            return [r.decls[prop][0] for r in self.rules if r.selector == sel and prop in r.decls]
        self.assertEqual(decl('.sec-band', 'position'), ['relative'])
        self.assertEqual(decl('.sec-band.is-scroll:not(.is-end)::after', 'opacity'), ['1'])
        self.assertEqual(decl('.sec-band-in', 'scroll-snap-type'), ['x proximity'])
        js = source('js', 'pages', 'section.js')
        self.assertNotIn('scrollIntoView', Script(js).text)             # the code, its comments aside
        # a segment cut at an edge or under the fade goes to the row's start, the snap point the row holds it to
        self.assertIn('if (l < row.scrollLeft + 16 || r > row.scrollLeft + row.clientWidth - 32) row.scrollLeft = l - 16;', js)
        self.assertIn("band.classList.toggle('is-end'", js)


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

    def test_the_search_buttons_and_the_filters_button(self):
        # Phase 7: the search button of the header's and the menu's box (core.search_form), the 404 page's, and the
        # phones' Filters button of the Trips page and the tick list (trips.more_button)
        go = self.nodes('', cls='nav-go', tag='button')
        self.assertEqual(len(go), 2)                                  # the header's and the menu's
        self.assertTargets('', go, inline=True, widths=(320,) + WIDTHS)
        self.assertEqual(page_doc('trips/').find_all('button', cls='nav-go'), [])     # trips/ has its own box
        self.assertTargets('404.html', self.nodes('404.html', cls='nf-go', tag='button'), widths=(320,) + WIDTHS)
        self.assertTargets('404.html', self.nodes('404.html', cls='nf-q', tag='input'), widths=(320,) + WIDTHS)
        for url in ('trips/', 'tick-list/'):
            self.assertTargets(url, self.nodes(url, cls='trx-more-btn', tag='button'), widths=(320, 390, 759))

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
        # none since Phase 13B removed the phone row (.prow, core.phone_row), which no page wrote
        self.assertEqual(found, [])
        self.assertEqual([r.selector for r in self.rules if re.search(r'cover-img\s*[+~]|[+~]\s*\.?(?:cover-img|img)\b', r.selector)], [])
        for url in sorted(self.pages):
            for pic in page_doc(url).find_all('picture'):
                self.assertEqual(pic['class'], 'cover-pic', url)
                self.assertEqual([n.tag for n in pic.elements()][-1], 'img')

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
                            (trip_url('tour'), 'rep-title'), (trip_url('journal'), 'rep-title'),
                            (REGION_PAGES[0], 'reg-head'), (REGION_PAGES[1], 'reg-head')):      # contract-phase5.md: .reg-head has the room
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
                        self.assertGreaterEqual(min(left, right), 0)
                        if holder == 'reg-head':
                            # a region page widens the area of its short 'Map' crumb sideways (inset-inline, which wins
                            # over the 4 px read here): test_the_map_crumb_of_a_region_page measures how far it reaches
                            self.assertIsNotNone(computed_pseudo(a, 'before', 'inset-inline', self.rules, e))
                        else:
                            self.assertLessEqual(left + right, px(computed(crumbs, 'gap', self.rules, e)))
                            for prop in ('inset-inline', 'inset-inline-start', 'inset-inline-end', 'left', 'right'):
                                self.assertIsNone(computed_pseudo(a, 'before', prop, self.rules, e), prop)      # nothing else moves a side
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

    # ---- contract-phase5.md section 5: the links the region pages brought

    def test_a_region_pages_head_gives_the_breadcrumb_its_room(self):
        # .reg-head: 24 / 32 / 40 px above the crumbs at the 760 and 1200 px breakpoints; the crumbs' hit area reaches
        # 21 px up (base.css), so it stays under the header at every width
        for url in REGION_PAGES:
            head = self.nodes(url, cls='reg-head', tag='section')[0]
            crumbs = head.elements()[0]
            self.assertIn('crumbs', crumbs.classes)
            for width, want in ((320, '24px'), (390, '24px'), (759, '24px'), (760, '32px'), (1024, '32px'), (1199, '32px'), (1200, '40px'), (1300, '40px')):
                e = env(width)
                self.assertEqual(computed(head, 'padding-top', self.rules, e), want, why(head, 'padding-top', self.rules, e))
                self.assertTrue(displayed(crumbs, self.rules, e))                       # shown on a phone too, unlike a report's
                reach = -sides(computed_pseudo(crumbs.find('a'), 'before', 'inset', self.rules, e))[0]
                self.assertLessEqual(reach, px(want))
                self.assertIsNone(computed(head, 'padding', self.rules, e))             # no shorthand takes the room back

    def test_the_map_crumb_of_a_region_page_answers_over_44_px_of_width(self):
        # contract-phase5.md section 5 (REVISED in round 2): .reg-head .crumbs a::before { inset-inline: min(-4px,
        # (100% - 44px) / 2); }. 'Map' is three letters of the crumbs' Mono caps: 23 px wide at 12 px, 25 px at 13 px
        # (from 760 px). Its hit area was 31 to 33 px wide with the 4 px each side every crumb has; it is 44 px now,
        # widened by the same amount on both sides. 'Reports' is wider than 44 px and keeps its 4 px.
        seen = 0
        for url in REGION_PAGES:
            crumbs = self.nodes(url, cls='crumbs', tag='nav', within='reg-head')[0]
            self.assertEqual([(n.tag, n.text()) for n in crumbs.elements()][:4], [('a', 'Reports'), ('span', '/'), ('a', 'Map'), ('span', '/')])
            reports, map_ = crumbs.find_all('a')
            last = crumbs.elements()[-1]
            self.assertEqual((last.tag, last['aria-current'], focusable(last)), ('span', 'page', False))       # no link after 'Map'
            for width in (320,) + WIDTHS:
                e = env(width)
                gap = px(computed(crumbs, 'gap', self.rules, e))
                self.assertEqual(gap, 8.0)
                for a in (reports, map_):
                    with self.subTest(page=url, width=width, link=a.text()):
                        seen += 1
                        inline = pseudo_winner(a, 'before', 'inset-inline', self.rules, e)
                        short = pseudo_winner(a, 'before', 'inset', self.rules, e)
                        self.assertIsNotNone(inline, 'no inset-inline for the hit area of %r' % a)
                        self.assertEqual((inline.selector, short.selector), ('.reg-head .crumbs a::before', '.crumbs a::before'))
                        self.assertEqual(inline.media, ())                                 # at every width
                        # it is the later and more specific declaration: it decides left and right, and the shorthand of
                        # base.css still decides top and bottom (no longhand of either rule says otherwise)
                        self.assertGreater(_key(inline, 'inset-inline'), _key(short, 'inset'))
                        for prop in ('left', 'right', 'inset-inline-start', 'inset-inline-end', 'top', 'bottom', 'inset-block', 'width', 'min-width'):
                            self.assertIsNone(computed_pseudo(a, 'before', prop, self.rules, e), prop)
                        self.assertEqual(sorted(inline.decls), ['inset-inline'])           # the rule says nothing else
                        value = inline.decls['inset-inline'][0]
                        self.assertIsNotNone(widen(value, 23.0), 'not a value this file reads: %s' % value)
                        up, _right, down, _left = (-v for v in sides(short.decls['inset'][0]))
                        self.assertGreaterEqual(up + line_height(crumbs, self.rules, e) + down, 44.0)      # the height is as it was
                        # a 23 px word and a 25 px word: 44 px across, 10.5 and 9.5 px on each side
                        for words, each in ((23.0, 10.5), (25.0, 9.5)):
                            reach = -widen(value, words)
                            self.assertEqual(reach, each)
                            self.assertEqual(words + 2 * reach, 44.0)
                        # never more than 10.5 px each side for a word of 23 px or more, and 44 px across up to 36 px
                        for words in (23.0, 23.4, 24.0, 25.0, 28.0, 30.5, 36.0):
                            reach = -widen(value, words)
                            self.assertLessEqual(reach, 10.5)
                            self.assertGreaterEqual(reach, 4.0)
                            self.assertAlmostEqual(words + 2 * reach, 44.0)
                        # from 36 px on a crumb has the 4 px every crumb has, and a crumb of 44 px or more only that:
                        # 'Reports', seven letters of the same face, is not widened
                        for words in (36.0, 40.0, 43.9, 44.0, 44.1, 54.0, 60.0, 120.0):
                            self.assertEqual(-widen(value, words), 4.0)
                # 'Map' never reaches the area of 'Reports' before it: between the two links are two gaps of the row
                # and the separator, and the two areas reach 10.5 px and 4 px into them, less than the gaps alone
                value = pseudo_winner(map_, 'before', 'inset-inline', self.rules, e).decls['inset-inline'][0]
                for map_words in (23.0, 25.0):
                    for reports_words in (44.0, 54.0, 60.0):
                        self.assertLess(-widen(value, map_words) + -widen(value, reports_words), 2 * gap)
        self.assertEqual(seen, 2 * 2 * 7)
        # the rule is the region head's own: a crumb of a section page or a report keeps the 4 px of base.css
        for url in ('ski/', trip_url('story')):
            for a in self.nodes(url, cls='crumbs', tag='nav')[0].find_all('a'):
                self.assertIsNone(pseudo_winner(a, 'before', 'inset-inline', self.rules, env(1024)))
        # region.css is where it is written
        mine = parse_css(source('css', 'pages', 'region.css'))[0]
        self.assertEqual([(r.selector, r.media, dict((k, v[0]) for k, v in r.decls.items())) for r in mine if 'crumbs' in r.selector],
                         [('.reg-head .crumbs a::before', (), {'inset-inline': 'min(-4px, (100% - 44px) / 2)'})])

    def test_the_stats_line_of_a_region_page_breaks_after_the_counts(self):
        # .reg-stats .ml-br is shown at every width: counts and years on one line, places on the next
        slot = self.nodes(REGION_PAGES[0], cls='ml-br', tag='span', within='reg-stats')
        self.assertEqual(len(slot), 1)
        other = Doc('<p class="t-mono-s"><span class="ml"><span class="ml-br" aria-hidden="true"></span></span></p>').find('span', cls='ml-br')
        for width in (320,) + WIDTHS:
            e = env(width)
            self.assertEqual(computed(slot[0], 'display', self.rules, e), 'block', why(slot[0], 'display', self.rules, e))
            self.assertEqual(computed(other, 'display', self.rules, e), 'none')          # a break slot is off unless a page shows it

    def test_a_place_in_a_region_pages_head_may_wrap_and_nothing_else_of_the_line(self):
        # contract-phase5.md section 3.1 (REVISED in round 2): a place is free text, so its item carries .mi-w and may
        # wrap at its spaces when it alone is wider than the line (base.css: .ml > .mi-w); the counts and the years stay
        # one item on one line each. region.css takes none of that back
        stats = self.nodes(REGION_PAGES[0], cls='reg-stats', tag='p')[0]
        items = stats.find_all('span', cls='mi')
        places = [mi for mi in items if 'mi-w' in mi.classes]
        self.assertEqual(len(places), 2)                                      # the journal's place and the story's
        self.assertIn(', SYNTHETIC BASIN', [mi.text() for mi in places])
        self.assertEqual(len(items) - len(places), 4)                         # reports, kinds, planned routes, years
        self.assertEqual(items[-len(places):], places)                        # the places are the line's last items
        for width in (320,) + WIDTHS:
            e = env(width)
            for mi in items:
                self.assertEqual(computed(mi, 'white-space', self.rules, e), 'normal' if mi in places else 'nowrap',
                                 why(mi, 'white-space', self.rules, e))
            for node in (stats, stats.find('span', cls='ml')):
                for prop in ('white-space', 'overflow', 'overflow-x', 'min-width', 'width', 'text-overflow'):
                    self.assertIsNone(computed(node, prop, self.rules, e), why(node, prop, self.rules, e))
            self.assertEqual(computed(stats.find('span', cls='ml'), 'flex-wrap', self.rules, e), 'wrap')       # items go to a new line whole
        for mi in places:
            self.assertNotIn('\xa0', mi.text(clean=False))                    # ... and a place has a space to break at

    def test_one_word_of_a_place_too_long_for_a_line_breaks_instead_of_widening_the_page(self):
        # Round 3: .reg-stats .mi-w { overflow-wrap: anywhere; }. A place wraps at its spaces (the test above), but a
        # single word wider than the line has no space to wrap at: its least width held the head, and so the page, open
        # (a long compound name at 320 px). `anywhere` lets the word break and, unlike break-word, takes it out of the
        # least width the flex line works with. The rule is for the places of a region page's head and for nothing else,
        # and the places keep base.css's white-space: they still wrap at a space first
        url = REGION_PAGES[0]
        stats = self.nodes(url, cls='reg-stats', tag='p')[0]
        items = stats.find_all('span', cls='mi')
        places = [mi for mi in items if 'mi-w' in mi.classes]
        others = [mi for mi in items if mi not in places]
        self.assertEqual((len(places), len(others)), (2, 4))
        # the same class outside the head: the places on the cards of the same page, and a meta line of any page
        cards = [n for n in page_doc(url).find_all('span', cls='mi-w') if not inside(n, 'reg-stats')]
        self.assertTrue(cards, '%s has no .mi-w outside its head' % url)
        loose = Doc('<p class="t-mono-s"><span class="ml"><span class="mi mi-w">SYNTHETIC PLACE</span></span></p>').find('span', cls='mi-w')
        bare = Doc('<p class="reg-stats"><span class="ml"><span class="mi">3 REPORTS</span></span></p>').find('span', cls='mi')
        for width in (320,) + WIDTHS:
            for scripting in ('enabled', 'none'):
                e = env(width, scripting=scripting)
                with self.subTest(width=width, scripting=scripting):
                    for mi in places:
                        self.assertEqual(computed(mi, 'overflow-wrap', self.rules, e), 'anywhere', why(mi, 'overflow-wrap', self.rules, e))
                        self.assertEqual(winner(mi, 'overflow-wrap', self.rules, e).selector, '.reg-stats .mi-w')
                        self.assertEqual(computed(mi, 'white-space', self.rules, e), 'normal', why(mi, 'white-space', self.rules, e))
                        self.assertEqual(winner(mi, 'white-space', self.rules, e).selector, '.ml > .mi-w')
                        # nothing else about how the item breaks or how wide it may be
                        for prop in ('word-break', 'word-wrap', 'hyphens', 'overflow', 'overflow-x', 'text-overflow', 'min-width', 'max-width',
                                     'width', 'flex', 'flex-shrink'):
                            self.assertIsNone(computed(mi, prop, self.rules, e), why(mi, prop, self.rules, e))
                    for node in others + cards + [loose, bare, stats, stats.find('span', cls='ml')]:
                        self.assertIsNone(computed(node, 'overflow-wrap', self.rules, e), '%r: %s' % (node, why(node, 'overflow-wrap', self.rules, e)))
                    for mi in others + [bare]:
                        self.assertEqual(computed(mi, 'white-space', self.rules, e), 'nowrap')     # a count or the years: one piece
                    self.assertEqual(computed(loose, 'white-space', self.rules, e), 'normal')
        # region.css: one rule, outside every media query, with that one declaration; it names no white-space anywhere
        mine = parse_css(source('css', 'pages', 'region.css'))[0]
        self.assertEqual([(r.selector, r.media, dict((k, v[0]) for k, v in r.decls.items())) for r in mine
                          if 'mi-w' in r.selector or 'overflow-wrap' in r.decls or 'word-break' in r.decls],
                         [('.reg-stats .mi-w', (), {'overflow-wrap': 'anywhere'})])
        self.assertEqual([r.selector for r in mine if 'white-space' in r.decls], [])
        # base.css: the rule the places lean on is where it was, and is the only thing base.css says of .mi-w
        base = parse_css(source('css', 'base.css'))[0]
        self.assertEqual([(r.selector, r.media, dict((k, v[0]) for k, v in r.decls.items())) for r in base if 'mi-w' in r.selector],
                         [('.ml > .mi-w', (), {'white-space': 'normal'})])
        # and in the stylesheet as published no other rule gives a .mi-w a way to break
        self.assertEqual([r.selector for r in self.rules if 'mi-w' in r.selector and ('overflow-wrap' in r.decls or 'word-break' in r.decls)],
                         ['.reg-stats .mi-w'])

    def hovered(self, node, prop, e):
        """(value, selector) of the declaration of `prop` that wins for the element while the pointer is over it: the
        cascade as computed() reads it, with :hover taken as holding for the element and what is around it."""
        best = None
        for r in self.rules.declaring(prop):
            if r.parts is None or not all(media_matches(q, e) for q in r.media):
                continue
            parts = [(comb, [x for x in simples if x[:2] != ('pc', 'hover')]) for comb, simples in r.parts]
            if matches(node, parts) and (best is None or _key(r, prop) >= _key(best, prop)):
                best = r
        return (best.decls[prop][0], best.selector) if best else (None, None)

    def test_the_region_name_link_of_the_home_page(self):
        # The name is one 16 px line of the caption, as before the phase; as a link it answers over 44 px, and since
        # Phase 13C (a11y-03) the link's own box is 44 px: padding above and below its line, taken back by negative
        # margins, so no box of the home page moves (Lighthouse measures the element, not a ::before area). Only a
        # region with a page has the link. REVISED in round 2: the link is an inline-block (as high as its 16 px line)
        # and lies above the count line under it (z-index). Round 3: where the caption is two lines (below 1200 px) the
        # area is 14 px above and below the line (16 + 14 + 14 = 44); where it is one line (from 1200 px) the map
        # starts 13 px under the name, so the area sits 2 px higher there: 16 px above and 12 px below, 44 px as before
        links = self.nodes('', tag='a', within='hom-reg-n')
        self.assertEqual([a['href'] for a in links], ['regions/synthetic-range/'])
        a = links[0]
        h3 = a.parent
        self.assertEqual((h3.tag, h3.classes, h3.elements()), ('h3', ['hom-reg-n'], [a]))
        head = h3.parent
        self.assertIn('hom-reg-h', head.classes)
        count, open_map = head.elements()[1], head.elements()[2]
        self.assertEqual((count.classes, open_map.classes), (['t-mono-s', 'hom-reg-c'], ['hom-reg-a']))
        block = head.parent
        # the map is the next thing in the block: it starts where the caption's lower padding ends
        self.assertEqual([(n.tag, n.classes) for n in block.elements()], [('div', ['hom-reg-h']), ('div', ['map'])])
        the_map = block.elements()[1]
        regions = block.parent
        self.assertIn('hom-regions', regions.classes)
        # The one length here that the stylesheet does not state. From 1200 px the caption is one line of three items set
        # on a common baseline (align-items: baseline): the name at 12/16 px, the count at 13/18 px and 'Open the map' at
        # 14/20 px. The line is as high as the tallest of them needs, so the name's own 16 px line ends a little above
        # the caption's content edge: by how much depends on the fonts' metrics, which this reader does not have. In a
        # browser the name's box ends 13 px above the map: the caption's 12 px of padding and that 1 px (home.css says
        # so beside the rule; measured in Chrome at 1200 and 1440 px, with the site's own fonts loaded)
        MAP_UNDER_NAME = 13.0
        for width in sorted(set((320, 1199, 1200) + WIDTHS)):
            e = env(width)
            one_line = width >= 1200
            with self.subTest(width=width):
                line = line_height(h3, self.rules, e)
                self.assertEqual(line, 16.0)
                # An inline-block: its box is the line it stands in, the heading's 16 px (the link sets no line height,
                # font or height of its own, so it has the heading's). As an inline box it was the font's content area,
                # about 14 px of a 12 px face, and 14 px above and below that came to 42 px
                self.assertEqual(computed(a, 'display', self.rules, e), 'inline-block', why(a, 'display', self.rules, e))
                # 16 + 14 + 14, or 16 + 16 + 12: the link's own box, never wider than its words (no inline padding)
                pad = [px(v) for v in computed(a, 'padding-block', self.rules, e).split()]
                up, down = (pad[0], pad[-1])
                self.assertEqual((up, down), (16.0, 12.0) if one_line else (14.0, 14.0), why(a, 'padding-block', self.rules, e))
                self.assertEqual(line + up + down, 44.0)
                # ... and the margins take it back, so the caption, the count under the name and the map stay where they were
                self.assertEqual([px(v) for v in computed(a, 'margin-block', self.rules, e).split()], [-up, -down] if one_line else [-up])
                for prop in ('padding', 'padding-inline', 'padding-top', 'padding-bottom', 'margin', 'margin-top', 'margin-bottom', 'min-height',
                             'height', 'max-height', 'line-height', 'font', 'font-size', 'font-weight', 'letter-spacing', 'float', 'inset',
                             'top', 'bottom', 'left', 'right', 'vertical-align', 'overflow', 'transform'):
                    self.assertIsNone(computed(a, prop, self.rules, e), why(a, prop, self.rules, e))
                self.assertIsNone(computed_pseudo(a, 'before', 'content', self.rules, e))   # no ::before area any more
                # Where the caption is two lines the lower 14 px of the area lie over the count line under the name,
                # whose items are positioned (.ml > .mi) and come later in the page: they would take the presses there.
                # The link is a layer above them (z-index: 1), and nothing of the caption has a z-index to answer it with
                self.assertEqual(computed(a, 'z-index', self.rules, e), '1', why(a, 'z-index', self.rules, e))
                items = count.find_all('span', cls='mi')
                self.assertTrue(items)
                self.assertEqual({computed(mi, 'position', self.rules, e) for mi in items}, {'relative'})
                for node in [head, h3, count, open_map] + list(count.walk()):
                    self.assertIsNone(computed(node, 'z-index', self.rules, e), why(node, 'z-index', self.rules, e))
                self.assertIsNone(computed_pseudo(a, 'before', 'z-index', self.rules, e))            # the area is inside the link's own layer
                self.assertEqual(computed(a, 'color', self.rules, e), 'inherit')         # the heading's colour, not a link's
                self.assertEqual(computed(a, 'text-decoration', self.rules, e), 'none')  # the reset every link has: underlined on hover only
                # under the pointer it is ink, the heading's colour, and underlined: since Phase 13B (visual-09) the one hover
                # of a plain text link (before, base.css gave every other link the route colour, and this one kept its own)
                self.assertEqual(self.hovered(a, 'color', e), ('var(--ink)', ':is(.prose, .hom-also, .hom-reg-n, .f-nav, .menu-list, .crumbs, '
                                                               '.c-day, .mul-di, .mul-st-r, .ser-mnav, .goal-refs) a:hover'))
                self.assertEqual(self.hovered(a, 'text-decoration', e), ('underline', '.hom-reg-n a:hover'))
                self.assertEqual(self.hovered(open_map, 'color', e)[1], 'a:hover')        # the link beside it is as it was
                # the heading keeps the type it had
                self.assertEqual(computed(h3, 'font', self.rules, e), '600 12px/16px var(--sans)')
                # 'Open the map' is the 44 px box it was, in its own column or pulled into the line from 1200 px
                self.assertEqual(min_block(open_map, self.rules, e), 44.0)
                # nothing pulls the map up into the caption, or pushes the caption's padding out of the way
                for node, props in ((the_map, ('margin', 'margin-block', 'margin-top', 'top', 'inset', 'transform')),
                                    (head, ('padding', 'padding-block', 'margin', 'margin-block', 'margin-bottom', 'height', 'max-height', 'overflow'))):
                    for prop in props:
                        self.assertIsNone(computed(node, prop, self.rules, e), why(node, prop, self.rules, e))
                if one_line:
                    # one caption line, its three items on one baseline; the 44 px link is pulled in by 14 px above and
                    # below, so it adds 16 px to the line, as the name does
                    self.assertEqual(computed(open_map, 'margin-block', self.rules, e), '-14px')
                    self.assertEqual((computed(head, 'display', self.rules, e), computed(head, 'align-items', self.rules, e)), ('flex', 'baseline'))
                    # Under the name there is the caption's padding and then the map. The area's 12 px end inside that
                    # padding whatever the baseline leaves between the name and the caption's edge, so it never lies
                    # over the map; the 14 px of the narrower widths would end 1 px inside it (2 px outside the padding)
                    padding = px(computed(head, 'padding-bottom', self.rules, e))
                    self.assertEqual(padding, 12.0, why(head, 'padding-bottom', self.rules, e))
                    self.assertLessEqual(down, padding)
                    self.assertLess(down, MAP_UNDER_NAME)
                    self.assertLessEqual(padding, MAP_UNDER_NAME)                         # the measured gap is the padding and a little more
                    # above the name: the 24 px between the section's heading and the two maps (both captions are in
                    # the first row), which hold nothing that answers
                    self.assertLessEqual(up, px(computed(regions, 'margin-top', self.rules, e)))
                    self.assertEqual(computed(regions, 'grid-template-columns', self.rules, e), 'repeat(2, minmax(0, 1fr))')
                else:
                    # the name above the count, 'Open the map' beside both: below the name there is the gap and the
                    # count's own line before the caption ends, above it the space between two blocks
                    self.assertEqual(computed(head, 'display', self.rules, e), 'grid')
                    self.assertLessEqual(down, px(computed(head, 'row-gap', self.rules, e)) + line_height(count, self.rules, e))
                    self.assertLessEqual(up, px(computed(regions, 'gap', self.rules, e)))
        # the rule is written for the link, so a name without a page (plain text in the h3) is untouched
        plain = Doc('<div class="hom-reg-h"><h3 class="hom-reg-n">Synthetic Plain</h3></div>').find('h3')
        for prop in ('position', 'z-index', 'display'):
            self.assertIsNone(computed(plain, prop, self.rules, env(390)))
        # home.css says all of it in one rule for the link, and moves its padding in one more: in the block that makes
        # the caption one line (where .hom-reg-h becomes a flex row); there is no ::before area any more (Phase 13C)
        mine = parse_css(source('css', 'pages', 'home.css'))[0]
        own = [(r.media, dict((k, v[0]) for k, v in r.decls.items())) for r in mine if r.selector == '.hom-reg-n a']
        self.assertEqual(own, [((), {'display': 'inline-block', 'padding-block': '14px', 'margin-block': '-14px', 'position': 'relative',
                                     'z-index': '1', 'color': 'inherit'}),
                               (('(min-width: 1200px)',), {'padding-block': '16px 12px', 'margin-block': '-16px -12px'})])
        self.assertEqual([r.selector for r in mine if r.selector == '.hom-reg-n a::before'], [])
        rows = [r for r in mine if r.selector == '.hom-reg-h' and r.decls.get('display', ('',))[0] == 'flex']
        self.assertEqual([(r.media, r.decls['padding-bottom'][0], r.decls['align-items'][0]) for r in rows],
                         [(own[1][0], '12px', 'baseline')])

    def test_the_panel_link_to_a_region_page(self):
        # a.alink.arc-reg-a under the rows of a Map page panel: an .alink (44 px high, a real box), 4 px under the list
        links = self.nodes('map/', cls='arc-reg-a', tag='a')
        self.assertEqual([a['href'] for a in links], ['../regions/synthetic-range/', '../regions/synthetic-mesa/'])
        self.assertTargets('map/', links, widths=(320,) + WIDTHS)
        for width in (320,) + WIDTHS:
            e = env(width)
            for a in links:
                self.assertIn('arc-inreg', a.parent.classes)
                self.assertEqual(computed(a, 'display', self.rules, e), 'inline-flex')
                self.assertEqual(computed(a, 'margin-top', self.rules, e), '4px')
                self.assertIsNone(computed(a, 'margin-left', self.rules, e))             # no 'Show all' button beside it here
                self.assertSizeUntouched(a, e)
        # the link is the Map page's alone (REVISED in round 2: a region page has no link to itself)
        for url in REGION_PAGES:
            self.assertEqual(page_doc(url).find_all('a', cls='arc-reg-a'), [])
        # beside a 'Show all' button, once archive.js has shown it, and after the hidden one it is without JavaScript
        shown = Doc('<div class="arc-inreg"><ol class="arc-rows arc-collapsed" id="arc-rows-x"></ol>'
                    '<button type="button" class="alink arc-all-btn" aria-expanded="false" aria-controls="arc-rows-x">Show all 9</button>'
                    '<a class="alink arc-reg-a" href="../regions/x/">All Synthetic reports</a></div>')
        hidden = Doc('<div class="arc-inreg"><ol class="arc-rows" id="arc-rows-x"></ol>'
                     '<button type="button" class="alink arc-all-btn" aria-expanded="false" aria-controls="arc-rows-x" hidden>Show all 9</button>'
                     '<a class="alink arc-reg-a" href="../regions/x/">All Synthetic reports</a></div>')

        def between(doc, e):
            """The px the stylesheet puts between the button and the link that follows it on one line."""
            button, link = doc.find('button'), doc.find('a')
            return (px(computed(button, 'margin-right', self.rules, e) or '0px') or 0.0) + (px(computed(link, 'margin-left', self.rules, e) or '0px') or 0.0)

        for width in (320,) + WIDTHS:
            e = env(width)
            self.assertEqual(between(shown, e), 24.0)                                    # 24 px to the left of the link, after a shown button
            self.assertEqual(between(hidden, e), 0.0)                                    # without JavaScript the button is not there
            for doc in (shown, hidden):
                self.assertEqual(min_block(doc.find('a'), self.rules, e), 44.0)
                self.assertEqual(computed(doc.find('button'), 'margin-top', self.rules, e), '4px')      # the button is where it was
                self.assertEqual(min_block(doc.find('button'), self.rules, e), 44.0)
                self.assertIsNone(computed(doc.find('button'), 'margin-left', self.rules, e))

    def test_the_show_all_button_of_a_region_pages_list(self):
        # REVISED in round 2: a region page has the Map page's list, so a region with more than nine trips has its
        # 'Show all N' button. As generated the button is off the page (the hidden attribute) and every row is on it;
        # archive.js collapses the list (.arc-collapsed) and shows the button, 44 px high, 4 px under the rows
        url = REGION_PAGES[0]
        (button,) = self.nodes(url, cls='arc-all-btn', tag='button')
        box = button.parent
        # no link beside it here; the p is the panel's live region (Phase 12, the legend's 'N of M reports')
        self.assertEqual((box.classes, [n.tag for n in box.elements()]), (['arc-inreg'], ['div', 'p', 'ol', 'button']))
        ol = box.find('ol')
        self.assertEqual((ol['id'], button['aria-controls'], ol.classes), ('arc-rows-' + RS, 'arc-rows-' + RS, ['arc-rows']))
        rows = ol.elements()
        more = [li for li in rows if 'arc-more' in li.classes]
        self.assertEqual((len(rows), len(more)), (12, 4))
        self.assertTargets(url, [button], widths=(320,) + WIDTHS)
        for width in (320,) + WIDTHS:
            for scripting in ('enabled', 'none'):
                e = env(width, scripting=scripting)
                with self.subTest(width=width, scripting=scripting):
                    # the attribute wins over the display .alink gives the button (base.css: [hidden], !important)
                    self.assertFalse(displayed(button, self.rules, e))
                    self.assertIs(hidden_by(button, self.rules, e), button)
                    self.assertEqual(computed(button, 'display', self.rules, e), 'none')
                    for li in rows:
                        self.assertTrue(displayed(li, self.rules, e), '%r at %d px' % (li, width))
                        self.assertTrue(displayed(li.find('a'), self.rules, e))
                    self.assertIsNone(computed(button, 'margin-right', self.rules, e))        # the 24 px belong to a shown button
        self.assertNotIn('arc-collapsed', self.pages[url])                                  # the script's class is never generated
        # the same box as archive.js leaves it: the list collapsed, the button shown
        html_ = self.pages[url]
        start = html_.index('<div class="arc-inreg">')
        piece = html_[start:html_.index('</button>', start) + len('</button>')] + '</div>'
        self.assertEqual((piece.count('<ol class="arc-rows" '), piece.count(' hidden>Show all 10')), (1, 1))
        after = Doc(piece.replace('<ol class="arc-rows" ', '<ol class="arc-rows arc-collapsed" ').replace(' hidden>Show all 10', '>Show all 10'))
        shown, list_ = after.find('button'), after.find('ol')
        self.assertNotIn('hidden', shown)
        for width in (320,) + WIDTHS:
            e = env(width)
            with self.subTest(width=width, state='after archive.js'):
                self.assertTrue(displayed(shown, self.rules, e))
                self.assertEqual(computed(shown, 'display', self.rules, e), 'inline-flex')
                self.assertEqual(min_block(shown, self.rules, e), 44.0)
                self.assertEqual(computed(shown, 'margin-top', self.rules, e), '4px')
                self.assertEqual(computed(shown, 'margin-right', self.rules, e), '24px')    # .arc-all-btn:not([hidden]); nothing follows it here
                self.assertIsNone(computed(shown, 'margin-left', self.rules, e))
                self.assertSizeUntouched(shown, e, allowed=('margin', 'margin-right'))
                self.assertEqual([displayed(li, self.rules, e) for li in list_.elements()], [True] * 8 + [False] * 4)
                self.assertEqual([li['data-key'] for li in list_.elements() if not displayed(li, self.rules, e)],
                                 [SLUGS[k] for k in ('spring', 'undated', 'goal', 'idea')])
        # opened again (the class toggled off, aria-expanded true): every row is back, the button stays
        opened = Doc(piece.replace(' hidden>Show all 10', '>Show fewer').replace('aria-expanded="false"', 'aria-expanded="true"'))
        for width in (390, 1024):
            e = env(width)
            self.assertEqual([displayed(li, self.rules, e) for li in opened.find('ol').elements()], [True] * 12)
            self.assertTrue(displayed(opened.find('button'), self.rules, e))
        # archive.css: the two rules of the button's margins, as the Map page has them
        mine = parse_css(source('css', 'pages', 'archive.css'))[0]
        self.assertEqual([(r.selector, dict((k, v[0]) for k, v in r.decls.items())) for r in mine
                          if 'arc-all-btn' in r.selector and any(p.startswith('margin') for p in r.decls)],
                         [('.arc-all-btn', {'margin-top': '4px'}), ('.arc-all-btn:not([hidden])', {'margin-right': '24px'})])

    def test_the_other_regions_links_of_a_region_page(self):
        # the browse-row markup of the Trips page, so its rules apply: 44 px high as a real box, and a hit area at least
        # 44 px wide that moves no link (16 px apart)
        for url in REGION_PAGES:
            nav = self.nodes(url, cls='reg-others', tag='nav')[0]
            links = nav.find_all('a')
            self.assertEqual(len(links), 2)                                # the other region page, then the Map page
            self.assertEqual([inside(a, 'trx-bgroup') for a in links], [True, True])
            self.assertTargets(url, links, widths=(320,) + WIDTHS)
            label = nav.find('span', cls='t-label')
            for width in (320,) + WIDTHS:
                e = env(width)
                with self.subTest(page=url, width=width):
                    self.assertEqual(computed(label, 'line-height', self.rules, e), '44px')
                    self.assertEqual(computed(nav.find('ul'), 'column-gap', self.rules, e), '16px')
                    self.assertEqual(computed(nav.find('div', cls='trx-browse'), 'display', self.rules, e), 'flex')
                    for a in links:
                        self.assertEqual(a.parent.tag, 'li')
                        self.assertSizeUntouched(a, e)
                        self.assertEqual(computed(a, 'display', self.rules, e), 'inline-flex')
                        for words in (28.0, 43.8, 44.0, 96.3, 130.6):
                            wide, high, left, right, up, down = self.hit_box(a, words, 44.0, e)
                            self.assertAlmostEqual(wide, max(words, 44.0))
                            self.assertEqual((high, up, down), (44.0, 0.0, 0.0))
                            self.assertAlmostEqual(left, right)
        # the same rules as the Trips page's own browse links, element for element
        theirs = self.nodes('trips/', tag='a', within='trx-bgroup')[0]
        mine = self.nodes(REGION_PAGES[0], tag='a', within='trx-bgroup')[0]
        for width in (320,) + WIDTHS:
            e = env(width)
            for prop in ('min-height', 'display', 'align-items', 'gap', 'font', 'font-size', 'color', 'position'):
                self.assertEqual(computed(mine, prop, self.rules, e), computed(theirs, prop, self.rules, e), prop)

    def test_the_links_into_the_explorer_are_44_px_and_every_control_is_in_a_known_component(self):
        for url in REGION_PAGES:
            marked = [n for n in self.nodes(url, cls='reg-x') if 'reg-acts' not in n.classes]
            links = [n.find('a') for n in marked]
            self.assertTrue(all('alink' in a.classes for a in links))
            self.assertTargets(url, links, widths=(320,) + WIDTHS)
            for n in marked:
                for width in (320,) + WIDTHS:
                    self.assertEqual(computed(n, 'margin-top', self.rules, env(width)), '12px')
            # the activities line's links (Phase 12): 44 px tall inline-flex items in a Mono-S line
            acts = page_doc(url).find('p', cls='reg-acts').find_all('a', cls='reg-act')
            self.assertTrue(acts)
            for a in acts:
                for width in (320,) + WIDTHS:
                    e = env(width)
                    self.assertEqual((computed(a, 'display', self.rules, e), computed(a, 'min-height', self.rules, e)),
                                     ('inline-flex', '44px'))
        # every link and button a region page has in <main> that is not one line of running text has a 44 px box or a
        # hit area of its own: rows, cards, chips, the crumbs, the browse links. What is new here is listed above; the
        # rest are components other pages use and other tests measure. Nothing on the page is a bare text link
        # (REVISED in round 2: the list beside the map is the Map page's, with its 'Show all' button; the first round's
        # link down to the table, a.arc-reg-a, is not on a region page)
        known = ('crumbs', 'arc-rows', 'map', 'tcard', 'arc-filt', 'arc-years', 'rtab', 'trx-bgroup', 'reg-x', 'arc-all-btn')
        met = set()
        for url in REGION_PAGES:
            for node in page_doc(url).by_id('main').walk():
                if node.tag in ('a', 'button'):
                    self.assertTrue(any(inside(node, cls) for cls in known), '%r on %s is in none of the known components' % (node, url))
                    met.update(cls for cls in known if inside(node, cls))
                    self.assertFalse(inside(node, 'arc-reg-a'), '%r on %s' % (node, url))
        self.assertEqual(met, set(known))                    # the fixture's pages have a control of every one of them

    def test_a_region_pages_featured_cards_keep_the_cover_rules(self):
        # ul.reg-cards.tgrid of core.trip_card items: the grid of the report pages' 'More like this' (1 / 2 / 3 columns
        # at 560 and 1200 px), and inside each card the cover rules written for an <img> in its link, which still reach
        # it through the phone-only <picture> wrapper (display: contents)
        grid = self.nodes(REGION_PAGES[0], cls='reg-cards', tag='ul')[0]
        self.assertEqual(grid.classes, ['reg-cards', 'tgrid'])
        cards = grid.elements()
        self.assertEqual([c.classes for c in cards], [['tcard']] * 3)
        for width, columns in ((320, None), (390, None), (559, None), (560, 'repeat(2, minmax(0, 1fr))'), (800, 'repeat(2, minmax(0, 1fr))'),
                               (1199, 'repeat(2, minmax(0, 1fr))'), (1200, 'repeat(3, minmax(0, 1fr))'), (1300, 'repeat(3, minmax(0, 1fr))')):
            e = env(width)
            with self.subTest(width=width):
                self.assertEqual(computed(grid, 'display', self.rules, e), 'grid')
                self.assertEqual(computed(grid, 'grid-template-columns', self.rules, e), columns)
                for card in cards:
                    # a row card on a phone (photo beside the text), a column card from 560 px
                    self.assertEqual(computed(card, 'display', self.rules, e), 'grid' if width < 560 else 'flex')
        pics = grid.find_all('picture')
        self.assertEqual([p['class'] for p in pics], ['cover-pic', 'cover-pic'])
        covers = grid.find_all('img', cls='cover-img')
        self.assertEqual(len(covers), 3)
        # two covers are wrapped (the story's and the tour's have a card-size copy), one is bare (the crag's)
        self.assertEqual([img.parent.tag for img in covers], ['picture', 'picture', 'a'])
        self.assertEqual([img.parent for img in covers][:2], pics)
        # each wrapper's phone source declares the slot as 106 px (core.CARD_PHONE_SIZES), the <img> string ends with 112 px
        for pic in pics:
            self.assertEqual((pic.find('source')['sizes'], pic.find('source')['media']), ('106px', '(max-width: 559.98px)'))
            self.assertTrue(pic.find('img')['sizes'].endswith(', 112px'))
        for width in (390, 800, 1300):
            e = env(width)
            for pic in pics:
                self.assertEqual(computed(pic, 'display', self.rules, e), 'contents')
            for img in covers:
                holder = img.parent if img.parent.tag == 'a' else img.parent.parent
                self.assertEqual((holder.tag, holder.classes), ('a', ['tcard-img']))
                self.assertEqual(computed(img, 'display', self.rules, e), 'block')
                self.assertEqual(computed(img, 'width', self.rules, e), '100%')
                self.assertEqual(computed(img, 'height', self.rules, e), '100%')
                self.assertEqual(computed(img, 'object-fit', self.rules, e), 'cover')
                self.assertEqual(computed(holder, 'aspect-ratio', self.rules, e), '4 / 3' if width < 560 else '3 / 2')
                self.assertEqual(computed(holder, 'overflow', self.rules, e), 'hidden')
        # region.css asks for no image as a direct child of anything, and sizes no image itself
        mine = parse_css(source('css', 'pages', 'region.css'))[0]
        self.assertEqual([r.selector for r in mine if re.search(r'\b(img|picture)\b|cover-', r.selector)], [])
        self.assertEqual([r.selector for r in mine if '>' in r.selector or '+' in r.selector or '~' in r.selector], [])

    def test_a_region_page_is_set_like_the_pages_it_borrows_from(self):
        # contract-phase5.md section 5: the head is a section page's (the same room above the crumbs, the same Mono line
        # under the h1) and the Featured row is the report pages' 'More like this' grid; region.css repeats those rules
        # under its own names, and this holds the two to each other at every width
        url = REGION_PAGES[0]
        head, stats, h1 = self.nodes(url, cls='reg-head')[0], self.nodes(url, cls='reg-stats')[0], page_doc(url).find('h1')
        sec_head, sec_stats = self.nodes('ski/', cls='sec-head')[0], self.nodes('ski/', cls='sec-stats')[0]
        sec_row = self.nodes('ski/', cls='sec-h1row')[0]
        cards, related = self.nodes(url, cls='reg-cards')[0], self.nodes(trip_url('story'), cls='rep-rel')[0]
        self.assertIn('tgrid', related.classes)
        for width in (320, 360, 390, 559, 560, 600, 759, 760, 800, 1024, 1199, 1200, 1300):
            e = env(width)
            with self.subTest(width=width):
                self.assertEqual(computed(head, 'padding-top', self.rules, e), computed(sec_head, 'padding-top', self.rules, e))
                self.assertEqual(computed(h1, 'margin-top', self.rules, e), computed(sec_row, 'margin-top', self.rules, e))
                for prop in ('margin-top', 'font', 'font-size', 'line-height', 'letter-spacing', 'text-transform', 'color'):
                    self.assertEqual(computed(stats, prop, self.rules, e), computed(sec_stats, prop, self.rules, e), prop)
                    self.assertIsNotNone(computed(stats, 'font', self.rules, e))
                for prop in ('display', 'grid-template-columns', 'gap', 'row-gap', 'margin-top'):
                    self.assertEqual(computed(cards, prop, self.rules, e), computed(related, prop, self.rules, e), prop)

    def test_region_css_is_in_the_published_stylesheet(self):
        mine = parse_css(source('css', 'pages', 'region.css'))
        self.assertEqual(mine[1], [])                                               # the reader reads every selector of it
        published = {(r.selector, r.media) for r in self.rules}
        for r in mine[0]:
            self.assertIn((r.selector, r.media), published)
        # every class it styles is one the region page writes: no rule is left without an element
        html_ = self.pages[REGION_PAGES[0]]
        # (.js is <html>'s class from the head's inline script, not written in the markup: Phase 13A)
        for cls in sorted({m for r in mine[0] for m in re.findall(r'\.([a-z][\w-]*)', r.selector)} - {'js'}):
            self.assertRegex(html_, r'class="[^"]*\b%s\b' % re.escape(cls), '.%s is styled and never written' % cls)

    def test_the_search_placeholder_is_cut_with_an_ellipsis(self):
        rules = parse_css(source('css', 'pages', 'trips.css'))[0]
        box = Doc('<form><input class="trx-q" type="search" placeholder="x"></form>').find('input')
        self.assertEqual(computed(box, 'text-overflow', rules, env(320)), 'ellipsis')
        ph = [r for r in rules if r.selector.replace(' ', '') == '.trx-q::placeholder' and 'text-overflow' in r.decls]
        self.assertEqual([r.decls['text-overflow'][0] for r in ph], ['ellipsis'])
        for url in ('trips/', 'tick-list/'):
            self.assertEqual(len(self.nodes(url, cls='trx-q', tag='input')), 1)

# ---------------------------------------------------------------- forced colours: the units switch

class Phase11Tests(unittest.TestCase):
    """Phase 11: 'Open the full map' (core.map_full_link, gap1-02) is on screen only at 560-1199 px, where the page draws
    the 718 px render larger than drawn; the photo viewer is described by its live region (a11y-14)."""

    def test_open_the_full_map_shows_from_560_to_1199_only(self):
        rules = published_rules()[0]
        a = Doc('<div class="wrap">%s</div>' % core.map_full_link('../../trips/syn-x/map/')).find('a', cls='map-full')
        for width, shown in ((360, False), (390, False), (559, False), (560, True), (800, True), (1024, True), (1199, True),
                             (1200, False), (1300, False)):
            with self.subTest(width=width):
                self.assertEqual(hidden_by(a, rules, env(width)) is None, shown, why(a, 'display', rules, env(width)))

    def test_the_viewer_is_described_by_its_live_region(self):
        dlg = Doc(core.lightbox()).find('dialog', cls='lb')
        self.assertEqual(dlg['aria-describedby'], 'lb-live')
        self.assertEqual(dlg.find('p', cls='sr')['aria-live'], 'polite')


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
        # the header has two switches since Phase 16: the row's and the phone's beside the menu button
        self.assertEqual(got, sorted([(w, c) for w in ('header', 'header', 'menu', 'page') for c in ('false', 'true')]))
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
                          ('body.p-report .site-f', '0', ('(min-width: 760px)',)),
                          # a short or sideways phone's one-row bar (Phase 13A, phone-10): less room, never more than 0 for
                          # a page without the bar, as the clearing rule outweighs it
                          ('body.p-report .site-f', '56px', ('(max-width: 759.98px) and (max-height: 500px)',))])
        clearing = room[1]
        self.assertEqual([r.selector for r in rules if r.order == clearing.order], [clearing.selector])
        self.assertEqual(clearing.decls, {'padding-bottom': ('0', False)})
        self.assertGreater(clearing.spec, room[0].spec)                # it wins wherever it stands in the file
        self.assertNotIn('p-goal', ' '.join(r.selector for r in room))      # one rule for reports and goals: a goal page is p-report too


if __name__ == '__main__':
    unittest.main()
