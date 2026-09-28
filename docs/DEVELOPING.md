# Developing the site

Static site, Python 3 standard library only. No npm, no pip.

```
content/trips/<slug>/index.md     one trip: YAML-ish front matter + Markdown write-up
content/trips/<slug>/track.gpx    full recorded track (single-day trips and planned routes)
content/trips/<slug>/days/NN.md   multi-day / series days (front matter + write-up) with NN.gpx beside them
content/trips/<slug>/photos/      web copies: NN.webp (1600 px) + NN.sm.webp (800 px); no EXIF/GPS
rendered/trips/<slug>/            maps (.svg.html overlay + .png hillshade), profiles, tiles, glyphs, meta.json
rendered/site/                    region + ski-panel overview maps, meta.json
tools/add_trip.py                 new trip from a FIT/GPX file or a Strava export (runs render.py)
tools/render.py                   renders rendered/ (needs internet; caches in .cache/, which is not committed)
tools/build.py                    builds _site/ from content/ + rendered/ + assets/ (what the GitHub Action runs)
tools/sitegen/core.py             shared layout + components (header, footer, units, chips, maps, rows, …)
tools/sitegen/pages/*.py          one module per page type; each has build(site) -> [core.Page]
assets/css/base.css               tokens, type scale, layout, shared components
assets/css/pages/<module>.css     page CSS (bundled after base.css into assets/site.css)
assets/js/base.js (+ pages/*.js)  bundled into assets/site.js
```

## Design: "Datum"
Warm paper `#F2F1EC`, ink `#16171A`, one route red `#D2381A` used only for the GPX line (and 3px active bars).
Archivo (display/UI, wdth 112 for headings) · Source Serif 4 (Eric's words) · Geist Mono (anything measured).
Activity colours: ski `#4A8CCD`, climb `#70355E`, hike `#69883C`, mtb `#845011`, other `#1C7D78` — never the only cue
(always with icon + word). Radii 0 for maps/cards/photos, 2px for chips/buttons. Touch targets ≥ 44px.

Type classes (phone → tablet ≥760 → desktop ≥1200 sizes are built in): `t-d1` (`t-d1--long` for titles > 28 chars),
`t-d2`, `t-h2`, `t-h3`, `t-h4`, `t-dek`, `t-body` (write-ups, max 620px via `.prose`), `t-excerpt`, `t-small`,
`t-label` (caps overline), `t-data-xl`, `t-data-m`, `t-mono-s` (dates/meta; write Mono-S text in CAPS).

Layout: `.wrap` (1248 max, page margins 16/40/48px), `.bleed` (full width up to 1440), `.sec` (section gap
56/72/96px), `.grid12`. Breakpoints: phone < 760, tablet 760–1199, desktop ≥ 1200. Header nav collapses to the
menu button below 1140px.

## Rules
- Facts only from the content files. Never invent stats, grades, conditions, bios or captions. Hide empty fields.
- Eric's write-ups are verbatim (`markdown.to_html(t['body_md'])`).
- Units: every distance/elevation goes through `core.U` / `core.distance` / `core.elev` so the MI|KM toggle works.
  Rendered fragments carry both units too: profile grid lines, y labels and distance ticks, map scale bars and GPS-max
  labels sit in `<g class="u-mi">` / `<g class="u-km">` (or `<tspan>`s), which base.css shows one at a time. Mile discs
  and contour labels stay imperial.
- Links are relative: build hrefs with `core.link(here, target)` where `here` is the page URL (`''`, `ski/`,
  `trips/<slug>/`). Rendered fragments use `@@ROOT@@` which `core.frag` rewrites.
- Maps are static: `core.map_block(t, here, [(name, size)…], asset_dir, ns)` shows exactly one variant per
  breakpoint (`wide` ≥1200, `col` 560–1199 or ≥1200 with `map--nowide`, `desktop` ≥560, `phone` <560).
  Charts: `core.chart_block`. Every inline fragment needs a unique `ns` (ids are namespaced with it).
- Key rows decode symbols only, never values (`core.key_row(['skin','ski','start_end','gps','mile'])`).
- Mono-S meta lines are ALL CAPS with units (`SAT, JAN 17, 2026 · 12.8 MI`).
- Accessibility: landmarks, one h1 per page, headings in order, `aria-current` on the active nav; filters are
  `role="radiogroup"` / `role="radio"` with `aria-checked` (base.js gives every radio group one tab stop, arrow / Home /
  End keys and Space / Enter); tab rows sit in `.tabs-x` (base.css + base.js: they scroll sideways, never widen the page);
  visible focus (base.css), alt text from front matter, `role="img"` + aria-label on maps (already in fragments).
- Copy: tracks are "GPS recordings via Strava" — never name a device (some tracks are Strava GPX exports). Map captions
  read `Track: <Mon D, YYYY> · full track, not trimmed · North up` (`core.map_caption`). The menu's Other row names only
  the sub-types that have reports (`core.other_subtypes()`); flat water is `core.is_flat()` (SUP / Kayaking, or under
  30 m of relief — render.py uses the same rule).
- Lists: `core.trip_row` is the one index row; a single-day row with no excerpt is `.trow--brief` (120px tile in the same
  column, tighter row), and phones show a Mono-S stats line (`.trow-ps`) instead of the stat grid.

## Trip dict (from tools/lib/content.py)
`slug, title, activity (ski|climb|hike|mtb|other), activity_label, cat, subtype, kind (trip|multi-day|series|planned),
date, end_date, start_time, timezone, place, region, party, route_shape, featured, beta[{label,value}],
conditions{}, map{}, body_md, photos[{file, sm, w, h, alt, caption}], days[…], url ('trips/<slug>/'), track,
rendered, stats{distance_km, gain_m, loss_m, high_m, low_m, moving_s, elapsed_s}, season, has_writeup`.
Day: `n, id, label, title, date, start_time, hut, transfer_before, stats, photos, body_md, track`.
`site = {'trips': all (newest first), 'by_slug', 'published' (not planned), 'planned'}`.

Rendered names per trip (see `rendered/trips/<slug>/meta.json`):
- single: `map-wide` 1440×640, `map-col` 718×400, `map-phone` 390×336, `profile-wide|col|phone` (1248/718/358)
  or `speed-wide|col|phone` for flat water, `tile` 200×152, `g112` 112×64, `g64` 64×48. `tile`, `g112` and `g64` are
  served as cached images: build.py writes them to `trips/<slug>/<name>.svg` and `core.tile` / `core.glyph` return an
  `<img>` (series day glyphs and sparklines stay inline).
- multi-day: `overview-wide` 1440×560, `overview-col` 718×440, `overview-phone` 390×260, `day-NN-col` 718×400,
  `day-NN-phone` 390×240, `profile-wide` 1248, `profile-phone` 358, `day-NN-profile-col|phone`, `spark-NN(-cur)`
  96×24, `tile`, `g112`, `g64`.
- series: `overview-tall` 560×860, `overview-phone` 390×600, `days/NNN-g64`, `days/NNN-spark`, `tile`, `g112`, `g64`.
- site (`rendered/site/`): `region-<region-slug>-desktop` 718×620 / `-phone` 390×480 and
  `ski-<region-slug>-desktop` 506×680 / `-phone`; pins link to trips; tracks carry `data-key="<slug>"`
  (`base.js` highlights a track when an element with that `data-key` inside `[data-map-target=<map id>]` is hovered).
  PNGs are copied to `assets/maps/` — pass `site_maps=True, asset_dir='assets/maps/'` to `core.map_block`.

## Checking your work
`python3 tools/build.py --check` builds everything and verifies every internal link, image and anchor, including
anchors on other pages (`map/#region-utah` must land on an element with that id).
