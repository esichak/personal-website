"""Goal sidecars for the tick list: content/trips/<slug>/goal.json beside a kind: planned trip.

index.md keeps the trip's identity (title, activity, place, region, approximate stats, the planning notes); goal.json
keeps the intent and provenance: status, priority, archived, tags, why, preferred months / target year, time commitment,
season notes, difficulty, route scope, route source, references, field evidence, checklist, outings and the derived
route block the importer writes. Everything here is strict: an explicit value that is not allowed stops the build with a
message naming the file and the field. A planned trip without a sidecar is a legacy goal and gets the defaults.
Research is published only when its field_evidence is approved; completion only exists as an explicitly logged outing.
"""
import hashlib
import json
import os
import re
from datetime import date

STATUSES = ('idea', 'researching', 'shortlisted', 'attempted', 'completed')
PRIORITIES = ('high', 'normal', 'someday')
COMMITMENTS = ('half-day', 'full-day', 'overnight', 'multi-day')
SCOPES = ('full-intended-route', 'approach-only', 'ascent-only', 'partial', 'unknown')
SOURCE_KINDS = ('author-drawn', 'planner-export', 'third-party-recording', 'own-prior-recording', 'unknown')
OUTCOMES = ('attempted', 'completed')
EVIDENCE_STATES = ('proposed', 'approved')
STATUS_LABELS = {'idea': 'Idea', 'researching': 'Researching', 'shortlisted': 'Shortlisted', 'attempted': 'Attempted', 'completed': 'Completed'}
PRIORITY_LABELS = {'high': 'High priority', 'normal': 'Normal priority', 'someday': 'Someday'}
COMMITMENT_LABELS = {'half-day': 'Half day', 'full-day': 'Full day', 'overnight': 'Overnight', 'multi-day': 'Multi-day'}
SCOPE_LABELS = {'full-intended-route': 'the full intended route', 'approach-only': 'the approach only', 'ascent-only': 'the ascent only',
                'partial': 'part of the route', 'unknown': 'scope unknown'}
SOURCE_LABELS = {'author-drawn': 'drawn by hand', 'planner-export': 'a planner export', 'third-party-recording': "someone else's recording",
                 'own-prior-recording': 'an earlier recording of my own', 'unknown': 'source unknown'}
ELEVATION_LABELS = {'full': '', 'partial': 'PARTIAL ELEVATION', 'none': 'NO ELEVATION IN THE FILE'}
_ID = re.compile(r'^[a-z0-9][a-z0-9-]*$')
_HEX64 = re.compile(r'^[0-9a-f]{64}$')
KEYS = ('schema_version', 'status', 'priority', 'archived', 'tags', 'why', 'added_at', 'target_months', 'target_year', 'time_commitment',
        'season_notes', 'difficulty', 'route_scope', 'route_source', 'references', 'field_evidence', 'checklist', 'outings', 'route')


def _error():
    from content import ContentError  # content imports this module; resolved lazily
    return ContentError


def defaults():
    return {'schema_version': 1, 'status': 'idea', 'priority': 'normal', 'archived': False, 'tags': [], 'why': '', 'added_at': None,
            'target_months': [], 'target_year': None, 'time_commitment': None, 'season_notes': '', 'difficulty': None,
            'route_scope': 'unknown',
            'route_source': {'kind': 'unknown', 'url': None, 'label': None, 'checked_at': None, 'public_copy_approved': False, 'approximation_note': None},
            'references': [], 'field_evidence': {}, 'checklist': [], 'outings': [], 'route': None, 'legacy': False}


def _err(slug, msg):
    return _error()('content/trips/%s/goal.json: %s' % (slug, msg))


def _str(v, field, slug, allow_none=False):
    if v is None and allow_none:
        return None
    if not isinstance(v, str):
        raise _err(slug, '%s must be text, got %r' % (field, v))
    return v.strip()


def _bool(v, field, slug):
    if not isinstance(v, bool):
        raise _err(slug, '%s must be true or false, got %r' % (field, v))
    return v


def _enum(v, field, allowed, slug, allow_none=False):
    if v is None and allow_none:
        return None
    if v not in allowed:
        raise _err(slug, '%s must be one of %s, got %r' % (field, ', '.join(allowed), v))
    return v


def _date(v, field, slug):
    if v is None:
        return None
    if not isinstance(v, str):
        raise _err(slug, '%s must be a date written YYYY-MM-DD, got %r' % (field, v))
    try:
        date.fromisoformat(v)
    except ValueError:
        raise _err(slug, '%s must be a date written YYYY-MM-DD, got %r' % (field, v))
    return v


def _url(v, field, slug):
    if v is None:
        return None
    if not isinstance(v, str) or not re.match(r'^https?://\S+$', v.strip()):
        raise _err(slug, '%s must be an http(s) link, got %r' % (field, v))
    return v.strip()


def _strlist(v, field, slug):
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise _err(slug, '%s must be a list of text items, got %r' % (field, v))
    return [x.strip() for x in v if x.strip()]


def validate(goal, slug, track_path=None):
    """The normalised goal dict, or a ContentError naming the field. track_path: the goal's track.gpx, checked against
    route.source_sha256 when both exist."""
    E = _error()
    if not isinstance(goal, dict):
        raise _err(slug, 'the file must hold a JSON object')
    unknown = sorted(k for k in goal if k not in KEYS and k != 'legacy')
    if unknown:
        raise _err(slug, 'unknown field%s %s' % ('' if len(unknown) == 1 else 's', ', '.join(unknown)))
    g = defaults()
    if 'schema_version' in goal and goal['schema_version'] != 1:
        raise _err(slug, 'schema_version must be 1, got %r' % goal['schema_version'])
    if 'status' in goal:
        g['status'] = _enum(goal['status'], 'status', STATUSES, slug)
    if 'priority' in goal:
        g['priority'] = _enum(goal['priority'], 'priority', PRIORITIES, slug)
    if 'archived' in goal:
        g['archived'] = _bool(goal['archived'], 'archived', slug)
    if 'tags' in goal:
        g['tags'] = _strlist(goal['tags'], 'tags', slug)
    if 'why' in goal:
        g['why'] = _str(goal['why'], 'why', slug)
    if 'added_at' in goal:
        g['added_at'] = _date(goal['added_at'], 'added_at', slug)
    if 'target_months' in goal:
        tm = goal['target_months']
        if not isinstance(tm, list) or not all(isinstance(m, int) and not isinstance(m, bool) and 1 <= m <= 12 for m in tm) or len(set(tm)) != len(tm):
            raise _err(slug, 'target_months must be a list of distinct month numbers 1-12, got %r' % (tm,))
        g['target_months'] = sorted(tm)
    if 'target_year' in goal:
        ty = goal['target_year']
        if ty is not None and (not isinstance(ty, int) or isinstance(ty, bool) or not 2000 <= ty <= 2100):
            raise _err(slug, 'target_year must be a year such as 2027 or null, got %r' % (ty,))
        g['target_year'] = ty
    if 'time_commitment' in goal:
        g['time_commitment'] = _enum(goal['time_commitment'], 'time_commitment', COMMITMENTS, slug, allow_none=True)
    if 'season_notes' in goal:
        g['season_notes'] = _str(goal['season_notes'], 'season_notes', slug)
    if 'difficulty' in goal and goal['difficulty'] is not None:
        d = goal['difficulty']
        if not isinstance(d, dict) or not isinstance(d.get('system'), str) or not isinstance(d.get('value'), str) \
                or not d['system'].strip() or not d['value'].strip() or set(d) - {'system', 'value', 'note'}:
            raise _err(slug, 'difficulty must be {"system": ..., "value": ..., "note": optional} or null, got %r' % (d,))
        g['difficulty'] = {'system': d['system'].strip(), 'value': d['value'].strip(), 'note': _str(d.get('note', ''), 'difficulty.note', slug)}
    if 'route_scope' in goal:
        g['route_scope'] = _enum(goal['route_scope'], 'route_scope', SCOPES, slug)
    if 'route_source' in goal:
        rs = goal['route_source']
        if not isinstance(rs, dict) or set(rs) - {'kind', 'url', 'label', 'checked_at', 'public_copy_approved', 'approximation_note'}:
            raise _err(slug, 'route_source must be an object with kind, url, label, checked_at, public_copy_approved, approximation_note')
        src = g['route_source']
        if 'kind' in rs:
            src['kind'] = _enum(rs['kind'], 'route_source.kind', SOURCE_KINDS, slug)
        src['url'] = _url(rs.get('url'), 'route_source.url', slug)
        src['label'] = _str(rs.get('label'), 'route_source.label', slug, allow_none=True)
        src['checked_at'] = _date(rs.get('checked_at'), 'route_source.checked_at', slug)
        if 'public_copy_approved' in rs:
            src['public_copy_approved'] = _bool(rs['public_copy_approved'], 'route_source.public_copy_approved', slug)
        src['approximation_note'] = _str(rs.get('approximation_note'), 'route_source.approximation_note', slug, allow_none=True)
        if src['kind'] == 'author-drawn' and not src['approximation_note']:
            raise _err(slug, 'route_source.approximation_note is required for an author-drawn route (say that the line is a sketch)')
    ids = set()
    if 'references' in goal:
        refs = goal['references']
        if not isinstance(refs, list):
            raise _err(slug, 'references must be a list')
        for i, r in enumerate(refs):
            if not isinstance(r, dict) or set(r) - {'id', 'label', 'url', 'checked_at', 'note'}:
                raise _err(slug, 'references[%d] must have id, label, url, checked_at and an optional note' % i)
            rid = _str(r.get('id'), 'references[%d].id' % i, slug)
            if not _ID.match(rid):
                raise _err(slug, 'references[%d].id must be lower-case letters, digits and dashes, got %r' % (i, rid))
            if rid in ids:
                raise _err(slug, "references: duplicate id '%s'" % rid)
            ids.add(rid)
            url = _url(r.get('url'), 'references[%d].url' % i, slug)
            if not url:
                raise _err(slug, 'references[%d].url is required' % i)
            g['references'].append({'id': rid, 'label': _str(r.get('label'), 'references[%d].label' % i, slug), 'url': url,
                                    'checked_at': _date(r.get('checked_at'), 'references[%d].checked_at' % i, slug),
                                    'note': _str(r.get('note', ''), 'references[%d].note' % i, slug)})
    if 'field_evidence' in goal:
        fe = goal['field_evidence']
        if not isinstance(fe, dict):
            raise _err(slug, 'field_evidence must be an object keyed by field name')
        for field, ev in fe.items():
            if not isinstance(ev, dict) or set(ev) - {'source_ids', 'status'}:
                raise _err(slug, 'field_evidence.%s must be {"source_ids": [...], "status": "proposed" | "approved"}' % field)
            sids = ev.get('source_ids')
            if not isinstance(sids, list) or not sids or not all(isinstance(s, str) for s in sids):
                raise _err(slug, 'field_evidence.%s.source_ids must be a non-empty list of reference ids' % field)
            for s in sids:
                if s not in ids:
                    raise _err(slug, "field_evidence.%s names reference '%s', which is not in references" % (field, s))
            g['field_evidence'][field] = {'source_ids': list(sids), 'status': _enum(ev.get('status'), 'field_evidence.%s.status' % field, EVIDENCE_STATES, slug)}
    for field, present in (('difficulty', g['difficulty'] is not None), ('season_notes', bool(g['season_notes']))):
        if present and g['field_evidence'].get(field, {}).get('status') != 'approved':
            raise _err(slug, '%s is researched information: it needs field_evidence.%s with approved source_ids before it is published' % (field, field))
    if 'checklist' in goal:
        cl = goal['checklist']
        if not isinstance(cl, list):
            raise _err(slug, 'checklist must be a list')
        seen = set()
        for i, c in enumerate(cl):
            if not isinstance(c, dict) or set(c) != {'id', 'text', 'done'}:
                raise _err(slug, 'checklist[%d] must have exactly id, text and done' % i)
            cid = _str(c['id'], 'checklist[%d].id' % i, slug)
            if not cid or cid in seen:
                raise _err(slug, "checklist[%d].id must be unique and non-empty (got '%s')" % (i, cid))
            seen.add(cid)
            g['checklist'].append({'id': cid, 'text': _str(c['text'], 'checklist[%d].text' % i, slug), 'done': _bool(c['done'], 'checklist[%d].done' % i, slug)})
    if 'outings' in goal:
        os_ = goal['outings']
        if not isinstance(os_, list):
            raise _err(slug, 'outings must be a list')
        for i, o in enumerate(os_):
            if not isinstance(o, dict) or set(o) - {'outcome', 'date', 'report_slug', 'note'}:
                raise _err(slug, 'outings[%d] must have outcome, and optional date, report_slug, note' % i)
            rs_ = o.get('report_slug')
            if rs_ is not None and (not isinstance(rs_, str) or not _ID.match(rs_)):
                raise _err(slug, 'outings[%d].report_slug must be a trip slug or null, got %r' % (i, rs_))
            g['outings'].append({'outcome': _enum(o.get('outcome'), 'outings[%d].outcome' % i, OUTCOMES, slug),
                                 'date': _date(o.get('date'), 'outings[%d].date' % i, slug), 'report_slug': rs_,
                                 'note': _str(o.get('note', ''), 'outings[%d].note' % i, slug)})
    completed = [o for o in g['outings'] if o['outcome'] == 'completed']
    attempted = [o for o in g['outings'] if o['outcome'] == 'attempted']
    if g['status'] == 'completed' and not completed:
        raise _err(slug, "status is 'completed' but no outing with outcome 'completed' is logged (log one with tools/ticklist.py log-outing)")
    if completed and g['status'] != 'completed':
        raise _err(slug, "an outing with outcome 'completed' is logged, so status must be 'completed' (it is '%s')" % g['status'])
    if g['status'] == 'attempted' and not attempted:
        raise _err(slug, "status is 'attempted' but no outing with outcome 'attempted' is logged")
    if 'route' in goal and goal['route'] is not None:
        r = goal['route']
        need = {'source_sha256', 'method', 'selected', 'alternatives', 'segments', 'points', 'elevation', 'times', 'waypoints'}
        if not isinstance(r, dict) or set(r) != need:
            raise _err(slug, 'route must have exactly %s' % ', '.join(sorted(need)))
        if not isinstance(r['source_sha256'], str) or not _HEX64.match(r['source_sha256']):
            raise _err(slug, 'route.source_sha256 must be a 64-character hex SHA-256')
        sel = r['selected']
        if not isinstance(sel, dict) or sel.get('type') not in ('trk', 'rte') or not isinstance(sel.get('index'), int) \
                or not (sel.get('name') is None or isinstance(sel.get('name'), str)) or set(sel) - {'type', 'index', 'name'}:
            raise _err(slug, 'route.selected must be {"type": "trk" | "rte", "index": n, "name": text | null}')
        for k in ('alternatives', 'segments', 'points', 'waypoints'):
            if not isinstance(r[k], int) or isinstance(r[k], bool) or r[k] < 0:
                raise _err(slug, 'route.%s must be a whole number' % k)
        g['route'] = {'source_sha256': r['source_sha256'], 'method': _str(r['method'], 'route.method', slug),
                      'selected': {'type': sel['type'], 'index': sel['index'], 'name': sel.get('name')},
                      'alternatives': r['alternatives'], 'segments': r['segments'], 'points': r['points'],
                      'elevation': _enum(r['elevation'], 'route.elevation', ('full', 'partial', 'none'), slug),
                      'times': _bool(r['times'], 'route.times', slug), 'waypoints': r['waypoints']}
        if track_path and os.path.exists(track_path):
            with open(track_path, 'rb') as fh:
                actual = hashlib.sha256(fh.read()).hexdigest()
            if actual != g['route']['source_sha256']:
                raise _err(slug, 'track.gpx has changed since it was imported (SHA-256 %s, route.source_sha256 %s): re-import it with '
                                 'tools/ticklist.py rather than editing the published file' % (actual[:12], g['route']['source_sha256'][:12]))
    return g


def load_goal(folder, slug, kind):
    """The goal dict for a planned trip (defaults with legacy=True when goal.json is absent); None for other kinds, which
    may not carry a sidecar."""
    p = os.path.join(folder, 'goal.json')
    if kind != 'planned':
        if os.path.exists(p):
            raise _err(slug, 'only a kind: planned trip can carry a goal sidecar (this trip is kind: %s)' % kind)
        return None
    if not os.path.exists(p):
        g = defaults()
        g['legacy'] = True
        return g
    try:
        with open(p, encoding='utf-8') as fh:
            data = json.load(fh)
    except ValueError as ex:
        raise _err(slug, 'not valid JSON (%s)' % ex)
    return validate(data, slug, track_path=os.path.join(folder, 'track.gpx'))


def is_active(goal):
    return not goal['archived'] and goal['status'] != 'completed'


def approx_label(goal, stats=None):
    """Mono-S items for the stats strip's provenance line: [] for a legacy goal (nothing is known about the numbers'
    origin), else 'APPROX. FROM THE PLANNED ROUTE' plus the elevation caveat."""
    if not goal or goal.get('legacy') or not goal.get('route'):
        return []
    items = ['APPROX. FROM THE PLANNED ROUTE']
    cav = ELEVATION_LABELS.get(goal['route']['elevation'], '')
    if cav:
        items.append(cav)
    return items


def validate_site(site):
    """Outings must point at published, non-planned reports."""
    by = site.get('by_slug') or {}
    for t in site.get('goals') or []:
        for o in t['goal']['outings']:
            rs = o.get('report_slug')
            if not rs:
                continue
            r = by.get(rs)
            if r is None or r['kind'] == 'planned':
                raise _err(t['slug'], "outing report_slug '%s' is not a published report%s" % (rs, ' (it is a planned route)' if r else ''))


def backlinks(site):
    """{report slug: [goal trips whose outings name it]}, in goal order."""
    out = {}
    for t in site.get('goals') or []:
        for o in t['goal']['outings']:
            if o.get('report_slug'):
                out.setdefault(o['report_slug'], [])
                if t not in out[o['report_slug']]:
                    out[o['report_slug']].append(t)
    return out
