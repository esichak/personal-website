# Developing the site

Static site, Python 3 standard library only. No npm, no pip.

```
content/trips/<slug>/index.md     one trip: YAML-ish front matter + Markdown write-up
content/trips/<slug>/track.gpx    full recorded track (single-day trips and planned routes)
content/trips/<slug>/days/NN.md   multi-day / series days (front matter + write-up) with NN.gpx beside them
content/trips/<slug>/photos/      web copies: NN.webp (1600 px) + NN.sm.webp (800 px); no EXIF/GPS
content/home.json                 the home page's featured trips, in order (tools/sitegen/curation.py validates it)
rendered/trips/<slug>/            maps (.svg.html overlay + .png hillshade), profiles, tiles, glyphs, meta.json
rendered/site/                    region + ski-panel overview maps, meta.json
tools/add_trip.py                 new trip from a FIT/GPX file or a Strava export (runs render.py)
tools/render.py                   renders rendered/ (needs internet; caches in .cache/, which is not committed)
tools/build.py                    builds _site/ from content/ + rendered/ + assets/ (what the GitHub Action runs)
tools/sitegen/core.py             shared layout + components (header, footer, units, chips, maps, rows, …)
tools/sitegen/curation.py         content/home.json -> site['featured'] (strict: unknown, draft, planned, duplicate slugs fail the build)
tools/sitegen/search.py           the search index: normalize(), entry(t), build_index(site), dumps() -> trips/search.json
tools/sitegen/pages/trips.py      the Trips explorer (trips/) and its index (trips/search.json): every published trip, by year
tools/sitegen/pages/*.py          one module per page type; each has build(site) -> [core.Page]
assets/css/base.css               tokens, type scale, layout, shared components
assets/css/pages/<module>.css     page CSS (bundled after base.css into assets/site.css)
assets/js/base.js (+ pages/*.js)  bundled into assets/site.js
assets/css/pages/trips.css        the explorer: head, browse block, form, chips, year groups, .trx-grid and .trx--list
assets/js/pages/trips.js          the explorer's behaviour: URL state, history, search.json fetch, match / score (node-testable)
tests/                            stdlib unit tests: python3 -m unittest discover -s tests (CI runs them before the build)
docs/CONTENT_GUIDE.md             how to feature trips, choose covers, write card summaries and add search aliases
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
- Links are relative: build hrefs with `core.link(here, target)` where `here` is the page URL (`''`, `ski/`, `trips/`,
  `trips/<slug>/`). Rendered fragments use `@@ROOT@@` which `core.frag` rewrites.
- Maps are static: `core.map_block(t, here, [(name, size)…], asset_dir, ns)` shows exactly one variant per
  breakpoint (`wide` ≥1200, `col` 560–1199 or ≥1200 with `map--nowide`, `desktop` ≥560, `phone` <560).
  Charts: `core.chart_block`. Every inline fragment needs a unique `ns` (ids are namespaced with it).
- Key rows decode symbols only, never values (`core.key_row(['skin','ski','start_end','gps','mile'])`).
- Mono-S meta lines are ALL CAPS with units (`SAT, JAN 17, 2026 · 12.8 MI`).
- Accessibility: landmarks, one h1 per page, headings in order, `aria-current` on the active nav (`page` on the link whose page
  this is, `true` on Trips inside a section or report; the keys are under Trips explorer below); filters are
  `role="radiogroup"` / `role="radio"` with `aria-checked` (base.js gives every radio group one tab stop, arrow / Home /
  End keys and Space / Enter); tab rows sit in `.tabs-x` (base.css + base.js: they scroll sideways, never widen the page);
  visible focus (base.css), alt text from front matter, `role="img"` + aria-label on maps (already in fragments).
- Copy: tracks are "GPS recordings via Strava" — never name a device (some tracks are Strava GPX exports). Map captions
  read `Track: <Mon D, YYYY> · full track, not trimmed · North up` (`core.map_caption`). The menu's Other row names only
  the sub-types that have reports (`core.other_subtypes()`); flat water is `core.is_flat()` (SUP / Kayaking, or under
  30 m of relief — render.py uses the same rule).
- Cards: a trip's photo comes from `t['cover']` (`content.resolve_cover`: the explicit `cover_photo`, else the first landscape
  trip photo, else a day photo; `core.cover_img` / `core.cover_preload` draw it with its focal point) and its text from
  `core.card_summary` (explicit `card_summary` → the write-up's opening → a labelled day excerpt for multi-day trips → a
  neutral facts line for a series). A series never shows one day's excerpt as if it were the whole journal. The home
  card leaves a 'facts' result off (its DATE · PLACE and data lines already say it) and the recent cards
  (`core.trip_card`, `ns='rc'`, no `summary`) show none.
- Home features come only from `site['featured']` (content/home.json), never from dates or the `featured` flag, once
  the file exists; a missing file falls back to the legacy flag/date pick with a warning.
- Lists: `core.trip_row` is the one index row and `core.trip_card` the one card (explorer and Recent outings); a single-day
  row with no excerpt is `.trow--brief` (120px tile in the same
  column, tighter row), and phones show a Mono-S stats line (`.trow-ps`) instead of the stat grid.

- Trips explorer (`trips/`, `tools/sitegen/pages/trips.py`): one page lists every published trip exactly once, grouped by
  year, with a static browse block, a search box and filters; `trips/search.json` beside it is the search index. Planned
  routes are on neither (they stay on `map/` and their activity page until the Tick list exists); drafts are never loaded.
  - One card: `core.trip_card(t, here, sizes, ns='tc', cls='', summary=False)` returns one `<li class="tcard">` carrying the
    filter facets as attributes: `data-slug`, `data-act`, `data-kind` (`trip` | `multi-day` | `series`), `data-region`
    (`content.slugify(region)`, `''` when none), `data-year` (`YYYY` or `''`), `data-writeup` (`1` | `0`), `data-date` (ISO
    or `''`). Media falls back cover → route tile (`.tcard-img--tile`) → activity disc (`.tcard-img--none`); the media link is
    `tabindex="-1" aria-hidden="true"`, so the title link is the card's tab stop, described by the meta line
    `id="<ns>-<slug>-m"` (`ns` must be unique per list on a page). A 'facts' summary is never shown. `.tcard` and the
    `.fchip` filter chip live in base.css (shared with the home page and map/); everything prefixed `.trx-` (head, browse
    block, form, status row and active-filter chips, year groups, `.trx-grid`, `.trx--list`) is in trips.css.
  - The index: `search.build_index(site)` returns one `search.entry(t)` per trip in `site['published']`, newest first:
    `s` slug, `t` title, `p` place + region, `k` the activity label (and the Other sub-type word) + `search_aliases` +
    `map: peaks`, `x` the write-ups (parent plus every day, capped at 4000 normalised characters), `r` the plain write-up
    text (capped at 4000) that the snippet around a hit is cut from. `t`, `p`, `k`, `x` go through `search.normalize`
    (NFKD, the U+0300–036F combining marks dropped, lower-case, each run of non-alphanumerics → one space); trips.js
    `norm()` strips the same block, so the two agree on every input (tests/norm_cases.json checks both). Never in it:
    coordinates, GPX, HTML, photos, party, beta, stats, planned routes, drafts. `search.dumps` writes compact ASCII JSON
    with `<` as `\u003c`; the Page is `index=False` (not in the sitemap).
  - URL state: the query string, in this order with defaults omitted: `q`, `activity` (`all` | `ski` | `climb` | `hike` |
    `mtb` | `other`), `region` (slug), `year`, `format` (`trip` | `multi-day` | `series`), `writeup` (`1`), `sort`
    (`newest` | `oldest` | `relevance`), `view` (`cards` | `list`). Unknown keys are dropped and values the page does not
    offer fall back to the default (`parseState` in trips.js); the `<select>` option values, the chips' `data-filter` and
    the cards' data attributes are the same strings. Typing applies after 150 ms with `replaceState`; every other
    control, a chip's remove button and Clear all use `pushState` (Back steps through filters, never keystrokes);
    `popstate` re-reads the URL; arrow-key steps through a radio group within 600 ms share one entry. The load-time
    write keeps the fragment (`trips/#search` focuses the box after the first render and on a same-page click;
    `trips/#y-2024` still scrolls); later writes drop it. A query switches the sort to relevance and clearing it back to
    newest unless a sort was chosen explicitly (choosing Newest first counts); oldest and relevance move the visible cards
    into the `#trx-sorted-sec` section (its h2 names the order), newest moves them back into their year groups.
  - `search.json` is fetched the first time a non-empty query is applied; while it loads or after it failed the query
    hides nothing and does not count as a filter (the count stays `N REPORTS`), `#trx-msg` (`role="status"`) says so, and
    a changed query retries once. `match` needs every token as a substring of `t p k x`; `score` adds 3 per token in the
    title, 2 in place/region or activity/aliases/peaks, 1 in the body. A card matched only in the body shows a snippet
    around the first hit in place of its excerpt (textContent; a day excerpt's DAY label is hidden meanwhile). Nothing
    from the query or the index reaches innerHTML.
  - Without JavaScript the form stays `hidden` (a `<noscript>` note says so) and the browse block (activities → section
    pages, regions → `map/#region-<slug>` via `core.region_map_href`, or `?region=<slug>` for a region with no map
    anchor such as the PCT, years → `#y-YYYY`) and the year groups still hold every report. `build.py --check` verifies
    those anchors from every page.
  - Nav keys: `core.document(..., active=KEY)`. Main nav: Trips (`trips/`), Map (`map/`), PCT (`core.PCT_SLUG`, only when
    that trip exists), About, then Search (`trips/#search`). `'trips'` → `page` on Trips; an activity key (section, report,
    multi-day, full-screen-map pages) → `true` on Trips; `'map'` / `'about'` → `page` on their link; the PCT page → `page` on
    PCT and nothing on Trips. The phone menu keeps the five activity rows under Reports and lists Trips, Map & archive, PCT,
    About, Search under Site; the footer's Site list starts with Trips.
  - Adding a facet: emit it as a `data-*` attribute in `core.trip_card`; add the control in trips.py (option values = the
    attribute values present, and only those); in trips.js add the key to `DEFAULTS`, `KEYS`, `FACETS`, `allowed`,
    `names`, `sel` and its change listener, `setControls`, the per-card test in `render` and `chipLabel`; extend the
    Python test (option values match the data) and the Node test (`parseState` rejects values outside `allowed`). Adding
    an alias is content only (`search_aliases: [PCT]`); it needs a build, not a render.

## Trip dict (from tools/lib/content.py)
`slug, title, activity (ski|climb|hike|mtb|other), activity_label, cat, subtype, kind (trip|multi-day|series|planned),
date, end_date, start_time, timezone, place, region, party, route_shape, featured, beta[{label,value}],
conditions{}, map{}, body_md, photos[{file, sm, w, h, alt, caption}], days[…], url ('trips/<slug>/'), track,
rendered, stats{distance_km, gain_m, loss_m, high_m, low_m, moving_s, elapsed_s}, season, has_writeup,
cover_photo, cover_focal (x, y), card_summary, cover{photo, source ('explicit'|'parent'|'day'), day, focal}, aliases`.
`aliases`: the optional `search_aliases` front matter (an inline list `[PCT, Pacific Crest]`, or one string) as a list of
stripped, non-empty strings; `[]` when absent; anything else is a `content.ContentError`. Only `search.entry` reads it.
Day: `n, id, label, title, date, start_time, hut, transfer_before, stats, photos, body_md, track`.
`site = {'trips': all (newest first), 'by_slug', 'published' (not planned), 'planned', 'featured' (home.json's picks, in order)}`.

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
anchors on other pages (`map/#region-utah`, `trips/#y-2024` must land on an element with that id).
`python3 -m unittest discover -s tests` runs the unit tests (home.json curation, cover resolution, card summaries, home
cards, the search index, the Trips page, the header's nav state, trip cards; a Node test of trips.js's pure functions runs
when `node` is installed and is skipped otherwise); they build synthetic trips in temp folders, so they never touch
content/ and take a few seconds.
