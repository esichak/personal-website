# Developing the site

Static site, Python 3 standard library only. No npm, no pip.

```
content/trips/<slug>/index.md     one trip: YAML-ish front matter + Markdown write-up
content/trips/<slug>/track.gpx    full recorded track (single-day trips) or, for a kind: planned goal, the published planned GPX
content/trips/<slug>/goal.json    a tick-list goal's intent and provenance (tools/lib/goals.py validates; optional: a legacy planned route has none)
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
tools/sitegen/search.py           the search indexes: normalize(), entry(t), build_index(site) -> trips/search.json; day_entry(t, d),
                                  build_day_index(site) -> trips/journal.json (every day of every journal); dumps()
tools/sitegen/pages/trips.py      the Trips explorer (trips/) and its indexes (trips/search.json, trips/journal.json)
tools/sitegen/pages/ticklist.py   the Tick list (tick-list/): every goal as a map-led card, by region, with filters in ticklist.js
tools/lib/goals.py                goal.json defaults, validation, is_active(), site checks (outing report slugs) and report backlinks
tools/lib/gpxroute.py             safe GPX inspection for goals: routes and tracks, segments kept, selection among alternatives, measure()
tools/ticklist.py                 the local goal workflow: add, update, log-outing, review-packet, export (never pushes or deploys)
tools/sitegen/pages/*.py          one module per page type; each has build(site) -> [core.Page]
tools/sitegen/pages/report.py     single-day reports in two layouts (report.narrative: story or compact), goal pages, full-screen map pages
tools/sitegen/pages/series.py     the PCT journal: lead photo, facts-only introduction, highlights, written-entry navigation, month log
assets/css/base.css               tokens, type scale, layout, shared components
assets/css/pages/<module>.css     page CSS (bundled after base.css into assets/site.css)
assets/js/base.js (+ pages/*.js)  bundled into assets/site.js
assets/css/pages/trips.css        the explorer: head, browse block, form, chips, year groups, .trx-grid and .trx--list
assets/js/pages/explore.js        the pure helpers both lists share (norm, parseState, serialize, match, snippet, chipLabel): window.Explore
assets/js/pages/trips.js          the explorer's behaviour: URL state, history, search.json / journal.json fetch, match / score,
                                  journal-day hits (node-testable)
assets/js/pages/ticklist.js       the tick list's behaviour: scope, filters over data attributes, priority / added / name order (node-testable)
assets/js/pages/series.js         the journal's behaviour: month scrollspy, write-ups filter on by default, reveal on hash (node-testable)
docs/TICK_LIST_GUIDE.md           how to save, import, review, publish, update and complete a goal; the research prompt
tests/                            stdlib unit tests: python3 -m unittest discover -s tests (CI runs them before the build)
docs/CONTENT_GUIDE.md             how to feature trips, choose covers and lead photos, write card summaries, add search aliases, list PCT highlights
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
- Copy: tracks are "GPS recordings via Strava" — never name a device (some tracks are Strava GPX exports). Map
  captions go through `core.map_caption` and open with when the track was recorded, from `core.recorded(a, b=None)`:
  `As recorded on <Mon D, YYYY> · full track, not trimmed · North up` on a single-day report (`report.map_caption`)
  and on a section page's featured map (`section.map_caption`, which hides the full-track item under 560), `As
  recorded <date range> · full track, not trimmed · North up` on a multi-day overview (`multiday.overview_caption`),
  `As recorded <date range> · full tracks, not trimmed · North up` on a series (`series.map_caption`). A range that is
  one date reads `As recorded on <date>` there too. A trip without a date gets no `As recorded` item in any of the
  four (`core.recorded` returns `''`): an undated single-day trip, and a multi-day trip or series without dates. A
  goal's caption reads `Planned route, not a recorded track · North up`. The menu's Other row names only the sub-types
  that have reports (`core.other_subtypes()`); flat water is `core.is_flat()` (SUP / Kayaking, or under 30 m of relief
  — render.py uses the same rule).
- Cards: a trip's photo comes from `t['cover']` (`content.resolve_cover`: the explicit `cover_photo`; else the first
  trip photo at least `content.LEAD_MIN_AR` (1.2, so 6:5) wide, else the first at least as wide as tall, else the
  first trip photo; else the same three steps over the day photos, days in order; `core.cover_img` /
  `core.cover_preload` draw it with its focal point) and its text from `core.card_summary` (explicit `card_summary` →
  the write-up's opening → a labelled day excerpt for multi-day trips → a neutral facts line for a series). A series
  never shows one day's excerpt as if it were the whole journal. The home card leaves a 'facts' result off (its DATE ·
  PLACE and data lines already say it) and the recent cards (`core.trip_card`, `ns='rc'`, no `summary`) show none.
- Home features come only from `site['featured']` (content/home.json), never from dates or the `featured` flag, once
  the file exists; a missing file falls back to the legacy flag/date pick with a warning.
- Lists: `core.trip_row` is the one index row and `core.trip_card` the one card (explorer and Recent outings); a single-day
  row with no excerpt is `.trow--brief` (120px tile in the same
  column, tighter row), and phones show a Mono-S stats line (`.trow-ps`) instead of the stat grid.

- Trips explorer (`trips/`, `tools/sitegen/pages/trips.py`): one page lists every published trip exactly once, grouped by
  year, with a static browse block, a search box and filters; `trips/search.json` and `trips/journal.json` beside it are the search indexes. Planned
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
  - Journal days: `search.build_day_index(site)` has one `search.day_entry(t, d)` per day of a published `kind:
    series` trip (a track-only day is in, with `x` and `r` empty, and `t` empty too when it has no title): `s` slug,
    `a` the day's anchor from `series.day_anchor`, `n` label, `j` journal title (shown), `h` day title, `w` date, `t`
    the normalised day title, `p` the day's name, `day <label>` normalised (`day 31`, `day 5 2`), `k` `''`, `x` / `r`
    the write-up, normalised and plain, each capped at `search.DAY_CAP` (6000), and `q` the journal's title and
    aliases, normalised. The journal's title is in no field that finds a day by itself. The list is written to
    `trips/journal.json` only when it is not empty (a site with a journal), and the page then ends with
    `trips.journal_block(site)`, after the results: an empty hidden `<section class="trx-days wrap" id="trx-days"
    data-index="journal.json">` holding the h2 `Journal days` (`#trx-days-h`, `tabindex="-1"` so the status line's
    link can move the focus to it), `#trx-days-n`, the `<ol id="trx-days-l">` and the hidden `#trx-days-more` button.
    trips.js fetches the file with the first query (a failure costs only the day results; a changed query retries
    once) and lists `dayHits(days, toks)` there as DOM-built rows (`dayMeta`, `dayHref` = `<slug>/#<anchor>`, the day
    title or `Day <n>`, `dayText`; textContent only), each filtered as its journal's card is (`facetOk`); with "Has a
    write-up" on, a day is kept only when its own entry has text (`x`).
  - `TRX.dayHits(days, toks)`: `[]` without tokens. The day's name is the tokens of `p`; when the query holds it as a
    consecutive run the day is named and those tokens are done. Every other token must be a substring of the day's `t`
    or `x`, or a whole word of `q` (it then "rides along"). A day is dropped when a token rode along and nothing of
    the day's own was hit: its name, or a `t` / `x` token that is not also a word of `q`. Score: 100 per token of a
    matched name, plus 3 for each other token found in `t` and 1 for each found in `x`; a riding token scores
    nothing. Order: score descending, then index order. So `day 5.2` lists Day 5.2 above Day 5; `pct whitney` and
    `pacific crest trail 2024 day 48` find Day 48; the journal's name alone finds no day unless a day's own text
    holds it; and an untitled track-only day is found by `day <label>` only.
  - The other pure exports of trips.js: `dayMeta(e)` (`<journal> · Day <n> · <date>`, absent parts left out),
    `dayHref(e)`, `dayText(e, toks)` (the words around the hit, else the day's first 24 words; `''` without a
    write-up), `countText(k, total, narrowed)` (`167 REPORTS` / `3 OF 167 REPORTS`), `daysCount(n)` (`''` for 0, `1
    JOURNAL DAY`, `N JOURNAL DAYS`), `daysHead(n)` (`1 DAY`, `N DAYS`: the text of `#trx-days-n`), `DAYS_SHOWN` (5),
    `daysListed(list, all)` (the first five, or a copy of all), `daysMoreText(n, all)` (`''` up to five, `Show all N
    journal days`, `Show fewer journal days`), `dayShown(e, cardOk, writeup)` (the day's journal card passes the
    filters, and with "Has a write-up" on the day's own entry has text), `pending(searching, tripsState, daysState)`
    (true while a search waits for either index), `failText(searching, tripsFailed, daysReady)` (`''` unless searching
    and the trip index failed; then `FAIL_REPORTS` when the journal index is ready, else `FAIL`) and
    `noteText(searching, tripsState, daysState)`, the one note under the search box: `failText` when the trip index
    failed, else `LOADING` while `pending`, else `''`.
  - In the page the status line reads `<count> · <a href="#trx-days">N JOURNAL DAYS</a>` (trips.js builds it and
    rewrites it only when its text changes). While `pending` the line is left alone and `#trx-none` stays hidden, so
    a first search never flashes "No trips match" before the journal days arrive and the live region speaks once;
    the note under the box reads `Loading search…` meanwhile, and the journal request is given up as failed after
    `DAYS_WAIT` (8 s), so the wait is bounded. The link is followed by script (`toDays`: scroll to `#trx-days`, focus
    its heading; `preventDefault`), because a `#trx-days` fragment in the address would not land on a list that is
    filled after loading. The `popstate` handler ignores a navigation that left the query string unchanged (a jump to
    a year heading; it compares `location.search` with what the browser held after the last write), so the automatic
    sort a search puts in the URL is never taken for the visitor's own choice. `Show all` belongs to one query: any
    other query (typing, Enter, Back / Forward) starts from five rows again; the button carries `aria-expanded`.
    `#trx-none` stays hidden while a day
    matches, and an empty `Best match first` head is hidden. The snippet is shown whole (trips.css `.trx-day-x` has no
    clamp). A day never gets a page or a trip entry of its own. Multi-day trips stay whole in `search.json`.
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
    `names`, `sel` and its change listener, `setControls`, the test in `facetOk` (cards and journal days both go
    through it) and `chipLabel`; extend the
    Python test (option values match the data) and the Node test (`parseState` rejects values outside `allowed`). Adding
    an alias is content only (`search_aliases: [PCT]`); it needs a build, not a render.

- Tick list (`tick-list/`, `tools/sitegen/pages/ticklist.py`): every `kind: planned` trip is a goal. `t['goal']` is
  `goals.load_goal()`'s dict (status, priority, archived, tags, why, added_at, target_months, target_year, time_commitment,
  season_notes, difficulty, route_scope, route_source, references, field_evidence, checklist, outings, route, legacy); the
  rules are in `tools/lib/goals.py` and docs/TICK_LIST_GUIDE.md. `site['goals']` = `site['planned']` (pages and assets for
  every goal); `site['active_goals']` (not completed, not archived) drives every '+ N PLANNED ROUTE' counter and the Planned
  blocks (home tiles and region counts, section pages, About, the map page's head, year groups and region lists through
  `archive.listed(site)`, and `render.py`'s region maps); `site['goal_backlinks']` maps a report slug to the goals whose
  outings name it (`report.tick_backlink`, called by the single-day, multi-day and series page builders). Goals never enter
  `site['published']`, the feed, the search index, home features or report counts. `build.site_of(trips)` assembles all of
  this and runs `goals.validate_site`; the tests call it too.
  - A goal's numbers are approximate wherever they are shown: `core.approx(t)` is '≈ ' for a planned trip, and
    `plain_stats`, `row_stats_line`, `stats_cells` (label 'High point', not 'GPS max'), `table_row` and
    `archive.dist_line` use it.
  - `outings` is a history read in order: `goals.OUTCOMES` (attempted, completed) are what `log-outing` records;
    `goals.EVENTS` adds `reopened`, written by `ticklist.py update --reopen`, after which the status may be anything but
    completed until a new completed outing.
  - `core.goal_card(t, here)` is the one goal card (`data-slug / act / region / status / priority / months / gpx / archived /
    added / text`); the route tile is its image, with 'Map not rendered yet' / 'Route not added yet' fallbacks.
  - ticklist.js state keys: `q, activity, region, status, priority, month, gpx (1), scope (active | shortlisted | completed
    | archived | all), sort (priority | added | name), view (cards | list)`; filtering is entirely from the cards' data
    attributes (no index fetch); the history rules are trips.js's. The explorer's control classes (`.trx-*`) are reused.
  - A goal page (`report.goal_page`) says Planned route and Planning notes, never Trip report: an approximate stats strip
    (≈, gain only with full elevation, never a moving time, a note naming the source kind and scope), the rendered map or
    an honest fallback, Why · Planning notes · Season and commitment (only approved field_evidence is published) · Route
    source · References · Still to check (read-only) · Outings. The download is the published source bytes.
  - `render.py` draws a goal from `gpxroute.as_tracks` (one Track per segment, routes included) so gaps stay gaps, on its
    own map and on the region maps (`goal_lines`, `start_of`, `site_tracks`); goals get no elevation chart. A goal without
    a GPX (`no_route(t)`) is skipped, and a render left from an earlier route is removed; region maps draw active goals
    only. tests/test_render_goals.py covers these with the drawing and OpenStreetMap functions stubbed.
- Report pages (`tools/sitegen/pages/report.py`, `kind: trip`): `report.narrative(t)` is True for a single-day trip with
  a write-up (`t['body_md']`) and a cover (`t['cover']`, so any photo). `page()` then builds the story layout
  (`body_cls='p-report p-report--story'`), else the compact one (`p-report`). Both keep `#title #stats #map #profile
  #beta #report #photos` wherever the section exists, and no nav item points at a section the page lacks.
  - Story order: `title_block` (actions `View route` → `#map`, the ink `Download GPX`, `core.copy_link`) →
    `tick_backlink` → `report.hero` (only with a lead photo: `lead_photo` below) → `#stats` → `report.section_nav` →
    `.rep-body` (Beta rail `#beta`, `#report`) → `#map` → `#profile` → `gallery` (`#photos`) → `report.share_row` →
    `core.related_block` → `pager`.
  - Compact order: `title_block` (`Read the report` → `#report` when there is a write-up, `Download GPX`,
    `core.copy_link`) → `tick_backlink` → `#stats` → `#map` → `#profile` → `.rep-body` → `gallery` → `share_row` →
    `related_block` → `pager`.
  - `report.hero(t, here, photos_anchor=False)` → `<figure class="rep-hero wrap" id="hero"><a class="jph jph--l
    rep-hero-a" href="<trip url + cover file>" data-lb-group="photos">` + `core.cover_img(t, here, report.HERO_SIZES,
    eager=True)` + `</a></figure>`, with `data-cap` and a `<figcaption class="t-small">` when the cover photo has a
    caption, and `aria-label="Lead photo, full size"` on the link when it has no alt text. `photos_anchor=True` puts
    `<span class="rep-anchor" id="photos"></span>` first in the figure. `HERO_SIZES = '(min-width: 1200px) 1248px,
    100vw'`. series.py calls the same function.
  - `report.lead_photo(t)` → the cover photo when it can lead a page: its aspect ratio is at least
    `report.LEAD_MIN_AR` (the same object as `content.LEAD_MIN_AR`: 1.2, so 6:5; a photo without recorded dimensions
    counts as a landscape), else None. The lead frame is 4:3 to 2:1, so a portrait, square or near-square cover is not
    put in it; it still fronts the cards and is still the share image. The automatic cover pick prefers a photo that
    clears the same line (`content.resolve_cover`), so a square first photo does not keep a later landscape from
    leading. series.py applies the same rule.
  - `page()` shows the hero when `narrative(t)`, not `lone_portrait(t)` and `lead_photo(t)`. With a hero: `gallery`
    gets `t['photos']` minus the cover file (order kept) and `lead=1`, the head carries `core.cover_preload(t, here,
    HERO_SIZES)` in place of `core.map_preloads`, and `map_block` gets `eager=False`. When no photo remains for the
    grid there is no Photos section; the hero is then built with `photos_anchor=True`, so an old link to `#photos`
    still lands on the photo, and the section row and the bottom bar list no Photos item. Without a hero every photo
    stays where it was, and the map preloads and the eager map stay. That is three cases: a compact page; a story
    whose only photo is a portrait, which keeps `aside_photo` beside the write-up and has no `#photos`; and any other
    story whose cover is narrower than 6:5 (a portrait or square cover among several photos, or a single square or
    near-square photo), which keeps the story order with every photo in `#photos`. The share image is the cover file
    whenever `t['cover']` exists, with or without a hero, on both layouts.
  - `report.gallery(t, here, photos, ns='ph', lead=0)` puts `data-lb-group="photos"` on the `#photos` section; its
    heading counts the photos in the grid. `lead` goes on to `core.photo_rows(..., lead=0)`, where a grid photo
    without alt text is labelled `Photo <k + lead> of <n + lead>, full size`. A story with a lead photo passes
    `lead=1`, so those labels count as the viewer counts (`Photo 2 of 7` for the first grid photo of a seven-photo
    trip) while the heading still reads `6 PHOTOS`.
  - `report.section_nav(has_report, has_gallery, has_beta)` → `<nav class="rep-toc wrap" aria-label="Sections"><ul>`
    of `<li><a class="rep-toc-a" href="#…">`: Report (`#report`), Photos (`#photos`, only with a gallery), Route
    (`#map`), Trip details (`#beta` with beta rows, else `#stats`), always in that fixed order, which is not the
    page's (the gallery follows the map). No link in it is ever marked current. Story layout only: it replaces the
    rail's old Contents list, which no page can show any more (a trip with a write-up and a gallery is always a
    story).
  - `report.share_row(here)` → `<div class="wrap rep-share">` + `core.copy_link(core.SITE_URL + here, 'Copy link to this
    page', cls='alink')`: the copy control for phones, where the title actions are hidden. After the gallery and
    before the related block on both single-day layouts, after `.mul-body` and before the related block on multi-day
    pages, before `goal_pager` on goal pages. Series pages have none: their title actions stay visible on phones.
  - `report.bottom_bar(t, here, gpx_href, has_beta, has_report, has_gallery, chart='', story=False)`: compact unchanged
    (Map · Beta | Profile / Speed | Stats · Report | Photos · GPX). `story=True`: with a gallery Report · Map · Photos ·
    GPX; no gallery but beta rows Beta · Report · Map · GPX; neither Report · Map · Profile / Speed (Stats without a
    chart) · GPX.
  - `report.neighbours(t, site)` → `(newer, older)`: the published reports of `t`'s activity on either side of it in
    `site['published']` order, None at an end, `(None, None)` when `t` is not a published report. `report.pager` draws
    them, and `report.page` and `multiday.page` hand them to `core.related_block` as `skip`.
  - Goal pages (`goal_page`): `core.copy_link` is the last title action and `share_row` sits before `goal_pager`; no
    hero, no section row, no related block. Multi-day pages (`multiday.page`): `core.copy_link` is the last title
    action, then `share_row` and `core.related_block` before the pager, and the share image is
    `multiday.share_image(t)` (the cover; `first_photo(t)` only for a trip without one). Decision for Phase 3:
    multi-day pages keep their map-first layout. They get no lead photo and no section row, whatever their cover, and
    `multiday.page` calls neither `report.hero` nor `report.section_nav`.
- Related reports: `core.related(t, site, k=3, skip=())` → up to k trips from `site['published']`: never `t`, never
  planned, never a report in `skip` (None entries are ignored), each slug once (drafts are never loaded). Candidates
  share `t['region']` (when set; exact string) or `t['activity']`. Order: same region and same activity, then same
  region, then same activity; within a tier the smallest gap in days to `t['date']` first (an undated candidate after
  the dated ones; every candidate counts as undated when `t` has no date), then the newer one, then
  `site['published']` order. `core.related_block(t, here, site, k=3, skip=())` → `''` when empty, else `<section
  class="rep-related wrap sec" aria-labelledby="rel-h">` with the h2 `More like this` (`id="rel-h"`), the rule as
  `core.meta_items` (`SAME REGION, THEN ACTIVITY`, or `SAME ACTIVITY` when `t` has no region; then `NEAREST IN DATE`;
  then `NEWER / OLDER NOT REPEATED` when `skip` holds a report)
  and `<ul class="rep-rel tgrid">` of `core.trip_card(x, here, core.RELATED_SIZES, ns='rel')`. Called by `report.page`
  (both layouts) and `multiday.page`, before the pager, with `skip=report.neighbours(t, site)`: the block leaves out
  the two reports the pager right under it links as Newer / Older, and the rule line says so. Never on
  goal or series pages. `RELATED_SIZES = '(min-width: 1200px) 400px, (min-width: 560px) calc((100vw - 104px) / 2),
  112px'`.
- Copy link: `core.copy_link(url, label='Copy link', cls='btn', of='')` → `<span class="copy"><button type="button"
  class="<cls> copy-btn" data-copy="<url>">` + `icon('link', 18)` + `<span><label></span></button><span
  class="copy-msg t-small" role="status"></span></span>`. With `of` the button ends `<span><label></span><span
  class="sr">, <of></span></button>` (escaped), so each control has its own accessible name on a page that repeats a
  label. `url` is absolute: `core.SITE_URL + here`, plus `'#' + day_anchor(d)` for a series entry. Callers: the last
  title action on single-day, goal, multi-day and series pages (`cls='btn'`); `report.share_row` (`cls='alink'`, 'Copy
  link to this page'); `series.written_nav` (`cls='alink'`, 'Copy link to this entry', `of='Day <label>'`). The status
  element is always rendered, empty until base.js fills it. Never inside `<noscript>`: with scripting off report.css
  hides the control and the share row (`@media (scripting: none) { .copy, .rep-share { display: none; } }`). A
  browser that does not know the `scripting` media feature still shows the button there, and it then does nothing.
- Journal page (`tools/sitegen/pages/series.py`; `body_cls` stays `p-series`; day articles, month sections, ids, GPX
  hrefs and `download` names are unchanged):
  - Page order: `title_block` → `tick_backlink` → `report.hero` (when `t['cover']` and `report.lead_photo(t)`) → strip
    → `intro` → `highlights` → `day_log` → `pager`. With a lead photo the head carries `core.cover_preload(t, here,
    report.HERO_SIZES)` in place of `ov_preloads`; a portrait, square or near-square cover gives no hero, and
    `ov_preloads` stay. The share image is the cover file whenever `t['cover']` exists, lead or not. The hero is alone
    in its viewer group (no other element on the page carries `data-lb-group`), and the cover photo stays in its day's
    `.ser-phs`.
  - Actions: `Read the first written entry` → `#<day_anchor(first_written(t))>` (omitted when there is none), `Browse
    all recordings` → `#days` with `data-ser-all`, then `core.copy_link`. No 'Day by day' action and no 'Download all
    GPX'. series.css keeps the three under the title at every width.
  - `series.first_written(t)` → the first day dict with a write-up, in `t['days']` order, or None.
  - `lede(t)`: the series write-up when `t['body_md']`; else `<p class="ser-lede">` opening with `<title>: <N>
    recorded day(s)[, <core.frange(date, end_date)>][, <place>].` (a journal without dates or without a place leaves
    that part out), then the sentences on how the log is organised (each with a singular form when its count is one).
    Fields and counts only, never a day's prose. `page()` builds the meta description the same way: `<title>: <N>
    recorded days[, <range>], with a GPX track for every day[ and <N> written up].`
  - `series.highlights(t, here)` → `''` when `t['journal_highlights']` is empty; else `<section class="ser-high wrap
    sec" id="highlights" aria-labelledby="high-h">` with the h2 `Highlights` (`id="high-h"`), a count (`N ENTRIES`, `1
    ENTRY`) and `<ol class="ser-high-l">`: per day, in the listed order, `<li><a class="ser-high-a"
    href="#<day_anchor(d)>"><span class="t-label">Day <label></span>[<span class="ser-high-t">name</span>]</a>[<p
    class="t-mono-s">DATE</p>][<p class="t-excerpt">…</p>]</li>`. `name` is the day's title, else its date
    (`core.fdate(date, 'day')`); a day with neither has no `.ser-high-t` span. The date paragraph (the same date in
    caps) is there only for a day with both a title and a date, so an untitled day's date is printed once. The excerpt
    is `markdown.plain(body_md, 160)`, for a written day.
  - `series.written_nav(t, d, here)` → `''` for a track-only day; else `<div class="ser-wnav">` (a div: a nav per
    entry would add one landmark per written day) with `<a class="alink ser-wnav-p">` 'Previous write-up: Day <label>'
    and `<a class="alink ser-wnav-n">` 'Next write-up: Day <label>' for the nearest written days in `t['days']` order
    (each omitted at the ends), then the entry's `core.copy_link` with `of='Day <label>'`, so every entry's button has
    its own accessible name. `day_article` appends it to `.ser-body`.
  - `series.day_anchor(d)` is `content.day_anchor(d['label'])` → `'day-'` + the label with every run of characters
    outside `A-Z a-z 0-9` replaced by `-` and leading and trailing `-` stripped: `31` → `day-31`, `5.2` → `day-5-2`,
    `5 (zero)` → `day-5-zero`. It is the day article's id and the only source of a day fragment (the first-entry
    action, highlights, written-entry navigation, copy links, `search.day_entry`), so the id is safe in an attribute
    and a URL whatever a day file's `day:` holds. `content.load_trip` refuses a `kind: series` trip in which two days
    get the same anchor, one day's anchor equals an id another day's article writes (`<anchor>-n` on its number,
    `<anchor>-t` on its title: `content.DAY_SUB_IDS`), or a label has no letter or digit (`ContentError` naming the day
    file; a file without a `day:` line is told so, since the label is then its position). A day's label is its `day:`
    as text, `0` included, else its position among the day files.
  - The toggle (`#ser-only`, rendered when some but not all days are written) carries `data-default="wu"`; its markup is
    otherwise unchanged.
- base.js additions:
  - Copy: one delegated click handler on `.copy-btn` calls `navigator.clipboard.writeText` with `data-copy` (the page
    URL when the attribute is missing). On success `.copy-msg` says 'Link copied' for 4 s. When the promise rejects,
    or there is no clipboard API, the handler empties `.copy-msg` and appends `<span class="copy-pop"><input
    class="copy-url" type="text" readonly aria-label="Link to copy"></span>` to `.copy` (beside the status element,
    not inside it), shifts it to stay 16 px inside the viewport's edges, and focuses, selects and scrolls the field to
    its start. The field is removed on Escape (focus returns to the button), on a second press of the button, or on a
    press anywhere outside it. The status and the field are out of the flow, so a button at the bottom edge of the
    screen (or just above the phone bottom bar) would open them out of sight: both are brought in with
    `scrollIntoView({ block: 'nearest' })`, which honours `html`'s scroll padding and does nothing when they already
    show.
  - Viewer groups: a photo link inside, or carrying, `data-lb-group` opens the group of every `a.jph` under an element
    with that value plus every `a.jph` carrying it, in document order (hero, then the grid), so `PHOTO k / N` counts each
    photo once. Links without the attribute group as before (`.jrows`, `.mul-photos`, `.ser-phs`, `.rep-aside-ph`).
  - The current-section spy marks the phone bottom bar only (`.bbar` links, `aria-current="location"`); the section
    row (`.rep-toc`) is never marked. A bar link the reader presses is pinned as current while its section stays
    where the jump put it: the click asks for an update, which runs after the jump and records the section's top, and
    the pin is released once that top has moved by more than 8 px (any scroll, by any means) or a `hashchange` (Back /
    Forward) names another fragment.
- series.js: four pure helpers, exported before any DOM access through `module.exports` under Node and as
  `window.SeriesLog`. `hashTarget(hash)` → `{kind: 'day' | 'month' | 'other' | null, id}` (`'#day-5-2'` → day,
  `'#month-2024-06'` → month, `'#days'` → other, `''` → `{kind: null, id: ''}`; the hash is URI-decoded).
  `startFiltered(defaultOn, hash, hiddenIds)` → `defaultOn` and the hash's id is not in `hiddenIds`.
  `revealId(filtered, hash, hiddenIds)` → the id a link must reveal: `''` unless `filtered` and the hash names an id
  in `hiddenIds`. `landAfterLoad(filtered, hash, navType)` → true only when `filtered`, the hash names a day or a
  month, and `navType` (`PerformanceNavigationTiming.type`) is `''`, undefined or `'navigate'`; false for `'reload'`,
  `'back_forward'` and `'prerender'`. In the page:
  - The hidden ids are those of `.ser-day:not(.has-wu)` and `.ser-month:not(.has-wu)`.
  - On load the box is set to `startFiltered(default, location.hash, hidden)`, where `default` is the reader's stored
    choice when there is one, else `data-default === 'wu'`. So a first load starts filtered unless the hash targets a
    hidden day or month; then the filter stays off, the browser's own fragment scroll lands and nothing is announced.
  - The reader's choice is `sessionStorage['ser-only:' + location.pathname]` (`'1'` | `'0'`), written when the toggle
    changes and on every `[data-ser-all]` click, also when the filter is already off (a link may have revealed the
    days; the choice must still hold after a reload). A reveal through a hash is not stored. Storage errors are
    ignored.
  - When `landAfterLoad` is true for the load, the target is scrolled into view again (on the next frame and on
    `load`): the browser may have jumped to it before the filter shortened the page. The `load` landing is skipped
    when the page has scrolled since the first one, so a reader who has started reading on a slow connection is not
    pulled back. `landAfterLoad` is false on a reload and on Back / Forward, so the page does not scroll a second time
    there: the browser restores the reader's own position.
  - On `hashchange`, `revealId` decides: for a hidden id while the filter is on, the box is unchecked, `#ser-live`
    says 'Showing all N days' and the target is scrolled into view. A click on a same-page link whose `href` equals
    the current `location.hash` runs the same reveal, because no `hashchange` fires for it.
  - A click on `[data-ser-all]` unchecks the box and stores the choice, and announces 'Showing all N days' when the
    filter was on. Without JavaScript every day shows.
- CSS: report.css gains the story block (`.rep-hero` / `.rep-hero-a`: 3 / 2, 4 / 3 and edge to edge under 560, 2 / 1
  from 1200, `object-fit: cover` under the `object-position` `core.cover_img` sets; `.rep-toc` / `.rep-toc-a`: a
  wrapping row of 48 px links, not sticky, with no current-section marker (no `.rep-toc-a[aria-current]` rule and no
  `::before` square); `.p-report--story` spacing), `.rep-rel` (one column, two from 560, three from 1200),
  `.rep-share`, `.rep-anchor`, and the copy control: `.copy` is `position: relative`, and `.copy-msg` (the status) and
  `.copy-pop` (the fallback field, `.copy-url`) hang under the button with `position: absolute; top: 100%`, out of the
  flow, so no row moves. Inside `.rep-share` the status is in flow beside the button (`position: static`). `@media
  (scripting: none)` hides `.copy` and `.rep-share`. `.rep-toc` is `display: none` under 760 (the bottom bar is the
  phone's section nav) and `.rep-share` is `display: none` from 760 (the title actions hold the control there); both
  stay in the markup at every width. series.css gains `.ser-high-l` / `.ser-high-a` / `.ser-high-t` (one column, two
  from 760, three from 1200), `.ser-wnav`, the strip's margin under the hero, the title actions under the title from
  1000 too (`body.p-series .rep-head` stays a column) and flexible title buttons under 760 (`.copy` flexes like the
  buttons). trips.css gains `.trx-days` and the `.trx-day*` rows (`.trx-day-x`, the snippet, is not clamped) and the
  link in `.trx-count`. The compact layout's rules are untouched, apart from the removed `.rail-toc`.
- Icons: `link` in `tools/lib/icons.py` (`PATHS`), drawn by `core.copy_link`.

## Trip dict (from tools/lib/content.py)
`slug, title, activity (ski|climb|hike|mtb|other), activity_label, cat, subtype, kind (trip|multi-day|series|planned),
date, end_date, start_time, timezone, place, region, party, route_shape, featured, beta[{label,value}],
conditions{}, map{}, body_md, photos[{file, sm, w, h, alt, caption}], days[…], url ('trips/<slug>/'), track,
rendered, stats{distance_km, gain_m, loss_m, high_m, low_m, moving_s, elapsed_s}, season, has_writeup,
cover_photo, cover_focal (x, y), card_summary, cover{photo, source ('explicit'|'parent'|'day'), day, focal}, aliases,
journal_highlights, goal (None unless kind is planned)`.
`cover`: `content.resolve_cover(t)`, None when the trip has no photo at all. `content.LEAD_MIN_AR` (1.2) is the 6:5 line
the automatic pick prefers and `report.lead_photo` requires (`report.LEAD_MIN_AR` is the same object).
`aliases`: the optional `search_aliases` front matter (an inline list `[PCT, Pacific Crest]`, or one string) as a list of
stripped, non-empty strings; `[]` when absent; anything else is a `content.ContentError`. Only `search.entry` reads it.
`journal_highlights`: the optional `journal_highlights: [001, 059]` front matter (day ids as in the `days/NNN.md` file
names; a number is zero-padded to the width of those names) as the matching day dicts in the listed order; `[]` when
absent or empty, and the key is always present. A value that is not a list, a non-empty list on a trip that is not
`kind: series` (or on a series with no day files), an id with no day file, or a repeat is a `content.ContentError`
naming `content/trips/<slug>/index.md`. Only `series.highlights` reads it.
Day: `n, id, label, title, date, start_time, hut, transfer_before, stats, photos, body_md, track`.
`site = {'trips': all (newest first), 'by_slug', 'published' (not planned), 'planned', 'goals' (= planned), 'active_goals',
'goal_backlinks', 'featured' (home.json's picks, in order)}`.

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
cards, the search indexes, the Trips page, the header's nav state, trip cards, goal sidecars, the GPX inspector, the tick-list
CLI and page, the renderer's handling of goals, the report layouts, related reports and the copy-link control, the journal
page and `journal_highlights`; Node tests of trips.js's, ticklist.js's and series.js's pure functions run when `node` is
installed and are skipped otherwise); they build synthetic trips in temp folders, so they never touch content/ and take
a few seconds. The Phase 3 files: `tests/test_report_page.py` (layout selection, id order, section links, hero, gallery,
captions, actions, share row, bottom bar), `tests/test_related.py` (`core.related`, `related_block`, `copy_link`),
`tests/test_series_page.py` (highlights validation, the introduction, actions, written-entry navigation, hero, toggle,
day anchors, write-ups verbatim, unchanged anchors and GPX names), `tests/test_journal_days.py` (day labels, the
anchor checks, `core.recorded`, a journal of one day), `tests/test_series_js.py` with `tests/series_js_harness.js`
(series.js's pure helpers, the hooks it looks up on a generated journal page, and the whole script run against a
stand-in for the browser, which starts about thirty short Node processes), the automatic cover pick in
`tests/test_cover.py`, and the journal-day cases in `tests/test_search.py`, `tests/test_trips_page.py` and
`tests/trips_js_harness.js`. Same-page anchors the new
blocks link to (`#day-5-2`, `#days`, `#map`) are resolved by `build.py --check` like the others; journal-day links on
`trips/` are built in the browser, so the check does not see them.
