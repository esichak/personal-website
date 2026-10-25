"""Synthetic terrain, tracks and OpenStreetMap data for the offline renderer tests (tests/test_mapkit_golden.py).

Everything sits around the spot of tests/gpx_fixtures.py (38.9°N 120.1°W, a round number picked for the tests): the
ground is a made-up hill, the names are invented, and no track is a real trip or a repurposed recording. Nothing here
reads tools/lib, so a change to the renderer cannot change its own inputs.

  ground(lat, lon)        metres above sea level: a 650 m hill north-east of the spot, a lower ridge to the south-east,
                          a shallow basin under the lake, a gentle rise to the east and small ripples for the contours
  synth_tile(z, x, y)     what geo.get_tile returns for that Terrarium tile: 256 x 256 elevations in metres, row by row
                          (index py * 256 + px), sampled at each pixel's centre and quantised to 1/256 m as a Terrarium
                          PNG stores it; built from ground() and kept per tile for the life of the process
  terrarium_png(z, x, y)  the same tile as the bytes of an RGB Terrarium PNG (r * 256 + g + b / 256 - 32768), for
                          tests that go through geo.get_tile's own decoding
  OSM                     one hand-written Overpass answer in the shape render.fetch_osm returns (geo.overpass's
                          'out geom' JSON): a named lake, a primary road with a ref, a path, a named peak and a village
  LOOP_GPX, OUT_BACK_GPX  a hike loop over the hill and an out-and-back ride up its south-east side, written with
                          gpx_fixtures' helpers; their point lists and the stats a trip's front matter would carry are
                          kept beside them
  TOUR_DAY_GPX            the two days of a tour, with a gap between the end of day 1 and the start of day 2
  JOURNAL_DAY_GPX         three days of a journal, each going on from where the one before ended
"""
import array
import math
import struct
import zlib

import gpx_fixtures as gf

LAT0, LON0 = 38.9, -120.1
KY = 110574.0                                   # metres per degree of latitude
KX = 111320.0 * math.cos(math.radians(LAT0))    # metres per degree of longitude at LAT0


def _height(x, y):
    """Elevation (m) at x metres east and y metres north of (LAT0, LON0)."""
    return (1900.0 + 120.0 * math.tanh(x / 3000.0)
            + 650.0 * math.exp(-((x - 300.0) ** 2 + (y - 500.0) ** 2) / 1300.0 ** 2)
            + 260.0 * math.exp(-((x - 1700.0) ** 2 / 700.0 ** 2 + (y + 700.0) ** 2 / 1500.0 ** 2))
            - 60.0 * math.exp(-((x + 2000.0) ** 2 + (y - 300.0) ** 2) / 600.0 ** 2)
            + 14.0 * math.sin(x / 260.0) * math.cos(y / 340.0))


def ground(lat, lon):
    """Metres above sea level at (lat, lon): the synthetic hill, smooth and bounded everywhere."""
    return _height((lon - LON0) * KX, (lat - LAT0) * KY)


def _quantised(e):
    """An elevation as a Terrarium PNG holds it: (r, g, b) bytes and the value geo.get_tile decodes from them."""
    total = int(round((e + 32768.0) * 256.0))
    r, g, b = total >> 16, (total >> 8) & 255, total & 255
    return (r, g, b), (r * 256 + g + b / 256.0) - 32768.0


def _tile_rows(z, x, y):
    """Per row of tile (z, x, y): [((r, g, b), value)] for its 256 pixels, sampled at the pixel centres."""
    n = 256 * 2 ** z
    xs = [((x * 256 + i + 0.5) / n * 360.0 - 180.0 - LON0) * KX for i in range(256)]
    rows = []
    for j in range(256):
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y * 256 + j + 0.5) / n))))
        ym = (lat - LAT0) * KY
        rows.append([_quantised(_height(xm, ym)) for xm in xs])
    return rows


_TILES = {}


def synth_tile(z, x, y):
    """geo.get_tile's answer for tile (z, x, y), computed from ground(): array('d') of 65,536 elevations in metres."""
    key = (z, x, y)
    if key not in _TILES:
        _TILES[key] = array.array('d', [v for row in _tile_rows(z, x, y) for _, v in row])
    return _TILES[key]


def terrarium_png(z, x, y):
    """Tile (z, x, y) as RGB Terrarium PNG bytes (8-bit, no filter), the form the AWS terrain tiles come in."""
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    raw = bytearray()
    for row in _tile_rows(z, x, y):
        raw.append(0)
        for rgb, _ in row:
            raw.extend(rgb)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 256, 256, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(raw), 6)) + chunk(b'IEND', b''))


# ---------------------------------------------------------------- OpenStreetMap (hand-written; every name is invented)

OSM = {
    'version': 0.6,
    'generator': 'synthetic fixture',
    'elements': [
        {'type': 'way', 'id': 9001, 'tags': {'natural': 'water', 'water': 'lake', 'name': 'Ostrey Lake'},
         'geometry': [{'lat': 38.902713, 'lon': -120.11893}, {'lat': 38.90449, 'lon': -120.11934},
                      {'lat': 38.905111, 'lon': -120.121892}, {'lat': 38.905111, 'lon': -120.124279},
                      {'lat': 38.90449, 'lon': -120.126831}, {'lat': 38.902713, 'lon': -120.127241},
                      {'lat': 38.9013, 'lon': -120.126064}, {'lat': 38.899951, 'lon': -120.12446},
                      {'lat': 38.899951, 'lon': -120.121711}, {'lat': 38.9013, 'lon': -120.120107},
                      {'lat': 38.902713, 'lon': -120.11893}]},
        {'type': 'way', 'id': 9002, 'tags': {'highway': 'primary', 'ref': 'Q7', 'name': 'Mill Grade Road'},
         'geometry': [{'lat': 38.875582, 'lon': -120.12828}, {'lat': 38.886434, 'lon': -120.126548},
                      {'lat': 38.894574, 'lon': -120.124817}, {'lat': 38.903617, 'lon': -120.125971},
                      {'lat': 38.912661, 'lon': -120.128857}, {'lat': 38.923514, 'lon': -120.130588}]},
        {'type': 'way', 'id': 9003, 'tags': {'highway': 'path', 'name': 'Ostrey Lake Trail'},
         'geometry': [{'lat': 38.888243, 'lon': -120.11616}, {'lat': 38.891408, 'lon': -120.117891},
                      {'lat': 38.894574, 'lon': -120.119623}, {'lat': 38.897739, 'lon': -120.120777},
                      {'lat': 38.900271, 'lon': -120.121931}]},
        {'type': 'node', 'id': 9004, 'lat': 38.904522, 'lon': -120.096537,
         'tags': {'natural': 'peak', 'name': 'Quillon Peak', 'ele': '2566'}},
        {'type': 'node', 'id': 9005, 'lat': 38.888695, 'lon': -120.129434,
         'tags': {'place': 'village', 'name': 'Vardle', 'population': '240'}},
    ],
}


# ---------------------------------------------------------------- tracks

def _walk(waypoints, step, offset=0.0, wiggle=0.0, wiggle_m=90.0):
    """Points every ~step metres along a polyline of (x, y) metres, shifted `offset` metres to the right of the direction
    of travel plus a sine wiggle of amplitude `wiggle`, as a GPS trace wanders around the line it follows."""
    out, s = [], 0.0
    for (xa, ya), (xb, yb) in zip(waypoints, waypoints[1:]):
        seg = math.hypot(xb - xa, yb - ya)
        nx, ny = (yb - ya) / seg, -(xb - xa) / seg    # unit normal, to the right of travel
        k = max(1, int(round(seg / step)))
        for i in range(k):
            f = i / float(k)
            d = offset + wiggle * math.sin((s + f * seg) / wiggle_m)
            out.append((xa + (xb - xa) * f + nx * d, ya + (yb - ya) * f + ny * d))
        s += seg
    out.append(waypoints[-1])
    return out


def _points(xys):
    """(lat, lon, ele, None) tuples as gpx_fixtures.line makes them: lat/lon to 6 places, elevation from ground() plus a
    little recorder noise, to 0.1 m; no timestamps."""
    pts = []
    for i, (x, y) in enumerate(xys):
        ele = round(_height(x, y) + 1.5 * math.sin(i / 4.0), 1)
        pts.append((round(LAT0 + y / KY, 6), round(LON0 + x / KX, 6), ele, None))
    return pts


def _stats(pts):
    """What a trip's front matter carries for render.load_track: the published distance (km, 1 place) and high point."""
    return {'distance_km': round(gf.poly_km(pts), 1), 'high_m': int(round(max(p[2] for p in pts)))}


# a hike loop of about 7.4 km from a trailhead south-west of the hill, over the shoulder of Quillon Peak and back
LOOP_WAYPOINTS = [(-1400, -1300), (-1000, -700), (-500, -100), (0, 350), (280, 480), (800, 350), (1300, -200),
                  (1250, -900), (600, -1450), (-300, -1650), (-1000, -1550), (-1400, -1300)]
LOOP_PTS = _points(_walk(LOOP_WAYPOINTS, 15.0, wiggle=4.0))
LOOP_STATS = _stats(LOOP_PTS)
LOOP_GPX = gf.gpx(gf.trk([LOOP_PTS], 'Synthetic hill loop'))

# an out-and-back ride of about 3.1 km each way up the south-east ridge; the way back runs 6 m to the right of the way
# out (the other side of the trail) and is sampled more sparsely, as a faster descent is
OUT_WAYPOINTS = [(2100, -2200), (1700, -1500), (1200, -1050), (980, -450), (720, 120), (520, 420)]
OUT_BACK_PTS = _points(_walk(OUT_WAYPOINTS, 12.0, wiggle=3.0) + _walk(OUT_WAYPOINTS[::-1], 18.0, offset=6.0, wiggle=2.0)[1:])
OUT_BACK_STATS = _stats(OUT_BACK_PTS)
OUT_BACK_GPX = gf.gpx(gf.trk([OUT_BACK_PTS], 'Synthetic ridge ride'))

# a two-day tour (tests/test_render_contract.py): day 1 climbs from the loop's trailhead to the summit shoulder; day 2
# starts 1.2 km away on the far side of the hill (a transfer between the two) and walks back towards the south-west
TOUR_DAY_PTS = [_points(_walk([(-1400, -1300), (-1000, -700), (-500, -100), (0, 350), (280, 480)], 15.0, wiggle=4.0)),
                _points(_walk([(1300, -200), (1250, -900), (600, -1450), (-300, -1650)], 15.0, wiggle=4.0))]
TOUR_DAY_GPX = [gf.gpx(gf.trk([pts], 'Synthetic tour day %d' % (i + 1))) for i, pts in enumerate(TOUR_DAY_PTS)]

# a three-day journal walking north along the west side: day 1 starts inside the box of the trips above, day 2 goes on
# from where day 1 ended, day 3 leaves the area northwards
JOURNAL_DAY_PTS = [_points(_walk(w, 25.0, wiggle=5.0)) for w in
                   ([(-1300, -1900), (-1600, -1000), (-1500, 0)], [(-1500, 0), (-1200, 1200), (-900, 2400)],
                    [(-900, 2400), (-600, 4000), (-300, 5500)])]
JOURNAL_DAY_GPX = [gf.gpx(gf.trk([pts], 'Synthetic journal day %d' % (i + 1))) for i, pts in enumerate(JOURNAL_DAY_PTS)]
