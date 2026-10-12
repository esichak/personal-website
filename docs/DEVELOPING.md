# Developing the site

Static site, Python 3 standard library only. No npm, no pip.

```
content/trips/<slug>/index.md     one trip: YAML-ish front matter + Markdown write-up
content/trips/<slug>/track.gpx    full recorded track (single-day trips) or, for a kind: planned goal, the published planned GPX
content/trips/<slug>/goal.json    a tick-list goal's intent and provenance (tools/lib/goals.py validates; optional: a legacy planned route has none)
content/trips/<slug>/days/NN.md   multi-day / series days (front matter + write-up) with NN.gpx beside them
content/trips/<slug>/photos/      web copies: NN.webp (1600 px) + NN.sm.webp (800 px) + NN.th.webp (card size, 320 px short edge); no EXIF/GPS
content/home.json                 the home page's featured trips, in order (tools/sitegen/curation.py validates it)
rendered/trips/<slug>/            maps (.svg.html overlay, .webp hillshade, .base.svg contours / water / roads), profiles, tiles, glyphs, meta.json
rendered/site/                    region + ski-panel overview maps, meta.json
tools/add_trip.py                 new trip from a FIT/GPX file or a Strava export (runs render.py unless --no-render)
tools/render.py                   renders rendered/ (needs internet; caches in .cache/, which is not committed)
tools/build.py                    checks content/, then builds _site/ from content/ + rendered/ + assets/ (what the GitHub Action runs);
                                  --check then checks the built site
tools/validate.py                 the content checks without a build: one line per finding, then a summary; --site DIR adds the site checks
tools/lib/checks.py               the content rules: run() -> findings (error | warning | note) for every broken file in one pass
tools/sitegen/sitecheck.py        the built-site rules behind build.py --check: links, anchors, ids, head metadata, sitemap, feed, search
                                  indexes, published GPX bytes
tools/lib/photos.py               photo copies without EXIF/GPS: web_copies() (full, .sm, .th), thumb_size(), thumb_copy()
tools/thumbs.py                   makes the missing card-size (.th) copies of cover photos (needs cwebp); only adds files beside the photos
tools/privacy_audit.py            the author's offline, read-only report on the published tracks and photos; never run by the build or CI
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
tools/sitegen/pages/region.py     the region pages (regions/<slug>/): one per region with a region map and a published report filed under
                                  it; map/'s panel and table (archive.py draws both) for the trips filed under the region, under a head
                                  of counts, years and places
assets/css/base.css               tokens, type scale, layout, shared components
assets/css/pages/<module>.css     page CSS (bundled after base.css into assets/site.css)
assets/js/base.js (+ pages/*.js)  bundled into assets/site.js
assets/css/pages/trips.css        the explorer: head, browse block, form, chips, year groups, .trx-grid and .trx--list
assets/js/pages/explore.js        the pure helpers of the two lists (norm, tokens, parseState, serialize, match, score, snippet, chipLabel, historyStep): window.Explore
assets/js/pages/trips.js          the explorer's behaviour: URL state, history, search.json / journal.json fetch, match / score,
                                  journal-day hits (node-testable)
assets/js/pages/ticklist.js       the tick list's behaviour: scope, filters over data attributes, priority / added / name order (node-testable)
assets/js/pages/series.js         the journal's behaviour: month scrollspy, write-ups filter on by default, reveal on hash (node-testable)
assets/css/pages/region.css       the region pages' own rules (head, Featured grid, the links into trips/); archive.css draws the rest
assets/js/pages/archive.js        map/'s region tabs, "Show all" and the table's activity filter; the last two also run on a region page
docs/TICK_LIST_GUIDE.md           how to save, import, review, publish, update and complete a goal; the research prompt
tests/                            stdlib unit tests: python3 -m unittest discover -s tests (CI runs them before the build)
docs/CONTENT_GUIDE.md             how to feature trips, choose covers and lead photos, write card summaries, add search aliases, list PCT highlights;
                                  what a region page shows and when it changes (section 11)
docs/PRIVACY_NOTES.md             what the site and its public repository disclose, as counts only, and the decisions that are the author's
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
- Dates: a trip's `date` is the day of the trip and is never shown or marked up as the day its report was published, and
  no publication or modification time is made up, because a date the content does not state would be an invented fact.
  `published_at` / `updated_at` are optional lines of index.md (Trip dict below), written out exactly as typed and
  absent from the page when the lines are absent; the day of the build appears nowhere but the footer's © year. One
  legacy exception stands, and tests/test_metadata.py pins it: `build.feed` writes each item's `<pubDate>` from the
  trip's `date` at 12:00 UTC (no `<pubDate>` for an undated trip) and reads neither field.
- Structured data: the only JSON-LD on the site is the one `BlogPosting` block that `core.document(report=t)` writes
  from `core.blog_posting`, and only when `core.written_report(t)`, because marking up a bare track as an article, or
  adding a rating, a publisher logo or a date the content lacks, would tell a search engine something the page does
  not say.
- Units: every distance/elevation goes through `core.U` / `core.distance` / `core.elev` so the MI|KM toggle works.
  Rendered fragments carry both units too: profile grid lines, y labels and distance ticks, map scale bars and GPS-max
  labels sit in `<g class="u-mi">` / `<g class="u-km">` (or `<tspan>`s), which base.css shows one at a time. Mile discs
  and contour labels stay imperial.
- Links are relative: build hrefs with `core.link(here, target)` where `here` is the page URL (`''`, `ski/`, `trips/`,
  `trips/<slug>/`, `regions/<slug>/`). Rendered fragments use `@@ROOT@@` which `core.frag` rewrites.
- Maps are static: `core.map_block(t, here, [(name, size)…], asset_dir, ns)` shows exactly one variant per
  breakpoint (`wide` ≥1200, `col` 560–1199 or ≥1200 with `map--nowide`, `desktop` ≥560, `phone` <560).
  Charts: `core.chart_block`. Every inline fragment needs a unique `ns` (ids are namespaced with it).
- Key rows decode symbols only, never values (`core.key_row(['skin','ski','start_end','gps','mile'])`).
- Mono-S meta lines are ALL CAPS with units (`SAT, JAN 17, 2026 · 12.8 MI`).
- Accessibility: landmarks, one h1 per page, headings in order, `aria-current` on the active nav (`page` on the link whose page
  this is, `true` on Trips inside a section or report and on Tick list inside a goal page; the keys are under Trips
  explorer below); filters are `role="radiogroup"` / `role="radio"` with `aria-checked` (base.js gives every radio group
  one tab stop, arrow / Home / End keys and Space / Enter); tab rows sit in `.tabs-x` (base.css + base.js: they scroll
  sideways, never widen the page); visible focus (base.css), alt text from front matter, `role="img"` + aria-label on
  maps (already in fragments). Phase 4 added the rules below; tests/test_a11y_static.py checks them statically, in the
  sources and in a generated fixture site.
  - Targets: the Design rule is 44 px to press, and Phase 4 brought these up to it. Only the filter chips grew as
    boxes (`.fchip`, with `min-width: 44px` for the short `All` radio, which moves the chips after it by about 6 px on
    a phone). Everything else got a hit area that is out of the flow and changes no box, because a real 44 px box
    moved the layout each time it was tried:
    - the browse links on trips/ (`.trx-bgroup a`: activities, regions, years) and the home page's `ALSO` links
      (`.hom-also a`) are 44 px high as before, and `a::before { inset: 0 min(0px, (100% - 44px) / 2); }` widens a
      link under 44 px by the same amount on each side, to exactly 44; a wider link gets nothing;
    - the two buttons of the view switch are 42 px inside the 44 px `.trx-view` frame, and the segments of the section
      pages' filter band are 42 px (`.sec-seg-a`: ski seasons, Other sub-types, years): `::before { inset: -1px 0; }`
      takes in the frame's line above and below. `All` in the band is under 38 px wide with a phone's padding, so its
      area also reaches left to 44 px (`.sec-seg-a:first-child::before`), never right;
    - the footer's brand link (`.f-brand a.brand-n::before`) is an in-flow block 44 px high whose margins cancel its
      height (`margin: -12px 0 -32px`): 12 px up into the footer's padding, 8 px down into the gap under the name. It
      is not a positioned box on purpose: `position: relative` on that link changed how the name was drawn at 1x;
    - the breadcrumb links: `.crumbs a::before { inset: -21px -4px -7px; }` gives the 16 px line a hit area 44 px
      high (46 from 760 px, where the line is 18 px).

    The crumb's inset is not the same above and below, on purpose. On a report the chip link sits 16 px
    under the crumbs and reaches 9 px up for its own hit area (`a.chip--title::before`), and where two areas overlap
    the later link takes the press. So the crumb's area goes 21 px up, into the 24 px or more of padding above it, and
    only 7 px down. The 4 px each side is half the 8 px gap between two crumbs, so their areas only touch. A region
    page widens its short `Map` crumb to 44 px (Region pages, Styles, below). A card's title link keeps its text
    height: the photo or tile link beside it opens the same page.
  - Without JavaScript the header shows only what works: `@media (scripting: none)` in base.css hides the menu button,
    the units switches (the header's, the menu's and the About page's) and the Search link with the block that holds it
    (`.menu-btn`, `.site-h .units`, `.units.abo-units`, `.nav .nav-search`, `.nav-sep`, `.nav-sep + .nav-l`) and shows
    the primary links (`.nav`) at every width. Where the links do not all fit beside the name they wrap onto a second
    row (`.nav-l` gets `flex-wrap: wrap`, `.site-h-in` gets `height: auto` with `min-height: var(--header-h)`, and
    `.site-h .brand` gets `flex: none`, so the name stays on one line and the links give way), so nothing scrolls
    sideways. A second block, `@media (scripting: none) and (max-width: 479.98px)`, takes the header out of its sticky
    position on a phone (`.site-h { position: static; }`) and sets `--header-h` to `0px`, so the scroll padding and the
    `top` of the day and month bars reserve no room for it; `.site-h-in` gets `min-height: 56px` and `padding-block:
    6px` there, which keeps the focus ring of a link in the first or last row whole. The two-part selectors are needed:
    `.nav a` and the later `.units` and `.nav-l` rules would win over a bare class. On the About page the sentence
    about the `MI | KM` switch is hidden with the switch (`.abo-units-how`, written by `about.units_block` and hidden
    in about.css; tests/test_about_units.py), and the sentence before it, which is true either way, stays. A browser
    that does not know the `scripting` media feature shows the header as it is with JavaScript.
  - A second sticky bar needs its own scroll margin, because `html`'s `scroll-padding-top` clears the header only. Under
    the journal's month bar `.ser-log :is(a, button, input, summary)` has `scroll-margin-top: calc(var(--ser-nav-h) +
    8px)`, and under the multi-day day bar `.mul-body :is(a, button, input, summary)` has `calc(var(--dnav-h) + 8px)`,
    so a control reached with the keyboard is not left under the bar; the bars' own links are set back to 0. On a
    viewport under 480 px high the day bar is not sticky (`@media (max-height: 480px) { .mul-dnav { position: static;
    } }`); the journal's month bar is unchanged there.
  - Map cluster markers (`.mk-cluster`) are `aria-hidden` pointer targets without a name and must never become Tab
    stops: base.js gives them hover and click listeners but no `focusin` / `focusout` listener (its comment records that
    Chrome makes an SVG `<g>` with a focus listener a Tab stop), and nothing gives them a `tabindex`. Pins are links and
    keep their focus listeners.
  - The copy-link fallback field (`.copy-pop`) does not stay open behind the reader: it closes on Escape from anywhere
    on the page, when focus moves from its `.copy` control to something else, on a second press of the button and on a
    press elsewhere. Escape pressed in the field puts the focus back on the button (base.js additions below).
  - A section page's filter band is emitted as `<nav class="sec-seg" aria-label="…" data-filter-nav="…">` of plain links
    (without JavaScript they jump to the lists). section.js replaces each by a `<div>` with the same attributes and
    children and sets `role="radiogroup"` on that, because the role may not sit on a `<nav>` element; a link of the band
    that had the keyboard's focus gets it back in its new place. No generated `<nav>` carries a role.
  - Forced colours: the `@media (forced-colors: active)` block in base.css keeps a visible cue on every current state,
    and Phase 4 added two rules for that mode. In that block, `.site-h .units button:not([aria-checked="true"]) {
    border-block-color: Canvas; }`: the 6 px transparent borders that make each button of the header's and the menu's
    units switch 44 px high are drawn in a system colour in that mode, as bars above and below the unselected button,
    and `Canvas` is the colour of what they lie on (the About page's switch has 1 px borders that lie on its frame's
    own lines, and is left alone). In archive.css, `.arc-legend .disc { forced-color-adjust: none; }` keeps the Map
    legend's discs in their own colours: they are the key to the track colours on the maps, which that mode leaves
    alone.
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
  row with no excerpt is `.trow--brief` (120px tile in the same column, tighter row), and phones show a Mono-S stats
  line (`.trow-ps`) instead of the stat grid. `core.trip_tags` writes `Multi-day · 1 day` for a trip with one day file
  and `Multi-day · N days` otherwise.
- No file, no control: a page offers, links to or mentions a download, a map or a route only when the file behind it
  is built, so nothing leads to a file that is not there. `core.has_track(t)` is the test (the trip's own `track.gpx`,
  or any day's). A single-day report without `t['track']` has no `Download GPX` and no `View route` title action, no
  `#map` section, no Route item in `report.section_nav`, no Map and no GPX item in `report.bottom_bar`, and no
  `trips/<slug>/map/` page. When it has no stats to show either, it has no `#stats` strip, no Trip details item unless
  it has beta rows and no Stats item in the bar (`has_stats`, under Report pages below). A trip's renders go with its
  track: without one `core.render_meta(t)` returns no maps and no charts and `core._drawing`, behind `core.glyph` and
  `core.tile`, returns `''`, so the page has no profile or speed section, no key and no map preload and no card, row or
  pager draws the route, and `build.copy_trip_assets` publishes neither `tile.svg`, `g112.svg` and `g64.svg` nor the
  `map/` renders, whatever `rendered/trips/<slug>/` still holds. render.py agrees: `render.no_track(t)` is a report with
  no track of its own and none on any day, and for one `render_trip` draws nothing, removes a render folder left from
  when the report had a track (it prints `removed render of <slug> (the report has no track now)`) and returns False;
  `render_site` keeps the report out of the region maps and in `all_regions`, and `--charts` passes it by
  (tests/test_render_goals.py, `ReportWithoutTrackTests`, with the drawing functions stubbed: no test runs the
  renderer itself). The shared maps under `rendered/site/` are another matter: only render.py redraws them, so they
  keep such a trip's line until it has run again, and the validator warns (Content checks below). Further,
  `core.summary` leaves out its closing `with map and GPX` fact and `core.stats_note` its two sentences about the
  recording; `section.pick_featured` never picks such a report, so a section page can be without a featured block, and
  an Other sub-type segment then links to `#reports`, not to a `#featured` the page lacks; a section page's
  description ends `with the full GPX track and map` only when every report it lists has a track; and
  `multiday.has_gpx(t)` (some day has a track) gates `Download all GPX`, the bar's GPX item and the combined file
  build.py writes. Goal pages and journal day rows follow the same rule. One part stays whatever the files hold: a
  multi-day or journal page keeps its map section, so with no day track at all it draws an empty map and offers no
  downloads, and the validator warns (`none of the N days has a GPX (days/NN.gpx): the page shows an empty map and
  offers no downloads`). No report lacks a track today (the validator would warn), so tests/test_report_page.py,
  tests/test_track_rules.py and tests/test_build_site.py hold the rule with fixtures.
- Image sizes: a page module that draws a photo across a phone's width ends the `sizes` it passes with `core.PHONE_FULL`
  (`(min-width: 560px) 100vw, 55vw`; the phone part alone is `core.PHONE_SLOT`) and never writes that part by hand,
  because a 3x phone told the true width takes the 1600 px file where the 800 px copy already gives it about two device
  pixels per CSS pixel. `core.phone_sizes(sizes, p)` then decides photo by photo: a landscape photo between 6:5 and 8:5
  keeps the string, and a portrait, a square, a panorama or a photo without a recorded size gets `100vw` in place of
  `PHONE_FULL`, because the 800 px copy is too small for those shapes (a 1200 x 1600 portrait's is 600 px wide).
  `core.photo`, `core.cover_img` and `core.cover_preload` all pass their `sizes` through it, so the image and its
  preload get the same string. Details are under Photos below.
- Controls that only work with JavaScript ship `hidden`, and one that sits above content is shown by `core.reveal(id)`,
  an inline script placed right after the element, not by the deferred bundle, so that it is in place at first paint
  and nothing under it moves when site.js arrives. Today that is `form#search` on trips/ and tick-list/ (their scripts
  still set `form.hidden = false`, which by then changes nothing); map/'s tab row, filter and `Show all N` buttons
  (`.arc-tabs`, `.arc-filt`, `.arc-all-btn`) are still shown by archive.js (a region page has no tab row, and the
  other two where its region calls for them), and the journal's write-ups toggle (`.ser-only`) by series.js.
- iCloud conflict copies under `rendered/` and `assets/` are never part of the site, because nothing the site is made
  from has such a name and CI's checkout has none, so a local build must not differ from the published one. The name is
  one that ends in a space and a number, before the extension when there is one (`meta 3.json`, `map-wide 4.webp`,
  `trips 2.js`, a folder `<slug> 2`). `sitecheck.conflict_copy(name)` is the rule: `build.conflict_copy(path)` applies
  it to every file copied out of `rendered/`, to the files directly in `assets/` and to the page stylesheets and scripts
  that go into the two bundles (a copy of a page script would run twice), and every site check treats such a file as
  absent. `.gitignore` ignores them under `rendered/` (files and folders) and under `assets/` (files), for a number of
  one to three digits. Under `content/` neither the build nor `.gitignore` leaves a copy out; the validator names it
  instead (`checks._check_copies` looks in each trip folder and its `days/`; docs/CONTENT_GUIDE.md, section 5, tells the
  author what to do):
  - A copy of a day file (`days/02 2.md` or `days/02 2.gpx`) is an error and stops the build, because the loader would
    read `02 2.md` as one more day: `looks like an iCloud conflict copy (the name ends in a space and a number): it
    would be published as one more day; delete it`.
  - Any other copy in a trip folder or its `days/` (`index 2.md`, `track 2.gpx`) is a warning: `looks like an iCloud
    conflict copy (the name ends in a space and a number): nothing reads it, but git add of the folder would stage it;
    delete it`.
  - A stray file in a trip's `photos/` folder (`01 2.webp`) is copied into the build all the same and gets the warning
    for any undeclared photo: `not declared under photos: in index.md or a days/NN.md, and not the .sm or .th copy of a
    declared photo; the build publishes it all the same`.
  - A copy of a trip folder (`<slug> 2/`) stops the build with the folder-name error: `the folder name '<slug> 2' cannot
    be a page address: …`.
  - A copy beside the trip folders, such as `content/home 2.json`, is read by nothing and reported by nothing.
- Privacy audit: `tools/privacy_audit.py` is the author's own report, run by hand: it opens files for reading and
  prints, writes no file, fetches nothing, and by default prints counts that name no trip and no place. The default
  report also gives no figure about one track or about one or two places: no earliest or latest start, the spread of
  start times only to the quarter hour, hours joined until none holds one or two tracks, and `fewer than 3` for a
  count of places below that (`privacy_audit.FEW`); `--list` prints the exact figures, to a terminal only. It counts
  what the build publishes, so every file in a trip's `photos/` folder is read whatever its name. `--site DIR` also
  reads a built folder: the GPX copies against their sources, the images, and the text files, in which it looks for
  the first or the last point of any track written out as numbers (`written_positions`: both numbers in one file, three
  or more decimals, rounded or cut short, in either order) and counts look-alike pairs of long decimals apart.
  docs/PRIVACY_NOTES.md repeats what the default report prints. Nothing that
  names a trip, a place or a position, and nothing else from its output beyond the counts already in
  docs/PRIVACY_NOTES.md, goes into a tracked file, a commit message, an issue, a pull request or a CI log, because the
  repository is public and such a list would itself be the disclosure. For the same reason no tool imports or runs it
  and the CI workflow does not mention it (tests/test_privacy_audit.py keeps both true).

- Trips explorer (`trips/`, `tools/sitegen/pages/trips.py`): one page lists every published trip exactly once, grouped by
  year, with a static browse block, a search box and filters; `trips/search.json` and `trips/journal.json` beside it are
  the search indexes. Planned routes are on neither the page nor the indexes: they are tick-list goals, on `tick-list/`,
  `map/` and their activity page; drafts are never loaded.
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
    the cards' data attributes are the same strings. The load-time write keeps the fragment (`trips/#search` focuses
    the box after the first render and on a same-page click; `trips/#y-2024` still scrolls); later writes drop it,
    except the rewrite of an entry that Back or Forward lands on (Sort, below), which keeps the fragment that entry
    had.
  - History: Back steps through deliberate changes, never keystrokes. `Explore.historyStep(kind, entry, now, next,
    recent)` → `{push, restore}`, in explore.js and shared with the tick list (trips.js also exports it as
    `TRX.historyStep`), decides each write. Typing (`'type'`, applied after 150 ms) rewrites the current entry with
    `replaceState`. A filter, the sort menu, the view switch, a chip's remove button and Clear all (`'pick'`) add an
    entry with `pushState`. Enter in the search box (`'submit'`) adds an entry whenever the view differs from the one
    the entry stood for, also when the typing pause has already written the words into the address; the entry is then
    first put back to the view it stood for (`restore`), so Back from a submitted search shows the list from before
    the search and not a second copy of its result. Enter again on the same search adds nothing. A change within
    600 ms of the last new entry rewrites that entry (`recent`: arrow keys through a radio group make one entry). The
    page keeps two addresses for this: `entryUrl`, what the current entry stood for when the visitor last settled on
    it, and `nowUrl`, what it carries at this moment. Both are built by `address()` and never read back from
    `location`, which spells an apostrophe `%27`. `popstate` re-reads the URL, except when only the fragment changed
    (a year link, and Back from one), and `hashchange` settles the entry on the view on screen.
  - Sort: a query switches the sort to relevance unless a sort was chosen explicitly (choosing Newest first counts).
    Without search words Best match does not stay (`sortForSearch`, which asks `TRX.clearedSort(sort, userSort)` →
    `[sort, still chosen]`): emptying the box by hand, Clear all and removing the search chip go back to newest unless
    the visitor chose Oldest first, which stays. An address with `sort=relevance` and no search is rewritten without
    the sort, on load and when Back or Forward lands on it. The one way to that state is picking Best match in the
    menu while the box holds no search words: the entry it makes says `sort=relevance`, and so does every entry a
    filter or the view switch adds after it, while the list stays newest first (the renderer orders by relevance only
    with a query). Each such entry is rewritten when Back or Forward lands on it from an entry with another query
    string (after a jump to a year heading and back, the handler does not read the address); typing words and removing
    them, or Clear all, also puts the sort back to newest. Oldest and relevance move the visible cards into the
    `#trx-sorted-sec` section (its h2 names the order), newest moves them back into their year groups.
  - `search.json` is fetched the first time a non-empty query is applied; while it loads or after it failed the query
    hides nothing and does not count as a filter (the count stays `N REPORTS`) and `#trx-msg` (`role="status"`) says so.
    A failed index is asked for again once the search box has been cleared or changed, also when the same words are
    then typed again, and never on a later render with the query it failed on (a filter, the view switch):
    `stillFailed` and `mayLoad`, among the other pure exports below. `match` needs every token as a substring of `t p k
    x`; `score` adds 3 per token in the title, 2 in place/region or activity/aliases/peaks, 1 in the body. A card
    matched only in the body shows a snippet around the first hit in place of its excerpt (textContent; a day excerpt's
    DAY label is hidden meanwhile). Nothing from the query or the index reaches innerHTML.
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
    trips.js fetches the file with the first query (a failure costs only the day results, and the file is asked for
    again by the rule of `search.json`) and lists `dayHits(days, toks)` there as DOM-built rows (`dayMeta`, `dayHref` =
    `<slug>/#<anchor>`, the day title or `Day <n>`, `dayText`; textContent only), each filtered as its journal's card
    is (`facetOk`); with "Has a write-up" on, a day is kept only when its own entry has text (`x`).
  - `TRX.dayHits(days, toks)`: `[]` without tokens. The day's name is the tokens of `p`; when the query holds it as a
    consecutive run the day is named and those tokens are done. Every other token must be a substring of the day's `t`
    or `x`, or a whole word of `q` (it then "rides along"). A day is dropped when a token rode along and nothing of
    the day's own was hit: its name, or a `t` / `x` token that is not also a word of `q`. Score: 100 per token of a
    matched name, plus 3 for each other token found in `t` and 1 for each found in `x`; a riding token scores
    nothing. Order: score descending, then index order. So `day 5.2` lists Day 5.2 above Day 5; `pct whitney` and
    `pacific crest trail 2024 day 48` find Day 48; the journal's name alone finds no day unless a day's own text
    holds it; and an untitled track-only day is found by `day <label>` only.
  - The other pure exports of trips.js: `adoptForm` and `ownSort` (with the form, two items down),
    `stillFailed(failedFor, q)` (the query a failed index request is remembered for: `failedFor` while the box still
    holds it, `null` once the box has been cleared or changed, so the same words typed again ask again),
    `mayLoad(indexState, failedFor, q)` (whether a search for `q` fetches an index now: `q` has a token and the index is
    `idle`, or it `failed` on another query; never while a request is out and never once the index is here), `facetOk(d,
    st)` (a card's data attributes `act`, `region`, `year`, `kind` and `writeup` against the filters of the state `st`;
    the search text is matched separately), `dayMeta(e)` (`<journal> · Day <n> · <date>`, absent parts left out),
    `dayHref(e)`, `dayText(e, toks)` (the words around the hit, else the day's first 24 words; `''` without a write-up),
    `countText(k, total, narrowed)` (`167 REPORTS` / `3 OF 167 REPORTS`), `daysCount(n)` (`''` for 0, `1 JOURNAL DAY`,
    `N JOURNAL DAYS`), `daysHead(n)` (`1 DAY`, `N DAYS`: the text of `#trx-days-n`), `DAYS_SHOWN` (5), `daysListed(list,
    all)` (the first five, or a copy of all), `daysMoreText(n, all)` (`''` up to five, `Show all N journal days`, `Show
    fewer journal days`), `dayShown(e, cardOk, writeup)` (the day's journal card passes the filters, and with "Has a
    write-up" on the day's own entry has text), `pending(searching, tripsState, daysState)` (true while a search waits
    for either index), `failText(searching, tripsFailed, daysReady)` (`''` unless searching and the trip index failed;
    then `FAIL_REPORTS` when the journal index is ready, else `FAIL`) and `noteText(searching, tripsState, daysState)`,
    the one note under the search box: `failText` when the trip index failed, else `LOADING` while `pending`, else `''`.
  - In the page the status line reads `<count> · <a href="#trx-days">N JOURNAL DAYS</a>` (trips.js builds it and
    rewrites it only when its text changes). While `pending` the line is left alone and `#trx-none` stays hidden, so
    a first search never flashes "No trips match" before the journal days arrive and the live region speaks once;
    the note under the box reads `Loading search…` meanwhile, and the journal request is given up as failed after
    `DAYS_WAIT` (8 s), so the wait is bounded. The link is followed by script (`toDays`: scroll to `#trx-days`, focus
    its heading; `preventDefault`), because a `#trx-days` fragment in the address would not land on a list that is
    filled after loading. The `popstate` handler does not re-read the address after a navigation that left the query
    string unchanged (a jump to a year heading, and Back from one; it compares `location.search` with what the
    browser held after the last write or the last Back or Forward onto another view): it only settles the entry on
    the view on screen, as `hashchange` does, so the automatic sort a search puts in the URL is never taken for the
    visitor's own choice. `Show all` belongs to one query: any
    other query (typing, Enter, Back / Forward) starts from five rows again; the button carries `aria-expanded`.
    `#trx-none` stays hidden while a day matches, and an empty `Best match first` head is hidden. The snippet is shown
    whole (trips.css `.trx-day-x` has no clamp). A day never gets a page or a trip entry of its own. Multi-day trips
    stay whole in `search.json`.
  - The form ships `hidden` and `core.reveal('search')`, right after `</form>`, shows it (rule above), so a visitor may
    have used it before trips.js arrives. The script therefore starts from `TRX.adoptForm(st, form, traversal)`: `st` is
    the URL's state (`parseState`) and `form` what the controls hold, `{q, region, year, format, sort, writeup}`. A key
    the URL sets keeps the URL's value, so a shared address opens as it was shared. A key the URL leaves at its default
    takes its control's value when that is off the default: a select, the ticked write-up box, the text typed. Text
    taken this way is sorted by relevance unless `TRX.ownSort(st, form, traversal)` says the visitor chose a sort, in
    the address or in the sort menu. `traversal` is true when the page was reached by Back or Forward
    (`PerformanceNavigationTiming.type` is `back_forward`): a browser may then have put the selects and the write-up box
    back itself, to what it remembers, so they are not taken; the text is taken either way. The form is
    `autocomplete="off"` (and so is the search box) so that browsers leave its controls alone: Chrome refills a form
    after the deferred script has set the controls from the address, with the values of the view that was on screen
    when the visitor left the page, which need not be the history entry they return to (seen after a jump back over
    two entries, and whenever the page is loaded again from history). The activity chips and the view switch are not
    read. Without JavaScript the form stays
    `hidden` (a `<noscript>` note says so) and the browse block and the year groups still hold every report: the block's
    activities lead to the section pages, its regions to `regions/<slug>/` when the region has a page
    (`core.region_page_href`, under Region pages below), else to `map/#region-<slug>` (`core.region_map_href`), else to
    `?region=<slug>` (a region with no map anchor, such as the PCT), and its years to `#y-YYYY`. `build.py --check`
    verifies those links and anchors from every page.
  - Nav keys: `core.document(..., active=KEY)`. Main nav (`core.main_nav()`): Trips (`trips/`), Tick list (`tick-list/`),
    Map (`map/`), PCT (`core.PCT_SLUG`, only when that trip exists), About, then Search (`trips/#search`). `'trips'` gives
    `page` on Trips; an activity key (section, report, multi-day, full-screen-map pages) gives `true` on Trips;
    `'ticklist'` gives `page` on Tick list and `'goal'` (a goal page) gives `true` there; `'map'` / `'about'` give `page`
    on their link, and `'map'` on a page that is not `map/` itself (a region page) gives `true` on Map; the PCT page
    gives `page` on PCT and nothing on Trips. The phone menu keeps the five activity rows under Reports and lists
    Trips, Tick list, Map & archive, PCT, About, Search under Site; the footer's Site list is Trips, Tick list, Map &
    archive, About, RSS.
  - Adding a facet: emit it as a `data-*` attribute in `core.trip_card`; add the control in trips.py (option values = the
    attribute values present, and only those); in trips.js add the key to `DEFAULTS`, `KEYS`, `FACETS`, `allowed`,
    `names`, `sel` and its change listener, `setControls`, the test in `facetOk` (cards and journal days both go
    through it) and `chipLabel`; extend the Python test (option values match the data) and the Node tests (`parseState`
    rejects values outside `allowed`; the harness's `facetOk` cases; the list of filters tests/test_trips_js.py switches
    off one at a time). Adding an alias is content only (`search_aliases: [PCT]`); it needs a build, not a render.

- Tick list (`tick-list/`, `tools/sitegen/pages/ticklist.py`): every `kind: planned` trip is a goal. `t['goal']` is
  `goals.load_goal()`'s dict (status, priority, archived, tags, why, added_at, target_months, target_year, time_commitment,
  season_notes, difficulty, route_scope, route_source, references, field_evidence, checklist, outings, route, legacy); the
  rules are in `tools/lib/goals.py` and docs/TICK_LIST_GUIDE.md. `site['goals']` = `site['planned']` (pages and assets for
  every goal); `site['active_goals']` (not completed, not archived) drives every '+ N PLANNED ROUTE' counter and the Planned
  blocks (home tiles and region counts, section pages, About, the map page's head, year groups and region lists through
  `core.listed_trips(site)`, which `archive.listed(site)` wraps and `core.region_pages` reads for the region pages,
  and `render.py`'s region maps); `site['goal_backlinks']` maps a report slug to the goals whose
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
    attributes (no index fetch); the history rules are trips.js's (`Explore.historyStep`, with the page's own
    `entryUrl` / `nowUrl`, `address()` and `write(kind, keepHash, settle)`), with two differences: there is no sort
    rule to go with a search, and `popstate` re-reads the address also when only the fragment changed (the skip
    link), which puts the box back to the address's words. The explorer's control classes (`.trx-*`) are reused.
    `TKL.goalShown(d, st, toks)` is the one predicate a card is shown by: the scope, then every filter, then every
    search token in the card's `data-text`. The form is revealed as on trips/ (`core.reveal('search')`) and is
    `autocomplete="off"` for the same reason, and the script
    starts from `TKL.adoptForm(st, form, traversal)` by the rules of trips.js: `form` is `{q, region, status, priority,
    month, sort}`, a key the URL leaves at its default takes its control's value, and after Back or Forward only the
    text is taken. Text taken this way changes no sort: the tick list has no relevance order.
  - A goal page (`report.goal_page`) says Planned route and Planning notes, never Trip report: an approximate stats strip
    (≈, gain only with full elevation, never a moving time, a note naming the source kind and scope), the rendered map or
    an honest fallback, Why · Planning notes · Season and commitment (only approved field_evidence is published) · Route
    source · References · Still to check (read-only) · Outings. The download is the published source bytes.
  - `render.py` draws a goal from `gpxroute.as_tracks` (one Track per segment, routes included) so gaps stay gaps, on its
    own map and on the region maps (`goal_lines`, `start_of`, `site_tracks`); goals get no elevation chart. A goal without
    a GPX (`no_route(t)`) is skipped, and a render left from an earlier route is removed; region maps draw active goals
    only. tests/test_render_goals.py covers these with the drawing and OpenStreetMap functions stubbed.
  - `ticklist.py add` names `"rendered/trips/<slug>"` in its closing `Next:` line only when that folder holds a
    meta.json after the run. When it published a track and no map was drawn, it first prints `  no map was drawn
    (render.py leaves drafts out): once "draft: true" is removed, run python3 tools/render.py <slug> and add
    "rendered/trips/<slug>" as well`: render.py loads no draft, and a new goal is one.
- Report pages (`tools/sitegen/pages/report.py`, `kind: trip`): `report.narrative(t)` is True for a single-day trip with
  a write-up (`t['body_md']`) and a cover (`t['cover']`, so any photo). `page()` then builds the story layout
  (`body_cls='p-report p-report--story'`), else the compact one (`p-report`). Both keep `#title #stats #map #profile
  #beta #report #photos` wherever the section exists, and no nav item points at a section the page lacks.
  - Story order: `title_block` (its actions are `View route`, a link to `#map`, and the ink `Download GPX`, both only
    when the trip has a track, then `core.copy_link`), then `tick_backlink`, `report.hero` (only with a lead photo:
    `lead_photo` below), `#stats`, `report.section_nav`, `.rep-body` (Beta rail `#beta`, `#report`), `#map` (only with a
    track), `#profile`, `gallery` (`#photos`), `report.published_line`, `report.share_row`, `core.related_block` and
    `pager`.
  - Compact order: `title_block` (`Read the report`, a link to `#report`, when there is a write-up, `Download GPX` when
    the trip has a track, `core.copy_link`), then `tick_backlink`, `#stats`, `#map` (only with a track), `#profile`,
    `.rep-body`, `gallery`, `published_line`, `share_row`, `related_block` and `pager`.
  - `#stats`: `report.page` builds the strip section when `has_stats = bool(cells) or has_map`, where `cells` is
    `core.strip_cells(t)`. So a report with a track always has it, as before, and a report without a track has it only
    when it has a stats value to show. Without the strip the page has no `id="stats"`, `section_nav` and `bottom_bar`
    are passed `has_stats=False`, and the Beta block keeps its `Track` row (`report.beta_list(t, noted=has_stats)`; with
    a strip that row is left out of the block because the strip's footnote prints it).
  - `report.hero(t, here, photos_anchor=False)` → `<figure class="rep-hero wrap" id="hero"><a class="jph jph--l
    rep-hero-a" href="<trip url + cover file>" data-lb-group="photos">` + `core.cover_img(t, here, report.HERO_SIZES,
    eager=True)` + `</a></figure>`, with `data-cap` and a `<figcaption class="t-small">` when the cover photo has a
    caption, and `aria-label="Lead photo, full size"` on the link when it has no alt text. `photos_anchor=True` puts
    `<span class="rep-anchor" id="photos"></span>` first in the figure. `HERO_SIZES` is `'(min-width: 1200px) 1248px,
    ' + core.PHONE_FULL`, that is `(min-width: 1200px) 1248px, (min-width: 560px) 100vw, 55vw`; a lead photo wider than
    8:5 is drawn with `(min-width: 1200px) 1248px, 100vw` (`core.phone_sizes`, under Photos below). series.py calls the
    same function.
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
    whenever `t['cover']` exists, with or without a hero, on both layouts (`core.share_photo(t)`).
  - `report.gallery(t, here, photos, ns='ph', lead=0)` puts `data-lb-group="photos"` on the `#photos` section; its
    heading counts the photos in the grid. `lead` goes on to `core.photo_rows(..., lead=0)`, where a grid photo
    without alt text is labelled `Photo <k + lead> of <n + lead>, full size`. A story with a lead photo passes
    `lead=1`, so those labels count as the viewer counts (`Photo 2 of 7` for the first grid photo of a seven-photo
    trip) while the heading still reads `6 PHOTOS`.
  - `report.section_nav(has_report, has_gallery, has_beta, has_map=True, has_stats=True)` returns `<nav class="rep-toc
    wrap" aria-label="Sections"><ul>` of `<li><a class="rep-toc-a" href="#…">`: Report (`#report`), Photos (`#photos`,
    only with a gallery), Route (`#map`, only with `has_map`: a report without a track has no map section), Trip details
    (`#beta` with beta rows, else `#stats`; left out when the page has neither beta rows nor a stats strip), always in
    that fixed order, which is not the page's (the gallery follows the map). No link in it is ever marked current. Story
    layout only: it replaces the rail's old Contents list, which no page can show any more (a trip with a write-up and a
    gallery is always a story).
  - `report.share_row(here)` → `<div class="wrap rep-share">` + `core.copy_link(core.SITE_URL + here, 'Copy link to this
    page', cls='alink')`: the copy control for phones, where the title actions are hidden. After the gallery and
    before the related block on both single-day layouts, after `.mul-body` and before the related block on multi-day
    pages, before `goal_pager` on goal pages. Series pages have none: their title actions stay visible on phones.
  - `report.published_line(t)` returns `''` unless index.md states `published_at`; else `<p class="wrap rep-pub
    t-mono-s">Published <time datetime="<as written>">Oct 3, 2026</time></p>`, with ` · Updated <time …>…</time>` before
    `</p>` when `updated_at` is set. The visible date is `core.fdate(…, 'short')` of the value's first ten characters.
    It is the visible, labelled date the page's metadata must agree with. It sits before `share_row` on single-day pages
    (both layouts) and multi-day pages and before the pager on the journal; a goal page has none (`content` refuses the
    two fields on a planned route).
  - `report.bottom_bar(t, here, gpx_href, has_beta, has_report, has_gallery, chart='', story=False, has_map=True,
    has_stats=True)`: compact unchanged (Map · Beta | Profile / Speed | Stats · Report | Photos · GPX). `story=True`:
    with a gallery Report · Map · Photos · GPX; no gallery but beta rows Beta · Report · Map · GPX; neither Report · Map
    · Profile / Speed (Stats without a chart) · GPX. A report without a track passes `gpx_href=''` and `has_map=False`
    and gets neither the GPX nor the Map item, and `has_stats=False` (the page has no strip) leaves the Stats item out
    as well; `--n` counts the items shown, and the bar is `''` when fewer than two would be left.
  - `report.neighbours(t, site)` → `(newer, older)`: the published reports of `t`'s activity on either side of it in
    `site['published']` order, None at an end, `(None, None)` when `t` is not a published report. `report.pager` draws
    them, and `report.page` and `multiday.page` hand them to `core.related_block` as `skip`.
  - Goal pages (`goal_page`): `core.copy_link` is the last title action and `share_row` sits before `goal_pager`; no
    hero, no section row, no related block. Multi-day pages (`multiday.page`): `Download all GPX` is a title action
    only when `multiday.has_gpx(t)`, `core.copy_link` is the last title action, then `published_line`, `share_row` and
    `core.related_block` before the pager, and the share image is `multiday.share_image(t)`, which returns
    `core.share_photo(t)` (the cover's dict, or None). Decision for Phase 3: multi-day pages keep their map-first
    layout. They get no lead photo and no section row, whatever their cover, and `multiday.page` calls neither
    `report.hero` nor `report.section_nav`.
- Related reports: `core.related(t, site, k=3, skip=())` → up to k trips from `site['published']`: never `t`, never
  planned, never a report in `skip` (None entries are ignored), each slug once (drafts are never loaded). Candidates
  share `t['region']` (when set; exact string) or `t['activity']`. Order: same region and same activity, then same
  region, then same activity; within a tier the smallest gap in days to `t['date']` first (an undated candidate after
  the dated ones; every candidate counts as undated when `t` has no date), then the newer one, then
  `site['published']` order. `core.related_block(t, here, site, k=3, skip=())` → `''` when empty, else `<section
  class="rep-related wrap sec" aria-labelledby="rel-h">` with the h2 `More like this` (`id="rel-h"`), the rule as
  `core.meta_items` (`SAME REGION, THEN ACTIVITY`, or `SAME ACTIVITY` when `t` has no region; then `NEAREST IN DATE`;
  then `NEWER / OLDER NOT REPEATED` when `skip` holds a report) and `<ul class="rep-rel tgrid">` of `core.trip_card(x,
  here, core.RELATED_SIZES, ns='rel')`. Called by `report.page` (both layouts) and `multiday.page`, before the pager,
  with `skip=report.neighbours(t, site)`: the block leaves out the two reports the pager right under it links as Newer /
  Older, and the rule line says so. Never on goal or series pages. `RELATED_SIZES = '(min-width: 1200px) 400px,
  (min-width: 560px) calc((100vw - 104px) / 2), 112px'`.
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
  - Page order: `title_block`, then `tick_backlink`, `report.hero` (when `t['cover']` and `report.lead_photo(t)`), the
    strip, `intro`, `highlights`, `day_log`, `report.published_line` and `pager`. With a lead photo the head carries
    `core.cover_preload(t, here, report.HERO_SIZES)` in place of `ov_preloads`; a portrait, square or near-square cover
    gives no hero, and `ov_preloads` stay. The share image is the cover file whenever `t['cover']` exists, lead or not
    (`core.share_photo(t)`), and the page passes `report=t` as the other report pages do. The hero is alone in its
    viewer group (no other element on the page carries `data-lb-group`), and the cover photo stays in its day's
    `.ser-phs`.
  - Actions: `Read the first written entry` → `#<day_anchor(first_written(t))>` (omitted when there is none), `Browse
    all recordings` → `#days` with `data-ser-all`, then `core.copy_link`. No 'Day by day' action and no 'Download all
    GPX'. series.css keeps the three under the title at every width.
  - `series.first_written(t)` → the first day dict with a write-up, in `t['days']` order, or None.
  - `lede(t)`: the series write-up when `t['body_md']`; else `<p class="ser-lede">` opening with `<title>: <N>
    recorded day(s)[, <core.frange(date, end_date)>][, <place>].` (a journal without dates or without a place leaves
    that part out), then the sentences on how the log is organised (each with a singular form when its count is one).
    Fields and counts only, never a day's prose. `page()` builds the meta description the same way: `<title>: <N>
    recorded days`, the date range, then the GPX part and `<N> written up` joined by ` and `; the three are separated
    by commas and each is left out when it has nothing to say. The GPX part reads `with a GPX track for every day` only
    when every day has a track, and `with a GPX track for <N> of them` when some have.
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
    its start. The field is removed on Escape, when focus moves on, on a second press of the button, or on a press
    anywhere outside it. Escape pressed in the field focuses the button first and closes the field after, so the field
    is never removed with the focus in it and the focus never rests on `<body>`; pressed anywhere else, the field just
    closes. Moving on is a `focusout` whose `relatedTarget` is outside the `.copy` control. A `focusout` without a
    `relatedTarget` leaves the field open: that is the window losing focus, the field being taken out, or a press on
    something that takes no focus, and the click listener sees to a press. `closeCopy(keep)` may be called twice, or
    from a listener that runs while it is at work, and then does nothing more: the field gives up the focus before it
    is removed (Chromium sends `focusout` from inside `removeChild`, and a listener that removed the field there made
    that call throw), and a field that has already left the page is not removed again. The status and the field are
    out of the flow, so a button at the bottom edge of the screen (or just above the phone bottom bar) would open them
    out of sight: both are brought in with `scrollIntoView({ block: 'nearest' })`, which honours `html`'s scroll
    padding and does nothing when they already show.
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
  - The hidden ids are those of `.ser-day:not(.has-wu)` and `.ser-month:not(.has-wu)` and of every element with an id
    inside one (a day's number `day-N-n` and title `day-N-t`, a month's heading `month-YYYY-MM-h`), each listed once.
    The inner ids were link targets while the filter started switched off (the public site before Phase 3, which
    made it start on), so an address that names one reveals its day or month.
  - On load the box is set to `startFiltered(default, location.hash, hidden)`, where `default` is the reader's stored
    choice when there is one, else `data-default === 'wu'`. So a first load starts filtered unless the hash names a
    hidden id; then the filter stays off, the browser's own fragment scroll lands and nothing is announced. The box is
    `autocomplete="off"` (series.py): Chrome otherwise refills it after the script when the page is loaded again by
    Back or Forward, without a `change` event, and the list would not follow the box.
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
  link in `.trx-count`. The compact layout's rules are untouched, apart from the removed `.rail-toc`. Phase 4 added
  `.rep-pub` to report.css (the published line: Mono-S caps in `--ink-2`) and `body.p-report:not(:has(.bbar)) .site-f {
  padding-bottom: 0; }` beside the bottom bar's rules (a page without the bar, because `report.bottom_bar` returned
  `''` or the page is a goal that is only an idea, keeps no room for one under the footer; a browser that does not
  know `:has()` keeps the 72 px), an ellipsis for a search placeholder longer than its box to trips.css (`.trx-q`), and
  the rules listed under Accessibility above.
- Icons: `link` in `tools/lib/icons.py` (`PATHS`), drawn by `core.copy_link`.
- Photos: a published photo has up to three files beside each other: the full file (long edge 1600 px), the `.sm` copy
  (800 px) and the `.th` copy (card size: `core.THUMB_EDGE`, 320 px, on the short edge). `content._photos` records `sm`
  and `th` on the photo dict only when the file exists, so a missing copy is never linked.
  - Srcsets: `core.photo` (galleries, featured blocks) lists the `.sm` copy and the full file, and writes them and
    `width` / `height` only when both `w` and `h` are recorded. `core._cover_srcset(t, p, here)`, behind
    `core.cover_img` and `core.cover_preload`, lists the same two for a cover. The `.th` copy is never a candidate of
    an `<img>` or a preload. It is offered to phones only: for a card cover (a `sizes` string that ends with
    `core.CARD_PHONE_SLOT`, 112 px: `trips.TRX_SIZES`, `core.RELATED_SIZES`, `home.RECENT_SIZES`) whose photo has the
    file, `core.cover_img` wraps the image in `<picture class="cover-pic">` with the `<source>` of
    `core._card_source`: `media="(max-width: 559.98px)"` (`core.CARD_PHONE_MEDIA`), the three copies as candidates and
    `sizes="106px"` (`core.CARD_PHONE_SIZES`, `core.THUMB_EDGE // 3`). The slot is 112 px wide and the source
    declares 106 px on purpose: 3 x 106 = 318, so a 3x phone takes the `.th` copy of a portrait or square cover, which
    is 320 px wide. Declared at 112 px, such a phone asks for 336 px, more than that copy has, and the next candidate
    is the 800 px copy (600 px wide for a portrait). A landscape cover's `.th` copy is 427 px wide and is enough
    either way. `core.CARD_PHONE_SLOT` stays `'112px'`: it is the last item of every card `sizes` string and still
    decides which strings get a source. The `<img>` inside is what it was before the copy existed, so from 560 px up
    a card loads what it always did. Reason, seen in a before / after screenshot comparison: with the 427 px copy in
    the `<img>` list a 1x desktop screen took it for the 400 px card slot, about one source pixel per screen pixel,
    and the photos looked softer than with the 800 px copy. `picture.cover-pic` is `display: contents` (base.css), so
    the wrapper has no box and every `.cover-img` rule applies as before; never select `.cover-img` as a direct child.
    A lead image (`eager=True`) and a full-width slot are never wrapped. `core.thumb_width(p)` is
    `round(w * 320 / min(w, h))` (427 for a 1600 x 1200 photo, 320 for a 1200 x 1600 one) and must equal the width
    `photos.thumb_size(w, h)` writes; tests/test_thumbs.py holds the two to each other.
  - `sizes`: `core.PHONE_FULL` ends `report.HERO_SIZES`, home's `LEAD_SIZES`, `SUB_SIZES` and `WIDE_SUB_SIZES`, the
    default of `core.photo`, the three `core.photo_rows` strings (a portrait shown two to a row on a phone keeps
    `50vw`), `report.aside_photo` and `section.featured`. `core.phone_sizes(sizes, p)` returns the string as it is when
    it does not hold `PHONE_FULL`, or when the photo's recorded `w / h` lies within `core.PHONE_SHAPES` (`(1.2, 1.6)`,
    both ends included); otherwise it returns it with `PHONE_FULL` replaced by `100vw`. So below 560 px the slot of a
    landscape photo between 6:5 and 8:5 is declared as 55vw, and a 3x phone up to 484 px wide asks for no more than 800
    px and takes the `.sm` copy, while a portrait, a square, a panorama and a photo without `w` and `h` are declared at
    their real width (`report.aside_photo` only ever draws a portrait, so its string always ends in `100vw` on the
    page). The viewer still opens the full file.
  - `tools/lib/photos.py`: `web_copies` (which `add_trip.py` calls for every imported photo) writes all three files.
    `thumb_size(w, h)` and `thumb_copy(src, dst, w, h, quality=72)` make the `.th` copy with cwebp (`sips` for the JPEG
    fallback) and keep the colour profile and nothing else (no EXIF, no GPS), as the other two copies do.
  - `python3 tools/thumbs.py [SLUG ...] [--all-photos] [--dry-run] [--force]` makes the copies that are missing: each
    trip's cover by default, every declared photo under `--all-photos`, in both cases only a photo with recorded
    dimensions whose path is `photos/<name>` (`in_photos`). It only adds `content/trips/<slug>/photos/<name>.th.webp`
    files, and it needs cwebp. A photo that is not on disk, or that the converter cannot read, is skipped with a line
    (`skipped <path of the copy>: the photo itself is missing`, `skipped <path of the copy>: the photo could not be
    converted`) and counted at the end of the closing line (`wrote 0 card-size copies; 0 already there; 1 skipped
    (photo missing or unreadable)`); the run goes on to the next photo and ends with exit status 0. A build never needs
    the tool (the srcset falls back); the validator names each cover without a copy (`cover photos/NN.webp has no
    card-size copy (.th); run python3 tools/thumbs.py <slug>`). After a trip's
    `cover_photo` changes, run it for that trip and commit the new file. `wanted(t, all_photos=False)`, `th_path(t,
    p)`, `run(trips, all_photos=False, dry_run=False, force=False, say=print)` (returns `(written, existing,
    skipped)`) and `main(argv=None)` are importable; the tests replace `photolib.thumb_copy` and
    `photolib.have_cwebp`, so they need neither cwebp nor sips.
- Share metadata and structured data (`core.document`; tests/test_metadata.py pins the tags, their order and the cases):
  - `core.share_photo(t)` returns `{'path': t['url'] + file, 'w', 'h', 'alt'}` from `t['cover']`, or None for a trip
    without a photo. Every page that shares a trip's photo takes it from here, so the card, the lead photo and the share
    image cannot disagree: single-day pages (both layouts), goal pages, multi-day pages (`multiday.share_image`), the
    journal, the home page (its lead feature), section pages (`section.og_image(ts)`: the first trip with a cover,
    the featured trip first) and region pages (`region.share_image(feat, pub)`: the first Featured pick with a cover,
    else the first report of the region with one).
  - `core.site_share()` returns the share photo of the first trip in `site['featured']` (kept by `core.register_site`),
    or None when nothing is featured. Only the four pages that stand for the whole site pass it outright: About, Map,
    Trips and Tick list. A region page falls back to it when none of its reports has a cover
    (`region.share_image`). A trip page without a photo, a full-screen map page and the 404 page share no image.
  - `core._share_tags(image)` writes, in this order: `og:image` (absolute), `og:image:type` (webp, jpeg, png or gif by
    the extension, else left out), `og:image:width` and `og:image:height` only when both are recorded positive whole
    numbers, `og:image:alt` only when the photo has alt text, `twitter:card` `summary_large_image`, and
    `twitter:image:alt` under the same condition. Without an image the one tag is `twitter:card` `summary`. A plain path
    string still works as `image` and gives `og:image`, its type and the card. Nothing is measured or worded here.
  - `core.document(..., canonical=True, report=None)`: `canonical=False` leaves out the canonical link and `og:url` (the
    404 page, which stands for no URL). `report=t`, passed by single-day, multi-day and journal pages, adds after the
    share tags `article:published_time` / `article:modified_time` when index.md states them, and the `BlogPosting` block
    when `core.written_report(t)`. A goal page passes no `report`.
  - `core.written_report(t)`: a trip that is not planned whose own write-ups (the `body_md` of index.md and of every
    day, as `markdown.plain` text joined with spaces) come to at least `core.STRUCTURED_MIN_CHARS` (100) characters.
  - `core.blog_posting(t, canon, description, image=None)` returns the dict: `@context`, `@type` `BlogPosting`,
    `headline` (the title as written), `url` and `mainEntityOfPage` (the canonical), `description` (the page's meta
    description), `inLanguage` `en`, `author` (`core.AUTHOR_NAME` and `core.AUTHOR_URL`, the About page; never a
    `party:` name), `image` only from the page's own share photo and only with a recorded size, `datePublished` /
    `dateModified` only from `published_at` / `updated_at`. It is serialised with `json.dumps(..., ensure_ascii=False)`
    and every `<` written as `\u003c`, so no title can close the script element.
  - Also new in core.py: `core.has_track(t)` (the trip's own track or any day's: see "No file, no control" above),
    `core.reveal(el_id)` (returns `<script>document.getElementById("<id>").hidden=false</script>`) and
    `core.read_json(path, default=None)` (a JSON file's value with the handle closed, `default` when the file does not
    exist; the page modules read rendered/site/meta.json through it).
- Content checks (`tools/lib/checks.py`; `tools/validate.py` is its command line and build.py runs it first;
  tests/test_checks.py and tests/test_validate_cli.py):
  - `checks.run(trips_dir=None, home_json=None, rendered_dir=None, today=None)` returns every finding about the content,
    sorted by file, then error before warning before note, then text, and never raises on content. A finding is
    `{'level': 'error' | 'warning' | 'note', 'file': <repo-relative path>, 'text': <one line>}`; the text starts with
    the file and `': '`, the form every `ContentError` already had. `checks.survey(...)` returns `(findings, counts)`
    with `counts = {'trips', 'photos', 'gpx'}`; `checks.errors`, `checks.warnings` and `checks.notes` filter;
    `checks.line(f)` is the printed form (`ERROR …`, `WARNING …`, `NOTE …`) and `checks.summary(findings, counts)` the
    closing line.
  - Levels: an error is a broken explicit value, or one the generator cannot read, and stops the build. A warning is
    optional metadata left incomplete, which the pages cope with. A note is an optional field that is simply absent:
    counted, and listed only on request.
  - Per trip folder: read index.md and the day files raw; check the raw values, so a wrong type is named by its file
    and field; only when that found nothing, load the trip as the build does (`content.load_trip`: a `ContentError`
    comes through with its text unchanged, any other exception becomes `could not be read (<ExceptionName>:
    <message>)`, never a traceback); then the warnings and notes on the loaded trip. Then the checks that need every
    trip: content/home.json (`curation`'s own messages), goal outings (`goals.validate_site`'s own messages), write-up
    links, repeated titles and region spellings, and, when there is a `rendered/` folder, two warnings read from
    `rendered/site/meta.json`, whose maps only `tools/render.py` can redraw. `checks._region_findings` names a
    single-day or multi-day report whose region is not in the file's `all_regions`: `region 'X' is not in
    rendered/site/meta.json, so the map page does not list it yet; run python3 tools/render.py --site --force`.
    `checks._site_map_findings` names a trip that one of the file's `maps` still lists under `trips` although it is a
    draft, has no track any more (`core.has_track`) or has no folder under content/trips any more: `the site maps under
    rendered/site/ still draw this trip, which is a draft: its line and title stay on the pages that show those maps
    (the home page, the Map page, an activity page) until python3 tools/render.py has been run and rendered/site/
    committed`. Of the activity pages only the Ski page shows such a map (`section.ski_panel`). Since Phase 5 the
    region pages show the region maps as well; the message, which the author guides quote, does not name them. The
    build passes meanwhile, and so does `--check` for a report that only lost its track. For a draft or a removed
    folder that has a pin of its own on a map the check fails, because the pin still links to `trips/<slug>/`
    (`BROKEN map/index.html -> ../trips/<slug>/`, and for the region's own page `BROKEN regions/<region-slug>/index.html
    -> ../../trips/<slug>/`); a pin merged into a `.mk-cluster` carries no link. Drafts are checked too, because a
    broken draft stops a build as well.
  - Rules on the files of a trip folder that were added after the author guides had been followed literally on scratch
    content (tests/test_checks_more.py, tests/test_frontmatter.py). `checks._check_copies` is under the conflict-copy
    rule above. `checks._check_tracks` gives the error for a GPX file without a point, which ends `(without the file
    there is no map and no download for it)`, and three findings about day files, with `checks._has_trk(path)` as the
    test for a recorded track: on a `kind: multi-day` trip an error on index.md when no day GPX holds a `<trk>` (`none
    of the day GPX files holds a recorded track (<trk>): "Download all GPX" would be an empty file; a day's file is that
    day's recording`) and a warning on one route-only day file among recorded ones (`holds a route and no recorded
    track (<trk>): "Download all GPX" leaves this day out`), and on a multi-day trip or a journal a warning on a
    `track.gpx` left beside day files (`is not used: this trip has day files, and its page, maps and downloads come
    from days/NN.gpx; remove the file`). Neither `_has_trk` nor `gpx_problem` opens a file that iCloud Drive has
    offloaded. `checks._date_warnings` warns about a day dated after the stated `end_date` (`date <d> is after the
    trip's end_date <e> (index.md), so the page's dates end before this day`). `checks._split_file` warns about a key
    written twice (`key '<k>' is written twice in the front matter; only the last one is read`; `_top_keys` lists the
    keys at the left margin). Dates, clock times, durations and numbers are ASCII digits only: `_DATE`, `_CLOCK` and
    `_DURATION` are compiled with `re.ASCII`, as `frontmatter._NUM` is, so a value typed in full-width digits stays the
    text that was typed and gets its field's error.
  - Existing messages are never reworded: the author guides quote them. A new rule names the file, the field and the
    value and says what is accepted. Two messages were reworded in Phase 4 after the guides had quoted them, each
    because its old text sent the author the wrong way, and the guides were changed with them. The region warning
    ended `run python3 tools/render.py --site`: without `--force`, `render.render_site` returns before it rewrites
    `all_regions` when the set of map jobs is unchanged, as it is for a new region with too few reports for a map. The
    site-maps warning named the Map page only, and the same maps are on the home page and the Ski page.
  - A new front-matter key is added to the tuple that lists its file's keys (`INDEX_KEYS`, `DAY_KEYS`, `PHOTO_KEYS`,
    `STATS_KEYS`, `MAP_KEYS`, `HOME_KEYS`), or every file that uses it gets a warning such as `unknown key 'card_sumary'
    (did you mean 'card_summary'?); nothing reads it`.
  - `python3 tools/validate.py [--content DIR] [--site DIR] [--strict] [--json] [-q | -v] [--today YYYY-MM-DD]` only
    reads. It prints the `ERROR` and `WARNING` lines (`-q`: the errors only; `-v`: the notes too), then `content: <E>
    errors, <W> warnings, <N> notes (<T> trips, <P> photos, <G> GPX files)`. `--json` prints every finding, notes
    included, as a JSON list. `--site DIR` also runs `sitecheck.check` on a built folder and prints each problem as an
    `ERROR` line, then `site: N problems`. `--content DIR` names a folder laid out like content/ (trips/ and home.json
    inside; its renders are looked for in a rendered/ folder beside it). Exit status: 0 without an error, 1 for an
    error, a site problem or (under `--strict`) a warning, 2 for a mistake on the command line.
- Built-site checks (`tools/sitegen/sitecheck.py`; `build.check()` wraps it; tests/test_sitecheck.py):
  - `sitecheck.check(out_dir, content_trips_dir=None, site_url=None)` reads a built folder and returns one line per
    problem, in a stable order: page by page (sorted by path) the links, then the same-page anchors, then the duplicate
    ids; then `META` page by page, `SITEMAP`, `FEED`, `INDEX`, and `GPX` when `content_trips_dir` is given. It prints
    and writes nothing. Each rule is also a function of its own (`links`, `anchors`, `duplicate_ids`, `metadata`,
    `sitemap`, `feed`, `indexes`, `gpx`) over an `Output` made by `sitecheck.read(out_dir)` or, for pages held in
    memory, `sitecheck.of({path: html})`.
  - The three lines the link check always printed keep their exact form: `BROKEN <page> -> <ref>` (an href, src or
    srcset that names no file of the build), `BROKEN ANCHOR <page> -> <ref>` (a link to an id the page it lands on
    lacks) and `DUPLICATE IDS <page>: a, b, c`. Two things are stricter than before: an address under `core.SITE_URL`
    is followed like a relative one, and a path is looked up in the build by its exact spelling, so a link that leaves
    the folder, or differs from the file name only in upper and lower case, is broken on every machine as it is on the
    web server. One difference in spelling does not count: names are compared in Unicode NFC (`Output.find`,
    `Output.resolve`), so a file that macOS holds with a decomposed accent matches the composed spelling in a page.
    Only a `srcset` value (an `imagesrcset` too) is split into candidates; an `href` or a `src` is one URL even with a
    space in it (`sitecheck._urls`).
  - `META <page>: …`: exactly one `<title>` and one meta description in the head; exactly one canonical equal to the
    page's own URL and one `og:url` equal to it (the 404 page: neither, and it must be noindex); at most one
    `og:image`, absolute under the site URL, its file in the build; `og:image:width` and `og:image:height` both or
    neither; at most one `application/ld+json` block, valid JSON whose `@type` is `BlogPosting`.
  - `SITEMAP`: sitemap.xml parses and lists every indexable page (not noindex, not 404.html) exactly once, and nothing
    else. `FEED`: feed.xml parses and every item's `<link>` and `<guid>` is the address of a built page. `INDEX`: every
    `s` in trips/search.json and trips/journal.json is a built `trips/<s>/` page, and every journal `a` is an id on it.
  - `GPX`: `trips/<slug>/<slug>.gpx` is `content/trips/<slug>/track.gpx` byte for byte (SHA-256; in a `--link` build
    the download is the source file itself), `trips/<slug>/gpx/<slug>-day-<id>.gpx` is `days/<id>.gpx` byte for byte,
    and a multi-day trip's combined file holds each day's `<trk>` blocks unchanged, in day order, and no other track
    (`holds N <trk> blocks, the day files hold M`). The combined file gets two more lines: `holds no track (no day file
    has a <trk>)` when the day files hold routes and no recorded track (in a build of this checkout the content check
    stops such a trip first, with `none of the day GPX files holds a recorded track (<trk>): …`), and `not well-formed
    XML (…)`, for instance when a track uses a prefix that its day file's `<gpx>` tag does not declare.
  - A folder the build did not write is checked the same way (`validate.py --site DIR` takes any folder), and a
    malformed file in it is a problem line, never an exception or a stalled check (tests/test_sitecheck_hostile.py). A
    head that `html.parser` gives up on is `META <page>: the <head> could not be read as HTML`. A sitemap or a feed
    with a DOCTYPE or an entity declaration is `SITEMAP sitemap.xml: not well-formed XML (DOCTYPE and entity
    declarations are not accepted)` (`FEED feed.xml: …` likewise, and the combined GPX is held to the same rule). JSON
    nested too deeply to parse is `… not valid JSON (nested too deeply)`, in a search index (`INDEX …`) and in a
    structured-data block (`META <page>: application/ld+json is not valid JSON (nested too deeply)`).
- build.py (tests/test_build_cli.py drives `main` with stand-ins; tests/test_build_site.py builds a synthetic site):
  - `build.main(argv=None)` returns the exit status (0 or 1; a usage error is argparse's exit 2) and the file ends with
    `sys.exit(main())`, so tests call it in-process. Order: parse the arguments (a wrong `--only` or an unsafe `--out`
    ends here), `content_errors()`, `build(only=...)`, `check()` under `--check`, the preview server under `--serve`.
  - `--only` takes page module names (the files in `tools/sitegen/pages/`), split on commas and trimmed. An unknown
    name or an empty list is a usage error: `build.py: error: --only takes page modules (home, trips, ticklist, section,
    report, multiday, series, archive, region, about, notfound), got reports`.
  - `build.unsafe_out(path)` returns why `path` must not be the output folder, or None: `it is, or holds, this
    checkout`; `it is inside content/ of this checkout` (likewise `rendered`, `assets`, `tools`, `tests`, `docs`, `.git`
    and `.github`: `build._SOURCE_FOLDERS`); `it is a file`; `it is not empty and is not an earlier build (it has no
    .nojekyll file)`. `main` turns the answer into the usage error `--out DIR: a build empties its output folder first,
    and <why>`. `build()` writes `.nojekyll` (`build.BUILD_MARK`) first, so a build that stopped half-way still counts
    as a build. Only `main` asks: `build.build()` called directly deletes `build.OUT` unasked.
  - `build.content_errors()` runs `checks.run()` before the output folder is touched. With an error it prints every
    `ERROR …` line on stderr and `main` returns 1: nothing is built, and an output folder from an earlier build is left
    as it was. Otherwise it prints up to `build.WARNING_LINES` (10) `WARNING …` lines, then `... N more; python3
    tools/validate.py lists them` when there are more, and the build goes on. A build never prints the notes.
  - `build.check()` is a wrapper: it prints the first `build.CHECK_LINES` (40) lines of `sitecheck.check(OUT,
    content.TRIPS_DIR)`, then `... N more` when there are more, then `link check: OK` or `link check: N problems`, and
    returns the count.
  - `build.strip_css_comments(css)`: the published `assets/site.css` carries no comments, because every page waits for
    that file; the sources under `assets/css/` stay commented. Strings are left alone; a comment, or a run of adjacent
    comments, that sits tightly between two tokens is kept, because removing it could join them; blank lines are
    dropped and the result ends with one newline. Running it on its own output changes nothing. `js_bundle()` is not
    stripped.
  - A multi-day trip's combined `trips/<slug>/<slug>.gpx` is written exactly when a day has a track (`any(d['track']
    for d in t['days'])`, the condition of `multiday.has_gpx`). It holds every `<trk …>…</trk>` block of the day files
    in day order: a `<trk>` tag with attributes counts, and a day file without a track block adds nothing. The root
    `<gpx>` of the combined file repeats every `xmlns:<prefix>` declaration found on the `<gpx …>` start tag of a day
    file that gave a block (sorted by prefix; the first declaration of a prefix wins), so a block that uses a device's
    extension prefix stays well-formed; with no such prefix the root is the fixed one. `build.gpx_root_tag(text)` finds
    that tag: the one before the file's first `<trk`, comments skipped, a `>` inside a quoted value not taken for its
    end. Each day file is read, and the combined file written, with `newline=''`, so a day file with Windows line
    endings keeps them and its blocks are in the combined file byte for byte, which is what the site check compares. In
    a `--link` build the name may already be a symlink to the trip's own `track.gpx`; it is removed first, so the write
    never goes through a link into `content/`.
  - Unchanged, and now pinned by tests: `build.feed` (the 30 newest published reports; see Dates above),
    `build.sitemap` (every page whose `core.Page.index` is not False, except 404.html: the two search indexes and the
    full-screen map pages are `index=False`, and those map pages and the 404 page carry `noindex`) and robots.txt
    (`User-agent: *`, `Allow: /`, `Sitemap: <core.SITE_URL>sitemap.xml`).
- Region pages (`regions/<slug>/`, `tools/sitegen/pages/region.py`, `body_cls='p-region'`; Phase 5): one page for each
  region that has a region map and at least one published report filed under it. It is map/'s panel and table for
  that region under a head of counts, years and places, with a Featured row between them, and it lists what the
  content says: every report and active goal whose `region` is exactly the region's name. Nothing on it is written
  and it has no content file. map/ stays the parent: there is no `regions/` index page.
  - Which regions get one, and what a page lists. The rule is in core, so that every page module can ask it:
    - `core.read_site_meta()` returns `rendered/site/meta.json` as it is on disk at that call, or `{'maps': {},
      'regions': []}` without the file. `core.site_meta()` is that, read once per process and kept, and
      `archive.site_meta()` is `core.read_site_meta()`.
    - `core.listed_trips(site)` is what a region lists and counts: every report, and the tick-list goals in
      `site['active_goals']` (a site dict without that key falls back to `site['planned']`, and without that to every
      planned trip in `site['trips']`).
    - `core.region_groups(site, meta=None)` is the Map page's grouping, moved from `archive.regions` unchanged:
      `[(name, slug, ts)]` for each name in `meta['regions']`, the regions `render.py` has drawn a map for (`meta=None`
      reads `core.site_meta()`). `slug` is `content.slugify(name)`, the slug of `map/#region-<slug>`. `ts` is the
      listed trips that the map's own entry names (`meta['maps']['region-<slug>-desktop']['trips']`) or, when the
      entry names none, the listed trips whose `region` is the name, series left out; newest first, planned routes
      last. A group without a trip is dropped. Order: most published reports first, then the name. map/'s panels
      list these groups. The region pages do not.
    - `core.region_pages(site, meta=None)` decides the region pages and what each lists, from the content and not
      from the groups: `[(name, slug, ts)]` for each name in `meta['regions']` that has a region map
      (`region-<slug>-desktop` or `region-<slug>-phone` under `meta['maps']`), a non-empty slug that no earlier name
      of the list has taken, and at least one published report filed under it. `ts` is every listed trip whose
      `region` is exactly the name: reports of every kind, a journal included, and active goals; newest first,
      planned routes last. Planned routes alone make no page. Order: most published reports first, then the name.
      `meta=None` reads `core.site_meta()`.
    - `region.regions(site, meta=None)` is `core.region_pages(site, meta)`, with `archive.site_meta()` in place of a
      `meta` of None, and `region.url(name)` is `'regions/%s/' % content.slugify(name)`. `archive.regions(site, meta)`
      and `archive.listed(site)` remain, as wrappers with the results they had.
    - What follows from `ts` coming from the content. The meta file decides only whether a name has a page; the
      `region` field decides which trips are on it. A report without a track, a journal filed under the region and a
      report added since the last render (`add_trip.py --no-render`, say) are on the page at the next build, and the
      page counts the reports trips/ counts for the region in its "By region" link (`trips.regions_of` counts by slug,
      so a second spelling with the same slug is in that count and not on the page). A draft or a removed folder is
      not in `site['trips']`, so it leaves at the next build. A trip whose `region` changed leaves the old name's page
      at the next build, although the map still draws it, and is on the new name's page at once when that name has
      one. The map block, and map/'s panel through `region_groups`, go the other way: they show what the map was last
      drawn with until `render.py` has rewritten `rendered/site/`. So a region whose trips were all renamed or respelt
      has no page from the next build on, because no report is filed under the name `meta['regions']` holds, until a
      render has drawn a map under the new name, and nothing redirects `regions/<old-slug>/`. A new spelling with the
      same slug (`content.slugify` folds accents and drops every character that has no ASCII form, lower-cases, drops
      apostrophes, turns every run of characters outside `a-z0-9` into one hyphen and strips hyphens at the ends) gets the same address back at that render; until then its trips
      link to `map/#region-<slug>`, where the panel still stands under the old spelling. docs/CONTENT_GUIDE.md,
      section 11.4, tells the author.
    - A mapped region without a group. `core.region_groups` drops a region none of whose listed trips its map's entry
      names: every trip the map drew is a draft or gone. map/ then has no panel and no `#region-<slug>` for it, and
      `home.also_items` leaves it out (Links from other pages, below), so `build.py --check` passes when nothing is
      filed under the region any more: no page shows its map. Two callers still read the meta alone.
      `core.region_map_href` answers `map/#region-<slug>` for any name whose slug has a `region-<slug>-desktop` map,
      so the page of a goal that is still filed under such a region and is in no group (an active goal the map does
      not draw, because it has no route or is newer than the render, or a completed or archived goal, which
      `core.listed_trips` leaves out) links to an anchor map/ no longer has. `home.where` draws the block of a
      `HOME_REGIONS` name whenever the meta has its map, with "Open the map" to the same anchor. In both cases the
      check reports `BROKEN ANCHOR … -> map/#region-<slug>` until `render.py` has rewritten `rendered/site/`.
    - Two spellings with one slug. Before a render the second spelling is in no list of the meta, and map/ is sound.
      After one it is in `all_regions`, and `archive.other_places` gives its "Not on a region map" entry the id
      `region-<slug>`, which the first spelling's panel has: `DUPLICATE IDS map/index.html: region-<slug>`.
      `section.ski_panel` makes a tab and a panel (`rt-<slug>`, `rp-<slug>`) for every region name its ski trips state
      whose slug has a `ski-<slug>-desktop` map, and inlines the same map fragment under one namespace for each, so
      two spellings among the ski trips give a `DUPLICATE IDS ski/index.html: …` line, with or without a render. The
      line lists the first six double ids in sorted order, and the fragment's own ids (`rm-<slug>-…`) sort before
      `rp-` and `rt-`, so those two are usually not in it. The content check warns about the pair
      (`checks._region_spellings`); the author's fix is one spelling. A build is then enough, except after a render
      that gave each spelling a map: `meta['regions']` then holds both names with one map entry between them,
      `region_groups` makes a group, and map/ a panel, for each from that entry's trips, and the ids stay double until
      the next render.
  - Asking whether a region has a page: `core.register_site(site, meta=None)` clears `core._REGION_PAGES` (name to
    slug) and refills it from `core.region_pages(site, meta)` only when a `meta` is passed. `build.build()` passes
    `core.read_site_meta()`. `core.region_page_href(here, region)` returns `core.link(here, 'regions/<slug>/')` for a
    name in the dict, else None. It is asked by the exact name, as the page lists by it: a second spelling of a
    region is not on the page and keeps its link to map/. A site registered without a meta, as `helpers.make_site`
    does in the tests, has no region page, and `register_site` then reads nothing from `rendered/`: the answer is
    None for every region and every caller links as it did before Phase 5, so a page function called alone in a
    test behaves as before. A test that wants region pages passes a meta of its own. `region.build` and
    `archive.build` read `archive.site_meta()`, the file `build.build()` read just before them.
  - Links from other pages. Each asks `core.region_page_href` first and keeps the link it had when the answer is None:
    - the region crumb of `report.title_block` (single-day, multi-day, journal and goal pages): `regions/<slug>/`, else
      `map/#region-<slug>` (`core.region_map_href`), else no crumb;
    - `report.region_cell(t, here)`, the second cell of `report.goal_pager` (`report.planned_pager` uses it too, and
      nothing calls that function today): a list of zero or one `a.next`. Its label line is the region's name; its
      text is `All <Region> reports`, to the region's page, or `Open the map`, to `map/#region-<slug>`. `[]` for a trip
      without a region, or with one that map/ does not list;
    - `trips.browse`, the "By region" links: `regions/<slug>/`, else `map/#region-<slug>`, else `?region=<slug>`;
    - `home.also_items`, the mapped regions of the `ALSO` row: `regions/<slug>/`, else the region's panel on map/.
      The row names a mapped region only while it has something to link to: a panel on map/ (`core.region_groups(site)`
      lists it) or a page of its own. A mapped region whose reports were all made drafts or removed has neither, so
      map/ has no `#region-<slug>` for it until the next render, and an item for it would be a broken anchor. A
      mapped region that holds only active goals the map draws still has its panel and keeps its item, without a
      count; one whose stale map names no trip of the site but that has reports filed under it has its page, and its
      item links there;
    - `home.where`, the two region map blocks: the name inside `h3.hom-reg-n` is a link to `regions/<slug>/` (plain
      text without a page), and the block's `a.hom-reg-a`, "Open the map", still goes to `map/#region-<slug>`;
    - `archive.region_panel` on map/: one more link, `a.alink.arc-reg-a`, `All <Region> reports` with the arrow-right
      icon, after the rows and the "Show all" button, and no link for a region without a page.
  - Anatomy. `region.build(site)` returns one `core.Page` per region, from `region.page(name, slug, ts, site, meta,
    regs)` (`regs` is `regions(site, meta)`, for the links to the others); `'region'` follows `'archive'` in
    `build.PAGE_MODULES`. With `pub` the trips of `ts` that are not planned and `planned` the others, the body is, in
    this order:
    - `region.head(name, here, pub, planned)`: `<section class="reg-head wrap" aria-labelledby="reg-title">` with the
      breadcrumb `Reports / Map / <Region>` in the section pages' markup (`<nav class="crumbs t-mono-s"
      aria-label="Breadcrumb">`, `<span aria-hidden="true">/</span>` between the items; links to home and `map/`, the
      region as `<span aria-current="page">`), `<h1 id="reg-title" class="t-d1">` holding the escaped name and nothing
      else, and `<p class="reg-stats">`: one `core.meta_items` line with a break slot (`br_after`) between its two
      parts. The first is `core.count_items(pub, planned)` (`86 REPORTS`, `INCL. 8 MULTI-DAY`, `+ 1 PLANNED ROUTE`)
      and `region.years_item(pub)`: the years the reports span, from `date` and `end_date`, as `2022–2026` with an en
      dash or as one year, and no item when no report is dated. The second is `region.place_items(pub)`, the places in
      upper case in the order of `region.place_names(pub)`. That function strips and upper-cases each `place` before
      it counts, so two spellings that read the same in upper case are one place with their reports counted together,
      and it sorts by most reports first, then A to Z on the upper-case form. All of them are shown up to `MAX_PLACES
      + 1` (4), else the first `MAX_PLACES` (3) and `N MORE`; there is no second part when no report states a place. A
      place item is `(esc(PLACE), 'mi-w')`: escaped after upper-casing, so that an ampersand is `&amp;` and never
      `&AMP;`, and without `core.nb`. `.ml > .mi-w` (base.css) lets such an item wrap at its spaces, so a long place
      takes a second line instead of widening the page, and `.reg-stats .mi-w { overflow-wrap: anywhere; }`
      (region.css) breaks a single word that is too long for a line. `N MORE` is a plain `core.nb` item. This line is
      the page's whole introduction: no prose is generated for a region.
    - The map: `<section class="arc-map reg-map wrap" aria-labelledby="reg-map-h">`, a screen-reader `<h2 class="sr"
      id="reg-map-h">Map</h2>` and `archive.region_panel(name, slug, ts, here, meta, True, page=True,
      drawn=region.map_trips(name, site, meta) or None)`. With `page=True` the panel is `<div class="arc-panel"
      id="map">` (not `#region-<slug>`: that id belongs to map/) and has no `h3` naming the region, since the h1 does.
      The map block (`region-<slug>-desktop` / `-phone`, eager, `id="arc-map-<slug>"`), the caption and the legend are
      those of map/. The legend is the key to the map, so `archive.legend` is handed `drawn`, the trips the map draws,
      and not the page's `ts`. `region.map_trips(name, site, meta)` is map/'s group for the region
      (`core.region_groups`). A report without a track, a journal, a goal without a route and a trip newer than the
      last render are in `ts` and not in the group, so they add no activity disc and no "Planned route" symbol to the
      legend. When the group is empty (`drawn=None`: the map's entry names none of the listed trips) the legend is
      made from `ts`; where the map draws every trip of `ts` the two give the same legend. The cluster symbol follows
      the map's entry either way. On map/ (`page=False`) nothing passes `drawn` and the legend is made from the
      panel's own list, which is the group. The side list is map/'s list, for `ts`: `<h3 class="t-label"
      id="arc-in-<slug>">In this region</h3>`, an h3 because the panel head is gone, with the same count line beside
      it (`archive.count_line(ts, 'ml--end')`), then every trip of `ts`, the planned routes too, as an
      `archive.region_row` in `<ol class="arc-rows" id="arc-rows-<slug>" aria-labelledby="arc-in-<slug>"
      data-map-target="arc-map-<slug>">` (labelled by the h3 alone; on map/ the panel's heading is named as well).
      When `ts` has more than `archive.SHOW + 1` (9) trips, the rows from the ninth on carry `arc-more` and map/'s
      button follows the list: `<button type="button" class="alink arc-all-btn" aria-expanded="false"
      aria-controls="arc-rows-<slug>" hidden>`, `Show all N`, N being the published reports of `ts`. So archive.js and
      base.js treat the list as they do on map/ (Script, below). The panel carries no `a.arc-reg-a`: that link, to the
      region's own page, is on map/ only. With `page=False`, the default, the panel is what it was before Phase 5 plus
      that link.
    - `region.featured(slug, here, pub, feat)`: `''` when nothing was picked, else `<section class="reg-feat wrap sec"
      aria-labelledby="reg-feat-h">` with `core.section_head('Featured', id_='reg-feat-h')` and `<ul class="reg-cards
      tgrid">` of `core.trip_card(t, here, core.RELATED_SIZES, ns='rf', summary=True)`. After the cards, when at least
      two reports of `pub` have `t['has_writeup']`: `<p class="reg-more reg-x"><a class="alink">`, `All <K> write-ups
      in Trips`, to `trips/?region=<slug>&writeup=1` (the explorer's own URL state; `&amp;` in the markup).
    - `archive.archive_section(site, here, published=pub, active=planned)`: map/'s table for a subset, with the same
      ids (`all-reports`, `all-reports-h`, `yr-<year>`, `arc-live`), year groups, `core.table_row` rows, year index,
      live region and "Planned" group, here the region's active goals. The filter chips are only for the activities
      the subset has, and a subset with a single activity gets no `div.arc-filt` at all. Called without the two
      keywords, the function lists the whole site as before.
    - `<p class="reg-find reg-x wrap"><a class="alink">`, `Search and filter these in Trips`, to
      `trips/?region=<slug>`.
    - `region.others(slug, here, regs)`: `''` when there is no other region page, else `<nav class="reg-others wrap
      sec" aria-labelledby="reg-others-l">` in the browse-row markup of trips/ (`div.trx-browse > div.trx-bgroup >
      span.t-label#reg-others-l`, "Other regions", then `ul > li > a`): one link per other region page in the order
      of `regions()`, the name followed by `span.trx-bn` with `archive.count_n` of its published reports (spoken ",
      N reports"), then `Map & archive` to `map/`. The markup is reused so that the hit areas of `.trx-bgroup a`
      apply (Targets, under Accessibility above).
  - The Featured rule, `region.pick_featured(ts)`: up to `region.FEATURED_MAX` (3) trips of `ts` that are not planned.
    A journal filed under the region is in `ts` and can be picked, and so can a report without a track. Tier 0 is
    `t['featured']`, the front-matter flag behind the section pages' Featured block; `section.pick_featured` takes a
    single-day trip with a track, and here any report with the flag counts. Tier 1 is `core.written_report(t)` with
    `t['cover']`, tier 2 a written report without a cover, and nothing else is a candidate. Order: tier, then the
    order of `ts` (newest first). With no candidate the section is left out, and the `reg-more` link with it.
  - The document: `core.document(here, '<Region> trip reports', body, description, active='map', body_cls='p-region',
    image=..., extra_head=...)`. Map is the current item of the nav, as `aria-current="true"` (Nav keys above).
    - `region.description(name, pub)` is one sentence that starts with the region, so that no preposition has to suit
      its name: `Lake Tahoe: 86 trip reports, 2022 to 2026 (backcountry ski, climbing, hiking, mountain biking,
      paddleboarding and rafting), with a map of the region and the full GPX track of each.` Its parts: `1 trip
      report` or `N trip reports`; `, 2022 to 2026` or `, 2026`, left out when no report is dated; in brackets
      `region.activity_words(pub)` joined by `section.words_list(..., 'and')`, that is the activities in `core.NAV`
      order in lower case, and for Other the sub-types its reports have, each as its own word (`core.SUB_WORD`), or
      `other` when none states one. Then `, with a map of the region`, always. Only when every report has a track
      (`core.has_track`) it goes on ` and the full GPX track of each`, or ` and its full GPX track` for a single
      report. Then the full stop. It never says that the reports are on the map, because the map shows what it was
      last drawn with. No adjective, and nothing that is not a count or a field.
    - `region.share_image(feat, pub)`: `core.share_photo` of the first Featured pick that has a cover, else of the
      first report of `pub` that has one, else `core.site_share()`.
    - `extra_head` is `core.map_preloads(None, here, [('region-<slug>-desktop', 'desktop'), ('region-<slug>-phone',
      'phone')], 'assets/maps/', site_maps=True)`, as map/ does for its first panel.
    - The page is in sitemap.xml (`core.Page.index` stays True). It has no structured data (no `report=`) and is in
      neither the feed nor the search indexes. It has one h1, its heading levels do not skip, and its ids are unique.
  - Script: archive.js runs when `body` has `p-archive` or `p-region` (the guard at its top). A region page has no
    `.arc-tabs[role="tablist"]`, so the tab code does nothing. The rest runs as on map/. Where the panel has an
    `.arc-all-btn`, the script adds `arc-collapsed` to its list, which hides the `arc-more` rows, shows the button,
    and opens and closes the list on a press (`Show all N` / `Show fewer`). Opening moves focus to the first row
    that was hidden. Closing leaves focus on the button and calls `b.scrollIntoView({ block: 'nearest' })`: the
    page above the reader has just become shorter, and the button they pressed stays in view. That call is new with
    the region pages and runs on map/ too. A hash target (`#all-reports`, `#yr-2024`) is scrolled into view, and the
    activity filter runs, and shows its row, when the page has `.arc-filt`. base.js ties the list to the map through
    `data-map-target`, as on map/: a row highlights its track and pin, a pin its row, and a cluster marker's click
    opens a collapsed list and focuses its report's row. `highlight(map, keys)` in base.js marks the tracks and
    pins whose `data-key` is one of the keys, and the cluster markers whose `data-keys` hold one, with `hl`, and
    gives the map `is-hl`, the class that dims everything not picked out, only when at least one of them matched. A
    row whose trip the map does not draw (a report without a track, a trip newer than the last render) therefore
    leaves the map as it is; before, it dimmed every pin and picked none out. Rows of drawn trips, pins and cluster
    markers behave as they did.
  - Styles: `assets/css/pages/region.css` is bundled like every file in `assets/css/pages/` and holds only what is
    new. `.reg-head` has 24 / 32 / 40 px of padding above the crumbs at the 760 and 1200 px breakpoints (their hit
    area reaches 21 px up). `.reg-head .crumbs a::before { inset-inline: min(-4px, (100% - 44px) / 2); }` gives a
    crumb link narrower than 36 px a hit area 44 px wide, widened by the same amount on each side. That is the short
    `Map` crumb; a wider link (`Reports`) keeps the 4 px each side of base.css (Targets, under Accessibility above),
    and the two areas stay apart. `.reg-stats` is the Mono line, with its `.ml-br` shown so that the places start a
    second line, and with `.reg-stats .mi-w { overflow-wrap: anywhere; }`, so that one place word too long for a line
    breaks instead of widening the page. `.reg-cards` is the Featured grid: one column, two from 560 px, three from
    1200 px. `.reg-more` and `.reg-find` are the two links into trips/, and `@media (scripting: none) { .reg-x {
    display: none; } }` hides both without scripting, because the filters they carry in the address are read only by
    trips.js. Everything else on the page is an existing component (`.crumbs`, `.t-d1`, `.ml` with `.mi-w`, `.arc-*`,
    `.tgrid`, `.tcard`, `.shead`, `.alink`, `.trx-bgroup`). archive.css gained `.arc-reg-a { margin-top: 4px; }` for
    the link on map/, and `.arc-all-btn:not([hidden]) { margin-right: 24px; }`: a shown "Show all" button keeps 24 px
    to its right, so the link stands beside it, and wraps flush left where the column is too narrow for both. home.css
    gained `.hom-reg-n a { display: inline-block; position: relative; z-index: 1; color: inherit; }`, an underline on
    hover and `::before { inset: -14px 0; }`. The link is as high as its 16 px line and its hit area is 44 px high,
    with no box changed. From 1200 px the rule is `.hom-reg-n a::before { inset: -16px 0 -12px; }`: the head is one
    line there and the map starts 13 px under the name, so the area, still 44 px high, sits 2 px higher and ends above
    the map. The `z-index` keeps the area above the count line under the name, whose items are positioned (`.ml >
    .mi`) and come later in the page.
  - URLs and anchors: nothing that existed moved. Every `map/#region-<slug>` anchor is still on map/ (the panel of a
    region with a map, or the region's entry under "Not on a region map"), `core.region_map_href` is unchanged, and
    map/'s panels and table are what they were, apart from the one new link per panel. Phase 5 changed nothing under
    `content/` or `rendered/`, nor the feed, the search indexes or `tools/render.py`. The ids a region page has in
    common with map/ (`all-reports`, `all-reports-h`, `yr-<year>`, `arc-live`, `arc-map-<slug>`, `arc-in-<slug>`,
    `arc-rows-<slug>`) are on separate pages, and `#map` is the region page's own. `build.py --check` covers the new
    pages like any other: links, anchors, ids, `META` and the sitemap. No content file was added, so
    `tools/lib/checks.py` has no new rule.
  - Tests: tests/test_region_page.py, and the page tests that own the changed links (What the test files cover,
    below).

## Trip dict (from tools/lib/content.py)
`slug, dir (the trip folder), meta (index.md's front matter as parsed), title, activity (ski|climb|hike|mtb|other),
activity_label, cat, subtype, kind (trip|multi-day|series|planned), date, end_date, start_time, timezone, place, region,
party, route_shape, featured, draft, beta[{label,value}], conditions{}, map{}, body_md, photos[{file, sm, th, w, h, alt,
caption}], days[…], url ('trips/<slug>/'), track, rendered, stats{distance_km, gain_m, loss_m, high_m, low_m, moving_s,
elapsed_s}, season, has_writeup, cover_photo, cover_focal (x, y), card_summary, cover{photo, source
('explicit'|'parent'|'day'), day, focal}, aliases, published_at, updated_at, journal_highlights, goal (None unless kind
is planned)`.
`photos`: `sm` and `th` are the paths of the 800 px copy and the card-size copy when those files exist beside the photo,
else None (`content._photos`).
`cover`: `content.resolve_cover(t)`, None when the trip has no photo at all. `content.LEAD_MIN_AR` (1.2) is the 6:5 line
the automatic pick prefers and `report.lead_photo` requires (`report.LEAD_MIN_AR` is the same object).
`aliases`: the optional `search_aliases` front matter (an inline list `[PCT, Pacific Crest]`, or one string) as a list of
stripped, non-empty strings; `[]` when absent; anything else is a `content.ContentError`. Only `search.entry` reads it.
`journal_highlights`: the optional `journal_highlights: [001, 059]` front matter (day ids as in the `days/NNN.md` file
names; a number is zero-padded to the width of those names) as the matching day dicts in the listed order; `[]` when
absent or empty, and the key is always present. A value that is not a list, a non-empty list on a trip that is not
`kind: series` (or on a series with no day files), an id with no day file, or a repeat is a `content.ContentError`
naming `content/trips/<slug>/index.md`. Only `series.highlights` reads it.
`published_at`, `updated_at`: the optional lines of index.md that say when a report first went online on this site and
when its content last changed materially, kept exactly as written; None when absent or empty. Accepted: a date
`YYYY-MM-DD`, or a date and time with an explicit offset (`2026-10-03T18:30:00-07:00`, or `Z`; the seconds are
optional), written in the digits 0 to 9 (`content._PUB` is compiled with `re.ASCII`). `content._publication` raises a
`content.ContentError` naming `content/trips/<slug>/index.md` for any other shape, an impossible date or time (an offset
of more than 14:00 is one: `content._pub_value`), a value more than one day after `content._today()` (a function, so
tests can fix the day) on a trip that is not a draft, a `published_at` earlier than the trip's `date` (its first day,
not its last, so that a journal or a multi-day page that went online while under way stays valid as days are added:
the first day file's date when index.md has no `date:` line; `end_date` only when there is no date at all), an
`updated_at` without `published_at` or earlier than it, and either line on a `kind: planned` trip. A draft's two dates
may lie ahead (the day it is planned to go online); every other check applies to a draft as well, and the future check
applies again once `draft: true` is gone. In a days/NN.md file they are unknown keys, which the validator warns about.
They feed `report.published_line`, the two `article:*` meta tags and the `BlogPosting` dates, and nothing else: not the
order of any list, the feed, the sitemap or the home page.
Day: `n, id, label, title, date, start_time, hut, transfer_before, stats, photos, body_md, track`.
`site = {'trips': all (newest first), 'by_slug', 'published' (not planned), 'planned', 'goals' (= planned), 'active_goals',
'goal_backlinks', 'featured' (home.json's picks, in order)}`.

Rendered names per trip (see `rendered/trips/<slug>/meta.json`):
- single: `map-wide` 1440×640, `map-col` 718×400, `map-phone` 390×336, `profile-wide|col|phone` (1248/718/358)
  or `speed-wide|col|phone` for flat water, `tile` 200×152, `g112` 112×64, `g64` 64×48. `tile`, `g112` and `g64` are
  served as cached images: build.py writes them to `trips/<slug>/<name>.svg` and `core.tile` / `core.glyph` return an
  `<img>` (series day glyphs and sparklines stay inline). That holds for a trip of any kind with a track; for one
  without, build.py writes none of the three and none of the `map/` renders, and both functions return `''` (No file, no
  control above).
- multi-day: `overview-wide` 1440×560, `overview-col` 718×440, `overview-phone` 390×260, `day-NN-col` 718×400,
  `day-NN-phone` 390×240, `profile-wide` 1248, `profile-phone` 358, `day-NN-profile-col|phone`, `spark-NN(-cur)`
  96×24, `tile`, `g112`, `g64`.
- series: `overview-tall` 560×860, `overview-phone` 390×600, `days/NNN-g64`, `days/NNN-spark`, `tile`, `g112`, `g64`.
- site (`rendered/site/`): `region-<region-slug>-desktop` 718×620 / `-phone` 390×480 and
  `ski-<region-slug>-desktop` 506×680 / `-phone`; pins link to trips; tracks carry `data-key="<slug>"`
  (`base.js` highlights a track when an element with that `data-key` inside `[data-map-target=<map id>]` is hovered).
  The hillshade and base-layer files are copied to `assets/maps/` (conflict copies left out): pass `site_maps=True,
  asset_dir='assets/maps/'` to `core.map_block`. The `region-*` pair is drawn on the home page (two regions), in the
  region's panel on map/ and on the region's own page; meta.json's `regions` names the regions that have a pair,
  `all_regions` every region `render.py` grouped (a journal's is not among them), and each map entry's `trips` the
  slugs it draws. That is also the list a panel on map/ shows (`core.region_groups`); a region page lists by the
  `region` field instead (`core.region_pages`).

## Checking your work
Run these from the repository root. None of them needs the internet.

```bash
python3 tools/validate.py                # the content checks alone: every error and warning, then a summary line
python3 -m unittest discover -s tests    # the unit tests
python3 tools/build.py --check           # the content checks, the build into _site/, then the built-site checks
```

CI (`.github/workflows/pages.yml`, Python 3.12) runs the second and the third on every push to `main`, tests first, and
publishes only when both pass. A push to another branch runs and publishes nothing.

`python3 tools/build.py --check` stops before the output folder is touched when the content has an error (one `ERROR
content/trips/<slug>/index.md: …` line each on stderr, exit status 1). Otherwise it prints the first warnings, builds,
and checks the built site: every internal link, image and anchor, including anchors on other pages (`map/#region-utah`,
`trips/#y-2024` must land on an element with that id), each page's metadata, the sitemap, the feed, the search indexes
and the published GPX files against their sources. It ends with `link check: OK`, or with the problem lines, `link
check: N problems` and exit status 1. Same-page anchors (`#day-5-2`, `#days`, `#map`) are resolved like the others;
journal-day links on `trips/` are built in the browser, so the check does not see them. `python3 tools/validate.py
--site _site` runs the same site checks on a folder that is already built.

While working on the generator:
- `python3 tools/build.py --out DIR --link --check` builds into another folder and symlinks photos, maps and GPX instead
  of copying them. A build empties its output folder before it writes, so `--out` is refused, as a usage error with exit
  status 2, when DIR is this checkout or a folder that holds it, lies inside one of its source folders, is a file, or is
  a folder that is neither empty nor an earlier build: `build.py: error: --out DIR: a build empties its output folder
  first, and it is not empty and is not an earlier build (it has no .nojekyll file)`. An earlier build is still deleted
  and built again with whatever was put into it since, so keep no files of your own in one. On 2026-10-10 that command
  took about 3 s for the whole site (349 pages, 168 trips) in a copy of the working tree outside iCloud Drive, and
  `python3 tools/build.py --check`, which copies, took 3 to 4 s there (wall time, three runs of each). Those runs were
  before the region pages, which add one page per region with a region map: eight today, so a build prints `built 357
  pages, 168 trips`.
- `python3 tools/build.py --out DIR --only report,home --link` builds only the named page modules (the names are the
  files in `tools/sitegen/pages/`). Do not add `--check` to a partial build: every link into a page that was left out is
  counted as broken, so the check prints its first 40 lines, `... N more` and `link check: N problems` with N in the
  thousands (8,761 for `report,home` on 2026-10-10, with the region pages among the modules left out) and ends with
  exit status 1.
- `python3 tools/build.py --serve` previews the build on http://localhost:8000; `--port N` moves it to another port.
- `python3 tools/add_trip.py … --no-render` skips the map render. The build still passes and the validator warns `no
  rendered map (rendered/trips/<slug>/meta.json is missing); run python3 tools/render.py <slug>`; that command needs the
  internet and runs on Eric's Mac only. A wrong `--strava-export` folder or an unknown `--strava-id` is a usage error
  with exit status 2, not a traceback: `add_trip.py: error: --strava-export <dir>: no activities.csv in that folder
  (give the unzipped Strava export folder)` and `add_trip.py: error: --strava-id <id>: no such activity in
  <dir>/activities.csv`. The id in the tool's help text is a placeholder.
- `python3 tools/thumbs.py --dry-run` lists the card-size photo copies a real run would write.

The unit tests are standard library only and build synthetic trips in temp folders, so they never touch content/. The
tools must run on both Pythons, so run the tests on both, with warnings raised as errors, before a change to `tools/`
goes in:

```bash
/usr/bin/python3 -W error -m unittest discover -s tests    # 3.9, the Mac's system Python
python3.12 -W error -m unittest discover -s tests          # 3.12, the version CI uses
```

On 2026-10-11, after the review before publication, the suite (2,424 tests in 40 files) passed with both commands,
on 3.9.6 and 3.12.11 in this checkout, in about 70 s each, with no test skipped and none marked as an expected
failure. CI runs the plain command, without `-W error`. GitHub's runner image has Node.js (22 on `ubuntu-latest` in
October 2026), so the tests that run a Node harness run there too; they skip only where `node` is not installed (53
tests then). They have only been run under Node 24 and 25.

`tests/run_orders.py` is a helper, not a test module (discovery never loads it), for checking that the suite does not
depend on the order of its test modules: nothing that one module registers with `sitegen.core` (the site, the regions
that have a page of their own) may reach the tests of the next. It loads the tests as discovery does, runs the modules
reversed or shuffled, each keeping its own test order, then prints what `core` still holds and exits with status 1
when a test failed or a region page is still registered (`core._REGION_PAGES`):

```bash
python3 tests/run_orders.py --reverse       # discovery's order (A to Z), reversed
python3 tests/run_orders.py --shuffle 7     # shuffled with random.Random(7); any whole number
```

Four Node harnesses test the page scripts. Three test their pure functions: `tests/trips_js_harness.js` (trips.js),
`tests/ticklist_js_harness.js` (explore.js and ticklist.js) and `tests/series_js_harness.js` (series.js). Given a page
model, each of the three also runs the whole script against a stand-in for the browser. `tests/test_trips_js.py` and
`tests/test_ticklist_js.py` generate a Trips page and a Tick list page from synthetic sites and play a visitor's
typing, Enter, filters, fragment links, Back and Forward on them. The Tick list checks read the history list, the
position in it, the address, the box and the controls after every step (a test holds them to it); the Trips checks
read the history list, the position and the address at the steps a sequence is about, and in the sequences about a
corrected sort also the Sort menu and the order of the list. `tests/test_series_js.py` generates a journal page and
plays a reader's presses, the toggle, hash changes, reloads and loads of each navigation type on the series harness's
own stand-in, which keeps a session store and no history list. The stand-in for the Trips and Tick list pages is one
file, `tests/page_standin.js` (a document grown from the generated page, a history list, a location spelled as the URL
Standard spells it, timers and a clock); neither harness keeps a copy. `tests/js_fixtures.py` holds what the two
Python files share, among it the wrong versions of `historyStep` that both harnesses must reject. Neither file is a
test module. The fourth harness, `tests/maplist_js_harness.js`, runs base.js and archive.js as they are against a
stand-in for a page with a region map and the list beside it, and plays a reader's pointer, focus and presses on it:
which rows dim the map and which leave it as it is, and what `Show all N` and `Show fewer` focus and scroll to (Region
pages, Script, above). `tests/test_trips_js.py`, `tests/test_ticklist_js.py`, `tests/test_series_js.py` and
`tests/test_maplist_js.py` run them, also against modules and scripts with wrong answers that a harness must reject,
and skip those tests when `node` is not installed; the build never runs node. By hand:

```bash
node tests/trips_js_harness.js
node tests/ticklist_js_harness.js
node tests/series_js_harness.js
node tests/maplist_js_harness.js
```

What the test files cover:
- Phases 1 to 2T: home.json curation, cover resolution, card summaries, home cards, the search indexes, the Trips page,
  the header's nav state, trip cards, goal sidecars, the GPX inspector, the tick-list CLI and page, the renderer's
  handling of goals.
- Phase 3: `tests/test_report_page.py` (layout selection, id order, section links, hero, gallery, captions, actions,
  share row, bottom bar), `tests/test_related.py` (`core.related`, `related_block`, `copy_link`),
  `tests/test_series_page.py` (highlights validation, the introduction, actions, written-entry navigation, hero, toggle,
  day anchors, write-ups verbatim, unchanged anchors and GPX names), `tests/test_journal_days.py` (day labels, the
  anchor checks, `core.recorded`, a journal of one day), `tests/test_series_js.py` with `tests/series_js_harness.js`
  (series.js's pure helpers, the hooks it looks up on a generated journal page, and the whole script run against a
  stand-in for the browser, which starts several dozen short Node processes: 58 since the review before
  publication), the automatic cover pick in `tests/test_cover.py`, and the journal-day cases in `tests/test_search.py`, `tests/test_trips_page.py` and
  `tests/trips_js_harness.js`.
- Phase 4:
  - `tests/test_checks.py`: `checks.run` on a small valid synthetic site that each test breaks in one way, asserting
    the exact errors and warnings; a table of malformed inputs (`CASES`), none of which may raise; and the loading
    code's existing messages coming through unchanged.
  - `tests/test_checks_site_maps.py`: the validator's warning for a trip that the committed maps under `rendered/site/`
    still draw (a draft, a removed folder, a removed track), on a synthetic tree in a temp dir.
  - `tests/test_checks_more.py`: the content rules added after the author guides were followed literally: a conflict
    copy inside a trip folder, a multi-day trip whose day files hold routes and no recorded track, a `track.gpx` left
    beside day files, a day dated after the trip's `end_date`, and a key written twice in the front matter.
  - `tests/test_frontmatter.py`: which front-matter values are numbers: only ones written in the digits 0 to 9;
    full-width and other scripts' digits stay the text that was typed, and what the loader and the validator then make
    of a photo size written that way.
  - `tests/test_validate_cli.py`: `validate.main(argv)` in-process on a temp `--content` folder with a fixed `--today`:
    the output, the exit statuses, `--json`, the options, the command's side of `--site` (a stand-in takes the site
    checks' place), and three runs as a real process.
  - `tests/test_sitecheck.py`: every rule against built folders made by hand (in a sound one, a test breaks one thing
    and asserts the whole list `check()` returns), the three old lines character for character, conflict copies, and a
    small site built by `build.build()` itself, in which the checks must find nothing.
  - `tests/test_sitecheck_hostile.py`: the site checks on a folder the build did not write: malformed and hostile
    files must come back as problem lines, promptly, never as an exception or a stalled check.
  - `tests/test_build_cli.py`: `build.main(argv)`, `--only`, `--out` and `build.unsafe_out`, `content_errors`, the
    `check` wrapper, `build.gpx_root_tag`, day files with Windows line endings in the combined GPX, and the one write a
    `--link` build must never make (the combined GPX through a symlink into the content).
  - `tests/test_build_site.py`: `build.build()` end to end on a synthetic repository root in a temp dir: reports
    without a track, renders left in `rendered/` by a track that was removed, section descriptions, the combined GPX
    rule, the robots.txt, sitemap and feed files, a stylesheet without comments, conflict copies under `rendered/` and
    `assets/` left out, builds that stop; and the two pure helpers `strip_css_comments` and `conflict_copy`.
  - `tests/test_track_rules.py`: what the generator says about a recording, with a track and without one:
    `core.has_track`, `core.render_meta` and the route drawings, the closing fact of `core.summary`, `core.stats_note`,
    the Beta block's Track row, the size attributes of `core.photo`, the description of an empty section and the
    `Multi-day · 1 day` tag. What the pages do with it is in `tests/test_report_page.py` (`NoTrackTests`).
  - `tests/test_render_goals.py` (`ReportWithoutTrackTests`): `render.no_track`, a report without a track skipped, its
    stale render folder removed and the region maps drawn without it, all with the drawing functions stubbed.
  - `tests/test_about_units.py`: the About page's Units section without JavaScript: the sentence about the switch is
    hidden with the switch, and the sentence before it stays.
  - `tests/test_metadata.py`: `published_at` / `updated_at` (every accepted form and every refusal, with
    `content._today` fixed), the share tags and their order, the head of every page type, the site-wide share image on
    the four site pages only, one `BlogPosting` on a written report and none anywhere else, and `build.feed()` and
    `build.sitemap()`.
  - `tests/test_thumbs.py`: `photos.thumb_size`, `core.thumb_width` and tools/thumbs.py held to each other to the
    pixel; which photos get a copy, where it goes and what a run may touch; a photo path outside `photos/`, a photo the
    converter cannot read, and the cwebp command line, which keeps the colour profile.
  - `tests/test_privacy_audit.py`: the tool's arithmetic and every count of its default report on a synthetic tree; that
    the default report names nothing and gives no figure about fewer than three tracks or places, that a photo or a
    day file named like a conflict copy is counted, what `--site` finds in a built folder, that the tool only reads,
    and that neither the build nor CI runs it.
  - `tests/test_a11y_static.py`: the Phase 4 accessibility rules, read out of the stylesheets, base.js and section.js and
    out of a generated fixture site with a small cascade reader and script scanner written for the file (no browser,
    no node); and on every page type one h1, the skip link, alt attributes and no nested interactive elements.
  - `tests/test_archive_page.py`: the map page's anchors (`map/#all-reports`, `map/#other-places`, one
    `map/#region-<slug>` per region) and its share image.
- Phase 5 (region pages), on synthetic fixtures only: `tests/test_region_page.py` holds the rule for which regions get
  a page (`core.region_groups`, `core.region_pages`, `core.region_page_href` and what `core.register_site` records)
  and the page itself (the head, the map panel with `page=True`, the Featured rule, the table for a subset, the other
  regions, the description and the share image). The links that changed on other pages belong to the test files that
  own those pages (the report and goal pages, trips/, the home page, map/). A built-site test holds that the region
  pages exist, are in the sitemap and pass `sitecheck`, and the fixture site of `tests/test_a11y_static.py` has a
  region page. The list beside a region map is played under node by `tests/test_maplist_js.py` with
  `tests/maplist_js_harness.js` (a row whose trip the map does not draw, `Show all N` and `Show fewer`), and
  `tests/test_a11y_static.py` (`MapListScriptTests`) reads the same two behaviours from base.js and archive.js
  without node.
- The review before publication (2026-10-11): the Trips page's history and sort rules (`TripsPageScenarioTests` plays
  the sequences, `TripsPageSourceTests` reads the handlers, both in `tests/test_trips_js.py`) and the same history
  rule on the Tick list (`tests/test_ticklist_js.py`); the journal's hidden ids (`tests/test_series_js.py`); the
  `autocomplete="off"` of the two filter forms and of the journal's box (the three page test files); the home page's
  `latest-h` anchor (the id of the heading of the old home page's Latest reports list, kept on the Recent outings
  section so that a saved `…/#latest-h` still lands; `LatestAnchorTests` in `tests/test_home.py`); a manifest key
  written twice (`DuplicateKeyTests` in `tests/test_curation.py`); the 404 page (`tests/test_notfound_page.py`).
  `tests/test_fixture_text.py` holds that no file under `tests/` quotes a write-up: it fails when eight consecutive
  words of the text below a trip's or a day's front matter stand in a test file, and names the two files and the line,
  not the words. Reword the test's sentence when it fires. Its check of the real `content/` is skipped where that
  folder is absent.

## Measuring page loads
This is the method the Phase 4 loading measurements used, written down so that a later change can be measured the same
way. One run is one cold load in a fresh browser context (empty HTTP cache and storage) of a build served under
`/personal-website/` by a local server that gzips text as GitHub Pages does. The phone profile is a 390 x 844 viewport
at 3x with touch, the Slow 4G network preset and a 4x CPU slowdown, three runs per page with the median reported; the
desktop profile is 1440 x 900 at 1x without throttling, one run. The numbers are read inside the page: a
`PerformanceObserver` installed before navigation records the largest-contentful-paint and layout-shift entries (LCP and
CLS), and four seconds after `load` the navigation and resource timing entries give the transfer size of the document
and of every request (a run in which a resource came from the cache is not cold and is repeated). The scripts that drove
the browser, served the build and summarised the runs were scratch files and are not in the repository. The results
are in docs/IMPLEMENTATION_REPORT.md (the comment above `core.PHONE_SLOT` cites it for the lead photo's figures). They
were lab measurements, not field data.
