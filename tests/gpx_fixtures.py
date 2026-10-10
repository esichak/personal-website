"""Synthetic GPX fixtures for the Phase 2T tests (tests/test_gpxroute.py and tests/test_ticklist_cli.py).

Every file is hand-shaped XML text built from short point lists around an invented spot (38.9°N 120.1°W, which is open
water on Lake Tahoe: no real route). The point lists are kept beside the text so a test can compute its own haversine sums,
hysteresis gain and expected timestamps from the same numbers the file holds. Nothing here is a real goal, a real trip or a
repurposed recording, and nothing is written under content/ or rendered/: callers write the strings to a temp dir.
"""
import math
from datetime import datetime, timedelta, timezone

NS = 'xmlns="http://www.topografix.com/GPX/1/1"'
HEAD = '<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="synthetic fixture" %s>\n' % NS
HEAD_NO_NS = '<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="synthetic fixture">\n'
T0 = datetime(2026, 7, 4, 15, 0, tzinfo=timezone.utc)   # the recorder's clock: never a trip date


def iso(minutes):
    """The GPX <time> text `minutes` after T0, ISO with a trailing Z (the form fit_reader parses)."""
    return (T0 + timedelta(minutes=minutes)).strftime('%Y-%m-%dT%H:%M:%SZ')


def ts(minutes):
    """The unix timestamp iso(minutes) stands for."""
    return (T0 + timedelta(minutes=minutes)).timestamp()


def line(lat0, lon0, n, dlat=0.001, dlon=0.0, eles=None, times=True, t0=0):
    """n points stepping dlat/dlon from (lat0, lon0): [(lat, lon, ele|None, iso|None)]. eles: a list (None entries allowed)
    or None for no elevation; times=False leaves <time> out; t0: minutes after T0 for the first point."""
    pts = []
    for i in range(n):
        ele = None if eles is None else eles[i]
        pts.append((round(lat0 + i * dlat, 6), round(lon0 + i * dlon, 6), ele, iso(t0 + i) if times else None))
    return pts


def pt_xml(tag, p):
    lat, lon, ele, when = p
    inner = ''
    if ele is not None:
        inner += '<ele>%s</ele>' % ele
    if when is not None:
        inner += '<time>%s</time>' % when
    return '<%s lat="%s" lon="%s">%s</%s>' % (tag, lat, lon, inner, tag)


def trk(segments, name=None):
    segs = ''.join('<trkseg>%s</trkseg>' % ''.join(pt_xml('trkpt', p) for p in seg) for seg in segments)
    return '<trk>%s%s</trk>' % (('<name>%s</name>' % name) if name else '', segs)


def rte(points, name=None):
    return '<rte>%s%s</rte>' % (('<name>%s</name>' % name) if name else '', ''.join(pt_xml('rtept', p) for p in points))


def wpt(lat, lon, name):
    return '<wpt lat="%s" lon="%s"><name>%s</name></wpt>' % (lat, lon, name)


def gpx(*elements, **kw):
    return kw.get('head', HEAD) + '\n'.join(elements) + '\n</gpx>\n'


# ---------------------------------------------------------------- the point lists

# a 12-point track with full elevation and timestamps; 3 m hysteresis: gain 57, loss 7 (see ref_gain_loss)
ELES_A = [2000, 2005, 2010, 2008, 2003, 2015, 2025, 2030, 2028, 2040, 2045, 2050]
SEG_A = line(38.900, -120.100, 12, eles=ELES_A)

# three segments with ~2-3 km gaps between them; each boundary elevation equals the next segment's first, so a per-segment
# hysteresis and one over the concatenated points agree (gain 35, loss 20) and only the bridging distance differs
SEG_M1 = line(38.900, -120.100, 5, eles=[2000, 2005, 2010, 2015, 2020], t0=0)
SEG_M2 = line(38.920, -120.100, 5, eles=[2020, 2015, 2010, 2005, 2000], t0=30)
SEG_M3 = line(38.950, -120.100, 4, eles=[2000, 2005, 2010, 2015], t0=60)
SEGS_M = [SEG_M1, SEG_M2, SEG_M3]

# a route (rtept) of 11 points heading east, elevation but no timestamps: gain 100
RTE_PTS = line(39.000, -120.200, 11, dlat=0.0, dlon=0.001, eles=[2500 + 10 * i for i in range(11)], times=False)

# alternatives: two tracks (the second in two segments) and a route
TRK_N = line(38.800, -120.000, 6, eles=[2100 + 4 * i for i in range(6)], times=False)
TRK_S1 = line(38.810, -120.000, 4, eles=[2200, 2206, 2212, 2218], times=False)
TRK_S2 = line(38.815, -120.000, 3, eles=[2218, 2224, 2230], times=False)
RTE_D = line(38.820, -120.000, 5, eles=[2300, 2290, 2280, 2270, 2260], times=False)

ELES_PARTIAL = [2000, None, 2010, None, 2020, None, 2030, None, 2040, None, 2050, None]
SEG_NO_ELE = line(38.900, -120.100, 12)
SEG_PARTIAL = line(38.900, -120.100, 12, eles=ELES_PARTIAL)
SEG_NO_TIME = line(38.900, -120.100, 12, eles=ELES_A, times=False)
SEG_SPARSE = line(38.900, -120.100, 5, eles=[2000, 2010, 2020, 2030, 2040])

# ---------------------------------------------------------------- the files

SINGLE = gpx(trk([SEG_A], 'Synthetic ridge'))
SINGLE_NO_NS = gpx(trk([SEG_A], 'Synthetic ridge'), head=HEAD_NO_NS)
UNNAMED = gpx(trk([SEG_A]))
MULTISEG = gpx(trk(SEGS_M, 'Three segments'))
ROUTE_ONLY = gpx(rte(RTE_PTS, 'Ridge route'))
ALTERNATIVES = gpx(trk([TRK_N], 'North approach'), trk([TRK_S1, TRK_S2], 'South approach'), rte(RTE_D, 'Descent'))
WAYPOINT_ONLY = gpx(wpt(38.9, -120.1, 'Trailhead'), wpt(38.91, -120.1, 'Saddle'), wpt(38.92, -120.1, 'Top'))
TRACK_PLUS_WPTS = gpx(wpt(38.9, -120.1, 'Trailhead'), trk([SEG_A], 'With waypoints'), wpt(38.911, -120.1, 'Top'))
NO_ELE = gpx(trk([SEG_NO_ELE], 'No elevation'))
PARTIAL_ELE = gpx(trk([SEG_PARTIAL], 'Partial elevation'))
NO_TIME = gpx(trk([SEG_NO_TIME], 'No timestamps'))
SPARSE = gpx(trk([SEG_SPARSE], 'Five points'))
EMPTY_SEG = gpx(trk([[], SEG_A, []], 'Empty segments around one'))
EMPTY_TRACK_AND_ROUTE = gpx(trk([[]], 'Nothing in here'), rte(RTE_PTS, 'Ridge route'))

DOCTYPE = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE gpx [<!ENTITY boom "x">]>\n<gpx version="1.1" %s>\n%s\n</gpx>\n'
           % (NS, trk([SEG_A])))
ENTITY_IN_COMMENT = gpx(trk([SEG_A]), '<!-- <!ENTITY boom "x"> -->')
NOT_XML = HEAD + '<trk><trkseg><trkpt lat="38.9" lon="-120.1"></trkseg>'
NON_GPX_ROOT = '<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document/></kml>\n'
LAT_OUT = gpx(trk([[(95.0, -120.1, 2000, None), (38.9, -120.1, 2000, None)]]))
LON_OUT = gpx(trk([[(38.9, -190.5, 2000, None), (38.9, -120.1, 2000, None)]]))
MISSING_LAT = gpx('<trk><trkseg><trkpt lon="-120.1"><ele>2000</ele></trkpt><trkpt lat="38.9" lon="-120.1"></trkpt></trkseg></trk>')
NAN_LAT = gpx(trk([[('nan', -120.1, 2000, None), (38.9, -120.1, 2000, None)]]))
INF_LON = gpx(trk([[(38.9, 'inf', 2000, None), (38.9, -120.1, 2000, None)]]))
BAD_ELE = gpx(trk([[(38.9, -120.1, 'abc', None), (38.901, -120.1, 2000, None)]]))
INF_ELE = gpx(trk([[(38.9, -120.1, 'inf', None), (38.901, -120.1, 2000, None)]]))


# ---------------------------------------------------------------- reference maths (independent of tools/lib)

def hav_m(a, b):
    """Great-circle metres between two (lat, lon, ...) points, R = 6371 km (as tools/lib/geo.hav)."""
    r = 6371000.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    d = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, d)))


def poly_km(seg):
    return sum(hav_m(a, b) for a, b in zip(seg, seg[1:])) / 1000.0


def ref_gain_loss(eles, hysteresis=3):
    """Gain and loss with tracks.compute_stats' hysteresis: a move counts only once it leaves a 3 m band around the last
    counted elevation."""
    gain = loss = 0.0
    ref = eles[0]
    for e in eles[1:]:
        if e - ref >= hysteresis:
            gain += e - ref
            ref = e
        elif ref - e >= hysteresis:
            loss += ref - e
            ref = e
    return int(round(gain)), int(round(loss))
