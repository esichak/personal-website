"""Read a Strava bulk export (the folder with activities.csv, activities/ and media/)."""
import csv
import os
from datetime import datetime

# Strava activity type -> (site activity, Other sub-type)
TYPE_MAP = {
    'Backcountry Ski': ('ski', None), 'Alpine Ski': ('ski', None), 'Nordic Ski': ('ski', None), 'Snowboard': ('ski', None),
    'Rock Climb': ('climb', None), 'Rock Climbing': ('climb', None),
    'Hike': ('hike', None), 'Walk': ('hike', None), 'Trail Run': ('hike', None), 'Run': ('hike', None),
    'Ride': ('mtb', None), 'Mountain Bike Ride': ('mtb', None), 'E-Mountain Bike Ride': ('mtb', None), 'Gravel Ride': ('mtb', None),
    'Stand Up Paddling': ('other', 'SUP'), 'Kayaking': ('other', 'Kayaking'), 'Canoeing': ('other', 'Canoeing'),
    'Rowing': ('other', 'Rowing'), 'Snowshoe': ('other', 'Snowshoe'), 'Swim': ('other', 'Swimming'),
}


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


class Export:
    def __init__(self, folder):
        self.folder = os.path.expanduser(folder)
        with open(os.path.join(self.folder, 'activities.csv'), newline='', encoding='utf-8') as fh:
            rows = list(csv.reader(fh))
        self.hdr, self.rows = rows[0], rows[1:]

    def _col(self, r, name, which=0):
        ids = [i for i, h in enumerate(self.hdr) if h == name]
        return r[ids[which]] if len(ids) > which else ''

    def record(self, r):
        c = self._col
        media = [m for m in c(r, 'Media').split('|') if m]
        dist = _num(c(r, 'Distance', 1)) if len([h for h in self.hdr if h == 'Distance']) > 1 else None
        if dist is None:  # the first Distance column is km, the second metres
            km = _num(c(r, 'Distance'))
            dist = km * 1000 if km is not None else None
        return {
            'id': c(r, 'Activity ID'),
            'name': c(r, 'Activity Name').strip(),
            'type': c(r, 'Activity Type'),
            'date_utc': datetime.strptime(c(r, 'Activity Date'), '%b %d, %Y, %I:%M:%S %p'),
            'desc': c(r, 'Activity Description').strip(),
            'file': os.path.join(self.folder, c(r, 'Filename')) if c(r, 'Filename') else None,
            'distance_m': dist,
            'moving_s': _num(c(r, 'Moving Time')),
            'elapsed_s': _num(c(r, 'Elapsed Time', 1)) or _num(c(r, 'Elapsed Time')),
            'gain_m': _num(c(r, 'Elevation Gain')),
            'loss_m': _num(c(r, 'Elevation Loss')),
            'low_m': _num(c(r, 'Elevation Low')),
            'high_m': _num(c(r, 'Elevation High')),
            'media': [os.path.join(self.folder, m) for m in media],
        }

    def by_id(self, act_id):
        for r in self.rows:
            if self._col(r, 'Activity ID') == str(act_id):
                return self.record(r)
        raise KeyError('no activity %s in %s' % (act_id, self.folder))

    def search(self, text):
        t = text.lower()
        return [self.record(r) for r in self.rows if t in self._col(r, 'Activity Name').lower()]


def stats_from(rec):
    from tracks import fmt_hm
    s = {}
    if rec.get('distance_m'):
        s['distance_km'] = round(rec['distance_m'] / 1000.0, 2)
    if rec.get('moving_s'):
        s['moving'] = fmt_hm(rec['moving_s'])
    if rec.get('elapsed_s'):
        s['elapsed'] = fmt_hm(rec['elapsed_s'])
    for k in ('gain_m', 'loss_m', 'high_m', 'low_m'):
        if rec.get(k) is not None:
            s[k] = int(round(rec[k]))
    return s


def paragraphs(desc):
    """Strava descriptions use single newlines between thoughts; make each its own Markdown paragraph."""
    lines = [l.strip() for l in (desc or '').replace('\r\n', '\n').split('\n')]
    return '\n\n'.join(l for l in lines if l)
