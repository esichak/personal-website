"""Phase 2T: tools/lib/goals.py, the goal.json sidecar behind a tick-list goal (defaults, validate, load_goal, is_active,
approx_label, validate_site) and its hook in content.load_trip (t['goal']).

A full valid goal.json (VALID) is the baseline; every enum and type rule of the contract gets one invalid variant, each
asserted to raise content.ContentError with the `content/trips/<slug>/goal.json: ` prefix and the field's name. The
semantic rules (evidence for difficulty and season_notes, the author-drawn approximation note, status / outing consistency,
the route checksum against a written track.gpx, a sidecar beside a non-planned trip) and the legacy planned route without a
sidecar have their own tests. Fixtures are synthetic: an invented ridge, invented references at example.test. goals is
imported in setUp so a missing module fails each test clearly instead of breaking discovery.
"""
import hashlib
import importlib
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the repo root, from tests/
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402

import helpers  # noqa: E402

SLUG = 'synthetic-ridge-traverse'
PREFIX = 'content/trips/%s/goal.json: ' % SLUG
SHA0 = '0' * 64

VALID = {
    'schema_version': 1, 'status': 'shortlisted', 'priority': 'high', 'archived': False,
    'tags': ['ridge-traverse', 'scramble'], 'why': 'A long ridge I keep looking at from the road.',
    'added_at': '2026-05-01', 'target_months': [6, 7, 9], 'target_year': 2027, 'time_commitment': 'full-day',
    'season_notes': 'The guidebook describes a July to September window.',
    'difficulty': {'system': 'YDS', 'value': 'Class 3', 'note': 'One short exposed step.'},
    'route_scope': 'full-intended-route',
    'route_source': {'kind': 'planner-export', 'url': 'https://example.test/plan/1', 'label': 'Planner export',
                     'checked_at': '2026-05-01', 'public_copy_approved': True, 'approximation_note': None},
    'references': [{'id': 'guide-1', 'label': 'Synthetic guidebook', 'url': 'https://example.test/guide', 'checked_at': '2026-05-01',
                    'note': 'Route description.'},
                   {'id': 'access-1', 'label': 'Managing agency', 'url': 'http://example.test/access', 'checked_at': None}],
    'field_evidence': {'difficulty': {'source_ids': ['guide-1'], 'status': 'approved'},
                       'season_notes': {'source_ids': ['guide-1', 'access-1'], 'status': 'approved'}},
    'checklist': [{'id': 'descent', 'text': 'Does the file include the descent?', 'done': False},
                  {'id': 'permit', 'text': 'Is a permit needed?', 'done': True}],
    'outings': [],
    'route': None,
}
ROUTE = {'source_sha256': SHA0, 'method': 'ticklist-gpx-1', 'selected': {'type': 'trk', 'index': 0, 'name': 'Synthetic ridge'},
         'alternatives': 1, 'segments': 1, 'points': 12, 'elevation': 'full', 'times': True, 'waypoints': 0}
ATTEMPT = {'outcome': 'attempted', 'date': '2026-07-12', 'report_slug': None, 'note': 'Turned around at the notch.'}
DONE = {'outcome': 'completed', 'date': '2026-08-30', 'report_slug': 'synthetic-report', 'note': ''}
DEFAULT_KEYS = {'schema_version', 'status', 'priority', 'archived', 'tags', 'why', 'added_at', 'target_months', 'target_year',
                'time_commitment', 'season_notes', 'difficulty', 'route_scope', 'route_source', 'references', 'field_evidence',
                'checklist', 'outings', 'route', 'legacy'}


def load_goals(tc):
    """tools/lib/goals.py, or a clear failure of the calling test when it is missing."""
    try:
        return importlib.import_module('goals')
    except ImportError as ex:
        tc.fail('tools/lib/goals.py is not importable: %s' % ex)


def deep(d):
    return json.loads(json.dumps(d))


def variant(**over):
    """A deep copy of VALID with top-level keys replaced."""
    g = deep(VALID)
    g.update(over)
    return g


def with_route(**over):
    r = deep(ROUTE)
    r.update(over)
    return variant(route=r)


def with_source(**over):
    s = deep(VALID['route_source'])
    s.update(over)
    return variant(route_source=s)


def with_ref(i, **over):
    refs = deep(VALID['references'])
    refs[i].update(over)
    return variant(references=refs)


def with_evidence(field, **over):
    fe = deep(VALID['field_evidence'])
    fe[field].update(over)
    return variant(field_evidence=fe)


def with_check(i, **over):
    cl = deep(VALID['checklist'])
    cl[i].update(over)
    return variant(checklist=cl)


class GoalsFixture(unittest.TestCase):

    def setUp(self):
        self.goals = load_goals(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def validate(self, goal, slug=SLUG):
        return self.goals.validate(goal, slug)

    def assertRejects(self, goal, needle, slug=SLUG):
        """validate() raises a ContentError whose message carries the file prefix and names `needle`."""
        with self.assertRaises(content.ContentError) as cm:
            self.validate(goal, slug)
        msg = str(cm.exception)
        self.assertTrue(msg.startswith('content/trips/%s/goal.json: ' % slug), msg)
        self.assertIn(needle, msg)
        return msg

    def folder(self, slug=SLUG, goal=None, track=None, **meta):
        """A planned trip folder in the temp dir, with goal.json (a dict, or raw text) and track.gpx (bytes) when given."""
        meta.setdefault('kind', 'planned')
        meta.setdefault('activity', 'hike')
        f = helpers.make_trip(self.tmp, slug, **meta)
        if goal is not None:
            with open(os.path.join(f, 'goal.json'), 'w', encoding='utf-8') as fh:
                fh.write(goal if isinstance(goal, str) else json.dumps(goal))
        if track is not None:
            with open(os.path.join(f, 'track.gpx'), 'wb') as fh:
                fh.write(track)
        return f


# ---------------------------------------------------------------- constants and defaults

class ConstantTests(GoalsFixture):

    def test_enum_tuples(self):
        g = self.goals
        self.assertEqual(g.STATUSES, ('idea', 'researching', 'shortlisted', 'attempted', 'completed'))
        self.assertEqual(g.PRIORITIES, ('high', 'normal', 'someday'))
        self.assertEqual(g.COMMITMENTS, ('half-day', 'full-day', 'overnight', 'multi-day'))
        self.assertEqual(g.SCOPES, ('full-intended-route', 'approach-only', 'ascent-only', 'partial', 'unknown'))
        self.assertEqual(g.SOURCE_KINDS, ('author-drawn', 'planner-export', 'third-party-recording', 'own-prior-recording', 'unknown'))
        self.assertEqual(g.OUTCOMES, ('attempted', 'completed'))
        self.assertEqual(g.EVIDENCE_STATES, ('proposed', 'approved'))

    def test_labels(self):
        self.assertEqual(self.goals.STATUS_LABELS, {'idea': 'Idea', 'researching': 'Researching', 'shortlisted': 'Shortlisted',
                                                    'attempted': 'Attempted', 'completed': 'Completed'})
        self.assertEqual(self.goals.PRIORITY_LABELS, {'high': 'High priority', 'normal': 'Normal priority', 'someday': 'Someday'})

    def test_defaults_has_every_key_at_its_default(self):
        d = self.goals.defaults()
        self.assertEqual(set(d), DEFAULT_KEYS)
        self.assertEqual(d['schema_version'], 1)
        self.assertEqual((d['status'], d['priority'], d['archived']), ('idea', 'normal', False))
        self.assertEqual((d['tags'], d['why'], d['added_at']), ([], '', None))
        self.assertEqual((d['target_months'], d['target_year'], d['time_commitment']), ([], None, None))
        self.assertEqual((d['season_notes'], d['difficulty'], d['route_scope']), ('', None, 'unknown'))
        self.assertEqual(d['route_source'], {'kind': 'unknown', 'url': None, 'label': None, 'checked_at': None,
                                             'public_copy_approved': False, 'approximation_note': None})
        self.assertEqual((d['references'], d['field_evidence'], d['checklist'], d['outings']), ([], {}, [], []))
        self.assertIsNone(d['route'])
        self.assertIs(d['legacy'], False)

    def test_defaults_is_a_fresh_dict_each_time(self):
        a = self.goals.defaults()
        a['tags'].append('x')
        a['route_source']['kind'] = 'author-drawn'
        b = self.goals.defaults()
        self.assertEqual(b['tags'], [])
        self.assertEqual(b['route_source']['kind'], 'unknown')
        self.assertIsNot(a, b)

    def test_defaults_validate(self):
        d = self.goals.defaults()
        out = self.validate(d)
        for k in DEFAULT_KEYS - {'legacy'}:
            self.assertEqual(out[k], d[k], k)


# ---------------------------------------------------------------- validate: the full example and normalisation

class ValidateAcceptsTests(GoalsFixture):

    def test_full_example_is_accepted_and_returned_whole(self):
        out = self.validate(deep(VALID))
        for k, v in VALID.items():
            if k == 'target_months':
                self.assertEqual(sorted(out[k]), sorted(v))
            elif k in ('references', 'difficulty'):
                continue   # optional notes are normalised below
            else:
                self.assertEqual(out[k], v, k)
        self.assertEqual(set(out), DEFAULT_KEYS)
        self.assertIs(out['legacy'], False)

    def test_strings_are_stripped(self):
        out = self.validate(variant(why='  trimmed  ', tags=[' ridge ', 'scramble'], season_notes='  windowed  '))
        self.assertEqual(out['why'], 'trimmed')
        self.assertEqual(out['tags'], ['ridge', 'scramble'])
        self.assertEqual(out['season_notes'], 'windowed')

    def test_lists_are_copied_not_shared(self):
        g = deep(VALID)
        out = self.validate(g)
        out['tags'].append('added-later')
        out['references'].clear()
        out['checklist'][0]['done'] = True
        self.assertEqual(g['tags'], VALID['tags'])
        self.assertEqual(len(g['references']), 2)
        self.assertFalse(g['checklist'][0]['done'])

    def test_missing_keys_take_their_defaults(self):
        out = self.validate({'status': 'researching'})
        self.assertEqual(out['status'], 'researching')
        self.assertEqual(out['priority'], 'normal')
        self.assertEqual(out['route_source']['kind'], 'unknown')
        self.assertEqual(out['outings'], [])
        self.assertIsNone(out['route'])

    def test_a_route_block_is_accepted(self):
        out = self.validate(with_route())
        self.assertEqual(out['route']['source_sha256'], SHA0)
        self.assertEqual(out['route']['selected'], {'type': 'trk', 'index': 0, 'name': 'Synthetic ridge'})
        self.assertEqual(out['route']['elevation'], 'full')

    def test_optional_difficulty_note_and_reference_note_may_be_absent(self):
        g = variant(difficulty={'system': 'YDS', 'value': 'Class 3'})
        g['references'][0].pop('note')
        out = self.validate(g)
        self.assertEqual((out['difficulty']['system'], out['difficulty']['value']), ('YDS', 'Class 3'))
        self.assertEqual(out['references'][0]['id'], 'guide-1')

    def test_non_object_is_rejected(self):
        for bad in ([], 'text', 3, None):
            with self.subTest(value=bad):
                with self.assertRaises(content.ContentError) as cm:
                    self.validate(bad)
                self.assertTrue(str(cm.exception).startswith(PREFIX), str(cm.exception))

    def test_error_is_a_value_error_naming_the_slug(self):
        with self.assertRaises(ValueError) as cm:
            self.validate(variant(status='done'), slug='other-goal')
        self.assertTrue(str(cm.exception).startswith('content/trips/other-goal/goal.json: '))


# ---------------------------------------------------------------- validate: one invalid variant per rule

class EnumAndTypeRuleTests(GoalsFixture):

    def test_status_enum(self):
        self.assertRejects(variant(status='done'), 'status')
        self.assertRejects(variant(status=3), 'status')

    def test_priority_enum(self):
        self.assertRejects(variant(priority='urgent'), 'priority')

    def test_archived_bool(self):
        self.assertRejects(variant(archived='yes'), 'archived')
        self.assertRejects(variant(archived=1), 'archived')

    def test_tags_list_of_strings(self):
        self.assertRejects(variant(tags='ridge'), 'tags')
        self.assertRejects(variant(tags=['ridge', 7]), 'tags')

    def test_why_string(self):
        self.assertRejects(variant(why=['because']), 'why')

    def test_added_at_date(self):
        self.assertRejects(variant(added_at='2026-13-40'), 'added_at')
        self.assertRejects(variant(added_at='yesterday'), 'added_at')
        self.assertRejects(variant(added_at=20260501), 'added_at')

    def test_target_months_unique_ints_1_to_12(self):
        self.assertRejects(variant(target_months='6,7'), 'target_months')
        self.assertRejects(variant(target_months=[6, 13]), 'target_months')
        self.assertRejects(variant(target_months=[0]), 'target_months')
        self.assertRejects(variant(target_months=[6, 6]), 'target_months')
        self.assertRejects(variant(target_months=[6.0]), 'target_months')
        self.assertRejects(variant(target_months=['6']), 'target_months')
        self.assertEqual(sorted(self.validate(variant(target_months=[12, 1]))['target_months']), [1, 12])

    def test_target_year_int_in_range_or_null(self):
        self.assertRejects(variant(target_year='2027'), 'target_year')
        self.assertRejects(variant(target_year=1999), 'target_year')
        self.assertRejects(variant(target_year=2101), 'target_year')
        self.assertIsNone(self.validate(variant(target_year=None))['target_year'])

    def test_time_commitment_enum_or_null(self):
        self.assertRejects(variant(time_commitment='week'), 'time_commitment')
        self.assertIsNone(self.validate(variant(time_commitment=None))['time_commitment'])

    def test_season_notes_string(self):
        self.assertRejects(variant(season_notes=['x']), 'season_notes')

    def test_difficulty_shape(self):
        self.assertRejects(variant(difficulty='hard'), 'difficulty')
        self.assertRejects(variant(difficulty={'value': '5.7'}), 'difficulty')
        self.assertRejects(variant(difficulty={'system': 'YDS'}), 'difficulty')
        self.assertRejects(variant(difficulty={'system': 'YDS', 'value': 'Class 3', 'note': 3}), 'difficulty')

    def test_route_scope_enum(self):
        self.assertRejects(variant(route_scope='whole'), 'route_scope')

    def test_route_source_shape_and_kind(self):
        self.assertRejects(variant(route_source='planner'), 'route_source')
        self.assertRejects(with_source(kind='ai-sketch'), 'route_source')

    def test_route_source_url_http_or_https_only(self):
        for url in ('ftp://example.test/x', 'javascript:alert(1)', 'example.test/no-scheme', 7):
            with self.subTest(url=url):
                self.assertRejects(with_source(url=url), 'route_source')
        self.assertEqual(self.validate(with_source(url='http://example.test/x'))['route_source']['url'], 'http://example.test/x')
        self.assertIsNone(self.validate(with_source(url=None))['route_source']['url'])

    def test_route_source_other_fields(self):
        self.assertRejects(with_source(label=3), 'route_source')
        self.assertRejects(with_source(checked_at='May'), 'route_source')
        self.assertRejects(with_source(public_copy_approved='yes'), 'route_source')
        self.assertRejects(with_source(approximation_note=7), 'route_source')

    def test_references_shape(self):
        self.assertRejects(variant(references='x'), 'references')
        self.assertRejects(variant(references=[{'id': 'a', 'label': 'A'}]), 'references')   # no url
        self.assertRejects(with_ref(0, label=3), 'references')
        self.assertRejects(with_ref(0, checked_at='May 2026'), 'references')
        self.assertRejects(with_ref(0, note=['x']), 'references')

    def test_reference_ids_match_pattern_and_are_unique(self):
        self.assertRejects(with_ref(0, id='Guide 1'), 'references')
        self.assertRejects(with_ref(0, id='guide_1'), 'references')
        self.assertRejects(with_ref(1, id='guide-1'), 'guide-1')

    def test_reference_urls_http_or_https_only(self):
        for url in ('ftp://example.test/x', 'javascript:alert(1)', 'mailto:x@example.test', '//example.test', ''):
            with self.subTest(url=url):
                self.assertRejects(with_ref(1, url=url), 'references')

    def test_field_evidence_shape(self):
        self.assertRejects(variant(field_evidence=[]), 'field_evidence')
        fe = deep(VALID['field_evidence'])
        fe['difficulty'] = 'guide-1'
        self.assertRejects(variant(field_evidence=fe), 'field_evidence')
        self.assertRejects(with_evidence('difficulty', source_ids=[]), 'field_evidence')
        self.assertRejects(with_evidence('difficulty', source_ids='guide-1'), 'field_evidence')
        self.assertRejects(with_evidence('difficulty', status='maybe'), 'field_evidence')

    def test_field_evidence_source_ids_must_exist(self):
        self.assertRejects(with_evidence('difficulty', source_ids=['guide-1', 'nope']), 'nope')

    def test_checklist_shape(self):
        self.assertRejects(variant(checklist='x'), 'checklist')
        self.assertRejects(variant(checklist=[{'id': 'a', 'done': False}]), 'checklist')   # no text
        self.assertRejects(with_check(0, done='yes'), 'checklist')
        self.assertRejects(with_check(0, text=5), 'checklist')

    def test_checklist_ids_unique(self):
        self.assertRejects(with_check(1, id='descent'), 'checklist')

    def test_outings_shape(self):
        self.assertRejects(variant(outings='x'), 'outings')
        self.assertRejects(variant(status='attempted', outings=[dict(ATTEMPT, outcome='tried')]), 'outings')
        self.assertRejects(variant(status='attempted', outings=[dict(ATTEMPT, date='July')]), 'outings')
        self.assertRejects(variant(status='attempted', outings=[dict(ATTEMPT, report_slug=7)]), 'outings')
        self.assertRejects(variant(status='attempted', outings=[dict(ATTEMPT, note=5)]), 'outings')

    def test_route_shape(self):
        self.assertRejects(variant(route='x'), 'route')
        self.assertRejects(with_route(source_sha256='abc'), 'route')
        self.assertRejects(with_route(source_sha256='g' * 64), 'route')
        self.assertRejects(with_route(method=7), 'route')
        self.assertRejects(with_route(selected={'type': 'wpt', 'index': 0, 'name': None}), 'route')
        self.assertRejects(with_route(selected={'type': 'trk', 'index': 'a', 'name': None}), 'route')
        self.assertRejects(with_route(alternatives='two'), 'route')
        self.assertRejects(with_route(segments=1.5), 'route')
        self.assertRejects(with_route(points='12'), 'route')
        self.assertRejects(with_route(elevation='some'), 'route')
        self.assertRejects(with_route(times='yes'), 'route')
        self.assertRejects(with_route(waypoints=None), 'route')


# ---------------------------------------------------------------- validate: evidence, provenance and status rules

class SemanticRuleTests(GoalsFixture):

    def test_difficulty_needs_approved_evidence(self):
        fe = deep(VALID['field_evidence'])
        fe.pop('difficulty')
        self.assertRejects(variant(field_evidence=fe), 'difficulty')
        self.assertRejects(with_evidence('difficulty', status='proposed'), 'difficulty')
        self.validate(deep(VALID))   # approved: fine

    def test_season_notes_need_approved_evidence_only_when_non_empty(self):
        fe = deep(VALID['field_evidence'])
        fe.pop('season_notes')
        self.assertRejects(variant(field_evidence=fe), 'season_notes')
        self.assertRejects(with_evidence('season_notes', status='proposed'), 'season_notes')
        out = self.validate(variant(season_notes='', field_evidence={'difficulty': fe['difficulty']}))
        self.assertEqual(out['season_notes'], '')
        out = self.validate(variant(season_notes='   ', field_evidence={'difficulty': fe['difficulty']}))
        self.assertEqual(out['season_notes'], '')

    def test_proposed_evidence_is_allowed_for_other_fields(self):
        fe = deep(VALID['field_evidence'])
        fe['region'] = {'source_ids': ['access-1'], 'status': 'proposed'}
        out = self.validate(variant(field_evidence=fe))
        self.assertEqual(out['field_evidence']['region']['status'], 'proposed')

    def test_author_drawn_needs_an_approximation_note(self):
        self.assertRejects(with_source(kind='author-drawn', approximation_note=None), 'approximation_note')
        self.assertRejects(with_source(kind='author-drawn', approximation_note='   '), 'approximation_note')
        out = self.validate(with_source(kind='author-drawn', approximation_note='A hand-drawn line, not a recording.'))
        self.assertEqual(out['route_source']['approximation_note'], 'A hand-drawn line, not a recording.')
        self.validate(with_source(kind='planner-export', approximation_note=None))   # other kinds need none

    def test_completed_status_needs_a_completed_outing(self):
        msg = self.assertRejects(variant(status='completed', outings=[]), 'completed')
        self.assertIn('outing', msg.lower())
        self.assertRejects(variant(status='completed', outings=[deep(ATTEMPT)]), 'completed')

    def test_completed_outing_needs_completed_status(self):
        self.assertRejects(variant(status='shortlisted', outings=[deep(DONE)]), 'completed')
        self.assertRejects(variant(status='attempted', outings=[deep(ATTEMPT), deep(DONE)]), 'completed')

    def test_attempted_status_needs_an_attempted_outing(self):
        self.assertRejects(variant(status='attempted', outings=[]), 'attempted')
        out = self.validate(variant(status='attempted', outings=[deep(ATTEMPT)]))
        self.assertEqual(out['outings'][0]['outcome'], 'attempted')

    def test_attempted_before_completed_is_valid(self):
        out = self.validate(variant(status='completed', outings=[deep(ATTEMPT), deep(DONE)]))
        self.assertEqual([o['outcome'] for o in out['outings']], ['attempted', 'completed'])
        self.assertEqual(out['outings'][1]['report_slug'], 'synthetic-report')
        self.assertEqual(out['outings'][0]['note'], 'Turned around at the notch.')

    def test_completion_without_date_or_report_is_valid(self):
        out = self.validate(variant(status='completed', outings=[{'outcome': 'completed', 'date': None, 'report_slug': None}]))
        self.assertIsNone(out['outings'][0]['date'])
        self.assertIsNone(out['outings'][0]['report_slug'])
        self.assertEqual(out['status'], 'completed')

    def test_an_attempt_may_follow_a_completion(self):
        out = self.validate(variant(status='completed', outings=[deep(DONE), deep(ATTEMPT)]))
        self.assertEqual(len(out['outings']), 2)

    def test_reopened_goal_keeps_its_attempts(self):
        out = self.validate(variant(status='researching', archived=False, outings=[deep(ATTEMPT)]))
        self.assertEqual(out['status'], 'researching')
        self.assertEqual(len(out['outings']), 1)

    def test_archived_does_not_change_status_rules(self):
        out = self.validate(variant(archived=True, status='completed', outings=[deep(DONE)]))
        self.assertTrue(out['archived'])
        self.assertRejects(variant(archived=True, status='completed', outings=[]), 'completed')


# ---------------------------------------------------------------- load_goal

class LoadGoalTests(GoalsFixture):

    def test_planned_without_sidecar_is_legacy_defaults(self):
        f = self.folder(track=b'<gpx/>')
        g = self.goals.load_goal(f, SLUG, 'planned')
        self.assertIs(g['legacy'], True)
        d = self.goals.defaults()
        for k in DEFAULT_KEYS - {'legacy'}:
            self.assertEqual(g[k], d[k], k)

    def test_planned_with_sidecar_is_validated_and_not_legacy(self):
        f = self.folder(goal=VALID)
        g = self.goals.load_goal(f, SLUG, 'planned')
        self.assertIs(g['legacy'], False)
        self.assertEqual((g['status'], g['priority']), ('shortlisted', 'high'))
        self.assertEqual(g['references'][1]['url'], 'http://example.test/access')

    def test_non_planned_without_sidecar_is_none(self):
        f = helpers.make_trip(self.tmp, 'synthetic-report', activity='hike', date='2026-08-30', track=True)
        self.assertIsNone(self.goals.load_goal(f, 'synthetic-report', 'trip'))
        self.assertIsNone(self.goals.load_goal(f, 'synthetic-report', 'multi-day'))

    def test_sidecar_beside_a_non_planned_trip_is_an_error(self):
        f = self.folder('synthetic-report', goal=self.goals.defaults(), kind='trip', date='2026-08-30')
        for kind in ('trip', 'multi-day', 'series'):
            with self.subTest(kind=kind):
                with self.assertRaises(content.ContentError) as cm:
                    self.goals.load_goal(f, 'synthetic-report', kind)
                self.assertTrue(str(cm.exception).startswith(
                    'content/trips/synthetic-report/goal.json: only a kind: planned trip can carry a goal sidecar'), str(cm.exception))

    def test_malformed_json_is_an_error(self):
        f = self.folder(goal='{"status": "idea",')
        with self.assertRaises(content.ContentError) as cm:
            self.goals.load_goal(f, SLUG, 'planned')
        self.assertTrue(str(cm.exception).startswith(PREFIX))

    def test_non_object_json_is_an_error(self):
        for text in ('[]', '"idea"', 'null', '3'):
            with self.subTest(text=text):
                f = self.folder(goal=text)
                with self.assertRaises(content.ContentError) as cm:
                    self.goals.load_goal(f, SLUG, 'planned')
                self.assertTrue(str(cm.exception).startswith(PREFIX))

    def test_invalid_sidecar_errors_carry_the_file_prefix(self):
        f = self.folder(goal=variant(status='done'))
        with self.assertRaises(content.ContentError) as cm:
            self.goals.load_goal(f, SLUG, 'planned')
        self.assertTrue(str(cm.exception).startswith(PREFIX))
        self.assertIn('status', str(cm.exception))

    def test_route_sha_must_match_the_written_track(self):
        track = b'<gpx><trk><trkseg><trkpt lat="38.9" lon="-120.1"/></trkseg></trk></gpx>\n'
        sha = hashlib.sha256(track).hexdigest()
        f = self.folder(goal=with_route(source_sha256=sha), track=track)
        g = self.goals.load_goal(f, SLUG, 'planned')
        self.assertEqual(g['route']['source_sha256'], sha)
        with open(os.path.join(f, 'track.gpx'), 'ab') as fh:
            fh.write(b'\n')   # the published file changed: never a silent re-measure
        with self.assertRaises(content.ContentError) as cm:
            self.goals.load_goal(f, SLUG, 'planned')
        msg = str(cm.exception)
        self.assertTrue(msg.startswith(PREFIX))
        self.assertIn('sha', msg.lower())

    def test_route_sha_mismatch_from_the_start(self):
        f = self.folder(goal=with_route(source_sha256=SHA0), track=b'<gpx/>')
        with self.assertRaises(content.ContentError):
            self.goals.load_goal(f, SLUG, 'planned')

    def test_route_block_without_a_track_file_is_not_checked(self):
        f = self.folder(goal=with_route(source_sha256=SHA0))
        g = self.goals.load_goal(f, SLUG, 'planned')
        self.assertEqual(g['route']['source_sha256'], SHA0)


# ---------------------------------------------------------------- content.load_trip integration

class LoadTripTests(GoalsFixture):

    def test_legacy_planned_route_loads_with_defaults_and_legacy_flag(self):
        self.folder(track=b'<gpx/>', title='Legacy Ridge', stats={'distance_km': 8.0})
        t = helpers.load(self.tmp, SLUG)
        self.assertEqual(t['kind'], 'planned')
        self.assertIs(t['goal']['legacy'], True)
        self.assertEqual(t['goal']['status'], 'idea')
        self.assertEqual(t['stats']['distance_km'], 8.0)
        self.assertIsNone(t['stats']['gain_m'])   # unknown stays None, never 0

    def test_planned_route_with_sidecar(self):
        self.folder(goal=VALID, title='Synthetic Ridge Traverse')
        t = helpers.load(self.tmp, SLUG)
        self.assertIs(t['goal']['legacy'], False)
        self.assertEqual(t['goal']['status'], 'shortlisted')
        self.assertEqual(t['title'], 'Synthetic Ridge Traverse')   # title stays in index.md, never in goal.json

    def test_non_planned_trip_has_goal_none(self):
        helpers.make_trip(self.tmp, 'synthetic-report', activity='hike', date='2026-08-30', track=True)
        self.assertIsNone(helpers.load(self.tmp, 'synthetic-report')['goal'])

    def test_sidecar_beside_a_report_fails_the_load(self):
        self.folder('synthetic-report', goal=self.goals.defaults(), kind='trip', date='2026-08-30')
        with self.assertRaises(content.ContentError) as cm:
            helpers.load(self.tmp, 'synthetic-report')
        self.assertIn('content/trips/synthetic-report/goal.json', str(cm.exception))


# ---------------------------------------------------------------- is_active, approx_label, validate_site

class HelperTests(GoalsFixture):

    def test_is_active(self):
        g = self.goals
        for status in g.STATUSES:
            for archived in (False, True):
                with self.subTest(status=status, archived=archived):
                    goal = variant(status=status, archived=archived)
                    self.assertEqual(g.is_active(goal), not archived and status != 'completed')

    def test_approx_label_for_a_legacy_goal_is_empty(self):
        g = self.goals.defaults()
        g['legacy'] = True
        self.assertFalse(self.goals.approx_label(g, {'distance_km': 8.0}))

    def test_approx_label_without_a_route_block_is_empty(self):
        self.assertFalse(self.goals.approx_label(self.goals.defaults(), {'distance_km': 8.0}))

    def test_approx_label_elevation_caveats(self):
        none = self.validate(with_route(elevation='none'))
        self.assertEqual(list(self.goals.approx_label(none, {'distance_km': 8.0})), ['APPROX. FROM THE PLANNED ROUTE', 'NO ELEVATION IN THE FILE'])
        partial = self.validate(with_route(elevation='partial'))
        self.assertEqual(list(self.goals.approx_label(partial, {'distance_km': 8.0})), ['APPROX. FROM THE PLANNED ROUTE', 'PARTIAL ELEVATION'])

    def test_approx_label_full_elevation_has_no_caveat(self):
        full = self.validate(with_route(elevation='full'))
        items = list(self.goals.approx_label(full, {'distance_km': 8.0, 'gain_m': 500}))
        self.assertEqual(items[0], 'APPROX. FROM THE PLANNED ROUTE')
        self.assertFalse(any('ELEVATION' in x for x in items[1:]))

    def site(self, goal_outings, report_kind='trip'):
        """A site with one goal carrying `goal_outings` and one other trip 'synthetic-report' of `report_kind`."""
        status = 'completed' if any(o['outcome'] == 'completed' for o in goal_outings) else ('attempted' if goal_outings else 'idea')
        self.folder(goal=variant(status=status, outings=goal_outings))
        if report_kind == 'planned':
            helpers.make_trip(self.tmp, 'synthetic-report', activity='hike', kind='planned', track=True)
        else:
            helpers.make_trip(self.tmp, 'synthetic-report', activity='hike', date='2026-08-30', track=True)
        trips = helpers.load_dir(self.tmp)
        site = helpers.make_site(trips, register=False)
        site['goals'] = site['planned']
        site['active_goals'] = [t for t in site['goals'] if self.goals.is_active(t['goal'])]
        return site

    def test_validate_site_accepts_outings_naming_published_reports(self):
        self.assertIsNone(self.goals.validate_site(self.site([deep(DONE)])))
        self.assertIsNone(self.goals.validate_site(self.site([])))

    def test_validate_site_rejects_an_unknown_report_slug(self):
        site = self.site([dict(DONE, report_slug='nowhere-report')])
        with self.assertRaises(content.ContentError) as cm:
            self.goals.validate_site(site)
        msg = str(cm.exception)
        self.assertIn(SLUG, msg)
        self.assertIn('nowhere-report', msg)

    def test_validate_site_rejects_a_planned_report_slug(self):
        site = self.site([deep(DONE)], report_kind='planned')
        with self.assertRaises(content.ContentError) as cm:
            self.goals.validate_site(site)
        self.assertIn('synthetic-report', str(cm.exception))

    def test_validate_site_ignores_outings_without_a_report(self):
        self.assertIsNone(self.goals.validate_site(self.site([{'outcome': 'completed', 'date': None, 'report_slug': None}])))


if __name__ == '__main__':
    unittest.main()
