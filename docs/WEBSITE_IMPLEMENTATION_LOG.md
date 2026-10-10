# Website implementation log

Phase-by-phase record of the work from `docs/personal-website-improvement-plan.md`. Each entry says what was changed,
what was actually run, and what was not.

## Phase 0 — Baseline (2026-10-09)

**Environment.** macOS 25.5, `/usr/bin/python3` 3.9.6 (the tools stay 3.9-compatible; CI runs 3.12). Browser checks
used the Claude desktop app's built-in browser (Chromium) against a local `http.server` that served the build under a
`/personal-website/` prefix, like GitHub Pages. No Lighthouse, screen-reader or real-device testing was available.

**Starting point.** Commit `a9baab9` on `main` ("Polish round 3"). Work branch `phase1-curated-homepage` was created
from it; nothing was reset or rewritten. Pre-existing uncommitted work was left untouched: `README.md` (adds a link to
`ADDING-TRIPS.md`) and the untracked `ADDING-TRIPS.md`. About 6,282 untracked iCloud conflict copies sit under
`rendered/` (`meta 3.json`, `map-wide 4.webp`, …); none are part of this work and none should be staged.

**Content inventory.** 168 trips: 156 single-day, 10 multi-day, 1 series (the PCT), 1 planned route; no drafts. Nine
trips carry `featured: true`. 341 GPX files under `content/trips/` (SHA-256 of each recorded before any change). The PCT
has 150 recorded days, 32 with writing, 25 with photos, and no parent narrative or photo list.

**Baseline build.** `python3 tools/build.py --check` on the unchanged code: 345 pages, link check OK, exit 0. The run
took 29 min 54 s wall-clock (14 s of CPU) because about half of `rendered/` had to download from iCloud first (`CLAUDE.md` describes this); the same
build takes under a minute in CI. The 345 output HTML paths and the id sets of every page were saved for comparison.
Anchors relied on later: `map/#all-reports`, `map/#other-places`, 14 `map/#region-*` panels, and the PCT page's day and
month anchors.

**Plan vs. current code.** The plan's audit of `a9baab9` matched the checkout: one featured trip picked by flag or
date (`home.featured`), `first_photo` fallback, a ten-row latest table, the featured photo hidden below 1,000px and the
hero actions hidden below 760px. No newer work had to be reconciled. One number the plan did not state: the PCT journal
has 150 recorded days (the plan's "N recorded days" placeholder).

**Pre-existing problems.** None in the build check. The README's example Strava export path is stale (noted in the
workspace `CLAUDE.md`), unrelated to this phase.

## Phase 1 — Curated homepage and presentation foundation (2026-10-09)

### Changed files

| File | Change |
| --- | --- |
| `content/home.json` (new) | The ordered featured list: PCT, Matterhorn Peak – West Couloir, PEAK BAGGING SZN. |
| `tools/sitegen/curation.py` (new) | Loads and validates the manifest; `site['featured']`. Strict errors name the file and slug. |
| `tools/lib/content.py` | `cover_photo`, `cover_focal_x/y`, `card_summary` normalised; `resolve_cover()`; `ContentError`. Front-matter syntax errors now name their file (`content/trips/<slug>/index.md: front matter: …`). Files closed with `with`. |
| `tools/sitegen/core.py` | `card_summary()` (text + provenance), `cover_img()`, `cover_preload()`; fragment readers close their files. |
| `tools/build.py` | Resolves the manifest before any page; prints one `ERROR …` line and exits 1 on a content/curation error. |
| `tools/sitegen/pages/home.py` | Hero with both actions always visible; featured cards (0–6, lead + supporting); six recent outings; share image and preload from the lead cover. The single-feature map block and the ten-row table are gone. |
| `assets/css/pages/home.css`, `assets/css/base.css` | New hero, featured and recent-outings layout (phone stack, tablet lead-plus-two, desktop 7+5 columns). By-activity and region sections unchanged. `base.css`: the shared `.keyrow--compact` rule moved here from the old home CSS (section pages use it), `.hom-ft` replaced by `.hom-card-t` in the balance list, one stale comment. |
| `content/trips/{pacific-crest-trail-2024,matterhorn-peak-west-couloir,peak-bagging-szn}/index.md` | `cover_photo` and focal values only; titles, bodies, stats, photos and tracks untouched. |
| `tests/` (new) | 101 standard-library tests: curation matrix, cover resolution, summary provenance, home cards, cover image/preload helpers, share image, front-matter errors. |
| `docs/CONTENT_GUIDE.md` (new), `README.md`, `docs/DEVELOPING.md`, `ADDING-TRIPS.md`, workspace `CLAUDE.md` | Author workflow, front-matter fields, trip/site dict additions, test command. `ADDING-TRIPS.md` (Eric's uncommitted file) got a one-sentence correction: `featured: true` no longer picks the home page. README's publish step now stages by path instead of `git add -A`. |
| `.github/workflows/pages.yml` | Runs the unit tests before the build. |

### Behaviour

- `content/home.json` alone decides the homepage features and their order; `featured: true` keeps its section-page
  role. Zero to six entries; an explicit empty list hides the section. Duplicate, unknown, draft, planned, non-string
  and more-than-six entries fail the build with `content/home.json: …`. Only a missing file falls back to the legacy
  pick, with a warning. A newer trip never displaces a configured feature (dates are not consulted).
- Covers: an explicit `cover_photo` must be a declared photo (trip or day) that exists; traversal and bad focal values
  are errors (`content/trips/<slug>/index.md: …`). Automatic fallback: first landscape trip photo → first trip photo →
  first landscape day photo → first day photo → route tile → activity disc. The declared `w`/`h`/`alt`/`.sm` are reused.
- Summaries carry provenance: explicit `card_summary` → the write-up's opening → a labelled day excerpt (multi-day
  only) → facts → none. The PCT card shows `APR 22 – SEP 21, 2024 · MEXICO TO CANADA` and `150 RECORDED DAYS ·
  3,167 MI RECORDED`, never a day's prose. Matterhorn and Peak Bagging show the opening of Eric's own write-ups. No
  copy was written for any trip.
- Recent outings: the six newest published trips not featured above, with cover photo, route tile or disc; "All N
  reports" still goes to `map/#all-reports`. Hero actions: "Browse all trips" → `map/#all-reports`, "Explore the map" →
  `map/` (header navigation deliberately unchanged until Phase 2).
- Initial covers (editorial picks to confirm): PCT `photos/d059-01.webp` (day 58, hiker above a Sierra lake; focal
  45/55), Matterhorn `photos/01.webp` (focal y 40), Peak Bagging `photos/04.webp` (Lake Tahoe behind the alpine lakes;
  focal y 45). Alternatives looked at for the PCT: `d001-01` (southern terminus), `d049-02` (Mount Whitney), `d050-02`
  (Forester Pass).

### Checks actually run

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` | 101 tests, OK (0.5 s). |
| `python3 tools/build.py --out <scratch> --link --check` (full build of the new code) | 345 pages, link check OK, 13 s. |
| Output compatibility | HTML path set identical to the baseline (345); all 344 pages other than the home page byte-identical; id sets identical; `feed.xml` and `sitemap.xml` identical; 341 content GPX checksums unchanged; the same 351 GPX downloads, byte-identical. |
| Invalid manifests | Duplicate, unknown, draft, planned, >6, malformed JSON, non-list each stop the build with the named error (unit tests). |
| Screenshots (built-in browser, `/personal-website/` prefix) | After: 1440, 1024, 768, 390 and 320 px: three cards in order at every width, every card with its photo, both hero actions visible on phones, recent outings 3/2/1 per row with route-tile fallbacks. Before (baseline build, 1440 and 390 px): one map-first feature (the newest flagged report, Dunderberg Peak), no photo and no actions on the phone, ten-row table. Files are not committed; they were handed over with the phase report. |
| Long titles | Two 90–120-character titles injected into the supporting cards at 768 px: wrapped cleanly. |
| Keyboard and link names | Focusable links per card are chip, title and action (photo links `tabindex=-1`, `aria-hidden`); visible focus from `base.css`. Title links are described by their DATE · PLACE line (`aria-describedby`) and action links carry the trip title for screen-reader link lists. |
| No JavaScript | The home page is static HTML; `site.js` only adds the phone menu and the unit toggle. |
| Page weight (estimate from built file sizes, not a measured transfer) | Phone picks (smallest srcset candidate per image): about 1.2 MB in total (HTML 205 KB, CSS 141 KB, JS 36 KB, images 826 KB), against about 0.9 MB before; within the plan's 1–1.5 MB budget. The six recent-outing thumbnails take the 800 px copies (no smaller derivative exists yet; Phase 4 may measure whether one is worth adding). |
| Not run | Lighthouse/performance measurements, screen readers, real devices, 200% zoom, reduced-motion emulation. |

### Review

A six-lens review (plan compliance, Python correctness, HTML/accessibility, CSS/responsive, documentation accuracy,
test quality; 36 agents in all) checked the work, and three skeptics tried to refute every high/medium finding.
Confirmed and fixed:

- Featured cards 4–6 on desktop kept `align-items: start` from the two-column rule, so their photos shrank to 200px
  (high). Fixed; measured 400 × 267 px photos in 400 px cells with six cards.
- A supporting card with neither photo nor route tile put its copy in the 200 px photo column (medium). Fixed; its
  body now spans the 506 px cell.
- The guide's "What not to do" still promised a journal sentence on the PCT card (medium). Reworded.
- Front-matter syntax errors surfaced as a traceback without a file name, and the guide's quoting advice was wrong
  (medium). The loader now reports `content/trips/<slug>/index.md: front matter: …` (days too) and the guide
  describes the real rule.
- `ADDING-TRIPS.md` still said `featured: true` makes a trip eligible for the home page (medium). Corrected.
- No test rendered a multi-day card, so the `DAY N · TITLE` attribution could have been dropped silently (medium).
  Added, with tests for the no-photo card, recent-card covers, `cover_img`/`cover_preload`, the share image,
  singular/zero recorded-day wording, an undated multi-day facts line, a missing day-photo file and bare keys.

Low findings fixed as well: the one-card desktop layout's empty 40 px row, the `sizes` attribute for cards 4–6,
the `.keyrow--compact` rule the region maps and section pages still use, an undated multi-day facts line ending in
", .", unused imports, repeated link names ("Read the report", "Tallac") now distinguished for assistive
technology, README's `git add -A` publish step, the legacy-fallback wording, the "single-day trips only" scope of the
section Featured block, and the workspace `CLAUDE.md` claim that there is no test suite.

Rejected after verification (left as is, recorded for later phases): hiding the cover links from assistive
technology (deliberate: the title link names the card; the photo's alt text is kept in the markup), and dedicated
tests for the build's `main()` error path (pre-existing behaviour, Phase 4). Deliberately not adopted: rendering
the facts sentence on the PCT card (the data lines carry the same facts; the guide and a test pin the choice).

### Remaining issues and author inputs

- Confirm or change the three covers and focal points (see `docs/CONTENT_GUIDE.md`).
- Optional `card_summary` for each featured trip (without one the cards use the report's opening; the PCT uses facts).
- The site tagline is unchanged; the plan's optional supporting line ("Stories, photos, and routes from days outside.")
  was not adopted.
- Header navigation (Trips | Tick list | Map | PCT | About) and search belong to Phases 2 and 2T.

A draft trip with a broken `cover_photo` stops the build like any other content error (documented in the guide).

**Next smallest step:** Phase 2, the `trips/` explorer (section 8), reusing `core.cover_img` / `core.card_summary`.

## Phase 2 — Trips explorer and discovery (2026-10-09)

Starting point: Phase 1 committed as `c46949e` on `phase1-curated-homepage`; the working tree was clean apart from the
untracked iCloud conflict copies under `rendered/`.

### Changed files

| File | Change |
| --- | --- |
| `tools/sitegen/pages/trips.py` (new) | `trips/index.html`: head with counts, a static browse block (activities, regions, years), the search form (hidden until the script reveals it, with a `<noscript>` note), status row, every published report as a card grouped by year, and `trips/search.json`. |
| `tools/sitegen/search.py` (new) | The search index: `normalize()`, one entry per published trip (title, place + region, activity label + aliases + named peaks, the write-ups capped at 4,000 characters, and the plain text the hit snippet is cut from), compact JSON with `<` escaped. No coordinates, GPX, drafts or planned routes. |
| `assets/js/pages/trips.js` (new) | Filters from the cards' data attributes; text search over the lazily fetched index (loading and failure messages; the filters never need it); best-match / newest / oldest order; cards or list; the state in the query string (`replaceState` while typing, `pushState` for filters, `popstate` restores); chips with remove buttons, Clear all, counts, no-results state, snippets around a hit (textContent only). Pure functions exported for the Node test. |
| `assets/css/pages/trips.css` (new), `assets/css/base.css`, `assets/css/pages/home.css`, `assets/css/pages/archive.css` | Explorer layout; the filter chip (`.fchip`, formerly `.arc-chip` on the map page) and the trip card (`.tcard`, formerly the home page's recent card) are shared components in `base.css`. |
| `tools/sitegen/core.py` | `trip_card()` (one card for the home page and the explorer, with `data-*` facets and `aria-describedby`); main navigation Trips · Map · PCT · About + Search with the `aria-current` rules; phone menu Site column; footer. |
| `tools/lib/content.py`, `content/trips/pacific-crest-trail-2024/index.md` | `search_aliases` → `t['aliases']` (validated); the PCT gets `search_aliases: [PCT]`. |
| `tools/sitegen/pages/home.py`, `tools/build.py`, `tools/sitegen/pages/archive.py`, `assets/js/pages/archive.js` | Home actions and "All N reports" go to `trips/`; the recent cards use `core.trip_card`; `trips` registered; the map page's chips renamed to the shared class (behaviour unchanged). |
| `docs/DEVELOPING.md`, `docs/CONTENT_GUIDE.md`, `README.md` | The explorer's contracts (card attributes, index fields, URL keys, history, no-JS, nav keys, adding a facet or alias); the author guide's "Search and the Trips page" section; front-matter rows. |
| `tests/` | Phase 2 tests: 87 new methods (search index, Trips page, header navigation, trip cards, and a Node harness of 50 checks on the explorer's pure functions, skipped without `node`); 188 in all. |

### Behaviour

- `trips/` lists all 167 published reports once (a series counts once; the planned route is absent and stays on the map
  and its activity page until the Tick list). Counts come from the same data as the cards.
- Search covers title, place, region, activity, named peaks (`map: peaks`), `search_aliases` and the write-up text; every
  typed word must match; case, accents and punctuation are ignored. Filters: activity, region, year, format (single-day /
  multi-day / series), has a write-up; sort newest / oldest / best match; cards or list view.
- Shareable URLs such as `trips/?q=couloir&activity=ski&region=eastern-sierra&sort=relevance&view=list`; unsupported
  keys and values are ignored; Back and Forward restore the state; typing never creates history entries.
- Without JavaScript: every report link, the year anchors (`#y-2026`) and the browse links (section pages,
  `map/#region-*`) are plain HTML; the form stays hidden and a note says so. A failed index fetch shows a message and
  leaves the list and filters working.
- Navigation: Trips · Map · PCT · About · Search on every page (the five activity pages stay in the phone menu, the
  footer and the home page). The map page, `map/#all-reports`, `map/#region-*`, report URLs and GPX URLs are unchanged.

### Checks actually run

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` | 188 tests, OK (1.1 s), including the Node harness (50 checks). |
| `python3 tools/build.py --out <scratch> --link --check` | 347 pages (345 + `trips/` + `trips/search.json`), link check OK, 13 s. |
| Browser, served under `/personal-website/` (built-in browser, 1440 and 390 px) | "matterhorn" finds Matterhorn Peak and the Chamonix–Zermatt day that mentions it, best match first; Backcountry Ski + Eastern Sierra gives 6 of 167 with two chips and per-year counts; Clear all resets; reloading `?q=couloir&activity=ski&region=eastern-sierra&sort=relevance&view=list` restores every control and the list view; changing a filter then Back restores the previous filter, Forward re-applies it; "zzzzqqq" shows the no-results block and Clear filters; with `fetch` failing the status message appears, the count stays `167 REPORTS` and all 167 cards stay; 167 title links and the `<noscript>` note are in the server-rendered HTML; no duplicate ids; no horizontal overflow at 390 px; the phone menu lists Trips, Map & archive, PCT, About, Search; after the review fixes: the header's Search link lands on the Trips page with the search box focused, the phone menu's Search closes the menu, an explicit Newest first survives typing, "hiking" finds hikes by activity, best-match results sit under their own heading. |
| Page weight | `trips/index.html` 353 KB (167 cards with excerpts; the map page is 890 KB), `search.json` 68 KB, fetched only when a query is typed. |
| Not run | Lighthouse, screen readers, real devices, 768/1024/320 px screenshots of the explorer (the layout reuses the home page's card grid, checked at those widths in Phase 1). |

### Review

A seven-lens review (plan compliance, Python, JavaScript behaviour and safety, HTML/accessibility, CSS/responsive,
documentation, test quality; 70 agents) with three skeptics per high/medium finding. Confirmed and fixed:

- The header's Search link (`trips/#search`) never focused the box: the load-time `replaceState` dropped the fragment
  before the check ran, and year deep links lost their scroll (high). The fragment is now kept on the load-time write,
  the box is focused after the first render and on same-page clicks.
- The activity label was not searchable although plan 8.3 lists it (medium). The index's keyword field now opens with
  the activity (and the Other sub-type word); the placeholder, description and guide say so.
- The forced-colours rule still targeted the renamed map-page chip, so the checked activity chip (map/ and trips/) and
  the new view toggle had no high-contrast cue (medium). Fixed.
- Choosing "Newest first" explicitly was overridden by the next keystroke (medium). Any choice in the sort menu now
  sticks.
- The loading / unavailable message was not a live region and the count claimed `167 OF 167` while the index was
  unavailable (medium). The message has `role="status"` and the query counts as a filter only once the index answered.
- The phone menu's Search link on the Trips page itself left the menu open with the page inert (medium). A link in the
  menu now closes it.
- The active-filter remove chips were 32 px targets (medium). They keep their size with a 44 px hit area.
- DEVELOPING's trips.css clause and "adding a facet" recipe were incomplete (medium); the page description over-claimed
  (medium). Corrected; trips.js now keeps its facet list in one `FACETS` array.

Low findings fixed as well: the unused 160-character snippet field dropped from the index (68 KB instead of 77 KB);
Python and JavaScript normalisation now strip exactly the same combining-mark block (two parity cases added); regions
keyed by their map-anchor slug; `map: peaks` given as one string or with non-string items handled; a trailing comma in
`search_aliases` ignored; the loading message cleared when the query is; one retry per changed query after a failed
fetch; the submit handler no longer pushes history for an unchanged query; astral characters truncated by code point;
cards only re-attached when they moved (focus no longer lost while typing); all status elements guarded; the live count
only rewritten when it changes; sorted views keep the outline with an h2 ("Best match first" / "Oldest first");
arrow-key steps through a radio group within 600 ms share one history entry; the PCT region in the browse block links
to the explorer's own filter; a no-op list-view rule removed; the innerHTML test also bans the other HTML sinks; snippet
and chip-label behaviour checked in the harness; the two home-page tests no longer read `rendered/`.

Rejected after verification (recorded, not changed): a Python-level test of the DOM filter predicate (covered in the
browser and by the Node harness on the pure functions), guarding the relative `search.json` URL against a
root-relative rewrite (links go through `core.link` and the fetch is relative to the page), the 4,000-character cap on
the PCT's write-ups (deliberate; documented), a longer announcement delay for the live count.

### Remaining issues and author inputs

- Search "lovers leap" does not find Lover's Leap (the apostrophe splits the word); add `search_aliases: [Lovers Leap]`
  to those reports if people type it that way.
- The explorer's browse block repeats the 15 regions; once the Tick list and Phase 3 land, consider trimming it to the
  mapped regions.
- Planned routes have no explorer presence by design (Phase 2T).

**Next smallest step:** Phase 2T, the Tick list (section 20), reusing `core.trip_card`, the `.fchip` filters and the
explorer's URL-state code.

## Phase 2T — Tick list and future-goal workflow (2026-10-09)

Starting point: Phases 1 and 2 committed (`c46949e`, `ca5c6ec`); the working tree was clean apart from the untracked
iCloud conflict copies under `rendered/`. Baseline before this phase: 188 tests OK, `build.py --check` OK (347 pages).
The content has one existing planned route (`crystal-range-to-bayview`, a legacy goal without a sidecar) and no future
goals were supplied: every goal used for testing and screenshots is a synthetic fixture built in a scratch copy, never
in `content/`.

### Changed files

| File | Change |
| --- | --- |
| `tools/lib/goals.py` (new) | `goal.json` defaults and strict validation (statuses, priorities, months, commitment, scope, source kinds and the author-drawn approximation note, references, field evidence that must be approved before difficulty or season notes publish, checklist, outings, the derived route block and its checksum), `is_active`, site-level outing checks, report backlinks. |
| `tools/lib/gpxroute.py` (new) | Bounded GPX inspection (30 MB, 500,000 points, no DOCTYPE/ENTITY, finite coordinates in range), routes and tracks kept apart with every segment, explicit selection among alternatives, `measure()` (per-segment polyline length, gain only with full elevation, elevation full/partial/none, times only noted), byte-exact extraction of the chosen element, `as_tracks()` for the renderer. |
| `tools/ticklist.py` (new) | `add`, `update`, `log-outing`, `review-packet`, `export`, all with `--dry-run`; drafts by default; `--publish-track` is the only way a file enters the checkout; no local path is ever written; never calls `add_trip.py`; a render failure leaves a valid goal. |
| `tools/lib/content.py`, `tools/build.py` | `t['goal']` for planned trips; `site['goals']`, `site['active_goals']`, `site['goal_backlinks']`; site validation of outing report slugs. |
| `tools/sitegen/pages/ticklist.py` (new), `assets/css/pages/ticklist.css` (new), `assets/js/pages/ticklist.js` (new), `assets/js/pages/explore.js` (new) | `tick-list/`: counts from the data, search and filters (activity, region, status, priority, month, has a route), scope tabs, priority / newest / name order, cards or list, shareable URL state with Back/Forward; static region groups without JavaScript; read-only. `explore.js` holds the helpers trips.js and ticklist.js share. |
| `tools/sitegen/core.py` | `goal_card`, `goal_tags`, `goal_stats_line`; Tick list in the header, phone menu and footer; `summary()` for goals without a route. |
| `tools/sitegen/pages/report.py`, `assets/css/pages/report.css` | Goal pages: Tick list breadcrumb, Planned route and status tags, ≈ values, an approximate stats strip with a provenance note (no gain without full elevation, never a moving time), the map or an honest fallback, Why · Planning notes · Season and commitment · Route source · References · Still to check (read-only) · Outings, "Back to the tick list"; `On the tick list:` backlink on referenced reports; no full-screen map page for an unrendered goal. |
| `tools/render.py` | Planned routes drawn from `gpxroute.as_tracks`: one track per segment, routes included, gaps never bridged. No existing render changed. |
| `tools/sitegen/pages/home.py`, `section.py`, `archive.py` | "+ N PLANNED ROUTE" counters and the Planned blocks use the active goals; completed and archived goals keep their pages. |
| `docs/TICK_LIST_GUIDE.md` (new), `README.md`, `docs/DEVELOPING.md`, `docs/CONTENT_GUIDE.md` | The complete workflow, every field and rule, the importer's GPX behaviour, privacy, the enrichment workflow and the research prompt (verbatim from the prompt pack). |
| `tests/` | Phase 2T tests (see below). |

### Behaviour

- A goal is a `kind: planned` trip folder with an optional `goal.json`; the one legacy planned route keeps working with
  documented defaults (`legacy: true`, status idea, normal priority). A sidecar beside a report is an error.
- Minimum intake is a name and an activity; everything else is optional. New goals are drafts. `--publish-track` copies
  the chosen geometry byte for byte (or the chosen element of a multi-route file), records its SHA-256, writes the
  approximate stats and the route block; without it nothing from the file reaches the checkout. A changed published file
  fails the build rather than being re-measured silently.
- Statuses are intent; `completed` exists only as a logged outing and `attempted` needs an attempted outing; a report
  linked from an outing must be a published, non-planned trip; the planned track and the report are never modified;
  dates and reports may stay unknown. Archival is a separate flag.
- Goals never enter the Trips explorer, the search index, the feed, home features or report counts; the planned-route
  counters count only active goals.

### Checks actually run

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` | 436 tests OK (188 from Phases 1–2 plus 248 for this phase: 54 GPX inspector, 72 goal sidecar, 52 importer CLI, 65 tick-list page / goal pages / boundaries, 5 Node wrappers; the ticklist.js harness runs 59 checks). The matrix covers plan 20.10's list: metadata-only idea, route-only GPX, multi-segment track (nothing bridged), alternatives needing `--select`, no / partial elevation, no timestamps, waypoint-only, sparse geometry, duplicate checksum, rejected inputs, dry run, byte-identical publication, failed render fallback, legacy planned route, status / reference / evidence rules, attempts before completion, completion without date or report, active counts, draft exclusion, read-only pages, goals absent from published / feed / search / features. |
| Security review of the commit (automated) | Three findings fixed in the follow-up commit: a published third-party GPX is served from the site's own origin as XML, so files carrying a processing instruction (xml-stylesheet), XHTML / SVG / MathML content, a `<script>` or a `javascript:` URL are now refused; the DOCTYPE / ENTITY scan could be bypassed by a non-UTF-8 file, so only UTF-8 files are accepted and every `<!` but comments and CDATA is refused; the element extractor used a regex that a comment containing `<trk` could shift, so it now slices by the XML parser's own byte positions. The import report also lists what a file carries besides its geometry (metadata, extensions, links, named waypoints, timestamps, comments) before a copy is approved. A second review of that commit found the byte scan could be bypassed by what only an XML parser decodes (a character reference in a namespace URI, `<s:script>` under a prefix, `&#106;avascript:` in an href, an encoding declaration a browser honours), so the same checks now also run on the parsed document: declared encoding must be UTF-8, no DOCTYPE or processing instruction, no XHTML / SVG / MathML / XLink namespace however spelled, no script-like element under any prefix, no `on*` attribute, no `javascript:` / `vbscript:` / `data:` value once decoded. Garmin extensions, `xsi:schemaLocation` and CDATA still pass. A third review noted that the document assembled for a chosen element of a multi-route file was validated only as slices (its `<gpx>` start tag came from a regex that a `>` inside an attribute or a `<gpx` inside a comment could cut short), so the head now ends where the parser says the root start tag ends, the closing tag uses the root's real name, and the assembled document is inspected again as a whole and must hold exactly the chosen geometry. |
| `python3 tools/build.py --out <scratch> --link --check` | 348 pages (347 + `tick-list/`), link check OK, 13 s. The one existing planned route builds as a legacy goal with the defaults. |
| Importer, in a temporary content folder | Dry run writes nothing; a published track's bytes equal the source (SHA-256 recorded); no local path in any written file; a duplicate checksum, an existing slug, a traversal slug, `--status completed` without an outing, an unknown report slug, a review packet inside the checkout and reopening a completed goal are each refused; attempted then completed outings set the status and keep both events; the packet carries the research prompt; export lists non-draft goals only. |
| Synthetic demo site (a scratch copy of the content with five synthetic goals created through the importer: a two-segment track, a route-only file, an idea without a route, a completed goal with an attempt and a linked real report, an archived idea) | The tick list shows the six goals by region with honest counts (4 active · 1 shortlisted · 1 completed); scope, filters, search, sort and view work with shareable URLs; goal pages show ≈ stats with the provenance note, the map fallback, Why, Planning notes, Season and commitment, Route source, Still to check (read-only), Outings; the completed goal links to its report and the report shows "On the tick list"; the search index and the feed contain no goal; the Hiking page and the home tile count only active goals; no horizontal overflow at 390 px; no duplicate ids; the phone bottom bar reads Map · Notes · GPX. |
| Rendering | Not run (no new goals exist and render.py needs the internet); the segment-aware planned path is unit-tested at the geometry level and the existing planned render is untouched. |
| Not run | Lighthouse, screen readers, real devices, keyboard-only traversal, the pages with JavaScript disabled. The multi-lens review of this phase ran after the commit; see Review, which also records the 320 to 1440 px checks. |

### Review

Seven independent lenses read commit `a0eb1cd` (plan compliance, Python correctness, JavaScript behaviour, HTML and
accessibility, CSS and responsive layout, documentation accuracy, test quality) and returned 32 high or medium findings
and 30 low ones. Each high or medium finding went to skeptics told to refute it. The first verification run stopped
on a usage limit after 9 findings had their votes; the other 23 were handled on 2026-10-10: 7 were already fixed by
the follow-up commits, fixed directly, or duplicated a confirmed finding, and 16 went to a second run with two
skeptics each (one reproducing against the current code, one checking the plan and intent), with the fix itself as
the third look.

| Outcome | Count | What |
| --- | --- | --- |
| Confirmed and fixed | 19 | Listed below. |
| Fixed without a verification vote | 4 | The regex element extractor, the UTF-16 bypass and namespace-prefixed tracks (the follow-up commits); a byte order mark with `--select` (this round). |
| Rejected by the skeptics | 5 | No way to attach a GPX to a saved idea (the plan asks only that an idea can be saved without one); the planned map's accessible name (the named "Planned route map" region carries it); two test findings that judged the tests against the earlier commit; a test for the rendered-map branch of a goal page (not in the required list; the branch is unchanged code). |
| Split one to one, fixed anyway | 1 | Site wiring re-implemented by a test helper. |
| Duplicates of confirmed findings | 3 | The backlink (reported by three lenses) and the phone note (two). |

Confirmed and fixed:

- **Renderer.** `render.py` crashed on a published goal without a GPX (every later run failed, and a per-slug run
  deleted `rendered/site/` before failing); region maps crashed on a route-only goal and joined a multi-segment goal
  across gaps under 2 km. A goal without a route is now skipped (a render left from an earlier route is removed), and
  region maps read a goal like its own map does: routes and tracks, one line per segment, active goals only.
  `tests/test_render_goals.py` covers this with the drawing and OpenStreetMap functions stubbed. `render.py` itself was
  not run.
- **Counters and lists.** The About page counted completed and archived goals; the map page's region lists and the
  home region counts listed them. All use the active goals now.
- **Backlinks.** Multi-day and series reports named by an outing get the "On the tick list" line.
- **Provenance.** A planned route saved before the tick list no longer claims its GPX was "kept byte for byte"; a goal
  page keeps its approximate-values note on phones; a goal's numbers carry ≈ on every row that shows them (activity
  page, map page rows and table), with "High point" in place of "GPS max".
- **History.** A completed goal can be opened again without losing its outings: `update --reopen --status <status>`
  appends a dated "Reopened" entry, the goal page lists it, and a plain status flip is still refused.
- **Importer.** `--checked-at` no longer rewrites the route source's date when a reference is added (references have
  `--reference-checked-at`); timestamps with a negative UTC offset are recognised; the duplicate check also covers
  planned routes without a `goal.json`.
- **Tick list page.** Cards return in page order after switching sort away and back; an empty scope tab says what the
  tab holds instead of offering a dead "Clear filters"; a query of punctuation is not shown as a filter.
- **Documentation.** `--approximation-note`, the repeatable flags, the reference date, the exact duplicate rule, the
  export field list, what stops a multi-route import, what a chosen-element publish leaves out.
- **Tests.** The report recording's checksum is compared after `log-outing`; the build's own `site_of()` assembles the
  site in the tests; home tiles, the map head and the map's Planned group are covered for the active-only rule.

Low findings: 27 of 30 fixed (symlinked packet path, region sections sharing a slug, stricter numbers and empty
checklist text in `goal.json`, a traceback on a hand-edited `route_source`, an empty-slug message, the zero-goal page
state, the token-less search chip, the fallback wording that said "above", the one-item bottom bar (reported twice),
the fallback's spacing, a dead flex rule, tag sizes, a wrapping date, the placeholder contrast, four guide corrections,
five test gaps, the legacy list in `export`, what a chosen-element publish leaves out, the checks the log had not
listed as not run). The other three:

- Discovery (plan 20.2): planning notes are now searched; a tags filter and a time-commitment filter were not added
  (tags are searched). Recorded as a narrower scope.
- A copy-link action on goal pages (plan 20.9): added with the copy-link control in Phase 3.
- The checkbox finding described the earlier commit; the switch button was already in place.

Checks run for this round (2026-10-10): 480 tests OK; the ticklist.js harness 60 checks and the trips.js harness 50;
`build.py --out <scratch> --link --check` 348 pages, link check OK. On the synthetic demo site (now seven goals,
including one completed then reopened and one whose attempt names a multi-day report) in the built-in browser: no
horizontal overflow at 320, 390, 768, 1024 and 1440 px on the tick list, a goal page and the map page; one, two and
three card columns; the list view; the two failing sort sequences from the review restore the page order; empty scope
tabs on the real content read "Nothing shortlisted yet." and so on with no dead button; a filtered-empty state keeps
"Clear filters" and it works; planning notes are searched; the goal note shows on phones; an idea without a route has
no bottom bar. Not run: `render.py` (internet), keyboard-only traversal, the page with JavaScript disabled, Lighthouse,
screen readers, real devices.

### Remaining issues and author inputs

- No real goals exist yet: add the first with `python3 tools/ticklist.py add … --dry-run`, then publish by path.
- The header now has Tick list; the optional "On my list" home shelf (plan 20.9) was not added.
- Daily PCT search, collections and the local upload desk stay out of scope (Phases 3, 5 and the optional desk).
- The one existing planned route now shows "≈ 17.4 MI" on the map and Hiking pages and a plain statement that its
  GPX's source was not recorded. Running `tools/ticklist.py update crystal-range-to-bayview --source-kind …` gives it
  a `goal.json`; `export` names it until then.
- After logging a completion or archiving a goal, run `python3 tools/render.py --site` (internet) so the region maps
  drop its dashed line. The lists and counts change on the next build without it.
