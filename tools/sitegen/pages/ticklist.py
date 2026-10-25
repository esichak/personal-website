"""Tick list — /tick-list/: every goal (kind: planned trip) as a map-led card, grouped by region, with search and filters
(activity, region, status, priority, preferred month, has a route), a scope (active / shortlisted / completed / archived),
priority / newest / name order and cards or list, all in assets/js/pages/ticklist.js over the cards' data attributes.
Without JavaScript the page is the full list by region with every goal link. Read-only: no checkbox, no upload, no
write of any kind; authoring happens locally with tools/ticklist.py.
"""
from sitegen import core
from sitegen.core import esc, link, icon
from sitegen.pages.trips import more_button

import content
import goals

HERE = 'tick-list/'
INTRO = 'Routes and objectives I’d like to get to.'
MONTHS = [(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
          (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')]
SORTS = [('priority', 'Priority'), ('added', 'Newest added'), ('name', 'Name')]
SCOPES = [('active', 'Active'), ('shortlisted', 'Shortlisted'), ('completed', 'Completed'), ('archived', 'Archived'), ('all', 'All')]
VIEWS = [('cards', 'Cards', 'photo'), ('list', 'List', 'list')]
PRIORITY_RANK = {'high': 0, 'normal': 1, 'someday': 2}
# the search box, the filters and the status line appear once there are this many active goals to sort through; with
# fewer the page is its head and the active goals (completed and archived ones are left off, as the form's default scope
# leaves them off), and an address with ?status= or ?scope= shows that same page
FILTERS_FROM = 6


def with_form(site):
    """Whether the page carries the search form: FILTERS_FROM active goals (goals.is_active) or more."""
    return sum(1 for t in site['goals'] if goals.is_active(t['goal'])) >= FILTERS_FROM


def plural(k, word, pl=None):
    return '%d %s' % (k, word if k == 1 else (pl or word + 'S'))


def count_n(k, word='goal'):
    return '<span class="sr">, </span>%d<span class="sr"> %s</span>' % (k, word if k == 1 else word + 's')


def order(ts):
    """Priority (high first), then newest added (missing dates last), then slug."""
    return sorted(ts, key=lambda t: (PRIORITY_RANK.get(t['goal']['priority'], 1), t['goal']['added_at'] is None,
                                     '' if t['goal']['added_at'] is None else _desc(t['goal']['added_at']), t['slug']))


def _desc(iso):
    # a sortable key that puts the newest ISO date first among dates
    return ''.join(chr(0x7a - (ord(c) - 0x30)) if c.isdigit() else c for c in iso)


def region_slug(t):
    return content.slugify(t['region']) if t.get('region') else ''


def regions_of(ts):
    """[(name, slug)] A–Z, one per slug (two spellings of a region share a section, named by the first A–Z); goals without
    a region, or whose region gives no slug, come last as ('No region yet', '')."""
    names = sorted({t['region'] for t in ts if t.get('region')}, key=lambda s: (s.lower(), s))
    out, seen = [], set()
    for r in names:
        slug = content.slugify(r)
        if slug and slug not in seen:
            seen.add(slug)
            out.append((r, slug))
    if any(not region_slug(t) for t in ts):
        out.append(('No region yet', ''))
    return out


# ---------------------------------------------------------------- page parts

def head(site):
    gs = site['goals']
    active = [t for t in gs if goals.is_active(t['goal'])]
    short = [t for t in gs if t['goal']['status'] == 'shortlisted' and not t['goal']['archived']]
    done = [t for t in gs if t['goal']['status'] == 'completed']
    bits = [core.nb(plural(len(active), 'ACTIVE GOAL')), core.nb(plural(len(short), 'SHORTLISTED', 'SHORTLISTED')),
            core.nb(plural(len(done), 'COMPLETED', 'COMPLETED'))]
    return ('<section class="tkl-head wrap" aria-labelledby="tkl-title"><h1 id="tkl-title" class="t-d1">Tick list</h1>'
            '<p class="t-dek tkl-intro">%s</p><p class="t-mono-s tkl-stats">%s</p></section>' % (esc(INTRO), core.meta_items(bits)))


def select(name, label, options, blank):
    opts = '<option value="">%s</option>' % esc(blank) + ''.join('<option value="%s">%s</option>' % (esc(v), esc(lab)) for v, lab in options)
    return '<label class="trx-sel"><span>%s</span><select name="%s">%s</select></label>' % (esc(label), name, opts)


def controls(site):
    gs = site['goals']
    chips = ['<button type="button" class="fchip" role="radio" data-filter="all" aria-checked="true" tabindex="0">'
             '<span class="fchip-l">All</span></button>']
    for a, lab in core.NAV:
        k = sum(1 for t in gs if t['activity'] == a)
        if k:
            chips.append('<button type="button" class="fchip" role="radio" data-filter="%s" aria-checked="false" tabindex="-1">'
                         '<span class="chip-sw" style="background:%s" aria-hidden="true"></span><span class="fchip-l">%s</span>'
                         '<span class="fchip-n">%s</span></button>' % (a, core.ACT[a][3], esc(lab), count_n(k)))
    statuses = [(s, goals.STATUS_LABELS[s]) for s in goals.STATUSES if any(t['goal']['status'] == s for t in gs)]
    prios = [(p, goals.PRIORITY_LABELS[p]) for p in goals.PRIORITIES if any(t['goal']['priority'] == p for t in gs)]
    months = sorted({m for t in gs for m in t['goal']['target_months']})
    scope = ''.join('<button type="button" class="fchip" role="radio" data-scope="%s" aria-checked="%s" tabindex="%s">%s</button>'
                    % (v, 'true' if v == 'active' else 'false', '0' if v == 'active' else '-1', esc(lab)) for v, lab in SCOPES)
    sort = '<label class="trx-sel"><span>Sort</span><select name="sort">%s</select></label>' % ''.join(
        '<option value="%s">%s</option>' % (v, esc(lab)) for v, lab in SORTS)
    views = ''.join('<button type="button" role="radio" data-view="%s" aria-checked="%s" tabindex="%s">%s%s</button>'
                    % (v, 'true' if i == 0 else 'false', '0' if i == 0 else '-1', icon(ic, 16), lab) for i, (v, lab, ic) in enumerate(VIEWS))
    # autocomplete="off" on the form, as on the Trips page (trips.controls): the script sets the controls from the address
    return ('<form class="trx-form tkl-form wrap" role="search" aria-label="Search and filter goals" id="search" action="" autocomplete="off" hidden>'
            '<label class="sr" for="tkl-q">Search goals</label>'
            '<input class="trx-q" type="search" id="tkl-q" name="q" placeholder="Search by name, place, region, tag or note" autocomplete="off" maxlength="200">'
            '<div class="trx-filters">'
            '<div class="trx-acts" role="radiogroup" aria-label="Activity">%s</div>'
            '%s'
            '<div class="trx-more" id="tkl-more">%s%s%s%s'
            '<button type="button" class="fchip tkl-gpx" role="switch" aria-checked="false" data-toggle="gpx">Has a route (GPX)</button>'
            '</div></div>'
            '<div class="trx-filters tkl-row2">'
            '<div class="trx-acts tkl-scope" role="radiogroup" aria-label="Show">%s</div><div class="trx-more" id="tkl-more2">%s</div>'
            '<div class="trx-view" role="radiogroup" aria-label="View">%s</div>'
            '</div></form>%s'
            '<noscript><p class="note wrap trx-noscript">Search and filters need JavaScript. Every goal is listed below by region.</p></noscript>'
            % (''.join(chips), more_button('tkl-more tkl-more2'),
               select('region', 'Region', [(slug, name) for name, slug in regions_of(gs) if slug], 'All regions'),
               select('status', 'Status', statuses, 'Any status'),
               select('priority', 'Priority', prios, 'Any priority'),
               select('month', 'Month', [(str(m), lab) for m, lab in MONTHS if m in months], 'Any month'),
               scope, sort, views, core.reveal('search')))


def status_row(site):
    n = len(site['goals'])
    return ('<div class="trx-status wrap">'
            '<p class="t-mono-s trx-count" id="tkl-count" aria-live="polite">%s</p>'
            '<ul class="trx-chips" id="tkl-chips" aria-label="Active filters"></ul>'
            '<button type="button" class="alink" id="tkl-clear" hidden>Clear all%s</button></div>'
            '<div class="wrap"><div class="empty" id="tkl-none" hidden><p>No goals match these filters.</p>'
            '<button type="button" class="btn" data-clear>Clear filters</button></div></div>'
            % (plural(n, 'GOAL'), icon('close', 16)))


def results(site):
    # without the form nothing would hide the completed and archived goals: only the active ones are listed then
    gs = site['goals'] if with_form(site) else [t for t in site['goals'] if goals.is_active(t['goal'])]
    out = []
    for name, slug in regions_of(gs):
        ts = order([t for t in gs if region_slug(t) == slug])
        rid = 'region-%s' % slug if slug else 'region-none'
        out.append('<section class="tkl-region trx-yr" data-region="%s"><div class="trx-yr-h"><h2 class="t-label" id="%s">%s</h2>'
                   '<span class="t-mono-s trx-yr-n">%s</span></div><ul class="tkl-grid trx-grid tgrid">%s</ul></section>'
                   % (slug, rid, esc(name), plural(len(ts), 'GOAL'), ''.join(core.goal_card(t, HERE) for t in ts)))
    if gs:
        empty = ''
    elif site['goals']:
        empty = '<div class="empty"><p>No active goals right now.</p></div>'
    else:
        empty = '<div class="empty"><p>No goals yet. Add one with <code>python3 tools/ticklist.py add</code>.</p></div>'
    return ('<div class="trx-results tkl-results wrap" id="tkl-results">%s%s<section class="trx-yr" id="tkl-sorted-sec" hidden>'
            '<div class="trx-yr-h"><h2 class="t-label" id="tkl-sorted-h">Goals</h2></div><ul class="tkl-grid trx-grid tgrid" id="tkl-sorted"></ul></section></div>'
            % (empty, ''.join(out)))


def build(site):
    body = head(site) + ((controls(site) + status_row(site)) if with_form(site) else '') + results(site)
    desc = 'Routes and objectives on my tick list: planned routes with approximate stats, planning notes, status and priority.'
    return [core.Page(HERE, core.document(HERE, 'Tick list', body, desc, active='ticklist', body_cls='p-ticklist', image=core.site_share()), 'Tick list')]
