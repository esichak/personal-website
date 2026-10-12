"""Fixtures shared by tests/test_trips_js.py and tests/test_ticklist_js.py, whose page scripts (assets/js/pages/trips.js
and ticklist.js) take the rule for history entries from one place, assets/js/pages/explore.js (historyStep). Not a test
module: its name does not start with test_, so discovery never loads it.

- tree(node): a parsed element (helpers.Doc) as the Node harnesses grow it again in their stand-in for the browser
  (tests/page_standin.js).
- WRONG_HISTORY_STEPS: historyStep(kind, entry, now, next, recent) answering wrongly in one way each. wrong_explore()
  writes the real explore.js module with its historyStep replaced by one of them: the rule is broken where it is
  defined, and whatever takes it from there (trips.js through X.historyStep, the tick list harness directly) gets the
  wrong one. A harness has to fail such a module at a check whose label starts with 'historyStep'.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
EXPLORE_JS = os.path.join(ROOT, 'assets', 'js', 'pages', 'explore.js')

# the real explore module with its historyStep replaced (`real` is the module as the site has it)
WRONG_EXPLORE = ("var real = require(%(module)s);\n"
                 "module.exports = Object.assign({}, real, { historyStep: %(body)s });\n")
# (what is wrong, historyStep's wrong version)
WRONG_HISTORY_STEPS = (
    ('adds an entry while typing',
     "function (k, e, n, x, r) { return k === 'type' && !r ? { push: true, restore: false } : real.historyStep(k, e, n, x, r); }"),
    ('adds an entry for typing that changed the address',
     "function (k, e, n, x, r) { return k === 'type' ? { push: !r && x !== n, restore: false } : real.historyStep(k, e, n, x, r); }"),
    ('never puts the entry back',
     'function (k, e, n, x, r) { return { push: real.historyStep(k, e, n, x, r).push, restore: false }; }'),
    ('puts the entry back without making a new one',
     "function (k, e, n, x, r) { var s = real.historyStep(k, e, n, x, r); return { push: s.push, restore: k === 'submit' && !r && n !== e }; }"),
    ('puts the entry back when nothing had rewritten it',
     "function (k, e, n, x, r) { var s = real.historyStep(k, e, n, x, r); return { push: s.push, restore: s.push && k === 'submit' }; }"),
    ('adds an entry when Enter repeats the view',
     "function (k, e, n, x, r) { return k === 'submit' && !r ? { push: true, restore: n !== e } : real.historyStep(k, e, n, x, r); }"),
    ('adds an entry on Enter only when the address changes, as before',
     "function (k, e, n, x, r) { return k === 'submit' ? { push: !r && x !== n, restore: false } : real.historyStep(k, e, n, x, r); }"),
    ('never adds an entry on Enter',
     "function (k, e, n, x, r) { return k === 'submit' ? { push: false, restore: false } : real.historyStep(k, e, n, x, r); }"),
    ('forgets that an entry was just made',
     'function (k, e, n, x, r) { return real.historyStep(k, e, n, x, false); }'),
    ('adds an entry for a pick only when the view differs from the entry',
     "function (k, e, n, x, r) { return k === 'pick' ? { push: !r && x !== e, restore: false } : real.historyStep(k, e, n, x, r); }"),
    ('puts the entry back on a pick as well',
     "function (k, e, n, x, r) { return k === 'pick' ? { push: !r, restore: !r && n !== e } : real.historyStep(k, e, n, x, r); }"),
)
# the same wrapper around the right function: a module made this way is not rejected for how it is made
RIGHT_HISTORY_STEP = 'function (k, e, n, x, r) { return real.historyStep(k, e, n, x, r); }'


def wrong_explore(folder, body):
    """Write <folder>/explore.js, the real explore.js module with historyStep replaced by `body`; return its path. A
    copy of trips.js or ticklist.js put beside it asks for it as the site's own does (require('./explore.js'))."""
    path = os.path.join(folder, 'explore.js')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(WRONG_EXPLORE % {'module': json.dumps(EXPLORE_JS), 'body': body})
    return path


def tree(node):
    """A parsed element as a harness grows it again: its tag, its attributes and its children (elements and text)."""
    return {'tag': node.tag, 'attrs': node.attrs, 'children': [c if isinstance(c, str) else tree(c) for c in node.children]}
