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

## Publication (2026-10-12)

Eric asked for the branch to be published. `main` on GitHub was fast-forwarded from `a9baab9` to `e8d44dc` (no pull
request; the branch `phase1-curated-homepage` stays where it was).

- **The first run of the deploy job failed at the unit tests**, so nothing was deployed and the old site stayed up.
  The runner had Python 3.12.15 where this Mac has 3.12.11, and two tests of `tests/test_sitecheck_hostile.py` put a
  malformed `<![foo]>` declaration into a page's head and expected `html.parser` to give up on it. Python does through
  3.12.11 and no longer does in 3.12.15, where the declaration is read as a comment. Every other test passed there,
  the Node-dependent ones included, under the runner's own Node.
- **The fix is `d7272e0`, tests only.** The two tests force the parser's failure, for both errors older Pythons
  raise, and a third takes the real parser as it comes. Before the push the runner's two failures were reproduced
  here by putting `Lib/html/parser.py` of the CPython tag `v3.12.15` first on `PYTHONPATH`; with it the suite and the
  checked build then passed, as they did on 3.9.6 and 3.12.11.
- **The second run passed**: 2,425 tests in about 100 s on the runner, the build (357 pages) and its check, and the
  deploy. The site was live about two and a half minutes after the push.
- **The live site was compared with a local build of the same commit**: all 3,411 files, the 1,812 pages, tracks,
  data files, scripts and styles by SHA-256 and the 1,599 images by size. In Chrome 155 at 1440 px and at 390 px, 15
  pages loaded with no failed request and no console error; search with Back and Forward, a journal day link, GPX
  downloads, the units switch and the 404 page under `/personal-website/` behaved as in the local runs; Lighthouse
  gave accessibility, best practices and SEO 100 in 8 runs. All 186 sitemap addresses and the feed's 30 items
  answered, and every share image exists at its declared size.
- **Seen on the live site and left**: `robots.txt` is served under the project path, where crawlers do not read it
  (the sitemap can be submitted directly); every share image is a WebP, which some link previews may not draw; on a
  phone a report shows no link to its region page; the two bundles have unversioned addresses (report, 15.5).
- Not run: Safari, Firefox, a real phone, a share preview in a real app.

## Journal days on the region maps (2026-10-12)

Asked for by Eric after the publication: the Lake Tahoe and Eastern Sierra maps did not show his PCT and Tahoe Rim
Trail hikes. They are days of the PCT journal, which is one trip filed under a region of its own, and the renderer
drew a journal on no region map.

### Changed files

| File | Change |
| --- | --- |
| `tools/lib/content.py` | `_region_days`: the `region_days` block of a journal's `index.md`, which names the days of the journal that lie in a region, by the day numbers the page shows. `t['region_days']`. |
| `tools/render.py` | `journal_parts`, `day_runs`, `journal_pins`; `site_tracks(days=)`. `render_site` draws the listed days on the region's own map, keeps the map framed by the region's own trips (the specs carry that `bbox`), gives a run of days that starts inside the region a pin, and records the days in the map's entry as `journals`. |
| `tools/sitegen/pages/archive.py`, `region.py` | `journal_parts`, `journal_row`: one row for the journal in the region's list, on the Map page and on the region's page; the legend names its activity once the map draws it. |
| `tools/lib/checks.py` | `region_days` is a known key; `_journal_region_findings`: a region no report is filed under is an error; a region without a region map, and a map drawn with other days than the block lists, are warnings. |
| `content/trips/pacific-crest-trail-2024/index.md` | `region_days`: Lake Tahoe 67-76 and 147-153, Eastern Sierra 58-65. The days were chosen by computing which days' tracks cross each map; Eric chose to keep both maps' present area. |
| `rendered/site/` | `meta.json` and the four line overlays of the Lake Tahoe and Eastern Sierra maps (`*.svg.html`). No base image changed: the frames are the ones the maps had. |
| `tests/test_region_days.py` (new), `tests/test_checks.py`, `tests/test_region_page.py` | The block, the renderer with the drawing stubbed, the list row and the validator rules. |
| `README.md`, `docs/CONTENT_GUIDE.md` (5.2, 5.3, 11.1, new 11.7), `docs/DEVELOPING.md` | The block for the author and for a developer. |

### Behaviour

- **On the map.** Each listed day that has a GPX is drawn in the journal's activity colour where it crosses the map,
  and cut off at the map's edge: on both maps the PCT now runs from edge to edge, and the Tahoe Rim Trail is the loop
  around the lake. A journal day never moves or widens a region's map. A run of days that starts inside the region
  has a pin at its start (the Tahoe Rim Trail, Day 147); a run that walks in from outside has none.
- **In the list.** One row per region, "Pacific Crest Trail 2024", with the number of listed days and the distance
  they add up to, linking to the first of them on the journal page. Hovering it picks out the journal's lines on the
  map. No count of reports includes it.
- **Unchanged.** Every count, the "All reports" tables, the home page, the Trips page, the search indexes, the feed
  and the sitemap. Regions without journal days render as before, byte for byte.

### Checks actually run

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` | 2,459 tests in 41 files, OK, on Python 3.9.6 and 3.12.11 with `-W error`; also with the modules reversed. |
| `python3 tools/validate.py` | 0 errors, 1 warning (the planned route without `goal.json`), 467 notes. Before the render it also gave the new warning that the Lake Tahoe map was drawn without the listed days. |
| `python3 tools/render.py --site` | Run three times as the design changed (the last with `--force`); needs the internet. Against the published files only `meta.json` and the four overlays differ. |
| `python3 tools/build.py --out <scratch> --link --check` | OK: 357 pages. |
| In Chrome 155 at 1440 px and 390 px | Both region pages: the lines are drawn and cut at the map's edge, the row is in the list and highlights the lines, and its link and the pin's land on their day of the journal with the write-ups filter switched off. Before and after pictures were compared side by side. |
| Not run | Safari, Firefox, a real phone. |

### Remaining issues and author inputs

- The row's distance is that of the listed days, whole, also where a day leaves the map.
- Where the Tahoe Rim Trail starts, its pin shares a cluster with one report's, under the key "Several reports start
  here" (report, 15.4, point 7, is the same question for the planned route).
- Two previews were made and not kept: an Eastern Sierra map widened to the whole High Sierra put two peak labels on
  other summits of the same names, and its OpenStreetMap answer (about 200 MB) took longer than the renderer's
  180-second limit allows.
- Journal days 141 to 145 (the John Muir Trail) and the Sierra days south of the Eastern Sierra map are on no region
  map: they lie south of it, but for the last few kilometres of day 145, which were left out.

## Journal parts: rows that show and lines that answer the pointer (2026-10-13)

Asked for by Eric the day after the journal days went on the maps: the PCT and Tahoe Rim Trail routes did not show up
under the reports in the region's list, and nothing happened when he pointed at them on the map.

### What was wrong

- **The list.** The journal had one row per region, placed by the date of its last day there. Lake Tahoe's list folds
  after 8 rows, and the row stood far down behind "Show all 86", so the open page did not show it. One row also could
  not say that Lake Tahoe holds two walks, the PCT and the Tahoe Rim Trail.
- **The map.** Only pins and numbered markers answer the pointer. The PCT walks in from outside the map and has no
  pin, and the Tahoe Rim Trail has a single pin, at its start. So the lines themselves had nothing to point at: no
  highlight, no name, no link.

### Changed files

| File | Change |
| --- | --- |
| `tools/lib/content.py` | `_region_days`: a region's value may be a mapping of named parts. Every entry is now a part: `{'region', 'title', 'key', 'days'}`; a named part's key is `<slug>:<slugified name>`. |
| `tools/render.py` | `site_tracks(part=)`, `journal_pins(t, part, frame)`, `part_href`, `part_name`, `part_glyph`: a part's lines are keyed to the part and carry a link to its first day and its name; each part gets a 64×48 drawing of its own days; the map's `journals` entries carry `key`, `title` and `glyph`. |
| `tools/lib/mapkit.py` | `line_links`, `LINE_HIT`: one `a.mk-line` per key over the lines that carry an `href`, with a transparent 14 px stroke to point at, written under the pins. |
| `assets/js/base.js`, `assets/css/base.css`, `assets/css/pages/archive.css` | A line link is wired as a pin is (hover, focus, the row marked). A row marked from the map now looks like a hovered row; until now the mark had no style in a region's list. |
| `tools/sitegen/pages/archive.py` | `journal_row` per part, after the reports and never folded away; `part_glyph`: the row shows the part's own drawing. |
| `tools/build.py` | `copy_part_drawings`: the drawings are published as `assets/maps/<name>.svg`. |
| `tools/lib/checks.py` | The stale-map warning compares part by part and names the part. |
| `content/trips/pacific-crest-trail-2024/index.md` | Lake Tahoe: "Pacific Crest Trail" 67-76 and "Tahoe Rim Trail" 147-153; Eastern Sierra: "Pacific Crest Trail" 58-65. The same days as before, now named. |
| `rendered/site/` | `meta.json`, the four line overlays of the two maps, and three new part drawings. No base image changed. |
| `tests/test_region_days.py`, `tests/maplist_js_harness.js`, `tests/test_a11y_static.py` | Named parts, part keys, line links, the drawings and their publication, the rows' place and that they are never folded, the marked row, and a harness check that a line link picks out its lines and marks its row. |
| `README.md`, `docs/CONTENT_GUIDE.md` (5.2, 5.3, 11.7), `docs/DEVELOPING.md` | The named form, the line links and the rows. |

### Behaviour

- **In the list.** Lake Tahoe shows "Pacific Crest Trail" (Jun 27 to Jul 6, 2024, 10 journal days) and "Tahoe Rim
  Trail" (Sep 15 to 21, 2024, 7 journal days) directly after its first 8 reports, whether the list is folded or not;
  the Eastern Sierra shows "Pacific Crest Trail" (Jun 18 to 25, 2024, 8 journal days) after its 7 reports. Each row
  has the drawing of its own days and opens the journal at the part's first day.
- **On the map.** Pointing at a part's line picks out all of its days, dims the rest, marks its row and shows its name;
  a click opens the journal at the part's first day. Pointing at the row picks out the line. A pin or numbered marker
  on the line answers before the line does, and where the two Lake Tahoe parts share the trail the Tahoe Rim Trail
  does.
- **Unchanged.** Every count, the "Show all 86" button, the tables of reports, the maps' frames and base images, the
  home page, the Trips page, the search indexes, the feed and the sitemap.

### Checks actually run

| Check | Result |
| --- | --- |
| `python3 -W error -m unittest discover -s tests`, Python 3.9.6 and 3.12 | 2,470 tests, OK on both |
| The suite and `build.py --check` on Python 3.12 with the `html.parser` of CPython 3.12.15, the deploy runner's release | 2,470 tests, OK; link check OK |
| `python3 tests/run_orders.py --reverse` | 2,470 tests, OK |
| `node tests/maplist_js_harness.js` | 14 checks passed |
| `python3 tools/validate.py` | 0 errors, 1 warning (a planned route without `goal.json`, as before) |
| `python3 tools/build.py --check` | 357 pages, link check OK |
| `python3 tools/render.py --site --force` | all region and ski maps redrawn; only the two regions' overlays and `meta.json` differ, plus the three new drawings |
| Browser, local build, a real pointer | Lake Tahoe: both lines answer (highlight, row marked, name), both rows visible in the folded list with their own drawings; Eastern Sierra: the same for its one part |

Not run: Safari, Firefox, a real phone (a tap on a line opens the journal; there is no hover on touch).

## One stretch of a journal day on a region map (2026-10-13)

Asked for by Eric after the journal parts were published: Day 146 of the PCT journal belongs to the Tahoe Rim Trail
too. He finished a section of the PCT in the morning, drove to Lake Tahoe and started the Tahoe Rim Trail in the
afternoon, all in one recording, and wanted the afternoon on the Lake Tahoe map as part of that route, without the
straight line the recording has across the drive.

### What the track holds

Day 146 is one recording of 884 fixes with one break of about 168 km between two consecutive fixes: 6.7 km before it
and 27.6 km after it, which end where Day 147 starts. The site never drew a line across such a break (mapkit splits a
track wherever two fixes are more than 2 km apart), so the map was not the difficulty. Listing the day whole would
have put the morning into the route's small drawing, 168 km away from the loop, added its 6.7 km to the route's
distance, and taken the route's pin away, since a pin marks a run of days that starts inside the region.

### Changed files

| File | Change |
| --- | --- |
| `tools/lib/geo.py` | `stretches`, `STRETCH_GAP_M` (20 km): a recording falls into stretches where two consecutive fixes lie farther apart than that. |
| `tools/lib/content.py` | `_region_days`: `146/2` lists a day with one stretch of its recording; every part carries `'stretches': {day id: n}`. `day_points(day, n)`: the fixes of the day or of that stretch; a stretch the track does not have is a `ContentError`. |
| `tools/render.py` | `part_points`, `drawn_stretches`: a part's line, the pin of a run it starts and its small drawing take the stretch alone; the stretch is part of the site maps' hash and is recorded in the map's `journals` entry. |
| `tools/sitegen/pages/archive.py` | `part_day_km`: in the part's row, a day taken as a stretch counts with the stretch's length along its track; the day file's distance is the whole day's. |
| `tools/lib/checks.py` | A stretch the day's track does not have is an error; a map drawn with another stretch than the block lists is a warning. |
| `content/trips/pacific-crest-trail-2024/index.md` | Lake Tahoe, Tahoe Rim Trail: `146/2, 147-153`. |
| `rendered/site/` | `meta.json`, the two line overlays of the Lake Tahoe map and the Tahoe Rim Trail's small drawing. Nothing of the Eastern Sierra map changed, and no base image. |
| `tests/test_region_days.py` | The splitter, `day_points`, the form and what is refused, the line, the pin, the drawing, the hash, the row's distance and the validator's two rules. |
| `README.md`, `docs/CONTENT_GUIDE.md` (5.2, 5.3, 11.7), `docs/DEVELOPING.md` | The form for the author and for a developer. |

### Behaviour

- **On the map.** The Tahoe Rim Trail's line now includes the afternoon of Day 146, which closes the loop on its
  south-east side. Nothing is drawn of the morning or of the drive. The route's pin stands at the start of that
  stretch, and its link and name start at Day 146 ("Tahoe Rim Trail: Pacific Crest Trail 2024, Day 146 to Day 153").
- **In the list.** "Tahoe Rim Trail", Sep 14 to 21, 2024, 8 journal days, 209 mi (336 km): the seven days it had
  (192 mi) and the 27.6 km of the stretch. Its small drawing is the closed loop.
- **Unchanged.** The Pacific Crest Trail part, the Eastern Sierra map and list, every count, and the journal page
  itself, where Day 146 is the one day it was.

### Checks actually run

| Check | Result |
| --- | --- |
| `python3 -W error -m unittest discover -s tests`, Python 3.9.6 and 3.12.11 | 2,480 tests, OK on both |
| The suite on Python 3.12 with the `html.parser` of CPython 3.12.15, the deploy runner's release | 2,480 tests, OK |
| `python3 tests/run_orders.py --reverse` | 2,480 tests, OK |
| `node tests/maplist_js_harness.js` | 14 checks passed |
| `python3 tools/validate.py` | 0 errors, 1 warning (a planned route without `goal.json`, as before); before the render it also gave the stale-map warning for Lake Tahoe (Tahoe Rim Trail) |
| `python3 tools/build.py --check` | 357 pages, link check OK |
| `python3 tools/render.py --site` | all region and ski maps redrawn; `meta.json`, the two Lake Tahoe overlays and the Tahoe Rim Trail drawing differ, nothing else |
| Browser, local build | Lake Tahoe: the route's line holds the new stretch as one unbroken line inside the map, the loop is closed, the line answers the pointer there, the row reads 8 journal days and 209 mi |

Not run: Safari, Firefox, a real phone.

## Days off taken out of the Lake Tahoe PCT route (2026-10-13)

Asked for by Eric with a screenshot of the Map page: with the pointer on the Pacific Crest Trail route, three red
marks lit up that are no part of the trail's line, and he asked which activities they were.

### What they were

The route listed days 67 to 76 as one range, and three of those ten journal days were not walked on the trail. Each
is a recording of its own that joins neither the day before it nor the day after it:

| Day | Date | The day file's figures |
| --- | --- | --- |
| 70 | Jun 30, 2024 | 6.5 km, 1:28 moving in 7:11 |
| 71 | Jul 1, 2024 | 40.2 km, 1:18 moving in 3:12 |
| 75 | Jul 5, 2024 | 12.9 km, 1:47 moving in 5:01 |

The trail itself is continuous without them: Day 72 starts 1.5 km from where Day 69 ended, and Day 76 starts 0.5 km
from where Day 74 ended. The Tahoe Rim Trail route and the Eastern Sierra route were checked the same way and hold
no such day.

### Changed files

| File | Change |
| --- | --- |
| `content/trips/pacific-crest-trail-2024/index.md` | Lake Tahoe, Pacific Crest Trail: `67-69, 72-74, 76`. |
| `tools/render.py` | `journal_pins`, `RESUME_M` (5 km): a run of days that starts within that distance of where the part's previous run ended goes on with the same walk and gets no pin. Without it, leaving the three days out would have given the route two pins, at the places where the walk went on. |
| `rendered/site/` | `meta.json`, the two line overlays of the Lake Tahoe map and the route's small drawing. |
| `tests/test_region_days.py` | The resumed run. |
| `docs/CONTENT_GUIDE.md` (11.7), `docs/DEVELOPING.md` | List the days of the route, not every day in between; the pin rule. |

### Behaviour

- **On the map.** The three lines are no longer drawn on the Lake Tahoe map at all: they were only ever drawn as
  days of this route. The route is the trail from the map's bottom edge to its top edge, and has no pin, as before.
- **In the list.** "Pacific Crest Trail", Jun 27 to Jul 6, 2024, 7 journal days, 165 mi (was 10 journal days and
  202 mi, which counted the three days' 59.6 km).
- **Unchanged.** The journal page, where days 70, 71 and 75 are the days they were; the Tahoe Rim Trail route; the
  Eastern Sierra map.

### Checks actually run

| Check | Result |
| --- | --- |
| `python3 -W error -m unittest discover -s tests`, Python 3.9.6 and 3.12.11 | 2,481 tests, OK on both |
| The suite on Python 3.12 with the `html.parser` of CPython 3.12.15, the deploy runner's release | 2,481 tests, OK |
| `python3 tests/run_orders.py --reverse` | 2,481 tests, OK |
| `python3 tools/validate.py` | 0 errors, 1 warning (a planned route without `goal.json`, as before); before the render it also gave the stale-map warning for Lake Tahoe (Pacific Crest Trail) |
| `python3 tools/build.py --check` | 357 pages, link check OK |
| `python3 tools/render.py --site` | all region and ski maps redrawn; `meta.json`, the two Lake Tahoe overlays and the route's drawing differ, nothing else |
| Browser, local build, Map page | with the pointer on the route, 7 lines are picked out and they are the trail alone; the row reads 7 journal days and 165 mi; the route has no pin |

Not run: Safari, Firefox, a real phone.

## Phase 6 - Author tools (2026-10-24)

The first phase of the second plan (`docs/personal-website-improvement-plan-2.md`, section 6, and the Phase 6 prompt
of `docs/claude-code-website-prompt-2.md`), built on branch `phase-6-author-tools` from `main` at `1cb9cf2`. It needed
no decision from Eric. Everything is in `tools/`, `tests/` and the guides; the one page change, the box for a map that
is not drawn yet, reaches no published trip. The disk had about 21 GB free throughout, under the plan's 30 GB line:
builds were linked into the session's scratch folder, and no worktree or copy of the checkout was made.

### Changed files

| File | Change |
| --- | --- |
| `tools/lib/frontmatter.py` | `_strip_comment`: a `#` after a space ends the value outside quotes and `[...]` (YAML's rule); a quote opens a quoted value only where a value starts, so an apostrophe in plain text does not hide a note. `loads(text, first_line=1)` refuses a line indented with a tab (`line N is indented with a tab; use spaces`, N as the file numbers it). |
| `tools/add_trip.py` | `main(argv)` returns the exit status. `force_refusal` (`--force` only over an untouched import), `--subtype` limited to the four sub-types and a Strava sub-type outside them refused, `region_problem` (a second spelling of an existing region refused, a new name announced), `day_photo_count` (.webp and .jpg, copies not counted), `bump_end_date`, `rewrite_keys` (the frontmatter round trip, refused where it would change more), `--retime`, the `.zip` input, `--strava-export --list`, the zone it used printed, a numbered checklist, `render.py --status` after a render (whose exit statuses decide the checklist's draw step), one usage line for an unreadable track or zone. |
| `tools/lib/tracks.py` | `read` takes a `.zip` holding one `.fit`, `.fit.gz` or `.gpx` (`zip_member`: read from memory, 50 MB limit, several or none refused by name). `guess_tz` adds America/Phoenix (before Los Angeles), America/Chicago and America/New_York. |
| `tools/lib/fit_reader.py` | `read_fit_bytes`, `read_gpx_bytes`, `read_track_bytes`; `.gz` read in any case and bounded (`GZ_MAX`); GPX bytes must be UTF-8 and hold no `<!` declaration. |
| `tools/lib/strava.py` | `Export.not_imported(known_ids)`, newest first, unreadable rows counted in `skipped`; short rows read as empty cells. |
| `tools/lib/renderkey.py` (new) | `VERSION`, `file_hash`, `trip_inputs`, `input_parts`, `no_route`, `no_track`, `journal_parts`, `site_jobs`, `site_hash`, `goal_has_line`, moved out of `render.py` without a change to any hash. |
| `tools/render.py` | Imports those; `drawing_into` (temp folder, swap, old render kept on any failure or Ctrl+C); `main(argv)` goes on past a failed trip or the site maps and returns 1; `pending_reason`, `pending_trips`, `site_maps_stale`, `status` (`--status`); `inputs` in meta.json; `stored_hash` (a meta.json that does not parse is drawn again); `render_folders` (no dot-names, files, temp or old folders); `cache_report`. |
| `tools/lib/geo.py` | Caches in `~/Library/Caches/personal-website/{tiles,osm}` (`CACHE_HOME`; the old `.cache/` folders kept in use until moved), made on the first download, not at import; `cached_answer` (an answer that does not parse is removed and fetched again, one that cannot be read is kept); new answers stored with their date; `CACHE` counts. |
| `tools/lib/checks.py` | `_render_staleness` and `_site_hash_findings` (maps drawn from other inputs, or without OpenStreetMap data), `_offloaded`, `_inputs` (one hash per trip and run), `_cut_notes` (a note that looks like part of a value), the UTC note, the consequence added to the `no rendered map` warning. |
| `tools/build.py` | `--serve` links unless `--copy`; `--open [SLUG]`, `--watch` (`watch_state`, `changed`, `rebuild` in a child process, `watch`), `serve` (quiet Ctrl+C), `page_url`, `open_in_browser`. |
| `tools/sitegen/pages/report.py`, `multiday.py` | `report.not_rendered_section` (the goal page's box, now shared); a single-day report or a multi-day trip with a track and no render gets it in `#map`, no key rows, caption or map page, and the day chapters of such a trip no map, key or caption. |
| `.gitignore` | `rendered/**/*.tmp-*`, `rendered/**/*.old`. |
| `tests/` | New: `test_add_trip.py`, `test_strava_export.py`, `test_fit_reader.py`, `test_tracks.py`, `test_geo_cache.py`. Extended: `test_frontmatter.py`, `test_build_cli.py`, `test_render_goals.py`, `test_checks_site_maps.py`, `test_checks_more.py`, `test_report_page.py`. Changed to the new rule (a track without a render has no map and no map page): `test_report_page.py`, `test_metadata.py`, `test_sitecheck.py`, `test_build_site.py`, `test_ticklist_page.py`, whose fixtures now give a report a placeholder render where they need its map; the warning's new text in `test_checks.py` and `test_validate_cli.py`. |
| `ADDING-TRIPS.md`, `README.md`, `docs/CONTENT_GUIDE.md`, `docs/DEVELOPING.md`, `docs/TICK_LIST_GUIDE.md`, `docs/PRIVACY_NOTES.md` | The new options and commands, the preview, the error and warning rows, the rules for developers, the Render caches section, the test list. |

### Behaviour

- **Front matter.** `title: Rose Knob  # a note` is the title `Rose Knob`; `#` in quotes, in `[...]` or with no space
  before it stays. A tab-indented line stops the build naming the file and the line. A `#` that looks like part of
  the value (`Lap #2`) is a warning. All 352 index.md and day files parse exactly as before.
- **add_trip.py.** `--force` over a folder with a write-up, a photo description, a line an import never writes, day
  files or a `goal.json` exits 1 and writes nothing, with a message that says what it would erase and how to get the
  old folder back. A second spelling of a region exits 2 naming the spelling to use. `--day-of` counts the trip's day
  photos and moves an earlier `end_date:` to the new day. `--retime SLUG [--timezone Z]` rewrites timezone, date and
  start time from the trip's own track, offline. A Garmin `.zip` is read as it is. `--strava-export DIR --list` lists
  what is on no trip. The run ends with a numbered checklist.
- **Preview.** `build.py --serve --open SLUG --watch` builds linked in about 2 s, opens the page, rebuilds about 2 s
  after a save, keeps the last good build through a content error, and stops quietly on Ctrl+C.
- **render.py.** A failed trip keeps its last good maps, the run goes on, exit 1. `--status` lists, offline, what a run
  would draw and why. A corrupt cached OpenStreetMap answer is fetched again. The caches move out of iCloud Drive once
  Eric moves the old folders.
- **validate.py.** Warns when a trip's maps, or the region and ski maps, were drawn from other inputs or without
  OpenStreetMap data; notes a trip whose time zone is UTC.
- **Pages.** A report or a multi-day trip with a track and no render shows "Map not rendered yet" in place of an empty
  map with a key and a caption, and has no full-screen map page. No published trip is in that state: two builds of
  today's content, before and after the phase, differ in no file.

### Where the work departs from the prompt, and documented rules changed

- **The cache folders** default to `~/Library/Caches/personal-website/`, but a checkout that still has `.cache/tiles`
  or `.cache/osm` and no new folder keeps using the old one, and render.py says so at the end of a run. Without that,
  the first render after the change would have downloaded every tile and answer again (about 1.3 GB, one answer about
  200 MB) and drawn the region maps from newer OpenStreetMap data.
- **`--force`** also refuses a `kind:`, `end_date:`, `journal_highlights:` or `conditions:` line, day files and a
  `goal.json`: the import rewrites index.md from the track, so a goal or a multi-day folder would lose its kind.
- **Strava sub-types** the site lacks (Canoeing, Rowing, Snowshoe, Swimming) are refused, not added to
  `content.OTHER_SUBTYPES`: a new sub-type is a word, an icon and a menu row on the site, a choice for Eric.
- **The site maps' hash** is checked now (the prompt allowed leaving it for Phase 15): `site_jobs` moved with it.
- **`--watch`** rebuilds in a child process, so edits to the page modules and helpers take effect without a restart.
- **`strava_id`.** `add_trip.py --strava-id` writes no `strava_id:` line, as before, so an activity imported that way
  stays on the `--list`. Writing one would add a public line to every new trip, which `docs/PRIVACY_NOTES.md`,
  decision 4, leaves to Eric; the guide says how to add it by hand.
- **Rules changed.** `docs/DEVELOPING.md` "Existing messages are never reworded" (Content checks): the `no rendered map`
  warning gained a consequence at its end, and every guide that quotes it was changed with it. `docs/DEVELOPING.md`
  "No file, no control": a report with a track and no render no longer keeps an empty map section and its map page.
  `docs/CONTENT_GUIDE.md` 7.2 says the same for the author. `ADDING-TRIPS.md` step 3's warning about a `#` note was
  removed (the parser follows YAML now), and its multi-day and PCT steps no longer ask Eric to move `end_date:` by hand.

### Review

Three agents wrote the new tests from a written contract while the code was finished, and a fourth reviewed the
diff of `tools/` read-only. Their findings, all fixed with tests: `--watch` missed a save made during a rebuild; a
folder of zones (`--timezone America`) crashed on Python 3.9; the checklist took an old meta.json for a drawn map; a
damaged track file (bad XML in a .zip, a broken .gz, a folder) ended in a traceback; the Strava sub-type check fired
for `--day-of`; an unreadable (offloaded) OpenStreetMap answer would have been deleted; `.DS_Store` and the temp
folders of another render were taken for trip renders; a meta.json that does not parse stopped every run; UTF-16 GPX
and a gzip that unpacks without end got past the new .zip path's guards; `.FIT.GZ` in capitals read as empty; an
unrendered multi-day trip's day chapters kept key rows; `title: Lap #2` lost its `#2` without a word.

### Checks actually run

All on the working tree of 2026-10-24 (the final state, after the review's fixes), Python as named.

| Check | Result |
| --- | --- |
| `/usr/bin/python3 -W error -m unittest discover -s tests` (3.9.6) | 2,754 tests, OK, none skipped, 72 s (2,481 before the phase) |
| `python3.12 -W error -m unittest discover -s tests` (3.12.11) | 2,754 tests, OK, none skipped, 65 s |
| `python3 tests/run_orders.py --reverse` | 2,754 tests, OK; no region page left registered |
| `node tests/*_harness.js` | maplist 14, series 49, ticklist 91, trips 145 checks passed |
| `python3 tools/build.py --out <scratch> --link --check` | 357 pages, 168 trips, link check OK, 3.2 s |
| `diff -rq` of that build against a `--link` build of `1cb9cf2` made before any edit | no file differs |
| `python3 tools/validate.py` | 0 errors, 1 warning (the planned route without `goal.json`), 468 notes (467 before: the UTC note); no stale-map warning; about 0.4 s |
| Every stored hash in `rendered/` against `renderkey` and against `1cb9cf2`'s `render.py` | 168 trip hashes and the site hash equal on both |
| `python3 tools/render.py --status`, `curl` on PATH replaced by a script that fails and logs | `trips: all 168 up to date`, `site maps: up to date`, exit 0, curl never called, no cache folder made |
| `python3 tools/validate.py --content <fixture>` with a wrong, then a null hash | the two new warnings, one each |
| `build.py --serve --open matterhorn-peak-west-couloir --watch --out <scratch>`, by hand (`open` replaced by a script that logs) | serving 2.1 s after the command; `open` given `/trips/matterhorn-peak-west-couloir/`; photos linked; a save rebuilt 2.4 s later (`rebuilt in 1.8s`); a content error kept the last build serving (HTTP 200) and the fix rebuilt; Ctrl+C: `stopped`, exit 0, no traceback |
| `add_trip.py <synthetic gpx> --slug matterhorn-peak-west-couloir --force ...` on the real trip | refused with exit 1 (`has a write-up, 7 photo descriptions and the beta, map, cover_photo, cover_focal_y and featured lines; --force would erase them ...`); index.md and track.gpx byte-identical; `content/` clean |
| `add_trip.py --strava-export "<the current export>" --list` | 381 activities not on the site, of 721 |
| `python3 tools/privacy_audit.py` | runs; reads no track in a guessed zone, so the wider `guess_tz` changes none of its counts |

Not run: `--serve --copy` by hand (it copies about 240 MB, much of it offloaded by iCloud; the unit tests pin that
`--copy` copies); a real render (render.py needs the internet and rewrites committed files; its new paths are tested
with the drawing stubbed); a real Garmin `.zip` (synthetic archives only); the suite with the deploy runner's
`html.parser` (CPython 3.12.15), which the review gate before a publication runs; a browser look at the new box (no
published page has it, and the prompt asks for no screenshot).

### Remaining issues and author inputs

- **The cache move**, once, before a render and while the disk has room (about 1.4 GB afterwards):
  `mkdir -p ~/Library/Caches/personal-website && mv .cache/tiles .cache/osm ~/Library/Caches/personal-website/`.
  Until then renders keep using `.cache/` in iCloud Drive and say so.
- **The workspace `../CLAUDE.md`** (outside the repository) still says render.py caches in `.cache/`; after the move
  that line, and the iCloud gotcha's mention of the caches, can be shortened.
- **Time zones.** One published trip carries `timezone: UTC` (`validate.py -v` names it); the trips to correct are
  Eric's private list from `docs/IMPLEMENTATION_REPORT.md` 12.12, and `add_trip.py --retime <slug> --timezone <zone>`
  does each in one command. Nothing was re-timed.
- **Strava backfill.** `--list` finds 381 activities of the current export on no trip or day: the pool for later
  imports. Whether `--strava-id` should write a `strava_id:` line (so an import leaves the list) is Eric's call
  (`docs/PRIVACY_NOTES.md`, decision 4).
- **Plan 2** counts 467 validator notes in Phase 9; there are 468 now (the UTC note).
- **Interface copy for Eric to read:** "Map not rendered yet. The GPX file is published: use the Download GPX button."
  and the multi-day variant "... The GPX files of the days are published: use the Download all GPX button."

## Phase 7 - Search and the explorer (2026-10-24)

The second phase of the second plan (`docs/personal-website-improvement-plan-2.md`, section 7, and the Phase 7 prompt
of `docs/claude-code-website-prompt-2.md`), built on branch `phase-7-search-explorer` from `phase-6-author-tools` at
`da8c7cd`, with the default answer to each of its three decisions: the activity word lists as written, `sup` included
(gap3-01); the Trips page's browse block hidden with scripting on, not moved (visual-02, not ia-05); the tick list's form
from six goals, counting active goals only (visual-05). The disk had about 21 GB free throughout, under the plan's
30 GB line: builds were linked into the session's scratch folder, and no worktree or copy of the checkout was made.

### Changed files

| File | Change |
| --- | --- |
| `tools/sitegen/search.py` | `normalize`: an apostrophe (straight or curly) after one letter and before a letter becomes a space (`d'Argentière` → `d argentiere`), every other one is dropped (`Lover's` → `lovers`). `ACTIVITY_WORDS`, `SUBTYPE_WORDS`, `MONTH_NAMES`, `trip_months(t)`, `date_words(t)`; `entry()`'s `k` adds the other forms of the activity and sub-type (less the label's own words), the date words and `route_shape`. `day_entry()` adds `d`, the day's `<month> <day>`, and `f` (`'1'` when the day has photos). |
| `assets/js/pages/explore.js` | `norm` as `normalize`; `has(field, tok)` (a word start); `match`, `score` and `snippet` use it; `relaxOffers` and `moreCount`, exported. |
| `assets/js/pages/trips.js` | State keys `month` (a card is under every month it spans) and `photos`; `dayMonth` and `dayFacets` (a found journal day answers Month and Has photos itself); sorts `longest` and `gain` (`byValue`, `sortedMeta`, `SORTED_HEAD`, `#trx-sorted-m`); `FACETS` / `MORE`; `dayHits` by word start and on the day's date; `warm()` fetches the indexes on the box's focus or a press on the form, quietly; `listImages(on)`; the empty state's buttons (`showOffers`, `takeOffer`; the first also counts the journal days found); the Filters count. |
| `assets/js/pages/ticklist.js` | Word-start search, `MORE`, the Filters count, the empty state's buttons (noun `goal`). |
| `assets/js/pages/notfound.js` | An address `/trips/<words>/` fills the search box, less its one- and two-digit numbers, and the line `Looking for “<words>”?` (text only). |
| `assets/js/base.js` | The Filters button: `.is-more` on the form, `aria-expanded`, remembered per page in `sessionStorage`. |
| `tools/sitegen/core.py` | `search_form` (the header's and the menu's box, a named search landmark; trips/ keeps its Search link); `cover_img(list_sizes=)`; `repeated_titles`; `trip_card` gains `data-month` (every month spanned), `data-photos`, `data-km`, `data-gain`, `repeated` (a screen-reader date on a title more than one card carries) and `list_sizes`; `NAME_GENERIC`, `NAME_MIN`, `NAME_MAX`, `name_words`, `same_name`, the first tier of `related` and its rule line; `card_summary` and `excerpt_parts` cut at a sentence end. |
| `tools/lib/markdown.py` | `plain_sentences(text, limit, floor=1/3)`, `_SENT_END`, `_ABBREVIATIONS`. |
| `tools/sitegen/pages/trips.py` | `LIST_SIZES`, the form's name `Search and filter trips`, the Longest first and Most gain sorts, the Month menu and the Has photos box, `SEARCH_HINT` (placeholder and description), `months_of` (every month spanned), `more_button`, the secondary controls in `div.trx-more`; `regions_of` leaves out a region of journals alone. |
| `tools/sitegen/pages/ticklist.py` | `FILTERS_FROM = 6`, `with_form`; the form's name `Search and filter goals`; below it no form and only the active goals; the Filters button; `No active goals right now.` |
| `tools/sitegen/pages/notfound.py` | `search_block`: the hidden line and a search form to trips/, named `Find a trip report`. |
| `tools/sitegen/pages/home.py`, `region.py` | The recent cards show the write-up's opening (`summary=True`); both pass `repeated`. |
| `tools/sitegen/pages/report.py` | The description's "little writing" rule measures the whole write-up, not the sentence-cut excerpt. |
| `assets/css/base.css`, `pages/trips.css`, `pages/ticklist.css`, `pages/notfound.css` | The header and menu search box; the Filters button and panel below 760 px; the empty state's buttons; the phone list rows (64 px thumbnail, about 70 px a row); `@media (scripting: enabled)` hides `.p-trips nav.trx-browse`; the 404 box. |
| `tests/` | New cases in `test_search.py`, `norm_cases.json`, `trips_js_harness.js` (pure checks and a `phase7Checks` table on the generated page), `ticklist_js_harness.js` (the same), `test_trips_page.py`, `test_ticklist_page.py`, `test_nav.py`, `test_notfound_page.py`, `test_related.py` (`SameNameTests`), `test_summary.py` (`PlainSentencesTests`), `test_home.py`, `test_a11y_static.py` (the new controls' targets, a name for every search landmark); `page_standin.js` gains `insertBefore`; `test_build_site.py`, `test_region_page.py`, `test_trips_js.py` and `test_ticklist_js.py` follow the new markup and counts. |
| `docs/CONTENT_GUIDE.md`, `docs/DEVELOPING.md`, `docs/TICK_LIST_GUIDE.md` | Section 4's excerpt rule; section 6's search contract (word starts, apostrophes, dates, route shapes, journal dates, the header and 404 boxes, the empty state, the Filters button), the alias advice; 7.5's rule; the developer contracts and the test list; the tick list's six-goal threshold. |

### Behaviour

- **Search.** `lovers leap`, `lover's leap`, `lovers` and `lover’s` find the three Lover's Leap reports; `skiing` finds
  all 51 ski reports and scores them as a keyword; `bike` the 61 rides; `loop` the 71 loops; `june 2024` 30 journal
  days and `2024` alone none; `ice` one report (16 before, through every word holding "ice"). A word no longer matches
  inside another, so `horn` stops finding the Matterhorn.
- **Everywhere.** Every page but trips/ has a search box in its header (in the menu on a phone) that lands on
  `trips/?q=…&sort=relevance`; checked in a browser from a report: `lover's leap` gave `4 OF 167 REPORTS`, best match
  first. The 404 page has the same box, filled from a mistyped report address (`/trips/tallac-2026-09-25/` asks for
  `tallac 2026`).
- **Explorer.** Month and Has photos filters (a multi-day trip or the PCT is under every month it spans; a found
  journal day is listed under Month for its own month and under Has photos only with photos of its own); Longest first and Most gain; a search that finds nothing with the
  filters on offers the search without them and the filters without the search, with live counts (`whitney` with
  Climbing on offers `1 journal day matches ‘whitney’ in all activities`); the indexes start
  loading when the box takes the focus. With scripting the browse block is hidden. Below 760 px the menus, boxes and
  sort sit behind a Filters button that shows how many are on; the first card starts at 496 px on a 390 x 844 phone.
  List view below 560 px is a scan list of about 70 px rows, and at every width it takes the .th copy: at 1280 px the
  list view's photos went from 7,283,770 bytes (106 requests) to 3,035,814 (116: the rows on screen when the page
  opens in list view first fetch the card copy).
- **Cards.** 37 of the 39 explorer excerpts that ended mid-sentence end at a sentence now (the other two have no
  sentence end within 180 characters); the Matterhorn's ends at a full stop. Two of the six home recent cards show
  their write-up's opening, and 32 Trips cards whose title another card carries name their date to screen readers.
- **More like this.** On `mount-tallac-2026-02-15` it lists back-at-tallac-with-connor,
  bee-positive-5k-warm-up-tallac-tour and tallac-cathedral-bowl-solo (it listed the two 'Powderhouse lap before work'
  reports and 'Return to Emerald Chute').
- **Regions.** The Trips page counts 14 regions; the PCT's, which holds only the journal, is in neither the browse
  block nor the Region menu, and `?region=pacific-crest-trail` opens the unfiltered explorer.
- **Tick list.** With today's one goal the page is its head and the card, no form; a site with six active goals or
  more gets the form, the status line and the Filters button as before.

### Where the work departs from the prompt, and documented rules changed

- **Elision.** Dropping every apostrophe joined `d'Example` into `dexample`; an apostrophe after a single letter and
  before a letter is read as a space instead, in both normalisers (`tests/norm_cases.json` holds the cases).
- **The sentence floor** is a third of the limit, not the prompt's half: at half (90 of 180 characters) 31 of the 39
  excerpts end at a sentence, because six end their first sentence at 64 to 84 characters; the plan's own count of 37
  (sentence ends from 60 characters) is a third.
- **The report description** keeps its rule (the summary leads when the writing is short), but measures the whole
  write-up: with sentence cuts a long write-up's first sentence could be under 100 characters and lose its place.
- **`LIST_SIZES`** declares 200 px from 760 px, 160 from 560 and 112 below, as trips.css lays the list out; the prompt
  had 1200 px for the first step.
- **The name tier** leaves out a word in three or more place names and a generic part of a name (`NAME_GENERIC`:
  mount, peak, ridge, lake, north, …) as well as words under five letters: the prompt's five-letter rule alone paired
  every 'Mount …' trip. The rule line no-breaks inside each clause and may wrap after a comma, so it fits a phone.
- **Phone list rows** have a 64 px thumbnail at 4:3, not square: a square one with any padding makes rows of 80 px or
  more, and the prompt asks for about 72 (the Map page's rows fit 72 with a flat glyph).
- **`regions_of`** leaves out a region whose every report is a journal, so the browse link the PCT's region had
  (`?region=pacific-crest-trail`) is gone: the journal is found by Format: Series.
- **Rules changed.** `docs/CONTENT_GUIDE.md` 6: an apostrophe is no word break, and the advice to add `Lovers Leap` as
  an alias is gone; the search matches word starts. `docs/DEVELOPING.md`: `match` needs a word start, not a substring;
  the recent cards show a summary; the header's Search is a box.

### Review

An agent reviewed the whole diff read-only (it ran the suites and the harnesses, compared the two normalisers on
20,000 random strings with no disagreement, and used the built site in a browser). Its findings, all fixed with tests:
Month and Has photos let a found journal day through by its journal's card, so `?q=june&month=04` listed all 30 June
days and `?q=june&month=06` none (the card is now under every month it spans, and the day answers both filters
itself: 0, then 30, and 4 with Has photos); the empty state's "without the filters" counted reports only, so a search
that finds only journal days had no way out; the 404 box kept a dated address's month and day (`09 25`), which the
index never holds, so none of the 20 dated slugs found anything; the search landmarks had no names (the 404 page shows
two); `date_words` pairs every year with every month, which only shows for a trip across New Year (none is published:
written into the guide); four sentences of DEVELOPING.md that no longer matched the code; three published titles
copied into `tests/norm_cases.json` (now synthetic; one real title was there before this phase). `LIST_SIZES` below
560 px now says 64 px, as trips.css lays it out.

### Checks actually run

All on the working tree of 2026-10-24 (the final state, after the review's fixes), Python as named.

| Check | Result |
| --- | --- |
| `/usr/bin/python3 -W error -m unittest discover -s tests` (3.9.6) | 2,794 tests, OK, none skipped, 76 s (2,754 before the phase) |
| `python3.12 -W error -m unittest discover -s tests` (3.12.11) | 2,794 tests, OK, none skipped, 67 s |
| `python3 tests/run_orders.py --reverse` | OK; no region page left registered |
| `node tests/*_harness.js` (node 25.8.2) | maplist 14, series 49, ticklist 103, trips 167 checks passed |
| `python3 tools/build.py --out <scratch> --link --check` on 3.9.6 and on 3.12.11 | 357 pages, 168 trips, link check OK, about 2 s |
| The index gate (a script over the build's `search.json` and `journal.json` with explore.js's rules) | every row OK: the counts under Behaviour; `search.json` 76,047 B raw and 17,801 B gzip -9 (limits 80,000 and 20,000) |
| Excerpts counted with the loader | 82 reports with a write-up; 39 cut mid-sentence at 180 characters before, 37 of them end at a sentence now |
| `python3 tools/validate.py` | 0 errors, 1 warning (the planned route without `goal.json`), 468 notes |
| A copy of trips.js broken in one way each (no list swap, no warm, no offers, no photos filter), through the harness with a page model | each one fails its Phase 7 check |
| Chrome (DevTools), the build served under `/personal-website/` with its 404 page | screenshots in `.cache/plan2/phase7/` (trips at 1280 and 390, the list at 390, the tick list at 1280 and 390, the 404 page at 390, a report's header box at 1280, the home recent cards at 1280) beside the `before-` ones; first card at 496 px on 390 x 844; phone list rows 69 px; Filters opens, counts and keeps `?month=06`; the header box from a report lands on the search; list view at 1280 px 3,035,814 photo bytes (7,283,770 before); the four review scenarios above |

One run of `test_trips_js.py` failed a history scenario once while the machine was busy (the module took 76 s, not
16): it passed alone, in the module again and in both full runs above.

Not run: the suite with the deploy runner's `html.parser` (the review gate before a publication runs it); Safari and
Firefox (Chrome only); a screen reader (the landmark names and the screen-reader dates are checked in the markup).

### Remaining issues and author inputs

- **Interface copy for Eric to read:** the placeholder `Search titles, places, peaks, activities, dates or write-ups`;
  the header box (`Search`, its label `Search trips`); the 404 line `Looking for “<words>”?` and its `Search` button;
  `Filters` and its count (` · 2`); `Month`, `Any month`, the month names, `Has photos`; the sorts `Longest first`
  and `Most gain`, the headings `Longest first` and `Most gain first` and the line `MULTI-DAY AND SERIES BY THEIR
  TOTALS · N WITHOUT A DISTANCE, LISTED LAST` (or `GAIN`); the empty state's buttons `N reports match ‘<words>’ in all
  activities` (`… without Region: <name>`, `… without the filters`; `N journal days match …`, `N reports and N journal
  days match …`), `N climbing reports without the search`, `N reports with these filters, without the search`, and the
  tick list's `goal` forms; the search landmarks' names, heard with a screen reader: `Search trips`, `Find a trip
  report` (404), `Search and filter trips`, `Search and filter goals`; the chips `Month: June` and `Has photos`;
  More like this `SAME PLACE OR NAME AND ACTIVITY, THEN REGION AND ACTIVITY, THEN REGION, THEN ACTIVITY · NEAREST IN
  DATE`; the tick list's `No active goals right now.`; the Trips description `Every trip report on one page. Search
  titles, places, peaks, activities, dates or write-ups; filter by activity, region, year, month and format.`
- **Word lists.** `search.ACTIVITY_WORDS` and `SUBTYPE_WORDS` are the plan's lists as written (`sup` in); a word Eric
  would expect and is missing is one line there.
- **`horn`.** A short form typed for a longer name no longer finds it (`horn` for the Matterhorn); an alias is the way
  when people really type it.
- **The name tier's generic words** (`NAME_GENERIC`) are a hand list; a new trip whose place starts with another
  generic word (say `Col`, `Aiguille`) may pair trips that share only that word until the word is added.
- **The month menu** on a phone sits behind Filters with the others; on desktop the controls now take two rows at
  1280 px (search, chips and Region and Year, then Month, Format, the boxes, Sort and the view).
- **Not built here:** `strava_id` writing stays Eric's decision (`docs/PRIVACY_NOTES.md`, decision 4).

## Phase 8 - Publishing loop, CI and recovery (2026-10-24)

The third phase of the second plan (`docs/personal-website-improvement-plan-2.md`, section 8, and the Phase 8 prompt of
`docs/claude-code-website-prompt-2.md`), built on branch `phase-8-publishing-loop` from `phase-7-search-explorer` at
`9877edb`. Eric's answers to its decisions: (a) the checkout moves out of iCloud Drive (he moves it by hand; this phase
wrote the recipe and changed the documents that named the old path); (b) yes, the build leaves a drafted or deleted
trip's own pin and line out of the region maps (decision 12.8, item 22). He chose to leave the two pushes the phase
plans (the rollback rehearsal and the dispatch test) pending until the first publication of Phases 6 to 8: main is
still at `1cb9cf2`, so a push now would put commits on main that the phase branches lack. The disk had about 21 to 22
GB free throughout, under the plan's 30 GB line: builds were linked into the session's scratch folder, and no worktree
or copy of the checkout was made.

### Changed files

| File | Change |
| --- | --- |
| `tools/publish.py` (new) | `publish.py SLUG [SLUG ...] [--message] [--dry-run] [--push] [--allow-unrendered]`: refuses off `main`, with `--push` when main holds earlier commits not on GitHub, with something unrelated staged (renames split into both names), for a slug with no folder and no history, for a trip `render.pending_reason` would draw, when the linked check (`build.main(['--out', '.cache/publish-site', '--link', '--check'])`) fails, for a conflict copy among the files to stage (`git status --porcelain -z --no-renames`), and when what it would commit names a trip that is here but not committed (`content/home.json`, `rendered/site/meta.json`, a link in the write-up: `crossings`); stages `content/trips/<slug>`, `rendered/trips/<slug>`, `rendered/site` and `content/home.json` when they changed; commits `Add <title>`, `Update <title>` or `Remove <slug>`; `--push` pushes `main` and `watch` finds the run (`gh run list --commit`, 15 tries 2 s apart), `gh run watch --exit-status`, prints each trip's live address, that a newer push cancelled the run, or the end of `gh run view --log-failed` and that the old site is still up; gh runs in the checkout; without gh, or signed out, the Actions page and exit 0. |
| `tools/check.py` (new) | validate.py, the suite on `/usr/bin/python3` and `python3.12` with `-W error` (`--quick` skips the second; a missing python3.12 is one SKIP line), `build.py --check --out .cache/check --link`; every step runs, one summary line each with its time, exit 1 on any failure. |
| `tools/doctor.py` (new) | Read-only (`git --no-optional-locks`), offline: disk under 30 GB, `.git/index` present (else `git read-tree HEAD`), stray `.git/index N` copies with the `rm` line, branch, staged or changed tracked files, ahead/behind `origin/main`, identity, conflict copies by top folder (those under `content/` and staged ones named), offloaded tracked files under `rendered/` and `content/` (macOS `SF_DATALESS`), cwebp, node, python3.12, gh. Exit 1 only off main, without `.git/index`, or with a conflict copy staged. |
| `tools/tidy.py` (new) | Lists every conflict copy under `rendered/`, `assets/`, `content/` and `_site/` and the `.git/index N` files; a copy under `content/` or `assets/` (hand-written sources) is marked `identical`, `older` or `DIFFERS` and only listed; `--delete` removes only the copies under `rendered/` and `_site/`, and prints the by-hand lines for the rest. |
| `tools/smoke.py` (new) | Serves a build under `/personal-website/`, dumps five pages from headless Chrome and fails a page without base.js's live region, without its own sign (`CASES`) or with an `Uncaught` error on a Chrome `CONSOLE` line; exit 0 without Chrome. |
| `.github/workflows/pages.yml` | `paths-ignore` for the Markdown the build never reads; `workflow_dispatch` input `ref` used by both checkouts; `actions/setup-node@v4` at Node 22; `actions: read`; a `changed` step (`shell: bash`) that diffs the new commit with the commit of the last push run on `main` that succeeded (`gh run list ... --status success`), `code=true` for a manual run, no such run, an answer that is no commit id or a commit that cannot be fetched, and gates the Unit tests step on it; a `smoke` job after the build (`continue-on-error`, `timeout-minutes: 10`; the deploy job needs only the build) that unpacks the Pages artifact and runs smoke.py; the header comment's "about a minute" for the tests replaced. |
| `tools/sitegen/sitecheck.py` | `aria(out, page)`: `ARIA-REF` for an `aria-labelledby` / `aria-describedby` / `aria-controls` token naming no id of its page, `HEADING` for a level jump of more than one inside `<main>`; run per page in `check()` after the duplicate ids. |
| `tools/sitegen/core.py` | `_ON_MAPS` set by `register_site` (published trips with a track and active goals); `gone_keys(entry)`; `drop_keys(s, keys, where)` removes `a.mk-pin`, `a.mk-line` and `g.mk-cat` (also `.mk-planned`) carrying a gone key, leaves `g.mk-cluster` as drawn, and says once per map file on stderr when a key has nothing to remove; `frag(..., drop=)`; `map_block(site_maps=True)` passes the gone keys. |
| `tools/lib/markdown.py` | `heading_levels`, `heading_jumps`; `to_html(text, heading_shift, top=None)` counts a heading's level from the write-up's own top level, so a write-up led by `##` starts one level under its section as one led by `#` does (no write-up has a heading today). |
| `tools/lib/checks.py` | An error for a write-up (or a day's) whose headings skip a level. The site-map warning now ends `the build leaves its own pin and line out of them; run python3 tools/render.py --site when online (and commit rendered/site/) to redraw the maps, their merged pins and counts`. |
| `README.md`, `ADDING-TRIPS.md`, `docs/DEVELOPING.md`, `docs/CONTENT_GUIDE.md`, `docs/TICK_LIST_GUIDE.md`, `docs/PRIVACY_NOTES.md`, `CLAUDE.md` (new) | The one publish command with the manual steps kept under "What it does"; "When something goes wrong" in three parts (Before the push, After the push, The Mac); the web-edit warning and drafting from anywhere; Setting up a new Mac, Moving the checkout out of iCloud Drive, What is and is not in the repository; the `~/Library/Caches/personal-website/site` build commands; `###` headings in DEVELOPING's Rules (no bullet moved or reworded), check.py, the CI rules, Node 22, the one-module command, one timing, the two-builds diff, smoke.py, the Phase 8 tests; the two new site-check rows; the reworded warning wherever it was quoted; the iCloud path in ADDING-TRIPS.md and TICK_LIST_GUIDE.md replaced; a repository `CLAUDE.md`. |
| `tests/` | New: `test_publish_cli.py`, `test_check_cli.py`, `test_doctor.py`, `test_tidy.py`, `test_smoke.py`, `test_js_bundle.py`, `test_workflow.py`, `test_site_map_prune.py`. Extended: `test_sitecheck.py` (`AriaTests`, and the two lines in the order test), `test_build_site.py` (`DraftedPinTests`), `test_checks_site_maps.py` (the new wording), `test_region_page.py` (the drop warning kept out of the run's output, and asserted where the fixture lists a trip without a track), `test_markdown_headings.py` (new), `test_series_page.py` (a journal write-up's lone `##` heading is one level under its day now). |

### Behaviour

- **Publishing.** `python3 tools/publish.py <slug> --push` replaces the 14 hand steps from the check to the live
  address. On a synthetic trip in a temporary repository `--dry-run` ran the real check (3.6 s), listed the trip's four
  files and wrote nothing.
- **A drafted trip leaves from anywhere.** `draft: true`, committed from a phone, takes the trip's own pin and line
  off the region maps at the next build; `--check` passes without a render (on a fixture it failed with six `BROKEN`
  lines before). A cluster it was merged into keeps its count and tooltip until `render.py --site`.
- **CI.** A push of content alone skips the unit tests (live in about a minute instead of three); a push of only the
  log, the report, the plans or a root `*.md` starts no run; Node is pinned at 22; a smoke job reports and never holds
  the deploy. A manual run can build a past commit (`gh workflow run pages.yml -f ref=<sha>`).
- **The site check** reads ARIA references and heading order: 0 findings on today's 355 pages.
- **Write-up headings.** A write-up's first heading is shown one level under its section whatever number of `#` it
  has, and one that skips a level stops at the content check, naming the file, before the site check's HEADING line.
- **The Mac.** `doctor.py` (0.28 s) and `tidy.py` (0.14 s) say what the checkout holds: today 6,138 conflict copies
  (6,136 under `rendered/`, 2 empty folders under `_site/`), eight stray `.git/index N` files, about 22 GB free, no
  tracked file offloaded.
- **No page changed.** Two `--link` builds of today's content, before the phase and after it, differ in no file.

### Where the work departs from the prompt, and documented rules changed

- **The `changed` step compares with the last successful push run**, not with `github.event.before` as the prompt
  had it: with the prompt's form, a content push after a code push whose tests failed (or whose run a newer push
  cancelled) skipped the tests and deployed that code (the review found it and confirmed it with the step's own
  script). It needs `actions: read` and the runner's `gh`.
- **doctor.py does not stop on a changed tree** (the prompt's 'exit 1 on a dirty tree'): publish.py exists to commit
  such files and refuses only what is unrelated and staged, so doctor warns and says so.
- **tidy.py --delete leaves `assets/` alone**: its files are written by hand, and a copy may hold the newer edit; the
  copies there are compared and listed as under `content/`.
- **The `changed` step reads the diff into a variable** and greps it without `-q`: under Actions' `bash -eo pipefail`,
  `git diff | grep -q` ends the pipe early on a long list and the condition reads false, so a large push with code in
  it would have skipped the tests (shown with `seq 1 300000 | grep -Eq '^1$'`, and pinned by a test with 3,000 files).
- **paths-ignore** also lists the two plan-2 documents and the prompt packs, which the build never reads.
- **smoke.py** matches `CONSOLE:` as well as `CONSOLE(`: Chrome 155 writes `INFO:CONSOLE:2070] "Uncaught ..."`.
- **Completed and archived goals** count as gone from the region maps (the prompt's rule: not an active goal), which
  is what render.py draws anyway.
- **Rules changed.** `docs/DEVELOPING.md` "Existing messages are never reworded": the site-map warning was reworded,
  because its old text sent the author to render before a check that no longer fails; every guide that quoted it was
  changed with it. The plan's "the tests never read content/" holds with one exception, `tests/test_fixture_text.py`,
  which only a change to the tests can make fail, so skipping the tests on content pushes stays safe; DEVELOPING.md
  says so.

### Review

An agent reviewed the whole change read-only (both suites, a scratch build, the tools on the checkout, the step's
script in a temporary repository). Its findings, all fixed with tests: the `changed` step let code whose tests had
failed out with the next content push (now compared with the last successful run); publish.py missed a staged rename
out of another trip and committed it (`--no-renames`), checked the whole working tree but committed part of it (now
refuses a `home.json`, a `rendered/site` or a write-up that names a trip here but not committed), could not publish a
report whose render folder an earlier commit removed (paths kept only when on disk or in the index), would push
earlier unpushed commits unannounced (refused, listed), asked gh outside the checkout and reported a cancelled run as
a failure; tidy.py `--delete` removed hand-written copies under `assets/` (now compared and listed only); doctor.py
blocked the normal publish of changed files (now a warning, without the advice to restore them); a write-up led by
`##` would have failed the new HEADING rule on three page types (headings are now counted from the write-up's top,
and a skipped level is a content error); the dispatch recipe needs the full 40-character id; the README move recipe
lacked the `OLD=` line, a clean tree first and the local commits on `main`; the smoke job had no timeout; two
sentences of DEVELOPING.md about the step were inaccurate.

### Checks actually run

All on the working tree of 2026-10-24 (the final state, after the review's fixes), Python as named.

| Check | Result |
| --- | --- |
| `/usr/bin/python3 -W error -m unittest discover -s tests` (3.9.6) | 2,886 tests, OK, none skipped, 87 s (2,790 before the phase) |
| `python3.12 -W error -m unittest discover -s tests` (3.12.11) | 2,886 tests, OK, none skipped, 114 s |
| `python3 tests/run_orders.py --reverse` | OK; no region page left registered |
| `node tests/*_harness.js` (node 25.8.2) | maplist 14, series 49, ticklist 103, trips 167 checks passed |
| `python3 tools/build.py --out <scratch> --link --check` | 357 pages, 168 trips, link check OK (ARIA-REF and HEADING: 0 findings), about 2 s |
| `diff -rq` of that build against a `--link` build of `9877edb` made before any edit | no file differs |
| `python3 tools/validate.py` | 0 errors, 1 warning, 468 notes |
| `python3 tools/check.py` (before the review's fixes) | validate 0.4 s, tests on 3.9 88.4 s, on 3.12 112.4 s, build check 3.6 s: all passed |
| `publish.py synp-ridge-walk --dry-run` in a temporary repository, the real check | the check built this checkout in 1.8 s; it listed the trip's four files, `would commit: Add Synthetic Ridge Walk`, wrote nothing; 3.6 s in all |
| `publish.watch` with `gh`, on the finished run of `1cb9cf2` (nothing pushed) | found run 38429837834, read its success, printed the live address, exit 0 |
| `gh run list --workflow pages.yml --branch main --event push --status success --limit 1 --json headSha --jq '.[0].headSha // ""'` | `1cb9cf2ec5c19b339147e9df88fc260e5f27bb6d`; an unknown branch gives an empty line |
| `python3 tools/doctor.py`, twice | 0.28 s; `.git/index` size, time and hash and `git status` unchanged |
| `python3 tools/tidy.py` (listing) | 6,138 copies (`_site` 2, `rendered` 6,136) and the eight index copies, 0.14 s |
| `python3 tools/smoke.py <build>` (Chrome 155) | all 5 pages OK, 12 s; with a syntax error appended to the bundle, all 5 fail with the `Uncaught SyntaxError` line |
| `DraftedPinTests` with `core.gone_keys` stubbed to nothing | fails with six `BROKEN` lines: the test sees the change |
| `bash -c 'set -o pipefail; seq 1 300000 \| grep -Eq ^1$'` | not matched (exit 141): why the step greps without `-q` |

Not run: the rollback rehearsal and the dispatch test (both push or deploy; left for the first publication); a
content-only run on GitHub (needs a push); the smoke job and the `changed` step on a real runner (their scripts ran
locally, the step under `bash -eo pipefail` with a stand-in `gh`); `tidy.py --delete` on the checkout (Eric's call);
the suite with the deploy runner's `html.parser`.

### Remaining issues and author inputs

- **The move out of iCloud Drive** is Eric's to do: README.md "Moving the checkout out of iCloud Drive" has the
  commands (clone, bring the unpushed branches over through a temporary remote, copy
  `.cache/p4/PRIVACY_AUTHOR_ONLY.md`, move the render caches). Pending.
- **Cleanup of the old folder**, if it stays a while: `python3 tools/tidy.py --delete` (the 6,138 git-ignored copies),
  then by hand `rm ".git/index 2" ".git/index 3" ".git/index 4" ".git/index 5" ".git/index 6" ".git/index 7" ".git/index 8" ".git/index 9"`,
  and `git gc` once free disk is well above 20 GB and nothing else writes (after the move a fresh clone needs none).
  `.cache/review`, `p5`, `preview` and the rest of `p4` can go; keep `.cache/p4/PRIVACY_AUTHOR_ONLY.md`, and
  `.cache/plan2` until the plan is accepted. Today `git count-objects -v` reports 4,913 loose objects. Pending.
- **The rollback rehearsal** (a doc-only commit, `git revert`, push, time it) and **the dispatch test**
  (`gh workflow run pages.yml -f ref=<HEAD sha>`) were not run: both push or deploy, and Eric left them for the first
  publication. ADDING-TRIPS.md marks them as not yet rehearsed. The watch was tested with `gh` on the finished run of
  `1cb9cf2` (it found run 38429837834, read its success and printed the live address).
- **The first content-only run** after a push is to be checked with `gh run list` (the tests skipped, about a minute).
- **The workspace `../CLAUDE.md`** (outside the repository) can shrink its site section to a pointer to the new
  repository `CLAUDE.md`, and its path and iCloud notes change once the checkout moves.
- **The upload desk stays deferred** (authoring-19): if it is ever built, the 2026-10-08 plan's terms hold: loopback
  only, a per-session token, nothing in the deployed output.
- **Interface copy:** none new on the site. New command output: publish.py's, doctor.py's and tidy.py's lines, and
  one new content error (a write-up heading that skips a level).

## Phase 9 - Content (2026-10-24 and 25)

The fourth phase of the second plan (`docs/personal-website-improvement-plan-2.md`, section 9, and the Phase 9 prompt of
`docs/claude-code-website-prompt-2.md`), built on branch `phase-9-content` from `phase-8-publishing-loop` at `59790c9`.
Eric asked for the phases to run on without waiting for him, so the prompt's recommended answers stand: (c)
`published_at` option A (an empty line at import, filled on the day of the push; old reports stay dateless); (d)
summit outcomes `summit`, `turned-around`, `traverse`; (e) `--update` replaces the stats unless `--keep-stats`, and
refuses `--strip-times`; (f) the home page keeps Lake Tahoe and Eastern Sierra; (g) By year counts calendar years. The
two decisions that are his edits, (a) the region and place merges and (b) the 24 retitles, were not made: nothing
under `content/` changed. Nothing under `rendered/` changed and `render.py` was not run. The disk had about 21 GB free
throughout, under the plan's 30 GB line: builds were linked into the session's scratch folder, and no worktree or copy
of the checkout was made.

### Changed files

| File | Change |
| --- | --- |
| `tools/content_report.py` (new) | Read-only, one row per published report, newest first: date, slug, title flag (`strava` for a Strava default name, `xN` for a shared title), write-up characters, photos, cover source (`explicit` / `auto` / `none`), place, party, card summary. `--missing place\|writeup\|photos\|cover\|summary`, `--alt` (the home features, each region page's Featured row, every cover, with their alt text), `--taxonomy` (regions with slug and count, places per region, names inside names, one region spelt two ways, one-report regions with the region whose trips start within 150 km), `--markdown` (`.cache/content-report.md`). Never writes under `content/`. |
| `tools/trip_photos.py` (new) | `SLUG FILE\|DIR... [--day N] [--cover] [--dry-run]` (`--day` finds `days/03.md` or the journal's `days/003.md`): the import's three copies, numbered after the trip's (or the day's `dNN-`) highest photo, an entry each with an empty `alt:`, `--cover` sets `cover_photo:`; refuses a file whose front matter would not round-trip; ends with the empty alt lines and the content check's findings for the trip. |
| `tools/about_photo.py` (new) | The About page's photo: copies in `content/about/photos/portrait-NN.*` (numbered, so no browser keeps the old one) and a `photo:` block in `content/about.md` with an empty `alt:`; a file of words alone, or with an empty front matter, keeps its words. |
| `tools/add_trip.py` | `TRACK --update SLUG [--keep-stats] [--source S] [--timezone Z] [--dry-run] [--no-render]` (refuses day files, a planned route, a track published without times, `--strip-times` and the new-import options, and, on a trip that credits its stats to a service, new figures without `--source` or `--keep-stats`); `--source` on an import; a note when a title taken from Strava or the file name looks like a Strava default; new imports write an empty `published_at:` line and `source:` (Strava for an export, else only with `--source`); `--keep-stats`/`--dry-run` refused outside `--update` before any branch; `--force` help and refusal point at `--update`; the checklist's publish step names `publish.py`; photo import moved to `lib/photos.py`; `--force` also keeps `summits:`, `conditions:` and a `source:` other than Strava, and an empty kept line no longer blocks it. |
| `tools/lib/photos.py` | `PHOTO_EXT`, `collect()`, `import_photos()`, `next_number()` (from add_trip.py, shared by the three tools). |
| `tools/lib/frontmatter.py` | `dumps`/`render(..., keep_empty=True)` write a top-level `None` as a bare `key:` line, so a file holding the import's empty `published_at:` survives every round trip (`--update`, `--retime`, trip_photos, about_photo). |
| `tools/lib/strava.py` | `default_title()`. |
| `tools/lib/content.py` | `SOURCES`, `has_strava()`, `stats_source()`, `SUMMIT_OUTCOMES`, `_summits()` (trip and day), `publication_utc()`, `content_dir()`, `load_about()`, `load_region_intros()`; `conditions` no longer read; day dicts carry `strava` and `summits`. |
| `tools/lib/checks.py` | `source` (fixed list, an error otherwise), `summits` (index and day files), `conditions` retired with a pointer to `beta:`; `content/about.md` (alt required, file, size, unknown keys, heading levels) and `content/regions/*.md` (unknown slug an error, a region without a page a warning, `title:` must match); `home.json`'s `region_maps`; the per-file caption notes as one count line; a note for a title with Peak, Mount, Mountain, Couloir, Chute, Bowl or Lake and no `map: peaks:`; the site-hash warning accepts the hash without titles, the pre-Phase-9 one, and that one matched with the titles the maps were drawn with. The summit note skips a Strava default title (it names a town). |
| `tools/lib/renderkey.py`, `tools/render.py` | `SITE_INPUT_KEYS`, `site_inputs()`; `site_hash()` without trip titles (journal part and journal titles stay); `site_hash_with_titles()` (the old formula); `drawn_paths()`, `drawn_titles()`, `site_hash_as_drawn()`; `render.site_maps_stale` accepts the same three, and `render_site` asks it, so a run draws no site map that the status calls up to date. |
| `tools/sitegen/core.py` | `relabel()` (pin `aria-label`/`<title>` and cluster `<title>` from the registered titles of every trip but a journal, whose unnamed day parts are labelled 'Title, Day N'; site maps only, through `frag(..., labels=True)`); `via()`; `how_link()` and `stats_note(t, cls, here)`. |
| `tools/sitegen/pages/about.py` | `year_stats()`/`year_rows()` (By year), `site_rows()` (Trips and Tick list), `portrait()`; Eric's words replace the computed lede when `content/about.md` has any. |
| `tools/sitegen/pages/region.py` | The intro under the counts when `content/regions/<slug>.md` has words. |
| `tools/sitegen/pages/report.py` | `summit_item()`, the Summits row of the Beta block; the stats note gets `here`. |
| `tools/sitegen/pages/multiday.py`, `series.py`, `section.py` | The source word from the content; the multi-day and section notes get the link. |
| `tools/sitegen/pages/home.py`, `tools/sitegen/curation.py` | `home_regions()`; `resolve_region_maps()` (one or two names with a region map, spelt as the trips spell them), `region_maps_for()`. |
| `tools/sitegen/search.py` | Summit names (trip and days) in `k`. |
| `tools/build.py` | `pub_moment()`: `<pubDate>` from `published_at` (a date alone at 12:00 UTC), else the trip date, and the 30 items ordered by it; `sitemap(pages, trips)` writes `<lastmod>` from `updated_at` else `published_at`; `build()` reads the site meta once, `region_maps`, `about` and `region_intros`; `copy_about_assets()`. |
| `assets/css/pages/about.css`, `region.css`, `base.css`, `notfound.css` | Portrait at 4:5, the words in the lede's type, `.abo-ic` (with the 404's `.nf-ic`, moved here), year numbers tabular; the grid's second row takes the taller column's extra height and the column sticks only from 1600 px; `.reg-intro`; the footnote link underlined. |
| Docs | ADDING-TRIPS.md "Changing a trip that is on the site" (one table keyed on what the maps are drawn from), the Strava-title note, `--update`, adding photos, the region/place paragraph pointing at `--taxonomy`, publishing with `published_at`; README.md; CONTENT_GUIDE.md 1 (region_maps), 3, 5.1, 5.5 (content_report), 6 (findable checklist), 7.11 (source), 7.12 (conditions), 7.13 (summits), 8, 11.8 (region intros), 11.9 (names and merges), 12 (About); DEVELOPING.md (tool list, renderkey, relabel, trip and site dicts, feed and sitemap rule, Eric's words); PRIVACY_NOTES.md decision 1 names `--update`. |
| Tests | New: test_content_report (8), test_trip_photos (8), test_about_page (20). Changed: test_add_trip (UpdateTests and its guards, published_at, source, `--retime --dry-run`), test_checks (summit-title note, source, summits, conditions, home region_maps, known keys), test_checks_site_maps and test_render_goals (retitles, the old hash, the old hash with drawn titles, `render_site` drawing nothing after a retitle), test_site_map_prune (relabel, the journal left alone) and test_build_site (relabel), test_metadata (feed and sitemap), test_track_rules (SourceWordTests; fixtures carry no strava_id, so their note is the plain sentence), test_report_page (Summits row, the footnote link), test_region_page (IntroTests), test_home and test_curation (region_maps), test_search, test_frontmatter, test_a11y_static (its region page carries an intro). |

### Behaviour

- **Nothing changed for a reader but two things.** A `--link` build of today's content against one made before any
  edit differs in 172 files: `about/index.html` (the By year block and the Browse rows, inserted and nothing else),
  `assets/site.css`, and 170 pages (166 report and multi-day pages and the four section pages with a featured block)
  that differ only by the footnote link, checked file by file with the link removed.
- **About's By year** matches the loader: 2026 58 reports / 70 days out, 2025 36 / 36, 2024 5 / 165, 2023 12 / 12,
  2022 21 / 21, 2021 35 / 35, each with its gain and distance through `core.U`.
- **A retitle costs one trip render.** On today's content in memory, retitling a trip leaves `render.py`'s site maps
  up to date (the stored hash is still the pre-Phase-9 one, matched with the titles the 161 labelled trips show) and
  a stats change still marks them stale; the build writes the new title into the pins and clusters.
- **validate.py**: 0 errors, 1 warning, 346 notes (468 before): the 143 caption notes are one line, and 20 notes name
  a summit-like title without `map: peaks:`.
- **content_report.py today**: 167 rows; 79 without a place, 75 without a write-up, 61 without photos, 164 without an
  explicit cover (103 automatic, 61 with no photo), 167 without a card summary; 24 Strava titles; 15 regions, one pair
  of places with one name inside the other, Idaho named near Boise and Yosemite near Eastern Sierra.
- **Every published page still says "via Strava"**: all 167 tracked reports resolve to Strava through `strava_id`.

### Where the work departs from the prompt, and documented rules changed

- **A FIT or GPX import writes `source:` only with `--source`** (the prompt: "otherwise the file type"). The fixed list
  names services, and a file type is not one: a FIT file can come from any device. Without it the trip's note says
  "Stats from the GPS recording.".
- **`--update` asks where the new recording came from** when the trip credits its stats to a service (every trip today
  has a `strava_id:`): `--source` or `--keep-stats`, so new figures never go out as Strava's. It also refuses a track
  published without timestamps rather than give them back (decision (e) keeps `--strip-times` off updates).
- **The pre-Phase-9 site hash is also matched with the titles the maps show.** The prompt dropped titles from the hash
  and kept the old hash valid; but the stored hash holds the old titles, so the first retitle before the next site
  render would have marked all 76 site files stale. `renderkey.drawn_titles` reads each trip's title from the pins
  and clusters render.py drew; with those, the old formula reproduces the stored hash exactly on today's content.
- **About's words and region intros are read in `build()`, not `site_of()`**, beside home.json, so tests that call
  `site_of` on synthetic trips never read the real files.
- **The PCT page's series note has no footnote link**: the prompt names the report, section and multi-day notes.
- **The portrait** is a nested `photo:` block (file, w, h, alt) in `content/about.md`, its copies in
  `content/about/photos/`, written by a small new tool, `about_photo.py`, since the copies must be made on the Mac
  (CI has no sips or cwebp). The page shows it only with an alt.
- **Summits show on single-day reports only**: the multi-day and PCT pages have no Beta block; their names are
  searchable, which CONTENT_GUIDE 7.13 says.
- **About's layout**: the numbers column grew from 760 to 1,365 px (1,481 at 1000 px, where the year lines wrap), so
  the grid gives its extra height to the second row (it opened a 208 px gap under the intro) and the column sticks
  only from a 1600 px tall viewport.
- **The footnote link is underlined** (`.strip-note a`): in the note's grey and without a line it read as plain text.
- **`conditions:` is retired with its own hint** in the unknown-key warning (where the words go).
- **`--taxonomy` names a one-report region's neighbour** from the trips' rendered start points (150 km; no point is
  printed), so Idaho is named with Boise as the prompt's gate expects; text alone could not pair them.

### Review

One independent read-only review of the whole change (an agent given the prompt, the rules and the diff, not this
log). It ran both suites (2,958 tests then), the linked build check and the content report, and confirmed: the gate's
counts, `relabel` changing nothing on today's 27 site-map fragments, all 352 content files round-tripping byte for byte
with `keep_empty`, no Python 3.9 problem, no accessibility regression. Its findings, all fixed:

1. `render_site` compared the stored hash with the new formula only, so the first render after a retitle (or any slug
   render) would still have drawn all 76 site files although `--status` said up to date. It now asks
   `site_maps_stale`; a test patches `draw_site` to fail and renders after a retitle.
2. `relabel` would have cut "Day N" from a journal's pins for a day part written without a name (keyed by the
   journal's slug). Journals are left out of the titles; a test registers a journal.
3. `--update` kept `strava_id:`/`source:` while replacing the stats, so a Garmin file's figures would have said "via
   Strava". It now needs `--source` or `--keep-stats`.
4. `about_photo.py` refused the empty front matter CONTENT_GUIDE 12 shows (and a file of words alone).
5. `--retime ... --dry-run` wrote: the `--dry-run` check ran after the `--retime` branch.
6. `region_maps` matched by slug, so a second spelling passed and the home page lost its region link.
7. `--force` could drop `summits:`, `conditions:` or a hand-written `source:`.
8. Privacy: examples of Strava default titles and two place names that point at a frequent start were in docs, code
   comments and a fixture; all now generic or synthetic.
9. `--update` would have given timestamps back to a track published without them; refused now.
10. Doc and comment slips (region pages' "all the introduction", the caption-count docstring, the `region_maps` check
    without a site meta, the time-zone row), and small things: `--update` ignoring other options and accepting a
    planned route, `trip_photos.py --day 3` on the journal, the summit note on Strava default titles.

Left as documented: an unknown region-intro slug is an error and a region without a page a warning (the prompt's
"lost its page since" cannot be told from "never had one"); summits show only on single-day reports; By year puts a
trip that crosses New Year in its start year.

### Checks actually run

All on the working tree of 2026-10-25 (the final state, after the review's fixes), Python as named.

| Check | Result |
| --- | --- |
| `/usr/bin/python3 -W error -m unittest discover -s tests` (3.9.6) | 2,966 tests, OK, 88 s (2,886 before the phase). A first run took 146 s and one node harness timed out at 60 s; that module alone and the whole suite again passed |
| `python3.12 -W error -m unittest discover -s tests` (3.12.11) | 2,966 tests, OK, 114 s |
| `python3 tests/run_orders.py --reverse` | OK; no region page left registered |
| `node tests/*_harness.js` (node 25.8.2) | maplist 14, series 49, ticklist 103, trips 167 checks passed |
| `python3 tools/build.py --out <scratch> --link --check` | 357 pages, 168 trips, link check OK, 1.8 s |
| `diff -rq` against a `--link` build of `59790c9` made before any edit | 172 files: `about/index.html` (an insertion), `assets/site.css`, and 170 pages that differ only by the footnote link, checked file by file with it removed |
| `python3 tools/validate.py` | 0 errors, 1 warning, 346 notes |
| `python3 tools/render.py --status` (offline) | trips: all 168 up to date; site maps: up to date |
| A retitle and then a stats change on today's content, in memory | `render.site_maps_stale`: None, then 'a trip on a region or ski map changed' |
| `python3 tools/content_report.py` and its options | the numbers under Behaviour; `content/` untouched (the tests compare the tree) |
| Screenshots (headless Chrome 155; the 390 px ones in an emulated phone viewport) | `.cache/plan2/phase9/`: About at 1280 and 390, a fixture About with words and a placeholder portrait at 1280 and 390, a report's footnote, a fixture region page with an introduction. The fixture pages were written into the scratch build only |

Not run: `render.py` (nothing to draw; the merges' site render is Phase 15); `publish.py` for real; the W3C feed
validator (after a deploy); the suite with the deploy runner's `html.parser`.

### Remaining issues and author inputs

- **79 places** (the one-sitting list: `python3 tools/content_report.py --missing place`), names not addresses. Not
  filled: they are Eric's answers.
- **24 retitles** of Strava default titles (`content_report.py`, title flag `strava`): each now costs the trip's own
  render (`render.py <slug>`), no site render. Not done.
- **Merges** (recommended: Idaho into Boise, and the place pair `--taxonomy` names into its shorter spelling;
  Yosemite stays separate): Eric's call. A region merge needs `render.py --site --force`, queued for Phase 15;
  CONTENT_GUIDE 11.9 has the steps.
- **published_at for the old reports**: left out by decision (c); new imports carry the empty line.
- **The About words and portrait** (`content/about.md`, `about_photo.py`), **region introductions**
  (`content/regions/<slug>.md`), **summit names** (`summits:`) and **`region_maps`** in home.json: dormant until
  Eric writes them; the screenshots in `.cache/plan2/phase9/` show what they would look like.
- **The pre-Phase-9 site hash** stays accepted until the next site render writes the new one, also after a retitle.
- **`--update` on today's trips** needs `--source` (every one carries a `strava_id:`): `--source Strava` for a better
  Strava recording, `--source Garmin` for a watch file.
- **Interface copy, new on the site:** "By year"; "58 REPORTS · 70 DAYS OUT · 125,997 FT GAIN" (REPORT, DAY OUT
  singular); "Browse"; "Trips" / "SEARCH AND FILTER"; "Tick list" / "1 GOAL" ("N GOALS"); the footnote link "How these
  reports are made"; dormant until content exists: the "Summits" row ("via <route>", "(turned around)", "(traverse)"),
  "Stats from the GPS recording(s)." without "via" for a trip with neither `source:` nor `strava_id`, and "via Garmin"
  / "via CalTopo". New command output: content_report.py, trip_photos.py, about_photo.py, `add_trip.py --update` and
  `--source`, and the new check messages (source, summits, about.md, region intros, region_maps, the caption count,
  the summit note).

## Phase 10 - Report and multi-day pages (2026-10-25)

The fifth phase of the second plan (`docs/personal-website-improvement-plan-2.md`, section 10, and the Phase 10 prompt
of `docs/claude-code-website-prompt-2.md`), built on branch `phase-10-report-pages` from `phase-9-content` at
`43a2d9c`. Eric asked for the phases to run on without waiting for him, so the prompt's recommended answers stand: (a)
yes to report-02, report-01 and report-11 (photo-only reports get their lead photo, written reports without photos lead
with the words, multi-day pages get a lead photo and a day strip); (c) yes to the `Track only` tag and a factual More
like this head; (d) elapsed time in the strip, a clock column in the mile table and the GPS max time, all from the
content and the published GPX, and no derived finish time. (b), the lead photo's frame, waits on Eric's look at the
side-by-side sheet (`.cache/plan2/phase10/sheet/hero-frame-sheet.png`); variant A (3:2 from 560 px, one CSS rule) is
built until he picks. Nothing under `content/` or `rendered/` changed, and `render.py` was not run. The disk had about
21 GB free, under the plan's 30 GB line: builds were linked into the session's scratch folder, and no worktree or copy
of the checkout was made.

### Changed files

| File | Change |
| --- | --- |
| `tools/sitegen/pages/report.py` | Four layout cases: `has_photos()`, `written_first()` (a write-up, no photo, `core.written_report`), the hero for a story or a photo-only report; one label table `LABELS` / `ICONS` / `label()` with `STORY_ORDER` / `COMPACT_ORDER`; `section_nav(has_report, has_gallery, has_map=True, chart='')` in page order (Report · Map · Elevation/Speed · Photos); `bottom_bar` items in page order under the table's names; the write-up's h2 `Report`; the phone copy of the stats note under the map (`rep-note-ph`) removed; beta rows link a `url:` (http/https only); the profile section reads the published GPX once (`core.read_track`) for the GPS max time, the mile table's Time column and the readout data; key rows add the base layer's trail and road; captions add the contour interval. `report.elevation_table` moved to core. |
| `tools/sitegen/pages/multiday.py` | Lead photo (`report.hero`, `core.cover_preload` in place of the overview preloads); `photo_strip()` under the stage table; `day_photos()`, `day_content()`; the day nav's written dot and `WRITE-UP · N PHOTOS` line, the phone rows' same words, the Overview line's counts (`days_meta(t, content=True)`); the Moving sub-line (Elapsed · Start) on the rail; a mile table under each day chart; base-layer keys and contour items; the bar's names from `report.LABELS`; the stats note's Moving sentence. |
| `tools/sitegen/pages/section.py`, `series.py` | The featured map's contour item and the featured chart's mile table; the series note's Moving sentence. |
| `tools/sitegen/core.py` | `time_items()`, the Moving cell's 4th item (`strip-c--time`), `strip--1|2`; `read_track()`, `clock()`, `elevation_table(tr, stats, zone=None)` (Time column with a zone), `gps_max_clock()`; `MOVING_NOTE` in `stats_note`; `VERTICAL SCALE ×N`; `contour_items()`; `KEY_SYMBOLS` trail and road, `KEY_HTML` (`Mile (1.6 km)` under KM), `BASE_KEYS` / `base_keys()`, `feature_key` with base keys; `chart_block(..., readout=)`, `READOUT_SAMPLES`, `profile_readout()`; `PHONE_SOLO_MIN_AR` and `--arp` in `photo_rows`; `track_only()` and its tag in `trip_tags`; `related_block`'s head from what the cards share. |
| `tools/lib/checks.py`, `tools/lib/content.py` | `BETA_OPTIONAL = ('url',)`: a beta row's `url:` must pass `content.web_url` (http or https, `//` and a host), the test the page links by; a warning for a key a row does not take. |
| `tools/lib/fit_reader.py` | A GPX time with a fraction keeps its offset: `18:40:00.000Z` was read in the build machine's zone (latent: every published track has whole-second times); a negative offset now parses instead of giving no time. |
| `assets/js/pages/profile.js` (new) | The readout: a crosshair and `7.2 MI · 11,650 FT` (`KM · M` under KM) under a pointer or a sideways finger; hidden on pointerleave, pointercancel and Escape; aria-hidden, never focusable. 3,775 B, 1,731 gzipped. |
| `assets/css/pages/report.css`, `multiday.css`, `base.css` | Hero 3:2 from 560 px (2:1 from 1200 px retired), the strip right under the hero; the stats note under the strip on phones, the strip's sub-lines hidden there but the Moving cell's; the readout's crosshair and label (`touch-action: pan-y pinch-zoom` on the chart); `.mul-pst` photo strip, the day nav's dot and fourth line (one line, the photo count ellipsized in a narrow chip); phone galleries keep a landscape's shape (`--ar`) and a lone photo's down to 0.6 (`--arp`); one- and two-cell strips capped at a four-cell strip's cell width. |
| Docs | DEVELOPING.md (file list, key rows and captions, `trip_tags`, no-file rules, the report-pages section rewritten for the four cases, the label table, the page-order bars, the footnote, the mile table and readout, multi-day lead and strip, the factual head, `--arp`, the trip dict's `url?`); CONTENT_GUIDE.md 7.1, 7.2, 7.3 (frame), 7.5 (head), 7.6, the beta `url` message; README.md (`cover_photo` row); `home.py`'s `rcard` docstring. |
| Tests | New: test_report_phase10 (27: the four cases, multi-day lead and strip, frame, strip time, caption and key items, the tag, beta url, tables everywhere, gallery shapes, readout data), test_profile_js (7, running `tests/profile_js_harness.js`, 35 checks, against the script and against copies broken one line each). Changed: test_report_page (labels, bars in page order, section row, the no-track cases), test_track_rules and test_ticklist_page (the Moving sentence, `Report`), test_related (the head), test_build_site, test_a11y_static, test_checks (beta url, unknown row keys), test_fit_reader (fractional seconds and offsets under three `TZ` settings). |

### Behaviour

- **Which pages changed.** A `--link` build against one of `43a2d9c` made before any edit differs in the 168 trip
  pages, the 167 full-screen map pages (key rows and the contour item), the four section pages with a featured block (the
  featured map's key and contour item, the featured chart's mile table, the tag), and, by the `Track only` tag alone,
  the Ski page, the home page, the explorer (39), the Map page's table (39) and five region pages; and the two bundles. Nothing else.
- **Report layouts today** (156 single-day reports): 61 story; 15 written first; 27 photo-only with a lead photo;
  8 photo-only without one (portrait or square cover); 6 with a write-up under the 100-character floor and no photos,
  which stay compact; 39 track only.
  - The 27 photo-only reports that now lead with their cover, but for three left out here under
    docs/PRIVACY_NOTES.md (two Strava default titles that name a start town, one title that names a routine time):
    tallac-2026-09-24, white-salmon-rafting, tamolich-blue-pool, tumalo-falls-north-fork-to-bridge-creek-loop,
    misery-ridge-loop, tallac-2026-08-23, maggies-peak-with-the-family, false-white-mountain, mount-glory-2026-03-03,
    echo-peak-with-ross, back-at-tallac-with-connor, green-creek-virginia-pass, mount-tallac-sunrise,
    zion-canyon-overlook-and-angel-landing, bryce-canyon, mount-tallac, red-lake-peak-x2, jakes-peak-x-2,
    jakes-peak-to-emerald-bay, scoping-out-the-emerald-bay-chutes, finally-back-to-double-digit-temps,
    exploring-new-trails-in-santa-cruz, little-pre-wedding-hike-in-redwing-mn, half-dome. Locally the full list is the
    rows of `python3 tools/content_report.py --missing writeup` with photos.
  - The 15 written reports without photos that now lead with their words, but for one left out under the same rule:
    cal-trans-wall-climbing-with-adam, pie-shop-climbing-approach, first-uphill-of-the-season,
    fatigued-ride-for-the-enduro-training, first-ride-back-in-awhile, took-some-souls-on-the-climbs-today,
    finally-made-it-back-to-the-flow-trail, good-fun, new-tires-good-conditions-so-much-grip, soquel-demo-forest,
    stretching-out-the-legs, converted-to-clipless, love-a-fire-road-climb-with-a-rave-in-the-background,
    hit-the-three-piece. The six under the floor are not listed (three titles name a start place).
- **Multi-day**: 7 of the 10 multi-day trips have a cover at least 6:5 wide and now open with it; the other three keep
  the map first. Each has the photo strip when a day has photos.
- **The readout** runs on the 149 single-day reports with a drawn chart; its data adds 865 bytes per page (394
  gzipped; the plan estimated about 1.5 KB). Touch emulation (390 px, Chrome's touch events): a vertical swipe that
  starts on the chart scrolls the page 303 px, a sideways drag shows the distance and elevation, lifting the finger
  hides it.
- **Phone loads** (DEVELOPING.md "Measuring page loads": 390 × 844 at 3x, Slow 4G, 4x CPU, median of 3, a gzip server):

  | Page | LCP before → after | Image bytes | Total bytes | Document (gzip) | CLS |
  | --- | --- | --- | --- | --- | --- |
  | half-dome (photo-only, now with a lead photo) | 1,560 → 1,820 ms | 613,590 → 298,402 | 709,305 → 390,544 | 29,422 → 29,818 | 0 → 0 |
  | chamonix-zermatt-haute-route (multi-day) | 1,624 → 1,588 ms | 105,337 → 232,630 | 220,562 → 348,787 | 43,917 → 53,833 | 0 → 0 |

  Both stay under 2.5 s. On half-dome the LCP is now the lead photo (preloaded), and the map preloads it replaced no
  longer pull the map and the first gallery photos in. On the Haute Route the lead photo and the day strip add the
  image bytes, and the six new mile tables add about 8.7 KB of gzipped HTML (1.5 KB on their own: inside the page,
  between the day maps, they compress less).
- **validate.py**: 0 errors, 1 warning, 346 notes, as before.

### Where the work departs from the prompt, and documented rules changed

- **Two Phase 3 decisions reversed** (Eric's yes to report-02 and report-01, decision (a)): plan 9.1's "photo-only
  reports keep the compact page" and the Phase 3 note "multi-day pages get no lead photo". DEVELOPING.md and
  CONTENT_GUIDE 7.1 say so.
- **The written-first floor is `core.written_report`** (100 plain characters), the rule that already decides the
  BlogPosting markup: of the 21 written reports without photos, 15 clear it and the 6 notes under it keep the map
  first.
- **Section names**: the row and bar say Map (not Route), Elevation (not Profile), and Trip details is gone (the row
  never needed it once it followed the page). The write-up's heading is `Report`. A section page's featured block keeps
  its `Trip report` h3 (it is not a report section), and the multi-day stage table keeps its `Route` column.
- **The compact bar kept its items** and only changed order and names, so a phone reader still reaches the same four
  places.
- **The finish time is not shown** (decision (d) and PRIVACY_NOTES 6.2); the mile table's Time column and the GPS max
  time are the recording's own clock in the trip's `timezone:`, and nothing without a zone shows a clock.
- **Multi-day day charts and the section page's featured chart get the mile table without times** (a day has no zone
  of its own in the content); the readout stays on single-day reports, as the prompt says.
- **The map dot** for the readout waits (a ski report draws two route paths), as the prompt says.
- **Contour labels and mile discs inside the renders stay in feet** until Phase 15 draws them again; the caption's
  interval and the key's `Mile (1.6 km)` carry both units now. The contour item shows on single-day and featured
  maps; none of the 68 multi-day day renders records its interval, so those captions gain it at the redraw.
- **The readout formats its numbers in the script**, the one place a distance and an elevation do not go through
  `core.U` (the plan asked for both values prepared at build time: that would double the data). It uses
  `content.FT` and `content.MI`'s values and `html.km`; the elevations are whole metres, so a value can differ from
  the table's by a foot or two. DEVELOPING.md says so.
- **Written-first pages keep the map preloads** by the rule stories without a lead photo already follow: on a desktop
  their short write-ups put the map on the first screen.
- **The multi-day lead photo opens in the viewer on its own** and shows again in its day, as the PCT page's does; the
  footnote's Moving sentence there leaves elapsed time out (the trip strip shows none).

### Review

One independent read-only review of the whole change (an agent given the prompt, the rules and the diff, not this
log). It ran both suites, the linked build check and checks over the built site, and confirmed: every section-row and
bar link lands on an id the page has, 39 title blocks carry Track only, 27 photo-only reports and 7 multi-day pages
gained a lead photo, on all 149 timed tables the strip's Start equals the first row's time, every chart in meta.json
has `pad_l`, the readout's total is within 1.7% of the chart axis, nothing breaks Python 3.9. Its findings:

1. The day nav's fourth line wrapped (`.ml` is a wrapping flex row), so at 1200 px a chip grew to about 92 px in the 80 px
   bar. Fixed: one line, the photo count ellipsized; checked in Chrome at 1200 px (every chip 78 px), CSS test.
2. `touch-action: pan-y` stopped a pinch that starts on the chart from zooming the page. Fixed: `pan-y pinch-zoom`.
3. A GPX time with a fraction lost its offset and was read in the build machine's zone (a Mac and CI would disagree).
   Latent today. Fixed in `fit_reader`, tested under three `TZ` settings.
4. The check passed `https:example.org`, which the page would not link, and ignored misspelt row keys. Fixed: one test
   for both (`content.web_url`) and a warning for an unknown key.
5. The readout formats outside `core.U`. Documented as the one exception (above).
6. The multi-day contour item never shows (no interval in the day renders). The guides now say it waits for a redraw.
7. The multi-day footnote said "elapsed time includes them" under a strip that shows none. Fixed.
8. Docstrings of `report.bottom_bar`, `report.hero` and multiday.py lagged. Fixed.
9. The mile table's last row is the track's end time: a finish time read from the GPX, which the download carries too.
   Kept (decision 13 B); listed below for Eric.
10. Example times in the new docs and a docstring were one named report's real values. Replaced with made-up ones; this
    entry gives none.
11. The multi-day lead photo opens a one-photo viewer. Kept, as on the PCT page, and now documented.
12. Written-first pages preload a map that sits below the write-up. Kept (above).
13. Test gaps: a timed track without a zone or with one zoneinfo does not know, `https:host`, fractional seconds.
    Tests added.

### Checks actually run

All on the working tree of 2026-10-25 (the final state, after the review's fixes), Python as named.

| Check | Result |
| --- | --- |
| `/usr/bin/python3 -W error -m unittest discover -s tests` (3.9.6) | 2,996 tests, OK, 96 s (2,966 before the phase) |
| `python3.12 -W error -m unittest discover -s tests` (3.12.11) | 2,996 tests, OK, 122 s |
| `python3 tests/run_orders.py --reverse` | OK |
| `node tests/*_harness.js` (node 25.8.2) | profile 35, maplist 14, series 49, ticklist 103, trips 167 checks passed |
| `python3 tools/build.py --out <scratch> --link --check` | 357 pages, 168 trips, link check OK |
| `diff -rq` against a `--link` build of `43a2d9c` made before any edit | the pages under Behaviour |
| `python3 tools/validate.py` | 0 errors, 1 warning, 346 notes |
| Phone measurements (`measure.mjs`, the DEVELOPING.md method) | the table under Behaviour, taken before the review's fixes (CSS rules, a footnote sentence and the stricter check, none of which changes what those pages load beyond a few bytes) |
| Touch emulation over the chart (CDP `synthesizeScrollGesture` and touch events) | page scrolls, readout shows and hides |
| Screenshots (headless Chrome; 390 px in an emulated phone) | `.cache/plan2/phase10/`: before and after of the Matterhorn report, back-to-clipless, hit-the-three-piece and the Haute Route at 1280 and 390; the frame sheet; the Matterhorn report at 390 with the footnote under the strip; the readout at 1280; the Haute Route's day nav at 1200 after the fix |

Not run: `render.py` (nothing to draw); Lighthouse (the pre-push session); a real phone.

### Remaining issues and author inputs

- **The lead photo's frame** (decision (b)): variant A, 3:2 from 560 px, is built; B (each photo's own shape, capped
  at 72vh) or C (2:1 from 1200 px, as before) is one CSS rule (`report.css`, `.rep-hero .cover-img`), pinned by
  `HeroFrameTests`. Eric picks from `.cache/plan2/phase10/sheet/hero-frame-sheet.png`.
- **Time zones (IMPLEMENTATION_REPORT 12.12)**: a trip whose `timezone:` is wrong now shows wrong clock times in the
  mile table and after GPS max, until `add_trip.py --retime` fixes the zone.
- **The derived finish time** waits on PRIVACY_NOTES 6.2. With decision 13 B the mile table's last row is the track's
  end time, read from the GPX (which the download carries too): if Eric wants B without it, the table can leave the
  last row's time out.
- **The readout's map dot** waits (two route paths on ski maps).
- **Interface copy, new on the site:** the section names Stats, Beta, Report, Map, Elevation (Speed), Photos (Route,
  Profile, Trip details and Trip report retired on report pages); "Track only"; "Elapsed 5:10 · Start 8:15 AM" on
  phones; "Moving time leaves out stops." and "Moving time leaves out stops; elapsed time includes them."; "Contours
  every 200 ft" / "Contours every 61 m"; "VERTICAL SCALE ×4.0"; "Mile (1.6 km)", "Mile (1.6 km), outbound", "Trail
  (OSM)", "Road"; "GPS MAX … FT AT 10:55 AM"; the mile table's "Time" column; the readout "7.2 MI · 11,650 FT" /
  "11.6 KM · 3,551 M"; More like this heads "EASTERN SIERRA · BACKCOUNTRY SKI", "SANTA CRUZ", "MOUNTAIN BIKING",
  "3 REPORTS"; on multi-day pages "WRITE-UP", "3 PHOTOS", "2 WRITE-UPS · 7 PHOTOS", "DAY 4" and the list name "Days
  with photos". New check messages: "beta[N].url must be a full http or https address, such as
  https://www.example.org/route, got '…'" and the warning "beta[N] has an unknown key 'URL' (is it url:?); a row takes
  label:, value: and url:".

## Phase 11 - The PCT journal, the photo viewer and the full-screen map (2026-10-25)

The sixth phase of the second plan (`docs/personal-website-improvement-plan-2.md`, section 11, and the Phase 11 prompt
of `docs/claude-code-website-prompt-2.md`), built on branch `phase-11-journal-viewer-map` from `phase-10-report-pages`
at `b2a0740`. No decision from Eric was needed; the session made the one the prompt leaves to it, report-18's size cap
(below). Nothing under `content/` or `rendered/` changed, and `render.py` was not run (the route's start is read from
the committed overlays at build time). The disk had about 20 GB free, under the plan's 30 GB line: builds were linked
into the session's scratch folder, and no worktree or copy of the checkout was made. Two parts of the test work went
to subagents in the same checkout, each confined to its own test files: the series harness (Continue reading, the
month bar) and a new harness for base.js's viewer and share sheet.

### Changed files

| File | Change |
| --- | --- |
| `tools/sitegen/pages/series.py` | `day_photos()` and `DAY_ROWS`: a written day's photos through `core.photo_rows` at the write-up's measure, `full=False`; `thumbs()` for track-only days only; `so_far()`, `far_item()`, the `Recorded` cell in `stats_dl(d, far)` and its `Recorded so far` column head; `N MI SO FAR` in the month heads and By-month rows; `WRITE-UP N OF M` in `written_nav`; the first action `btn btn--ink`; the hidden `.ser-continue` link; `share='Share this entry'` on entry links; `core.fullscreen_link` and `core.map_full_link` in the intro; `core.fs_render` in `fullscreen`. |
| `tools/sitegen/core.py` | `photo(..., full=False)` (the `.th` and `.sm` copies only) and `photo_rows(..., name=, full=)`; `fs_render()`, `route_start()` (mapkit's start disc, else the paths), `fullscreen_link()`, `map_full_link()`, `FS_WIDTHS`, `fs_scale()`; `photo_rows(..., narrow=)` (the journal's sizes from 760 px); `map_block` writes `#route-start` in the fs render; `copy_link(..., share=None)` with `data-share`, both icons and `.copy-l`; `lightbox()` with `aria-describedby="lb-live"` and `.lb-file`. |
| `tools/sitegen/pages/report.py`, `multiday.py` | `fullscreen_link` for the corner button and 'Open the full map' after the key rows; `fullscreen_page` uses `fs_render` and gains the bar's second line (`fs_scale` and `NOT FOR NAVIGATION`). |
| `tools/lib/icons.py` | `share`. |
| `assets/js/base.js` | Viewer: history entry on open, `popstate` closes, close takes the entry back off only when it is ours, a leftover entry's mark is cleared on load; the error state (`lb--error`, the caption, 'Open the file', the live region); the opening announcement; the swipe ignores non-primary pointers and `pointercancel`; a capped srcset gets the file back. Share sheet under `(hover: none)` with the clipboard as fallback (`copyPath`). Full-screen map: the start from the start disc, else the first unfaded path (the ascent on ski maps); `is-fit`. |
| `assets/js/pages/series.js` | `openedDay()`; empty months `is-empty` with ', no write-ups' instead of `aria-disabled` / `tabindex`; Continue reading in `localStorage`. |
| `assets/css/base.css`, `assets/css/pages/series.css` | `.lb` `touch-action: pinch-zoom`, `html:has(dialog.lb[open])`, `.lb-file`, `.lb--error`; the copy icons; `.map-full` at 560-1199 px; the fs bar's two lines, `.fs-pan` without a script, `.is-fit`, `.mv-start` and the fs page's root scroll padding, 168 px; `.ser-body .jrows`, the tenth row column and fourth stats column, `.ser-mnav a.is-empty`, `.ser-wnav-c`, `.ser-continue`. |
| Docs | DEVELOPING.md (copy link and share sheet, the journal's photos, distance so far, counter, actions, the viewer on phones, series.js's fifth helper, month bar, Continue reading, the full-screen page, srcsets, icons, the harness list; the Phase 10 hero note in the CSS paragraph); CONTENT_GUIDE.md 7.2 (the full-size map), 7.6 (share), 7.7 (actions, Continue reading, month bar, photos, so far). |
| Tests | New: test_phase11 (26), test_viewer_js (9; `tests/viewer_js_harness.js`, 50 checks, and 50 copies of base.js broken one line each, all rejected), `Phase11Tests` in test_a11y_static (the cascade of 'Open the full map' at nine widths; the dialog's description). Changed: series_js_harness and test_series_js (58 pure checks, 53 page checks; the stand-in's `createElement`, `localStorage` and its `local` fault), page_standin.js (history state per entry, an initial state, `back()` as a later task, selector lists), test_series_page, test_related, test_report_page. |

### Behaviour

- **Which pages changed.** A `--link` build against one of `b2a0740` made before any edit differs in the 168 trip pages
  (the copy control's markup on every one; the photos, rows, counters and actions on the journal; the map links), the
  168 full-screen map pages and the two bundles. Nothing else.
- **The journal's photos (report-18, the size cap).** The written days' 98 photos are justified rows now, the 5 on
  three track-only days keep the square sheet. Measured on the phone profile (390 x 844 at 3x) in the default
  write-ups-only view, scrolled to the end so every lazy photo loads: 3,182,292 B before (98 `.th` squares), 9,239,288 B
  with the cap (98 `.sm` copies), 13,237,218 B without it (83 `.sm` copies and 16 full files). The cap stays: the
  journal never takes a full file (on a 2x desktop the uncapped rows would ask for the 1600 px file throughout), the
  trade-off IMPLEMENTATION_REPORT 12.1 accepts on phones. The first screen is unchanged (114,902 B of images).
- **Phone load of the journal** (DEVELOPING.md "Measuring page loads", median of 3): LCP 1,740 → 1,740 ms, CLS 0.036
  → 0.037, document 87,095 → 92,837 B, images on load 220,712 → 177,882 B (6 → 3), total 370,173 → 335,624 B. The 0.036
  is a shift that was there before (the title's place line arrives after the title); a 0.172 shift this phase first
  added, the share label wrapping the title actions, is fixed (below).
- **Running distance.** The last month's `MI SO FAR` equals the strip's total (both are the sum of the day files); a
  gap in the day numbers adds nothing.
- **The full-screen map (resilience-13).** Of the 168 `map/` pages, the 167 whose map has a route path carry
  `#route-start` inside the frame at mapkit's start disc (all 167 have one; checked by a stdlib script over the
  build); the journal's page has none and its link stays bare; every report's corner button and 'Open the full map'
  name the fragment; `build.py --check` passes with them. With every script removed from the page, three maps (a ride,
  the Matterhorn ski tour, a multi-day ski day) at 375 x 548, 390 x 664, 390 x 844 and 667 x 375 landscape: the start
  inside the map box every time, near its middle where the map can scroll that far, and the page itself never
  scrolled (the bar stays at 57 px).
- **The viewer on a touch screen** (Chrome's touch emulation, 390 px, the Matterhorn report): a one-finger swipe with
  60 px of vertical drift moves to the next photo; a vertical drag on the dialog leaves the page where it was; the
  dialog keeps `touch-action: pinch-zoom`; Next answers a tap; `history.back()` closes it; Close takes its history
  entry back off. A missing file shows 'This photo could not be loaded' and 'Open the file'.
- **validate.py**: 0 errors, 1 warning, 346 notes, as before.

### Where the work departs from the prompt, and documented rules changed

- **The share label of a title-block button is 'Share'**, not 'Share this page': the longer label wrapped the PCT's
  title actions onto a third row on a phone, and the page moved by 56 px when the script ran (CLS 0.172). The long
  control ('Copy link to this page', the report's phone row) becomes 'Share this page'; a PCT entry's 'Share this entry'.
- **The page itself must not scroll to the start**: with only the prompt's half-box margin the browser also scrolled
  the page and the bar (Back, the new scale line) went under the header, so on the fs page alone `html` has a
  `scroll-padding-top` of half the screen plus 100 px, which keeps the viewport's part of the fragment scroll at 0
  (a first attempt, a whole screen of margin on the marker, left the start out of view on short phones; the review
  caught it).
- **The start is mapkit's start disc** where the overlay has one (all 167 today), the path rule only without it: the
  prompt's 'dashed ascent' rule put the start in the wrong place on two ski maps whose recording opens with a descent.
- **The fs bar's scale is redrawn, not copied**: the 718 and 560 px renders are drawn at 1.5x on that page, so the
  render's own groups would be the wrong length; `core.fs_scale` takes their bar widths and labels and draws them at the
  page's size, in `u-mi` / `u-km` groups.
- **A press on Continue reading also stores its entry** (the harness subagent asked): following the offer is reading
  that entry.
- **Empty months are ink-3, not the rule colour**: they are links now and keep a text contrast.
- **The journal's rows use a 12 px gap** (the sheet's gap from 760 px; the report's 24 px is wide in a 620 px column),
  declared in `DAY_ROWS` and series.css alike.
- **The viewer hides a broken image** (`lb--error`) so its glyph and alt text do not show over the backdrop.
- **'Drag to pan' shows without a script** and base.js hides it when the map fits (`is-fit`), as the prompt asks; the
  class `is-pannable` stays for the other case.

### Review

One independent read-only review of the whole change (an agent given the prompt, the rules and the diff, not this
log). It ran the 3.9 suite, the gate script and headless Chrome on the built pages, and confirmed: one history entry
per open, removed by Close and by Back, focus back on the photo; the viewer's srcset gets the file back; the opening
announcement; the last month's SO FAR equals the strip's total; no sideways overflow at 390 or 1000 px; no privacy
problem (the start's position is the first point of a route already drawn in the same page, with its start marker).
Its findings:

1. Without a script the fs map hid the start on short phones (a whole screen of margin kept the box at its top) and
   scrolled the page on very short ones (bar under the header). Fixed with its tested change (half-box margin, the fs
   page's root scroll padding); checked at four viewports (above).
2. The dashed-ascent rule was wrong on two ski maps (215 and 133 px off the drawn start). Fixed: the start disc first,
   in core and base.js; a test.
3. CONTENT_GUIDE said only the PCT's title button reads 'Share'; every title block's does. Fixed.
4. A photo that fails was never announced. Fixed: 'Photo N of M could not be loaded' in `#lb-live`; a harness check and
   a broken copy.
5. A reload while the viewer is open left the entry marked, so the next open stacked a second entry. Fixed:
   `replaceState` on load; the stand-in can open a page on such an entry; a harness check and a broken copy.
6. The journal's photos declared the report's 760-1199 px widths, larger than drawn. Fixed: `photo_rows(narrow=True)`
   declares the 620 px column's widths from 760; a test.
7. 'RECORDED' overflowed the 72 px column at 1000-1199 px. Fixed: 80 px (the title column is 156 px at 1000, titles
   wrap); checked in Chrome.
8. 'Continue reading' moves the page for a returning reader (the title actions grow from 104 to 156 px at 390 px when
   it appears). Accepted and listed below: it appears once, only for a reader with a stored entry, and only on the
   journal.
9. Test gaps: the page's own so-far cell, the journal's 'Open the full map' with its bare link (now only when the
   overview is rendered), a multi-day overview and fs page after `slim`. Tests added.
10. The harness paragraph in DEVELOPING sat between 'By hand:' and its code block. Moved.

### Checks actually run

All on the working tree of 2026-10-25 (the final state, after the review's fixes), Python as named.

| Check | Result |
| --- | --- |
| `/usr/bin/python3 -W error -m unittest discover -s tests` (3.9.6) | 3,036 tests, OK, 105 s (2,996 before the phase). One earlier 3.9 run during the work reported one failure that did not recur on any later run; which test it was was not recorded |
| `python3.12 -W error -m unittest discover -s tests` (3.12.11) | 3,036 tests, OK, 131 s |
| `python3 tests/run_orders.py --reverse` | OK |
| `node tests/*_harness.js` (node 25.8.2) | profile 35, series 58, ticklist 103, trips 167, maplist 14, viewer 50 checks passed |
| `python3 tools/build.py --out <scratch> --link --check` | 357 pages, 168 trips, link check OK (with the `#route-start` fragments) |
| `diff -rq` against a `--link` build of `b2a0740` | the pages under Behaviour |
| `python3 tools/validate.py` | 0 errors, 1 warning, 346 notes |
| route-start script over the build (`p11tools/route_start_gate.py`, scratch) | 167 of 167 pages with a route path marked at the start disc, the journal bare, 0 problems |
| Phone measurements and a scroll-to-the-end byte count (scratch `measure.mjs`, `scrollbytes.mjs`) | under Behaviour |
| Touch emulation of the viewer (CDP touch events and `synthesizeScrollGesture`) and of the fs page with scripts removed at four viewports | under Behaviour |
| Screenshots (headless Chrome; 390 px in an emulated phone) | `.cache/plan2/phase11/`: the PCT page at 1280 and 390 before and after (top, Day 1, Day 15's photos); the Matterhorn report's map section at 1024 with 'Open the full map'; the fs pages at 390 with scripts removed (with the new bar); the viewer's error state at 390; the journal's row at 1000 |

Not run: a real phone (item 13, below); `render.py`; Lighthouse (the pre-push session).

### Remaining issues and author inputs

- **The sizes cap**: decided, the cap (journal photos stop at the `.sm` copy). If the photos look soft on a large 2x
  screen, `full=True` in `series.day_photos` lifts it (13.2 MB instead of 9.2 MB on a phone that scrolls the journal).
- **The real-phone look (item 13): pending.** The share sheet needs https, so it can only be tried on the published
  site; the other two can be tried before. Five minutes on an iPhone in Safari (and an Android phone in Chrome if one is
  at hand), after the push or in the review gate before it:
  1. Open a report with several photos (the Matterhorn report), tap a photo, then use the Back gesture (swipe from the
     left edge): the viewer should close and the report stay. Open it again and close with the X: Back should then
     leave the report, as usual.
  2. In the viewer, swipe left with a finger that also drifts up or down: the next photo should come, the page behind
     should not move, and a pinch should still zoom.
  3. In Settings > Safari > Advanced, turn JavaScript off; open the report's map, tap the corner button: the full map
     should open on the start of the route with the Back button and the scale line in view. Turn JavaScript back on.
  4. On the PCT page, the title's button should read 'Share' and open the share sheet.
  Tell the session what each did; it goes in the next log entry and closes IMPLEMENTATION_REPORT 15.5's "never run".
- **Continue reading moves a returning reader's page once** (finding 8): accepted; reserving 52 px for a link most
  visits never show would cost every visit.
- **A known edge**: a photo opened within a few milliseconds of closing the last one can be closed again by the close's
  own `history.back()` landing late (the harness cannot step between the two tasks). No fix: no reader taps that fast.
- **The pre-existing 0.036 CLS** on the journal (the place line under the title) is left for Phase 13's sweep.
- **The hero frame** (Phase 10, decision b) still waits on Eric's look at `.cache/plan2/phase10/sheet/hero-frame-sheet.png`.
- **Interface copy, new on the site:** "Recorded so far" (column head) and "Recorded" (its cell, read out); "254 MI SO
  FAR" (rows on phones, month heads, By-month rows); "WRITE-UP 12 OF 32"; "Continue reading: Day N · <title>"; ", no
  write-ups" (read out on an empty month); "Share", "Share this page", "Share this entry"; "This photo could not be
  loaded" and "Open the file"; "Open the full map"; "NOT FOR NAVIGATION" on the fs bar; "Day 15, photo 2 of 4, full
  size" (read out for a journal photo without alt text).

## Phase 12 - Maps on pages (2026-10-25)

The seventh phase of the second plan (`docs/personal-website-improvement-plan-2.md`, section 12, and the Phase 12 prompt
of `docs/claude-code-website-prompt-2.md`), built on branch `phase-12-maps-on-pages` from `phase-11-journal-viewer-map`
at `67aa468`. Eric asked for the phases to run on without waiting for him, so the prompt's recommended answers stand
for the two decisions it asks at the start: (d) no fourth title action, (e) yes to full-screen region maps; and (c),
recommended yes, the journal's month bar releases under 480 px of height. The two layout choices the prompt leaves to
Eric after he has seen pictures, (a) gap1-01's 1005 px column and hung stats strip and (b) qa-04's season dimming, were
not taken: side-by-side sheets were built for each and neither is applied. gap1-05 (the Ski list's stat cells two by
two) has no decision attached and is built, with a before-and-after sheet. Nothing under `content/` or `rendered/`
changed, and `render.py` was not run (every new attribute on a pin, line or cluster is added at build or run time). The
disk had 18 to 20 GB free, under the plan's 30 GB line: builds were linked into the session's scratch folder, and no
worktree or copy of the checkout was made. The harness work for the map scripts went to a subagent in the same
checkout, confined to the test files.

### Changed files

| File | Change |
| --- | --- |
| `tools/sitegen/core.py` | `_LISTED` and `_PANELS` (set in `register_site`); `region_link(here, region)` (the region page, else map/); `region_row_href(here, t)` (the trip's own row, `#arc-row-<slug>`, on its region page or map/; the plain region link for a trip no list rows; None); `see_on_map(here, t)` ('See on the <Region> map', with a track only); `place_line(t, items, here)` links the region (`a.mi-a`); `fs_scale(..., site_maps=)` for a site map. |
| `tools/sitegen/pages/archive.py` | `region_row(..., region=)` writes `id="arc-row-<slug>"` in the trip's own region list and `data-kind`; `journal_part_id()` and the journal rows' ids; `inject_acts()` (`data-act` on tracks, pins and journal lines, `data-acts` on clusters); `_site_draws`, `CLUSTER_SYM` and `region_key()` moved here from home.py; `region_panel`: the phone map's credit tag and full-screen button (only for a region with a panel on map/), the legend under the caption with `data-act` items and the compact key row, `#arc-count-<slug>`, `p.arc-plive`; the year lists' ids; `region_fullscreen()`; `build()` returns map/ and one `map/<slug>/` per panel. |
| `tools/sitegen/pages/home.py` | Uses archive's `region_key`; the phone maps' full-screen button for a region with a panel on map/. |
| `tools/sitegen/pages/report.py`, `multiday.py` | The place line's region link; the region cell of the goal pager to the planned route's row; 'See on the <Region> map' after the route map's caption and the multi-day overview's. |
| `tools/sitegen/pages/section.py` | `areas(ts, here)` and `totals_line(..., here)`: region names in the head link (one region's places stay text); the ski panel's region labels link. |
| `tools/sitegen/pages/region.py` | `activity_items()` and the head's activities line (`.reg-acts.reg-x`). |
| `tools/sitegen/pages/series.py` | `region_parts()`: the journal's parts on region maps under its overview map. |
| `assets/js/base.js` | `folded`, `openRow`, `countOf`, `panelList`, `select`, `unselect`, `untap`: a cluster of a map with a region list selects its rows (button, `aria-pressed`, the count line's 'N reports start here · Show all'); a second press, Escape, that Show all or the list's own Show all / Show fewer clears; a hover elsewhere returns to the selection; rule D4 revised (such a cluster is a named button; the Ski panel's keep their plain click); touch taps (`(hover: none)`), a tap off the pin or Escape ends a pick; `data-fs="region"` centres the whole map. |
| `assets/js/pages/archive.js` | Landing on `#arc-row-<slug>`; the legend's activity toggles, which unfold the list while on; the phone year folds on map/, which the activity filter, a year link, an address and a turn past 760 px open. |
| CSS | base.css: `.ml`'s clip reaching past the line, `.mi-a`, the linked cluster's ring (not dimmed when focused), `.is-sel`, `.is-out`, the journal line's focus halo and its forced-colours form, the coarse-pointer hit stroke, the landscape fs page. archive.css: the phone caption and compact key, the stuck column's fit and release, the legend toggles (24 px apart when stacked) and one-row legend, `.is-off` / `.is-actoff`, `.arc-sel-clear`, the year folds. multiday.css: the day maps to `--col-max`, the compact rail and its release. section.css: `100svh`, the phone render on short windows, the 2 x 2 stat cells at 960-1099. region.css, series.css: the activities line, `.ser-parts`, the month bar's release. |
| Docs | DEVELOPING.md: the Sticky parts rule and table, rule D4 revised and the halo, the Phase 12 map and region section, the harness paragraph. CONTENT_GUIDE.md: 11.2 (the activities line, the map's interactions, the phone folds), 11.5, 7.2 (the full-size map in landscape), 7.7 (the month bar); one example's real place names replaced with PLACE A/B/C. |
| Tests | New: test_phase12 (18). Changed: maplist_js_harness.js (45 checks, from 15; the stand-in's `>` and `^=` selectors, bubbling, `preventDefault`, focus events, `innerHTML`, a `matchMedia` stub that keeps change listeners, a Ski panel) and test_maplist_js (47 one-line broken copies, all rejected); test_region_days (journal row ids); test_a11y_static (D4 named and unnamed clusters, the halo, the Sticky parts table at six sizes with the Ski panel and the fs box, the Ski panel's phone render, the month bar, the explorer links, map/<slug>/ pages, target sizes, the review's CSS fixes); test_region_page, test_archive_page, test_build_site, test_home and test_report_page for the ids, the legend's place, the live line, the full-screen pages and the new links. |

### Behaviour

- **Which pages changed.** A `--link` build against one of `67aa468` made before any edit differs in the 168 trip pages
  (the place line's region link on all; 'See on the <Region> map' and the region cell's target where they apply), the
  eight region pages, map/, home, the five section pages and the two bundles, and has eight new pages, `map/<slug>/`
  for the eight region maps. The 168 trips' own full-screen pages are unchanged.
- **Row ids and landing (gap4-01 to gap4-04).** Every row of a region list carries its id once per page (on map/, a
  trip a stale render still draws in another region's panel is listed there without the id); journal rows are
  `arc-row-<region>-<part>`. `build.py --check` passes with every 'See on the … map' link, every region cell and every
  PCT part link resolving. The PCT page lists its three parts on region maps (two on Lake Tahoe's, one on the Eastern Sierra's) under its
  overview map.
- **Explorer links (ia-09, ia-10, ia-12).** The place line links the region at every width (the crumb is hidden under
  760 px); the region pages head with their activities and counts, each to `trips/?region=…&activity=…`; the section
  heads link their region names (Mountain Biking: three regions and '2 MORE').
- **Map interactions (qa-02, maps-07, gap1-03).** A cluster on a map with a list is a button named 'N reports start
  here' (N counts reports; a cluster of planned routes says so); pressing it narrows the list to its rows and the count
  line to 'N REPORTS START HERE · Show all'; a second press, Escape, that Show all or the list's own Show all / Show
  fewer brings the list back, and the focus stays on the cluster even when its rows were folded. The legend's
  activities are toggles: the other activities' markers fade to 15 %, their rows go, the list unfolds while the filter
  is on, and the live line says 'N of M reports'. On a touch screen a first tap on a pin or line shows its row and a
  second opens the report. Home's maps behave as before, and so do the Ski panel's clusters (a click brings the first
  of their reports into view).
- **Phones (phone-03, phone-04).** map/ at 390 x 844 is 9,141 px tall instead of 17,498 (every year of 'All reports'
  after the first folds behind 'Show N reports', the Planned group behind 'Show 1 planned route'); a region page is
  7,997 px instead of 11,019. The region maps carry the credit tag in the corner, a two-line caption and the compact
  key row; the 44 px corner button opens `map/<slug>/`.
- **Phone load** (DEVELOPING.md "Measuring page loads", median of 3; before → after, the final build): map/ LCP 1,744
  → 1,756 ms, CLS 0.041 → 0.041, document 125,070 → 128,063 B, total 268,258 → 277,329 B; regions/lake-tahoe/ LCP
  1,648 → 1,640 ms, CLS 0 → 0, total 261,651 → 269,554 B; the new map/lake-tahoe/ LCP 1,580 ms, CLS 0, 186,129 B.
- **Sticky parts at laptop sizes** (headless Chrome, CSS viewport heights): at 1366 x 683 the stuck Lake Tahoe column
  runs from 96 to 671 px (map 541 px wide, caption to 615, the one-row legend to 671); at 1280 x 620 from 96 to 608
  (map 468 px). The Ski panel shows the phone-shaped render at both (362 and 311 px wide, panel bottom 671 and 608) and
  the wide render at 1366 x 900. The Haute Route rail's 'Day N GPX' button ends at 592 px of 683 and 616 of 620. On a
  667 x 375 landscape phone the full-screen map box is 307 px, 82 % of the screen. The PCT month bar is static at
  667 x 375 and sticky at 390 x 844.
- **Layout fixes that need no decision.** The day maps and day profiles share the overview's right edge at 760-999 px;
  the Ski list's stat cells go two by two at 960-1099 px (sheet below); a focused journal line shows a faint halo
  without a script.
- **validate.py**: 0 errors, 1 warning, 346 notes, as before.

### Where the work departs from the prompt, and documented rules changed

- **Rule D4 revised (DEVELOPING.md).** A cluster marker was an unnamed, unfocusable pointer target. On a map with a
  list (map/, the region pages) it is now a named button: base.js takes `aria-hidden` off and gives it `role="button"`,
  `tabindex="0"`, `aria-pressed` and an `aria-label`, and focus listeners. On home's maps, which have no list, a cluster
  is as it was. A cluster whose keys are none of the list's rows (a stale render) stays unnamed.
- **The legend filter unfolds the list.** The prompt asks the filter to hide the other rows; with the list folded
  that could leave none on view (the review's first finding), so the filter also opens the fold while it is on.
- **The cluster count rule.** 'N reports start here' counts report rows only, as the prompt asks; a cluster of planned
  routes alone is named 'A planned route starts here' / 'N planned routes start here' rather than '0 reports'.
- **The legend's place (gap2-06).** The legend moved under the caption in the map column at every width (one element,
  no JavaScript condition), as one wrapping row from 1000 px; under 560 px the compact key row stands in for it.
- **The full-screen button only where the page exists.** map/ writes `map/<slug>/` for each of its panels; a region
  page or a home block whose map names none of the site's trips until the next render (so map/ has no panel for it)
  has no corner button, and the journal's part links skip such a region, rather than link to a page or row that is not
  built. The prompt did not cover the case.
- **The sticky table's sizes.** The prompt's five sizes plus 1300 x 599, the column release; the evaluator does not
  compute `calc()`, so a fitted part is asserted by its declaration.
- **gap1-01** is split: the day maps' alignment to the overview at 760-999 px has no decision attached and is built;
  the 1005 px column and the hung stats strip wait on Eric.
- **CONTENT_GUIDE.md** had an example naming real places (the 'same place' one in section 11); it reads PLACE A, B
  and C now.

### Review

Two rounds of finding, before the commit. First, the subagent that wrote the map scripts' harness cases found five
script bugs, each left with a failing case and then fixed: a press on a cluster of folded rows moved the focus to the
first revealed row (so a second Enter followed that link); `openRow` took rows set aside by a selection or the legend
for folded ones; a cluster none of whose keys the list rows became a button saying '0 reports'; the Planned year's
fold called a planned route a report; the selection's count line had an ordinary space where the others are no-break.

Then one independent read-only review of the whole change (an agent given the prompt, the rules and the diff, not this
log). It built the site, ran the 3.9 suite and the harness, and checked six of its findings in headless Chrome. It
confirmed: every row id and anchor resolves, including a trip filed in two regions, a stale render, journal parts on
two maps and completed goals; all 463 tracks, pins and lines carry `data-act` and all 42 clusters `data-acts`; the
stuck column fits at 1366 x 683 and 1024 x 640; the year folds and hash unfolding work at 375 px; no rule is lost to a
later one; no privacy problem (the fixtures are synthetic; the diff removed two real place names from a comment).
Its findings, all fixed:

1. The legend filter left the list folded: on Lake Tahoe's page 'Backcountry Ski' left 0 rows on view under '37 of 86
   reports'. The filter now unfolds the list (hiding 'Show all N') and gives the fold back when it ends.
2. The Ski page's clusters became selection buttons (its list names the map too), hiding all but 4 of 51 rows with
   nothing saying why. Only a map with a region list (`ol.arc-rows`) has selection buttons; the Ski panel's clusters
   keep their earlier click and stay unnamed.
3. Two new 44 px hit areas were cut to 16 px by the meta line's `clip-path` (the place line's region link, a section
   head's region names, the count line's 'Show all'). The clip now reaches 16 px past the line above and below and
   8 px to the right; the left inset that hides the dots is unchanged. Checked: the region link answers 12 px above
   and below its 16 px box.
4. A focused cluster was dimmed to 20 % with the tracks it picks out, its ring with it. `:focus-visible` is excepted
   as the pressed state was.
5. 'Show fewer' during a selection emptied the list. The list's own 'Show all N' / 'Show fewer' now ends the
   selection first; the press base.js makes itself to show a selection's folded rows does not.
6. Escape on the count line's 'Show all' dropped the focus to the page. It goes back to the cluster.
7. The full-screen region page had no key on phones (the legend is hidden under 560 px). It has the compact key row.

Its smaller points: a cluster of planned routes alone wrote '0 REPORTS START HERE' (now 'N PLANNED ROUTE(S) START
HERE'); a phone turned past 760 px kept its folded years (they open now); a touch pick survived a tap elsewhere and
Escape, and `.is-sel` had no style (both fixed); stacked legend buttons overlapped by 14-20 px (24 px apart now, so
each keeps its 44 px; in the one-row legend from 1000 px two wrapped rows still overlap, and each button keeps at
least 24 px of its own); the Ski panel's region labels show without a script only and had no hit area (`.mi-a` now;
the docs said they were visible links, corrected); a region row link could name a row map/ does not build for a
mapped region with neither a page nor a panel (plain region link now); an activity link read 'BACKCOUNTRY SKI37
reports' (now 'BACKCOUNTRY SKI: 37 reports'); CONTENT_GUIDE quoted a real cluster count (now 'N'); the sticky table
left the Ski panel and the fs box to string checks (both in the per-size table now); two docs passages and a test
comment misdescribed the live line and the full-screen page. Each fix has a harness check or a static test, and the
harness rejects 10 more broken copies (47 in all).

### Checks actually run

All on the working tree of 2026-10-25 (the final state, after the review's fixes), Python as named.

| Check | Result |
| --- | --- |
| `/usr/bin/python3 -W error -m unittest discover -s tests` (3.9.6) | 3,062 tests, OK, 106 s (3,036 before the phase) |
| `python3.12 -W error -m unittest discover -s tests` (3.12.11) | 3,062 tests, OK, 130 s. An earlier 3.12 run, made at the same time as a 3.9 run, timed one trips harness subprocess out at 60 s; it passed alone and on every later run |
| `python3 tests/run_orders.py --reverse` | OK; no region page left registered |
| `node tests/*_harness.js` (node 25.8.2) | maplist 45, profile 35, series 58, ticklist 103, trips 167, viewer 50 checks passed; the maplist harness rejects all 47 broken copies |
| `python3 tools/build.py --out <scratch> --link --check` | 365 pages, 168 trips, link check OK |
| `diff -rq` against a `--link` build of `67aa468` | the pages under Behaviour (185 changed files, 8 new pages) |
| `python3 tools/validate.py` | 0 errors, 1 warning, 346 notes |
| Phone measurements and page heights (scratch `measure.mjs`, CDP at 390 x 844) | under Behaviour |
| Sticky parts in headless Chrome (scratch `sticky.mjs`) at 1366 x 683, 1280 x 620, 1366 x 900, 667 x 375, 390 x 844 | under Behaviour |
| The review's fixes in headless Chrome | the legend filter on Lake Tahoe's page (10 rows on view → 37 under 'Backcountry Ski' → 10 and 'Show all 86' after), a keyboard-focused cluster at opacity 1, Show fewer ending a selection, the Ski page's 17 clusters unnamed with a click to the first row (51 rows still on view), the place line's region link answering 12 px above and below its box at 375 px, the fs page's compact key at 375 px and its legend at 1280 |
| Screenshots (headless Chrome) | `.cache/plan2/phase12/`: map/ at 390 before and after (top, caption; All reports before); regions/lake-tahoe/ at 390 before and after; the stuck map at 1366 x 683 and 1280 x 620 before and after; the ski panel at 1280 x 620 before and 1366 x 683 after; the Haute Route rail at 1280 x 620 before and after; a report's and a region's full-screen map at 667 x 375; a report's Route section with 'See on the Lake Tahoe map' at 1280 and 390; the journal at 900 x 460; the sheets for gap1-01, qa-04 and gap1-05 |

Not run: a real phone; `render.py`; Lighthouse (the pre-push session).

### Remaining issues and author inputs

- **(a) gap1-01, the report's map column at 1000-1199 px: waits on Eric.** Two changes, each to be taken or left: the
  stats strip hung from the map column, and the column raised from 860 to 1005 px. Side by side at 1024 and 1180 px
  (today, A, B, A + B, each with a close-up of the map): `.cache/plan2/phase12/sheets/gap1-01-sheet.png`. Nothing is
  applied.
- **(b) qa-04, the ski season band dimming the region map: waits on Eric.** 'All' beside a chosen season:
  `.cache/plan2/phase12/sheets/qa-04-sheet.png`. Not applied.
- **gap1-05, built:** the Ski list's stat cells two by two at 960-1099 px, before and after at 960, 1024 and 1100 px:
  `.cache/plan2/phase12/sheets/gap1-05-sheet.png`. One rule in section.css if he would rather not.
- **(c), (d), (e)** were taken as recommended (month bar released under 480 px of height; no fourth title action;
  full-screen region maps).
- **The cluster count rule:** 'N reports start here' counts the report rows a cluster stands for, never a planned
  route; a cluster of planned routes alone says 'A planned route starts here'.
- **Rule D4 revised:** a cluster beside a region list (map/, the region pages) is a named, focusable button; on home
  and on the Ski panel a cluster stays an unnamed pointer target, out of the Tab order (DEVELOPING.md).
- **The one-row legend from 1000 px:** when it wraps to two rows its 44 px buttons overlap by up to 20 px (each keeps at
  least 24 px of its own). Spacing the rows out would overflow the stuck column's budget at 683 px; left as it is.
- **The real-phone look** (Phase 11's five minutes) can now also cover Phase 12: on Lake Tahoe's region page on an
  iPhone, tap a pin once (its row should open and name the trip) and again (the report should open); tap a numbered
  circle (the list should narrow to its reports, 'Show all' bringing the rest back); turn the phone sideways on a
  full-size map (`map/lake-tahoe/`: the map should take most of the screen).
- **Interface copy, new on the site:** "See on the <Region> map"; the region head's activities line ("BACKCOUNTRY SKI
  37 · CLIMBING 13 · …", read "BACKCOUNTRY SKI: 37 reports"); "N reports start here" / "1 report starts here" / "A
  planned route starts here" (a cluster's name, read out); "N REPORTS START HERE · Show all" (the count line during a
  selection); "N of M reports" and "All M reports" (read out by the legend filter); "Show N reports" / "Show 1 planned
  route" / "Show fewer" (the phone year folds); "Days 67–76 · Lake Tahoe map (Pacific Crest Trail)" (the journal's
  parts); "Open the full map" (the corner button, read out); on the full-size region map, "Back to the map", "Drag to
  pan", "NOT FOR NAVIGATION", the title "<Region> map" and the description "Full-size map of <Region>."; "Several
  reports start here" in the phones' compact key.
- **Carried from earlier phases:** the hero frame (Phase 10, `.cache/plan2/phase10/sheet/hero-frame-sheet.png`); the
  mile table's last row (Phase 10); the real-phone look (Phase 11); the checkout and cache moves, `strava_id`, the
  rehearsal push (Phase 8); the place names, the retitles and the merges (Phase 9).

## Phase 13A - Header, menu and units (2026-10-25)

The first of Phase 13's three sessions (`docs/personal-website-improvement-plan-2.md`, section 13, and Prompt 13A of
`docs/claude-code-website-prompt-2.md`), built on branch `phase-13a-header-menu` from `phase-12-maps-on-pages` at
`09e0e97`. Eric asked for the phases to run on without waiting for him, so the recommended answers stand for both
decisions: (a) gap6-02, the Units row moved to the top of the phone menu (plan 8.1 kept), and (b) yes, a browser whose
language is not English starts in kilometers. Nothing under `content/` or `rendered/` changed and `render.py` was not
run. The disk had 17 GB free, under the plan's 30 GB line: builds were linked into the session's scratch folder, and no
worktree or copy of the checkout was made.

### Changed files

| File | Change |
| --- | --- |
| `tools/sitegen/core.py` | `PREPAINT`, the head's inline script: `js` on `<html>`, then the units (the stored choice, else km for a set, non-English `navigator.language`, else miles); `site.js` with `onerror` taking `js` (and `km`) back off; `header(..., page_bar=None)`: a Home row first in the menu's Site list (`page` on the home page), `a.ab-page` for a page bar, the Units row first in the menu's nav; `document(..., page_bar=None)`. |
| `tools/lib/icons.py` | `home`, `arrow-up`. |
| `tools/sitegen/pages/trips.py`, `archive.py`, `section.py`, `region.py`, `ticklist.py` | `page_bar` for Trips, Map & archive, the sections, the region pages and the tick list; `enterkeyhint="search"` on the Trips and tick-list boxes. |
| `tools/sitegen/pages/about.py` | The units sentence names the language rule. |
| `assets/js/base.js` | The menu closes from 1000 px; the title bar watches the heading `.ab-page` names; a press of the switch stores the choice, the page's start is not stored. |
| `assets/css/base.css` | The nav row from 1000 px; `.ab-page`; the Units row's phone and tablet layout (across both columns from 760 px); the short-phone header (with the menu open, sticky again); the `:where(html:not(.js))` / `:root:not(.js)` twins of the no-script rules. |
| `assets/css/pages/report.css`, `about.css`, `region.css` | The one-row bottom bar on short phones; the 16 px copy field (phones and touch screens); the no-script twins. |
| `assets/css/pages/multiday.css`, `series.css`, `trips.css` | The day and month bars release under 500 px of height; the 16 px selects (phones and touch screens). |
| Docs | DEVELOPING.md: the 1000 px breakpoint, the script-failed header and its twins, the short-phone header, the 500 px bar release in the Sticky parts rule and table, the units rule, the menu's rows, the phone title bar. |
| Tests | New: test_phase13a (the title bar, the menu's rows, the search key, `PREPAINT` run under node against 13 language and storage cases, the stored choice). Changed: test_a11y_static (999/1000 px, every no-script rule's twin, the script-failed header, the short-phone header and bar, the 16 px controls, the 500 px bars; the fixture's pages carry `class="js"` as a browser's do), test_nav and test_ticklist_page (Home, the Units row), test_about_units. |

### Behaviour

- **Which pages changed.** A `--link` build against one of `09e0e97` made before any edit differs in every page (the
  header, the head's script, site.js's `onerror`) and the two bundles; nothing is added or removed.
- **The header from 1000 px (visual-17).** The links, the search box and the switch show from 1000 px instead of
  1140: at 1000 px the row has 40 px to spare on map/ (headless Chrome), and an iPad in landscape gets the desktop
  header with its desktop layouts.
- **The phone menu (phone-12, gap6-02).** It opens with the Units row on top (on a 390 x 844 phone at 73-117 px, in view
  at once; before, about 833 px down a 788 px panel), then Reports, then Site, which starts with Home. From 760 px the
  Units row spans both columns above them.
- **The title bar on index pages (phone-13).** On a phone, once the H1 has scrolled under the header, Trips, Map &
  archive, the five sections, the region pages and the tick list show their title and an up arrow in the header, as a
  report shows its glyph and title; a tap goes back to the H1.
- **Kilometers by language (gap6-03).** A browser set to German or French starts in kilometers (checked with Chrome's
  language override), an English one in miles; a stored choice wins; only a press of the switch stores one.
- **Short and sideways phones (phone-10).** On a 667 x 375 phone the Matterhorn report kept 122 px of fixed chrome
  (header 57, bottom bar 65); now the header scrolls away and the bar is one 49 px row. With the menu open the header
  sticks again with its close button. The day and month bars release under 500 px of height.
- **When site.js does not load (resilience-01).** With site.js blocked in Chrome the home page shows the no-script
  header (the links in rows, no menu button, no switch, a static header on a phone); before, the menu button showed
  and did nothing.
- **iOS zoom (phone-09).** The Trips and tick-list selects and the copy field are 16 px on phones and touch screens;
  the two search boxes say Search on the phone keyboard's return key.
- **validate.py**: 0 errors, 1 warning, 346 notes, as before.

### Where the work departs from the prompt, and documented rules changed

- **Trips' title bar goes to its H1, not `#search`.** trips.js focuses the search box on a `#search` hashchange, so the
  bar's first tap raised a phone's keyboard and its second only scrolled (the review). The box sits right under the
  H1, so the bar's tap brings it into view without taking the focus.
- **The Units row spans both columns from 760 px** rather than sitting under the Site list: the markup has it first,
  and placed last on screen it was the one thing the Tab key reached out of order (the review). On a phone it is
  first in both.
- **The 16 px rule also applies to touch screens at any width** (`(hover: none) and (pointer: coarse)`): an iPhone on
  its side is 812-932 px wide and zoomed into the 15 px selects there. The short-phone header stays limited to under
  760 px wide, as the prompt has it: from 760 px there is no bottom bar, so the chrome is the 56 px header alone.
- **Only a press stores the units.** base.js stored what it showed on every load, so the language rule would have
  decided the first page and nothing after (DEVELOPING.md, Units).
- **site.js's `onerror` removes `km` too**, so a page without its switch says miles, as About does.
- **Documented rules changed:** DEVELOPING.md's breakpoint line (1140 → 1000 px); the Sticky parts rule and table
  (bars release under 500 px, the header static on short phones); the no-script header (the `html:not(.js)` twins);
  the Units rule; the menu and the title bar; the copy control's no-script sentence.
- **The menu's focus** still goes to its first link on opening, as the prompt asks; on a phone the Units row above it
  is reached with Shift+Tab, as the row above any first link is.

### Review

One independent read-only review of the whole change (an agent given the prompt, the rules and the diff, not this
log). It built the site and ran headless Chrome, and confirmed: the twins reproduce the no-script cascade exactly
(every header-related computed style on 5 pages at 10 sizes, scripting off against site.js blocked: identical); the
header row has no overflow at 1000, 1024, 1139 and 1199 px on home, trips/, the PCT page and About with web fonts
loaded; the short phone's header, bar and menu behave; the title bars show only under 760 px and past the H1, with
names that contain their titles; German and French start in km, a stored 'mi' wins, nothing is stored on load; no
privacy problem; no test was loosened. Its findings:

1. Trips' bar to `#search` focused the search box (raising a phone's keyboard). Fixed: the bar goes to the H1.
2. iPhones in landscape (812-932 px) missed the 16 px rule. Fixed for touch screens at any width; the short-phone
   header stays under 760 px (above).
3. The Units row came first in the markup and last on screen from 760 px. Fixed: it spans both columns on top.
4. With site.js failing, a non-English browser kept `km` with the switch hidden. Fixed: `onerror` removes `km` too.
5. A stale sentence in DEVELOPING.md said the copy button shows where `scripting` is unknown. Corrected.
6. The twin test named four stylesheets and checked only that a twin comes later. It now reads every page sheet and
   checks that nothing but no-script rules and twins stand between a rule and its twin.
7. Out of scope and unchanged: with the bundle failing, trips.css's `(scripting: enabled)` rule still hides the
   Trips page's browse links while its form shows and does nothing (the prompt leaves the forms alone; listed below).

### Checks actually run

All on the working tree of 2026-10-25 (the final state, after the review's fixes), Python as named.

| Check | Result |
| --- | --- |
| `/usr/bin/python3 -W error -m unittest discover -s tests` (3.9.6) | 3,076 tests, OK, 104 s (3,062 before the phase) |
| `python3.12 -W error -m unittest discover -s tests` (3.12.11) | 3,076 tests, OK, 130 s |
| `python3 tests/run_orders.py --reverse` | OK; no region page left registered |
| `node tests/*_harness.js` (node 25.8.2) | maplist 45, profile 35, series 58, ticklist 103, trips 167, viewer 50 checks passed |
| `python3 tools/build.py --out <scratch> --link --check` | 365 pages, 168 trips, link check OK |
| `diff -rq` against a `--link` build of `09e0e97` | every page and both bundles differ; no page added or removed |
| `python3 tools/validate.py` | 0 errors, 1 warning, 346 notes |
| `core.PREPAINT` under node (test_phase13a) | 13 cases of stored choice, language and storage that throws |
| Headless Chrome (scratch `p13tools/page.mjs`) | the header row at 1000 px (40 px spare, no overflow); de-DE and fr-FR start in km and store nothing until a press, en-US stays in miles; site.js blocked: the no-script header at 390 px, and `km` removed for de-DE; the menu at 390 (Units at 73-117 px, Home first) and 800 (Units across both columns); the Trips bar back to the H1 without focusing the box; the 667 x 375 report's chrome 122 → 49 px |
| Screenshots | `.cache/plan2/phase13a/`: the open menu at 390 before and after and at 800 after; the header at 1000 and 1024 before and after (trips/); the Matterhorn report at 667 x 375 before and after; the Trips title bar at 390; the home page at 390 with site.js blocked |

Not run: a real phone (the iOS zoom and the landscape header are worth the five minutes); Firefox; `render.py`;
Lighthouse; a phone-load measurement (the header grew by a row of markup and nothing loads before it).

### Remaining issues and author inputs

- **(a) and (b)** were taken as recommended: gap6-02 (the Units row first in the phone menu) and yes to starting in
  kilometers for a browser whose language is not English.
- **Interface copy, new on the site:** "Home" (the menu's first Site row); "Back to top: <page title>" (the title bar,
  read out; its visible text is the page's title); About: "Browsers set to a language other than English start in
  kilometers and meters. The MI | KM switch changes every page, and this browser remembers the choice."
- **The header on a short phone** scrolls away with the page, menu button included; to reach the menu the reader
  scrolls back up (accepted: the menu is rarely needed mid-report, and the bottom bar stays).
- **With site.js failing**, the Trips page's browse links stay hidden by a `(scripting: enabled)` rule while its form
  shows and does nothing; the prompt leaves the search forms alone. A twin like the header's would fix it in a later
  phase.
- **A real phone:** on an iPhone, tap the Trips page's Region menu (the page should not zoom), turn the phone on its
  side on a report (the header should scroll away and the bar be one row), and open the menu (Units first).
- **Carried:** the gap1-01 and qa-04 sheets (Phase 12), the hero frame and the mile table's last row (Phase 10), the
  real-phone look (Phase 11), the checkout and cache moves, `strava_id`, the rehearsal push (Phase 8), the place
  names, retitles and merges (Phase 9).

## Phase 13B - Legibility and the stylesheet (2026-10-25)

The second of Phase 13's three sessions (`docs/personal-website-improvement-plan-2.md`, section 13, and Prompt 13B of
`docs/claude-code-website-prompt-2.md`), built on branch `phase-13b-legibility` from `phase-13a-header-menu` at
`c31ab1f`. No decision from Eric was needed. Nothing under `content/` or `rendered/` changed and `render.py` was not
run. The disk had 16 GB free, under the plan's 30 GB line: builds were linked into the session's scratch folder, and no
worktree or copy of the checkout was made.

### Changed files

| File | Change |
| --- | --- |
| `assets/css/base.css` | 12/16 for `.t-label`, `.keyrow`, `.mv-attrib`, `.trow-dr` and `.rtab-h` at every width (the 760 px step-ups gone), the credit tag on two lines under 360 px; `min-height` on `.chip--title`, `.tag`, `.tcard-act .tag`; every `:hover` rule inside `@media (hover: hover)`; `a:hover` and `.crumbs a:hover` in ink (underlined), the shared `:is(.prose, .hom-also, …) a:hover`, `.alink`, the site's name and the title chip's hover, the viewer's file link kept light; `--route-ink` kept as the maps' token with a comment; the photo-less card tile on `--map-paper`, filling its slot; `.t-lede`; `.t-h4`, `.photos` and `.prow` deleted. |
| `assets/css/pages/*.css` | archive, home, multiday, report, section, series, ticklist, trips, about, region: the hover guard (two mixed lists split: archive's `.is-map-hl` row and section's checked segment stay unconditional); 12 px for `.arc-table .tag`, `.mul-tag`, `.gcard-tags .tag`, the tick list's no-map note and `.eltab th`; the 11 px day-map key under 560 deleted; `min-height` on the tags, `.trx-chip` and `.mul-tag`; the year heads (trips.css, archive.css); the section lists' column header and the filter band's fade (section.css); route-ink hovers in ink (section, trips, home); `.hom-lead` and `.sec-intro` on `.t-lede`; about.css's `.abo-dl` deleted. |
| `assets/css/print.css` | New: the print sheet. |
| `tools/build.py` | `css_bundle` appends `print.css` after the page sheets. |
| `tools/sitegen/core.py` | `stats_items`, `stats_labels`, `group_stat_labels` (`stats_cells` builds on them); `phone_row` deleted. |
| `tools/sitegen/pages/section.py` | `stat_cols`; the column header on each ski season and year, and on a flat list (`.sec-colrow`), not on Other; `.t-lede` on the intro. |
| `tools/sitegen/pages/home.py`, `about.py` | `.t-lede` on the lead; At a glance as `.dl-leader`. |
| `assets/js/pages/section.js` | The band's `.is-scroll` / `.is-end` and the chosen segment brought into the row by `scrollLeft`. |
| Docs | DEVELOPING.md: the hover idiom and the 12 px floor (Datum), the hover and `min-height` rules (Accessibility), the section headers, year heads, tiles, leader list, `.t-lede` and the bands, `print.css` in the file table, the hand checks before a publication, `t-lede` in the type classes. |
| Tests | New: test_section_page (the label rule, the headers on ski, climbing, hiking's planned routes and none on Other, the cascade at seven widths), `Phase13bCssTests` in test_a11y_static (no text under 12 px on a phone but the maps' own and two kept, every hover guarded, no route-ink hover and the one idiom, `min-height`, the year heads and the tick list's labels, the tiles, the dead rules, the print sheet last, the band). Changed: test_a11y_static, test_build_site (the fixture's print sheet, the bundle order), test_region_days, test_report_page. |

### Behaviour

- **Which pages changed.** A `--link` build against one of `c31ab1f` made before any edit differs in the five section
  pages, home, About and the two bundles; every other page differs only through the stylesheet.
- **Phones (phone-15).** Labels, key rows, tags, the map's credit tag, the day ruler and table heads are 12/16 instead
  of 11/14. The review found no key row on a third line at 320 or 360 px across 186 pages, no overflow and no tag
  spilling; at 320 px the credit tag would have reached the scale label by up to 3 px, so under 360 it wraps to two
  lines (54 px clear on the pages checked).
- **Touch (gap1-06).** Tapped in Chrome's touch emulation (hover: none), the Haute Route's second day chip stayed paper
  coloured before and does not now; the same for a PCT month tab.
- **Text zoom (a11y-10).** The title chip, tags and the explorer's chips grow with their words.
- **Year heads (visual-04).** Trips, map/ and the region pages show each year as a 22/28 head (24/30 from 760 px)
  above its count; the tick list's region heads are labels as before.
- **Card tiles (visual-01, step 1).** 61 photo-less cards on trips/ (the review's count) and the home featured
  fallback show their route tile filling the slot on the map's paper instead of a framed 64 % tile.
- **Section lists (visual-11).** Each ski season, each year of Hiking and Mountain biking, Climbing's list and Hiking's
  planned routes name their stat columns once from 760 px; the labels sit exactly over the row cells at every width
  checked (760 to 1600 px, brief and multi-day rows included); each row is 16-20 px shorter. Other keeps its labels.
- **Hovers (visual-09).** Plain text links hover in ink with a thin underline; nothing turns route red but a map's
  cluster ring.
- **Print (visual-13).** Chrome's print of the Matterhorn report is 4 Letter pages (8 before) and the Haute Route 14
  (17 before the sheet's photo cap): no header, footer, bars or buttons, the column map, photos at most a third of a
  page, a day's heading and stats together. Chrome fetched the lazy photos.
- **Filter bands (qa-10).** On a phone the band fades at its right edge while more segments lie beyond; a press, an
  arrow key or a deep link (`ski/#season-2022-23`, `hiking/#year-2021`) brings the chosen segment fully into view,
  and the page itself never moves.
- **validate.py**: 0 errors, 1 warning, 346 notes, as before.

### Where the work departs from the prompt, and documented rules changed

- **The region pages' year heads follow map/'s.** The prompt scopes the heads to `.p-trips` and `.p-archive` and asks to
  say whether the region pages follow; they share map/'s table, so `.p-region` is in the rule. One selector to take
  out if Eric wants the labels back there.
- **The column header is a line under the group's heading**, not on its right: on the Ski list beside its panel the
  heading, the four columns and the count do not fit one line at 1100-1199 px, and a line of its own lines up with
  the cells at every width. Flat lists (Climbing, Hiking's planned routes) get it under their section head.
- **Links already in ink keep a hover** (the review): `.alink` and the site's name underline, a title chip's border
  turns ink; the prompt's plain swap to ink would have left them with none.
- **The print sheet goes past the proposal**: photos capped at 3.4 in, headings kept with what follows, a day's rail
  and stats whole, the day and month bars and the GPX and map buttons hidden, the photo backgrounds off. The proposal's
  `.jrow` rule repeated a phone rule that already holds at a page's 740 px and is left out.
- **The band's reveal** puts a cut segment at the row's start, the snap point, rather than at the nearest edge: with
  `scroll-snap-type: x proximity` an in-between position was moved back under the fade (the review's finding 5).
- **Kept at 11 px:** the day bar's photo count (`.mul-dn-c`), which its chip already cuts off at 11 px, and SVG text on
  maps (the full-screen scale, hut numbers, mapkit's).
- **Documented rules changed:** DEVELOPING.md's Datum section (route red, the 12 px floor), Accessibility (hover under
  `(hover: hover)`, `min-height`), the type classes (`t-h4` out, `t-lede` in), the file table (`print.css`), the
  section, year, tile and band notes, and the hand checks before a publication.

### Review

One independent read-only review of the whole change (an agent given the prompt, the rules and the diff, not this
log). It rebuilt the site (byte for byte the same), compared the bundles rule by rule, measured 186 pages at 320 and
360 px and printed pages in Chrome. It confirmed: no declaration lost by the hover wrapping, every `:hover` guarded,
the split lists cascading as before, the one nested `@media (hover: hover)` valid; the column headers pixel-aligned at
ten widths with every group's header matching its rows; no third key-row line, no overflow; tiles, About's list and
the print sheet's chrome hiding; no privacy problem; no test weakened. Its findings, all fixed:

1. `.alink`, the title chip and the site's name had no hover left (their text is already ink). They underline or
   take an ink border now.
2. The viewer's 'Open the file' turned ink on its dark backdrop under the pointer. It stays light.
3. At 320 px the 12 px credit tag covered the end of the scale label on 9 pages. It wraps to two lines under 360 px.
4. Print: photos one per row with rows taller than a page left blank pages (9 pages for one report), day headings
   split from their stats, the day bar and GPX buttons printed. The sheet caps photos, keeps headings and a day's rail
   together and hides the controls (above).
5. The band could leave the chosen segment under its fade. It goes to the row's start now (above).
6. The region pages' year heads go past the prompt's scope: kept and listed for Eric (above).
7. DEVELOPING.md overstated three things (no route red at all, no text under 12 px, no `height` on chips). Corrected,
   with the exceptions named; `.mul-tag` takes `min-height` too.
8. Clean-ups: a comment the hover script had moved onto the wrong rule, an orphan comment, a redundant `.eltab th`
   step-up, blank lines left by `phone_row`.
9. Test gaps: the hover colour's rule, a list keeping its header at 960-1099 px, the band's fade clearance. Added;
   the band's scrolling itself is checked in a browser only.

### Checks actually run

All on the working tree of 2026-10-25 (the final state, after the review's fixes), Python as named.

| Check | Result |
| --- | --- |
| `/usr/bin/python3 -W error -m unittest discover -s tests` (3.9.6) | 3,092 tests, OK, 104 s (3,076 before the phase) |
| `python3.12 -W error -m unittest discover -s tests` (3.12.11) | 3,092 tests, OK, 95 s |
| `python3 tests/run_orders.py --reverse` | OK; no region page left registered |
| `node tests/*_harness.js` (node 25.8.2) | maplist 45, profile 35, series 58, ticklist 103, trips 167, viewer 50 checks passed |
| `python3 tools/build.py --out <scratch> --link --check` | 365 pages, 168 trips, link check OK |
| `diff -rq` against a `--link` build of `c31ab1f` | the section pages, home, About and the two bundles |
| `python3 tools/validate.py` | 0 errors, 1 warning, 346 notes |
| Headless Chrome (scratch `p13tools/`) | column labels against row cells on ski and climbing at 800, 1100, 1280, 1440 px (equal x); a tapped day chip and month tab under touch emulation, before and after; the credit tag against the scale label at 360 and 320 px; the band's reveal after presses and deep links on hiking/ and ski/ at 390 px |
| Chrome's print to PDF (`--print-to-pdf`, Letter) | the Matterhorn report (4 pages), the Haute Route (14), another report (6); a contact sheet of the pages |
| Screenshots | `.cache/plan2/phase13b/`: trips/ and ski/ at 1280 before and after, the ski band, the ski list and a report's key row at 390 before and after, the printed pages (`print-sheet.png`, the PDFs) |

Not run: Safari's print preview (whether it fetches the lazy photos before printing is unknown); Firefox at 200 %
text-only zoom (no Firefox here; the hand check is in DEVELOPING.md now); a real phone; `render.py`; Lighthouse.

### Remaining issues and author inputs

- **The region pages' year heads** follow map/'s (above); say if they should stay labels.
- **Interface copy, new on the site:** the column labels ("DIST", "GAIN", "GPS MAX", "MOVING", the row cells' own
  words, shown once per group). Nothing else is new text.
- **Safari's print preview and Firefox's text zoom** are listed in DEVELOPING.md's hand checks; neither could run here.
- **The day bar's photo count** stays at 11 px (its chip cuts it off already); a wider chip or a shorter text is a
  later layout change.
- **Carried:** the gap1-01 and qa-04 sheets (Phase 12), the hero frame and the mile table's last row (Phase 10), the
  real-phone look (Phases 11 to 13A), the checkout and cache moves, `strava_id`, the rehearsal push (Phase 8), the
  place names, retitles and merges (Phase 9).

## Phase 13C - Accessibility, copy and the VoiceOver pass (2026-10-25)

The last of Phase 13's three sessions (`docs/personal-website-improvement-plan-2.md`, section 13, and Prompt 13C of
`docs/claude-code-website-prompt-2.md`), built on branch `phase-13c-a11y-copy` from `phase-13b-legibility` at
`7f2b52b`. Eric's standing instruction for this run is to go on with the plan's recommended answers, so decisions (c)
and (d) took them (below). Nothing under `content/` or `rendered/` changed and `render.py` was not run. The disk had
about 14 GB free, under the plan's 30 GB line: builds were linked into the session's scratch folder, and no worktree or
copy of the checkout was made.

### Author inputs

- **(c) copy-11:** 'Backcountry Skiing' (the recommended answer). The URL and the `ski` folder are unchanged;
  `tools/lib/strava.py` is untouched.
- **(d) copy-14, ia-13:** the header keeps 'PCT', named 'PCT journal' for screen readers; the menu button stays 'Menu'
  (aria-expanded says whether it is open); the crumb root stays 'Reports' to home.
- **The VoiceOver pass (a11y-12): pending.** The script is ready in `docs/CHECKING_WITH_A_SCREEN_READER.md` (about 12
  minutes on the Mac in Safari, 8 on an iPhone); its table goes into this entry when Eric has run it.
- **Interface copy to read** (every new label and sentence on the site):
  - 'Backcountry Skiing' (header, menu, footer, home tiles and legends, section page, search keywords).
  - 'Map' for map/ everywhere: the header, menu and footer link, the page's H1 and `<title>` ('Map · Eric Sichak'),
    the region pages' link back to it.
  - 'By activity' for the menu's and footer's column of the five activities (and the 404's heading over them).
  - The 404's map row: 'Map', '167 REPORTS BY REGION AND YEAR' (the number is the site's count).
  - Destination links, one verb per kind: 'Read the report' (a written report), 'View the trip' (a track-only trip),
    'Open the journal' (the PCT), 'Open the goal' (a tick-list goal). 'Open the map' and 'All <region> reports' stay.
  - Map captions: 'Full track, not trimmed' / 'Full tracks, not trimmed', capitalised everywhere.
  - The tick list's empty state: 'Nothing on the list yet.'
  - The footer's training item: 'AVALANCHE TRAINING: AIARE 2' (About's own label), now on a line of its own.
  - Read by screen readers only: 'PCT journal'; the units switch's 'MI: miles and feet' and 'KM: kilometers and
    meters'; every abbreviated unit read as its word ('12.8 miles, 5,302 feet gain').

### Changed files

| File | Change |
| --- | --- |
| `tools/sitegen/core.py` | `UNIT_WORDS`, `unit_word`, `caps_unit`: a unit shown abbreviated and read as its word, inside `U`'s unit span and `U_sub`, in `plain_stats`, `row_stats_line`, the goal stats, the Moving time's 'h:mm' and the mile key's '(1.6 km)'; `UNITS_LABELS` on the units switch; `PCT_NAME` as the aria-label of the header's and the menu's PCT link; 'Map', 'By activity', the footer's training label; `FULL_TRACK` / `FULL_TRACKS`; 'Open the goal'; `trip_row(level=3)`; NAV 'Backcountry Skiing'; the contours caption's unit word. |
| `tools/lib/content.py` | ACTIVITIES: 'Backcountry Skiing'. |
| `tools/sitegen/pages/section.py` | `row(level=)`, rows under a year at H4; 'Read the report' / 'View the trip'; 'Open the journal'; `core.FULL_TRACK`; GPS max/min through `caps_unit`. |
| `tools/sitegen/pages/archive.py`, `region.py` | 'Map' (H1, title, page bar, the link back); 'Open the journal'; `core.FULL_TRACKS`; `caps_unit`. |
| `tools/sitegen/pages/home.py`, `notfound.py`, `ticklist.py`, `about.py`, `multiday.py`, `series.py`, `report.py` | The verbs; the 404's 'By activity' and map row; `ticklist.EMPTY`; About's switch labels from `core.UNITS_LABELS`; `caps_unit` (the multi-day heights, gains and losses too) and `FULL_TRACK(S)`; the journal day label's hidden comma. |
| `assets/css/base.css` | Forced colours keep `.keyrow--compact .disc` and `.fchip .chip-sw`; `@media (prefers-contrast: more)` (`--ink-3` to `--ink-2`, `--rule-strong` #5F5D57, `.pf-ax` and `.mk-lbl` in ink-2); `.ml > .mi::before { content: "·"; content: "·" / ""; }`. |
| `assets/css/pages/home.css` | `.hom-reg-n a`: a 44 px box of its own (padding cancelled by negative margins) instead of a `::before`. |
| `assets/css/pages/series.css` | Forced colours: the month bars (`.ser-rl i`) keep their colour with a CanvasText outline; an empty month link in GrayText; the day label's and stats line's dots drawn, not read. |
| `assets/css/pages/archive.css`, `section.css`, `ticklist.css` | Comments only (the new words). |
| `assets/js/base.js` | The touch pick survives the list's own press of 'Show all' (the walk's finding, below). |
| `assets/js/pages/ticklist.js`, `archive.js` | 'Nothing on the list yet.'; a comment. |
| Docs | DEVELOPING.md: the Copy bullets (FULL_TRACK, one word per destination), the destination verb table, the 13C accessibility notes (forced colours, more contrast and its two limits, unit words, the dot), the tablet profile and the coarse-pointer walk in "Measuring page loads"; CONTENT_GUIDE.md: the verbs, 'Map', 'backcountry skiing'; TICK_LIST_GUIDE.md: the empty state and where the command lives; new `docs/CHECKING_WITH_A_SCREEN_READER.md`. |
| Tests | New `tests/test_phase13c.py` (unit words, the switch's names, forced colours, more contrast, the dot, one word per destination, the PCT name, Backcountry Skiing, the verbs, caption capitals, the empty list and footer line); `test_a11y_static` (the region link's own 44 px box, `test_headings_nest_without_skipping_a_level`); `test_section_page` (rows under a year are H4); `maplist_js_harness.js` (a pin whose row is folded); `helpers.seen_text`; the renames across 25 modules and two harnesses. |

### Behaviour

- **Which pages changed.** A `--link` build against one made from `7f2b52b` before any edit differs in every page (the
  header, menu and footer words) and in the two bundles and `trips/search.json` (the ski label in the keywords);
  nothing else.
- **Home's region links (a11y-03).** 'Lake Tahoe' and 'Eastern Sierra' measure 44 px tall in Chrome at 390, 1280 and
  1440 px (16 px before); the captures before and after at 390 and 1280 show the same layout, the copy aside.
- **Headings (a11y-08).** On Hiking and Mountain biking the rows under a year are H4 under the year's H3; the Ski page
  is as it was. A walk of every built page finds no skipped level.
- **Units (a11y-05).** Chrome's accessibility tree of home reads '12.8 miles, 5,302 feet gain' and '3,167 miles
  recorded' where it read '12.8 MI' and '3,167 MI RECORDED'; the switch reads 'MI: miles and feet'. Read the way a
  screen reader reads them (hidden text and drawings left out, write-ups and titles too), the 363 built pages held
  3,407 numbers followed by a bare abbreviation on 341 pages before this phase and hold none now; the Haute Route's
  tree in Chrome has none of the 49 the review found.
- **The dot (qa-01).** Home's tree held 64 '·' texts, now 4, all real text (the page title, the line under the site's
  name, a label and the map credit); none in the cards. The PCT page's day labels and stats lines draw their dots the
  same way, and a day's label is read 'Day 2, <date>'.
- **Forced colours and more contrast (a11y-04, a11y-15).** As listed above. No ink-3 text sits on the sunk
  background (the transfer note and tags are ink-2), so `multiday.css` needed nothing.
- **Lighthouse** (13.5.0, mobile, the local build): home 100 / 100 / 100 (accessibility, best practices, SEO), as the
  build before this phase also scored; the one zero-weight audit still failing is `label-content-name-mismatch` on the
  five activity tiles, which is a11y-01, not planned. The Matterhorn report 100 / 100 / 100 with no failed audit.
- **The tablet profile (gap1-08).** The six pages at 768 x 1024, 1024 x 768 and 1180 x 820 with touch emulation
  (`.cache/plan2/phase13/tablet-*.jpeg`, `tablet-sheet.png`): no overflow or overlap; the Haute Route's title takes
  three lines beside its actions at 1024 x 768.
- **The coarse-pointer walk** (1024 x 768, touch, hover: none, pointer: coarse, Lake Tahoe and the Matterhorn report):
  a numbered circle narrows the list ('22 REPORTS START HERE, Show all'); a list row opens its report; a photo opens
  the viewer ('Photo 1 of 7' and its description) and a swipe goes to photo 2; a pin and a journal line are picked by
  a first tap, their row opened, and followed by a second (the line to its day of the journal). The walk found one
  bug, fixed here: a pin whose row sat behind 'Show all' lost its pick at once (the list's own scripted press of
  'Show all' counted as a tap outside the map), so a second tap was another first tap and never followed the link.
  Opening a row centres it, so the map can move under the finger between the two taps (72 px on the walk).
- **validate.py**: 0 errors, 1 warning, 346 notes, as before.

### Where the work departs from the prompt, and documented rules changed

- **'Map', not 'Map & archive'.** The prompt allows either; the header row at 1000 px has no room for the longer
  name, so the page, its H1 and every link say 'Map'.
- **`core.table_row` keeps its own sr unit words.** Its cells show a bare number (the unit is in the column head), so
  `unit_word` would put nothing on screen; nothing is read twice there.
- **The region crumb and 'Open the map'** got no box of their own: Lighthouse does not flag them.
- **Three destination verbs set on purpose by the 2026-10-08 plan are reversed:** 'Explore the journal', 'View trip'
  and 'View goal' (CONTENT_GUIDE.md updated).
- **Documented rules changed:** DEVELOPING.md's Copy section (one word per destination, the verb table,
  FULL_TRACK), Accessibility (forced colours, more contrast and its limits, unit words, the dot), "Measuring page
  loads" (the tablet profile and the walk, the review gate's capture sizes); CONTENT_GUIDE.md and TICK_LIST_GUIDE.md.

### Review

One independent read-only review of the whole change (an agent given the prompt, the rules and the diff, not this
log). It read Chrome's accessibility tree and the built pages, measured the home links, emulated forced colours and
more contrast, and scanned the aria-labels of all 365 pages. It confirmed: no unit spoken twice, the hidden system's
word hidden with it, `table_row`'s own words right to keep; no aria-label missing its visible text; no skipped
heading; forced colours, more contrast and the dot as intended; the home link 44 px with its surroundings in the same
places; none of the old words in the built pages; the touch fix right and complete (the other scripted clicks are key
presses or run at load); no privacy problem. Its findings, all fixed:

1. Units were still read as letters in places item 22 did not list: the multi-day heights, gains and losses
   (`multiday.caps_elev`, the day profile's head) and the strip's second line in the other system (`core.U_sub`) on
   reports, multi-day pages, the PCT, the section strips and About. They read their words now, and a test reads every
   fixture page and finds no number before a bare abbreviation (it caught the mile key's '(1.6 km)' too).
2. The H4 check in `test_a11y_static` could not fail (the fixture's lists are too short to be grouped by year). The
   check is now in `test_section_page` on `section.year_groups`, and fails with `level=4` taken out.
3. Old words in DEVELOPING.md (the menu's column, the footer's Site list, a related-reports example), CONTENT_GUIDE.md
   (the captions' examples, the same example), a docstring and four CSS comments.
4. The screen-reader script named a heading the report does not have, said one swipe reached the Units row, and
   described a day's heading as two. Corrected against the built pages.
5. A comment on the wrong constant; blank lines around `ticklist.EMPTY`.
6. The log entry was not yet written (this entry).
7. Older, not from this phase: the PCT page's day dots were read out (fixed, above); the Moving time's 'h:mm' was read
   as letters (now 'hours and minutes'); the home tiles' names (a11y-01, not planned, left).

### Checks actually run

All on the working tree of 2026-10-25 (the final state, after the review's fixes), Python as named.

| Check | Result |
| --- | --- |
| `/usr/bin/python3 -W error -m unittest discover -s tests` (3.9.6) | 3,109 tests, OK, 107 s (3,092 before the phase) |
| `python3.12 -W error -m unittest discover -s tests` (3.12.11) | 3,109 tests, OK, 97 s |
| `python3 tests/run_orders.py --reverse` | 3,109 tests, OK; no region page left registered |
| `node tests/*_harness.js` (node 25.8.2) | maplist 46, profile 35, series 58, ticklist 103, trips 167, viewer 50 checks passed |
| `python3 tools/build.py --out <scratch> --link --check` | 365 pages, 168 trips, link check OK |
| `diff -rq` against a `--link` build of `7f2b52b` | every page, the two bundles, `trips/search.json` |
| `python3 tools/validate.py` | 0 errors, 1 warning, 346 notes |
| Lighthouse 13.5.0 (Chrome DevTools, mobile) | home 100/100/100 (before this phase also 100), the Matterhorn report 100/100/100; reports in `.cache/plan2/phase13/lighthouse*/` |
| Chrome accessibility snapshots | home before and after, the Haute Route after (`.cache/plan2/phase13/*-a11y-*.txt`) |
| A scratch scan of the built pages as a screen reader reads them | 3,407 numbers before a bare unit abbreviation on 341 of 363 pages before the phase, 0 after |
| Headless Chrome (scratch `p12tools/`, `p13tools/`) | the region link's box at 390, 1280, 1440 px; the tablet captures; the coarse-pointer walk, before and after the fix |
| Screenshots | `.cache/plan2/phase13/`: home at 390 and 1280 before and after, the 18 tablet captures and their sheet |

Not run: VoiceOver (Eric's, pending with the script ready); a real iPad or phone; Lighthouse on the live site (after
the next deploy); Windows High Contrast itself (the forced-colours rules are checked in the stylesheet tests only);
`render.py`.

### Remaining issues and author inputs

- **The VoiceOver pass** (`docs/CHECKING_WITH_A_SCREEN_READER.md`): about 20 minutes on the Mac and an iPhone.
- **The interface copy** above: say if any word should change.
- **a11y-01** (the activity tiles' names) stays as planned: not planned, revisit after the VoiceOver pass.
- **The maps' own aria-labels** still give miles only; they are in the committed fragments and wait for Phase 15's
  render.
- **Carried:** the region pages' year heads (13B), the day bar's 11 px photo count (13B), the gap1-01 and qa-04
  sheets (Phase 12), the hero frame and the mile table's last row (Phase 10), the real-phone look (Phases 11 to 13),
  the checkout and cache moves, `strava_id`, the rehearsal push (Phase 8), the place names, retitles and merges
  (Phase 9).

## Phase 14 - Loading, metadata, sharing, follow and contact (2026-10-25)

Phase 14 of `docs/personal-website-improvement-plan-2.md` (section 14) and its prompt in
`docs/claude-code-website-prompt-2.md`, built on branch `phase-14-metadata-sharing` from `phase-13c-a11y-copy` at
`1d593b4`. Eric's standing instruction for this run is to go on with the plan's recommended answers; where an answer
needs something only he can give (a download, an address, his accounts), the work stops short of it and says so below.
Nothing under `content/` or `rendered/` changed and `render.py` was not run. The disk had 13 GB free, under the plan's
30 GB line: builds were linked into the session's scratch folder, and no worktree or copy of the checkout was made.

### Author inputs

- **(a) perf-02, the fonts: yes** (Eric, later the same day). `tools/fonts.py` downloaded seven files into
  `assets/fonts/`: the Latin woff2 files of Archivo (90,096 B), Source Serif 4 roman (48,704 B) and italic (50,560 B)
  and Geist Mono (23,108 B) from Google Fonts, and the three SIL Open Font License texts from the google/fonts
  repository; it wrote `assets/css/fonts.css`. No font is preloaded (below).
- **(b) gap5-01, the contact path: the address Eric gave** is in `content/author.json`; it shows on About ('Follow &
  contact'), in the footer and as 'Ask about this trip' on every report, and becomes public with the next push.
- **(c) gap5-03, profile links: none named.** The `links` list of the same file, empty until you name a service and
  a handle.
- **(d) seo-12, Search Console: yours to do.** README.md has the steps; `core.VERIFY_TAGS` takes the token. The
  `esichak.github.io` repository for a root robots.txt is skipped, as recommended.
- **(e) seo-04, share images: the text card and the WebP stay** until the real preview check (item 10, after the next
  deploy) shows a previewer that fails; no 1200 x 630 crops were made.
- **After the next deploy:** the `curl -I` check of a versioned bundle, Google's Rich Results Test on a report and the
  home page, the W3C feed validator, and the real share preview (the Matterhorn report, a report with a portrait cover,
  the home page; README.md lists them). All pending.
- **The feed readers named on About** (NetNewsWire, Feedly) were not checked online in this session; no RSS-to-email
  service is named until you approve one.
- **Interface copy to read** (every new label and sentence):
  - Trip page titles: '<title> · <activity>, <place or region> · Eric Sichak' (the date after the place when a title
    repeats).
  - The footer's Site list ends 'Follow' (with the RSS icon, to About's #follow) and 'Source on GitHub'.
  - About: the section heading 'Follow' ('Follow & contact' once there is an address or a link); 'New reports go out
    on the RSS feed. Paste this address into a feed reader, such as NetNewsWire or Feedly, to see each one as it is
    published.'; 'Prefer email? An RSS-to-email service can turn this feed into messages.'; buttons 'Copy feed
    address', 'Open feed.xml', and with an address 'Email'.
  - About's method list, last item: 'The site is built from a public repository on GitHub. To report a broken link or
    a wrong name, open an issue there. It needs a GitHub account, and it is for problems with the site, not for
    private questions.'
  - With an address only: 'Ask about this trip' on every report.
  - The feed's full items end 'Open the report · Download GPX'; a multi-day trip's days are headed 'Day N: <title>'.

### Changed files

| File | Change |
| --- | --- |
| `tools/sitegen/core.py` | `page_title`, `describe` (`DESC_LIMIT`, `DESC_FLOOR`), `crumbs`, `ld_script`; `document(ld=...)` writes og:site_name, og:locale, the verification tags, the home-screen icon (`touch_icon`), the bundles' `?v=` (`_ASSET_VERSION`) and, with `_SELF_FONTS`, two font preloads in place of Google's stylesheet (`FONT_PRELOADS`); `_report_head` adds article:author, article:section, article:tag; `photo(thumb=)`; `REPO_URL`, `VERIFY_TAGS`, `_AUTHOR`, `author_email`; the footer's Follow, Source on GitHub and address row. |
| `tools/build.py` | Bundles before pages and `asset_hash`; fonts.css first in the bundle and `assets/fonts/` copied when present; `site['author']`; `feed_content` and `xmlns:content`. |
| `tools/sitegen/author.py` | New: the strict loader of `content/author.json`. |
| `tools/sitegen/sitecheck.py` | `LD_TYPES`: BlogPosting and BreadcrumbList, at most one of each. |
| `tools/lib/checks.py` | `AUTHOR_KEYS`, `_author_findings`. |
| `tools/sitegen/pages/report.py` | `crumb_items`, `crumbs_ld`, `dup_title`, `ask_link`, `share_row(ask=)`; titles and descriptions through core; the BreadcrumbList on report and goal pages. |
| `tools/sitegen/pages/multiday.py`, `series.py` | The same titles, the BreadcrumbList and 'Ask about this trip'; `multiday.description` gone (core.describe). |
| `tools/sitegen/pages/section.py`, `region.py` | `crumb_items` and the BreadcrumbList; the Ski page's map preloads under `SKI_MEDIA`; the Hiking journal squares' `.th` first. |
| `tools/sitegen/pages/about.py` | The #follow section (copy, raw feed, RSS-to-email, contact and profiles); the issue path. |
| `tools/share_preview.py`, `tools/fonts.py` | New tools. |
| `assets/apple-touch-icon.png` | New: 180 px, from favicon.svg (`sips`). |
| `assets/fonts/`, `assets/css/fonts.css` | New: the four Latin woff2 files, the three OFL texts and their @font-face rules (tools/fonts.py). |
| `content/author.json` | New: the contact address Eric gave. |
| `assets/css/base.css`, `pages/about.css`, `pages/report.css` | `.f-mail`; the follow rows; `.rep-share--ask` shown on phones without scripting. |
| Docs | DEVELOPING.md (file table, Rules: structured data, indexing, titles and descriptions; sitecheck's META; the report head; a new section 'Metadata, loading, following and contact'; the measuring method's cache header), CONTENT_GUIDE.md section 9 (titles, descriptions, share_preview.py in place of the og:image grep, crumbs, author.json) and its table of messages (author.json), README.md ('Let readers reach you', the share and font tools, the after-deploy checks, 'Search Console'), PRIVACY_NOTES.md (the feed's full items, a published address). |
| Tests | New: `test_phase14.py`, `test_about_follow.py`, `test_share_preview.py`. Changed: `test_metadata`, `test_build_site`, `test_report_page`, `test_region_page`, `test_sitecheck`, `test_nav`. |

### Behaviour

- **Which files changed.** A `--link` build against one made from `1d593b4` before any edit differs in every page
  (the head and the footer), `assets/site.css`, `feed.xml` and the new `assets/apple-touch-icon.png`; `site.js` is
  unchanged.
- **Titles (seo-01).** Every trip page's `<title>` and og:title name the activity and the place, e.g. the Matterhorn
  report's 'Matterhorn Peak – West Couloir · Backcountry Skiing, Sawtooth Ridge · Eric Sichak'. No two indexable pages
  share a title. Ten pages whose title names both its place and its region keep the old form, as the prompt says. Titles over 60 characters go from 8 to 123 (share_preview.py); search results and cards cut the end, which is
  the site's name.
- **Descriptions (seo-02).** Of the 168 trip pages, 89 descriptions ended in '…' before and none does now: a
  description that leads with the facts writes them whole, and one that leads with the write-up ends at its last
  sentence end within 160 characters (the shortest, 56 characters, is a whole first sentence).
- **Head metadata (seo-03, seo-06).** og:site_name and og:locale on every page; article:author, article:section and
  one article:tag per region and summit on report pages; a BreadcrumbList on every page with crumbs (report,
  multi-day, journal, goal, section and region pages), its names and addresses those of the visible crumbs.
- **Bundles (perf-01).** Every page names `assets/site.css?v=<hash>` and `assets/site.js?v=<hash>` (the first 8 hex
  digits of each file's SHA-1). The live `curl -I` check waits for the deploy.
- **Fonts (perf-02).** Every page serves the site's own fonts and makes no request to fonts.googleapis.com or
  fonts.gstatic.com. Desktop first paint (medians of 25 cold runs, 1440 x 900): home 316 ms before (232-480; it waited
  for Google's stylesheet at 284 ms), 56 ms after (48-68); the Matterhorn report 312 ms before, 48 ms after. The phone
  profile's largest paint is unchanged (1,740 ms on home, 1,744 and 1,736 ms on the report). The only characters on
  the site outside the Latin files are → and ≈ (and emoji), which none of Google's 21 subsets covered either.
- **Ski page (perf-07).** Four preloads now: the first panel map's hillshade and base layer, each pair under the media
  where the panel shows that render (section.SKI_MEDIA). In Chrome a window fetches only the render it shows (390 x 844,
  1000 x 800 and 1280 x 720: the phone render; 1440 x 900: the desktop one). Phone profile, median of 3: LCP 2,368 ms
  before, 1,640 ms after.
- **Hiking page (perf-14).** The journal block's three squares take the .th copies: 229,912 bytes before (the .sm
  copies), 73,260 after, measured on the phone profile with the block scrolled into view.
- **Feed (seo-09).** feed.xml has 30 items as before; the 14 whose trip has a write-up carry it whole in
  `<content:encoded>` with its photos and links (16 KB to 33 KB). The W3C validator check waits for the deploy.
- **Home-screen icon (phone-16).** Linked from every head: the favicon's mark on an opaque square (iOS rounds it).
- **Follow and contact (gap5-01 to gap5-08).** About's Follow section (at #follow) explains the feed, copies its
  address, opens the raw feed and mentions RSS-to-email; the footer's RSS link is now 'Follow' and lands there, and
  'Source on GitHub' follows it. With no content/author.json nothing else appears; a scratch build with a synthetic
  example.test address showed About's 'Follow & contact', the footer's address and 'Ask about this trip' under the
  title's place line and in the phone share row (screenshots below).
- **validate.py**: 0 errors, 1 warning, 346 notes, as before.

### Where the work departs from the prompt, and documented rules changed

- **No font is preloaded** (the prompt preloads Archivo and Source Serif 4). With the two preloads, desktop first
  paint was the same (60 ms on home) and the phone profile's largest paint rose from 1,740 to 2,524 ms (2,496 on the
  report): 138 KB of fonts took the slow line from the lead image. Without them both profiles are as measured above
  (`core.FONT_PRELOADS = ()`, with the figures beside it).
- **The fonts and the contact waited for Eric's answers**, built and inert, until he gave them later the same day;
  the entry was amended then (one Phase 14 commit).
- **`core._ASSET_VERSION` is private and lives only for a build** (the prompt names `core.ASSET_VERSION`, default
  `{}`): build.build() sets it and clears it in a `finally`, so a page built in a test, or a second build in the same
  process, never carries a stale hash, and the test helpers' state snapshots cover it.
- **Descriptions end at a sentence from 40 characters, not 80.** The prompt's span of 80 to 160 left eight pages cut
  mid-sentence (their first sentences run 56 to 75 characters), against the gate's 'description ending in … 0'. A
  write-up that leads now ends at its last sentence end within 160 characters from 40 on, and one with no sentence end
  in that span leads with the facts instead (core.DESC_FLOOR, the review's finding 2).
- **'Ask about this trip' sits under the title's place line, not among the buttons.** In the button row (as the prompt
  says) it narrowed a long title from three lines to five at 1000 px (the review's finding 4); on phones the share row
  carries it, as the prompt says, and the journal, which has no share row, keeps it under its title.
- **The icon is linked only when the file exists**, as print.css is bundled only when present: the tests' temporary
  site trees have no icon, and a link to a missing file would be a broken link in the site check.
- **'Copy feed address' only copies** (`copy_link(share=False)`): on a touch screen base.js turns copy controls into
  the share sheet labelled 'Share this page', which would have offered the feed as a page; found on the 390 px
  capture.
- **The feed's multi-day sections carry that day's photos**, after each written day, besides the trip's own photos;
  unwritten days get no section.
- **Feed readers named without an online check** (NetNewsWire, Feedly), and no RSS-to-email service named (item 19
  names only services Eric approves).
- **Not done (optional in the prompt):** the web manifest and 512 px icon, the robots `max-image-preview` meta.
- **Documented rules changed:** DEVELOPING.md's Rules (structured data now BlogPosting and BreadcrumbList; indexing of
  track-only reports; titles and descriptions), sitecheck's META line, the report head's tags, the file table and a new
  section 'Metadata, loading, following and contact (Phase 14)'; CONTENT_GUIDE.md section 9; README.md; PRIVACY_NOTES.md
  section 1.

### Review

One independent read-only review of the whole change (an agent given the prompt, the rules and the diff, not this
log). It built the site, ran the share listing, checked every built page's bundle hashes against the bytes written,
every BreadcrumbList against the visible crumbs (181 pages), the feed's 65 absolute addresses, the fonts' paths as a
real fonts.css would give them, and measured the Ski page at four sizes in Chrome. It found nothing serious; its
findings, all fixed:

1. The Ski preload took the base `(min-width: 560px)` for the desktop render, but the panel shows the phone render at
   760-1199 px and in short desktop windows, so a 1000 x 800 window downloaded about 72 KB it never showed. The pairs
   now follow the panel's own rules (SKI_MEDIA), and a test holds them against section.css at 40 sizes.
2. Eight descriptions still ended in '…' (above): fixed.
3. A write-up's relative link would have resolved against feed.xml in a reader: every href and src in the feed's
   content is made absolute. (No write-up has one today.)
4. 'Ask about this trip' narrowed long titles at desktop widths: moved (above).
5. The address check let through `? # & %`, which a mailto reads as its own: now letters, digits, `. _ + -`, an `@`
   and a host.
6. tools/fonts.py would have fetched any address Google's stylesheet named, of any size: now fonts.gstatic.com only,
   2 MB at most per file.
7. Tests: nothing checked that the Hiking page passes the thumbnail option (added on the journal block; it fails
   without it); two tests re-derive core.describe's rule (left, with exact strings beside them).
8. CONTENT_GUIDE's table of messages had no content/author.json rows: added.
9. Nits: a multi-day day's own headings came out at the level of its 'Day N' heading (now one under); the icon's
   transparent corners (now opaque); the icon must be committed for the test that reads it (it is).

The review's measurement also showed each preloaded map fetched twice; that came from the scratch server's
`Cache-Control: no-store`. Served with GitHub Pages' `max-age=600`, the Ski and Climbing pages request each map once
(DEVELOPING.md's measuring method now says so).

### Checks actually run

All on the working tree of 2026-10-25 (the final state, after the review's fixes), Python as named.

| Check | Result |
| --- | --- |
| `/usr/bin/python3 -W error -m unittest discover -s tests` (3.9.6) | 3,158 tests, OK, 107 s (3,109 before the phase); the check of the checkout's own fonts.css runs once it exists |
| `python3.12 -W error -m unittest discover -s tests` (3.12.11) | 3,158 tests, OK, 98 s |
| `python3 tests/run_orders.py --reverse` | 3,158 tests, OK; no region page left registered |
| `node tests/*_harness.js` (node 25.8.2) | maplist 46, profile 35, series 58, ticklist 103, trips 167, viewer 50 checks passed |
| `python3 tools/build.py --out <scratch> --link --check` | 365 pages, 168 trips, link check OK |
| `diff -rq` against a `--link` build of `1d593b4` | every page, `assets/site.css`, `feed.xml`, the new icon |
| `python3 tools/validate.py` | 0 errors, 1 warning, 346 notes |
| `python3 tools/share_preview.py` on both builds | before: 62 no image, 89 descriptions ending in '…', 8 titles over 60, 124 WebP, 30 portrait; after: 62, 0, 123, 124, 30 (`.cache/plan2/phase14/share-preview-*.txt`) |
| Phone profile (scratch `measure14.mjs`, the DEVELOPING.md method, median of 3) | Ski LCP 2,368 ms before, 1,640 ms after; Hiking's three journal squares 229,912 bytes before, 73,260 after (scrolled into view) |
| Headless Chrome (scratch `p12tools/`, `p13tools/netcount.mjs`) | the Ski map each of four window sizes fetches; one request per preloaded map under `max-age=600` |
| A scratch build with a synthetic example.test contact (author.load patched in memory) | About's 'Follow & contact', the footer row, 'Ask about this trip' in the title and the phone share row |
| Screenshots | `.cache/plan2/phase14/`: About's section at 1280 and 390 px (synthetic address) and at 1280 without one; the Matterhorn report's title at 1280 and 1000 px and its share row at 390 px (synthetic address); `heads-before-after.txt` (four reports' heads as text) |

Fonts (after Eric's yes): `python3 tools/fonts.py` (the download, then `--check`: OK); the desktop profile 25 times
per build and page (scratch `p12tools/desktop.mjs`: Google Fonts, the site's own fonts with and without the two
preloads), and the phone profile (median of 3) for each; served with `max-age=600`. A first 'before' set was thrown
away: an old scratch server held its port and the runs measured its error page.

Not run: the checks after the deploy (curl, Rich Results Test, W3C feed validator, the real share preview); the feed
readers' names online; Lighthouse; `render.py`.

### Remaining issues and author inputs

- **Profile links**, if you want any, in `content/author.json` (README.md, 'Let readers reach you').
- **After the next deploy:** the curl check, the Rich Results Test, the W3C feed validator and the real share preview
  (README.md lists the pages); Search Console when you have time (README.md, 'Search Console').
- **The interface copy** above, and the two feed readers named on About.
- **Ten titles keep the old form** (their title names both place and region, so no activity word); a fallback of
  '<title> · <activity>' would read better, if you want it.
- **Carried:** the VoiceOver pass (13C), the region pages' year heads (13B), the gap1-01 and qa-04 sheets (Phase 12),
  the hero frame and the mile table's last row (Phase 10), the real-phone look, the checkout and cache moves,
  `strava_id`, the rehearsal push (Phase 8), the place names, retitles and merges (Phase 9). Phase 15 (one render
  round) needs your agreement to run `render.py` and, by the plan, more free disk (13 GB now).

## Phase 15 - Renderer round and storage budget (2026-10-25)

Phase 15 of `docs/personal-website-improvement-plan-2.md` (section 15) and its prompt in
`docs/claude-code-website-prompt-2.md`, built on branch `phase-15-render-round` from `phase-14-metadata-sharing` at
`be6e5d8`, in one session that held all three sittings (before the run, the run, after it). Eric agreed to the render
("Yes", 2026-10-25) and said not to worry about the disk (14 GB free, under the plan's 20 GB). Three commits:
`3346ccb` (the code, tests and goldens), `f2132d2` 'Render round 2026' (`rendered/` alone, staged by path) and the
commit holding this entry (the storage budget, the yearly upkeep list and the cost beside VERSION). The second needs
the first: base.css's halo and touch width rely on the redrawn site maps' class rule, and the redrawn maps on the new
MAP_CSS. Push them to `main` together.

### Author inputs

- **Hillshade quality: q80.** The preview sheets (`.cache/plan2/phase15/quality-*.png`: three site maps and the
  Matterhorn maps at q88, q80 and q75, 1x and 2x) showed no visible difference; q80 was 29 to 35 % smaller than q88.
  Eric did not pick between them (he asked for the branch push instead); the recommended q80 was taken under his
  standing instruction. On the committed files the hillshades went from 23.9 MB to 16.2 MB (-32 %).
- **The run:** 2026-10-25 around noon, `/opt/homebrew/bin/python3.12 tools/render.py --jobs 3 --no-site` (32 minutes,
  168 trips, none failed, no OpenStreetMap missing), then `--site` (5 minutes, 15 maps, all from cached answers).
  Both summary lines are in the 'Render round 2026' commit message.
- **The cost:** `git diff --stat -- rendered`: 1,427 files changed (1,241 changed, 168 new card drawings, 18 new files
  for the three panel maps). Packed, the round adds 18.8 MB of history (a thin pack of `f2132d2` against `3346ccb`;
  the 2026-09-28 round measures 9.7 MB the same way). Tracked `rendered/`: 51.0 MB before, 45.4 MB after.
- **count-objects:** before the round (`be6e5d8`) 5,733 loose objects, 53.49 MiB, and a 182.75 MiB pack; after
  `f2132d2` 7,610 loose, 77.08 MiB, the same pack. The whole history repacks to 224.2 MB (204.7 MB on 2026-10-13).
  `git gc` is due (DEVELOPING.md, Yearly upkeep, item 1); it is yours to run.
- **The contact sheet** of every changed map is in `.cache/render-sheet/index.html` (`render_sheet.py --all`); I
  looked through it; your own look is pending.
- **Region merges:** none were decided in Phase 9, so the round carried none and there are no old region URLs to
  check.
- **Pending yearly items** (DEVELOPING.md, Yearly upkeep): every workflow action has a newer major than the one
  pinned (a bump wants a `workflow_dispatch` proof run, so it is left to you); `git gc`; nine stray `.git/index N`
  files; both Overpass endpoints timed out on a one-node query on 2026-10-25 (the round did not need them); the
  render caches are still in `.cache/` (the move in DEVELOPING.md, Render caches).
- **Interface copy to read:** the panel headings 'Ride map by region' and 'Hike map by region'; the panel maps' alt
  text 'Map of mountain bike trips in <region>' and 'Map of hiking trips in <region>'; a one-region panel's label (the
  region's name, linked to its page); 'Kilometer' in the map key's KM view; a cluster's tooltip 'N reports start
  here: A; B; C and K more' ('1 report starts here: A'); the PCT's month labels 'MAY' to 'SEP'.

### Changed files

| File | Change |
| --- | --- |
| `tools/lib/renderkey.py` | VERSION 8 with the cost of a round beside it; `TALL`, `track_aspect`, `report_frame`, `FRAME_SINCE` and the frame in `trip_inputs`; ride and hike panel jobs in `site_jobs` (`PANEL_TRIPS`); `drawn_titles` reads the new cluster titles. |
| `tools/render.py` | `renderer_record` (meta['renderer']), `osm_fetches` and `POOL_FETCHED`; `HILLSHADE_Q` 80 with `-m 6`; the cwebp stop and `--allow-png`; `--list`; the progress and summary lines; the tall frames, the card drawing, the PCT month labels and the panel maps; the journal drawn with `--jobs`; `render_folders` leaves iCloud copies alone; the 'map frame changed' reason. |
| `tools/lib/mapkit.py` | The wide scale bar up to 200 px; contour labels and distance discs in both units; `cluster_title`; `point_labels`; the hit stroke as MAP_CSS's `.mk-line .mk-hit`; `render_tile(width=)`; two files closed. |
| `tools/lib/geo.py` | Tiles as `array('d')`, at most 256 in memory. |
| `tools/lib/checks.py` | The warning while renders disagree on the renderer version, or the site maps are older than the newest trip. |
| `tools/sitegen/core.py`, `pages/report.py`, `multiday.py`, `home.py`, `section.py`, `tools/build.py` | `card_tile` and the card drawing copied; `mile_key` and the Kilometer key; `relabel` through `cluster_title`; the ride and hike panels (`PANELS`, one region shown with its label). |
| `assets/css/base.css`, `pages/section.css` | The halo and the touch width without `!important`; `.sec-rp--one`. |
| `tools/render_sheet.py`, `tools/size_report.py` | New author tools. |
| `tests/` | New: `test_mapkit_golden.py` with `golden/render/`, `test_render_contract.py`, `render_fixtures.py`, `test_render_sheet.py`, `test_size_report.py`, `test_phase15.py`; changed: render goals (run record, renderer change, jobs, accounting), the credits test in `test_report_page.py`, and expectations of the new renderer in eight others. |
| `rendered/` | The round (`f2132d2`). |
| `docs/DEVELOPING.md`, `README.md`, `ADDING-TRIPS.md` | A render round, the 2026 changes, Storage budget, Yearly upkeep and the pointers to them. |

### Behaviour

- Every map is drawn by renderer 8. The 34 tall single-day tracks have 1440 x 800 and 718 x 500 frames; the ten
  multi-day phone overviews carry numbered day squares; the PCT overviews carry month labels; the Matterhorn wide
  map's scale bar reads 1 mi; 157 wide maps label their contours in both units and 146 carry a kilometre disc set.
- Cards show the 400 x 267 drawing (168 published); Mountain biking has the panel with Santa Cruz (43) and Lake
  Tahoe (9), Hiking the Lake Tahoe panel without a tab row; cluster tooltips read 'N reports start here: …'.
- Before and after captures of the Matterhorn report, the Haute Route, map/, Mountain biking, Hiking and the home
  page at 1280 and 390 px are in `.cache/plan2/phase15/` (`before-*`, `after-*`, `after-*-panel-*`).

### Where the work departs from the prompt

- **`--jobs 3` and no `--budget`:** the round fitted one sitting (32 minutes), so it ran once with three workers on
  a 10-core Mac; the prompt's `--jobs 2 --budget 3600`, repeated, stays the documented way for a longer round.
- **Three commits, not two:** the code first, so the renders are made by committed code; the budget and the log after
  the round, since they hold its measured cost.
- **The caches were not moved** before the run (the prompt's pre-run check); the run used `.cache/` as it is.
- **Fixed on the way, both older than Phase 15:** `render.py --jobs N` never drew the journal (the series was left
  out of the pool and the one-at-a-time loop skipped; since 2026-09-28); and a run removed iCloud copy folders
  (`<slug> 2`) as renders of gone trips. This round removed 66 such folders before the fix, and the folder swap of
  every redrawn trip dropped the copies inside it: about 6,200 untracked iCloud copies under `rendered/` are gone,
  none of them tracked. `tidy.py --delete` would have removed the same ones; the project leaves that to you.
- **Ten files iCloud put back:** after the run, five trip folders held `map-*.png` and `*.meta.json` files that
  render.py had already converted and deleted (they lack the provenance attribute every file the run wrote has).
  They are untracked, left out of the commit, and left in place; the next redraw of those trips removes them.

### Review

An independent read-only review of the code found no blocking defect; everything it found was fixed: a one-region
panel hid its region's name while scripting ran; the summary counted a failed trip again as left when a budget
stopped a run, and the journal as skipped; the progress line repeated; a trip drawn from a pool area fetched in the
same run recorded 'cached'; `drawn_titles` split the new cluster titles wrongly; `test_phase15` printed a
ResourceWarning (two files in mapkit closed now); the tab counts left out the featured report; a frame-only change
had no reason of its own in `--status`; a run past its budget skipped the site maps although only unchanged trips
were left; the panel tests mocked away the real lookup of the panel maps (a test now reads a synthetic site meta);
and two fixture docstrings called their spot open water. It also noted that the CSS must reach `main` with the
redrawn site maps (above).

### Checks actually run

| Check | Result |
| --- | --- |
| Both Pythons, `-W error`, `RENDER_TESTS=1`, before the run | 3,232 tests OK on 3.9.6 (201.5 s) and 3.12 (154.0 s), after fixing eight expectations of the new renderer |
| The goldens under `PYTHONHASHSEED=1` and `=2` | OK, both |
| `python3 tools/doctor.py` before the run | WARN disk 14 GB, 8 `.git/index` copies, 6,138 iCloud copies; all 5,092 tracked files on disk |
| `render.py --list` | 168 trips, 'renderer changed'; site maps stale |
| Preview renders into a temp folder | three trips and five site maps; the quality and contact sheets in `.cache/plan2/phase15/` |
| The run | the two summary lines above; `render.py --status` after: all 168 up to date, site maps up to date |
| `rendered/` after | no null hash, no `osm_failed`, all at renderer 8; no PNG, temp or old folder tracked or staged |
| `render_sheet.py --all` | `.cache/render-sheet/index.html` |
| `build.py --out <scratch> --link --check` | 365 pages, 168 trips, link check OK |
| `validate.py` | 0 errors, 1 warning (a planned route without a goal.json), 346 notes; no renderer-version warning |
| Both Pythons, `-W error`, `RENDER_TESTS=1`, after | 3,241 tests OK on 3.9.6 (207.6 s) and 3.12 (155.2 s) |
| `size_report.py` before and after, `git count-objects -vH`, `git pack-objects --stdout` | the figures above and in DEVELOPING.md, Storage budget |
| `privacy_audit.py` | 1,004 photos, none with EXIF, XMP or a colour profile; section 6 unchanged |
| The sources (curl), the actions' releases (`gh api`), GitHub's limits pages and the runner README | as in Yearly upkeep |

Not run: Lighthouse; a VoiceOver pass; anything after a deploy (there was none).

### Remaining issues and author inputs

- **Publishing:** nothing of Phase 15 is pushed. Phases 6 to 14 are on GitHub as branches (pushed at your word on
  2026-10-25); `main` is still `1cb9cf2`. The prompt's review gate is the step before a push to `main`.
- **Yours:** a look at the contact sheet; `git gc`; the `.git/index N` files; whether to delete the ten files iCloud
  put back; the workflow actions' bump; the cache move.
- **Carried:** the VoiceOver pass (13C), the region pages' year heads (13B), the gap1-01 and qa-04 sheets (Phase 12),
  the hero frame (Phase 10), the real-phone look, the checkout move, `strava_id`, the rehearsal push (Phase 8), the
  place names, retitles and merges (Phase 9), and the after-deploy checks of Phase 14.
