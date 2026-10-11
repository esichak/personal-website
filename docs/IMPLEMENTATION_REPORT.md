# Implementation report: website improvement plan, Phases 0 to 5

Written 2026-10-10 at the end of Phase 4. The plan is `docs/personal-website-improvement-plan.md`; the phase-by-phase
record of what was changed and what was run is `docs/WEBSITE_IMPLEMENTATION_LOG.md`. This report is the handoff the
plan's Phase 4 gate asks for. It keeps three kinds of statement apart:

- **Measured**: a number or an observation from a run that is described here, with its method.
- **Target**: a goal from the plan. A target is not a result.
- **Not run**: a check that was not made, with the reason.

All work is on the branch `phase1-curated-homepage`. Phases 1, 2, 2T and 3 are committed there (Phase 3 is
`6f6091d`), and Phase 4 is the commit that adds this report. Nothing has been pushed or deployed: the public site
is still the build of `main`.

Section 14, on Phase 5 (region pages), was added later the same day. Sections 1 to 13 describe the site at the end
of Phase 4, except for the few lines that say otherwise.

## 1. Where things stand

| Phase | What it delivered | State |
| --- | --- | --- |
| 0 and 1 | Baseline; the curated home page (`content/home.json`), covers and focal points, card summaries | Committed (`c46949e`) |
| 2 | The Trips explorer: search, filters, URL state, a static search index | Committed (`ca5c6ec`) |
| 2T | The Tick list: goals, GPX intake, outings, the goal page | Committed (`a0eb1cd` to `282d0db`) |
| 3 | Story layout for reports, related reports, copy link, the PCT journal page, journal-day search | Committed (`6f6091d`) |
| 4 | Validation, measured loading changes, share metadata and structured data, privacy notes, author docs, this report | Committed (`fb425ab`, and `c7ed3ee`, which corrects one row of this report) |
| 5 | Optional expansion. Scope decided on 2026-10-10: region pages only (section 14). Collections, a summit index, reading bookmarks and an interactive map were not built | The commit that adds section 14 |

What Phase 4 added, in short:

- **A content validator.** `python3 tools/validate.py` reports every broken content file in one run, one line each, and
  the build runs the same rules before it touches its output folder. Before this phase 31 of 187 malformed inputs
  ended in a Python traceback and 86 were accepted without a word (section 7).
- **Built-site checks.** `build.py --check` still verifies every link, image and anchor, and now also each page's
  metadata, the sitemap, the feed, the two search indexes and the bytes of every published GPX file. It takes about
  1 second where the old link check took about 13.
- **Loading changes, each one made because a measurement asked for it** (section 3): phones are offered the 800 px
  photo copy for full-width photos of ordinary shape, cards on phones get a 320 px copy, the search forms no longer
  appear late and push the page down, and the published stylesheet no longer carries its comments.
- **Share metadata and structured data** from content only (section 8): image size and description on every page that
  shares a photo, a site-level share image on the four pages without a photo of their own, `BlogPosting` data on the
  67 pages that are written reports, and optional `published_at` / `updated_at` fields that are never guessed.
- **Capability-driven pages.** No download control without a file. A report without a track (none exists today) has
  no map section, no route links and no claim of a recording, and renders left behind by a removed track are no
  longer published.
- **Accessibility fixes** from two real keyboard walks (section 5.2).
- **Privacy observations** in `docs/PRIVACY_NOTES.md`, with `tools/privacy_audit.py` to reproduce them. Track
  publication policy is unchanged and Git history was not touched (section 9).
- **Author docs** corrected by following them literally on scratch content (section 5.4).

## 2. Measured results

### 2.1 Method

Every number in 2.2 to 2.4 comes from one method, so builds can be compared with each other. It is a lab
measurement on one Mac; it is not field data from visitors.

- **Builds.** Three builds of the real content, each served under `/personal-website/` by a local server that
  gzips text as GitHub Pages does: *original* (commit `a9baab9`, the site before the redesign), *before* (commit
  `6f6091d`, the end of Phase 3) and *after* (the working tree at the end of Phase 4).
- **Browser.** Chrome 155, driven through its DevTools protocol. Each run is one cold load in a fresh browser
  context, so the HTTP cache and storage are empty.
- **Phone profile.** Viewport 390 x 844 CSS px at 3 device pixels per CSS pixel, touch, network throttled to
  Chrome's "Slow 4G" preset, CPU slowed 4 times. Three runs per page; the table gives the median.
- **Desktop profile.** Viewport 1440 x 900 at 1x, no throttling. One run per page.
- **What is read, in the page.** Largest Contentful Paint and layout shifts from `PerformanceObserver` (layout
  shifts without recent input, summed: CLS), first contentful paint from the paint timing entries, and every
  request's transferred bytes from resource timing. The page waits 4 seconds after its load event before reading.
- **Pages.** Home, Trips, the Matterhorn report, the Peak Bagging report, the PCT journal, the Map page (the six the
  plan names), plus a multi-day trip, a short report and the Tick list.
- **What is left out.** Font files are fetched from Google Fonts in every build but did not appear in the page's
  resource timing list, so no byte total includes them (2.6). Interaction latency (INP) needs real input over time
  and was not measured.
- **Repeatability.** The collection scripts were scratch files and are not in the repository. The steps above are
  enough to repeat the method with any tool that can throttle and read the same browser entries.

### 2.2 Page loads on the phone profile

Median of three cold loads. LCP in milliseconds; CLS is the sum of layout shifts; KB is everything transferred
except font files. "n/a": the page did not exist in the original site.

| Page | LCP ms original | before | after | CLS original | before | after | KB original | before | after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Home | 1620 | 5872 | 1744 | 0.000 | 0.000 | 0.000 | 114 | 1022 | 344 |
| Trips | n/a | 2132 | 1508 | n/a | 0.142 | 0.035 | n/a | 834 | 229 |
| Matterhorn report | 1660 | 4084 | 1748 | 0.000 | 0.000 | 0.000 | 428 | 358 | 179 |
| Peak Bagging report | 1652 | 6244 | 1896 | 0.037 | 0.036 | 0.036 | 825 | 867 | 308 |
| PCT journal | 1820 | 4200 | 1768 | 0.036 | 0.036 | 0.036 | 164 | 438 | 248 |
| Map | 1740 | 1764 | 1632 | 0.041 | 0.041 | 0.041 | 206 | 224 | 214 |
| Multi-day (Haute Route) | 1724 | 1740 | 1616 | 0.046 | 0.000 | 0.000 | 137 | 156 | 147 |
| Short report | 1588 | 3464 | 1624 | 0.000 | 0.000 | 0.000 | 471 | 377 | 166 |
| Tick list | n/a | 2052 | 1424 | n/a | 0.489 | 0.107 | n/a | 67 | 57 |

| Page | Image KB original | before | after | Images original | before | after | Requests original | before | after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Home | 24 | 928 | 260 | 1 | 4 | 4 | 17 | 9 | 9 |
| Trips | n/a | 734 | 138 | n/a | 9 | 6 | n/a | 16 | 13 |
| Matterhorn report | 366 | 278 | 108 | 4 | 2 | 2 | 10 | 8 | 8 |
| Peak Bagging report | 759 | 782 | 232 | 3 | 3 | 3 | 9 | 9 | 9 |
| PCT journal | 39 | 293 | 112 | 1 | 2 | 2 | 6 | 7 | 7 |
| Map | 34 | 34 | 34 | 1 | 1 | 1 | 19 | 19 | 19 |
| Multi-day (Haute Route) | 43 | 43 | 43 | 1 | 1 | 1 | 7 | 7 | 7 |
| Short report | 411 | 299 | 98 | 4 | 3 | 3 | 10 | 9 | 9 |
| Tick list | n/a | 0 | 0 | n/a | 0 | 0 | n/a | 6 | 6 |

What the table says:

- **The redesign had made photo-led pages slow on a phone, and Phase 4 undid that without removing the photos.**
  Phases 1 to 3 put a photograph first on the home page and on story reports. A 3x phone was then sent the 1600 px
  files: the home page went from 114 KB to 1,022 KB and its lab LCP from 1.6 s to 5.9 s. After Phase 4 the same page
  is 344 KB with an LCP of 1.7 s, and every one of the nine pages is between 1.4 and 1.9 s.
- **The pages are lighter than the original where the original already had photos** (Matterhorn 428 to 179 KB, Peak
  Bagging 825 to 308 KB, the short report 471 to 166 KB) and heavier where the redesign added a photograph that was
  not there before (Home, the PCT journal).
- **Run-to-run spread is small on this profile.** The three runs of a page differ by at most 52 ms in the after
  build. The after build was measured three times over about five hours, the last time on the final code, and that
  last set is the one in the tables: across the three sets every median LCP is within 40 ms and every byte total
  within 3 KB.
- One before-run of Trips took 5.0 s where the other two took 2.1 s; the median hides it.
- The largest single image any of these phone loads transferred after Phase 4 is 107 KB.

### 2.3 Page loads on the desktop profile

One cold load per page, no throttling.

| Page | LCP ms original | before | after | CLS original | before | after | KB original | before | after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Home | 300 | 356 | 584 | 0.001 | 0.000 | 0.000 | 226 | 605 | 595 |
| Trips | n/a | 404 | 440 | n/a | 0.050 | 0.002 | n/a | 895 | 887 |
| Matterhorn report | 284 | 340 | 372 | 0.000 | 0.000 | 0.000 | 408 | 427 | 418 |
| Peak Bagging report | 296 | 284 | 372 | 0.001 | 0.000 | 0.000 | 155 | 534 | 524 |
| PCT journal | 324 | 340 | 352 | 0.001 | 0.001 | 0.001 | 323 | 494 | 485 |
| Map | 344 | 372 | 368 | 0.031 | 0.031 | 0.031 | 272 | 290 | 281 |
| Multi-day (Haute Route) | 316 | 352 | 348 | 0.001 | 0.001 | 0.001 | 217 | 236 | 227 |
| Short report | 316 | 324 | 424 | 0.001 | 0.000 | 0.000 | 296 | 315 | 306 |
| Tick list | n/a | 308 | 348 | n/a | 0.080 | 0.001 | n/a | 67 | 57 |

- **Timing measures the font stylesheet, not the build.** In all 25 desktop runs of the three builds, first paint
  came 39 to 89 ms after the stylesheet from Google Fonts arrived, and in 21 of them the LCP is that first paint.
  That one request, to a server outside the build, took 236 to 347 ms, and 524 ms in the final run of Home, which
  is the 584 ms in the table (every other LCP is between 284 and 440 ms). With one run per page, the differences
  between builds in the LCP columns say nothing about the builds. What they do say is taken up in section 12,
  decision 3.
- **Bytes are what they were before the phase, less about 10 KB of stylesheet.** The image bytes are identical,
  page by page, before and after: from 560 px up a card loads exactly the photo it loaded before, and a 1440 px
  window still loads the 1600 px lead photo, on purpose.
- **A saving that was given back.** The card-size copy was first offered at every width, which took the desktop
  Trips page from 895 to 313 KB and Home from 605 to 407 KB. Before and after screenshots side by side then showed
  card photos visibly softer on a 1x desktop screen (a 427 px file drawn in a 400 px slot). The copy is now offered
  to phones only, where the slot is 112 px, and the desktop pages load what they always did.
- **Layout shift.** Trips went from 0.050 to 0.002 and the Tick list from 0.080 to 0.001 (the search form no longer
  appears late).

### 2.4 The loading changes, and the measurement behind each

| Change | Why (measured before) | Result (measured after) |
| --- | --- | --- |
| Phones are told that a full-width landscape photo fills about half the screen width (`core.PHONE_SLOT`), so a 3x phone picks the 800 px copy | Phone image bytes: Home 928 KB, Peak Bagging 782 KB, PCT 293 KB, Matterhorn 278 KB; LCP 4.1 to 6.2 s on those pages | 260, 232, 112 and 108 KB; LCP 1.7 to 1.9 s. Portraits, squares and panoramas are left at the real width, because their 800 px copy is too small for the slot (a reviewer measured a 1.7x to 2.5x upscale). |
| A 320 px copy (`.th`) for card covers, offered to phones only (`<picture>` with a source for widths under 560 px) | Trips loaded 734 KB of card images on a phone | 138 KB. Every card photo a phone loaded on Trips and Home was the card copy; no desktop load requested one |
| The Trips and Tick list search forms are revealed by a script right after the form, not by the deferred bundle | CLS 0.142 on Trips and 0.489 on the Tick list: the form appeared late and pushed everything down | 0.035 and 0.107; what is left is the web-font swap (2.5) |
| Comments stripped from the published stylesheet | 35.1 KB gzipped, on the critical path of every page | 22.7 KB gzipped |
| The site check reads each page once | The old link check took about 13 s on the real build | About 1 s, with more rules |

Not changed, because no measurement asked for it: the Map page's tab row (its shift is 0.041 and was 0.041 in the
original), the JavaScript bundle's structure, the font request, the PCT journal's markup.

### 2.5 The layout shift that is left

Three pages shift once, late in the load, by the same amount in all three builds: the PCT journal (0.036), the Peak
Bagging report (0.036) and the Map page (0.041). The Tick list shifts by 0.107 on a 390 px phone, a little over the
0.1 target. On the Tick list this is one shift at the moment the web fonts replace the fallback fonts: with the
fallback the filter row wraps onto one more line, with the web font it fits, and everything below moves up 52 px.
It was confirmed by switching a loaded page between the two font stacks; revealing the form moves nothing.

One fix was tried and not adopted: fallback fonts adjusted to the web fonts' widths (`size-adjust`). Measured at
six phone widths, it moved the re-wrap from some widths to others instead of removing it.

The options that would remove it change what a first-time visitor sees, or add files, so they are left to the
author: `font-display: optional` (a slow first visit keeps the fallback fonts for that page view), self-hosting the
fonts with a preload (shortens the swap; adds font files to the repository), or a filter row that scrolls sideways
on phones instead of wrapping.

### 2.6 Bundle sizes

Bytes as served by the measurement server (gzip) and on disk.

| File | Original | Before Phase 4 | After Phase 4 |
| --- | ---: | ---: | ---: |
| `assets/site.css`, gzipped | 31,281 | 35,059 | 22,697 |
| `assets/site.css`, on disk | 145,498 | 164,701 | 136,408 |
| `assets/site.js`, gzipped | 10,586 | 24,651 | 26,999 |
| `assets/site.js`, on disk | 37,049 | 91,304 | 99,612 |

The script grew in Phase 4 by the code that adopts a visitor's early input, retries a failed search and fixes the
keyboard defects. Four web-font files are fetched from Google Fonts in every build (212 KB in all by their stated
length when a page uses all four); the browser's resource timing list did not include them in any run, so they are
in no total, for any build.

### 2.7 Lighthouse (lab, local)

Lighthouse 13.4.1, 12 pages, mobile and desktop, before and after. Accessibility, best practices and SEO are 100 on
every page in both passes, with one exception that is the test server's: a mobile run of the Map page scored SEO 92
because Lighthouse's own request for `robots.txt` timed out; two repeats scored 100. The tool's layout-shift audit
went from 0.365 to 0.000 on the Tick list and from 0.099 to 0.000 on Trips (0.019 on one repeat of the Tick list).
One informational accessibility audit is unchanged from the original site: on Home and on an activity page, some
links are named by their title and details rather than by all of their visible text.

### 2.8 Build and check time

A full local build with `--link --check` takes about 4 seconds: about 0.15 s for the content validation, 2 s for the
build and 1 s for the site check. A copying build with the check took 3.9 s when every file was on disk. On this Mac
a build can take minutes instead when iCloud has offloaded files under `rendered/`; that is the machine, not the
build (see section 11).

## 3. Targets from the plan, against what was measured

| Plan target (section 12) | Kind | What can be said |
| --- | --- | --- |
| LCP at or below 2.5 s at the 75th percentile of real visits | Target | No field data exists for this site. In the lab, on the phone profile of 2.1, the median LCP of all nine pages is under 2.5 s after Phase 4 (table 2.2). That is a lab result on one machine, not the target itself. |
| CLS at or below 0.1 | Target | Lab: under 0.1 on eight of nine pages. The Tick list measured 0.107 on a cold slow load at 390 px; the cause and the options are in 2.5. |
| INP at or below 200 ms | Target | Not measured. It needs real interactions over time; lab Lighthouse does not establish it. |
| Mobile home page transfer around 1 to 1.5 MB or less | Target | Measured: 344 KB on the phone profile, fonts not included (about 160 to 210 KB more). |
| Lead-photo variants around 250 to 300 KB or less | Target | Measured on the phone profile: the lead images loaded were the 800 px copies, and the largest single image any of the nine pages transferred is 107 KB (2.2). The full 1600 px files are still what a large desktop window loads. |
| No interactive map and not all trip photos on the home page | Target | Met by construction since Phase 1; the home page made 4 image requests on the phone profile. |

## 4. What was not measured

- **Field performance** (real visitors, real networks, INP). The site has no analytics, by choice.
- **Lighthouse's performance score.** The tool used leaves that category out, and a local server's score would not be
  a field result anyway.
- **The CI job itself.** Nothing was pushed, so GitHub has not built this branch. It was rehearsed locally (5.3).
- **Safari and Firefox.** Every browser check was made in Chrome 155. The CSS and JavaScript avoid engine-specific
  behaviour where that was known, but nothing was run elsewhere.
- **Real devices and screen readers.** Phone sizes were emulated in desktop Chrome; safe-area insets, real touch
  scrolling and VoiceOver or TalkBack output were not observed.
- **True forced-colours rendering.** Checked with Chrome's media emulation on macOS, not with Windows contrast themes.
- **A real share preview.** The share tags are checked for form and truth by tests; no post was made to see how any
  service draws the card.
- **The map renderer.** `tools/render.py` needs the internet and rewrites committed assets, so it was never run in
  any phase. Its changes in Phases 2T and 4 are covered by tests that stub the drawing code, and everything said here
  about its behaviour on real content comes from reading it.

## 5. Test matrix (plan section 16)

### 5.1 Automated checks

`python3 -m unittest discover -s tests` runs 2,021 tests in 36 files in about 25 seconds, on Python 3.9
(local) and 3.12 (CI), with `-W error` on both. Three Node harnesses run the pure JavaScript helpers (253
checks); the Python runners skip them when `node` is absent, as on CI.

| Area (plan row) | Where it is tested | State |
| --- | --- | --- |
| Featured configuration | `test_curation.py`, `test_home.py`; the manifest's findings in `test_checks.py` | Covered |
| Cover resolution | `test_cover.py`, `test_thumbs.py`; photo rules in `test_checks.py` and `test_frontmatter.py` | Covered |
| Summary provenance | `test_summary.py`, `test_cards_extra.py`, `test_series_page.py`, `test_track_rules.py` | Covered |
| Source preservation | Write-up text and GPX bytes compared between builds (5.3); the GPX rule of `build.py --check` on every build (`test_sitecheck.py`, `test_build_site.py`, `test_build_cli.py`) | Covered, and re-checked on every build |
| URLs and anchors | `test_sitecheck.py` (links, anchors, ids), `test_report_page.py` (legacy ids), `test_series_page.py` (day and month anchors, decimal labels), `test_archive_page.py`; builds served under `/personal-website/` (5.3) | Covered |
| Search | `test_search.py`, `test_journal_days.py`, `test_trips_page.py`, `trips_js_harness.js` | Covered |
| Conditional UI | `test_report_page.py` (no track, no stats, no write-up, no photos), `test_track_rules.py`, `test_build_site.py` (built sites with such reports, stale renders) | Covered, with fixtures, since no real report lacks a track |
| Tick list and intake | `test_gpxroute.py`, `test_ticklist_cli.py`, `test_goals.py`, `test_render_goals.py` | Covered |
| Goal lifecycle | `test_goals.py`, `test_ticklist_cli.py`, `test_ticklist_page.py`; goal findings in `test_checks.py` | Covered |
| Tick-list publication | `test_ticklist_page.py`, `test_ticklist_cli.py`, `ticklist_js_harness.js` | Covered |
| Metadata | `test_metadata.py`, `test_sitecheck.py`, `test_sitecheck_hostile.py`; the META, SITEMAP, FEED and INDEX rules of `build.py --check` on every build | Covered |

Added in Phase 4 beyond the plan's rows: the content validator (`test_checks.py`, `test_checks_more.py`,
`test_checks_site_maps.py`, `test_validate_cli.py`), the build command (`test_build_cli.py`), static accessibility
rules read from the built CSS and JavaScript (`test_a11y_static.py`), the privacy tool (`test_privacy_audit.py`).
Most new test groups were checked with mutants on a scratch copy: a single-line change to the rule had to make a
test fail. The counts are in the log's Phase 4 entry.

Not automated: the page behaviour of `base.js`, `trips.js`, `ticklist.js` and `series.js` in a real browser. Their
decisions are pure functions that the Node harnesses run, and the wiring was exercised in Chrome (5.2), but no
browser test runs in CI.

### 5.2 Browser and visual checks

Two walks in Chrome 155 with real key presses: one on the build before Phase 4, one on the build after its first
round of changes, plus targeted re-checks after the later fixes. "Run" means the check was made and what follows is
what was observed.

| Check (plan row) | State | Result |
| --- | --- | --- |
| Widths 320, 390, 768, 1024, 1440 | Run | No horizontal scrolling: 28 loads at 320, 360, 390 and 412 px on seven page types in Phase 4, and 21 page types at 320 to 1440 px in Phase 3. |
| Portrait and landscape | Run | 667 x 375 landscape on a story and a multi-day page: the sticky bars took 32.5% of the height on the multi-day page (45.1% before; its day bar no longer sticks under 480 px of height). |
| 200% zoom | Run | 15 loads at 720 x 450, 640 x 400 and 320 x 568 at 2x: no horizontal scrolling, no text outside the viewport, no clipped text except intended line clamps. |
| Keyboard-only operation | Run | Home, Trips, Tick list, a story report at 1440 and 390, a multi-day trip, the PCT journal, the photo viewer, the phone menu, the units switch. No trap and no lost focus after the fixes below. |
| JavaScript disabled | Run | Headless Chrome with scripting off: every report, goal and journal day is listed and every anchor lands clear of the header. Controls that need script are not shown. |
| Reduced motion | Run | With the preference set, every transition computes to 0.01 ms and the multi-day day strip jumps instead of scrolling. |
| Blocked image and index requests | Run | With images blocked no box collapses (every image has its size). With the search index offline the Trips page says search is unavailable and the filters still work. |
| Long titles and empty optional metadata | Unit tests only | Fixtures cover long and hostile titles and every absent optional field; no browser pass was made for them in this phase. |
| Visible focus, skip link, headings, names, image descriptions | Run | Skip link first on all 12 pages; one `h1` each and no skipped level; no image without an `alt` attribute; no unnamed link or button. |
| Menu focus and viewer focus return | Run | The phone menu makes the rest of the page inert and returns focus to its button; the photo viewer returns focus to the photo that opened it. |
| 44 px touch targets | Run | After the fixes, every target the walks found under 44 px answers a press over at least 44 x 44 px: the filter chips as real boxes, the others through hit areas that change no box. Each was probed pixel by pixel in Chrome at 320, 390 and 1440 px. One accepted exception: card title links, whose whole card is the target. |
| Bottom bar: safe areas, no overlap | Partly run | The bar is 65 px and the page's last line ends 56 px above it; no focused element sits under a sticky bar. Safe-area insets cannot be observed in desktop Chrome: not run on a device. |
| Before and after screenshots | Run | 36 views (12 pages, each at 1440 px, at 390 px, and at 390 px scrolled to the bottom) were captured from the build before the phase and from the final build, and compared pixel by pixel outside the scrollbar. 31 are identical to the captures made before the phase. Two differ where intended: on Trips and the Tick list at 390 px the `All` filter chip is 6 px wider and pushes the chips after it, and the Trips search placeholder, which was clipped in the middle of a letter, ends in an ellipsis. Three differ from the stored earlier captures only in pixel values (the desktop home page's photos, two card photos on Trips by one level in 256, and 13 pixels of an arrow icon); for those three views a fresh cold capture of the build before the phase is pixel-identical to the final build, so the difference lies in the earlier captures and not in the builds. Why those captures differ was not established; they were taken in a browser session that had loaded other pages first. An earlier pass of the same comparison is what found the softer desktop card photos and the layout moves listed below. |
| Network panel: image selection and priority | Run | Read from the loads of 2.1 and from the walk: on the phone profile the lead image is the 800 px copy with high priority, cards load the 320 px copy, and no 1600 px file was requested on Home, Trips or the two story pages. |
| Lighthouse (not a plan row) | Run | Accessibility, best practices and SEO 100 on 12 pages, mobile and desktop, before and after (one mobile run of the Map page scored SEO 92 because the local server timed out on `robots.txt`; two repeats scored 100). |

Defects the walks found, and what became of them:

| Defect | State |
| --- | --- |
| Focus moving backwards could land under the second sticky bar (PCT month bar, multi-day day bar) | Fixed: scroll margins on the controls; re-walked. |
| With JavaScript off, the menu button, units switch and Search link were shown and did nothing | Fixed: hidden when scripting is off; the five main links wrap into view at every width; re-checked from 320 to 1280 px. |
| Hidden map cluster markers were Tab stops | Fixed: 66 stops on Home where there were 80. |
| Sticky bars took over 40% of a short landscape window on a multi-day page | Fixed (32.5%). |
| The copy-link fallback field stayed open when focus left it | Fixed. The first fix made Escape throw and drop focus; that was caught by the second walk and by a reviewer, fixed, and re-checked in Chrome. |
| Targets under 44 px (year links, region links, the "All" radio, the view switch, the breadcrumb, the footer brand) | Fixed. |
| A phone at 2x and 375 px was handed the 427 px card copy for a full-width lead photo | Fixed before commit: the card copy is offered for card slots only. Found by a test author's measurement and confirmed in the second walk. |
| Card photos looked softer on a 1x desktop screen: the 427 px card copy was chosen for the 400 px card slot | Fixed before commit: the card copy is offered to phones only, and from 560 px up a card loads exactly what it loaded before the phase. Found by comparing before and after screenshots side by side. |
| Five of the 44 px target fixes had moved layout (the view switch and the section pages' filter band 2 px taller, the footer 20 px taller, the Trips year links spaced wider, one home-page link 2 px wider) | Fixed before commit: those targets reach 44 px through hit areas that change no box, and every box on the compared pages is where it was before the phase, except the `All` filter chip, which is 6 px wider on phones on purpose. Found by the same comparison. |
| A failed search was not retried when the same words were typed again (older than Phase 4) | Fixed. |
| Forced colours: the Map legend lost its colours and the units switch grew bars | Fixed in CSS; checked with Chrome's emulation only. |
| Five smaller observations from the first walk (the section row's order differs from the page's, 26 browse links precede the search box on Trips, "Show all journal days" reveals rows above the button, the offline count wording, the open menu button is still named "Menu") | Left as they are: each is a design choice or a wording question for the author, listed in section 12. |

### 5.3 Compatibility checks

Measured by comparing whole builds file by file, leaving aside the iCloud conflict copies a local build used to carry.

| Comparison | Result |
| --- | --- |
| Original site (`a9baab9`, 3,294 files) against the Phase 4 build | No path of the original is missing. Two pages are new (`trips/`, `tick-list/`), plus the two search indexes and the 105 card-size photo copies. |
| GPX downloads | All 351 are byte for byte what they were in the original build and in the Phase 3 build. No tracked file under `content/` differs from the last commit. |
| Write-ups | The text of every write-up is identical on all 345 pages the original had. |
| Feed, sitemap, robots | `feed.xml` and `robots.txt` are identical to the original; `sitemap.xml` gained the two new pages. |
| Titles, canonicals, descriptions | Identical on every original page except the planned route's description, which Phase 2T rewrote on purpose. |
| Anchors | Five ids of the original pages are gone, all internal: `toc-h` (the removed Contents list, 53 pages), `ph-h` (12 pages whose only photo became the lead photo; `#photos` moved onto it), and three home-page ids (`feat-l`, `feat-t`, `latest-h`). One in-page link of the old home page (`#latest-h`) has no target now. Every documented anchor is present: `map/#all-reports`, `map/#other-places`, the region and year anchors, and the PCT's `#day-…` and `#month-…` ids including `#day-5-2`. |
| Project-prefix URLs | Every build was served and walked under `/personal-website/`; 2,827 internal URLs across 12 pages all answered 200 with no redirect and no missing fragment. Links are relative (`core.link`), and `build.py --check` fails a link that leaves the folder. |
| Python 3.9 against 3.12 | The two builds are identical file for file. |
| What CI would see | A copy of exactly the 5,198 files this commit holds, taken from the staged index, on a case-sensitive volume, with Python 3.12, UTC, the C locale, and no `node`, `git`, `cwebp` or `sips` available: all tests pass (the Node-dependent ones skip), the build and its check pass, and the output is identical to the measured build. This ran on macOS; the CI job on Linux has not run, because nothing was pushed. |

### 5.4 Author documentation

`README.md`, `ADDING-TRIPS.md`, `docs/CONTENT_GUIDE.md`, `docs/TICK_LIST_GUIDE.md` and `docs/DEVELOPING.md` were
each rewritten where the audit found them wrong, then followed literally by a second reader on synthetic content in
a scratch copy (every command block, every quoted message), then corrected again. What that found and fixed:

- `ADDING-TRIPS.md` told the author to run `git add -A`, which would have staged about 6,300 iCloud conflict copies.
  The guides now stage by path, and `.gitignore` hides the copies under `rendered/` and `assets/`.
- The documented multi-day procedure produced a trip with no page. It was rewritten and works when followed.
- No guide said that only pushes to `main` publish. They do now, with the message Git gives on another branch.
- Following the guides exposed tool gaps that are now fixed: an iCloud copy of a day file was published as an extra
  day, a wrong Strava export path gave a traceback, the tick-list tool named a render folder that did not exist, and
  `build.py --out` could empty any folder.
- Every validator and site-check message the guides quote was produced for real before it was written down.

Not run: `tools/render.py`. Every instruction that involves it rests on reading its code.

## 6. What Phase 4 changed, by area

The file-by-file list is in the log's Phase 4 entry. In outline:

- **New tools.** `tools/validate.py` with `tools/lib/checks.py`; `tools/sitegen/sitecheck.py` behind
  `build.py --check`; `tools/thumbs.py`; `tools/privacy_audit.py`.
- **Build.** Content is validated before the output folder is touched. `--out` refuses a folder that is not an
  earlier build. `--only` rejects an unknown module. iCloud conflict copies are neither bundled, copied nor checked.
  The stylesheet is published without comments. The combined multi-day GPX is written exactly when the page offers
  it, keeps Windows line endings and namespace prefixes, and can no longer be written through a `--link` symlink
  into `content/`.
- **Generator.** Share tags and structured data; `published_at` and `updated_at`; photo `sizes` by shape and the
  card-size copy; search forms revealed inline; renders shown only for trips that still have a track; no empty
  sections or dead links for a report without a track or stats.
- **Renderer** (`tools/render.py`, not run): it now skips a report without a track, as it already skipped a goal
  without a route. Before, by reading the code, such a report would have stopped the run, and in the site-map step
  only after `rendered/site/` had been emptied.
- **JavaScript and CSS.** Keyboard and no-JavaScript fixes (5.2); the Trips and Tick list pages adopt what a visitor
  typed or chose before the script arrived; a failed search retries.
- **Docs.** The five author guides, `docs/PRIVACY_NOTES.md`, this report, the log.

## 7. Validation, before and after

Measured on 187 malformed inputs, each a small edit to an otherwise valid synthetic site (the table is kept as a test,
`tests/test_checks.py`):

| What the build did with the input before Phase 4 | Inputs | What the validator does now |
| --- | ---: | --- |
| Python traceback | 31 | 31 errors that name the file and the field |
| A clear error already | 52 | 52 errors, the same text in 51 cases; one is now reported one step earlier by a new rule |
| Built, then failed only in the link check | 18 | 15 errors; 1 warning (a report without a track is allowed); 2 are anchors that only exist in built pages and stay with the built-site check |
| Accepted without a word | 86 | 35 errors, 31 warnings, 20 still accepted because they are legitimate or merely absent optional fields |

On the real content the validator reports 0 errors and 1 warning (the one planned route saved before goals had a
`goal.json`), plus 467 notes for optional fields that are simply absent (no place, no write-up, no photos, untitled
days, photos without a caption), which it lists only with `-v`.

The plan asked for strict failures on broken new configuration and warnings for incomplete legacy metadata. That is
how the levels are set: an error stops the build, a warning does not.

## 8. Share metadata and structured data

Everything comes from content files; nothing is measured, worded or dated by the build.

- **Share image.** A page that shows a trip shares that trip's cover, with `og:image:type`, width and height (only
  when both are recorded) and `og:image:alt` and `twitter:image:alt` (only when the photo has a description).
  116 of the 347 pages carry one.
- **Site-level fallback.** Home, About, Map, Trips and Tick list share the cover of the first featured trip in
  `content/home.json`. A report without a photo of its own shares no image and keeps the small card, as before:
  another trip's photo on its card would misdescribe it. That leaves 62 trip pages with a text-only card (decision
  in section 12).
- **Structured data.** One `BlogPosting` block on a published report whose write-up has at least 100 characters of
  text: 67 pages. It holds the headline, the page address, the description the page already has, the
  author, and the page's own share photo with its recorded size. No ratings, no FAQ, nothing about conditions.
  Google's Article guidance was applied from memory, not re-read online, and the block was not run through a
  validator service; it is checked for being valid JSON of the right type on every build.
- **Publication dates.** `published_at` and `updated_at` are optional fields in `index.md`. When present they give a
  "Published" line on the page, `article:published_time` / `article:modified_time`, and the dates in the structured
  data. When absent, nothing about publication is shown or written. No real report has them yet: Git history cannot
  supply honest values, because all 168 trips arrived in two bulk commits.
- **Unchanged on purpose.** The feed's `pubDate` is still the trip date at 12:00 UTC, as in the original site; the
  feed is byte for byte the same. Changing it is a migration for a later, deliberate step (section 12).
- **Checked on every build.** One title, one description, one canonical equal to the page's own address, `og:url`
  equal to it, at most one share image that exists in the build, at most one structured-data block; the 404 page has
  no canonical and is `noindex`; the sitemap lists every indexable page once and nothing else.

A limit that predates the redesign: `robots.txt` is published at `/personal-website/robots.txt`, because the site is
a project site. Crawlers read `robots.txt` only at the root of a host, so that file and its `Sitemap:` line are not
read by them. Nothing was changed here; see section 12.

## 9. Privacy observations

`docs/PRIVACY_NOTES.md` has the full observations and `python3 tools/privacy_audit.py` reproduces its counts. The
default report prints counts only and is written so that nothing in it is about one track or one place. In short:

- Every recorded track is published in full, with a timestamp on every point, as the README has always said. That
  policy is unchanged.
- Tracks that start or finish in the same place, read together, describe places returned to and the times of day.
  The notes give the counts; they name no place, and no tracked file does.
- Photos carry no EXIF, XMP or colour-profile data, in the repository now and in its history.
- The repository is public, so it publishes more than the site shows: the front matter (Strava activity ids, time
  zones, start times, companions' first names) and each track's start and end coordinates in
  `rendered/trips/*/meta.json`.
- Removing something from the site does not remove it from Git history, and this work did not rewrite history.
- Drafting or deleting a trip, or removing its `track.gpx`, takes its page, download and own map off the site at
  the next build, but the shared region maps (Home, Map and Ski pages) keep its line until `tools/render.py` is run
  again. The validator now warns about exactly that. And where the trip has a pin of its own on one of those maps,
  the pin links to a page that no longer exists, `build.py --check` fails, and nothing is deployed: the trip stays
  online until the maps are rendered again. Taking a trip off the site therefore needs the renderer first (section
  12, decision 8).

The decisions these observations lead to are the author's and are listed in the notes and in section 12.

## 10. Known limits

- **Layout shift from the web fonts.** Described in 2.5.
- **Taking a trip off the site needs a render.** See section 9. A build cannot redraw the region maps, and a draft
  or deleted trip with its own pin there fails the check, so the old site stays up until `tools/render.py` has run.
  This is older than the redesign; Phase 4 added the warning and the documentation, not a fix.
- **Reports without a track** are handled on single-day pages. A multi-day trip or a journal with no day track at
  all still draws an empty map block; the validator warns. No real trip is in that state.
- **`tools/render.py` leaves drafts out**, also when a draft is named. A new draft goal or trip has no map until the
  flag is removed and the renderer is run. The tools and guides now say so.
- **"Stats from the GPS recording via Strava."** is written under the stats of every recorded trip, including one
  imported from a Garmin file. It is site copy; see section 12.
- **A `#` note after a value** in front matter is kept as part of the value, and a tab-indented block is half-read.
  The guides warn; the validator does not catch either.
- **The card-size copy does not help every cover.** It is 320 px on the short edge. For a photo wider than 5:2
  (three real photos) it is wider than the 800 px copy and is never the one picked. A portrait cover's copy is 320 px
  wide, so at the end of Phase 4 a 3x phone, which wants 336 px for the 112 px card slot, skipped it and loaded the
  copy it loaded before the phase. Phase 5 changed that for portrait and square covers (14.3).
- **An earlier build folder** given to `--out` is emptied along with anything put into it since.
- **Tests cite "the contract"** in docstrings: those were working notes of each phase and are not in the repository.
  `docs/DEVELOPING.md` is the durable statement of the rules.
- **The workspace note** `../CLAUDE.md`, outside this repository, has three statements Phase 4 made stale: the tests
  now take about 25 seconds, the build no longer copies conflict copies into `_site/`, and the guides no longer use
  `git add -A`.

## 11. Incident during this phase

On 2026-10-10 the disk fell to about 13 GB free while many scratch copies of the checkout existed. iCloud Drive
then offloaded files in the checkout while they were in use, builds stalled, Git reported its index unreadable, and
a minute later `.git/index` was gone. No command had deleted it. History, branches, objects and the working tree were
intact. The index was rebuilt from the last commit with `git read-tree HEAD` after the working tree had been compared
with that commit through a temporary index: 43 modified files and 123 new ones at that moment, exactly the Phase 4
work, nothing staged, no object missing. The scratch copies were removed. Old iCloud copies of the index (`index 2`
to `index 7`, from September) are still in `.git/` and are the author's to delete.

## 12. Decisions for the author

None of these blocks a commit of Phase 4. Each is listed with what is in place now.

1. **Phone photo sharpness.** On phones, a full-width photo of ordinary landscape shape now loads the 800 px copy
   instead of the 1600 px file. That is where most of the byte and time saving comes from. The cost, measured: on a
   3x phone the lead photo has 0.68 source pixels per device pixel; it is not blurry at viewing size and is clearly
   softer than the full file when magnified. On a 2x phone nothing changed (the 800 px copy was already chosen).
   The viewer still opens the full file. Options: keep it; go back to the full file by changing `core.PHONE_SLOT`
   (lab LCP on a slow phone returns to 4 to 6 s); or add a copy of about 1200 px for every photo, which would give
   a 3x phone one source pixel per device pixel for roughly half the bytes of the full file (new files under
   `content/`, like the card copies).
2. **The 105 new `.th.webp` files** under `content/trips/*/photos/` (2.3 MB) are derivatives made by
   `tools/thumbs.py`. They need to be committed with the phase for cards to use them; without them the pages fall
   back to the 800 px copy.
3. **Font loading.** Keep `display=swap` (today), switch to `optional`, or self-host with a preload (2.5). The
   desktop measurements add one fact to weigh: the stylesheet request to Google Fonts decides when a desktop page
   first paints (2.3). Self-hosting would take that request away; it was not tried, so no figure is claimed for it.
4. **Reports without a photo share a text card.** Keep that, use the site-level image for them, or add a flat route
   map image to the renderer's output for sharing.
5. **`published_at` for existing reports.** Fill them in by hand where the real date is known, or leave them out.
6. **The feed's `pubDate`.** Keep the trip date, or move to `published_at` once reports have it.
7. **`robots.txt` at the project path.** Leave it, or add a root `robots.txt` in a `esichak.github.io` repository
   that points at this sitemap.
8. **Privacy.** The four decisions in `docs/PRIVACY_NOTES.md`: trim or keep starts and finishes, keep or strip
   timestamps, what to do about already-published history, and the Strava ids and coordinates in the repository.
   One more follows from section 9: whether the build should leave a drafted or deleted trip's pin and line out of
   the region maps by itself, so that taking a trip off the site no longer waits for a render. That is new behaviour
   and was not built.
9. **The 100-character floor** for structured data (`core.STRUCTURED_MIN_CHARS`).
10. **Wording.** "via Strava" in the stats note; the section row's order; the open menu button's name; the offline
    search wording; whether the About page should promise a track and a map for every report.
11. **One planned route has no `goal.json`** (the validator's one warning). `python3 tools/ticklist.py update` on it
    writes one.
12. **Time zones on a few trips** look wrong; the list is in the git-ignored author file the privacy notes point to.
13. **PCT Day 146**: its route drawing is nearly blank, which suggests a recording that spans two distant places.
    Seen in a screenshot; the GPX was not examined.
14. **Phase 5.** Decided on 2026-10-10: region pages only, built since (section 14, with its own decisions in 14.7).
    The other ideas (collections, a summit index, reading bookmarks, an interactive map) stay undecided.

## 13. Next smallest step

Review the Phase 4 and Phase 5 commits on `phase1-curated-homepage` (section 14 covers Phase 5). When the branch is
merged to `main` and pushed, look at the live pages on a phone and paste one report's address into a share-preview
tool: those are the two checks no local run could make.

## 14. Phase 5: region pages

Added 2026-10-10. The plan leaves Phase 5 optional and asks for a scope decision first. Asked, the author chose
region pages only. This section keeps the same three kinds of statement apart as the rest of the report.

### 14.1 What was built

A region that has a region map and at least one published report has a page at `regions/<slug>/`. Eight regions do
today: Lake Tahoe (86 reports), Santa Cruz (45), Eastern Sierra (7), Bay Area (5), Boise (5), Alps (4), Tetons (4)
and Oregon (3). The other seven regions the reports name have no region map and keep their list on the Map page.
The build went from 349 to 357 pages.

Nothing is written for a region and nothing was rendered. A page is made of:

- **A head of facts**: the name, a line of counts and the years the reports span, and a line of the places the
  reports name, most reports first. All of it is counted or copied from front matter.
- **The region's map**, the one `render.py` had already drawn, with its legend and the list the Map page shows
  beside it, including "Show all".
- **A Featured row** of up to three cards: reports flagged `featured: true` (the flag the activity pages already
  use), then written reports with a photo, then written reports without one, newest first. Tetons and Oregon have no
  written report and no flag, so they have no row.
- **Every report of the region by year**, with the Map page's activity filter, and the region's planned routes.
- **Links** into the Trips page with the region chosen, and to the other region pages.

The page lists what the content files say: every report and active tick-list goal whose `region:` is exactly the
region's name. Its map shows what it was last drawn with. Report and goal breadcrumbs, the goal pager, the Trips
page's "By region" links, the home page's region names and its `ALSO` row, and a new link under each panel of the
Map page lead to the region page. Every `map/#region-<slug>` address still works.

Two existing components changed with it, each for a measured or reproduced reason:

- The phone source of a card cover declares 106 px for its 112 px slot, so that a 3x phone takes the 320 px copy of
  a portrait or square cover (14.3).
- `base.js` dims a map only when the row pointed at has a line or pin on it, and "Show fewer" keeps its button in
  view. Both also apply to the Map page.

### 14.2 Method

The measurement method is that of 2.1, unchanged, with the same scripts. Builds: the Phase 4 commit; the Phase 5
code before the review fixes; and the Phase 5 code after the second round of fixes. The final build differs from the
last measured one only in the stylesheet (58 bytes gzipped) and the script (146 bytes): every HTML page is
byte-identical. Pages: three region pages (the largest, a middle one and the smallest) and four existing pages
(Home, Trips, the Map page and one report).

### 14.3 Measured results

Phone profile, median of three cold loads. KB is everything transferred except font files.

| Page | LCP ms | CLS | KB | HTML KB (gzip) | Image KB | Requests |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Lake Tahoe (86 reports) | 1592 | 0.000 | 185 | 42 | 76 | 19 |
| Santa Cruz (45 reports) | 1580 | 0.000 | 166 | 52 | 47 | 22 |
| Oregon (3 reports) | 1544 | 0.000 | 89 | 7 | 22 | 13 |

Desktop profile, one cold load each.

| Page | LCP ms | CLS | KB | Requests |
| --- | ---: | ---: | ---: | ---: |
| Lake Tahoe | 420 | 0.000 | 461 | 35 |
| Santa Cruz | 384 | 0.000 | 326 | 39 |
| Oregon | 340 | 0.000 | 115 | 13 |

The four existing pages, Phase 4 commit against Phase 5, phone profile:

| Page | LCP ms Phase 4 | Phase 5 | KB Phase 4 | Phase 5 | CLS (both) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Home | 1744 | 1756 | 344 | 344 | 0.000 |
| Trips | 1496 | 1492 | 229 | 229 | 0.035 |
| Map | 1640 | 1640 | 214 | 215 | 0.041 |
| A report (Back at Tallac) | 1596 | 1596 | 193 | 194 | 0.000 |

What the tables say:

- **The region pages load like the Map page they are cut from.** The largest element is the region map in all
  three, and the three runs of a page differ by at most 20 ms.
- **The existing pages did not change** beyond run-to-run noise: the same requests, the same image bytes, and a
  byte total within 0.5 KB.
- **A measurement changed the card copy.** In the first Phase 5 measurement the Lake Tahoe page transferred 290 KB
  on the phone profile, and 154 KB of that was one card photo drawn 112 px wide: a portrait cover, whose 320 px
  copy a 3x phone passed over for the 600 px one. With the slot declared as 106 px the phone takes the 320 px copy
  (42 KB) and the page is 185 KB. Read from the requests of a 3x phone scrolling the whole Trips page, 25 portrait
  covers and one near-square cover now load the small copy, 78 landscape covers load what they loaded before, and
  the covers together come to 2.22 MB where they were 3.46 MB. At 1x and 2x nothing changes.
- **Lighthouse** (13.4.1, Lake Tahoe and Oregon, mobile and desktop): accessibility, best practices and SEO 100 in
  all four runs, with no failed audit.

### 14.4 Browser checks

Chrome 155, with real key presses and pointer events, in three passes: on the first build, after the second round
of fixes, and on the last fixes.

| Check | Result |
| --- | --- |
| Widths 320, 360, 390, 768, 1024, 1440 | No horizontal scrolling on any region page; no clipped or overlapping text. A place of 60 characters wraps; a single word of 80 characters breaks instead of widening the page. |
| Keyboard | Lake Tahoe at 1440 and 390: every stop visible with a focus ring, none under the sticky header; the activity filter is one stop with arrow keys; the live region reports the count (for example "Showing 13 climbing reports"). |
| Map and list | Every cluster marker on the Lake Tahoe and Santa Cruz maps leads to its report's row (on the first build 10 of 13 on Lake Tahoe did nothing); a click opens the list, scrolls to the row and focuses it, as on the Map page. |
| Target sizes | Each new link answers over at least 44 x 44 px, probed pixel by pixel at 320, 390 and 1440 px, and no hit area lies over another control. |
| Nothing else moved | Every element box equals the Phase 4 build's on Home (seven widths from 320 to 1920 px) and on Trips, the Map page and a report (390 and 1440 px). The exceptions are the two links added on Home, and the new link row under the six Map page panels that have no "Show all" button. |
| JavaScript off | Every report of the region is listed; the links that need the Trips page's script, the filter and "Show all" are not shown. |
| Links into Trips | The explorer opens with the region applied and reports the number the link names (86, and 53 with a write-up, on Lake Tahoe); Back returns to the same scroll position. |
| Console | No error or warning on the eight region pages, Home, Trips and the Map page. |
| Reduced motion, forced colours | Checked with Chrome's emulation only: handled as on the Map page. |

### 14.5 Tests and compatibility

- 2,339 tests in 38 files (2,021 in 36 at the end of Phase 4), on Python 3.9 and 3.12 with `-W error`, also with the
  test modules in reverse and shuffled order. Four Node harnesses, 266 checks; the new one runs `base.js` and
  `archive.js` against a stand-in page.
- Mutants on scratch copies: 355 single-line changes over three rounds, 349 killed and 6 shown equivalent.
- Against the Phase 4 build: no path removed, 8 added; all 351 GPX files, the feed, `robots.txt` and both search
  indexes identical; no title, description, canonical, id or anchor changed; the sitemap gained the eight
  addresses. 169 of the 347 existing pages differ in their HTML, by the links of 14.1 and the `sizes` of the phone
  source of card covers.
- The CI rehearsal of 5.3 was repeated on the 5,204 files this commit holds, taken from the staged index: tests and
  the checked build pass, and the output equals the local build. The CI job itself has not run.

Not run, as in section 4: `tools/render.py`, Safari and Firefox, real phones and screen readers, a real share
preview, field performance.

### 14.6 Known limits

- **The map and the lists can differ until a render.** A report added since the maps were last drawn is on its
  region's page at once and on the page's map after `render.py` has run, as on the Map page. A region gets its page
  only once it has a region map, so a new region waits for a render too.
- **Small regions have small pages.** By the rule as built, every region with a region map has a page: Oregon's is a
  map and three rows.
- **A region written two ways is two regions.** The page lists the trips that spell the region as it does; the
  validator already warns about the pair. After a render with both spellings the check fails with a
  `DUPLICATE IDS` line until one spelling is used, as it did before this phase.
- **Stale maps can still fail the check in states that predate this phase.** When every report of a mapped region
  has been drafted or deleted and the maps have not been drawn again, the Map page drops the region's panel. Phase 5
  stopped the home page's `ALSO` row from linking to it. Two links still do: the page of a tick-list goal that is
  filed under the region and is not on its map, and the home page's own map block when the region is Lake Tahoe or
  Eastern Sierra. The check says so (`BROKEN ANCHOR`), and a render ends it.
- **Small things left as they are.** After "Show fewer" the page moves 11 px more than it needs to when the button
  sits just under the header. A list row without a route drawing starts further left than its neighbours. A map
  that draws only a planned route has a legend with an empty activities list, as on the Map page. On the home page
  "Open the map" answers over 42 of its 44 rows from 1200 px, and on report pages a short region crumb answers over
  41 px of width; both are as they were in Phase 4.

### 14.7 Decisions for the author

1. **Which regions deserve a page.** Every region with a region map has one today. Raising the bar (for example to
   five reports) is a one-line rule in `core.region_pages`; it was not chosen for you.
2. **The Featured row.** It follows a fixed rule from `featured: true`, write-ups and photos. A list per region, as
   `content/home.json` is for the home page, would let you choose and order the cards; it was not built.
3. **An introduction.** A region page has no prose. If you want one, it needs a place in `content/` for your own
   words; none was invented.
4. **A `regions/` index.** There is none; the Map page is the parent of the region pages.
5. **Portrait card photos on 3x phones.** They now come from the 320 px copy, 5% under the 336 device pixels the
   slot has. Side by side at device-pixel level the copy is softer in fine texture; at card size it was not judged
   blurred. `core.CARD_PHONE_SIZES` is the one value to change back.

