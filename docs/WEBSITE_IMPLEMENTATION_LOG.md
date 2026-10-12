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
| Keyboard and link names (read from the markup, not walked) | Focusable links per card are chip, title and action (photo links `tabindex=-1`, `aria-hidden`); visible focus from `base.css`. Title links are described by their DATE · PLACE line (`aria-describedby`) and action links carry the trip title for screen-reader link lists. |
| No JavaScript (read from the markup, not run with scripting off) | The home page is static HTML; `site.js` only adds the phone menu and the unit toggle. |
| Page weight (estimate from built file sizes, not a measured transfer) | Phone picks (smallest srcset candidate per image): about 1.2 MB in total (HTML 205 KB, CSS 141 KB, JS 36 KB, images 826 KB), against about 0.9 MB before; within the plan's 1–1.5 MB budget. (Phase 4 measured it and the assumption did not hold: a 3x phone does not take the smallest candidate. The measured weights are in the report, 2.2.) The six recent-outing thumbnails take the 800 px copies (no smaller derivative exists yet; Phase 4 may measure whether one is worth adding). |
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
| `python3 -m unittest discover -s tests` | 436 tests OK at commit `dacc841` (188 at `a0eb1cd`; 188 from Phases 1–2 plus 248 for this phase: 54 GPX inspector, 72 goal sidecar, 52 importer CLI, 65 tick-list page / goal pages / boundaries, 5 Node wrappers; the ticklist.js harness runs 59 checks). The matrix covers plan 20.10's list: metadata-only idea, route-only GPX, multi-segment track (nothing bridged), alternatives needing `--select`, no / partial elevation, no timestamps, waypoint-only, sparse geometry, duplicate checksum, rejected inputs, dry run, byte-identical publication, failed render fallback, legacy planned route, status / reference / evidence rules, attempts before completion, completion without date or report, active counts, draft exclusion, read-only pages, goals absent from published / feed / search / features. |
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
- **What a published GPX carries.** An automated security review of the fix commit objected to a new report line that
  said a chosen-element publish does not copy "its metadata": the chosen track still carries its own name,
  description, links, extensions and timestamps, and the copy keeps the file's opening `<gpx>` tag (the `creator`
  text) and any comment before it. The importer now reads the list from the exact bytes it is about to write ("the
  published copy carries: …", including creator, names and description text) and says separately what was left out;
  the guide says the same. Four tests use a synthetic file full of personal-looking details. The review of that
  change raised two more points, both fixed: text from the file was printed as it came (a track name with a line
  break could forge a report line, and invisible characters could hide text), and the "nothing besides the geometry"
  line rested on a scan of known fields only. File text now goes through one escaping function (one line, quoted,
  bounded, control and formatting characters shown as `\uXXXX`), and the scan files every element and attribute as
  either geometry or a reported item (unknown elements, stray attributes, unnamed waypoints, named points, GPS
  fields, loose text, a track hidden inside a waypoint), so only a truly bare file is called bare; a missing scan is
  an error. Tests use a hostile but well-formed file. A further review pass found the inventory still missed free
  text outside elements and that names alone decided what counted as geometry. Namespace declarations (prefix and
  URI), a `version` that is not 1.0 or 1.1 and non-XML white space are now reported; only GPX-namespace elements are
  read as tracks, routes and points (a lookalike `trk` in another namespace is never a candidate and is listed as an
  unknown element); the escaping also covers stacked combining marks and right-to-left letters; and the bare-file
  line now says what it is, a scan result, and that the coordinates themselves are public.
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

Checks run for this round (2026-10-10): 493 tests OK (480 at the fix commit `029ad39`, 13 more with the published-copy report); the ticklist.js harness 60 checks and the trips.js harness 50;
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

## Phase 3 — Reports and PCT reading (2026-10-10)

Starting point: Phases 1, 2 and 2T committed on `phase1-curated-homepage`; `HEAD` was `282d0db` (the last of the
Phase 2T review commits). Baseline before this phase: 493 tests OK and `build.py --check` OK (348 pages). The content
relied on is the Phase 0 inventory: 156 single-day reports, 10 multi-day trips, one planned route and the PCT, which
has 150 recorded days, 32 of them written, and no parent write-up. Three trips carry `cover_photo` (the Phase 1 picks:
the PCT, Matterhorn Peak – West Couloir, PEAK BAGGING SZN). No journal highlights were supplied and no introduction
was written, so `journal_highlights` is not set anywhere and the PCT's introduction is built from fields. No copy was
written for any page, and nothing under `content/` or `rendered/` changed.

### Changed files

| File | Change |
| --- | --- |
| `tools/lib/content.py` | `t['journal_highlights']`: `journal_highlights: [001, 059]` resolved to the day dicts in the listed order (a number is padded to the width of the day file names); `[]` when absent or empty; a value that is not a list, a non-empty list on a trip that is not `kind: series`, an id with no day file, or a repeat is a `ContentError` naming the file. `LEAD_MIN_AR` (1.2) and the automatic cover pick that uses it: the first photo at least 6:5 wide, else the first at least as wide as tall, else the first photo. No real trip's cover changed. `day_anchor()`; a day's label is its `day:` as text (`0` included), else its position; two days of a journal with one anchor, or a label with no letter or digit, is a `ContentError` naming the day file. |
| `tools/lib/icons.py` | The `link` icon for the copy-link control. |
| `tools/sitegen/core.py` | `related()` and `related_block()` ("More like this", with `skip` for the reports a page already links), `RELATED_SIZES`, `copy_link()` (with `of` for a per-control accessible name); `photo_rows(lead=)` numbers unnamed grid photos as the viewer does; a card's place may wrap; `recorded()`, the opening item of every map caption; `photo_rows` sums aspect ratios with `math.fsum` so Python 3.9 and 3.12 print the same value. |
| `tools/sitegen/pages/report.py` | `narrative()`, `lead_photo()`, `hero()`, `section_nav()`, `share_row()`, `neighbours()`, `HERO_SIZES`; `page()` builds the story order or the compact order, takes the lead photo out of the gallery (it carries a `#photos` target when no photo remains for a grid), preloads the cover in place of the map when there is a lead photo, and appends the share row and the related block; `bottom_bar(story=)`; `map_caption` opens with "As recorded on <date>"; `data-lb-group="photos"` on the gallery; the share image is the cover; the copy-link action and share row on goal pages. The rail's old Contents list is removed: no page could show it once a report with a write-up and photos became a story. |
| `tools/sitegen/pages/multiday.py` | Copy-link as the last title action; the share row and the related block before the pager; the overview caption opens with "As recorded <date range>" (no such item without dates); `share_image()`: the cover. |
| `tools/sitegen/pages/series.py` | The lead photo and its preload; `lede()` opens with a facts sentence, has singular forms and leaves out a missing date range or place; the actions "Read the first written entry" and "Browse all recordings" and the copy-link control in place of "Day by day"; `first_written()`, `highlights()`, `written_nav()`; `day_anchor()` is safe for any label; `data-default="wu"` on the write-ups toggle; the map caption opens with "As recorded <date range>". |
| `tools/sitegen/pages/section.py` | The featured map's caption opens "As recorded on <date>" like every other map caption. |
| `tools/sitegen/search.py` | `day_entry()` and `build_day_index()`: one entry per day of a published journal (`kind: series`), with the journal's slug, title and aliases, the day's label, anchor, title and date, and the day's write-up. The trip index is unchanged. |
| `tools/sitegen/pages/trips.py` | `journal_block()`: the empty, hidden "Journal days" section after the results; `build()` writes `trips/journal.json` when the site has a journal. |
| `assets/js/base.js` | The copy-link handler (clipboard, "Link copied" for four seconds, else a selected read-only field that closes on Escape, a second press or a press elsewhere); photo viewer groups by `data-lb-group`; the current-section marker is the phone bottom bar's alone, and a pressed link stays current until the page scrolls on from where the jump put it. |
| `assets/js/pages/series.js` | `hashTarget`, `startFiltered`, `revealId` and `landAfterLoad`, exported for Node; the write-ups filter starts on; the reader's own choice is kept in `sessionStorage` for the tab; a hash that targets a hidden day or month keeps the filter off on load and turns it off on `hashchange` or when its link is followed again; a page opened by a link that ends filtered scrolls to its day or month target again (not once the reader has scrolled on), a reload or Back does not; "Browse all recordings" turns the filter off and is remembered. |
| `assets/js/pages/trips.js` | Fetches `journal.json` with the first query; `dayHits`, `dayMeta`, `dayHref`, `dayText` and the count, list, waiting and message helpers (exported for Node); lists matching journal days under "Journal days", five at first, filtered like their journal's card; the status line is written once both indexes have answered and links to the list; a jump to a fragment is no longer read as a change of view; an empty sorted section is hidden. |
| `assets/css/pages/report.css`, `series.css`, `trips.css`, `base.css` | The story layout (`.rep-hero`, `.rep-anchor`, `.rep-toc`), `.rep-rel`, `.rep-share`, the copy control (status and fallback field out of the flow; hidden when scripting is off); `.ser-high-*`, `.ser-wnav`, the journal's title actions under its title; the journal-day rows. `.rep-toc` is hidden under 760 px and `.rep-share` is shown only there. The `.rail-toc` rules are gone with the list. |
| `docs/CONTENT_GUIDE.md`, `docs/DEVELOPING.md`, `README.md` | Section 7 "Report pages and the PCT journal", the "Journal days" paragraph in the search section, four error-table rows, the "What not to do" bullets; the developer rules for both layouts, related reports, the copy control, the journal page and the journal-day index; two README rows. |
| `tests/test_report_page.py`, `tests/test_related.py`, `tests/test_series_page.py`, `tests/test_series_js.py`, `tests/series_js_harness.js`, `tests/test_journal_days.py` (new) | See Checks. |
| `tests/test_search.py`, `tests/test_trips_page.py`, `tests/trips_js_harness.js`, `tests/test_cover.py`, `tests/test_cards_extra.py` | The journal-day index, `trips/journal.json`, the Journal days block and the journal-day helpers; the automatic cover pick; the card's place line and the section page's caption. |

### Behaviour

- A single-day report with a write-up and a photo gets the story layout: the title block ("View route", "Download
  GPX", "Copy link"), the lead photo, the stats strip, a section row listing only the sections the page has (Report,
  Photos, Route, Trip details, in the plan's order), the write-up beside the Beta block, the map, the profile, the
  remaining photos, the related reports, Newer / Older. Track-only, photo-only and no-photo reports keep the compact
  map-first order. Both layouts keep `#title #stats #map #profile #beta #report #photos` wherever the section exists;
  when the lead photo is a story's only photo, `#photos` lands on the lead photo.
- The lead photo is the trip's cover (`cover_photo`, else the automatic pick) when it is at least 6:5 wide. It is left
  out of the Photos grid and shares the viewer with it: the viewer steps through every photo of the trip once, lead
  first. A cover that is a portrait or nearly square does not lead: the page keeps the story order and its photos stay
  in the Photos section, or, for a single portrait, beside the write-up. The write-up is rendered word for word and no
  copy is generated on either layout.
- Multi-day pages keep their map-first layout in this phase (no lead photo, no section row). They gained the copy
  link, the related reports and the caption wording only.
- Map captions open with when the track was recorded: "As recorded on <date>" on single-day reports and on the
  section pages' featured map, "As recorded <date range>" on multi-day trips and the PCT, and no such item when the
  trip has no date. Goal captions are unchanged.
- "More like this" shows up to three other published reports on single-day and multi-day pages: same region and
  activity first, then same region, then same activity, the nearest in date first within each. Never the report
  itself, a planned route, a draft or a repeat, and never the two reports the page links as Newer / Older just below;
  omitted when empty; not on goal or series pages. The rule is printed beside the heading, and ends "NEWER / OLDER NOT
  REPEATED" when one was left out.
- "Copy link" copies the page's absolute public URL. It is the last title action on single-day, multi-day, goal and
  series pages. Single-day, multi-day and goal pages hide their title actions under 760 px, so a second control near
  the end of the page is shown there. On success "Link copied" shows under the button for four seconds; when the
  clipboard is unavailable the URL is shown there in a selected read-only field. Neither moves anything on the page;
  a button at the bottom edge of the screen has them scrolled into view. With scripting off the control is not shown,
  in browsers that know the `scripting` media feature.
- The phone bottom bar of a story page reads Report, Map, Photos, GPX, or Beta, Report, Map, GPX without a Photos
  section, or Report, Map, Profile (Speed, Stats), GPX with neither photos nor beta rows. The compact bar is unchanged.
  The bar marks the current section, and a link the reader pressed stays current until the page scrolls on. The section row
  is not sticky, carries no current marker, and is hidden on phones, where the bottom bar is the one section navigation.
- PCT: the page opens with the cover as a lead photo. The introduction is one paragraph from fields and counts until
  `index.md` has a write-up, which then replaces it. The actions, under the title, are "Read the first written entry",
  "Browse all recordings" and "Copy link". Every written entry ends with "Previous write-up" and "Next write-up" links
  to the nearest written days (anchors from `day_anchor`, so Day 5.2 is `#day-5-2`) and "Copy link to this entry", which
  names its day for assistive technology. `journal_highlights` renders a Highlights section between the overview and
  the day log when set and nothing when absent. The build refuses a journal in which two day labels give the same
  anchor.
- PCT reading mode: with JavaScript the day log starts on the days with write-ups, and the reader's own choice (the
  toggle, or "Browse all recordings") is kept for the browser tab. A page opened with a hash that targets a track-only
  day or a month without write-ups starts unfiltered; a link to such a target turns the filter off, announces
  "Showing all N days" and scrolls to it, also when the URL already ends with that hash. A reload or Back returns the
  reader to where they were, not to the hash. Month browsing, the all-recordings view, every `#day-…` and `#month-…`
  anchor, the GPX links and their file names are unchanged, and no day pages were created. Without JavaScript every
  day shows.
- Journal-day search: a search on the Trips page also reads every day of a journal (`trips/journal.json`: the PCT's
  150 days, 95 KB, 19 KB gzipped, fetched with the first search) and lists the matching days under "Journal days"
  after the reports, each naming its journal, day and date and linking to that day's anchor on the journal page. A day
  is found by its own title and write-up ("whitney" finds Day 48, a track-only day titled "Mount Whitney") or by
  naming it ("day 100"). The journal's name and aliases never find a day alone, but may be typed with something of the
  day's own ("pct whitney"). The status line counts the days and links to the list. Five show at first; the filters
  apply to a day as to its journal's card, and "Has a write-up" also to the day itself. Multi-day trips stay whole in
  the trip index. A journal index that fails to load costs only the day results.
- The share image of every trip page with a cover is the cover. Against the build from before the phase it changed
  on 16 pages, each from the trip's first photo to its cover.

### Checks actually run

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` | 930 tests, OK (493 before the phase). |
| The same suite under Python 3.12 (`python3.12 -W error::DeprecationWarning`), the version CI uses | 930 tests, OK. |
| Node harnesses | `trips_js_harness.js` 89 checks, `series_js_harness.js` 43 checks and 25 more when `test_series_js.py` gives it a generated journal page to run the whole script against, `ticklist_js_harness.js` 60 checks. All pass. |
| `python3 tools/build.py --out <scratch> --link --check` | OK: 349 pages, 168 trips, every internal link, image and anchor resolved. |
| Builds under Python 3.9 and 3.12 compared file by file | Identical. One fix was needed on the way: `sum()` of photo aspect ratios rounds differently in 3.12, which changed one printed CSS value on one page; `math.fsum` gives the same value in both. |
| Output compared with the build from just before this phase (3,297 files, leaving aside the iCloud conflict copies a local build carries) | No path removed; one added (`trips/journal.json`). All 351 GPX downloads byte-identical. `feed.xml`, `sitemap.xml` and `trips/search.json` identical. Write-up text identical on all 347 HTML pages. No legacy anchor lost: `#title #stats #map #profile #beta #report #photos #days #overview` are present wherever they were, and the PCT keeps all of its `#day-…` and `#month-…` ids, `#day-5-2` included. Two internal heading ids are gone: `toc-h` on 53 pages (the removed Contents list) and `ph-h` on the 12 pages whose only photo became the lead photo (their `#photos` target moved onto it). |
| Layout census in the built site (156 single-day reports) | 45 story pages with a lead photo (on 12 of them it is the only photo); 16 story pages without one (8 with a single portrait beside the write-up, 8 whose photos are all portraits or squares); 95 compact pages. |
| Covers before and after the automatic-pick change (168 trips) | No trip's cover changed. |
| Horizontal overflow, measured in the browser | All 167 published trip pages at 320 and 1000 px, and 21 other pages (home, Trips with three queries and in list view, Tick list, Map, About, the goal, the PCT, a multi-day trip, four reports, the five activity pages) at 320, 390, 768, 1024 and 1440 px: the page is never wider than the window. |
| Copy link in the browser (journal, a story, a multi-day trip, the goal, Matterhorn; 320 to 1440 px) | With "Link copied" showing, the scroll position, the page height, the H1 and the button do not move, and the status stays inside the page. With the clipboard stubbed to succeed the handler wrote the control's URL; stubbed to fail, the read-only field appeared with the address selected, inside the page gutters, with no sideways scroll; Escape closed it and returned focus to the button; a press elsewhere and a second press closed it. With the phone button 6 px above the bottom bar the field was scrolled clear of the bar, and an entry button at the bottom edge of a desktop window had its status scrolled into view. A real clipboard write was not observed: the test browser refuses them. |
| Section navigation in the browser | The section row never carries a current marker, before or after scrolling. On a 390 px page the bottom bar starts on Report; each pressed link becomes and stays the current one after the jump and through a 4 px drift; a scroll to the top with no wheel, touch or key event releases it; Back moves the marker to the earlier fragment; after a second press of the link already in place, one 300 px step moves the marker on. |
| PCT page in the browser | The title is on one line from 800 px with the three actions under it; at 390 px the first action fills the row and the other two share the next. Opened at `#day-3` the page lands on Day 3 with the filter on; after scrolling to 9,000 px and reloading it was still at 9,000 px. A link to hidden Day 25 turned the filter off; with the filter turned back on, a second link to the same hash turned it off again and announced "Showing all 150 days". "Browse all recordings" stored the choice with the filter already off. The 32 entry copy buttons have 32 different names. With one image answered 1.5 s late, a reader who scrolled on before the page finished loading stayed where they were; one who waited stayed on the entry. |
| Journal-day search in the browser | "pacific crest trail": the PCT's card and no journal days. "pct whitney" and "pacific crest trail 2024 day 48": Day 48, a track-only day. "day 100": Day 100 first. "day 5.2": Day 5.2, then Day 5. "whitney" with "Has a write-up": no day. "tent" at 320 px: 11 days, five shown, no snippet cut off when all are shown; a new query entered with Enter went back to five. On a first search with either index answered 600 ms late the status line was written once and "No trips match" did not appear before the days did. The status link scrolled to the list, moved the focus to its heading and left no fragment in the address; after it, and after a jump to a year heading (also with an apostrophe in the query), clearing the search returned the sort to Newest first. With the journal index never answering, the note read "Loading search…", the request was given up after 8.2 s, and the count and the empty state then appeared. Under Node, over the real index: "day N", alone and after the journal's name, lists the named day first for all 150 days. |
| Rendering | Not run. `render.py` needs the internet and this phase changes no track, title or `map:` setting; `git status` shows no tracked change under `rendered/` or `content/`. |
| Not run | A real clipboard write; the pages with scripting off (the rule that hides the copy control is in the built CSS and parsed by the browser, but the state was not loaded); keyboard-only operation by hand; 200 % zoom; reduced motion; Lighthouse; screen readers; real devices. The test browser's pane was hidden during these checks: layout was measured and events were dispatched by script, so real wheel and touch scrolling, the viewer's focus return and a visible window were not observed. The page code of `base.js` and `trips.js` has no automated test. Most of its decisions are pure functions that the Node harness runs; four rules of `trips.js` are not, and were checked in the browser only: the status line and the empty state waiting while a search is pending, the status link followed by script, and the `popstate` guard. `series.js` is also run whole against a stand-in for the browser, which is not a browser: a property it does not model reads as undefined instead of failing the run. |

### Review

The phase went through two review rounds before it was left for commit. Reviewers and skeptics were read-only; every
fix was made afterwards and re-checked.

**First round: seven lenses over the whole phase** (plan compliance, Python, JavaScript, HTML and accessibility, CSS
and responsive layout, documentation, test quality). 57 findings: none high, 11 medium, 46 low (two of the low entries
were a lens's "requirements met" summary). One medium was a duplicate; the other ten each went to two skeptics, one
told to reproduce it and one to judge it against the plan and the contract.

| Verdict | Count | What happened |
| --- | --- | --- |
| Confirmed by both | 3 | Fixed: "Link copied" re-wrapped the title on 65 of 168 pages at 1000 px (the status now hangs under the button); the two-line clamp hid the matched words of a journal hit on phones (removed); the guide described a near-square cover as a lead photo (rewritten, and the automatic cover now prefers a photo at least 6:5 wide). |
| Split | 6 | All six fixed. Every written day matched its journal's name, and "day 2" ranked Day 2 twenty-first (new matching and ranking; the list moved below the reports). A reload threw the journal reader back to the entry in the URL. The section row marked "Trip details" as current at the top of the page (the row no longer carries a marker). Three test weaknesses: a substring check of the journal script, a share-image test that passed by coincidence, and "write-ups verbatim" not pinned on the journal page. |
| Rejected by both | 1 | "No automated test runs the page scripts' DOM code." Not required by the plan, which asks for unit tests of pure logic and browser checks of interaction. The decisions those scripts take were still moved into pure functions and tested under Node. |

Low findings fixed in the same pass: the copy control without JavaScript and its per-entry names; the fallback field
squeezing the title row; the journal's title wrapping beside three buttons; "More like this" repeating the Newer /
Older links on 155 of 167 pages; 23 titled track-only PCT days that could not be found; a highlight printing an
untitled day's date twice; captions and sentences for trips without dates; the section pages' "Track: <date>" caption;
unescaped day anchors; grid photo labels that disagreed with the viewer's count; "Show all" staying open for a new
query; the search-failure message over working journal results; "Browse all recordings" not remembered; a repeated
link to a hidden day doing nothing; a card's place line widening four report pages at 320 px; dead CSS; stale
developer notes; and the test gaps the test-quality lens listed. Recorded, not built: multi-day pages keep their
map-first layout (Remaining issues).

**Second round: four lenses over the fixes** (JavaScript, CSS and accessibility, Python, plan and intent), again with
two skeptics for anything medium or higher. 19 findings: none high, one medium, 18 low.

- The medium one split and was fixed with the reproducing skeptic's stricter rule: after the first round a query such
  as "pct whitney" or the very words a result row prints ("Pacific Crest Trail 2024 · Day 48") found nothing. The
  journal's name and aliases may now accompany something of the day's own, as whole words, and still find no day
  alone. On the real index "day N" and "Pacific Crest Trail 2024 day N" list the named day first for all 150 days.
- Low findings fixed: every journal day is indexed, so "day 100" finds Day 100; "Has a write-up" no longer lists
  track-only days; the status line is written once and "No trips match" no longer flashes while the journal index
  loads; its link to the list no longer leaves a fragment in the address or makes the automatic sort stick; the
  journal's second landing yields to a reader who has already scrolled; the copy status and field are scrolled into
  view at the bottom edge and above the phone bar; the bottom bar's pressed link is released by any scroll, not by
  four input events; two days of a journal can no longer share an anchor, and `day: 0` is a label; a one-day journal
  says "1 recorded day" and "As recorded on"; the "More like this" rule line says when Newer / Older were left out;
  three sizes (the phone gap above the write-up, the "Route" link, the fallback field).
- Not changed: two trips whose share image is now a weaker photo than before (an author choice, under Remaining
  issues); file handles left to the garbage collector in six older `json.load(open(...))` calls (Phase 4); a goal
  page's share image, which stays its first photo.

**Third round: three lenses over the second round's fixes, the tests and the three guides** (JavaScript and CSS,
Python and tests, documentation). 15 findings, all low; nothing went to a skeptic. Fixed: the fragment-jump guard
missed any query with an apostrophe; the status line could wait on a stalled journal index with nothing saying so
(a "Loading search…" note now stays up, and the request is given up after 8 s); a second press of a bottom-bar link
already in place kept the marker through the next move; the day's name typed twice found other days; a day label
such as "5 n" could take the id the page writes on Day 5's number; a day file without a `day:` line that collides on
the PCT is now told so; a test fixture used the wrong `kind` for a multi-day trip; "nothing is announced on load" had
no check; raw non-breaking spaces in two test files; four statements in the guides (the Ski page has no featured
map, the facet checklist, the README's cover row, unlabelled days on the PCT). The same reviewer ran the suite five
times under each Python, in reversed and shuffled order and one test at a time, without a failure. Not changed: the
browser stand-in's leniency about unmodelled properties (noted under Not run).

The reviewers' independent comparisons with the build from before the phase agree with the table above: no path
removed, 351 GPX files byte-identical, no write-up changed, no legacy anchor lost.

### Remaining issues and author inputs

- Lead photos are not yet Eric's choices. The PCT leads with the Phase 1 pick (`cover_photo: photos/d059-01.webp`,
  focal 45 / 55), still waiting for confirmation. Every single-day report without `cover_photo` leads with the automatic
  pick (the first photo at least 6:5 wide declared in `index.md`); only the three Phase 1 trips have the line. Set
  `cover_photo` and the focal point on the reports that matter (CONTENT_GUIDE section 7.3).
- Sixteen written reports have no lead photo because no photo of theirs is wide enough: eight with a single portrait,
  eight with only portraits or squares. Adding a landscape and naming it in `cover_photo` gives them one.
- `journal_highlights` is empty, so the PCT page has no Highlights section until Eric lists the entries he wants to
  point to (day-file ids, display order; section 7.8). No entry was chosen for him.
- The PCT introduction is facts only until Eric writes one under the front matter of its `index.md` (section 7.7).
- Multi-day pages keep their map-first layout. Giving them a lead photo and a section row is a design decision for a
  later phase, not something this phase attempted.
- Two share images are now a weaker picture than before, because the automatic cover is the first wide photo:
  Tumalo Falls (the waterfall portrait gave way to a trail through pines) and the LTCC multiday ski class (skiers
  gave way to the inside of a tent). The same photos have fronted those trips' cards since Phase 1; naming a
  `cover_photo` on each fixes both.
- A day added to the PCT needs a `day:` line. Its labels do not follow the file order (`days/148.md` is Day 151), and
  `add_trip.py --day-of` writes none, so the new file would take a position another day already uses as its label; the
  build now stops and says so (CONTENT_GUIDE section 7.7).
- Day search covers journals (`kind: series`, today the PCT) and lives in the Trips page's search box only. An
  untitled track-only day is found by its name alone ("day 100"), multi-day trips are searched as whole reports, and
  no day pages exist or should be added for search.
- For Phase 4: six older `json.load(open(...))` calls leave the file to the garbage collector (`core.py`, `archive.py`,
  `multiday.py`, `series.py`, `section.py`); harmless in a build, a `ResourceWarning` under `-W error`.
- No Phase 5 features were added: collections, region pages, a verified summit index, the local "Continue reading"
  bookmark and the interactive map stay out of scope.

**Next smallest step:** Phase 4 (hardening, performance measurements, share metadata, structured data where the
content supports it, the remaining manual checks).

## Phase 4 — Hardening, performance, metadata and handoff (2026-10-10)

Starting point: Phases 1, 2, 2T and 3 committed on `phase1-curated-homepage`; `HEAD` was `6f6091d`. Baseline before
this phase: 930 tests OK and `build.py --check` OK. No copy was written for any page, no trip fact was added, and no
tracked file under `content/` or `rendered/` changed. The 105 new `content/trips/*/photos/*.th.webp` files are
derivatives of existing photos. `tools/render.py` was not run. Nothing was pushed or deployed. The final
report is `docs/IMPLEMENTATION_REPORT.md`; this entry records what changed and what was run.

### Changed files

| File | Change |
| --- | --- |
| `tools/lib/checks.py`, `tools/validate.py` (new) | The content validator. `checks.run()` returns findings (`error`, `warning`, `note`) for every trip folder, `content/home.json`, goal outings, write-up links and the pre-rendered site maps, and never raises on content. `validate.py` prints them (`--strict`, `--json`, `-q`, `-v`, `--content DIR`, `--site DIR`, `--today`); exit 0, 1 or 2. |
| `tools/sitegen/sitecheck.py` (new) | The built-site checks behind `build.py --check`: the old link, anchor and duplicate-id rules with their exact lines, plus `META`, `SITEMAP`, `FEED`, `INDEX` and `GPX` lines. Reads a build once (about 1 s for the real site); hostile or malformed files give lines, not exceptions. |
| `tools/build.py` | `main(argv)`; content is validated before the output folder is touched (errors stop the build, the first 10 warnings print); `check()` wraps `sitecheck`; `--only` rejects unknown modules; `unsafe_out()` refuses an `--out` that is the checkout, inside its source folders, a file, or a non-empty folder that is not an earlier build; `.nojekyll` is written first; `strip_css_comments()`; conflict copies under `rendered/` and `assets/` are left out; drawings and map renders are copied only for a trip with a track; the combined multi-day GPX is written exactly when the page offers it, keeps line endings and `xmlns:` prefixes (`gpx_root_tag()`), and is never written through a `--link` symlink. |
| `tools/lib/content.py` | `published_at` / `updated_at` (`_publication`): a date or a date-time with an offset, kept as written; refused when malformed, in the future (except on a draft), before the trip's first day, on a planned route, or when `updated_at` stands alone or precedes `published_at`. Photo dicts gain `th`. |
| `tools/lib/frontmatter.py` | Numbers are ASCII digits only. |
| `tools/lib/photos.py`, `tools/thumbs.py` (new) | The card-size `.th` copy (320 px on the short edge, colour profile kept): `thumb_size`, `thumb_copy`, written by `web_copies` for new photos and by `thumbs.py` for existing covers. `thumbs.py` only adds files beside photos in `photos/`, skips what it cannot read and says so. |
| `tools/sitegen/core.py` | Share tags (`share_photo`, `site_share`, `_share_tags`), `written_report`, `blog_posting`, `document(report=, canonical=)`; `has_track`, with `render_meta` and `_drawing` answering "nothing" for a trip without a track; `summary` and `stats_note` claim a recording only when there is one; `PHONE_SLOT`, `PHONE_FULL`, `PHONE_SHAPES`, `phone_sizes`; the `.th` copy offered to phones only, in a `<picture class="cover-pic">` source around a card cover whose `<img>` is unchanged (`_cover_srcset`, `_card_source`, `cover_img`); `photo` sized only with both dimensions; `reveal`; `read_json`; "Multi-day · 1 day". |
| `tools/sitegen/pages/report.py` | `published_line`; the GPX action and bar item only with a track; a report without a track has no map section, no "View route", no Route or Map item, no full-screen map page, and no stats strip when it has no stats; the bar is omitted below two items; the beta Track row stays when there is no stats note. |
| `tools/sitegen/pages/multiday.py`, `series.py`, `section.py`, `home.py`, `about.py`, `archive.py`, `trips.py`, `ticklist.py`, `notfound.py` | Share image and `report=` where they apply; "Download all GPX" only with a day track; the journal description says "for every day" only when true; the section page features only a report with a track, links `#featured` only when the block exists, and promises a track only when every report has one; the search forms are revealed inline; the 404 page passes `canonical=False`; the About page's sentence about the units switch is its own element. |
| `tools/render.py` | `no_track()`: a report without a track is skipped, its stale render folder removed, and it is left out of the region maps while its region stays listed. Not run; covered by `tests/test_render_goals.py` with the drawing code stubbed. |
| `tools/add_trip.py`, `tools/ticklist.py` | `add_trip.py`: a placeholder Strava id in the help, a usage error for a wrong export folder or unknown id, clearer next steps after `--day-of`. `ticklist.py add`: the closing line names the render folder only when it exists, and says when no map was drawn. |
| `tools/privacy_audit.py` (new), `docs/PRIVACY_NOTES.md` (new) | A read-only audit of what the published tracks, photos and repository files add up to. The default report prints counts only and nothing about a single track or place; `--list` is for the author and refuses to print anywhere but a terminal. The notes state the observations and the decisions that are the author's. |
| `assets/js/base.js`, `pages/section.js`, `pages/trips.js`, `pages/ticklist.js` | Cluster markers take no focus; the copy-link fallback closes on focus leaving or Escape and returns focus to its button; the section filter band becomes a `div` radiogroup without losing focus; the explorers adopt what was typed or chosen before the script ran (`adoptForm`, `ownSort`) and ask for a failed search index again (`stillFailed`, `mayLoad`); `facetOk` and `goalShown` exported. |
| `assets/css/base.css`, `pages/*.css` | The no-JavaScript header (dead controls hidden, links wrap, not sticky on a phone); 44 px targets (the filter chips as boxes, the rest as hit areas that change no box); `picture.cover-pic` has no box; scroll margins under the second sticky bar; the multi-day day bar is static in a short window; the footer reserves bar space only when there is a bar; forced-colours rules for the units switch and the Map legend; `.rep-pub`. |
| `.gitignore` | iCloud conflict copies under `rendered/` and `assets/`. No tracked file is ignored. |
| `README.md`, `ADDING-TRIPS.md`, `docs/CONTENT_GUIDE.md`, `docs/TICK_LIST_GUIDE.md`, `docs/DEVELOPING.md` | Corrected by following them literally on scratch content; see the report, section 5.4. |
| `docs/IMPLEMENTATION_REPORT.md` (new) | The final report. |
| `content/trips/*/photos/*.th.webp` (105 new files, 2.2 MB) | Card-size copies of the covers that had none, made by `tools/thumbs.py`. |
| Tests | 16 new test files; 11 changed ones and the two Node harnesses; see Checks. |

### Behaviour

- **Validation.** `python3 tools/validate.py` lists every content problem, one line each, and the build runs the same
  rules first: an error stops it before the output folder is touched, a warning does not. Errors are broken explicit
  values and values the generator cannot read (wrong types, missing files, bad dates, a day file's iCloud copy,
  day files with no recorded track). Warnings are incomplete optional metadata and things the author should look
  at (a report without a track, a trip the pre-rendered maps still draw after it was drafted or removed, an unknown
  key, a key written twice). Notes count absent optional fields.
- **Site check.** `build.py --check` prints `BROKEN`, `BROKEN ANCHOR` and `DUPLICATE IDS` lines as before, and `META`,
  `SITEMAP`, `FEED`, `INDEX` and `GPX` lines for the new rules, then the same `link check:` summary.
- **Share metadata.** A page that shows a trip shares the trip's cover with its recorded size and description; Home,
  About, Map, Trips and the Tick list share the first featured trip's cover; a report without a photo shares none.
  A published report with at least 100 characters of write-up carries one `BlogPosting` block. `published_at` and
  `updated_at` are shown and written only when the author sets them. The feed and the sitemap are unchanged.
- **Photos.** On phones a full-width landscape photo of ordinary shape loads its 800 px copy; portraits, squares and
  panoramas are told the real width. On phones a card loads a 320 px copy where one exists; from 560 px up a card
  loads exactly what it loaded before the phase. A lead image and its preload always
  name the same candidates.
- **Search forms.** On Trips and the Tick list the form is in place at first paint, and what a visitor types or
  chooses before the script arrives is kept. With JavaScript off the form stays hidden behind the existing note.
- **A report without a track** (none exists) has no map, profile, route drawing, download or route link, promises
  none in its description, and has no stats strip when it has no stats. A track that is removed takes its renders
  off the site at the next build; the shared region maps keep its line until `tools/render.py` is run, and the
  validator says so.
- **Accessibility.** In the walks no focused control was under a sticky bar; hidden map markers take no focus; the copy-link fallback
  behaves under Tab and Escape; with JavaScript off the header shows only working links, all of them; the targets
  the walks found small are 44 px.
- **Tools.** `--out` cannot empty the checkout or a folder that is not a build; `--only` rejects unknown modules;
  `add_trip.py` and `ticklist.py` say plainly what to do next and what was not drawn.

### Checks actually run

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` | 2,021 tests in 36 files, OK (930 before the phase), on Python 3.9.6 and 3.12 with `-W error`. |
| Node harnesses | `trips_js_harness.js` 125 checks, `series_js_harness.js` 43, `ticklist_js_harness.js` 85. All pass. |
| `python3 tools/validate.py` on the real content | 0 errors, 1 warning (the planned route without `goal.json`), 467 notes; 168 trips, 398 declared photos, 341 GPX files. |
| The 187 malformed inputs of the groundwork | Before: 31 tracebacks, 52 clear errors, 18 caught only by the link check, 86 accepted. Now: 133 errors, 32 warnings, 2 left to the site check, 20 accepted as legitimate. Kept as a test table. |
| `python3 tools/build.py --out <scratch> --link --check` | OK: 349 pages, 168 trips, about 4 s. |
| A copying build (no `--link`) with `--check`, and `validate.py --site` on it | OK, `site: 0 problems`. All 341 published single and day GPX files are byte for byte their sources; the 10 combined files hold every day's tracks unchanged. |
| Builds under Python 3.9 and 3.12 compared file by file | Identical. |
| CI rehearsal: a copy of exactly the 5,198 files the commit holds (taken from the staged index), on a case-sensitive volume, Python 3.12, `TZ=UTC`, `LANG=C`, with nothing on the path but Python (no `node`, `git`, `cwebp` or `sips`) | 2,021 tests OK (25 skipped, the Node-dependent ones); `build.py --check` OK; the 3,403 files of the output are identical, file for file, to the build that was measured. It ran on macOS, not Linux, and the CI job itself has not run, since nothing was pushed. GitHub's runner has Node (22 on `ubuntu-latest`), so the 25 tests skipped here will run there; see the review gate entry. |
| The final build against the build of `6f6091d` | No path removed; 105 added (the `.th` copies). All 351 GPX files, the feed, the sitemap, `robots.txt` and both search indexes identical. Titles, canonicals, descriptions and write-up text identical on all 347 pages; no id lost. 163 pages differ in their HTML (share tags, structured data, photo `sizes`, the phone-only `<picture>` source around card covers, the inline reveal). Every `<img>` of a card cover is what it was. |
| The final build against the original site (`a9baab9`) | See the report, section 5.3. |
| Page-load measurement, three builds, nine pages, phone and desktop profiles | See the report, section 2. The after build was measured three times (36 cold loads each); the last set, on the final code, is the one reported. |
| Lighthouse, 12 pages, mobile and desktop, before and after | Accessibility, best practices and SEO 100 on every page, except one mobile run of the Map page (SEO 92, a `robots.txt` timeout of the local server; two repeats 100). The after pass ran on the working tree of the afternoon, before the last fixes; see the report, 2.7. |
| Before and after screenshots, 36 views (12 pages at 1440 px, 390 px and 390 px at the bottom), compared pixel by pixel | Final build against the captures made before the phase: 31 identical; 2 differ where intended (the `All` chip 6 px wider on phones, the Trips placeholder ending in an ellipsis); 3 differ in pixel values only, and for those a fresh cold capture of the build before the phase is pixel-identical to the final build. See the report, 5.2. |
| Browser walks with real key presses | Two full walks (before the phase and after its first round), then targeted re-checks of the later fixes; see the report, 5.2. |
| Author docs followed literally in scratch copies | Three writers, three independent readers, three fix passes, then a final pass against the frozen code; see the report, 5.4. |
| Mutants | Most new test groups were checked by applying single-line changes to the rule on a scratch copy: validator 166 (165 killed, 1 equivalent), site check 110 (109, 1 equivalent), privacy tool 120 and later 50 (all killed), page and metadata tests 130 (all killed), thumbs, filters and static accessibility 120 (119, 1 equivalent), the no-track rules 41 and 49 (all killed but 1 equivalent), JavaScript and CSS fixes 58 (all killed), the phone-only card copy 19 (all killed), the hit areas 28 and 3 (all killed). |
| Rendering | Not run. `tools/render.py` needs the internet and rewrites committed assets. No tracked file under `rendered/` changed. |
| Not run | Safari and Firefox; real phones; screen readers; true forced-colours themes; a real share preview; field performance. See the report, section 4. |

### Review

- **Groundwork before any change**: five read-only audits (validation, metadata, loading, privacy, author docs) and
  four measurement and browser passes on the builds before the phase. Each proposed change had to cite what was
  observed.
- **Round 1: eight reviewers by lens** (metadata truth, capability and compatibility, loading, accessibility, site
  check, privacy, hostile input, Python versions and CI). Seven reported 36 findings, each with a reproduced failing
  example: 1 high (the missing Git index, an incident and not a code defect), 9 medium, 26 low. The eighth and the
  planned skeptic stage were stopped to free disk space (see below), so the coordinator reproduced or read each
  finding instead. Fixed: all 9 medium and 23 of the 26 low ones. The three left concern pages for content that
  does not exist (a multi-day trip or a journal with no day track at all, a report whose track is not rendered
  yet); they are in the report's section 10.
- **The docs readers** found a further set of tool gaps by following the guides literally (a day file's iCloud copy
  published as a day, `--out` able to empty any folder, a traceback on a wrong Strava export, the tick-list tool
  naming a folder that did not exist). All fixed.
- **Comparing screenshots found what the tests could not.** The first after-set, laid beside the before-set, showed card
  photos softer on a 1x desktop screen (the 320 px copy drawn in a 400 px slot) and five 44 px target fixes that had
  moved layout by 2 to 20 px. The card copy became phone-only (`<picture>`), the targets became hit areas that change
  no box, each hit area was probed pixel by pixel in Chrome at three widths, and the final set was compared again.
- **Test authors found production bugs while writing tests**: the no-JavaScript rules that did not apply, the
  comment stripper that was not idempotent, the "Download all GPX" link without a file, the card copy handed to
  small 2x phones for a full-width photo, a dead `#featured` link, a multi-day trip's own `track.gpx` overwritten by
  a `--link` build. All fixed and pinned.
- **Incident.** While about fifteen scratch copies of the checkout existed, free disk fell to 13 GB and iCloud Drive
  offloaded files in use; `.git/index` disappeared. It was rebuilt from `HEAD` after the tree had been verified
  against it; the report's section 11 has the details. After that, agents were limited to scratch copies of
  `tools/`, `tests/` and `assets/`.

### Remaining issues and author inputs

Listed in `docs/IMPLEMENTATION_REPORT.md`, sections 10 and 12. The ones that most need the author: the phone photo
size, the font-loading choice, the privacy decisions in `docs/PRIVACY_NOTES.md`, `published_at` for existing
reports, and whether to start Phase 5.

## Phase 5 — Region pages (2026-10-10)

Starting point: Phases 1 to 4 committed on `phase1-curated-homepage`; `HEAD` was `c7ed3ee` (the code of `fb425ab`).
Baseline before this phase: 2,021 tests OK and `build.py --check` OK (349 pages). Phase 5 is the plan's optional
expansion and needed a scope decision. Asked on 2026-10-10, Eric chose region pages only; collections, a summit
index, reading bookmarks, an interactive map and the upload desk were not built. No copy was written for any region,
no trip fact was added, and no file under `content/` or `rendered/` changed. `tools/render.py` was not run: the pages
use the region maps that were already rendered. Nothing was pushed or deployed. The report's section 14 has the
measured results; this entry records what changed and what was run.

### Changed files

| File | Change |
| --- | --- |
| `tools/sitegen/pages/region.py` (new) | One page per region that has a region map and at least one published report: `regions/<slug>/`. `regions`, `head` with `years_item`, `place_names` and `place_items`, `pick_featured`, `featured`, `others`, `activity_words`, `description`, `share_image`, `map_trips`, `page`, `build`. |
| `tools/sitegen/core.py` | `read_site_meta` (the site meta as it is on disk; `site_meta` is the cached copy), `listed_trips`, `region_groups` (the Map page's grouping, moved here with the same results), `region_pages` (which regions get a page and what each lists), `region_page_href`; `register_site(site, meta=None)` records the regions that have a page, only when a meta is passed. `CARD_PHONE_SIZES`: the phone source of a card cover declares 106 px for its 112 px slot. |
| `tools/sitegen/pages/archive.py` | `site_meta`, `listed` and `regions` delegate to core. `region_panel(page=True, drawn=)` is the panel as a region page shows it (no heading of its own, id `map`, the legend from the trips the map draws); on the Map page each panel gains a link to the region's page. `archive_section(published=, active=)` lists a subset with the same markup. |
| `tools/sitegen/pages/report.py`, `home.py`, `trips.py` | A region link goes to the region's page when it has one: the breadcrumb and the region cell of the goal pager (`region_cell`), the "By region" links on Trips, the `ALSO` row and the two region names on Home. A region without a page keeps its link to the Map page. `home.also_items` names a mapped region only while it has a panel on the Map page or a page of its own. |
| `tools/build.py` | `'region'` in `PAGE_MODULES`; `register_site` is given the site meta on disk. |
| `assets/js/base.js` | A map dims what is not picked out only when a track, pin or cluster matched, so a list row whose trip the map does not draw leaves it as it is. |
| `assets/js/pages/archive.js` | Its guard accepts `body.p-region`; "Show fewer" keeps its button in view. |
| `assets/css/pages/region.css` (new), `archive.css`, `home.css` | The region page's head, Featured grid and link rows; the Map crumb's 44 px hit area; a long place wraps or breaks; the panel's link; the home page's region name as a link with a 44 px hit area that changes no box. |
| `README.md`, `ADDING-TRIPS.md`, `docs/CONTENT_GUIDE.md` (new section 11), `docs/DEVELOPING.md` | Region pages for the author and for a developer; statements the pages made wrong were corrected. |
| `docs/IMPLEMENTATION_REPORT.md` | Section 14 and the rows that Phase 5 changes. |
| Tests | `tests/test_region_page.py`, `tests/test_maplist_js.py` with `tests/maplist_js_harness.js`, and `tests/run_orders.py` (a helper, not a test module) are new; 21 existing files under `tests/` changed. See Checks. |

### Behaviour

- **Which regions have a page.** A region that has a region map in `rendered/site/meta.json` (drawn by `render.py`
  from three trips with a track) and at least one published report. Eight today: Lake Tahoe, Santa Cruz, Eastern
  Sierra, Bay Area, Boise, Alps, Tetons, Oregon. A region without a map keeps its list on the Map page. There is no
  `regions/` index; the Map page is the parent.
- **What a page lists.** Every report and active tick-list goal whose `region:` is exactly the region's name, at
  every build: also a report without a track, a journal, or a report newer than the last render. The map on the page
  shows what it was last drawn with, as on the Map page.
- **The page.** Breadcrumb `Reports / Map / <Region>`; the name; one line of counts and years and one of places, all
  from front matter; the Map page's panel for the region (map, legend, the list with "Show all"); a Featured row of
  up to three cards (reports flagged `featured: true`, then written reports with a photo, then without, newest
  first); every report by year with the activity filter; links to the other region pages. Its description is one
  sentence of the same counts. It is in the sitemap, not in the feed or the search indexes.
- **Links.** Report and goal breadcrumbs, the goal pager, the Trips page's "By region" links, the home page's `ALSO`
  row and region names, and a new link under each Map page panel lead to the region page. Every
  `map/#region-<slug>` address still lands on the Map page.
- **Card photos on phones.** A portrait or square cover's 320 px copy is now taken by a 3x phone; it took the 600 px
  copy before.
- **Unchanged.** Every existing URL, anchor, id, title, description, write-up, GPX file, the feed and both search
  indexes. Against the Phase 4 build, 169 of 347 pages differ in their HTML: the links above, and the `sizes` of the
  phone source of card covers.

### Checks actually run

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` | 2,339 tests in 38 files, OK (2,021 in 36 before the phase), on Python 3.9.6 and 3.12 with `-W error`. |
| Module order | The suite also passes with its modules reversed and in shuffled orders (`tests/run_orders.py`), and no test leaves a region page registered. |
| Node harnesses | `trips_js_harness.js` 125 checks, `series_js_harness.js` 43, `ticklist_js_harness.js` 85, `maplist_js_harness.js` 13 (new: `base.js` and `archive.js` against a stand-in page). All pass. |
| `python3 tools/validate.py` on the real content | 0 errors, 1 warning (the planned route without `goal.json`), 467 notes, as before the phase. |
| `python3 tools/build.py --out <scratch> --link --check` | OK: 357 pages (349 and the eight region pages), 168 trips. |
| Builds under Python 3.9 and 3.12 compared file by file | Identical. |
| CI rehearsal: the 5,204 files the commit holds (from the staged index), case-sensitive volume, Python 3.12, `TZ=UTC`, `LANG=C`, nothing on the path but Python | 2,339 tests OK (29 skipped, the Node-dependent ones); `build.py --check` OK; the 3,411 files of the output identical to the local build. macOS, not Linux; the CI job itself has not run. GitHub's runner has Node, so the 29 tests skipped here will run there; see the review gate entry. |
| The final build against the Phase 4 build | No path removed; 8 added (the region pages). All 351 GPX files, the feed, `robots.txt` and both search indexes identical; the sitemap gained the eight addresses. Titles, canonicals, descriptions and write-up text identical on all 347 pages; no id or anchor lost. |
| Page-load measurement, same method as Phase 4 | Three region pages and four existing pages, three phone runs and one desktop run each, on the build before the review fixes (44 loads, with the Phase 4 build beside it) and after the second round of fixes (28 loads). See the report, 14.3. |
| Lighthouse, two region pages, mobile and desktop | Accessibility, best practices and SEO 100 in all four runs; no failed audit. The runs were made on the build before the second round of fixes and were not repeated on the committed code; the review gate ran both pages again on its final build, with the same result (see the review gate entry). |
| Browser walk in Chrome 155 with real key presses and pointer events | Three passes (first build, after round 2, and the last fixes): widths 320 to 1440, keyboard order, target sizes pixel by pixel, cluster markers, JavaScript off, reduced motion and forced colours by emulation, boxes of every element on Home, Trips, the Map page and a report against the Phase 4 build. See the report, 14.4. |
| Author docs | Written by one agent from the code, then read literally by an independent reader on synthetic sites, corrected, read again by a third, and the remaining over-precise passages tightened by hand. |
| Mutants | Single-line changes on scratch copies: 202 in the first round (199 killed, 3 equivalent), 104 in the second (102, 2 equivalent), 49 in the third (48, 1 equivalent). |
| Rendering | Not run. No file under `rendered/` changed. |
| Not run | Safari and Firefox; real phones; screen readers; a real share preview; field performance; the CI job. |

### Review

- **Round 1** (nine agents: tests and docs from the contract, two code lenses with a skeptic each, a browser walk
  with a skeptic, a measurement). 18 findings, 13 distinct. Fixed: the page listed only what its map's entry named,
  so a report without a track or newer than the last render was missing from its own region's page (the rule was
  changed to the `region:` field); ten of thirteen cluster markers on the Lake Tahoe page were clickable and did
  nothing; two new links answered over less than 44 px; a long place could make the head scroll sideways; places
  were ordered and merged case-sensitively; the description read "each" for one report; registering a site in a
  unit test read the checkout's real `rendered/site/meta.json`. The measurement found that a portrait card cover
  loaded a 154 KB file on a 3x phone where a 42 KB copy does, which became the 106 px declaration.
- **Round 2** (seven agents on the revised code). The first-round problems were confirmed fixed in the browser.
  New: the legend beside a region's map was built from the page's list and could name activities the map does not
  draw (fixed); a list row for an undrawn trip dimmed the whole map (fixed in `base.js`); "Show fewer" left its
  focused button thousands of pixels above the viewport, on the Map page too since before this phase (fixed); the
  home link's hit area reached 1 px into the map from 1200 px (fixed); one unbreakable 36-character place word
  still widened a 320 px page (fixed). An independent reader of the docs found ten false or misleading statements;
  one of them was a real failure of the check that predates the phase (the home page linked to a Map page panel
  that had gone once all of a region's reports were drafted), fixed in `home.also_items`.
- **Round 3** (four agents on those six fixes): no regression against `c7ed3ee` beyond the stated differences. One
  side effect fixed (a region with a page but no panel had dropped out of the `ALSO` row). Left as they are, all
  low: two sibling states of the check failure that predate the phase (report, 14.6), an 11 px extra scroll after
  "Show fewer" when the button sits just under the header, and an empty activities list in the legend of a map that
  draws only a planned route (as on the Map page).

### Remaining issues and author inputs

Listed in `docs/IMPLEMENTATION_REPORT.md`, sections 14.6 and 14.7. In short: the regions with
three or four reports have thin pages by the rule as built; the Featured row is automatic; the 320 px card copy is
slightly softer than the 600 px one on a 3x phone for portrait covers; and a few stale-map states that predate the
phase still fail the check until the maps are drawn again.

## Review gate before publication (2026-10-11)

Starting point: Phases 1 to 5 committed on `phase1-curated-homepage`; `HEAD` was `dbce17b`, 14 commits ahead of
`main` (`a9baab9`, which is also `origin/main`). After Phase 5 was committed, asked what to do next, Eric chose the
review gate that closes the prompt pack. The gate compares the branch with the site that is public today: `main` was
built with its own code (345 pages, 3,294 files) and the branch beside it (357 pages, 3,411 files), both from the real
content, both served under `/personal-website/`. Nothing was pushed, merged or deployed, `tools/render.py` was not
run, and no file under `content/` or `rendered/` changed. The report's section 15 has the six items with their
evidence, the list of what a push would make public, and the open points; this entry records what changed and what
was run.

### Changed files

| File | Change |
| --- | --- |
| `tools/sitegen/pages/home.py` | The "Recent outings" section carries `id="latest-h"`, the id of the heading of the public home page's "Latest reports" list. |
| `assets/js/pages/series.js` | The list of ids the write-ups filter hides also holds the ids inside a hidden day or month (a day's number and title, a month's heading), each once. |
| `assets/js/pages/explore.js` | `historyStep(kind, entry, now, next, recent)`: the one rule for what a change of view does to the browser's history, pure, shared by the two list pages. |
| `assets/js/pages/trips.js` | `clearedSort(sort, userSort)`, pure and exported; `address()`, `write(kind, keepHash, settle)`, `sortForSearch()`; the page keeps `entryUrl` and `nowUrl`; the `popstate` and `hashchange` handlers settle them, and `popstate` rewrites an entry whose sort it had to correct. See Behaviour. |
| `assets/js/pages/ticklist.js` | The same page part as trips.js (`entryUrl`, `nowUrl`, `address()`, `write`, the three kinds of change), without the sort rule. |
| `tools/sitegen/pages/trips.py`, `ticklist.py`, `series.py` | `autocomplete="off"` on the two filter forms and on the journal's "write-ups only" box. |
| `tools/sitegen/curation.py` | `_once`: a key written twice in `content/home.json` is an error. |
| `tools/sitegen/pages/notfound.py` | The 404 page's "Site" list offers Trips before "Map & archive". |
| `docs/DEVELOPING.md`, `docs/CONTENT_GUIDE.md`, `docs/TICK_LIST_GUIDE.md`, `README.md`, `ADDING-TRIPS.md` | The behaviour above; what the CI runner has; where planned routes are counted and listed; a deploy takes "a few minutes", not "about a minute", now that the job runs the tests. |
| `.github/workflows/pages.yml` | One comment line: the job is no longer said to run in well under a minute. No step changed. |
| `docs/IMPLEMENTATION_REPORT.md`, this log | Section 15 and this entry; the corrections listed under Review. |
| Tests | `tests/test_notfound_page.py`, `tests/test_fixture_text.py`, `tests/page_standin.js` (the stand-in for the browser that the trips and tick-list harnesses share) and `tests/js_fixtures.py` are new; 11 existing files under `tests/` changed. See Checks. |

### Behaviour

- **Home.** `…/#latest-h` lands on the newest reports again. It was the one fragment link of the public site, out of
  3,352, whose target the branch had dropped.
- **Journal.** An address that names an id inside a day or month the default view hides (`#day-30-t`, `#day-30-n`,
  `#month-2024-07-h`) switches the filter off and lands, as an address naming the day or month itself already did.
- **Trips and the Tick list, Back after a search.** Typing still rewrites the current history entry. Enter in the
  search box adds an entry whenever the view differs from the one the entry stood for, also when the typing pause had
  already written the words into the address, so Back returns to the list from before the search. Enter again adds
  nothing. A filter, the sort, the view switch and Clear all add an entry as before.
- **Trips, sort.** "Best match" does not stay when there is no search: after Clear all, after removing the search
  chip, after emptying the box by hand, and for an address that arrives with `sort=relevance` and no search, on load
  and on Back or Forward. A sort the visitor chose (Oldest first) stays.
- **Controls after Back and Forward.** The two filter forms and the journal's box ask browsers not to refill them.
  Chrome refilled them after the page's script whenever it loaded the page again from history, so a menu or the box
  could show a value the list did not follow.
- **Manifest.** `content/home.json: "featured_slugs" is written twice; keep one` stops the build and the validator.
  Before, the second list silently won.
- **404 page.** One more row, "Trips / SEARCH AND FILTER".
- **Unchanged.** Every URL, title, description, write-up, GPX file, the feed, both search indexes and the sitemap.
  Against the build of `dbce17b`, six files differ: `index.html`, `404.html`, `trips/index.html`,
  `tick-list/index.html` and the journal page by the lines named above, and `assets/site.js`.

### Checks actually run

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` | 2,424 tests in 40 files, OK (2,339 in 38 before the review), on Python 3.9.6 and 3.12.11 with `-W error`; no test skipped and none marked as an expected failure. |
| Module order | The suite also passes with its modules reversed and shuffled (`tests/run_orders.py`), and no test leaves a region page registered. |
| Node harnesses (Node 25.8.2) | `trips_js_harness.js` 145 checks, 187 with its page model; `ticklist_js_harness.js` 91, 111 with its page model (new); `series_js_harness.js` 49, 85 with its page model; `maplist_js_harness.js` 13. All pass. |
| `python3 tools/validate.py` on the real content | 0 errors, 1 warning (the planned route without `goal.json`), 467 notes, as before. |
| `python3 tools/build.py --out <scratch> --link --check` | OK: 357 pages, 168 trips. Builds under Python 3.9 and 3.12 are identical file by file. |
| The final build against the build of `dbce17b` | Six files differ. Compared tag by tag, the five pages differ by the lines named under Behaviour and by nothing else; the sixth is `assets/site.js`. |
| The final build against the build of `main` | All 3,294 paths of the public site are present (117 new); all 351 GPX files, the feed and `robots.txt` are byte-identical. |
| CI rehearsal: the 5,208 files a commit of this change holds (from a temporary index: `HEAD` plus the 33 files as they are at the end), case-sensitive volume, Python 3.12, `TZ=UTC`, `LANG=C`, the workflow's two commands | With only Python on the path: 2,424 tests OK, 53 skipped (the Node-dependent ones); `build.py --check` OK; the 3,411 files of the output identical to the local build. With Node 25 on the path as well, as a runner has Node: 2,424 OK, none skipped; the same build. macOS, not Linux, and not the runner's Node 22; the CI job itself has not run. |
| Mutants | Changes on scratch copies, over four passes: 234 (221 of one line, 6 of two or three lines, 5 whole-fix reverts and 2 inserted quotes), of which 221 fail a behaviour check and 13 are equivalent in behaviour. The tests that read the source hold 12 of those; the thirteenth (in `historyStep`, `kind === 'pick'` written as `kind !== 'submit'`) passes every test, because the callers pass only the three kinds. Three more by hand for the three `autocomplete` attributes, each failing its test. |
| Browser replays in Chrome 155, real key presses, clicks and touch, 1440 px and 390 px, back/forward cache on and off | Six passes; see Review. On the build of the sixth pass, from which the final build differs in comment lines of the script only: the Tick list 1,084 step records, Trips 1,588 against the build before it, the journal 284; no page exception or console error in 603 sequence runs. |
| Lighthouse 13.4.1 | 30 runs (15 pages, mobile and desktop) on the final build, after a full pass on the build of the fourth pass and partial ones on the builds between: accessibility, best practices and SEO 100 in every run. In those three categories the one failed audit is the informational one of weight 0 on Home and two activity pages, as on `main`; in the tool's fourth category the Map page's mobile run has a layout shift of 0.051. No console error or warning on the 15 pages at 1440 px or 390 px. |
| Screenshots | 39 views of `main` and 51 of the branch (phone and desktop), paired on a local review page; after the first fixes 18 views were taken again: 14 byte-identical, the 404 page's three replaced, and one differing by capture noise only (a capture of the unchanged commit taken the same day is byte-identical to it). Kept in the git-ignored `.cache/review/`, not in the repository. |
| Author docs | After pass 6 two independent readers checked what the review had written: the changed passages of the guides against the code (88 statements, the history rules played under Node), and this entry and the report's section 15 against the stored results (235 statements, the counts recomputed). They found 17 and 29 defects. A third reader then checked the 46 corrections against the code and the evidence: 42 held, and the four that did not, with five smaller points, were corrected in turn (see Review). |
| Rendering | Not run. No file under `rendered/` or `content/` changed. |
| Not run | Safari and Firefox (two questions about them were answered from their source, by reasoning only); real phones; screen readers; a real share preview; the CI job; Node 22. |

### Review

- **Pass 1** (seven agents on `dbce17b`: curation and goals, compatibility with the public build, the inventory of
  public material, the log's evidence, a browser walk of links and downloads, photographs and screenshots, and a
  second reader of all six). Five of the six items held, two of them with one exception each (report, 15.1). The
  sixth, approval of the new public material, is the author's and is open: the pass made the inventory. Found: the
  home anchor; the journal's inner ids; the Back defect
  after a typed search; "Best match" left behind by Clear all; a manifest key written twice read silently; a test that
  quoted two sentences of a real write-up; no way to Trips from the 404 page. In the documents: the report and this
  log said the CI runner has no Node, and gave the Lighthouse results of Phases 4 and 5 without saying they were made
  before each phase's last fixes; seven table cells were 1 KB off, one size was given as 2.3 MB for 2.2 MB, three
  numeric wordings were loose, and two cross-references pointed at the wrong section. All fixed or corrected; the
  smaller points that were left are in the report, 15.4.
- **Pass 2** (four agents on the fixes: tests with mutants, an adversarial reader, a browser walk with Lighthouse,
  and a skeptic on what they found). Five
  of the six fixes held. The history fix was wrong in two cases and incomplete in two: a search containing an
  apostrophe added an entry at every Enter, because the page compared its own spelling of the address with the
  browser's (`'` against `%27`); after arrow keys through the activities and a submitted search, Back landed on a
  filter the visitor had only passed through; emptying the box by hand still left "Best match"; and Enter after a
  year link rewrote the year link's entry. The id list of the journal held the days of hidden months twice. All
  corrected: the page now keeps both addresses in its own spelling and never reads them back from `location`.
- **Pass 3** (two agents: tests rewritten to the corrected rule, with 65 mutants, 58 killed by a harness check and 7
  shown equivalent and held by the tests that read the source; 19 sequences of typing, Enter, filters, year links,
  Back and Forward replayed in Chrome with real key presses at 1440 px, 13 of them also at 390 px with touch, each
  compared with `dbce17b`). All 19 follow the plan's rule; 12 are better than `dbce17b` and 7 the same. One new
  inconsistency: after "Best match" was picked from the menu with an empty box, Back onto that entry showed "Newest
  first" under an address that still said `sort=relevance`. Corrected: the entry's address is rewritten when the
  visitor lands on it, as a load of it already was.
- **Pass 4** (three agents: tests with 25 mutants, 23 killed and 2 equivalent; an adversarial replay; Lighthouse).
  The rewrite holds, and 398 step records against the logs of pass 3 show no regression. Lighthouse 13.4.1 on 15
  pages, mobile and desktop (30 runs): accessibility, best practices and SEO 100 in every run, each audit equal to
  the pass-2 report of the same page, and no console error or warning at either width. Found: when Chrome loads a
  Trips entry again from history (a jump back over two entries, or after it has dropped the page from its cache), it
  refills the form's controls after the page's script, with the values of the view that was on screen when the
  visitor left, so the Sort, Year or write-up control could show another entry's value; the jump case was already in
  `dbce17b`. Fixed with `autocomplete="off"` on the two filter forms.
- **Pass 5** (two agents: a replay with a load probe, and Lighthouse on the changed pages). On 60 Trips documents
  loaded again from history the controls now have the address's values at `DOMContentLoaded` and do not change
  afterwards; the build before the fix had a control changed on 46 of 60 and `dbce17b` on 28 of 60. The Tick list had
  the same fault and agrees in 27 of 27 runs. 1,104 step records against the build before show those differences
  and five of driver noise (scroll positions, the order of popstates), which re-runs showed to vary within one
  build. Found: the journal's "write-ups only" box is refilled in the same way, on the public site as well
  (fixed with the same attribute). In the same pass a reading of ticklist.js showed that the Tick list still had the
  Back defect fixed on Trips; the rule moved to explore.js and the Tick list follows it.
- **Pass 6** (two agents: tests with 65 mutants, 61 killed and 4 equivalent; a replay). The Tick list: 16 sequences
  with their variants and 14 extras, 41 in all, follow the rule on the build of this pass in every setting; `dbce17b` fails
  it in 24 of them (Enter after the typing pause makes no entry and Back leaves the page). Trips: no state field
  differs from the build before. The journal: 15 sequences, 130 documents loaded, the box never changed after
  `DOMContentLoaded`, and box and list agree at every step. Three low points were found and left, none a regression
  against `dbce17b` (report, 15.4): a filter clicked within about 150 ms of the last key drops the typed words;
  words typed before the script arrives become the view the page opened on; at an address naming a hidden day the
  journal's stored choice does not survive a reload.
- **The documents** (two readers, after pass 6, then a third on their corrections). In the guides: two statements
  were false (the journal's filter was said not to have existed on the public site, where it exists and starts
  switched off, in two guides; a count of Node processes was stale), and twelve were incomplete, loose or
  unsupported, 17 defects in all, among them what the Trips tests read after each step,
  where the Tick list's `popstate` differs from the Trips page's, which pages count a planned route, and "about a
  minute" for a deploy whose tests alone now take about that long. In this entry and the report: a Lighthouse pass
  attributed to the final build that had run on the build of the fourth pass; the Phase 5 Lighthouse statements
  left uncorrected; "all 478 ids" for 475 of 478; mutants called single-line that were not all so; open points
  that had been left off the list; and what has to be decided before a push rather than after. The same false
  sentence about the filter stood in a comment of series.js and of one test, and two comments in trips.js and
  ticklist.js named `write()` where `address()` was meant: corrected, which changes comment lines of the bundle and
  nothing else. Five rows of earlier entries of this log also gained a commit id, a forward pointer or a narrower
  wording. Lighthouse was then run on all 15 pages of the final build. The third reader found 42 of the 46
  corrections sound; the others (a count of Node processes corrected to a wrong number, the photo choices listed
  as a matter for before the push, one sentence on which low points are new, one breakdown of the mutants) and five
  smaller wordings were corrected in turn.

### Remaining issues and author inputs

Listed in `docs/IMPLEMENTATION_REPORT.md`, section 15.4. In short: of the files that become public for the first
time, four are worth a read first (`ADDING-TRIPS.md`, the privacy notes and their tool, the plan), and that and the
co-author lines of the commits have to be settled before a push; the cover photos, focal points and one search
alias were chosen for the author and can be changed afterwards; the deploy job has never run, and the runner's Node is a
version nothing here was tested with; the journal's default view hides three days that have photographs; one map pin
counts the planned route in with reports, on the public site as well. Left as they are in the Trips page's history,
all low: a year link followed between search actions leaves an entry that Back passes through with nothing changing
on screen; Enter on a box holding only spaces or punctuation makes an entry whose list is the plain one; "Best match"
can be picked with an empty box, where it orders nothing.
