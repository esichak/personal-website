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
