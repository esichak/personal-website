#!/usr/bin/env python3
"""Tick-list goals: save an idea or a route, update its intent, log an outing, export a review packet or the public data.

  python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity hike --dry-run
  python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity hike --gpx ~/Downloads/route.gpx --select trk:0 --publish-track --no-render
  python3 tools/ticklist.py update YOUR-GOAL-SLUG --status shortlisted --priority high --months 6,7
  python3 tools/ticklist.py log-outing YOUR-GOAL-SLUG --outcome completed --date 2027-07-04 --report-slug an-existing-report
  python3 tools/ticklist.py review-packet YOUR-GOAL-SLUG --out ~/Desktop/goal-review.md
  python3 tools/ticklist.py export --out ~/Desktop/tick-list.json

Everything is local and file-backed: the commands write content/trips/<slug>/index.md, goal.json and (only with
--publish-track) track.gpx; nothing is committed, pushed or deployed. New goals are drafts (draft: true) until you remove
that line. The GPX is somebody's plan or recording, not a trip: routes and tracks are kept apart, segments are kept,
alternatives need an explicit choice, no elevation means no gain, and timestamps are never a date. A local path never
reaches a public file. --publish-track approves copying the file into the public checkout; it is not a push, a deploy
or a judgement about the route. See docs/TICK_LIST_GUIDE.md.
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import frontmatter  # noqa: E402
import goals  # noqa: E402
import gpxroute  # noqa: E402

TRIPS = content.TRIPS_DIR          # patched by the tests
RENDER = os.path.join(ROOT, 'tools', 'render.py')
ACTIVITIES = ('ski', 'climb', 'hike', 'mtb', 'other')
_SLUG = re.compile(r'^[a-z0-9][a-z0-9-]{0,79}$')


class Fail(Exception):
    """A user-facing refusal: printed on one line, exit status 2, nothing written."""


def today():
    return datetime.date.today().isoformat()


def say(*parts):
    print(' '.join(str(p) for p in parts))


def folder_of(slug):
    if not _SLUG.match(slug or ''):
        raise Fail('slug must be lower-case letters, digits and dashes (got %r)' % slug)
    return os.path.join(TRIPS, slug)


def read_index(folder):
    with open(os.path.join(folder, 'index.md'), encoding='utf-8') as fh:
        return frontmatter.split(fh.read())


def read_goal(folder, slug):
    """The raw goal.json (or the defaults for a legacy goal), plus whether the file exists."""
    p = os.path.join(folder, 'goal.json')
    if not os.path.exists(p):
        g = goals.defaults()
        g.pop('legacy')
        return g, False
    with open(p, encoding='utf-8') as fh:
        try:
            return json.load(fh), True
        except ValueError as ex:
            raise Fail('%s is not valid JSON (%s)' % (os.path.relpath(p, ROOT), ex))


def public_goal(g):
    return {k: v for k, v in g.items() if k != 'legacy'}


def write_goal(folder, g, dry):
    text = json.dumps(public_goal(g), indent=2, ensure_ascii=False) + '\n'
    p = os.path.join(folder, 'goal.json')
    if dry:
        say('  would write', os.path.relpath(p, ROOT))
        return
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(text)
    say('  wrote', os.path.relpath(p, ROOT))


def write_index(folder, meta, body, dry):
    p = os.path.join(folder, 'index.md')
    if dry:
        say('  would write', os.path.relpath(p, ROOT))
        return
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(frontmatter.render(meta, body))
    say('  wrote', os.path.relpath(p, ROOT))


def load_goal_trip(slug):
    folder = folder_of(slug)
    if not os.path.exists(os.path.join(folder, 'index.md')):
        raise Fail('no goal at content/trips/%s/' % slug)
    meta, body = read_index(folder)
    if meta.get('kind') != 'planned':
        raise Fail('content/trips/%s/ is a %s, not a planned route (tick-list goal)' % (slug, meta.get('kind') or 'trip'))
    return folder, meta, body


def published_sha256s():
    """{sha256: slug} for every goal's published route: the checksum its goal.json records, or, for a planned route with
    a track.gpx and no route block (saved before the tick list), the checksum of that file as it is."""
    out = {}
    for idx in sorted(glob.glob(os.path.join(TRIPS, '*', 'index.md'))):
        folder = os.path.dirname(idx)
        sha = None
        gp = os.path.join(folder, 'goal.json')
        if os.path.exists(gp):
            try:
                with open(gp, encoding='utf-8') as fh:
                    r = (json.load(fh) or {}).get('route') or {}
                sha = r.get('source_sha256') if isinstance(r, dict) else None
            except (ValueError, AttributeError):
                sha = None
        tp = os.path.join(folder, 'track.gpx')
        if not sha and os.path.exists(tp):
            try:
                with open(idx, encoding='utf-8') as fh:
                    planned = frontmatter.split(fh.read())[0].get('kind') == 'planned'
            except ValueError:
                planned = False
            if planned:
                with open(tp, 'rb') as fh:
                    sha = hashlib.sha256(fh.read()).hexdigest()
        if sha:
            out[sha] = os.path.basename(folder)
    return out


def carried(info):
    """What a file carries besides its geometry (published as-is when the whole file is copied)."""
    c = info.get('contains') or {}
    out = []
    if c.get('metadata'):
        out.append('metadata (%s)' % ', '.join(c['metadata']))
    if c.get('extensions'):
        out.append('extensions (device or app data such as heart rate)')
    if c.get('links'):
        out.append('%d link(s)' % c['links'])
    if c.get('waypoint_names'):
        out.append('named waypoints (%s)' % ', '.join(c['waypoint_names'][:5]) + (', …' if len(c['waypoint_names']) > 5 else ''))
    if c.get('times'):
        out.append('timestamps')
    if c.get('comments'):
        out.append('XML comments')
    return out


def months_arg(v):
    if not v:
        return None
    try:
        ms = sorted({int(x) for x in str(v).split(',') if x.strip()})
    except ValueError:
        raise Fail('--months must be numbers 1-12 separated by commas, got %r' % v)
    if any(m < 1 or m > 12 for m in ms):
        raise Fail('--months must be between 1 and 12')
    return ms


def list_arg(v):
    return [x.strip() for x in str(v).split(',') if x.strip()] if v else None


def apply_intent(g, a):
    """Copy the intent options an add / update command carries into the goal dict (None = not given)."""
    for k in ('status', 'priority', 'why', 'time_commitment', 'route_scope', 'target_year'):
        v = getattr(a, k, None)
        if v is not None:
            g[k] = v
    if getattr(a, 'tags', None) is not None:
        g['tags'] = list_arg(a.tags) or []
    if getattr(a, 'months', None) is not None:
        g['target_months'] = months_arg(a.months) or []
    if getattr(a, 'archived', None) is not None:
        g['archived'] = a.archived == 'true'
    src = g.setdefault('route_source', goals.defaults()['route_source'])
    if not isinstance(src, dict):
        raise Fail('goal.json: route_source must be an object (it is %s); fix the file by hand, then run this again' % json.dumps(src))
    for k, opt in (('kind', 'source_kind'), ('url', 'source_url'), ('label', 'source_label'), ('checked_at', 'checked_at'), ('approximation_note', 'approximation_note')):
        v = getattr(a, opt, None)
        if v is not None:
            src[k] = v


def validated(g, slug, track_path=None):
    try:
        return goals.validate(g, slug, track_path=track_path)
    except ValueError as ex:
        raise Fail(str(ex))


# ---------------------------------------------------------------- add

def cmd_add(a):
    if a.activity not in ACTIVITIES:
        raise Fail('--activity must be one of %s' % ', '.join(ACTIVITIES))
    title = a.title.strip()
    if not title:
        raise Fail('--title is required')
    slug = a.slug if a.slug is not None else content.slugify(title)[:60].strip('-')   # an explicit --slug is checked as given
    if a.slug is None and not slug:
        raise Fail('the title %r gives no usable folder name (letters and digits only survive); pass one with --slug' % title)
    folder = folder_of(slug)
    if os.path.exists(folder):
        raise Fail('content/trips/%s/ already exists; pick another name with --slug' % slug)
    meta = {'title': title, 'activity': a.activity, 'kind': 'planned', 'draft': True}
    if a.subtype:
        meta['subtype'] = a.subtype
    if a.place:
        meta['place'] = a.place
    if a.region:
        meta['region'] = a.region
    g = goals.defaults()
    g.pop('legacy')
    g['added_at'] = today()
    apply_intent(g, a)
    body = (a.notes or '').strip()
    say('Goal:', title, '(%s)' % slug)
    track_bytes = None
    if a.gpx:
        path = os.path.expanduser(a.gpx)
        if not os.path.isfile(path):
            raise Fail('no such GPX file')
        try:
            info = gpxroute.inspect(path)
        except gpxroute.GpxError as ex:
            raise Fail('GPX rejected: %s' % ex)
        say('  GPX: %d bytes, sha256 %s…, %d track(s), %d route(s), %d waypoint(s)'
            % (info['bytes'], info['sha256'][:12], len(info['tracks']), len(info['routes']), info['waypoints']))
        extra = carried(info)
        if extra:
            say('  the file also carries: %s — a published copy keeps all of it; check that none of it is private' % '; '.join(extra))
        try:
            cand = gpxroute.select(info, a.select)
        except gpxroute.NoRoute as ex:
            say('  no route in the file (%s): saving a metadata-only idea; add a route later' % ex)
            cand = None
        except gpxroute.SelectionNeeded as ex:
            raise Fail(str(ex))
        except gpxroute.GpxError as ex:
            raise Fail(str(ex))
        if cand:
            m = gpxroute.measure(cand['segments'])
            say('  selected %s' % gpxroute.describe(cand))
            say('  approximate: %.2f km over %d segment%s (nothing bridged between segments), %d points%s'
                % (m['distance_km'], m['segments'], '' if m['segments'] == 1 else 's', m['points'], ' (sparse: a rough line)' if m['sparse'] else ''))
            say('  elevation:', {'full': 'every point (gain ≈ %s m, loss ≈ %s m, high ≈ %s m)' % (m['gain_m'], m['loss_m'], m['high_m']),
                                 'partial': 'only some points: no gain is recorded', 'none': 'none in the file: no gain or profile'}[m['elevation']])
            say('  timestamps:', 'present, ignored (they are the recorder’s, not a trip date)' if m['times'] else 'none')
            if a.publish_track:
                track_bytes = gpxroute.extract_bytes(path, cand)
                sha = hashlib.sha256(track_bytes).hexdigest()
                dup = published_sha256s().get(sha)
                if dup and not a.allow_duplicate:
                    raise Fail('this file is already published under content/trips/%s/ (same checksum); reference that goal, or pass --allow-duplicate' % dup)
                st = {'distance_km': m['distance_km']}
                for k in ('gain_m', 'loss_m', 'high_m', 'low_m'):
                    if m[k] is not None:
                        st[k] = m[k]
                meta['stats'] = st
                g['route'] = {'source_sha256': sha, 'method': gpxroute.METHOD,
                              'selected': {'type': cand['type'], 'index': cand['index'], 'name': cand['name']},
                              'alternatives': len(gpxroute.candidates(info)), 'segments': m['segments'], 'points': m['points'],
                              'elevation': m['elevation'], 'times': m['times'], 'waypoints': info['waypoints']}
                g['route_source']['public_copy_approved'] = True
                whole = track_bytes == open(path, 'rb').read()
                say('  publishing the %s (%d bytes, sha256 %s…) as track.gpx' % ('whole file' if whole else 'chosen element', len(track_bytes), sha[:12]))
                if not whole:
                    say('  the published copy holds only that %s: the file\'s other tracks and routes, its %d waypoint%s and its metadata are not copied'
                        % ('track' if cand['type'] == 'trk' else 'route', info['waypoints'], '' if info['waypoints'] == 1 else 's'))
            else:
                say('  not published: pass --publish-track to copy this geometry into the public checkout (nothing from it is written now)')
    g = validated(g, slug)
    say('Files:')
    if a.dry_run:
        say('  (dry run: nothing is written)')
        write_index(folder, meta, body, True)
        write_goal(folder, g, True)
        if track_bytes:
            say('  would write', os.path.relpath(os.path.join(folder, 'track.gpx'), ROOT))
        return 0
    os.makedirs(folder)
    write_index(folder, meta, body, False)
    write_goal(folder, g, False)
    if track_bytes:
        with open(os.path.join(folder, 'track.gpx'), 'wb') as fh:
            fh.write(track_bytes)
        say('  wrote', os.path.relpath(os.path.join(folder, 'track.gpx'), ROOT))
        if a.no_render:
            say('  map not rendered (--no-render): the goal page shows a map-unavailable note until render.py runs')
        else:
            say('Rendering the map (needs the internet)…')
            r = subprocess.run([sys.executable, RENDER, slug], cwd=ROOT)
            if r.returncode != 0:
                say('  render failed (exit %d): the goal is valid; the page says the map is not rendered yet. Re-run: python3 tools/render.py %s' % (r.returncode, slug))
    say('Next: review content/trips/%s/ (index.md, goal.json%s); remove "draft: true" to publish; python3 tools/build.py --check; '
        'git add "content/trips/%s"%s' % (slug, ', track.gpx' if track_bytes else '', slug, ' "rendered/trips/%s"' % slug if track_bytes and not a.no_render else ''))
    return 0


# ---------------------------------------------------------------- update / log-outing

def is_done(g):
    """True when the goal's history ends completed: a completed outing with no 'reopened' entry after it."""
    done = False
    for o in g.get('outings') or []:
        if isinstance(o, dict) and o.get('outcome') == 'completed':
            done = True
        elif isinstance(o, dict) and o.get('outcome') == 'reopened':
            done = False
    return done


def cmd_update(a):
    folder, meta, body = load_goal_trip(a.slug)
    g, existed = read_goal(folder, a.slug)
    if a.reopen:
        # reopening is an explicit, dated entry in the history; the completed outing stays where it is
        if not is_done(g):
            raise Fail('--reopen is for a completed goal; %s is not completed' % a.slug)
        if a.status is None or a.status == 'completed':
            raise Fail('--reopen needs the status the goal goes back to, e.g. --reopen --status shortlisted')
        g.setdefault('outings', []).append({'outcome': 'reopened', 'date': today(), 'report_slug': None,
                                            'note': (a.reopen_note or '').strip()})
    elif a.reopen_note:
        raise Fail('--reopen-note goes with --reopen')
    apply_intent(g, a)
    if a.reference_checked_at and not a.add_reference:
        raise Fail('--reference-checked-at goes with --add-reference')
    for ref in a.add_reference or []:
        parts = ref.split('|', 2)
        if len(parts) != 3:
            raise Fail('--add-reference wants ID|LABEL|URL')
        # a reference carries its own date (--reference-checked-at, else today); --checked-at is the route source's alone
        g.setdefault('references', []).append({'id': parts[0].strip(), 'label': parts[1].strip(), 'url': parts[2].strip(),
                                               'checked_at': a.reference_checked_at or today()})
    for text in a.add_check or []:
        ids = {c.get('id') for c in g.get('checklist', [])}
        i = len(g.get('checklist', [])) + 1
        while 'c%d' % i in ids:
            i += 1
        g.setdefault('checklist', []).append({'id': 'c%d' % i, 'text': text.strip(), 'done': False})
    for cid, done in ((a.check, True), (a.uncheck, False)):
        if cid:
            for c in g.get('checklist', []):
                if c.get('id') == cid:
                    c['done'] = done
                    break
            else:
                raise Fail('no checklist item with id %r' % cid)
    g = validated(g, a.slug, track_path=os.path.join(folder, 'track.gpx'))
    say('Goal:', meta.get('title'), '(%s)%s' % (a.slug, '' if existed else ' — no goal.json yet; creating it'))
    say('  status %s · priority %s · archived %s' % (g['status'], g['priority'], g['archived']))
    if a.reopen:
        say('  reopened on %s: the earlier outings stay in the history' % today())
    write_goal(folder, g, a.dry_run)
    return 0


def report_exists(slug):
    """A published (non-draft), non-planned trip with that slug."""
    p = os.path.join(TRIPS, slug or '', 'index.md')
    if not slug or not _SLUG.match(slug) or not os.path.exists(p):
        return False
    with open(p, encoding='utf-8') as fh:
        m, _b = frontmatter.split(fh.read())
    return m.get('kind') != 'planned' and not m.get('draft')


def cmd_log_outing(a):
    folder, meta, body = load_goal_trip(a.slug)
    g, _existed = read_goal(folder, a.slug)
    if a.report_slug and not report_exists(a.report_slug):
        raise Fail('--report-slug %r is not a published report (content/trips/<slug>/index.md, not a draft, not a planned route)' % a.report_slug)
    if a.date:
        try:
            datetime.date.fromisoformat(a.date)
        except ValueError:
            raise Fail('--date must be YYYY-MM-DD')
    outing = {'outcome': a.outcome, 'date': a.date, 'report_slug': a.report_slug, 'note': (a.note or '').strip()}
    g.setdefault('outings', []).append(outing)
    if a.outcome == 'completed':
        g['status'] = 'completed'
    elif g.get('status') != 'completed':
        g['status'] = 'attempted'
    g = validated(g, a.slug, track_path=os.path.join(folder, 'track.gpx'))
    say('Goal:', meta.get('title'), '(%s)' % a.slug)
    say('  logged: %s%s%s' % (a.outcome, (' on ' + a.date) if a.date else ' (date not recorded)', (' → report ' + a.report_slug) if a.report_slug else ''))
    say('  status is now', g['status'], '(the planned track and the report are untouched)')
    write_goal(folder, g, a.dry_run)
    return 0


# ---------------------------------------------------------------- review packet / export

PACKET_PROMPT_START = '## Ongoing use: add or enrich a tick-list goal'


def enrichment_prompt():
    p = os.path.join(ROOT, 'docs', 'TICK_LIST_GUIDE.md')
    if not os.path.exists(p):
        return '(docs/TICK_LIST_GUIDE.md is missing: see the plan, section 20.7)'
    text = open(p, encoding='utf-8').read()
    m = re.search(r'```text\n(Add or enrich this future goal.*?)```', text, re.S)
    return m.group(1).strip() if m else '(see the research prompt in docs/TICK_LIST_GUIDE.md)'


def public_record(slug, meta, g, track):
    st = meta.get('stats') or {}
    return {'slug': slug, 'url': 'trips/%s/' % slug, 'title': meta.get('title'), 'activity': meta.get('activity'), 'subtype': meta.get('subtype'),
            'place': meta.get('place'), 'region': meta.get('region'), 'draft': bool(meta.get('draft')),
            'status': g['status'], 'priority': g['priority'], 'archived': g['archived'], 'tags': g['tags'], 'why': g['why'],
            'added_at': g['added_at'], 'target_months': g['target_months'], 'target_year': g['target_year'],
            'time_commitment': g['time_commitment'], 'route_scope': g['route_scope'],
            'route_source': {k: g['route_source'][k] for k in ('kind', 'label', 'url', 'checked_at')},
            'references': [{k: r[k] for k in ('id', 'label', 'url', 'checked_at')} for r in g['references']],
            'approx_stats': {k: st.get(k) for k in ('distance_km', 'gain_m', 'loss_m', 'high_m', 'low_m') if st.get(k) is not None},
            'route': ({k: g['route'][k] for k in ('segments', 'points', 'elevation')} if g['route'] else None),
            'has_gpx': track,
            'outings': [{'outcome': o['outcome'], 'date': o['date'], 'report_url': ('trips/%s/' % o['report_slug']) if o['report_slug'] else None, 'note': o['note']}
                        for o in g['outings']]}


def cmd_review_packet(a):
    folder, meta, body = load_goal_trip(a.slug)
    g, _existed = read_goal(folder, a.slug)
    g = validated(g, a.slug)
    out = os.path.abspath(os.path.expanduser(a.out))
    # compared after resolving symbolic links, on both sides, so a link that leads into the checkout does not get past
    real_out = os.path.realpath(out)
    real_root = os.path.realpath(ROOT)
    if real_out == real_root or real_out.startswith(real_root + os.sep) or out == ROOT or out.startswith(ROOT + os.sep):
        raise Fail('the review packet must be written outside the checkout (it holds unreviewed research): %s is inside it' % out)
    track = os.path.exists(os.path.join(folder, 'track.gpx'))
    rec = public_record(a.slug, meta, g, track)
    missing = [k for k in ('place', 'region') if not meta.get(k)]
    if not g['why']:
        missing.append('why')
    if not g['target_months']:
        missing.append('target_months')
    if not g['time_commitment']:
        missing.append('time_commitment')
    if not g['difficulty']:
        missing.append('difficulty (with a source)')
    if not g['season_notes']:
        missing.append('season_notes (with a source)')
    if not g['references']:
        missing.append('references')
    lines = ['# Review packet: %s' % meta.get('title'), '', 'Goal `%s` · generated %s · public data as committed (draft: %s).' % (a.slug, today(), bool(meta.get('draft'))), '',
             '## Public data', '', '```json', json.dumps(rec, indent=2, ensure_ascii=False), '```', '',
             '## Route source and limits', '']
    if g['route']:
        r = g['route']
        lines += ['- Published GPX: %s, %s selected, %d segment(s), %d points, elevation %s, timestamps %s.'
                  % (goals.SOURCE_LABELS[g['route_source']['kind']], '%s:%d' % (r['selected']['type'], r['selected']['index']), r['segments'], r['points'], r['elevation'], 'present (ignored)' if r['times'] else 'none'),
                  '- Scope: %s. Approximate stats: %s.' % (goals.SCOPE_LABELS[g['route_scope']], json.dumps(rec['approx_stats'])),
                  '- The measurements are polyline lengths of the supplied geometry, not routed trail distances; no gain is given without full elevation.']
    elif track:
        lines += ['- A track.gpx exists but no route block records its provenance (legacy goal).']
    else:
        lines += ['- No GPX yet: an idea.']
    lines += ['', '## Planning notes', '', body.strip() or '(none)', '', '## Missing or unresolved', ''] + ['- %s' % m for m in missing] + ['',
              '## How to enrich', '', 'Run the prompt below in a chat session that can read sources. Every factual proposal must come back as',
              '`{"field": ..., "proposed_value": ..., "source_ids": [...], "checked_at": "YYYY-MM-DD", "qualification": ...}`; add the sources to',
              '`references` and the field to `field_evidence` with `"status": "proposed"`, review, then set `"approved"` and the value.',
              'Nothing here is applied automatically.', '', '```text', enrichment_prompt(), '```', '']
    if a.dry_run:
        say('  would write', out)
        return 0
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    say('  wrote', out, '(outside the checkout; do not commit it)')
    return 0


def cmd_export(a):
    recs = []
    for p in sorted(glob.glob(os.path.join(TRIPS, '*', 'index.md'))):
        folder = os.path.dirname(p)
        slug = os.path.basename(folder)
        with open(p, encoding='utf-8') as fh:
            meta, _body = frontmatter.split(fh.read())
        if meta.get('kind') != 'planned' or meta.get('draft'):
            continue
        g, existed = read_goal(folder, slug)
        g = validated(g, slug)
        rec = public_record(slug, meta, g, os.path.exists(os.path.join(folder, 'track.gpx')))
        rec['legacy'] = not existed   # a planned route saved before the tick list: no goal.json, default metadata
        recs.append(rec)
    text = json.dumps(recs, indent=2, ensure_ascii=False) + '\n'
    legacy = [r['slug'] for r in recs if r['legacy']]
    if legacy:
        # to stderr, so `export > file.json` still writes clean JSON
        sys.stderr.write('%d planned route%s without a goal.json (default metadata; review and run update on each): %s\n'
                         % (len(legacy), '' if len(legacy) == 1 else 's', ', '.join(legacy)))
    if a.out:
        out = os.path.abspath(os.path.expanduser(a.out))
        if a.dry_run:
            say('  would write', out)
            return 0
        os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
        with open(out, 'w', encoding='utf-8') as fh:
            fh.write(text)
        say('  wrote', out, '(%d goals)' % len(recs))
    else:
        sys.stdout.write(text)
    return 0


# ---------------------------------------------------------------- cli

def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    def intent(p):
        p.add_argument('--status', choices=goals.STATUSES)
        p.add_argument('--priority', choices=goals.PRIORITIES)
        p.add_argument('--tags', help='comma-separated')
        p.add_argument('--why', help='one sentence, in your words')
        p.add_argument('--months', help='preferred months, e.g. 6,7')
        p.add_argument('--year', dest='target_year', type=int)
        p.add_argument('--commitment', dest='time_commitment', choices=goals.COMMITMENTS)
        p.add_argument('--scope', dest='route_scope', choices=goals.SCOPES)
        p.add_argument('--source-kind', choices=goals.SOURCE_KINDS)
        p.add_argument('--source-url')
        p.add_argument('--source-label')
        p.add_argument('--checked-at', help='YYYY-MM-DD the source was read')
        p.add_argument('--approximation-note', help='required for an author-drawn line')
        p.add_argument('--dry-run', action='store_true', help='show what would be written; write nothing')
    p = sub.add_parser('add', help='save an idea, with or without a GPX')
    p.add_argument('--title', required=True)
    p.add_argument('--activity', required=True)
    p.add_argument('--subtype')
    p.add_argument('--slug')
    p.add_argument('--place')
    p.add_argument('--region')
    p.add_argument('--gpx', help='a GPX file to inspect (copied only with --publish-track)')
    p.add_argument('--select', help='trk:<i> or rte:<i> when the file holds several')
    p.add_argument('--publish-track', action='store_true', help='approve copying the chosen geometry into the public checkout')
    p.add_argument('--allow-duplicate', action='store_true')
    p.add_argument('--no-render', action='store_true', help='skip render.py (needs the internet)')
    p.add_argument('--notes', help='planning notes (Markdown)')
    intent(p)
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser('update', help='change intent, references, checklist')
    p.add_argument('slug')
    p.add_argument('--archived', choices=('true', 'false'))
    p.add_argument('--add-reference', action='append', help='ID|LABEL|URL (repeatable)')
    p.add_argument('--reference-checked-at', help='YYYY-MM-DD the added reference(s) were read (default: today)')
    p.add_argument('--add-check', action='append', help='a checklist question (repeatable)')
    p.add_argument('--check', help='checklist id to mark done')
    p.add_argument('--uncheck', help='checklist id to reopen')
    p.add_argument('--reopen', action='store_true', help='open a completed goal again, keeping its outings (needs --status)')
    p.add_argument('--reopen-note', help='why it is open again (optional, shown with the outings)')
    intent(p)
    p.set_defaults(fn=cmd_update)
    p = sub.add_parser('log-outing', help='record an explicit attempt or completion')
    p.add_argument('slug')
    p.add_argument('--outcome', required=True, choices=goals.OUTCOMES)
    p.add_argument('--date', help='YYYY-MM-DD (omit when unknown)')
    p.add_argument('--report-slug', help='an existing published report')
    p.add_argument('--note')
    p.add_argument('--dry-run', action='store_true')
    p.set_defaults(fn=cmd_log_outing)
    p = sub.add_parser('review-packet', help='write a Markdown packet for research, outside the checkout')
    p.add_argument('slug')
    p.add_argument('--out', required=True)
    p.add_argument('--dry-run', action='store_true')
    p.set_defaults(fn=cmd_review_packet)
    p = sub.add_parser('export', help='the public tick-list data as JSON')
    p.add_argument('--out')
    p.add_argument('--dry-run', action='store_true')
    p.set_defaults(fn=cmd_export)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        return a.fn(a)
    except Fail as ex:
        print('ERROR %s' % ex, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
