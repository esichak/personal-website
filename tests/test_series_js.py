"""Phase 3: assets/js/pages/series.js, the script of the journal page.

Four kinds of test:

- The pure helpers (hashTarget, startFiltered, revealId, landAfterLoad, openedDay) run under node through
  tests/series_js_harness.js, and once more on the ids of a generated journal page, so the script and
  sitegen.pages.series cannot drift apart on what a day or a month is called. Skipped when node is not installed (node
  is a dev-only convenience, the production build never runs it).
- The listeners: the same harness runs the whole script against a stand-in for the browser built from a generated
  journal page (page_model), and plays a reader's presses, toggles, hash changes and reloads. Skipped without node.
- The hooks: every element id, selector and data attribute the script looks up is read out of its source (read_hooks,
  indifferent to quote style and whitespace) and resolved on a journal page built from a synthetic fixture
  (hook_problems), so the test fails when the page stops emitting something the script needs; and the class the script
  filters with is held against what assets/css/pages/series.css hides under it. Always runs.
- What the source itself must hold to: it exports for node before touching the DOM, its page code goes through the
  tested helpers, and it never writes markup. Always runs.

Review gate (fix B): the script lists, with each hidden day and month, every id inside it (a day's number and title,
a month's heading), so an address that names one turns the filter off as an address to the day or month does. The
ids are read off the generated page (INNER, inner_ids), the harness plays visits and hash changes to them, and the
script with its collecting lines changed one at a time must fail those checks (BROKEN_COLLECTING). Round 3: each id is
in that list once, also a hidden day that is met again as an id inside its hidden month (ONCE, a check of the harness
like any other; in round 2 it was a known gap).

Phase 11: a fifth pure helper, openedDay (the entry a pressed in-page link names: features-08, 'Continue reading', kept
in localStorage per journal and offered on a later visit), and month-nav links that stay links under the filter (a11y-07:
class is-empty and a ', no write-ups' note the script makes itself instead of aria-disabled and tabindex). read_hooks
also reads the elements the script makes (Hooks.made), so the hook check does not ask the page for that note; the page
model carries each element's text, the parsed form of each selector (for the elements the script makes, which the
stand-in matches itself) and the links and texts the new "dom:" checks press and expect; FAULTS gains 'local'
(localStorage throws on every call, as in a private window).

The stand-in is not a browser: layout, real scrolling, focus and the back/forward cache are still checked by hand
(docs/WEBSITE_IMPLEMENTATION_LOG.md).
"""
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
TESTS = os.path.join(ROOT, 'tests')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
from sitegen import core  # noqa: E402

import helpers  # noqa: E402
from helpers import Doc, photo, LANDSCAPE  # noqa: E402

tearDownModule = helpers.no_region_pages_left      # this module registers a site: no region page may stay registered after it

HARNESS = os.path.join(TESTS, 'series_js_harness.js')
SERIES_JS = os.path.join(ROOT, 'assets', 'js', 'pages', 'series.js')
SERIES_CSS = os.path.join(ROOT, 'assets', 'css', 'pages', 'series.css')
HELPERS = ('hashTarget', 'startFiltered', 'revealId', 'landAfterLoad', 'openedDay')   # contract 10.6 + features-08: the pure exports

# a module with the right exports but wrong answers: the harness must reject it
BAD_STUB = ("module.exports = {hashTarget: function () { return {kind: 'other', id: ''}; },"
            " startFiltered: function () { return true; }, revealId: function () { return ''; },"
            " landAfterLoad: function () { return true; }, openedDay: function () { return 'day-1'; }};\n")
# hashTarget is right, but the filter starts on whatever the hash names: a link to a hidden day would land on nothing
BAD_FILTER = ("function hashTarget(hash) {\n"
              "  var id = decodeURIComponent(String(hash || '').replace(/^#/, ''));\n"
              "  if (!id) return {kind: null, id: ''};\n"
              "  return {kind: id.indexOf('day-') === 0 ? 'day' : (id.indexOf('month-') === 0 ? 'month' : 'other'), id: id};\n"
              "}\n"
              "module.exports = {hashTarget: function (h) { try { return hashTarget(h); } catch (e) { return {kind: 'other', id: String(h)}; } },"
              " startFiltered: function (defaultOn) { return !!defaultOn; }, revealId: function () { return ''; },"
              " landAfterLoad: function () { return false; }, openedDay: function () { return ''; }};\n")
# The real module with one helper replaced (%s: the real file's path as a JavaScript string, then the replacement).
ONE_WRONG = "var real = require(%s);\nmodule.exports = Object.assign({}, real, {%s});\n"
# revealId gone wrong: it reveals although nothing is hidden / never reveals (the second press of a link does nothing)
BAD_REVEAL = ('revealId: function (filtered, hash, hidden) { return real.revealId(true, hash, hidden); }',
              "revealId: function () { return ''; }",
              "revealId: function (filtered, hash) { return filtered ? real.hashTarget(hash).id : ''; }")
# landAfterLoad gone wrong: the reload bug (the navigation type is ignored, or only 'reload' is known), a scroll although
# the list was not shortened, a scroll to any hash
BAD_LAND = ("landAfterLoad: function (filtered, hash) { return real.landAfterLoad(filtered, hash, 'navigate'); }",
            "landAfterLoad: function (filtered, hash, nav) { return real.landAfterLoad(filtered, hash, nav === 'reload' ? nav : ''); }",
            'landAfterLoad: function (filtered, hash, nav) { return real.landAfterLoad(true, hash, nav); }',
            "landAfterLoad: function (filtered, hash, nav) { return !!filtered && !!hash && (!nav || nav === 'navigate'); }")
# The helpers right, their signature not: an argument more, an argument fewer, an export more (the harness's last pure
# check, 'signatures', must say so; every helper's own check passes first)
BAD_SIGNATURE = ('startFiltered: function (defaultOn, hash, hiddenIds, inside) { return real.startFiltered(defaultOn, hash, hiddenIds); }',
                 'revealId: function (filtered, hash) { return real.revealId(filtered, hash, arguments[2]); }',
                 'hashTarget: function (hash, hiddenIds) { return real.hashTarget(hash); }',
                 'landAfterLoad: function (filtered, hash) { return real.landAfterLoad(filtered, hash, arguments[2]); }',
                 'openedDay: function (href) { return real.openedDay(href, arguments[1]); }',
                 'openedDay: function (href, firstDayOf, hiddenIds) { return real.openedDay(href, firstDayOf); }',
                 'insideHidden: function (id, hiddenIds) { return hiddenIds.indexOf(id) !== -1; }')
# openedDay gone wrong (features-08): a month link names the month instead of its first day; any hash names its id; a
# link to another page names the day in its fragment; a month link names its first day without asking firstDayOf
BAD_OPENED = ("openedDay: function (href, firstDayOf) { var t = real.hashTarget(href); return t.kind === 'day' || t.kind === 'month' ? t.id : ''; }",
              "openedDay: function (href, firstDayOf) { var t = real.hashTarget(href); return t.kind === 'month' ? firstDayOf(t.id) || '' : t.id; }",
              "openedDay: function (href, firstDayOf) { return real.openedDay(String(href || '').replace(/^[^#]*/, ''), firstDayOf); }",
              "openedDay: function (href, firstDayOf) { var t = real.hashTarget(href); return t.kind === 'month' ? 'day-1' : real.openedDay(href, firstDayOf); }",
              "openedDay: function (href) { return real.hashTarget(href).kind === 'day' ? real.hashTarget(href).id : ''; }")
# series.js with the lines that collect what the filter hides changed in one way each: (what the change does, the text as
# it is, the text instead). The helpers are untouched, so only the harness's "dom:" checks can tell.
_COLLECT = "    Array.prototype.forEach.call(el.querySelectorAll('[id]'), function (c) { if (hidden.indexOf(c.id) === -1) hidden.push(c.id); });\n"
# the line that lists a hidden day or month itself, once (round 3), and the harness check that holds it to that
_OWN = "    if (el.id && hidden.indexOf(el.id) === -1) hidden.push(el.id);"
ONCE = 'dom: every id the filter hides is listed once, a hidden day inside a hidden month too'
BROKEN_COLLECTING = (
    ('a hidden day or month is listed every time it is met, as in round 2', _OWN, '    if (el.id) hidden.push(el.id);'),
    ('the ids inside a hidden day or month are not collected, as before', _COLLECT, ''),
    ('every id of the day log is collected', "el.querySelectorAll('[id]')", "log.querySelectorAll('[id]')"),
    ('an id inside is collected every time it is met', 'function (c) { if (hidden.indexOf(c.id) === -1) hidden.push(c.id); }',
     'function (c) { hidden.push(c.id); }'),
    ('the hidden day or month itself is left out', 'hidden.push(el.id);', 'void 0;'),
    ('the id of the day or month stands in for the ids inside it', 'hidden.push(c.id); });', 'hidden.push(el.id); });'),
    ('only the first id inside is collected', "Array.prototype.forEach.call(el.querySelectorAll('[id]'), function (c) {",
     "Array.prototype.slice.call(el.querySelectorAll('[id]'), 0, 1).forEach(function (c) {"),
    ('only the last id inside is collected', "Array.prototype.forEach.call(el.querySelectorAll('[id]'), function (c) {",
     "Array.prototype.slice.call(el.querySelectorAll('[id]'), -1).forEach(function (c) {"),
    ('only days are looked into', "    Array.prototype.forEach.call(el.querySelectorAll('[id]'),",
     "    if (el.id.indexOf('day-') === 0) Array.prototype.forEach.call(el.querySelectorAll('[id]'),"),
    ('only months are looked into', "    Array.prototype.forEach.call(el.querySelectorAll('[id]'),",
     "    if (el.id.indexOf('month-') === 0) Array.prototype.forEach.call(el.querySelectorAll('[id]'),"),
)
# the cases the harness kept as known gaps in round 2 ('gap:<name>'); each is a regular check now, and no name is left
FORMER_GAPS = ('once',)
# what the harness's stand-in browser can be told to fail at (its FAULT argument): each stands for a gutted listener
FAULTS = ('hashchange', 'click', 'change', 'store', 'navigation', 'local')


def source():
    with open(SERIES_JS, encoding='utf-8') as fh:
        return fh.read()


def code_only(src):
    """The source without its comments (block comments, then // to the end of a line), so a word in a comment is never
    taken for code."""
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    return re.sub(r'(?m)(^|\s)//.*$', r'\1', src)


# ---------------------------------------------------------------- a small CSS selector matcher over helpers.Node

class Unsupported(Exception):
    """A selector this file's matcher does not understand. The hook check reports it: extend the matcher, do not skip."""


_SEL = re.compile(r'''
      (?P<comma>\s*,\s*)
    | (?P<comb>\s*>\s*|\s+)
    | (?P<tag>[A-Za-z][\w-]*|\*)
    | \#(?P<id>[\w-]+)
    | \.(?P<cls>[\w-]+)
    | \[\s*(?P<attr>[\w:-]+)\s*(?:(?P<op>[~|^$*]?=)\s*(?:"(?P<dq>[^"]*)"|'(?P<sq>[^']*)'|(?P<bare>[^\]\s"']+))\s*)?\]
    | :not\(\s*(?P<neg>[^()]+?)\s*\)
''', re.X)


def parse_selector(text):
    """'a[href^="#"], .x > .y:not(.z)' -> one chain per comma part. A chain is ((combinator, tests), ...) from left to
    right, the combinator being '' for the first compound and ' ' or '>' after it; a test is ('tag', name), ('id', v),
    ('class', v), ('attr', name, op, value) or ('not', tests). Quote style and spacing leave the result unchanged."""
    text = text.strip()
    chains, chain, tests, comb, pos = [], [], [], '', 0
    while True:
        m = _SEL.match(text, pos) if pos < len(text) else None
        if m is None and pos < len(text):
            raise Unsupported('%r, from %r' % (text, text[pos:]))
        if m is None or m.group('comma') is not None or m.group('comb') is not None:
            if not tests:
                raise Unsupported('%r has an empty part' % text)
            chain.append((comb, tuple(tests)))
            tests = []
            if m is None or m.group('comma') is not None:
                chains.append(tuple(chain))
                chain, comb = [], ''
            else:
                comb = '>' if '>' in m.group('comb') else ' '
            if m is None:
                return tuple(chains)
        elif m.group('tag') is not None:
            if tests:
                raise Unsupported('%r, from %r' % (text, text[pos:]))
            tests.append(('tag', m.group('tag').lower()))
        elif m.group('id') is not None:
            tests.append(('id', m.group('id')))
        elif m.group('cls') is not None:
            tests.append(('class', m.group('cls')))
        elif m.group('attr') is not None:
            value = next((v for v in (m.group('dq'), m.group('sq'), m.group('bare')) if v is not None), None)
            tests.append(('attr', m.group('attr'), m.group('op'), value))
        else:
            inner = parse_selector(m.group('neg'))
            if len(inner) != 1 or len(inner[0]) != 1:
                raise Unsupported('%r: :not() of more than one compound' % text)
            tests.append(('not', inner[0][0][1]))
        pos = m.end()


def _attr_ok(have, op, value):
    if have is None:
        return False
    if op is None:
        return True
    if op == '=':
        return have == value
    if op == '^=':
        return bool(value) and have.startswith(value)
    if op == '$=':
        return bool(value) and have.endswith(value)
    if op == '*=':
        return bool(value) and value in have
    if op == '~=':
        return value in have.split()
    return have == value or have.startswith(value + '-')      # |=


def node_matches(node, tests):
    if node.tag.startswith('#'):                              # the parser's own root is not an element
        return False
    for t in tests:
        if t[0] == 'tag':
            ok = t[1] in ('*', node.tag)
        elif t[0] == 'id':
            ok = node['id'] == t[1]
        elif t[0] == 'class':
            ok = t[1] in node.classes
        elif t[0] == 'attr':
            ok = _attr_ok(node[t[1]], t[2], t[3])
        else:
            ok = not node_matches(node, t[1])
        if not ok:
            return False
    return True


def chain_matches(node, chain):
    comb, tests = chain[-1]
    if not node_matches(node, tests):
        return False
    if len(chain) == 1:
        return True
    up = node.parent
    while up is not None:
        if chain_matches(up, chain[:-1]):
            return True
        if comb == '>':
            return False
        up = up.parent
    return False


def unique(nodes):
    seen, out = set(), []
    for n in nodes:
        if id(n) not in seen:
            seen.add(id(n))
            out.append(n)
    return out


def select(scope, chains):
    """querySelectorAll: the descendants of the scope nodes that match any of the parsed chains."""
    return unique(n for s in scope for n in s.walk() if any(chain_matches(n, c) for c in chains))


def closest(node, chains):
    while node is not None:
        if any(chain_matches(node, c) for c in chains):
            return node
        node = node.parent
    return None


# ---------------------------------------------------------------- what series.js looks up, read out of its source

Lookup = collections.namedtuple('Lookup', 'recv fn arg name')     # name: the variable the result is assigned to, or None
Read = collections.namedtuple('Read', 'recv attr value')          # value: what the attribute is compared with, or None
Hooks = collections.namedtuple('Hooks', 'lookups each reads made')   # each: {callback parameter: {collection it walks}}

_NAME = r'[A-Za-z_$][\w$]*'
_RECV = r'(?<![\w$.])(?P<recv>%s(?:\s*\.\s*%s)*?)\s*\.\s*' % (_NAME, _NAME)
_STR = r'''(?P<q>['"`])(?P<arg>(?:(?!(?P=q)).)*)(?P=q)'''
_LOOKUP = re.compile(_RECV + r'(?P<fn>querySelectorAll|querySelector|getElementById|getElementsByClassName|closest|matches)'
                     r'\s*\(\s*' + _STR + r'\s*\)', re.S)
_ATTR = re.compile(_RECV + r'(?:getAttribute|hasAttribute)\s*\(\s*' + _STR + r'\s*\)', re.S)
_DATA = re.compile(_RECV + r'dataset\s*(?:\.\s*(?P<key>%s)|\[\s*%s\s*\])' % (_NAME, _STR)
                   + r'''(?:\s*={2,3}\s*(?P<vq>['"`])(?P<value>(?:(?!(?P=vq)).)*)(?P=vq))?''', re.S)
_EACH = re.compile(r'(?<![\w$.])(?P<coll>%s)\s*\.\s*(?:forEach|map|filter|some|every|find)\s*\(\s*'
                   r'(?:function\s*\(\s*(?P<a>%s)|\(\s*(?P<b>%s)\s*[,)]|(?P<c>%s)\s*=>)' % ((_NAME,) * 4))
_BIND = re.compile(r'\s*(?:(?:var|let|const)\s+)?(%s)\s*=(?!=)' % _NAME)
# an element the script makes itself (Phase 11: a month link's ', no write-ups' note), and the classes it gives it
_MAKE = re.compile(r'(?<![\w$.])(?P<name>%s)\s*=(?!=)\s*document\s*\.\s*createElement\s*\(\s*' % _NAME + _STR + r'\s*\)', re.S)
_CLASSNAME = re.compile(_RECV + r'className\s*=(?!=)\s*' + _STR, re.S)


def read_hooks(code):
    """Everything the (comment-free) script asks the page for, however it is quoted or spaced:
    - lookups: <recv>.querySelector / querySelectorAll / closest / matches('<selector>'), getElementById('<id>') and
      getElementsByClassName('<classes>') with a literal argument, each with the variable its statement assigns to;
    - each: the parameter name a forEach / map / ... callback gives the items of a collection;
    - reads: <recv>.dataset.<key> (with the literal it is compared with, if any) and <recv>.getAttribute('<name>');
    - made: (tag, (classes, sorted)) of each element the script makes, document.createElement('<tag>') assigned to a
      variable whose className is then set to a literal (no className: no classes). A lookup of such an element finds
      nothing on the generated page, and is not asked of it (hook_problems)."""
    lookups = []
    for m in _LOOKUP.finditer(code):
        before = code[:m.start()]
        statement = before[max(before.rfind(c) for c in ';{}') + 1:]
        bound = _BIND.match(statement)
        lookups.append(Lookup(re.sub(r'\s+', '', m.group('recv')), m.group('fn'), m.group('arg'), bound.group(1) if bound else None))
    each = {}
    for m in _EACH.finditer(code):
        each.setdefault(m.group('a') or m.group('b') or m.group('c'), set()).add(m.group('coll'))
    reads = [Read(re.sub(r'\s+', '', m.group('recv')), m.group('arg'), None) for m in _ATTR.finditer(code)]
    for m in _DATA.finditer(code):
        key = m.group('key') or m.group('arg')
        attr = 'data-' + re.sub(r'[A-Z]', lambda c: '-' + c.group(0).lower(), key)
        reads.append(Read(re.sub(r'\s+', '', m.group('recv')), attr, m.group('value')))
    named = {}
    for m in _CLASSNAME.finditer(code):
        named.setdefault(re.sub(r'\s+', '', m.group('recv')), set()).update(m.group('arg').split())
    made = sorted(set((m.group('arg').lower(), tuple(sorted(named.get(m.group('name'), ())))) for m in _MAKE.finditer(code)))
    return Hooks(lookups, each, reads, made)


def signature(hooks):
    """The hooks in a form that does not depend on how the script spells them: selectors parsed, everything sorted."""
    plain = ('getElementById', 'getElementsByClassName')
    lookups = sorted((lk.recv, lk.fn, lk.arg if lk.fn in plain else repr(parse_selector(lk.arg)), lk.name or '') for lk in hooks.lookups)
    reads = sorted((r.recv, r.attr, '(any)' if r.value is None else 'is ' + r.value) for r in hooks.reads)
    return lookups, sorted((k, sorted(v)) for k, v in hooks.each.items()), reads, sorted(hooks.made)


def lookup_result(lk, hooks, root, seen=()):
    """The elements one lookup returns on this page ([] when it finds nothing)."""
    if lk.fn == 'getElementById':
        return [n for n in root.walk() if n['id'] == lk.arg]
    scope = scope_of(lk.recv, hooks, root, seen)
    if lk.fn == 'getElementsByClassName':
        return unique(n for s in (scope or [root]) for n in s.walk() if all(c in n.classes for c in lk.arg.split()))
    chains = parse_selector(lk.arg)
    if scope is None and lk.fn in ('closest', 'matches'):
        return select([root], chains)                      # from an element this file cannot trace: any element may be it
    if lk.fn == 'closest':
        return unique(n for n in (closest(s, chains) for s in scope) if n is not None)
    if lk.fn == 'matches':
        return [s for s in scope if any(chain_matches(s, c) for c in chains)]
    return select([root] if scope is None else scope, chains)


def bindings_of(name, hooks, root, seen=()):
    """Every element list a variable of this name can hold: one per statement that assigns it from a lookup, and one
    per collection whose callback calls its items by this name. [] for a name that is never bound to a lookup."""
    if name in seen:
        return []
    seen = seen + (name,)
    out = [lookup_result(lk, hooks, root, seen) for lk in hooks.lookups if lk.name == name]
    for coll in sorted(hooks.each.get(name, ())):
        out += bindings_of(coll, hooks, root, seen)
    return out


def scope_of(recv, hooks, root, seen=()):
    """The elements a receiver stands for: the document, a traced variable (all its bindings together), or None when it
    cannot be traced (an event target, a property chain)."""
    if recv in ('document', 'window.document'):
        return [root]
    found = bindings_of(recv, hooks, root, seen) if re.match(_NAME + r'\Z', recv) else []
    return unique(n for nodes in found for n in nodes) if found else None


def made_by_the_script(chains, made):
    """True when every part of the selector names an element the script makes itself (hooks.made): one compound of its
    tag and classes and nothing else. Such an element is on no generated page until the script runs."""
    def fits(tests):
        return any(all((t[0] == 'tag' and t[1] in ('*', tag)) or (t[0] == 'class' and t[1] in classes) for t in tests)
                   for tag, classes in made)
    return bool(made) and all(len(chain) == 1 and fits(chain[0][1]) for chain in chains)


def hook_problems(hooks, root):
    """Why the page (the root of its parsed tree) does not serve the script: one line per lookup that finds nothing
    where the script looks, per part of a querySelectorAll list that finds nothing, per :not(...) whose positive form
    finds nothing, per in-page link the script collects whose target is missing, and per attribute the script reads that
    the elements do not carry (or never with the value it tests for). [] when every hook resolves. A lookup of an element
    the script makes itself (made_by_the_script) is not asked of the page."""
    ids = set(n['id'] for n in root.walk() if n['id'])
    out = []
    for lk in hooks.lookups:
        what = '%s.%s(%r)' % (lk.recv, lk.fn, lk.arg)
        try:
            found = lookup_result(lk, hooks, root)
            if lk.fn == 'getElementById' and len(found) != 1:
                out.append('%s: %d elements on the page have that id' % (what, len(found)))
            elif not found and not (lk.fn in ('querySelector', 'querySelectorAll', 'closest', 'matches')
                                    and made_by_the_script(parse_selector(lk.arg), hooks.made)):
                out.append('%s finds nothing on the page' % what)
            if lk.fn not in ('querySelector', 'querySelectorAll', 'closest', 'matches') or not found:
                continue
            scope = scope_of(lk.recv, hooks, root)
            wide = [root] if scope is None or lk.fn in ('closest', 'matches') else scope
            for chain in parse_selector(lk.arg):
                if lk.fn == 'querySelectorAll' and not select(wide, [chain]):
                    out.append('%s: one part of the list finds nothing on the page' % what)
                comb, tests = chain[-1]
                for t in tests:
                    if t[0] == 'not':
                        positive = chain[:-1] + ((comb, tuple(x for x in tests if x is not t) + t[1]),)
                        if not select(wide, [positive]):
                            out.append('%s: nothing on the page is what its :not() leaves out' % what)
                    if t == ('attr', 'href', '^=', '#'):
                        for n in found:
                            if (n['href'] or '')[1:] not in ids and n['href'] != '#':
                                out.append('%s: %s links to an id the page does not have' % (what, n['href']))
        except Unsupported as ex:
            out.append('%s: this test cannot read the selector (%s): extend its matcher' % (what, ex))
    for rd in hooks.reads:
        what = '%s reads %s' % (rd.recv, rd.attr)
        try:
            traced = bindings_of(rd.recv, hooks, root) if re.match(_NAME + r'\Z', rd.recv) else []
        except Unsupported:
            continue                                       # already reported with its lookup
        if traced:
            holders = [nodes for nodes in traced if nodes and all(rd.attr in n for n in nodes)]
            if not holders:
                out.append('%s: the elements it is read from do not all carry it' % what)
        else:
            holders = [[n for n in root.walk() if rd.attr in n]]
            if not holders[0]:
                out.append('%s: no element on the page carries it' % what)
        if rd.value is not None and not any(n[rd.attr] == rd.value for nodes in holders for n in nodes):
            out.append('%s and tests it for %r: no element has that value' % (what, rd.value))
    return out


# ---------------------------------------------------------------- the synthetic journal the hooks are resolved on

SLUG = 'syn-j-hooks'              # 'syn-j-': the prefix of every synthetic journal; no real trip's slug starts with it
WRITE_UP = 'Synthetic write-up for a test.'
# what the write-ups filter hides on this journal: the track-only days and the month without a write-up
HIDDEN = ['day-1', 'day-40', 'day-5-zero', 'month-2024-06']
SHOWN = ['day-2', 'day-5-2', 'month-2024-04', 'month-2024-05']
ELSEWHERE = ['days', 'title', 'stats', 'map', 'highlights', 'ser-only', 'ser-live']
# the ids inside a day (its number, its title) and inside a month (its heading): link targets of the public site's journal
INNER = {'day': ('-n', '-t'), 'month': ('-h',)}
# what the script must take for hidden: each hidden day and month (HIDDEN) and every id inside one. Day 40 is inside
# June, so its number and title are inside a hidden day and inside a hidden month at once
HIDDEN_INSIDE = ['day-1-n', 'day-1-t', 'day-40-n', 'day-40-t', 'day-5-zero-n', 'day-5-zero-t', 'month-2024-06-h']
ALL_HIDDEN = sorted(HIDDEN + HIDDEN_INSIDE)
MIDDOT = ' \u00b7 '              # between a day's number and its title in 'Continue reading: Day 2 \u00b7 Bravo'


def hook_days():
    """Five recorded days over three months: Day 2 and Day 5.2 are written; Day 1, the untitled Day '5 (zero)' and Day 40
    are track only, and Day 40 is alone in June, so June is a month without a write-up. Day 1 has a photo: a track-only
    day can have a body too, and is hidden all the same. The journal lists Day 1 as a highlight, so the page has a link
    to a day the filter hides."""
    return [
        {'id': '001', 'day': '1', 'title': 'Alpha', 'date': '2024-04-22',
         'photos': [photo('photos/d001-01.webp', LANDSCAPE, alt='Synthetic view')]},
        {'id': '002', 'day': '2', 'title': 'Bravo', 'date': '2024-04-23', 'body': WRITE_UP},
        {'id': '003', 'day': '5.2', 'title': 'Charlie', 'date': '2024-05-01', 'body': WRITE_UP},
        {'id': '004', 'day': '5 (zero)', 'date': '2024-05-02'},
        {'id': '005', 'day': '40', 'title': 'Delta', 'date': '2024-06-03'},
    ]


class JournalPageCase(unittest.TestCase):
    """setUp builds the journal page of the synthetic journal (self.html) and reads the script's hooks (self.hooks)."""

    def setUp(self):
        self.assertTrue(os.path.exists(SERIES_JS), 'assets/js/pages/series.js is missing')
        try:
            from sitegen.pages import series
        except ImportError as ex:
            self.fail('sitegen/pages/series.py is not importable: %s' % ex)
        self.assertFalse(os.path.lexists(os.path.join(content.RENDERED, 'trips', SLUG)), 'fixture slug %r names a real trip' % SLUG)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.object(core, '_SITE_META', [{'hash': '', 'maps': {}, 'regions': [], 'all_regions': []}])
        patcher.start()
        self.addCleanup(patcher.stop)
        helpers.make_trip(tmp.name, SLUG, title='Synthetic Journal', kind='series', date='2024-04-22', end_date='2024-06-03',
                          days=hook_days(), journal_highlights=['001'])
        t = helpers.load(tmp.name, SLUG)
        self.html = series.page(t, helpers.make_site([t])).html
        self.code = code_only(source())
        self.hooks = read_hooks(self.code)

    def page_ids(self, cls):
        return [n['id'] for n in Doc(self.html).find_all(cls=cls)]


def filter_rules(code, css):
    """{state class: [selectors]}: each class the script sets on an element (classList.toggle / add) and the selectors of
    the stylesheet rules that take elements out of the page under it (display: none)."""
    states = set(m.group(2) for m in re.finditer(r'''classList\s*\.\s*(?:toggle|add)\s*\(\s*(['"`])([\w-]+)\1''', code))
    found = {}
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', re.sub(r'/\*.*?\*/', '', css, flags=re.S)):
        if re.search(r'display\s*:\s*none', m.group(2)):
            for part in m.group(1).split(','):
                for state in states:
                    if re.search(r'\.%s(?![\w-])' % re.escape(state), part):
                        found.setdefault(state, []).append(part.strip())
    return found


def filtered_out(doc, state, selectors):
    """The elements those rules remove once the day log (#days) carries the state class."""
    log = doc.by_id('days')
    before = log.attrs.get('class', '')
    log.attrs['class'] = before + ' ' + state
    try:
        return select([doc.root], parse_selector(', '.join(selectors)))
    finally:
        log.attrs['class'] = before


def inner_ids(doc, id_):
    """The ids inside the element with this id, in page order (an element without an id is passed through)."""
    node = doc.by_id(id_)
    if node is None:
        raise AssertionError('the journal page has no element with the id %s' % id_)
    return [d['id'] for d in node.walk() if d['id']]


def page_model(page_html, hooks, code, css):
    """The journal page as tests/series_js_harness.js needs it for its "dom:" checks: every element (with its text), the
    answer to each selector the script uses and its parsed form, what the stylesheet hides while the filter is on, and
    the elements and ids the checks press and read. Everything comes from the generated page, the script and the
    stylesheet; nothing is assumed. The one exception is ids.continued, what 'Continue reading' must say for each day:
    written from the fixture (hook_days), so it does not repeat what the page itself prints."""
    doc = Doc(page_html)
    nodes = list(doc.root.walk())
    at = dict((id(n), i) for i, n in enumerate(nodes))
    rules = filter_rules(code, css)
    if len(rules) != 1:
        raise AssertionError('expected one filter class shared by series.js and series.css, found %r' % sorted(rules))
    (state, selectors), = rules.items()

    def where(node, what):
        if node is None:
            raise AssertionError('the journal page has no %s' % what)
        return at[id(node)]

    def link(scope, href, what):
        return where(next((a for a in (scope.find_all('a') if scope is not None else []) if a['href'] == href), None), what)

    def within(id_, cls):
        node = doc.by_id(id_)
        return node.find(cls=cls) if node is not None else None

    def days_in(id_):
        node = doc.by_id(id_)
        return [d['id'] for d in node.find_all(cls='ser-day')] if node is not None else []

    box = doc.by_id('ser-only')
    gone = [n for n in filtered_out(doc, state, selectors) if n['id']]
    entries = set(n['id'] for n in gone)
    hidden_ids = sorted(set(d['id'] for n in gone for d in [n] + list(n.walk()) if d['id']))
    queried = [lk.arg for lk in hooks.lookups if lk.fn in ('querySelector', 'querySelectorAll', 'closest', 'matches')]
    nav = doc.find('nav', cls='ser-mnav')
    day_nodes, fixture = doc.find_all(cls='ser-day'), hook_days()
    if len(day_nodes) != len(fixture):
        raise AssertionError('the journal page has %d day articles for %d fixture days' % (len(day_nodes), len(fixture)))
    model = {
        'pathname': '/personal-website/trips/%s/' % SLUG,
        'total': len(hook_days()),
        # text: the element's textContent on the page (its children's text included)
        'elements': [{'tag': n.tag, 'id': n['id'] or '', 'classes': n.classes, 'attrs': n.attrs, 'parent': at.get(id(n.parent), -1),
                      'text': n.text(clean=False)} for n in nodes],
        'selectors': dict((sel, [at[id(n)] for n in select([doc.root], parse_selector(sel))]) for sel in queried),
        # the same selectors parsed: the stand-in tries them on the elements the script makes (on no page, so in no answer)
        'parsed': dict((sel, parse_selector(sel)) for sel in queried),
        'filterClass': state,
        'filteredOut': [at[id(n)] for n in filtered_out(doc, state, selectors)],
        'ids': {'hiddenDay': 'day-1', 'hiddenMonth': 'month-2024-06', 'shownDay': 'day-2', 'shownMonth': 'month-2024-04',
                # the ids inside them, read off the page: a day's number and title, a month's heading and (for the hidden
                # month) the title of a hidden day in it
                'inHiddenDay': inner_ids(doc, 'day-1'),
                'inHiddenMonth': inner_ids(doc, 'month-2024-06')[:1] + [i for i in inner_ids(doc, 'month-2024-06') if i.endswith('-t')][:1],
                'inShown': inner_ids(doc, 'day-2') + inner_ids(doc, 'month-2024-04')[:1],
                # Phase 11: the written entry after day-2; the days of April (its first is track only, so the filter
                # hides it) and of June (the month without write-ups); and 'Continue reading: Day N · title' for each day,
                # a day without a title by its number alone
                'nextShownDay': 'day-5-2',
                'shownMonthDays': days_in('month-2024-04'),
                'hiddenMonthDays': days_in('month-2024-06'),
                'continued': dict((n['id'], 'Continue reading: Day %s%s' % (d['day'], (MIDDOT + d['title']) if d.get('title') else ''))
                                  for n, d in zip(day_nodes, fixture))},
        # everything the stylesheet takes out of the page while the filter is on, by id; and of those, the ids that
        # are inside a hidden day or month without being one
        'hiddenIds': hidden_ids,
        'hiddenInside': [i for i in hidden_ids if i not in entries],
        'handles': {
            'log': where(doc.by_id('days'), 'day log (#days)'),
            'box': where(box, 'toggle (#ser-only)'),
            'live': where(doc.by_id('ser-live'), 'live region (#ser-live)'),
            'wrapper': where(closest(box, parse_selector('[hidden]')) if box is not None else None, 'hidden wrapper around the toggle'),
            'browse': where(doc.find(attrs={'data-ser-all': ''}), '"Browse all recordings" action ([data-ser-all])'),
            'dayLink': link(doc.by_id('highlights'), '#day-1', 'highlight linking to #day-1'),
            'monthLink': link(doc.find('ol', cls='ser-mi'), '#month-2024-06', 'month index link to #month-2024-06'),
            'shownLink': link(doc.find(cls='rep-actions'), '#day-2', 'title action linking to #day-2'),
            # Phase 11: the month nav, its links to April (written, its first day hidden by the filter) and to June (no
            # write-ups); the written entries' Next (Day 2 -> 5.2) and Previous (5.2 -> 2) links; 'Continue reading'
            'mnav': where(nav, 'month nav (nav.ser-mnav)'),
            'monthNav': link(nav, '#month-2024-04', 'month nav link to #month-2024-04'),
            'emptyMonthNav': link(nav, '#month-2024-06', 'month nav link to #month-2024-06'),
            'nextLink': link(within('day-2', 'ser-wnav'), '#day-5-2', 'Next write-up link of day-2'),
            'prevLink': link(within('day-5-2', 'ser-wnav'), '#day-2', 'Previous write-up link of day-5-2'),
            'cont': where(doc.find(cls='ser-continue'), "'Continue reading' link (.ser-continue)"),
        },
    }
    return model


# The same script, spelled three other ways (each is still valid JavaScript: SeriesJsNodeTests runs them). Only what
# lies outside the string literals is respaced.
_LITERAL = re.compile(r'''('(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*")''')
_SPACED = re.compile(r'\s*([()\[\],]|(?<![!=<>+*/|&-])={1,3}(?![=>]))\s*')


def respaced(code, how):
    parts = _LITERAL.split(code)
    return ''.join(p if i % 2 else how(p) for i, p in enumerate(parts))


def spell(code):
    """{name: the script rewritten}: quotes swapped, every member access and bracket spaced out, all of that squeezed out."""
    return {
        'quotes swapped': code.translate({ord("'"): '"', ord('"'): "'"}),
        'spaced out': respaced(code, lambda p: _SPACED.sub(r'  \1  ', re.sub(r'\s*\.\s*(?=[A-Za-z_$])', '\n      . ', p))),
        'squeezed': respaced(code, lambda p: re.sub(r'\s*([.()\[\],=?:&|])\s*', r'\1', p)),
    }


def reclass(nodes, old, new=None):
    """Rename a class token on these nodes (or drop it, without `new`)."""
    for n in nodes:
        if old in n.classes:
            n.attrs['class'] = ' '.join(new if c == old else c for c in n.classes if new or c != old)


def reattr(nodes, name, value=None):
    """Set an attribute on these nodes (or remove it, without `value`)."""
    for n in nodes:
        if value is None:
            n.attrs.pop(name, None)
        else:
            n.attrs[name] = value


def month_links(root):
    return root.find('nav', cls='ser-mnav').find_all('a')


# One hook taken off the parsed page at a time: (what goes, the change to the tree, a word the report must contain).
# The changes name the page's hooks as contract section 5 does, not the markup around them.
DROPPED = (
    ('the day log class', lambda r: reclass(r.walk(), 'ser-log', 'ser-list'), 'ser-log'),
    ('the month nav class', lambda r: reclass(r.walk(), 'ser-mnav', 'ser-months'), 'ser-mnav'),
    ('the toggle id', lambda r: reattr([r.by_id('ser-only')], 'id', 'ser-toggle'), 'ser-only'),
    ('the toggle wrapper class', lambda r: reclass(r.walk(), 'ser-only', 'ser-switch'), 'ser-only'),
    ('the live region id', lambda r: reattr([r.by_id('ser-live')], 'id', 'ser-status'), 'ser-live'),
    ('data-default', lambda r: reattr([r.by_id('ser-only')], 'data-default'), 'data-default'),
    ('the value of data-default', lambda r: reattr([r.by_id('ser-only')], 'data-default', 'all'), 'data-default'),
    ('data-total', lambda r: reattr([r.by_id('ser-only')], 'data-total'), 'data-total'),
    ('data-wu on the toggle', lambda r: reattr([r.by_id('ser-only')], 'data-wu'), 'data-wu'),
    ('data-wu on the month links', lambda r: reattr(month_links(r), 'data-wu'), 'data-wu'),
    ('data-wu on one month link', lambda r: reattr(month_links(r)[:1], 'data-wu'), 'data-wu'),
    ('the zero on the month links', lambda r: reattr([a for a in month_links(r) if a['data-wu'] == '0'], 'data-wu', 'none'), 'data-wu'),
    ('data-ser-all', lambda r: reattr(r.walk(), 'data-ser-all'), 'data-ser-all'),
    ('the day class', lambda r: reclass(r.walk(), 'ser-day', 'ser-entry'), 'ser-day'),
    ('the month class', lambda r: reclass(r.walk(), 'ser-month', 'ser-mon'), 'ser-month'),
    ('the written marker', lambda r: reclass(r.walk(), 'has-wu', 'written'), 'has-wu'),
    ('the written marker on the days', lambda r: reclass(r.find_all('article'), 'has-wu'), 'has-wu'),
    ('the written marker on the months', lambda r: reclass(r.find_all('section'), 'has-wu'), 'has-wu'),
    ('the id of a month the nav links to', lambda r: reattr([r.by_id('month-2024-06')], 'id', 'm-2024-06'), 'month-2024-06'),
    ('the in-page month links', lambda r: [reattr([a], 'href', './' + a['href']) for a in month_links(r)], 'href'),
    ('the month links', lambda r: reattr(month_links(r), 'href'), 'href'),
)


class SeriesJsPageHookTests(JournalPageCase):

    def test_every_hook_series_js_looks_up_is_on_the_journal_page(self):
        # contract 5, Reader mode + 10.6: the ids, selectors and data attributes the script reads all resolve on the page
        # sitegen.pages.series writes, on the elements the script reads them from
        self.assertEqual(hook_problems(self.hooks, Doc(self.html).root), [])

    def test_series_js_reads_the_hooks_the_contract_names(self):
        # contract 5, Reader mode: the toggle (#ser-only with data-default="wu", data-total, data-wu), the #ser-live
        # announcement, the month links' data-wu and a click on [data-ser-all]: the page emits them for this script
        ids = set(lk.arg for lk in self.hooks.lookups if lk.fn == 'getElementById')
        self.assertLessEqual({'ser-only', 'ser-live'}, ids)
        attr_tests = set()
        for lk in self.hooks.lookups:
            if lk.fn not in ('getElementById', 'getElementsByClassName'):
                attr_tests.update(t[1] for chain in parse_selector(lk.arg) for _, tests in chain for t in tests if t[0] == 'attr')
        self.assertIn('data-ser-all', attr_tests)
        reads = set((r.attr, r.value) for r in self.hooks.reads)
        self.assertIn(('data-default', 'wu'), reads)
        self.assertLessEqual({'data-wu', 'data-total', 'data-default', 'href'}, set(attr for attr, _ in reads))
        # and none slipped past read_hooks: every lookup call with a literal argument, and every dataset read, was read
        calls = re.findall(r'''\.\s*(?:querySelectorAll|querySelector|getElementById|getElementsByClassName|closest|matches)\s*\(\s*['"`]''',
                           self.code)
        self.assertEqual(len(self.hooks.lookups), len(calls))
        self.assertGreater(len(calls), 0)
        self.assertEqual(len([r for r in self.hooks.reads if r.attr.startswith('data-')]), len(re.findall(r'\.\s*dataset\b', self.code)))

    def test_the_hooks_are_on_the_elements_the_page_contract_names(self):
        # the same hooks, stated from the page's side (contract 5): where each one sits
        doc = Doc(self.html)
        log = doc.by_id('days')
        self.assertIn('ser-log', log.classes)
        box = log.by_id('ser-only')
        self.assertEqual((box.tag, box['type'], box['data-default'], box['data-total'], box['data-wu']), ('input', 'checkbox', 'wu', '5', '2'))
        self.assertIn('ser-only', box.parent.parent.classes)
        self.assertIn('hidden', box.parent.parent)
        self.assertEqual(log.by_id('ser-live')['aria-live'], 'polite')
        links = log.find('nav', cls='ser-mnav').find_all('a')
        self.assertEqual([(a['href'], a['data-wu']) for a in links],
                         [('#month-2024-04', '1'), ('#month-2024-05', '1'), ('#month-2024-06', '0')])
        browse = doc.find_all(attrs={'data-ser-all': ''})
        self.assertEqual([(a.tag, a['href']) for a in browse], [('a', '#days')])
        self.assertIsNone(closest(browse[0], parse_selector('.ser-log')))   # it sits in the title block, outside the day log

    def test_the_script_lists_what_the_filter_hides_by_the_page_ids(self):
        # contract 5, Reader mode: the filter hides a track-only day and a month without write-ups; the script collects
        # exactly those elements, and each has the id a link to it would name
        root = Doc(self.html).root
        lists = [sorted(n['id'] or '(no id)' for n in lookup_result(lk, self.hooks, root))
                 for lk in self.hooks.lookups if lk.fn == 'querySelectorAll']
        self.assertIn(sorted(HIDDEN), lists)
        self.assertEqual(sorted(self.page_ids('ser-day') + self.page_ids('ser-month')), sorted(HIDDEN + SHOWN))

    def test_a_day_and_a_month_hold_the_ids_an_old_link_may_name(self):
        # the page's side of fix B: a day's number and title and a month's heading carry ids of their own (they were link
        # targets on the public site, where the filter starts switched off), named after the day or month they are in
        doc = Doc(self.html)
        for cls, tags in (('ser-day', (('p', 'ser-n'), ('h4', 'ser-t'))), ('ser-month', (('h3', 'ser-mh-t'),))):
            kind = 'day' if cls == 'ser-day' else 'month'
            for node in doc.find_all(cls=cls):
                with self.subTest(entry=node['id']):
                    want = [node['id'] + suffix for suffix in INNER[kind]]
                    # the ids that are this entry's own: not a day of the month, nor an id inside such a day
                    entry = parse_selector('.ser-day, .ser-month')
                    own = [i for i in inner_ids(doc, node['id']) if closest(doc.by_id(i), entry) is node]
                    self.assertEqual(own, want)
                    self.assertEqual([(doc.by_id(i).tag, cls_ in doc.by_id(i).classes) for i, (_tag, cls_) in zip(want, tags)],
                                     [(tag, True) for tag, _cls in tags])
        # what the filter hides, with everything inside: the days and months of HIDDEN and the ids of HIDDEN_INSIDE
        self.assertEqual(sorted(set(i for h in HIDDEN for i in [h] + inner_ids(doc, h))), ALL_HIDDEN)
        self.assertEqual(sorted(i for i in ALL_HIDDEN if i not in HIDDEN), sorted(HIDDEN_INSIDE))
        # a hidden day inside a hidden month: its ids are inside both
        self.assertIn('day-40-t', inner_ids(doc, 'month-2024-06'))
        self.assertIn('day-40-t', inner_ids(doc, 'day-40'))
        # and no id of a written day or month, or of the rest of the page, is among them
        for id_ in SHOWN + ELSEWHERE + [s + suffix for s in SHOWN for suffix in INNER['day' if s.startswith('day-') else 'month']]:
            self.assertIn('id="%s"' % id_, self.html)
            self.assertNotIn(id_, ALL_HIDDEN)

    def test_the_page_model_names_what_the_filter_hides_with_the_ids_inside(self):
        # the model the harness checks the script's own list against is read off the page and the stylesheet
        with open(SERIES_CSS, encoding='utf-8') as fh:
            model = page_model(self.html, self.hooks, self.code, fh.read())
        self.assertEqual(model['hiddenIds'], ALL_HIDDEN)
        self.assertEqual(model['hiddenInside'], sorted(HIDDEN_INSIDE))
        self.assertEqual(model['ids']['inHiddenDay'], ['day-1-n', 'day-1-t'])
        self.assertEqual(model['ids']['inHiddenMonth'], ['month-2024-06-h', 'day-40-t'])
        self.assertEqual(model['ids']['inShown'], ['day-2-n', 'day-2-t', 'month-2024-04-h'])
        # the script asks each hidden element for the ids inside it: the model answers that selector with every element
        # that has an id, and the stand-in keeps the ones inside the element asked
        doc = Doc(self.html)
        self.assertEqual(len(model['selectors']['[id]']), len([n for n in doc.root.walk() if 'id' in n]))
        self.assertGreater(len(model['selectors']['[id]']), len(ALL_HIDDEN))

    def test_the_page_model_serves_the_month_nav_and_continue_reading_checks(self):
        # Phase 11: the selectors the script added are answered from the page (.ser-mn-none, a note the script makes
        # itself, by nothing), each with its parsed form for the stand-in; the model names the links the new "dom:"
        # checks press, and what 'Continue reading' must say for each day
        with open(SERIES_CSS, encoding='utf-8') as fh:
            model = json.loads(json.dumps(page_model(self.html, self.hooks, self.code, fh.read())))   # as the harness reads it
        sel, n_days, el = model['selectors'], len(hook_days()), model['elements']
        self.assertEqual(sorted(sel), sorted(model['parsed']))
        self.assertEqual([len(sel[s]) for s in ('.ser-continue', '.ser-day', '.ser-dn', '.ser-t', '.ser-mn-none')],
                         [1, n_days, n_days, n_days, 0])
        self.assertEqual(model['parsed']['.ser-mn-none'], [[['', [['class', 'ser-mn-none']]]]])
        self.assertEqual(model['parsed']['a[href^="#"]'], [[['', [['tag', 'a'], ['attr', 'href', '^=', '#']]]]])
        self.assertEqual([el[i]['text'] for i in sel['.ser-dn']], ['Day 1', 'Day 2', 'Day 5.2', 'Day 5 (zero)', 'Day 40'])
        h = model['handles']
        self.assertEqual([el[h[k]]['attrs'].get('href') for k in ('monthNav', 'emptyMonthNav', 'nextLink', 'prevLink', 'cont')],
                         ['#month-2024-04', '#month-2024-06', '#day-5-2', '#day-2', '#days'])
        self.assertEqual((el[h['emptyMonthNav']]['attrs']['data-wu'], el[h['emptyMonthNav']]['text']), ('0', 'JuneDays 40'))
        self.assertEqual((el[h['cont']]['text'], 'hidden' in el[h['cont']]['attrs']), ('', True))
        self.assertEqual((model['ids']['shownMonthDays'], model['ids']['hiddenMonthDays']), (['day-1', 'day-2'], ['day-40']))
        self.assertEqual(model['ids']['continued'], {
            'day-1': 'Continue reading: Day 1 \u00b7 Alpha', 'day-2': 'Continue reading: Day 2 \u00b7 Bravo',
            'day-5-2': 'Continue reading: Day 5.2 \u00b7 Charlie', 'day-5-zero': 'Continue reading: Day 5 (zero)',
            'day-40': 'Continue reading: Day 40 \u00b7 Delta'})
        # the page's month links carry neither aria-disabled nor tabindex: what the harness checks after the script ran
        for a in Doc(self.html).find('nav', cls='ser-mnav').find_all('a'):
            self.assertEqual([k for k in ('aria-disabled', 'tabindex') if k in a], [], a['href'])

    def test_the_stylesheet_hides_what_the_script_lists(self):
        # the filter is a class the script sets and the stylesheet acts on: what series.css takes out of the page under
        # that class must be what series.js believes is hidden, or a link to a "hidden" entry is handled wrongly
        with open(SERIES_CSS, encoding='utf-8') as fh:
            rules = filter_rules(self.code, fh.read())
        self.assertEqual(len(rules), 1, 'series.js and series.css no longer share one filter class: %r' % sorted(rules))
        (state, selectors), = rules.items()
        doc = Doc(self.html)
        gone = filtered_out(doc, state, selectors)
        self.assertEqual(sorted(n['id'] for n in gone if n['id']), sorted(HIDDEN))
        self.assertEqual(select([doc.root], parse_selector(', '.join(selectors))), [])    # and nothing before the class is set
        for n in gone:                                     # what else goes (the 'no recording' rows) holds nothing a link names
            if not n['id']:
                self.assertEqual([d['id'] for d in n.walk() if d['id']], [])

    def test_the_hook_check_does_not_depend_on_quote_style_or_whitespace(self):
        # the check itself: the same script with its quotes swapped, spaced out or squeezed reads as the same hooks
        want = signature(self.hooks)
        self.assertTrue(want[0] and want[1] and want[2])
        for name, code in spell(self.code).items():
            with self.subTest(spelling=name):
                self.assertNotEqual(code, self.code)
                hooks = read_hooks(code)
                self.assertEqual(signature(hooks), want)
                self.assertEqual(hook_problems(hooks, Doc(self.html).root), [])

    def test_the_hook_check_fails_when_the_page_drops_a_hook(self):
        # the check itself: take one hook off the page and it must say so, naming it
        def state(root):
            return [(n.tag, sorted(n.attrs.items())) for n in root.walk()]

        for what, change, word in DROPPED:
            with self.subTest(dropped=what):
                root = Doc(self.html).root
                before = state(root)
                change(root)
                self.assertNotEqual(state(root), before, 'the change for %r changed nothing on the fixture page' % what)
                problems = hook_problems(self.hooks, root)
                self.assertNotEqual(problems, [], 'dropping %s went unnoticed' % what)
                self.assertIn(word, ' '.join(problems))

    def test_the_hook_check_reports_a_selector_it_cannot_read(self):
        # the check itself: syntax beyond the matcher is a failure with a clear message, never a silent pass
        hooks = read_hooks(self.code + "\nvar odd = document.querySelector('.ser-log ~ .ser-day:nth-child(2)');\n")
        problems = hook_problems(hooks, Doc(self.html).root)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn('extend its matcher', problems[0])

    def test_the_hook_check_knows_the_element_the_script_makes(self):
        # Phase 11 (a11y-07): the ', no write-ups' note of a month link is made by the script and is on no generated
        # page. read_hooks reads it off the createElement and className lines, and its lookup is not asked of the page;
        # without that, or for any other selector, a lookup that finds nothing is still reported
        self.assertEqual(self.hooks.made, [('span', ('ser-mn-none', 'sr'))])
        self.assertIn(Lookup('a', 'querySelector', '.ser-mn-none', 'note'), self.hooks.lookups)
        root = Doc(self.html).root
        self.assertEqual(hook_problems(self.hooks._replace(made=[]), root), ["a.querySelector('.ser-mn-none') finds nothing on the page"])
        for selector in ('.ser-mn-none.other', 'div.ser-mn-none', '.ser-mn-none[id]', '.ser-mnav .ser-mn-none', '.ser-mn-gone'):
            with self.subTest(selector=selector):
                hooks = read_hooks(self.code + "\nvar odd = document.querySelector('%s');\n" % selector)
                self.assertEqual(hook_problems(hooks, root), ['document.querySelector(%r) finds nothing on the page' % selector])

    def test_the_selector_matcher_matches_like_a_browser(self):
        # the check itself: the matcher on a page small enough to verify by eye
        doc = Doc('<main id="m" class="a b"><p class="x" data-k="v">one</p><div class="x y"><a href="#m" data-k>two</a>'
                  '<a href="other/">three</a></div><p class="y">four</p></main>')
        cases = (('.x', ['p', 'div']), ('p.x', ['p']), ('.x.y', ['div']), ('#m', ['main']), ('main .y', ['div', 'p']),
                 ('main > .y', ['div', 'p']), ('.x > a', ['a', 'a']), ('p > a', []), ('[data-k]', ['p', 'a']),
                 ('[data-k="v"]', ['p']), ("[data-k='v']", ['p']), ('[data-k=v]', ['p']), ('a[href^="#"]', ['a']),
                 ('a[href$="/"]', ['a']), ('a:not([href^="#"])', ['a']), ('.x:not(.y), p.y', ['p', 'p']),
                 ('.x:not( .y )', ['p']), (' .a   .x ', ['p', 'div']), ('*', ['main', 'p', 'div', 'a', 'a', 'p']),
                 ('[class~="b"]', ['main']), ('.nothing', []))
        for selector, want in cases:
            with self.subTest(selector=selector):
                self.assertEqual([n.tag for n in select([doc.root], parse_selector(selector))], want)
        self.assertEqual(parse_selector('a[href^="#"]'), parse_selector("a[href^='#']"))
        self.assertEqual(parse_selector('.x:not(.y),.z>a'), parse_selector(' .x:not( .y ) , .z > a '))
        self.assertEqual(closest(doc.find('a'), parse_selector('.x')).tag, 'div')
        self.assertIsNone(closest(doc.find('a'), parse_selector('.nothing')))
        for selector in ('a:hover', '.x + .y', '.x ~ .y', 'a::before', '', ',', '.x,', 'p >', ':not(.x .y)'):
            with self.subTest(selector=selector):
                self.assertRaises(Unsupported, parse_selector, selector)


class SeriesJsSourceTests(unittest.TestCase):

    def setUp(self):
        self.assertTrue(os.path.exists(SERIES_JS), 'assets/js/pages/series.js is missing')
        self.src = source()
        self.code = code_only(self.src)

    def test_series_js_exports_for_node_before_touching_the_dom(self):
        # contract 5, Reader mode: pure helpers exported for Node, `module.exports` before any DOM access (as trips.js does)
        self.assertIn('module.exports', self.code)
        dom = re.search(r'\bdocument\b', self.code)
        self.assertIsNotNone(dom, 'series.js no longer mentions document: this check needs another anchor')
        self.assertLess(self.code.index('module.exports'), dom.start(), 'series.js touches the DOM before exporting')

    def test_series_js_never_writes_markup(self):
        # day ids come from the URL hash: nothing may reach innerHTML (only clearing an element with '' is tolerated)
        self.assertNotRegex(self.src, r'\.(outerHTML|insertAdjacentHTML)\b|document\.write\b')
        for m in re.finditer(r'\.innerHTML\s*(\+?=)\s*([^;\n]*)', self.src):
            self.assertEqual(m.group(1), '=', m.group(0))
            self.assertIn(m.group(2).strip(), ("''", '""'), m.group(0))

    def test_the_helpers_keep_their_signatures(self):
        # fix B changed the list the page hands over, not the helpers: the same four, with the same arguments; Phase 11
        # adds a fifth, openedDay(href, firstDayOf) (features-08)
        for declaration in ('function hashTarget(hash) {', 'function startFiltered(defaultOn, hash, hiddenIds) {',
                            'function revealId(filtered, hash, hiddenIds) {', 'function landAfterLoad(filtered, hash, navType) {',
                            'function openedDay(href, firstDayOf) {'):
            with self.subTest(declaration=declaration):
                self.assertEqual(self.code.count(declaration), 1)
        api = re.search(r'var api = \{([^}]*)\};', self.code)
        self.assertIsNotNone(api, 'series.js no longer builds its exports as var api = { ... };')
        self.assertEqual(re.split(r'\s*,\s*', api.group(1).strip()), ['%s: %s' % (h, h) for h in HELPERS])
        # and the page still hands them the one list, at the same two places: on load and when a link is followed
        page_code = self.code[self.code.index('module.exports'):]
        self.assertIn('var id = revealId(box.checked, window.location.hash, hidden);', page_code)
        self.assertRegex(page_code, r"box\.checked = startFiltered\(pref === null \? box\.dataset\.default === 'wu' : pref === '1', window\.location\.hash, hidden\);")
        self.assertEqual(len(re.findall(r'(?<![\w$.])(?:startFiltered|revealId)\s*\(', page_code)), 2)
        self.assertEqual(len(re.findall(r'\bvar hidden\b', page_code)), 1)

    def test_the_page_code_decides_through_the_tested_helpers(self):
        # contract 10.6: the decisions are the pure exports the harness checks; the code that runs on the page (everything
        # after the export) must call each of them, not repeat the rule beside it
        page_code = self.code[self.code.index('module.exports'):]
        for name in HELPERS:
            with self.subTest(helper=name):
                self.assertRegex(page_code, r'(?<![\w$])%s\s*\(' % name, 'the page code never calls %s()' % name)


class SeriesJsNodeTests(unittest.TestCase):

    def setUp(self):
        self.node = shutil.which('node')
        if self.node is None:
            self.skipTest('node is not installed')

    def run_node(self, *args):
        return subprocess.run([self.node] + list(args), cwd=TESTS, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=60)

    def run_stub(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        stub = os.path.join(tmp.name, 'stub.js')
        with open(stub, 'w', encoding='utf-8') as fh:
            fh.write(text)
        return self.run_node(HARNESS, stub)

    def assertRejected(self, r, failing, passing=()):
        """The harness exits non-zero at the named helper, having passed the ones before it."""
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn('FAIL ' + failing, r.stderr)
        for name in passing:
            self.assertNotIn('FAIL ' + name, r.stderr)
        self.assertNotIn('checks passed', r.stdout)

    def test_harness_is_valid_javascript(self):
        # the harness itself: a syntax error must not pass for a failing module
        r = self.run_node('--check', HARNESS)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_harness_rejects_a_module_with_wrong_answers(self):
        # the harness itself: the right exports with wrong answers fail, starting at hashTarget
        self.assertRejected(self.run_stub(BAD_STUB), 'hashTarget', passing=('exports',))

    def test_harness_rejects_a_module_without_the_new_helpers(self):
        # the harness itself: contract 10.6 adds revealId and landAfterLoad; a module that lacks them fails at the exports
        r = self.run_stub("module.exports = {hashTarget: function () {}, startFiltered: function () {}};\n")
        self.assertRejected(r, 'exports')
        # and Phase 11 adds openedDay: the real four helpers without it fail there too
        r = self.run_stub("var real = require(%s);\nmodule.exports = {hashTarget: real.hashTarget, startFiltered: real.startFiltered,"
                          " revealId: real.revealId, landAfterLoad: real.landAfterLoad};\n" % json.dumps(SERIES_JS))
        self.assertRejected(r, 'exports')
        self.assertIn('does not export openedDay', r.stderr)

    def test_harness_rejects_a_filter_that_ignores_the_hash(self):
        # the harness itself: a correct hashTarget does not excuse a startFiltered that hides the linked entry
        self.assertRejected(self.run_stub(BAD_FILTER), 'startFiltered', passing=('exports', 'hashTarget'))

    def test_harness_rejects_a_wrong_reveal(self):
        # the harness itself: the real helpers with revealId alone gone wrong fail there, and only there
        for replacement in BAD_REVEAL:
            with self.subTest(revealId=replacement):
                r = self.run_stub(ONE_WRONG % (json.dumps(SERIES_JS), replacement))
                self.assertRejected(r, 'revealId', passing=('exports', 'hashTarget', 'startFiltered'))

    def test_harness_rejects_a_scroll_after_reload_or_back(self):
        # the harness itself: the real helpers with landAfterLoad alone gone wrong (the reload bug among them) fail there
        for replacement in BAD_LAND:
            with self.subTest(landAfterLoad=replacement):
                r = self.run_stub(ONE_WRONG % (json.dumps(SERIES_JS), replacement))
                self.assertRejected(r, 'landAfterLoad', passing=('exports', 'hashTarget', 'startFiltered', 'revealId'))

    def test_harness_rejects_a_wrong_opened_day(self):
        # the harness itself, for features-08: the real helpers with openedDay alone gone wrong fail at its checks, after
        # every check of the four before it
        for replacement in BAD_OPENED:
            with self.subTest(openedDay=replacement):
                r = self.run_stub(ONE_WRONG % (json.dumps(SERIES_JS), replacement))
                self.assertRejected(r, 'openedDay', passing=('exports', 'hashTarget', 'startFiltered', 'revealId', 'landAfterLoad'))

    def test_harness_rejects_a_changed_signature(self):
        # the harness itself: the real helpers behind another signature, or one export more, fail its last pure check and
        # none of the checks of what the helpers answer
        for replacement in BAD_SIGNATURE:
            with self.subTest(changed=replacement.split(':')[0]):
                r = self.run_stub(ONE_WRONG % (json.dumps(SERIES_JS), replacement))
                self.assertRejected(r, 'signatures', passing=('exports',) + HELPERS + ('inner ids',))

    def test_harness_rejects_helpers_that_work_the_inner_ids_out_themselves(self):
        # the harness itself: the list decides, as before. A helper that takes an id for hidden because it begins like a
        # hidden day's would hide Day 12 for Day 1 (checked since Phase 3) and is stopped there
        prefix = ("startFiltered: function (d, hash, hidden) { var t = real.hashTarget(hash);"
                  " return !!d && !hidden.some(function (h) { return t.id === h || t.id.indexOf(h + '-') === 0; }); }")
        self.assertRejected(self.run_stub(ONE_WRONG % (json.dumps(SERIES_JS), prefix)), 'startFiltered', passing=('exports', 'hashTarget'))

    def test_pure_helpers_match_the_contract(self):
        # contract 5, Reader mode + 10.6: hashTarget(hash) -> {kind, id}; startFiltered(defaultOn, hash, hiddenIds);
        # revealId(filtered, hash, hiddenIds); landAfterLoad(filtered, hash, navType); features-08: openedDay(href,
        # firstDayOf)
        self.assertTrue(os.path.exists(SERIES_JS), 'assets/js/pages/series.js is missing')
        r = self.run_node(HARNESS)
        self.assertEqual(r.returncode, 0, 'node %s failed:\n%s\n%s' % (os.path.basename(HARNESS), r.stdout, r.stderr))
        self.assertRegex(r.stdout, r'series_js_harness: \d+ checks passed')

    def test_the_respelled_scripts_are_still_the_script(self):
        # the check of the hook check: the three spellings SeriesJsPageHookTests reads are real scripts, not text that only
        # this file's patterns accept: node parses each and the harness passes on each
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for i, (name, code) in enumerate(sorted(spell(code_only(source())).items())):
            with self.subTest(spelling=name):
                path = os.path.join(tmp.name, 'spelling-%d.js' % i)
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.write(code)
                r = self.run_node(HARNESS, path)
                self.assertEqual(r.returncode, 0, r.stderr[:600])
                self.assertIn('checks passed', r.stdout)

    def test_browser_global_carries_the_same_helpers(self):
        # contract 10.6: the pure exports are on module.exports and on window.SeriesLog (set even where there is no
        # document, after which the script stops)
        script = ("var vm = require('vm'), fs = require('fs');\n"
                  "var ctx = {window: {}};\n"
                  "vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);\n"
                  "var api = ctx.window.SeriesLog || {};\n"
                  "console.log(JSON.stringify(Object.keys(api).filter(function (k) { return typeof api[k] === 'function'; }).sort()));\n"
                  "console.log(JSON.stringify([api.hashTarget('#day-5-2'), api.revealId(true, '#day-1', ['day-1']),"
                  " api.landAfterLoad(true, '#day-1', 'reload'), api.openedDay('#month-2024-06', function (m) { return m + '/first'; })]));\n")
        r = self.run_node('-e', script, SERIES_JS)
        self.assertEqual(r.returncode, 0, r.stderr)
        names, answers = [json.loads(line) for line in r.stdout.splitlines()]
        self.assertLessEqual(set(HELPERS), set(names))
        self.assertEqual(answers, [{'kind': 'day', 'id': 'day-5-2'}, 'day-1', False, 'month-2024-06/first'])


class SeriesJsOnPageTests(JournalPageCase):
    """The script on a generated page, under node. The pure helpers on its ids: what series.py calls a day or a month is
    what series.js takes for one, including a decimal label (day-5-2) and a label that is not a number (day-5-zero).
    And the listeners, through the harness's stand-in browser (its "dom:" checks)."""

    def setUp(self):
        self.node = shutil.which('node')
        if self.node is None:
            self.skipTest('node is not installed')
        super().setUp()

    def ask(self, ids, hidden):
        script = ("var S = require(process.argv[1]), q = JSON.parse(process.argv[2]), out = {};\n"
                  "q.ids.forEach(function (id) {\n"
                  "  var h = '#' + id;\n"
                  "  out[id] = [S.hashTarget(h).kind, S.hashTarget(h).id, S.startFiltered(true, h, q.hidden), S.revealId(true, h, q.hidden),\n"
                  "             S.revealId(false, h, q.hidden), S.landAfterLoad(true, h, 'navigate'), S.landAfterLoad(true, h, 'reload')];\n"
                  "});\n"
                  "console.log(JSON.stringify(out));\n")
        r = subprocess.run([self.node, '-e', script, SERIES_JS, json.dumps({'ids': ids, 'hidden': hidden})], cwd=TESTS,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_helpers_take_the_page_ids_for_days_and_months(self):
        # contract 5, Reader mode + 10.6, on the ids sitegen.pages.series wrote: a link to a hidden day or month starts
        # unfiltered and is revealed later; a link to a written entry keeps the filter and is landed on once
        days, months = self.page_ids('ser-day'), self.page_ids('ser-month')
        self.assertEqual(days, ['day-1', 'day-2', 'day-5-2', 'day-5-zero', 'day-40'])
        self.assertEqual(months, ['month-2024-04', 'month-2024-05', 'month-2024-06'])
        self.assertEqual(sorted(days + months), sorted(HIDDEN + SHOWN))
        got = self.ask(days + months + ELSEWHERE, HIDDEN)
        for id_ in days + months:
            kind = 'day' if id_ in days else 'month'
            hidden = id_ in HIDDEN
            with self.subTest(id=id_):
                self.assertEqual(got[id_], [kind, id_, not hidden, id_ if hidden else '', '', True, False])
        for id_ in ELSEWHERE:
            with self.subTest(id=id_):
                self.assertIn('id="%s"' % id_, self.html)
                self.assertEqual(got[id_], ['other', id_, True, '', '', False, False])

    def test_with_the_ids_inside_in_the_list_the_helpers_take_them_for_hidden(self):
        # fix B on the page's own ids: handed everything the filter hides (ALL_HIDDEN), an address to the number or the
        # title of a hidden day, or to the heading of a hidden month, starts unfiltered and is revealed later; the same
        # ids of a written day or month keep the filter and are landed on
        doc = Doc(self.html)
        inside = dict((id_, inner_ids(doc, id_)) for id_ in HIDDEN + SHOWN)
        every = [i for ids in inside.values() for i in ids]
        got = self.ask(sorted(set(every)), ALL_HIDDEN)
        for entry, ids in sorted(inside.items()):
            for id_ in ids:
                with self.subTest(entry=entry, id=id_):
                    kind = 'day' if id_.startswith('day-') else 'month'
                    hidden = id_ in ALL_HIDDEN            # a hidden day, or an id inside a hidden day or month
                    self.assertEqual(got[id_], [kind, id_, not hidden, id_ if hidden else '', '', True, False])
        # the hidden ones are exactly HIDDEN_INSIDE and the hidden days themselves (each is an id inside its month)
        self.assertEqual(sorted(i for i in set(every) if got[i][2] is False),
                         sorted(HIDDEN_INSIDE + [h for h in HIDDEN if h.startswith('day-')]))
        # handed the days and months alone, as before the fix, no id inside one is hidden
        before = self.ask(HIDDEN_INSIDE, HIDDEN)
        self.assertEqual([before[i][2:4] for i in HIDDEN_INSIDE], [[True, '']] * len(HIDDEN_INSIDE))

    def run_dom(self, *fault, script=SERIES_JS):
        """The harness on the real script with the model of the generated page (and a fault for its stand-in browser).
        script: another copy of series.js to run on that page."""
        with open(SERIES_CSS, encoding='utf-8') as fh:
            model = page_model(self.html, self.hooks, self.code, fh.read())
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, 'page.json')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(model, fh)
        return subprocess.run([self.node, HARNESS, script, path] + list(fault), cwd=TESTS, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, timeout=60)

    def passed(self, r):
        m = re.search(r'series_js_harness: (\d+) checks passed', r.stdout)
        self.assertIsNotNone(m, 'no "N checks passed" line:\n%s\n%s' % (r.stdout, r.stderr))
        return int(m.group(1))

    def test_the_listeners_do_what_the_contract_says_on_a_generated_page(self):
        # contract 5 (Reader mode), 9 (the choice lasts the session) and 10.6 (Behaviour): the filter on load; a link to a
        # hidden entry, by hashchange and by a second press of the same link; no scroll to the hash on reload or Back /
        # Forward; 'Browse all recordings' remembered even when the filter is already off. Phase 11: the month nav under
        # the filter (a11y-07) and 'Continue reading' (features-08)
        r = self.run_dom()
        self.assertEqual(r.returncode, 0, 'the "dom:" checks failed:\n%s\n%s' % (r.stdout, r.stderr))
        pure = subprocess.run([self.node, HARNESS], cwd=TESTS, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=60)
        self.assertGreaterEqual(self.passed(r) - self.passed(pure), 53, 'the "dom:" checks did not run')

    def test_the_listener_checks_notice_a_change_to_what_the_script_collects(self):
        # the harness itself, for fix B: series.js with the lines that list what the filter hides changed in one way each
        # fails a "dom:" check, and no check of the helpers (they are the same)
        src = source()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for n, (what, old, new) in enumerate(BROKEN_COLLECTING):
            with self.subTest(broken=what):
                self.assertEqual(src.count(old), 1, 'assets/js/pages/series.js no longer has this text once: %r' % old)
                path = os.path.join(tmp.name, 'series_%d.js' % n)
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.write(src.replace(old, new))
                check = subprocess.run([self.node, '--check', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
                self.assertEqual(check.returncode, 0, check.stderr)
                r = self.run_dom(script=path)
                self.assertNotEqual(r.returncode, 0, 'the harness passed a script in which %s' % what)
                self.assertEqual(len(re.findall(r'(?m)^FAIL dom: ', r.stderr)), 1, r.stderr[:400])
                self.assertEqual(len(re.findall(r'(?m)^FAIL ', r.stderr)), 1)
                self.assertNotIn('the page model has no answer', r.stderr)
                self.assertNotIn('checks passed', r.stdout)
        # the unchanged script, copied the same way, passes
        path = os.path.join(tmp.name, 'series.js')
        shutil.copy(SERIES_JS, path)
        self.assertEqual(self.run_dom(script=path).returncode, 0)

    # ------------------------------------------------------------ round 3: each id once

    def test_every_id_the_filter_hides_is_listed_once(self):
        # a hidden day inside a hidden month is met twice, as an id inside its month and as a hidden day, and listed
        # once: the script asks whether the id is already there before it adds the day or month itself, as it does for
        # the ids inside
        src = source()
        self.assertEqual(src.count(_OWN), 1, 'assets/js/pages/series.js no longer has this line once: %r' % _OWN)
        self.assertEqual(len(re.findall(r'\bhidden\.push\(', self.code)), 2)         # the day or month, and an id inside it
        self.assertEqual(len(re.findall(r'if \((?:el\.id && )?hidden\.indexOf\((?:el|c)\.id\) === -1\) hidden\.push\(', self.code)), 2)
        # the harness holds the list of the generated page to it, in a check of its own (ONCE) ...
        with open(HARNESS, encoding='utf-8') as fh:
            self.assertEqual(fh.read().count("check('%s'," % ONCE), 1)
        self.assertEqual(self.run_dom().returncode, 0)
        # ... which is the check that fails, and the only one, when the script lists the day or month every time
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, 'series.js')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(src.replace(_OWN, '    if (el.id) hidden.push(el.id);'))
        r = self.run_dom(script=path)
        self.assertNotEqual(r.returncode, 0, 'the harness passed a script that lists a hidden day twice')
        self.assertEqual(re.findall(r'(?m)^FAIL (.*)$', r.stderr), [ONCE])
        self.assertIn('ids listed more than once', r.stderr)
        self.assertNotIn('checks passed', r.stdout)

    def test_no_case_is_left_as_a_known_gap(self):
        # round 2 kept "each id once" as a case the script did not handle ('gap:once', an expected failure). It is a
        # regular check now, so the harness knows no gap by that name, nor by any other
        for name in FORMER_GAPS + ('no-such-case',):
            with self.subTest(gap=name):
                r = self.run_dom('gap:' + name)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn('unknown gap: ' + name, r.stderr)
                self.assertEqual(re.findall(r'(?m)^FAIL (.*)$', r.stderr), [])        # every check before it passed
                self.assertNotIn('checks passed', r.stdout)
        with open(HARNESS, encoding='utf-8') as fh:
            self.assertRegex(fh.read(), r'(?m)^  const GAPS = \{\};$')

    def test_the_listener_checks_notice_a_gutted_listener(self):
        # the harness itself: with one event never delivered, the session store forgetting, every load passed off as a
        # fresh visit, or localStorage throwing on every call (Phase 11: it keeps nothing), a "dom:" check fails (the pure
        # checks before them still pass)
        for fault in FAULTS:
            with self.subTest(fault=fault):
                r = self.run_dom(fault)
                self.assertNotEqual(r.returncode, 0, 'the harness passed although %s was broken' % fault)
                self.assertIn('FAIL dom: ', r.stderr)
                for name in HELPERS + ('exports',):
                    self.assertNotIn('FAIL ' + name, r.stderr)
                self.assertNotIn('checks passed', r.stdout)
        r = self.run_dom('no-such-fault')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('unknown fault', r.stderr)


if __name__ == '__main__':
    unittest.main()
