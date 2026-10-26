# Personal website improvement plan 2

Date: 2026-10-13. Commit: `1cb9cf2` on `main`, which is what is live at https://esichak.github.io/personal-website/ . Follows `docs/personal-website-improvement-plan.md` (2026-10-08), whose Phases 0 to 5 were published on 2026-10-12; this plan numbers its phases 6 to 15.

**Recommendation:** Run Phases 6, 7 and 8 first, in that order, because they need no decision from Eric and fix the things that cost him or a visitor the most today: an import flag that erases a write-up without a word (`tools/add_trip.py:182-198`), a front-matter parser that keeps `# a note` as part of a title (`tools/lib/frontmatter.py:83`), a search that cannot find `lovers leap`, `skiing` or `june 2024` (`tools/sitegen/search.py:34-62`), a header "Search" that is a link rather than a box (`tools/sitegen/core.py:1650`), a 14-action publish with no rollback recipe, and a checkout in iCloud Drive whose conflict copies and offloaded files have already cost a git index. Then take the content phase (9) and the four page phases (10 to 13) module by module, each one a commit on `main` with its own log entry, with Eric's decisions from section 4 answered before the phase that waits on them. Phase 14 (metadata, fonts, contact) waits for Phase 7 and for three decisions; Phase 15 is one evening on the Mac that redraws every map once, after a golden test and a contact sheet exist, so that one `VERSION` bump carries every renderer change. Nothing here changes the stack, invents a word of copy, or reverses a design rule in `docs/DEVELOPING.md` without saying so and asking first.

## 2. Scope and evidence

The reviewers looked at the live site at https://esichak.github.io/personal-website/ (commit `1cb9cf2`), the site built from that commit in `_site/`, the sources, and the screenshots in `.cache/plan2/shots/` (`desktop-*.jpeg` at 1280 CSS px and `phone-*.jpeg` at 390 CSS px for home, trips, the Matterhorn report, the Haute Route, the PCT series, the Eastern Sierra region, map, tick list, about, the ski section, the Crystal Range goal and the bare ride `back-to-clipless`). They ran Lighthouse on the live home page and on the Matterhorn report for accessibility, best practices and SEO (`.cache/plan2/lh-home/report.json`, `.cache/plan2/lh-report/report.json`): home 96 / 100 / 100 with two accessibility failures (`label-content-name-mismatch` on the five `a.hom-tile` links and `target-size` on `.hom-reg-n a`), the report 100 / 100 / 100. Nobody ran a page-load trace, so performance was not measured today; the last measurements are in `docs/IMPLEMENTATION_REPORT.md` sections 2 and 14.3, and every loading change below is gated on a new measurement by the method in `docs/DEVELOPING.md:1428-1439`. Evidence cited as 'pipeline map', 'design map', 'history map', `brief.md`, `files/pages.md`, `maps/history.md`, `finder-gap9/probe.py`, `runner-ubuntu2404.md`, `deploy-pages-README.md` or a file under `.cache/plan2/` is review scratch, not in the repository; where a repository file holds the same fact, the citation names that file too.

The review ran as a pipeline. Four readers mapped the design rules, the page modules, the authoring pipeline and the history (the 2026-10-08 plan, `docs/IMPLEMENTATION_REPORT.md` sections 10, 12, 14.6, 14.7, 15.4 and 15.5, and the log's "Remaining issues" lists). Finders, one per lens (24 lenses), wrote findings with an observation, its evidence (a `path:line`, a URL or a screenshot name), a proposal, the files it touches, an effort grade (S, M or L) and a confidence. Every finding then went to three skeptics, one asking whether the observation is true today, one whether it is already built, one whether it is worth the change; each left a keep, modify or drop note, and a modify note carries the revised observation or proposal, which is the version printed in section 6. Judges then scored each survivor for visitor value and author value (the register in section 7 shows the averages, from 1 to 4.3) and the planner placed every one of the 265 ids in exactly one phase (210) or in the not-planned list with a reason (55); a coverage script checked that no id is missing or doubled. Of the 265, 212 are rated high confidence and 53 medium; 175 are S, 80 M and 10 L.

The lenses and the id prefix each uses:

| Lens | Id prefix | Findings |
| --- | --- | --- |
| Accessibility and inclusive design | a11y | 15 |
| Authoring | authoring | 18 |
| What the best comparable sites do | benchmark | 7 |
| Copy | copy | 16 |
| Features | features | 13 |
| Tablet widths and touch | gap1 | 8 |
| Storage budget (gap10) | gap10 | 6 |
| Sticky map columns on map/ and region pages against 720-800 px laptop viewports | gap2 | 7 |
| Search vocabulary, dates and partial answers (gap3) | gap3 | 8 |
| From a report to its place: no pin ids, no landing on one trip on a region map, no locator | gap4 | 6 |
| No way to reach Eric or find him elsewhere, and the follow decision beyond RSS | gap5 | 8 |
| First visit on a phone or tablet: units and unexplained words | gap6 | 8 |
| Undo and recovery (gap7) | gap7 | 9 |
| Changing a published trip | gap8 | 9 |
| Renderer tests, fixtures and re-render verification (gap9) | gap9 | 9 |
| Navigation, information architecture and discovery | ia | 17 |
| Maps | maps | 14 |
| Loading performance and resilience | perf | 15 |
| Phone | phone | 14 |
| QA | qa | 8 |
| Report | report | 10 |
| Edge cases, errors and the states nobody tested | resilience | 9 |
| Search engines, sharing and metadata | seo | 15 |
| Visual | visual | 16 |

What was not run, and stays open: no performance trace or Lighthouse performance score; no Safari or Firefox pass; no real phone, no screen reader and no real share preview (all still open from `docs/IMPLEMENTATION_REPORT.md` 15.5, and scheduled here in Phases 11, 13 and 14); `tools/render.py` was never run; only one reviewer drove a browser, and the touch, print and forced-colors checks it names below are listed as checks to do in the phase, not as things measured today.

## 3. What the site does well and must keep

Each item names where the strength is and which phase relies on it. The design rules in `docs/DEVELOPING.md:58-110` stay in force; where a finding reverses one of them, the phase says so and Eric decides first (section 4).

- **The report page already scores 100 / 100 / 100** on accessibility, best practices and SEO in Lighthouse, and the home page 96 / 100 / 100 (`.cache/plan2/lh-report/report.json`, `.cache/plan2/lh-home/report.json`). Phase 13 closes the two home failures; every other phase must leave these scores where they are (gate in each phase).
- **Every trip's GPX is published byte for byte** (`tools/build.py:174-222`, evidence of maps-13) and every report with a track has its own full-screen map page (`tools/sitegen/pages/report.py:683-705`). Phases 11 and 12 build on those pages instead of adding a map runtime.
- **Pages work without JavaScript.** Each page script guards on a body class and returns (`assets/js/pages/archive.js:8`, `assets/js/pages/section.js:5`, evidence of perf-10), the header search form is hidden without scripting (`assets/css/base.css:178`, evidence of ia-02) and the explorer reads `q` from the URL on load (`assets/js/pages/trips.js:12-16`). Phase 7's search box and Phase 11's full-screen map keep the no-script path first.
- **Facts come only from content and write-ups are verbatim** (`docs/DEVELOPING.md:72` onward). The validator already notes every published trip without a `place:`, a write-up or photos (`tools/lib/checks.py:836-838`, evidence of ia-16's review). No phase in this plan writes copy for a page; where a slot for Eric's words is built (Phase 9), it shows nothing until he writes.
- **Datum** (`docs/DEVELOPING.md:58-71`): paper `#F2F1EC`, ink `#16171A`, route red `#D2381A` for the GPX line only, activity colors always with icon and word, radii 0 and 2 px, 44 px targets. Phase 13's visual items remove exceptions to these rules (a hover that borrows route red, three copies of the same chip size) rather than adding tokens.
- **Maps are drawn once on Eric's Mac and committed; CI never renders** (`.github/workflows/pages.yml:2-3`, `:6-9`, `:24`, evidence of gap7-02). The plan keeps that split: Phase 6 makes a render safe to interrupt, Phase 8 stops a push from going out with a stale map, Phase 15 batches every renderer change into one round.
- **The PCT journal is honest about its gaps**: track-only days read `TRACK ONLY` in the rows and month index (`tools/sitegen/pages/series.py:35-48`, evidence of copy-04) and missing days read `DAYS N · NO RECORDING` (`tools/sitegen/pages/series.py:447-449`, evidence of features-07). Phase 10's `Track only` tag and Phase 11's running distance extend these idioms rather than inventing new ones.
- **The goal page already handles a map that is not rendered** with an `.empty` box (`tools/sitegen/pages/report.py:394-409`, evidence of resilience-12); Phase 6 gives reports the same state.
- **The home page's one-line map key** (`tools/sitegen/pages/home.py:306-340`, evidence of gap2-06) and the cluster-click handler that opens a folded list and scrolls to a row (`assets/js/base.js:188-203`, evidence of gap4-02) are the components Phase 12 reuses for region pages and for landing on a trip.
- **Photos are WebP at three sizes with EXIF stripped** (brief, site facts) and every cover has a focal point (`tools/lib/content.py:278-287`, read at `tools/sitegen/core.py:811-822`, evidence of seo-04). Phase 14 adds no new derivative unless a real share preview shows a defect.
- **Standard-library Python, 2,476 tests plus the Node harnesses, Python 3.9 locally and 3.12 in CI** (brief; `.github/workflows/pages.yml:27`). Every phase gate below runs the suite on both interpreters with `-W error`.
- **`docs/PRIVACY_NOTES.md` is the public statement** and the full-screen map pages carry `noindex` (`tools/sitegen/core.py:46-51`, evidence of seo-08). Nothing in this plan publishes a new personal fact except, if Eric chooses it, a contact alias (section 4, decision 17).
- **The built-site check already strips `?` and `#` from hrefs** (`tools/sitegen/sitecheck.py:263-267`, evidence of perf-01) and `<title>` already appends the date when a title repeats (`tools/sitegen/pages/report.py:649-650`, evidence of a11y-13); Phases 13 and 14 build on both.

## 4. Decisions for Eric

Thirty decisions, each with the options, the trade-off, a recommendation and the phase that waits on it. A phase whose decision is unanswered uses the recommendation only where the decision says so; otherwise its item waits. Nothing is built from a guess about Eric's own words, names or addresses.

**Decision 1. Where the checkout lives (authoring-16, gap10-05)**

- Options: (A) Move the clone out of iCloud Drive, e.g. ~/Code/personal-website, GitHub being the backup of everything tracked; (B) stay in ~/Documents, mark the folder Keep Downloaded, run tidy.py before each commit.
- Recommendation: A. It ends the index incident class, the 29-minute builds and the 6,100 conflict copies; three documents change their path. Run git gc only after the move.
- Waits on it: Phase 8 (the doc edits; nothing waits)

**Decision 2. Taking a trip off the site without a render (12.8, gap7-03)**

- Options: (A) The build drops a drafted or deleted trip's own pin and line from the region maps itself, leaving merged pins to the next render; (B) keep needing render.py on the Mac with the internet.
- Recommendation: A: pins and lines only, no cluster rewriting; a draft: true push from a phone then works.
- Waits on it: Phase 8 (gap7-03)

**Decision 3. Trips browse block (visual-02 or ia-05)**

- Options: (A) Hide the duplicate browse nav when scripting is on (one scoped CSS rule); (B) reorder search above it and trim By region to the 8 mapped regions plus 'N more'.
- Recommendation: A; its region trim can ride along if you prefer the links visible.
- Waits on it: Phase 7

**Decision 4. Activity search words and small explorer defaults (gap3-01, visual-05)**

- Options: Accept the proposed inflection lists (ski/mtb/hike/climb/SUP/Rafting) or edit them; tick-list form from 6 goals counting active goals only, or another threshold.
- Recommendation: Accept the lists with 'sup' included; threshold 6, active goals only.
- Waits on it: Phase 7 (defaults are used if you say nothing)

**Decision 5. Region and place merges (copy-16)**

- Options: Merge Idaho into Boise and Kingsbury Grade into Kingsbury (or the reverse); keep Yosemite separate from Eastern Sierra; or leave all as they are.
- Recommendation: Merge the two pairs, keeping the spelling that has a region page (boise) and whichever Kingsbury you use; the render follows in Phase 15.
- Waits on it: Phase 9 (the merge step) and Phase 15 (its site render)

**Decision 6. Retitling the 24 Strava default titles (copy-05)**

- Options: Retitle by hand from the content report, or keep them (a Strava name is a true title).
- Recommendation: Retitle; a title change then costs one trip render, not 76 site files, after gap8-04.
- Waits on it: Nothing waits on it. Phase 9's `content_report.py` lists the 24 titles; the retitling itself is Eric's hand work, and after gap8-04 a retitle costs one trip render.

**Decision 7. Publication dates (seo-10; 12.5, 12.6)**

- Options: (A) add_trip writes an empty published_at you fill on the day you push; feed pubDate and sitemap lastmod use it when set; old reports stay dateless; (B) add_trip writes today's date at import; (C) leave everything on the trip date.
- Recommendation: A: no invented date, and the feed stops presenting a write-up finished weeks later as old news.
- Waits on it: Phase 9 (seo-10)

**Decision 8. Summits (features-05)**

- Options: Publish typed summit claims with a fixed outcome vocabulary (summit, turned-around, traverse) as a Beta-rail row and search words, with an A-Z page later once names are settled; or not at all.
- Recommendation: Yes to step 1; the page waits for a few dozen typed names.
- Waits on it: Phase 9 (features-05)

**Decision 9. Your own words on About and region pages, a portrait, and the home region maps (visual-16, features-17, ia-15)**

- Options: The slots are built dormant; the decisions are whether to write an About body, which region introductions, and whether a portrait goes on a public site (PRIVACY_NOTES level). Also which two regions the home page maps (ia-15, Phase 9 item 18): keep Lake Tahoe and Eastern Sierra, or name another pair in content/home.json.
- Recommendation: Build the slots; write About first; a portrait only if you want one, as a separate step. Keep Lake Tahoe and Eastern Sierra on home (the Eastern Sierra map now carries the PCT days).
- Waits on it: Nothing waits on it. Phase 9 builds the About body, portrait and region-intro slots dormant; they show nothing until Eric writes. ia-15 uses the recommended pair if he says nothing.

**Decision 10. Report layouts (report-01, report-02, report-11)**

- Options: Words above the map on written reports without photos (over 100 characters); the lead photo on photo-only reports; a lead photo and day strip on multi-day pages. Each yes or no.
- Recommendation: Yes to all three; they reverse plan 9.1 only where its reason (not manufacturing content) does not apply.
- Waits on it: Phase 10

**Decision 11. Lead-photo frame on desktop (report-03)**

- Options: (a) cap the 1200+ frame at 3:2 (one CSS line); (b) the photo's own shape clamped to 72vh; (c) today's 2:1 band. Chosen from a side-by-side at 1280 px.
- Recommendation: (a) unless the preview changes your mind.
- Waits on it: Phase 10 (report-03)

**Decision 12. Two documented reversals: 'Track only' tag and a factual 'More like this' head (copy-04, visual-03)**

- Options: Show a 'Track only' status tag on the 39 bare trips instead of CONTENT_GUIDE:164's blank slot; replace the selection-rule line with e.g. 'EASTERN SIERRA · BACKCOUNTRY SKI'. Each yes or no.
- Recommendation: Yes to both.
- Waits on it: Phase 10

**Decision 13. Times of day on report pages (report-04, report-05; PRIVACY_NOTES 6.2)**

- Options: (A) Elapsed time only; (B) elapsed plus a clock column in the mile table and the GPS-max time, all read from the published GPX; (C) also a derived finish time (start + elapsed).
- Recommendation: B now; C only once you have settled 6.2 (keep or drop timestamps).
- Waits on it: Phase 10 (scope of report-04 and report-05)

**Decision 14. Units on phones (gap6-02 or gap6-01) and the km default (gap6-03)**

- Options: Units row moved to the top of the phone menu (keeps plan 8.1) or the MI|KM control beside the menu button at every width (reverses 8.1); and whether a browser whose language does not start with 'en' starts in kilometers.
- Recommendation: gap6-02 and yes to the km default; revisit the header switch only if the menu row proves hard to find.
- Waits on it: Phase 13

**Decision 15. Site words (copy-11, copy-14, ia-13; 12.10)**

- Options: 'Backcountry Ski' to 'Backcountry Skiing' (or 'Ski touring', or keep); 'PCT' with an aria-label 'PCT journal' or a visible 'PCT journal'; crumb root 'Reports' to home kept or retargeted to Trips; open menu button 'Menu' or 'Close menu'.
- Recommendation: 'Backcountry Skiing'; 'PCT' with the aria-label; keep the crumb root; keep 'Menu' (aria-expanded already announces the state).
- Waits on it: Phase 13 (the copy session)

**Decision 16. Self-hosting the fonts (perf-02; 12.3)**

- Options: Self-host the four Latin woff2 files under assets/fonts/ with display: swap and two preloads, measured before and after; later consider font-display: optional on the Tick list; or keep Google Fonts.
- Recommendation: Self-host with swap now; 'optional' only if a measurement asks.
- Waits on it: Phase 14 (perf-02)

**Decision 17. Contact and follow (gap5-01, gap5-08, gap5-03, gap5-05, gap5-07, gap5-02)**

- Options: (A) A dedicated public alias as a plain mailto on About and the footer, 'Ask about this trip' on every report, profile links only for services you name, one sentence pointing at RSS-to-email services, 'Source on GitHub' in the footer; (B) an obfuscated address; (C) a hosted contact form or newsletter provider (the site's first third-party endpoint); (D) none. The address stays in git history for good.
- Recommendation: A, with an alias you are willing to keep public; no provider until you name one.
- Waits on it: Phase 14 (every contact item)

**Decision 18. Per-trip 'View on Strava' links (gap5-04; 12.8)**

- Options: Link each report to its Strava activity from the stored strava_id (ties a timed track to the activity page; a dead link is undetectable by the build) or not.
- Recommendation: Not now.
- Waits on it: Nothing waits on it; gap5-04 is not planned and is built only on a yes.

**Decision 19. Search Console and the sitemap (seo-12, seo-11)**

- Options: Set up a verified property (your Google account), submit sitemap.xml and import into Bing; optionally make the esichak.github.io user-site repository for a root robots.txt.
- Recommendation: Set it up; skip the second repository.
- Waits on it: Phase 14 (the account steps)

**Decision 20. Share image for the 62 photo-less reports (seo-04, seo-05; 12.4)**

- Options: Keep the text card; use the site image; render JPEG crops of covers or a route image. A real share preview is pasted first.
- Recommendation: Keep the text card; build the 1200×630 crops only if the preview check shows WebP or a portrait cover failing.
- Waits on it: Phase 14 (seo-04 step 2 only)

**Decision 21. Hillshade quality (perf-05)**

- Options: q88 (today), q80 or q75, judged from a side-by-side at 1x and 2x; a change re-encodes 595 rasters in the round (about 12 MB of history).
- Recommendation: q80 if it passes; decide only from the preview.
- Waits on it: Phase 15

**Decision 22. When to run the renderer round (maps-16, gap10-03)**

- Options: One evening after Phases 10-14 land, with warm caches and --jobs 2, then once a year; or sooner for a subset (--force per slug).
- Recommendation: After Phases 10-14, as Phase 15; one forced round a year.
- Waits on it: Phase 15

**Decision 23. 1200 px photo copy for 3x phones (phone-14; 12.1)**

- Options: Add a 1200 px copy for lead photos (about 15-18 MB of derivatives) or all 398 (50-70 MB), or keep the 800 px copy.
- Recommendation: Not now; measure on a real 3x phone after the real-device pass before adding bytes to an iCloud checkout.
- Waits on it: Nothing waits on it; phone-14 is not planned.

**Decision 24. Zoomable topo on the full-screen map page (maps-13)**

- Options: A self-hosted Leaflet with USGS tiles on single-day full-screen pages (the site's first vendored runtime and a street-level view of each track's start), or none.
- Recommendation: Not now; take the static map improvements first and revisit after Phase 15.
- Waits on it: Nothing waits on it; maps-13 is not planned.

**Decision 25. Dark mode, custom domain, service worker (features-14, seo-16, perf-11)**

- Options: Each is a separate decision the plan may propose: a dark token set with light map insets; a bought domain with DNS and a redirect to confirm; a cache-first worker for offline reading.
- Recommendation: None of the three now: maps stay light islands, the domain costs a yearly renewal and a rankings re-settle for short URLs, and a wrong cache pins stale pages with nothing in CI to test it.
- Waits on it: Nothing waits on it; features-14, seo-16 and perf-11 are not planned.

**Decision 26. Companions' names in search and PCT chapters, named lists (features-10, features-06, benchmark-14)**

- Options: Make the 13 party names searchable (PRIVACY_NOTES 6.5); name PCT chapters and their day ranges; write a first objectives list with done/planned/not-yet.
- Recommendation: No to searchable names; chapters and lists only when you have names to type, in a later session.
- Waits on it: Nothing waits on it; features-10 is not planned, and features-06 and benchmark-14 wait for names from Eric.

**Decision 27. Layout choices after previews (gap1-01, gap2-05, qa-04, visual-18)**

- Options: Raise the 1000-1199 report map column to 1005 px; release the journal's month bar under 480 px of height with the one sticky rule; dim the ski map to the chosen season; stack the home tablet maps.
- Recommendation: Take the 1005 cap if the 1024/1180 preview reads well; yes to the month-bar release; yes to the dim if it reads as filtered; leave the tablet home maps.
- Waits on it: Phase 12 and Phase 13 (those items only)

**Decision 28. Author-tool defaults (gap8-02, gap8-07, features-01)**

- Options: --update replaces stats you corrected by hand unless --keep-stats; which trips to --retime (your private list); calendar years or ski seasons for the By-year block.
- Recommendation: Replace with --keep-stats; retime from your list; calendar years with the ski row linking the explorer.
- Waits on it: Phase 6 (gap8-07) and Phase 9 (gap8-02, features-01) use the recommended defaults if he says nothing.

**Decision 29. 'See on the map' as a fourth title action (gap4-03)**

- Options: (A) Keep the 'See on the <Region> map' link in the report's Route section and the goal pager only; (B) add it as a fourth title action at 1000 px and up as well.
- Recommendation: A (no fourth action): the Route section and the pager are enough, and the title row stays at three actions.
- Waits on it: Phase 12 (gap4-03 only) uses the recommendation if he says nothing.

**Decision 30. Full-screen pages for the region maps (qa-06)**

- Options: (A) Give each of the eight region maps a full-screen page like the report map pages, reached from the phone panel (qa-06's proposal); (B) leave the region maps inline only.
- Recommendation: A (yes): the phone render's clusters overlap (qa-06's evidence) and the page type already exists for reports.
- Waits on it: Phase 12 (qa-06 only) uses the recommendation if he says nothing.

## 5. The roadmap

Ten phases, numbered after the 2026-10-08 plan's 0 to 5. Each is a reviewable change of one to a few Claude Code sessions, grouped by the modules it touches so that a session reads one area and its tests. Bug fixes and quick wins come first; the page phases follow by module; the renderer round is last so that one `VERSION` bump carries every change. Effort is the count of items by grade (S, M, L) from the register.

| Phase | Title | Goal | Effort | Prerequisites |
| --- | --- | --- | --- | --- |
| 6 | Author tools: safe imports, instant preview, stale-map warnings | Fix the author-tool traps (--force, two parser traps, stale maps, half-written render folders, the copying preview) and give the import tools their first tests. | 16 items: 15 S, 1 M, 0 L | None. gap9-06's cache move is a one-time step Eric runs when the disk has room. |
| 7 | Search and the explorer: vocabulary, matching, filters, cards and forms | A search that finds what a route or peak searcher types, a search box on every page and the 404, a way out of zero results, and the explorer's month facet, sorts, photo filter, cards and phone forms. | 24 items: 17 S, 7 M, 0 L | None. Eric reads gap3-01's word list and picks visual-02 or ia-05 (recommended visual-02). |
| 8 | Publishing loop, CI and recovery | One publish command with a linked check, stage by path, rollback and recovery recipes, a clean checkout, a one-minute content deploy, Node pinned in CI, and a draft: true push that takes a trip off the site. | 23 items: 18 S, 5 M, 0 L | Phase 6 (publish.py refuses a slug that `render.py --status` names). Decisions: where the checkout lives; 12.8 for gap7-03. |
| 9 | Content: inventory, editing a published trip, and places for Eric's words | A per-trip inventory of what each report lacks, tools to change a published trip (track, photos, titles, time zone, dates), and dormant slots for Eric's own words (About body and portrait, region introductions, summits, year totals, home region maps). | 18 items: 9 S, 9 M, 0 L | Phase 6 (the add_trip tests, the frontmatter fix, --retime). Decisions: region and place merges, the 24 Strava titles, published_at, the summits vocabulary, --update's stats default. An afternoon from Eric for 79 `place:` lines. |
| 10 | Report and multi-day pages: layout, facts, captions and the profile readout | Report and multi-day pages: lead photo or words where a reader lands, a day strip on multi-day pages, elapsed and clock times, contour interval and key rows that decode OSM trails, one label per section, the Track only tag, a factual More-like-this head, and the profile readout. | 20 items: 16 S, 4 M, 0 L | None hard. Decisions: the three layouts, the hero frame after a preview, the two reversals, times of day. maps-01 part 3 waits for Phase 15. |
| 11 | The PCT journal, the photo viewer and the full-screen map | PCT journal photos shown as photos, place in the hike and a local Continue-reading bookmark, July and August tabs that answer, a photo viewer that behaves on phones, the share sheet, and a full-screen map that opens on the route with scale and disclaimer in view. | 13 items: 10 S, 3 M, 0 L | Phase 10 (core.photo_rows and the label table). No decision from Eric; the session picks report-18's sizes cap from the measurement. |
| 12 | Maps on pages: landing on a trip, legends, touch, sticky columns | Maps on pages: a report links to its own row on the region map, the PCT to the maps that draw its days, cluster taps and legend toggles answer, touch gets select-then-open, the phone list folds, phone region maps get a full-screen page, and every sticky part fits common laptop and landscape-phone windows under one rule. | 24 items: 16 S, 8 M, 0 L | None hard (gap4-04 can land before Phase 11). Previews for gap1-01, qa-04 and gap2-01; decisions on a fourth title action (recommended no) and full-screen region pages (recommended yes). |
| 13 | Phone, tablet, accessibility and copy polish | Three sessions of small CSS, markup and wording fixes: header, menu and units; legibility and touch; accessibility and copy; ending with the tablet capture profile and Eric's first VoiceOver pass. | 33 items: 30 S, 3 M, 0 L | Decisions on the units switch (gap6-02 or gap6-01), the km default, and the site words (copy-11, copy-14, ia-13). visual-01 step 2 waits for Phase 15. |
| 14 | Loading, metadata, sharing, follow and contact | Honest titles and whole descriptions on every trip page, og:site_name and breadcrumbs, versioned asset URLs, self-hosted fonts if Eric agrees, two measured image fixes, a Follow section and a contact path, Search Console and the first real share preview. | 21 items: 16 S, 5 M, 0 L | Phase 7 (markdown.plain_sentences). Decisions: fonts, the contact alias, profile links, the share image, Search Console. |
| 15 | Renderer round and storage budget | Build the safety net (golden and contract tests, contact sheet, resumable budgeted run, renderer version in meta.json, bounded tile cache), re-render every map in one evening with one VERSION bump, commit rendered/ by path, and write the storage budget and the yearly checklist. | 18 items: 7 S, 11 M, 0 L | Phases 6 and 8, and the page phases landed so that one round carries everything (maps-01 part 3, visual-01 step 2, copy-16's merges). Decisions: hillshade quality from a preview; the evening for the run. |

Ten phases, numbered 6 to 15 after the 2026-10-08 plan's 0 to 5, each a reviewable change of one to a few sessions, grouped by the modules they touch so a session reads one area and its tests. Order: bug fixes and quick wins first. Phase 6 fixes the traps in the tools Eric runs every week (a --force that erases a write-up, two parser traps that mangle front matter, maps drawn from old inputs with no warning, half-written render folders, a 240 MB copying preview) and gives add_trip.py its first tests; Phase 7 is the biggest visitor win that needs no decision: a search that finds 'lovers leap', 'skiing', 'june 2024' and 'loop', a search box on every page, a way out of zero results, and the explorer's facets, sorts, cards and phone forms; Phase 8 replaces the 14-action publish with one command, writes the rollback and recovery recipes that have never existed, cleans the checkout and makes a content push live in about a minute. Phase 9 then depends on Phase 6 for the content work: the per-trip inventory, editing a published trip, and the dormant slots for Eric's own words. The page phases follow by module: Phase 10 report.py and multiday.py (layouts, facts, captions, profile readout), Phase 11 series.py and the base.js viewer plus the full-screen map, Phase 12 archive.py, region.py and the sticky-column CSS (landing on a trip, legends, touch, laptop windows), Phase 13 the cross-site CSS, accessibility and copy sweep in three sessions ending with the VoiceOver pass that closes 15.5. Phase 14 (metadata, share, fonts, follow and contact) comes late because seo-02 reuses Phase 7's sentence cut and most of its items wait on Eric's decisions (fonts, alias, Search Console). Phase 15 is last so one VERSION bump carries every renderer change, with the golden and contract tests, the contact sheet, the resumable run and the renderer version in meta.json built before the evening the maps are redrawn, and the storage budget written from the measured cost of that round. The optional large items (interactive map, dark mode, custom domain, service worker, PCT day pages) are decisions with a recommendation and are prerequisites of nothing. Duplicates and alternatives are resolved rather than planned twice: ia-16 part 2 is resilience-03, features-15 is visual-16, benchmark-08 is features-01, ia-14 is visual-05, maps-11 is visual-01, copy-08 folds into copy-07, gap8-06 is superseded by authoring-08, ia-05 and gap6-01 are the alternatives Eric picks against visual-02 and gap6-02.

## 6. The phases

Each phase below lists its goal, the decisions it waits on, every finding in it (id, the observation with its evidence, the proposal, the files, the effort and the review note that changed it), the gates, the tests to add, the screenshots to capture and the author inputs. The observation and proposal printed are the versions after the skeptics' revisions; where a skeptic changed the text, the review note says what was corrected. Where a finding's printed proposal or Files line and the prompt pack (`claude-code-website-prompt-2.md`) differ, the prompt pack is the scope a session builds; the plan keeps the finding's evidence and reasoning.

### Phase 6. Author tools: safe imports, instant preview, stale-map warnings

**Goal.** Fix the traps in Eric's own tools (a --force that erases a write-up, two front-matter parser traps, maps drawn from old inputs, half-written render folders, a 240 MB copying preview) and make every weekly step a few seconds, all inside tools/ with the import tools' first tests.

**Prerequisites.** None. For gap9-06 Eric runs the one-time move of .cache/tiles and .cache/osm to ~/Library/Caches (about 1.3 GB downloads from iCloud) when the disk has room; the code change does not wait on it.

**Decisions this phase waits on.**

- Which trips to --retime is Eric's private list (IMPLEMENTATION_REPORT 12.12); the tool ships regardless.

**Findings in this phase** (16, in working order): authoring-08, gap8-01, authoring-10, perf-12, gap8-05, authoring-09, authoring-13, authoring-06, authoring-07, gap8-08, gap8-07, gap9-03, gap9-06, gap7-09, resilience-12, authoring-15.

#### authoring-08. Fix the two front-matter traps instead of warning about them

**Observation.** Reproduced today with tools/lib/frontmatter.loads: `title: Rose Knob  # a note` loads the title as 'Rose Knob  # a note' (comments are skipped only when a line starts with #, frontmatter.py:83); a `beta:` block indented with tabs loads as {'beta': [{'label': 'Trailhead'}], 'value': 'Twin Lakes'} because indentation is measured with lstrip(' ') (frontmatter.py:85), so a tab counts as column 0 and the second key escapes to the top level. The validator catches neither (report 10.6); ADDING-TRIPS.md:163 warns instead.

**Evidence.** `tools/lib/frontmatter.py:83`; `tools/lib/frontmatter.py:85`; `ADDING-TRIPS.md:163`; `docs/IMPLEMENTATION_REPORT.md:463-464`; `tools/lib/checks.py:53-61`.

**Proposal.** frontmatter.loads: (1) on a `key: value` line strip a comment that starts with ` #` outside quotes and outside [brackets] (YAML's rule: # preceded by whitespace), leaving `#` inside quoted strings and in values with no space before it; (2) raise ValueError('line N is indented with a tab; use spaces') on any leading tab, which content.load_trip already surfaces as an ERROR naming the file. Tests in tests/test_frontmatter.py for both, plus `#` inside quotes and in inline lists, and a round-trip with dumps (which already quotes strings containing #, frontmatter.py:136). Add the two lines to the error table in docs/CONTENT_GUIDE.md 5.2 and delete the warning sentence at ADDING-TRIPS.md:163.

**Files.** `tools/lib/frontmatter.py`, `tests/test_frontmatter.py`, `docs/CONTENT_GUIDE.md`, `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1, author value 3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 10 ('A # note after a value')

**Risk.** A literal `#` in an unquoted value preceded by a space would change meaning; run the validator over content/ after the change (today 0 errors, 1 warning) to confirm no trip has one.

**Review note.** Kept as written by all three skeptics.

#### gap8-01. Refuse --force on a trip that has a write-up or descriptions

**Observation.** tools/add_trip.py refuses an existing folder only without --force (:182-183). With --force it rewrites track.gpx and index.md from scratch: the front matter is built at :186-194 from the track and the flags, the body is '' or the Strava description (:155) with the placeholder comment at :195-196, and photos are numbered from 01 (:193; add_photos :63-80, start=1), so photos/01.webp onwards are overwritten. The existing index.md is never read, so a re-import of a published trip silently drops the write-up, every alt line, beta rows, map: peaks, cover_photo and focal point, card_summary, featured, search_aliases and published_at. The option's help says only 'overwrite an existing trip folder' (:126); ADDING-TRIPS.md never mentions add_trip's --force (its only --force is render.py's, :44), and the validator cannot catch the loss afterwards because a bare trip is valid (76 of 168 trips have no write-up today by content.load_all's has_writeup: 74 of the 156 single-day reports plus one multi-day trip and the planned goal).

**Evidence.** `tools/add_trip.py:126`; `tools/add_trip.py:155`; `tools/add_trip.py:182-198`; `tools/add_trip.py:63-80`; `ADDING-TRIPS.md:44`; `tools/lib/checks.py:811-848`.

**Proposal.** Before writing, when <folder>/index.md exists, split it with frontmatter.split and refuse (exit 1, nothing written) when the body is non-empty and not the placeholder comment, when any photo entry has a non-empty alt, or when any of beta, map, cover_photo, cover_focal_x, cover_focal_y, card_summary, featured, search_aliases, published_at, updated_at, region_days is present; also refuse when days/ exists. Message: 'content/trips/<slug>/index.md has a write-up and N photo descriptions; --force would erase them. Move the folder out of content/trips/ first (git keeps the old one: git checkout -- content/trips/<slug> restores it).' If gap8-02 is built, add 'or use --update <slug>' to the message. Keep --force only for a folder with no index.md or whose index.md is still the untouched import (placeholder body, empty alts), and print the files it will overwrite. Tests in a new tests/test_add_trip.py: a written-up trip from helpers.make_trip in a temp folder, add_trip.TRIPS patched, main() run with --force and a GPX string from tests/gpx_fixtures.py; assert exit 1, the message, and index.md unchanged byte for byte; a second case where the untouched import is overwritten. Document the rule in ADDING-TRIPS.md under 'If something goes wrong'.

**Files.** `tools/add_trip.py`, `tests/test_add_trip.py`, `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1, author value 3.7, confidence high.

**Risk.** None to the site. A re-import Eric truly wants now needs --update or a moved folder, which is the point.

**Review note (condensed; the observation and proposal above are the revised text).** Observation verified: tools/add_trip.py:182-183 refuses an existing folder only without --force, :184-198 then writes track.gpx and index.md from scratch without reading the old file, add_photos starts at 01 (:63-80, :193), the help says only 'overwrite an existing trip folder' (:126), and ADDING-TRIPS.md's only --force is render.py's (:44). Cheap (S is honest) and feasible with frontmatter.split alone. Reproduced: tools/add_trip.py:126 help is 'overwrite an existing trip folder'; :182-183 refuse only without --force; :184-198 rebuild track.gpx and index.md from the track and flags with body '' or the Strava description (:155) and the placeholder (:195-196); add_photos (:63-80) numbers from start=1 so photos/01.* onward are overwritten; the existing index.md is never opened.

#### authoring-10. Preview by symlink, open the new page, no traceback on Ctrl+C

**Observation.** build.py --serve copies about 240 MB of photos, GPX files and renders into _site/ on every preview (LINK is set only by --link, build.py:398; copy at :301-305); with iCloud offloading half of rendered/ that is the stall the docs describe (report 2.8: minutes; log:21-23: 29 min 54 s once), while a --link build measured 2.84 s today. The author then types the trip's URL by hand, and the guide says the traceback after Ctrl+C 'is normal' (ADDING-TRIPS.md:174-175); main() has no KeyboardInterrupt handling (build.py:409-414).

**Evidence.** `tools/build.py:398`; `tools/build.py:409-414`; `ADDING-TRIPS.md:170-175`; `docs/IMPLEMENTATION_REPORT.md:216-221`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:21-23`.

**Proposal.** build.py: --serve implies --link (add --copy to opt out), accepts --open [SLUG] which runs macOS `open` on http://localhost:<port>/ or /trips/<slug>/ once the server is up, and catches KeyboardInterrupt around serve_forever() to exit quietly. add_trip.py's 'next:' line prints `python3 tools/build.py --serve --open <slug>`. Update README.md:35 and ADDING-TRIPS.md step 4. Test: --serve with --copy still copies; the symlinked build is never used by CI (pages.yml runs plain --check).

**Files.** `tools/build.py`, `tools/add_trip.py`, `README.md`, `ADDING-TRIPS.md`, `tests/test_build_cli.py`.

**Effort.** S. Visitor value 1, author value 3.7, confidence high.

**Risk.** http.server follows symlinks, so a symlinked build serves correctly; a symlinked _site/ must never be uploaded (CI builds its own).

**Review note.** Kept as written by all three skeptics.

#### perf-12. Rebuild on change while serving the preview

**Observation.** `build.py --serve` builds once and then serves `_site/` with `http.server` (build.py:409-414); every edit to a write-up, a stylesheet or a page module means Ctrl+C, re-run, reload. A linked build takes 1.9 s and the whole command 2.8 s (measured today with `--out <scratch> --link --check`), so the edit loop is dominated by the restart, not the build.

**Evidence.** `tools/build.py:409-414`; `pipeline map section 3.4 (built 357 pages, 168 trips in 1.9s; 2.84 s wall)`; `ADDING-TRIPS.md:170-184`.

**Proposal.** Add `--watch` to tools/build.py for use with `--serve`: a daemon thread polls every second (stdlib os.stat) the mtimes of files under content/ (for each photos/ folder, its own mtime rather than its files), assets/, tools/sitegen/, tools/lib/ and rendered/site/, skipping conflict_copy() names (build.py:72), and re-runs build() when something changed, printing one line per rebuild; when the content validator raises, print the ERROR lines as main() does at build.py:402-405 and keep serving. Turn `--link` on under `--watch`. State in the code and in ADDING-TRIPS.md's preview step (lines 170-175) that build() empties the output folder first (build.py:272-274), so a reload during the two-second rebuild can show a 404 and a second reload fixes it. Effort S.

**Files.** `tools/build.py`, `ADDING-TRIPS.md`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1, author value 3.3, confidence high.

**Risk.** Polling thousands of files under `rendered/` would touch iCloud-offloaded files; scope the watch to `rendered/site/` and the folders named, and skip conflict copies with the existing `conflict_copy` rule.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible in the stdlib and 3.9 (a daemon thread with os.stat), S is honest, and the observation is right: tools/build.py:409-414 serves OUT with http.server after one build, and ADDING-TRIPS.md:170-175 tells the author to Ctrl+C and rerun.

#### gap8-05. Validator warns when a trip's maps are older than its inputs

**Observation.** tools/lib/checks.py:831-835 warns only when rendered/trips/<slug>/meta.json is missing. Nothing compares the hash stored there (tools/render.py:455-458) with the current inputs: checks.py never mentions a hash, and the only hashing in sitegen/sitecheck.py (:31, :626) checks that a published GPX copy equals its source, not that a render is current. So after a hand or github.com change of map: peaks, stats, activity, kind or the track, the build passes and publishes maps drawn from the old inputs, and ADDING-TRIPS.md:318-319 relies on Eric remembering to run render.py. A render that lost its OpenStreetMap data sets hash to null (render.py:475-477) and is equally invisible to the build.

**Evidence.** `tools/lib/checks.py:831-835`; `tools/render.py:430-434`; `tools/render.py:455-458`; `tools/render.py:475-477`; `ADDING-TRIPS.md:318-319`; `tools/sitegen/sitecheck.py:31`.

**Proposal.** Move VERSION, file_hash and trip_inputs out of tools/render.py into a new tools/lib/renderkey.py (no mapkit import; render.py imports it) and, in checks._trip_findings, when meta.json exists and its hash differs from renderkey.trip_inputs(t), warn 'maps were drawn from other inputs (the track, activity, kind, map: or stats changed since): run python3 tools/render.py <slug>'; when the hash is null warn 'maps were drawn without OpenStreetMap data; run python3 tools/render.py <slug> again'. Optionally one line for the site maps when rendered/site/meta.json's hash differs from the current site hash (that expression needs journal_parts, render.py:543, so move it too or leave the site line for a later step). Add both lines to docs/CONTENT_GUIDE.md section 5 and tests in tests/test_checks_site_maps.py with a fixture meta.json carrying a wrong hash and a null hash. Once gap8-04 is in, a title change no longer trips the warning, which is the intended split.

**Files.** `tools/lib/renderkey.py`, `tools/render.py`, `tools/lib/checks.py`, `tests/test_checks_site_maps.py`, `docs/CONTENT_GUIDE.md`.

**Effort.** S. Visitor value 1.7, author value 3.3, confidence high.

**Already known.** ADDING-TRIPS.md:318-319 states the manual rule; docs/IMPLEMENTATION_REPORT.md section 10.2 covers the related case of a deleted trip.

**Risk.** file_hash reads every GPX on each validate run (341 files, 30 MB); measure, and cache per run if it shows.

**Review note (condensed; the observation and proposal above are the revised text).** Substance reproduced: checks.py:831-835 warns only when rendered/trips/<slug>/meta.json is missing; render.py:455-458 compares the stored hash only inside render_trip and :475-477 nulls it after an OSM failure; nothing in checks.py mentions a hash (grep: no match).

#### authoring-09. render.py --status: what a render would do, offline

**Observation.** render.py with no arguments draws everything whose input hash changed (render.py:1-11, :457) and nothing lists that set without the internet. An OSM failure sets meta['hash'] = None so the next run retries silently (render.py:475-476; the same for the site maps at :694-695); drafts are never rendered and naming a draft slug says nothing (render.py:711); add_trip.py starts the render with check=False and prints 'next: edit …' whether or not maps were drawn (add_trip.py:201-203); the validator only notices a missing meta.json (checks.py:834). Today no render is marked osm_failed, but the author has no way to know that.

**Evidence.** `tools/render.py:455-458`; `tools/render.py:475-477`; `tools/render.py:641-645`; `tools/render.py:694-695`; `tools/render.py:711`; `tools/add_trip.py:201-203`; `tools/lib/checks.py:834`.

**Proposal.** (1) tools/lib/checks.py: the existing `no rendered map` warning (checks.py:834-836) also fires when rendered/trips/<slug>/meta.json exists but its 'hash' is null or 'osm_failed' is true, with the text 'rendered without OpenStreetMap data; run python3 tools/render.py <slug>' (reads the JSON only; no import of render.py). The same for rendered/site/meta.json as one warning. Test in tests/test_checks.py. (2) Extract pending_trips(trips, slugs, force) from render.main() (:733-735) and site_maps_stale(trips) from render_site's hash (:638-644), and add `python3 tools/render.py --status`: one line per trip to be rendered and why (new; track changed; title/map/stats changed; OSM missing last time; no track; draft, skipped), then 'site maps: up to date | stale', exit 1 when anything is pending; it reads content/ and rendered/ only and fetches nothing. add_trip.py prints that status after its render and, with --no-render, 'maps not drawn: python3 tools/render.py <slug>'. If tools/publish.py (authoring-01) exists, it refuses when --status names a slug being published. Unit test with the drawing stubbed as tests/test_render_goals.py does.

**Files.** `tools/render.py`, `tools/add_trip.py`, `tests/test_render_goals.py`.

**Effort.** S. Visitor value 1, author value 3.3, confidence high.

**Risk.** Must not fetch anything: the status reads content/ and rendered/ only.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: render_trip compares meta['hash'] with trip_inputs(t) (tools/render.py:455-458), sets hash None on an OSM failure (:475-476; site maps :694-695), main() builds the pending list inline (:733-735), add_trip.py:201-203 prints 'next: edit' whether or not maps were drawn, and checks.py:834-836 warns only when meta.json is missing; no render is marked osm_failed today (0 files). tests/test_render_goals.py already stubs render_map, fetch_osm, render_single and optimize_images with mock.patch.object (:3-5, :56, :82, :218-220), so the test pattern exists.

#### authoring-13. Validate region and sub-type at entry and print the remaining steps

**Observation.** add_trip.py takes --region and --subtype as free text (add_trip.py:115, 117); a second spelling becomes a second region that only the validator's warning (checks.py:949-963) and two paragraphs of the guide (ADDING-TRIPS.md:39-46) catch afterwards, while the site knows exactly four Other sub-types (core.SUB_WORD). The tool writes `alt: ''` for every photo (add_trip.py:78) and ends with one 'next:' line (:203); the rest of the checklist lives in a 332-line guide. add_trip.py:166 still counts existing day photos with a *.jpg glob although photos have been .webp since cwebp came in.

**Evidence.** `tools/add_trip.py:78`; `tools/add_trip.py:115-117`; `tools/add_trip.py:166`; `tools/add_trip.py:203`; `tools/lib/checks.py:949-963`; `ADDING-TRIPS.md:39-46`; `tools/sitegen/core.py:34-35`.

**Proposal.** add_trip.py: load existing regions with content.load_all(include_drafts=True); when content.slugify(--region) matches an existing region spelled differently, exit 2 with 'region "eastern sierra" is written "Eastern Sierra" on 12 trips; use that or --new-region'; a name no trip uses needs --new-region; --subtype uses argparse choices=content.OTHER_SUBTYPES (tools/lib/content.py:25, the list checks.py:640 already enforces; core.SUB_WORD in tools/sitegen is not on add_trip.py's import path). At the end print a numbered checklist: the file to edit, how many alt lines are empty, the optional beta/peaks lines and that peaks need a re-render, the preview command (authoring-10) and the publish command (authoring-01). Replace the *.jpg glob at :166 with one that counts .webp (and the .jpg fallback web_copies writes without cwebp). Tests in tests/test_add_trip.py (authoring-15).

**Files.** `tools/add_trip.py`, `tests/test_add_trip.py`, `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1, author value 3, confidence high.

**Risk.** Region matching must use the same slugify as checks.py so the two rules never disagree.

**Review note (condensed; the observation and proposal above are the revised text).** Observation verified: tools/add_trip.py:78 writes 'alt': '' for every photo; :115 and :117 take --subtype and --region as free text; :166 counts existing day photos with a *.jpg glob although photos.web_copies returns 'webp' (tools/lib/photos.py:169) and content/trips/*/photos/ holds 0 .jpg and 1,004 .webp files; :203 prints one 'next:' line; tools/lib/checks.py:949-963 (_region_spellings) only warns afterwards; core.py:34-35 lists four sub-types. Observation verified: --subtype and --region are free text (tools/add_trip.py:115,117), `alt: ''` for every photo (:78), one 'next:' line (:203), the validator's region-spelling warning at tools/lib/checks.py:949-963, and the *.jpg glob at :166 (photos are written as webp by photos.web_copies, tools/lib/photos.py:169). The observation reproduces in full: tools/add_trip.py:78 writes 'alt': '' for every photo; :115 --subtype and :117 --region are free-text help strings; :166 globs photos/*.jpg while every one of the 1,004 photo files under content/trips/ is .webp (photos.web_copies writes .webp whenever cwebp is present, tools/lib/photos.py:150-166), so 'existing' is 0 and only the printed count at :172 is wrong; :203 is the single 'next:' line; tools/lib/checks.py:949-963 is _region_spellings, a warning; ADDING-TRIPS.md:39-46 is the two paragraphs; tools/sitegen/core.py:35 SUB_WORD has four keys; ADDING-TRIPS.md is 332 lines.

#### authoring-06. Read Garmin's zip directly; no Garmin bulk-export path

**Observation.** ADDING-TRIPS.md:9 tells the author to unzip Garmin Connect's 'Export Original' download first; tracks.read accepts .fit, .fit.gz and .gpx and fit_reader.read_track dispatches on '.gpx' else FIT (fit_reader.py:151-152; gzip is handled inside read_fit, :35-38), so a .zip fails. Strava has a bulk path (`--strava-export DIR --strava-id N`, add_trip.py:130-139, strava.py:24-63), Garmin has none, although the workspace holds a full Garmin account export: DI_CONNECT/DI-Connect-Fitness/*_1_, *_301_, *_601_summarizedActivities.json (300, 300 and 138 activities, 738 in all, with activityId, name, activityType, startTimeLocal, startTimeGmt, beginTimestamp, timeZoneId, distance, movingDuration, and elevationGain/elevationLoss on 470 of them) and DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_0-_Part1..3.zip (18,167 .fit members). The FIT members are named by a 12-digit upload id, not by activityId (0 of 738 activityIds appear in any member name), and most members hold no GPS points; the ones that do match a JSON activity by start time (7 of 7 in a 200-member sample, within 5 minutes of beginTimestamp). Every file name in the export carries the account's e-mail address.

**Evidence.** `ADDING-TRIPS.md:9`; `tools/lib/tracks.py:16-18`; `tools/lib/fit_reader.py:151-152`; `tools/add_trip.py:130-139`; `tools/lib/strava.py:24-63`; `../Garmin and Strava Data Exports/Garmin Export 9:28:26/DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_0-_Part1.zip`; `../Garmin and Strava Data Exports/Garmin Export 9:28:26/DI_CONNECT/DI-Connect-Fitness/ (three *summarizedActivities.json parts)`.

**Proposal.** tracks.read: when the path ends in .zip, open it with zipfile, require exactly one .fit/.fit.gz/.gpx member under a size bound (say 50 MB), read it from memory (no extraction) and pass the bytes to fit_reader (add read_fit_bytes and read_gpx_bytes; read_fit and read_gpx call them; read_fit already gzip-decompresses bytes it has read). Test in tests/test_tracks.py with a temp zip holding a hand-built FIT or a small GPX, plus a zip with two members that must be refused with a message naming them. Change ADDING-TRIPS.md:9 and README.md to say the .zip from 'Export Original' can be given to add_trip.py as it is. The review looked at a Garmin bulk path (a tools/lib/garmin.py mirroring strava.Export, `--garmin-export DIR --garmin-id N`, a `garmin_id:` key) and dropped it: the account export's FIT members are named by upload id, not activity id, and join a JSON activity only by time; do not build one, and no garmin_id key.

**Files.** `tools/lib/tracks.py`, `tools/lib/fit_reader.py`, `tools/add_trip.py`, `tests/test_tracks.py`, `ADDING-TRIPS.md`, `README.md`.

**Effort.** S. Visitor value 1, author value 3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 10 ('via Strava' footnote)

**Risk.** The account export is personal data: nothing from it, not even a file name, goes into tests or docs; the zip test uses a synthetic member.

**Decision for Eric.** None (the dropped bulk path was the only part that needed a stats rule).

**Review note (condensed; the observation and proposal above are the revised text).** Part (a) is verified and worth S: ADDING-TRIPS.md:9 tells the author to unzip Garmin Connect's 'Export Original' download, tracks.read (tools/lib/tracks.py:16-18) and fit_reader.read_track (tools/lib/fit_reader.py:151-152) dispatch on .gpx else FIT, so a .zip fails; reading the one member from memory is stdlib zipfile. The code side reproduces: ADDING-TRIPS.md:9 tells the author to unzip Garmin's Export Original; tools/lib/tracks.py:16-18 reads .fit, .fit.gz or .gpx through fit_reader.read_track, which at fit_reader.py:151-152 dispatches on '.gpx' else read_fit (gzip handled inside read_fit, :35-38), so a .zip fails; the only bulk path is Strava's (add_trip.py:130-139, strava.py:24-63); Strava's stats win at add_trip.py:149; INDEX_KEYS/DAY_KEYS are checks.py:53-63; the 'via Strava' footnote is core.py:1045, multiday.py:348, series.py:166 and report section 10 :461.

#### authoring-07. List the Strava activities not yet on the site

**Observation.** 156 trips and 184 journal day files carry a `strava_id` from the first bulk import, 340 distinct ids, and 'nothing reads it' (checks.py:60; content.py and core.py never mention it). The current export (Strava Export 9:28:26: activities.csv with 721 activities, 603 .fit.gz and 118 .gpx tracks, 561 media files) holds 381 activities whose id is on no trip or day; finding one to import means reading the CSV by hand for `--strava-id` (ADDING-TRIPS.md:132-138), and the guide gives only a placeholder export path (:137; the workspace CLAUDE.md names the current folder).

**Evidence.** `tools/lib/checks.py:60`; `tools/add_trip.py:130-139`; `tools/lib/strava.py:59-67`; `ADDING-TRIPS.md:132-138`; `../Garmin and Strava Data Exports/Strava Export 9:28:26/activities.csv (721 activities by csv.DictReader, 772 lines by wc -l because descriptions span lines; 340 ids on a trip or day, 381 not)`.

**Proposal.** `python3 tools/add_trip.py --strava-export DIR --list [--type Hike,Ride] [--since YYYY-MM-DD]`: strava.Export.not_imported(known_ids) (beside by_id and search, strava.py:59-67) returns the records whose id is on no index.md or days/NN.md (collect ids with frontmatter.split over content/trips, including days, since the trip dict does not keep the field); print id, date, type, name, distance and whether media exists, newest first. Document the flag in ADDING-TRIPS.md step 2 next to --strava-id; the export path there stays a placeholder (the export is personal data outside the repository). Tests in a new tests/test_strava_export.py with a synthetic activities.csv in a temp dir (the only existing Strava tests are the key-list cases in tests/test_checks.py).

**Files.** `tools/add_trip.py`, `tools/lib/strava.py`, `tests/test_strava_export.py`, `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1, author value 2.7, confidence high.

**Risk.** The listing prints activity names and dates to the terminal only; nothing is written or committed.

**Review note (condensed; the observation and proposal above are the revised text).** Nothing is built (strava.Export has only by_id and search, strava.py:59-67; add_trip.py has no --list), but two parts of the observation are wrong. The gap is real (tools/lib/checks.py:60: nothing reads strava_id; ADDING-TRIPS.md:132-138 says to find the id in activities.csv) and strava.Export.by_id/search exist (tools/lib/strava.py:59-67), so a --list is under an hour. The code citations hold: checks.py:60 says strava_id is 'on 156 trips and every day file; nothing reads it' (content.py and core.py never mention strava_id, so the proposal's frontmatter.split collector is the right one); add_trip.py:130-139 and strava.py:59-67 (by_id, search) are the right places; ADDING-TRIPS.md:132-138 is the manual --strava-id step.

#### gap8-08. --day-of: replace a day, bump end_date, count day photos right

**Observation.** --day-of always appends the next number (tools/add_trip.py:163-164): there is no way to replace days/NN.gpx with a better recording short of hand work. When the new day's date is later than index.md's end_date the build only warns (tools/lib/checks.py:764-771) and ADDING-TRIPS.md:111-114 tells Eric to edit the line by hand. Line :166 counts existing day photos with a *.jpg glob, so the 'N existing' print says 0 for every trip since the copies became .webp (tools/lib/photos.py:149-169); the pipeline reader noted the same. 11 multi-day trips and the PCT journal are affected.

**Evidence.** `tools/add_trip.py:159-176`; `tools/add_trip.py:166`; `tools/lib/checks.py:764-771`; `ADDING-TRIPS.md:111-117`; `tools/lib/photos.py:149-169`.

**Proposal.** (1) Count existing day photos by the dNN- prefix across .webp and .jpg (glob photos/d*-*.webp and .jpg), so the 'N existing' print is right; a one-line fix with a test. (2) After --day-of, when index.md has an end_date earlier than the new day's date, rewrite end_date through the frontmatter round trip (byte-identical on all files today) and print 'end_date 2026-09-12 -> 2026-09-13' (the day file's own date from the track, no guess); when index.md has no end_date line, write none, since the page already ends on the last day (content.load_trip). Update ADDING-TRIPS.md:111-114 to say the line is updated for you. Tests in tests/test_add_trip.py with a helpers.make_trip multi-day fixture: the count, the bump, and no bump when the day is not later. Effort S. (3) Replacing a day's recording (days/NN.gpx plus only date, start_time and stats in days/NN.md, title/day/hut/transfer_before/photos/body kept) is `add_trip.py TRACK --update SLUG --day NN` once gap8-02 exists; until then it stays hand work, and a PCT day still needs its day: label by hand (docs/WEBSITE_IMPLEMENTATION_LOG.md Phase 3 'Remaining issues').

**Files.** `tools/add_trip.py`, `tests/test_add_trip.py`, `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1, author value 2.3, confidence high.

**Already known.** docs/WEBSITE_IMPLEMENTATION_LOG.md Phase 3 'Remaining issues' (a new PCT day needs a day: line).

**Risk.** A replaced day changes the render hash, so rendered/trips/<slug> must be committed with it; a PCT day still needs its day: label by hand (log Phase 3).

**Review note (condensed; the observation and proposal above are the revised text).** Verified: --day-of always appends the next number (add_trip.py:163-164); :166 counts existing day photos with a *.jpg glob while every photo file is .webp (1,004 .webp, 0 .jpg under content/trips/*/photos), so the 'N existing' print is always 0; checks.py:764-771 only warns when a day is later than end_date, and ADDING-TRIPS.md:111-114 tells Eric to edit it by hand.

#### gap8-07. Fix a trip's time zone and recompute its date and start time

**Observation.** timezone, date and start_time are written once at import from tracks.local_start (tools/add_trip.py:147, :188-189). guess_tz (tools/lib/tracks.py:87-95) knows three zones, Europe/Zurich, America/Los_Angeles and America/Denver, and returns 'UTC' for everything else: one published trip carries timezone: UTC today (its region lies east of the Mountain zone), so the 'Start HH:MM' line the page shows (tools/sitegen/core.py:987) is a UTC clock, and Arizona, which keeps no summer time, falls in the Denver box. docs/IMPLEMENTATION_REPORT.md section 12.12 lists more suspected zones in a private file. A fix needs the UTC timestamps, which the published GPX keeps (156 of the 157 track.gpx files and all 184 days/NN.gpx files hold <time>; tools/lib/tracks.py:72-79), so it can be done offline; none of timezone, date or start_time is in the render hash (render.py:432), so no render follows.

**Evidence.** `tools/lib/tracks.py:87-104`; `tools/add_trip.py:147`; `tools/add_trip.py:188-189`; `tools/sitegen/core.py:987`; `tools/lib/tracks.py:66-84`; `tools/render.py:432`; `tools/lib/fit_reader.py:129-148`.

**Proposal.** (1) A `--retime SLUG [--timezone Z]` mode in tools/add_trip.py: read the trip's own track.gpx with fit_reader.read_gpx, call tracks.local_start(pts, zone or the file's timezone), set timezone, date and start_time through the frontmatter round trip, print old -> new, refuse a GPX without timestamps and a folder with days/. Typical use: `add_trip.py --retime SLUG --timezone America/Chicago`. (2) Extend guess_tz with America/Phoenix for Arizona's box (lat 31.3-37, lon -114.8 to -109), America/Chicago (lon >= -102 and < -85, lat > 25) and America/New_York east of -85, and have add_trip.py print the zone it used ('timezone America/Denver, guessed; --timezone to change'). (3) A validator note when timezone is UTC on a trip with a track: 'start_time is a UTC clock; set timezone: and run add_trip.py --retime'. Tests: a guess_tz table and the retime on a fixture GPX with a known timestamp in a new tests/test_tracks.py (tests/test_track_rules.py is about the generator). Which trips to re-time is Eric's list; do not guess. No edit_trips.py (gap8-06 is not planned).

**Files.** `tools/add_trip.py`, `tools/lib/tracks.py`, `tools/lib/checks.py`, `tests/test_tracks.py`, `ADDING-TRIPS.md` (option table).

**Effort.** S. Visitor value 1.7, author value 2.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 12.12 (time zones on a few trips look wrong).

**Risk.** A changed date moves the trip in every newest-first list, the feed (build.py pubDate) and the sitemap: correct, but visible. Start times are already published (docs/PRIVACY_NOTES.md), so nothing new goes public.

**Decision for Eric.** Which trips to correct (his private list from report section 12.12).

**Review revision (applies on top of the text above).** Observation, corrected sentence: 'A fix needs the UTC timestamps, which the published GPX keeps (156 of the 157 track.gpx files hold <time>; the 11 other trips keep their recordings in days/NN.gpx or have no track; tools/lib/tracks.py:72-79), so it can be done offline; none of timezone, date or start_time is in the render hash (render.py:432), so no render follows.' Everything else in the observation and the proposal stands as written.

**Review revision (applies on top of the text above).** Observation correction: 156 of the 157 track.gpx files keep <time> (days/NN.gpx are separate), so a fix runs offline. (1) A `--retime SLUG [--timezone Z]` mode in tools/add_trip.py (or `--update SLUG --timezone Z` without a new track, if gap8-02 is built): read the trip's own track.gpx with fit_reader.read_gpx, call tracks.local_start(pts, zone or the file's timezone), set timezone, date and start_time through the frontmatter round trip, print old -> new, refuse a GPX without timestamps and a folder with days/. Typical use: `add_trip.py --retime SLUG --timezone America/Chicago`. (2) Extend guess_tz with America/Phoenix for Arizona's box (lat 31.3-37, lon -114.8 to -109), America/Chicago (lon >= -102 and < -85, lat > 25) and America/New_York east of -85, and have add_trip.py print the zone it used ('timezone America/Denver, guessed; --timezone to change'). (3) A validator note when timezone is UTC on a trip with a track: 'start_time is a UTC clock; set timezone: and run add_trip.py --retime'. Tests: a guess_tz table and the retime on a fixture GPX with a known timestamp in a new tests/test_tracks.py (tests/test_track_rules.py is about the generator, not tracks.py). Effort S for (2) and (3); (1) is S on its own or part of gap8-02.

**Review note (condensed; the observation and proposal above are the revised text).** Not built, but one count in the observation is wrong. tracks.py:87-95 guess_tz knows exactly Europe/Zurich, America/Los_Angeles and America/Denver and returns 'UTC' otherwise; exactly 1 index.md carries timezone: UTC (155 Los_Angeles, 7 Denver, 4 Zurich), and that trip has a start_time line and a track.gpx, so core.py:987 prints its Start line from a UTC clock. add_trip.py:147 and :188-189 write the values once; fit_reader.read_gpx (:129-148) parses <time>; checks.py treats timezone only as a text field (:73). Verified: guess_tz knows three zones and returns 'UTC' otherwise (tools/lib/tracks.py:87-95), timezone/date/start_time are written once at import (add_trip.py:147, :188-189), the start time is shown (core.py:987), one published index.md carries timezone: UTC (counted: 155 Los_Angeles, 7 Denver, 4 Zurich, 1 UTC, 1 none), Arizona lies inside the Denver box and keeps no summer time, and none of the three keys is in the render hash (:432). Reproduced: guess_tz (tracks.py:87-95) knows three zones and falls back to 'UTC'; add_trip.py:147 and :188-189 write timezone/date/start_time once; core.py:987 prints 'Start HH:MM' from start_time; exactly one index.md has timezone: UTC; Arizona's longitudes sit inside the Denver box; IMPLEMENTATION_REPORT 12.12 (:520) is the time-zone decision; render.py:432 hashes none of timezone/date/start_time; fit_reader.read_gpx is :129-148 and build.py:234 writes pubDate.

#### gap9-03. Render into a temp folder and swap, so a failed render keeps the last good map

**Observation.** render_trip removes rendered/trips/<slug>/ before it draws anything (render.py:460) and writes meta.json last (render.py:479); render_site does the same to rendered/site/ (render.py:647). A terrain-tile failure raises RuntimeError in geo.get_tile (geo.py:205) and nothing in render_trip or main catches it, so the run stops with that trip's folder already gone; with --jobs the first exception re-raises from f.result() (render.py:751): the executor's exit waits for the other workers, so their trips finish, but the failing trip's folder stays half-written and any further worker failures are never read. A Ctrl-C leaves hillshade PNGs that build.py copies by glob into the site (build.py:186) beside a page with no map (core.render_meta finds no meta.json, core.py:469-478). The validator then only says 'no rendered map' (checks.py:832-835). OSM failure, by contrast, degrades to a terrain-only map marked hash null (render.py:164-165, 476-477).

**Evidence.** `tools/render.py:460`; `tools/render.py:479`; `tools/render.py:647`; `tools/lib/geo.py:205`; `tools/render.py:751`; `tools/build.py:186`; `tools/sitegen/core.py:476-483`; `tools/lib/checks.py:834`; `tools/render.py:164-165`; `tools/render.py:476-477`.

**Proposal.** In render_trip and render_site, bind the output to `<folder>.tmp-<pid>` for the whole drawing (render_single, render_multi and set_out write through t['rendered'] at render.py:402, 406, 461, 471, so set t['rendered'] to the temp path inside a try/finally and restore it after; add `rendered/**/*.tmp-*` to .gitignore), draw, run optimize_images, write meta.json, then swap: rename the old folder to `<folder>.old`, the temp folder to `<folder>`, and rmtree `.old` (os.replace of a folder over a non-empty folder fails with ENOTEMPTY on macOS). In the finally clause remove any temp folder left, so a KeyboardInterrupt (not an Exception subclass) also cleans up. On an Exception print `! <slug>: <error>`, keep the old render and go on to the next trip in both the serial loop and the pool loop (f.result() at render.py:751 currently re-raises); exit 1 at the end with the failed slugs. Cover it in tests/test_render_goals.py with the existing stubs: render_single raising leaves the previous folder's files intact and the run completes with exit 1; a BaseException leaves no .tmp folder. Add to ADDING-TRIPS.md 'If something goes wrong' (line 313): a render that fails leaves the old maps on the site.

**Files.** `tools/render.py`, `tests/test_render_goals.py`, `.gitignore`, `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1, author value 3.3, confidence high.

**Risk.** os.replace of a folder over an existing folder fails on macOS, so remove the old folder immediately before the rename (a window of milliseconds instead of minutes), or rename old to .old, new to final, then delete .old. Nothing else changes in what is drawn.

**Review revision (applies on top of the text above).** Proposal: unchanged. Risk: os.replace of a folder over an existing non-empty folder fails on any POSIX system (ENOTEMPTY), so remove the old folder immediately before the rename, or rename old to .old, new to final, then delete .old.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible, small and worth it: a tile failure raises through render_trip after shutil.rmtree has already run (render.py:460, geo.py:205), and a Ctrl-C leaves half a folder that build.py copies by glob (build.py:186). Effort S is honest only because tests/test_render_goals.py already stubs render_single and points render.OUT at a temp dir. Reproduced: render_trip removes the folder at render.py:460 and writes meta.json last at 479; render_site removes rendered/site/ at 647; geo.get_tile raises RuntimeError at geo.py:205 after three curl tries (199); nothing in render_trip or main catches it; build.py:186 copies *.png, *.webp and *.base.svg by glob whenever has_track; core.render_meta returns empty maps when meta.json is missing (core.py:469-478); checks.py:832-835 only warns 'no rendered map'; OSM failure degrades at render.py:164-165 and 476-477; the .gitignore patterns (space + digits) do not match '.tmp-<pid>'; os.replace over a non-empty directory fails with ENOTEMPTY (tested in scratch; it is POSIX behavior, not macOS-only).

#### gap9-06. Move the tile and OSM caches out of iCloud Drive and give answers an age

**Observation.** TILE_DIR and OSM_DIR default to <repo>/.cache/{tiles,osm} (geo.py:14-15), inside ~/Documents, which iCloud Drive offloads. Measured today: 206 of the 220 OSM answers (1,189 MB logical, 298 MB on disk) and 1,806 of the 2,524 tiles (265 MB logical, 81 MB on disk) are dataless stubs (`ls -lO` shows 'dataless'); the disk has 19 GB free. So the caches do not make a re-render offline: each first read blocks on an iCloud download, and offline it fails and falls through to fetch() (geo.py:206-211). The caches never expire (overpass(): if the file exists it is loaded, geo.py:464-465) and the key is the sha1 of the query text, which carries the bbox at 5 decimals (geo.py:486-507), so any change of frame (size, pad, min_extent_m, a changed track) misses every cached answer, while an unchanged frame reuses OpenStreetMap as it was on 2026-09-27/28 forever: a map redrawn next year sits beside neighbours drawn from a different snapshot. Three cached answers are 64 to 71 MB, and one preview's ~200 MB answer exceeded the 180 s limit (geo.py:469; log:1014-1016).

**Evidence.** `tools/lib/geo.py:14-15`; `tools/lib/geo.py:206-211`; `tools/lib/geo.py:461-481`; `tools/lib/geo.py:486-507`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:1014-1016`; `docs/DEVELOPING.md:15`; `a reviewer's probe script run against tools/render.py on 2026-10-13`; `tools/lib/geo.py:14-17`; `tools/lib/mapkit.py:18-20`; `tools/render.py:9`; `ls -la .cache; du -sh .cache/osm .cache/tiles .cache/review .cache/p4 .cache/p5 .cache/plan2 (2026-10-13)`; `../CLAUDE.md, the workspace CLAUDE.md one folder above the repository (iCloud Drive gotcha: offloaded 'dataless' files)`.

**Proposal.** Default TILE_DIR and OSM_DIR to ~/Library/Caches/personal-website/{tiles,osm} (outside iCloud Drive; macOS excludes ~/Library/Caches from Time Machine; the same folder Phase 8 names for scratch builds), keeping the TILE_DIR and OSM_DIR env overrides; create the folders lazily in get_tile and overpass rather than at import (geo.py:16-17), so tests and CI do not create a folder under ~/Library. Store each new OSM answer as {'fetched': 'YYYY-MM-DD', 'query': ..., 'data': ...} and read the old bare form too; at the end of a run print the tile and OSM hit/miss counts and the oldest and newest OSM date used (Phase 15's gap9-05 also puts them into meta['renderer']). No --refresh-osm flag and no --migrate-cache: a deliberate refresh is deleting .cache/osm (gap7-09), and the one-time move is a mv Eric runs himself, documented in docs/DEVELOPING.md:15 and ADDING-TRIPS.md's 'needs the internet' lines (a plain mv makes iCloud download each file first, about 1.3 GB; do it before, not during, a re-render; it then occupies about 1.4 GB of local disk). The iCloud note in the workspace-root CLAUDE.md sits one folder above the repository and outside git, so tell Eric in the report rather than editing it.

**Files.** `tools/lib/geo.py`, `tools/render.py`, `docs/DEVELOPING.md`, `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1, author value 3, confidence high.

**Also covers.** gap7-08 (merged into this finding).

**Already known.** memory note 'iCloud offloading under low disk'; CLAUDE.md 'Workspace gotchas: iCloud Drive'

**Risk.** The migration downloads about 1.3 GB from iCloud onto a disk with 19 GB free (fine once; do it before, not during, a re-render). No test sets TILE_DIR or OSM_DIR today (grep of tests/). Refreshing OSM changes roads and lake outlines on maps whose tracks did not change; pair it with gap9-02's sheet.

**Review note (condensed; the observation and proposal above are the revised text).** The cache problem is real and measured this session: 206 of 220 OSM answers and 1,806 of 2,524 tiles are iCloud dataless stubs (1,134 MB and 252 MB logical against 284 MB and 77 MB on disk; 18 GB free), so a re-render blocks on about 1.3 GB of iCloud downloads and fails offline. Reproduced exactly: TILE_DIR/OSM_DIR at geo.py:14-15 under <repo>/.cache; ls -lO today: 206 of 220 OSM answers dataless (1,189 MB logical, 298 MB on disk) and 1,806 of 2,524 tiles (265 MB logical, 81 MB on disk); df shows 18 GB free; offline reads fall through to fetch() (geo.py:206-211); the cache never expires (464-465); the key is sha1 of the query (461-463) whose bbox is formatted at 5 decimals (487); the three biggest answers are 71, 68 and 64 MB; curl --max-time 180 at 469; log:1014-1016; 218 of the 220 answers are dated Sep 27/28 and 2 Oct 12; no test sets TILE_DIR or OSM_DIR.

#### gap7-09. Guard the OSM cache against a corrupt answer

**Observation.** `geo.overpass()` returns a cached answer for ever (keyed by a hash of the query; files today date from Sep 27 to Oct 12) and reads it with a bare `json.load`: a truncated or unreadable cache file raises, `render.fetch_osm` catches it, retries the same read three times with 10/20/30 s sleeps, then draws the map 'terrain only' and marks `osm_failed`, and the next run hits the same file again, so roads and lake names stay missing until someone deletes the file by hand. `get_tile` already refetches a truncated tile (geo.py:206-211). The render hashes exclude OSM data, so newer OSM is never picked up without `--force`, and even `--force` takes the cached answer.

**Evidence.** `tools/lib/geo.py:461-477`; `tools/lib/geo.py:206-211`; `tools/render.py:153-166`; `tools/render.py:430-434`; `tools/render.py:638-645`; `ls -lt .cache/osm (newest Oct 12 13:34, oldest Sep 27 12:21; 2026-10-13)`; `ADDING-TRIPS.md:316-317`.

**Proposal.** (a) In `geo.overpass()`, read the cached file inside try/except (ValueError, OSError): on failure remove it and fall through to the fetch, as `get_tile` does; one test with a temp OSM_DIR holding a truncated file and `subprocess.run` stubbed to return a good answer. (b) No new flag: add one line beside `--force` in README 'Check, build and re-render' and in ADDING-TRIPS 'If something goes wrong': to pick up newer OpenStreetMap data (a new trail, a renamed lake), delete `.cache/osm/` (or the one answer) and run `python3 tools/render.py --site --force`; say that this refetches every answer (the log's 200 MB case, docs/WEBSITE_IMPLEMENTATION_LOG.md:1014-1016) and can change roads and labels on every map, which the hash check does not notice. (c) No automatic expiry. Effort S.

**Files.** `tools/lib/geo.py`, `tests/test_geo_cache.py`, `README.md`, `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1, author value 2, confidence high.

**Already known.** docs/WEBSITE_IMPLEMENTATION_LOG.md:1014-1016 (the oversized Overpass answer)

**Risk.** Deleting `.cache/osm/` before `--force` refetches every answer: Overpass load and time (the log records a ~200 MB answer that overran the 180 s limit). A refetch can change a map's roads and labels, which the hash check does not notice; say so in the doc.

**Decision for Eric.** Whether a cached OSM answer should ever expire on its own (proposed: no, refresh only on request).

**Review note (condensed; the observation and proposal above are the revised text).** Part (a) is verified and cheap: geo.py:464-465 returns `json.load(open(p))` on any cached file with no guard, render.py:158-166 retries the same read three times with 10/20/30 s sleeps and then draws terrain only, so a bad cache file degrades every later run of that map silently; get_tile (geo.py:208-212) already shows the pattern to copy.

#### resilience-12. Show an honest empty box for a report whose map is not rendered

**Observation.** A report with a track but no render (the validator's 'no rendered map' warning, checks.py:834: after `--no-render`, without internet, or a draft just un-drafted) still gets a `#map` section because `has_map = bool(t['track'])` (report.py:598): `core.map_block` returns an empty `<div class="map map--report">` when `meta['maps']` has no entry (core.py:484-527), yet the section keeps its legend rows and the 'As recorded on … Terrain: AWS Terrain Tiles' caption, the title action 'View route' and the phone bar's Map item lead to that blank, and the full-screen map page is built around nothing. The goal page already handles the same state with an `.empty` box saying 'Map not rendered yet' (report.py:394-409). No live trip is in this state; the build passes with a warning.

**Evidence.** `tools/lib/checks.py:834`; `tools/sitegen/pages/report.py:598-630`; `tools/sitegen/core.py:484-527`; `tools/sitegen/pages/report.py:394-409`.

**Proposal.** In report.page (report.py:598-623) and multiday.overview_map (multiday.py:381-393) test meta['maps'] as goal_map_section does (report.py:394-409): with no render, emit the .empty box ('Map not rendered yet; the GPX file is published') in the #map section, drop the key rows, caption, map preloads and the full-screen page for that trip (report.py:708-715, multiday.py:802-806), and keep the GPX download and the title action. Make the validator warning at checks.py:834 name the consequence ('the page shows an empty map box'). Add the fixture state to tests/test_report_page.py and to the file that holds the multi-day page tests (MultiDayPageTests in tests/test_report_page.py:1967; there is no tests/test_multiday_page.py), following the 'report without a track' test at tests/test_a11y_static.py:1818. Effort S.

**Files.** `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tools/lib/checks.py`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 1.3, author value 2.3, confidence high.

**Already known.** IMPLEMENTATION_REPORT.md 10.3 (empty map block on a track-less multi-day); ADDING-TRIPS.md 'Maps not rendered' (pipeline map 7.4)

**Risk.** None for rendered trips; the full-screen page's absence must not break the phone button (the button is only emitted with a phone variant, core.py:523-524).

**Review revision (applies on top of the text above).** Evidence lines: tools/sitegen/pages/report.py:596 (has_map), :613-621 (the map section), :714 (the full-screen page is built for any report with a track; a planned goal only with a render), :394-409 (goal_map_section); tools/sitegen/core.py:469-475 (render_meta returns empty maps when meta.json is missing, so the build passes), :484-527 (map_block), :522-523 (the full-map link needs a phone variant); tools/lib/checks.py:833-835; tools/sitegen/pages/multiday.py:389; tests/test_a11y_static.py:1818. Observation otherwise as written.

**Review note (condensed; the observation and proposal above are the revised text).** Mechanics verified: report.py:598 sets has_map from the track alone; core.map_block skips every variant whose render is absent (core.py:505-506) and returns an empty <div class="map map--report">, while the key rows, caption and phone stats note are emitted regardless (report.py:621-623); fullscreen_page is built for every trip with a track (report.py:708-715) and multiday.py:381-393 follows the same pattern; render_meta returns {'maps': {}} when meta.json is missing (core.py:474-475); the goal page already handles the state with an .empty box (report.py:394-409). Reproduces with two line corrections.

#### authoring-15. Tests for the import tools that have none

**Observation.** 2,476 test methods cover the generator, validator and page scripts, but nothing tests tools/add_trip.py (grep 'add_trip' in tests/ finds test_build_site's own helper of that name, three comments, and test_ticklist_cli.py:664-676 asserting that the tick-list CLI never calls it); tools/lib/strava.py is imported by no test file, geo.py and fit_reader.py by one each (test_region_days, test_gpxroute), and mapkit.py by three that use only its Track class, line_links helper and MAP_CSS constant, never a drawing call (test_render_goals.py:1-9 stubs render_map, fetch_osm, render_single and optimize_images and says render.py is never run). The path from a recording to a trip folder (FIT decode, simplify, stats, front matter, photo copies) is exercised only by a real import.

**Evidence.** `grep 'add_trip' tests/*.py (helper only)`; `grep -l 'import strava' tests/test_*.py (none)`; `tests/test_render_goals.py:1-9`; `tests/test_thumbs.py`; `docs/DEVELOPING.md:1340-1360`.

**Proposal.** tests/test_add_trip.py: a synthetic 20-point GPX and a hand-built FIT (header, one definition message, three records, written with struct) in a temp dir; run add_trip.main() with TRIPS patched and --no-render; assert the folder, the keys of checks.INDEX_KEYS written, a well-formed track.gpx, --strip-times, --draft, --day-of numbering and its `note:` lines, refusal of an existing folder without --force, and the Strava path against a synthetic activities.csv (two Distance columns, a Media list) with tests/test_strava_export.py for Export.by_id, stats_from and paragraphs. tests/test_fit_reader.py decodes the hand-built FIT through read_fit and read_track. No render smoke test (mapkit's drawing gets its own tests in Phase 15). Photo steps stub photos.web_copies the way test_thumbs stubs thumb_copy and have_cwebp (test_thumbs.py:10-11), or skip when shutil.which('sips') is None as the Node tests skip without node.

**Files.** `tests/test_add_trip.py`, `tests/test_strava_export.py`, `tests/test_fit_reader.py`, `docs/DEVELOPING.md`.

**Effort.** M. Visitor value 1, author value 3, confidence high.

**Risk.** Fixtures must stay synthetic (tests/test_fixture_text.py forbids real write-ups; no real recording may be checked in).

**Review note (condensed; the observation and proposal above are the revised text).** The gap is real and this is the most valuable test work in the set: tools/add_trip.py is what Eric runs for every trip and no test runs it (tests mention it only in comments and in two negative assertions, tests/test_ticklist_cli.py:664,675); tools/lib/strava.py (88 lines, stats_from :70, paragraphs :85) is imported by no test; fit_reader.py (161 lines, read_fit :35) is touched only through read_gpx in tests/test_gpxroute.py:125. The substance holds: 2,476 'def test_' methods; no test file imports tools/lib/strava.py (only strava_id front-matter mentions in test_checks.py and test_privacy_audit.py); geo is imported by tests/test_region_days.py:90 only (test_privacy_audit reaches it as pa.geo.hav, :304) and fit_reader by tests/test_gpxroute.py only; tests/test_render_goals.py:1-9 says render.py is never run and stubs render_map, fetch_osm, render_single, optimize_images; add_trip.py has no test.

**Gates.** The phase is done when every line below holds and is recorded in the log entry:

1. python3 -W error -m unittest discover -s tests passes on /usr/bin/python3 (3.9.6) and python3.12, with the new tests/test_add_trip.py (synthetic GPX and hand-built FIT; --no-render; --force refused and index.md byte-identical; --day-of count and end_date bump; --retime on a fixture GPX; a .zip with one member read, two members refused; --strava-export --list on a synthetic CSV) and the tests/test_frontmatter.py cases for a ' #' value and a tab-indented block.
2. frontmatter.loads('title: Rose Knob  # a note') returns 'Rose Knob' and a tab-indented beta block raises ValueError naming the line; python3 tools/validate.py over today's content still reports 0 errors, 1 warning.
3. validate.py on a fixture whose rendered meta.json hash differs from trip_inputs, and on one with hash null, prints the two new warnings; python3 tools/validate.py on today's content prints neither.
4. With the network off, python3 tools/render.py --status lists nothing pending today, fetches nothing and exits 0; on a fixture with a changed track it names the trip and the reason and exits 1.
5. python3 tools/build.py --serve --open <slug> builds with --link in under 5 s, opens the page, and Ctrl+C ends without a traceback; --serve --copy still copies; --watch rebuilds within about 2 s after an edit to an index.md and keeps serving after a validator error.
6. A fixture trip with a track and no meta.json builds an .empty 'Map not rendered yet' box in #map, no key rows, no caption and no trips/<slug>/map/ page, and build.py --check passes.
7. In tests/test_render_goals.py a render_single that raises leaves the previous rendered folder's files intact, the run completes with exit 1, and no .tmp-* folder remains; a truncated .cache/osm file is removed and refetched (stubbed) instead of marking the map osm_failed.
8. add_trip.py refuses a second spelling of an existing region (exit 2 with the existing spelling named), takes --subtype only from content.OTHER_SUBTYPES, prints a numbered checklist with the count of empty alt lines, and the '(N existing)' photo count is right for .webp files.
9. ADDING-TRIPS.md step 4 (preview) and the option table (--timezone, --force, --retime, --list) updated; README preview line updated; python3 tools/build.py --check passes.

**Tests to add.** New: `tests/test_add_trip.py`, `tests/test_fit_reader.py`, `tests/test_geo_cache.py`, `tests/test_strava_export.py`, `tests/test_tracks.py`. Extended: `tests/test_build_cli.py`, `tests/test_checks_site_maps.py`, `tests/test_frontmatter.py`, `tests/test_render_goals.py`, `tests/test_report_page.py`. Plus the checks the gates name that no unit test covers: Network off for the `--status` gate; a second terminal for `--watch`; `python3 tools/validate.py` before and after on today's content (0 errors, 1 warning today).

**Screenshots to capture.** None of the site. Keep the terminal output of `render.py --status` and of `build.py --serve --open <slug>` in the log entry, and the validator's output on today's content before and after.

**Author inputs needed.** Which trips to `--retime` (Eric's private list, `docs/IMPLEMENTATION_REPORT.md` 12.12); the tool ships regardless. The one-time move of `.cache/tiles` and `.cache/osm` to `~/Library/Caches` (about 1.3 GB that iCloud must download first).

### Phase 7. Search and the explorer: vocabulary, matching, filters, cards and forms

**Goal.** Make a typed search find what a route or peak searcher means (apostrophes, inflections, dates, route shapes, word starts), give zero results a way out, put a search box on every page and the 404, and sharpen the explorer's facets, sorts, cards and phone forms, all in search.py, explore.js, trips.js, trips.py, ticklist.py, notfound.py and core.related.

**Prerequisites.** None (independent of Phase 6). Eric reads the activity word list of gap3-01 and picks visual-02 or ia-05 for the browse block (recommended visual-02).

**Decisions this phase waits on.**

- gap3-01's word list (Eric reads it; defaults proposed)
- visual-02 (hide the browse block with scripting, scoped to .p-trips) versus ia-05 (reorder and trim); recommended visual-02
- visual-05's FILTERS_FROM = 6 counting active goals only

**Findings in this phase** (24, in working order): resilience-03, gap3-01, gap3-02, gap3-03, gap3-07, gap3-04, gap3-05, qa-07, perf-08, ia-02, seo-14, ia-08, ia-06, ia-07, benchmark-02, qa-05, copy-03, a11y-13, ia-04, visual-02, phone-02, visual-05, phone-05, visual-07.

#### resilience-03. Drop apostrophes in the search normalizer instead of adding aliases

**Observation.** `normalize()` (search.py:33-39) and `norm()` (explore.js:9-13) turn every non-alphanumeric run into a space, so "Lover's Leap" is indexed as `lover s leap` (tests/norm_cases.json holds exactly that case). A visitor typing "lovers leap", "jakes peak", "maggies", "toms thumb" or "didnt" gets no result, although nine titles carry an apostrophe (three Lover's Leap reports, two Jake's Peak, Maggie's Peak, Tom's Thumb, "It's good to be back", "didn't see anyone else out") and write-ups hold more. The log's answer was an alias per affected title; the normalizer is the general fix and needs no content edits.

**Evidence.** `tools/sitegen/search.py:33-39`; `assets/js/pages/explore.js:9-13`; `tests/norm_cases.json`; `content/trips/lovers-leap-corrugation-corner/index.md`; `content/trips/jakes-peak/index.md`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:215-216`.

**Proposal.** In both normalizers delete `'`, `’` and `‘` before the non-alphanumeric replacement (Python: `re.sub("['’‘]", '', s)`; JS: `s.replace(/['’‘]/g, '')`), so title, index and query all become `lovers leap` / `didnt`. Update tests/norm_cases.json (the Lover's Leap cases and a `didn’t` case) and add a harness case in tests/trips_js_harness.js that `lovers`, `lover's` and `lover’s` each find the Lover's Leap entries. Rebuilding rewrites trips/search.json and the tick-list `data-text` (core.goal_card) in the new form. Update docs/CONTENT_GUIDE.md:397-398, which currently advises an alias.

**Files.** `tools/sitegen/search.py`, `assets/js/pages/explore.js`, `tests/norm_cases.json`, `tests/trips_js_harness.js`, `docs/CONTENT_GUIDE.md`.

**Effort.** S. Visitor value 3.3, author value 1.7, confidence high.

**Already known.** WEBSITE_IMPLEMENTATION_LOG.md Phase 2 'Remaining issues' (log:215-216); CONTENT_GUIDE.md:397-398

**Risk.** Index and script must ship in the same deploy; for up to ten minutes a cached old search.json pairs with the new script, which still matches `leap` and only misses the apostrophe forms, as today.

**Review note.** Kept as written by all three skeptics.

#### gap3-01. Write the activity's inflections and synonyms into the keyword field

**Observation.** tools/sitegen/search.py:53-62 puts only the activity label (and the Other sub-type word) into the index's 'k' field before aliases and peaks: in _site/trips/search.json (167 entries, identical to the live file) 51 entries' k starts with 'backcountry ski' (43 are exactly that), 61 'mountain biking', 33 'hiking' (29 exactly), 13 'climbing', 7 'other paddleboarding', 2 'other rafting'. explore.js match() (44-47) needs every typed word as a substring of title+place+keywords+write-up, so an inflection or synonym only ever hits write-ups: 'skiing' 9 hits (1 outside write-ups) against 51 ski reports, 'skied' 6, 'touring' 2, 'bike' 10 (1 outside) against 61 rides, 'mtb' 2, 'hike' 13 (7 outside, all titles) against 33 hikes, 'climbed' 1, 'paddle' 7, and 'sup' 12 hits of which 1 is a title, 9 are write-ups containing 'super' and 2 are paddle write-ups saying 'sup'. The placeholder promises 'activity' (trips.py:128) and the status row (trips.js:65) reads e.g. '9 OF 167 REPORTS' as if that were the answer.

**Evidence.** `tools/sitegen/search.py:47-65`; `assets/js/pages/explore.js:43-56`; `tools/sitegen/pages/trips.py:128`; `_site/trips/search.json (167 entries, hit counts measured with a stdlib script)`; https://esichak.github.io/personal-website/trips/search.json (same 167 entries, 43 with k == 'backcountry ski'); `tests/test_search.py:199-214`; `docs/CONTENT_GUIDE.md:383-416`.

**Proposal.** Add one table to search.py, ACTIVITY_WORDS keyed by activity key plus SUBTYPE_WORDS keyed by the Other sub-type, holding the longest forms so that the existing prefix/substring match covers the short ones: ski -> 'skiing skied skis skimo skinning touring'; mtb -> 'mountain biking bikes rides riding mtb cycling'; hike -> 'hiking hikes hiked'; climb -> 'climbing climbs climbed'; SUP -> 'paddleboarding paddleboards paddling sup standup'; Rafting -> 'rafting rafts' (Kayaking, Mountaineering alike). entry() appends them to 'k' after the label, before aliases and peaks. Nothing in JavaScript changes: 'ski', 'skiing', 'skied', 'tour', 'touring', 'bike', 'biking', 'ride', 'mtb', 'hike', 'climb', 'sup', 'paddle' all reach the activity's reports at keyword score (2), above write-up hits (1). Like search_aliases the words are searched, never shown (CONTENT_GUIDE.md:415). Update tests/test_search.py:199-214, which pin 'k' to the bare label, docs/DEVELOPING.md:280-283 (the 'k' contract) and CONTENT_GUIDE.md section 6. Measured cost of the expansion: search.json 67,718 -> about 76,200 B raw, 17,196 -> 17,418 B gzip.

**Files.** `tools/sitegen/search.py`, `tests/test_search.py`, `docs/DEVELOPING.md`, `docs/CONTENT_GUIDE.md`.

**Effort.** S. Visitor value 3.3, author value 1, confidence high.

**Risk.** Category words are a claim about what the activity is called, not a fact about a trip, so keep the list to inflections and the sport's common names (no 'splitboard' on every ski report, no 'rock' on every climb) and let Eric read it. 'Best match' ties every report of one activity at score 2, which is how 'ski' behaves today. A climbing report whose write-up mentions skiing still appears, last.

**Decision for Eric.** The word list itself: which names he and his partners actually type (skimo, skinning, cycling, standup) and whether 'sup' belongs beside 'paddleboarding'.

**Review note (condensed; the observation and proposal above are the revised text).** Reproduced: search.py:53-62 writes only the activity label (plus Other sub-type) into 'k' before aliases and peaks; explore.js:44-47 needs every token as a substring of t+p+k+x.

#### gap3-02. Match typed words at word starts, not inside words

**Observation.** explore.js match() (46), score() (51-53) and snippet() (64), trips.js dayHits (41) and the write-up-only test (334), and ticklist.js matches() (37) all use indexOf, so a token hits anywhere inside a word. Measured over search.json: 'ice' 16 hits of which 15 are inside 'nice', 'practice', 'price', 'office', 'noticed', 'sliced', 'choice' (word-start: 1); 'ice climbing' 4 hits, none containing the word ice (word-start: 0); 'tal' 26 (word-start 20: Tallac kept, 'total', 'mental', 'brutal' dropped); 'win' 15 -> 10; 'fall' 6 -> 5 ('snowfall'); 'rain' 8 -> 6 ('terrain', 'training'). The harnesses pin 'matter' -> Matterhorn (trips_js_harness.js:160), 'for' -> 'ford' (:259) and 'coul' (ticklist_js_harness.js:415) as 'substring'; all three are prefixes, so word-start matching keeps every pinned case.

**Evidence.** `assets/js/pages/explore.js:43-71`; `assets/js/pages/trips.js:41`; `assets/js/pages/trips.js:334`; `assets/js/pages/ticklist.js:37`; `tests/trips_js_harness.js:158-170`; `tests/trips_js_harness.js:259`; `tests/ticklist_js_harness.js:415`; `_site/trips/search.json (substring vs word-start counts measured with a stdlib script)`.

**Proposal.** Add has(field, tok) to explore.js: (' ' + field).indexOf(' ' + tok) !== -1, and use it in match(), score(), snippet() (its per-word loop becomes w.indexOf(tok) === 0), trips.js dayHits (title and text at line 41) and the write-up-only check (334), and ticklist.js matches() over data-text. Index files unchanged. Harness cases: 'ice' must not hit 'practice', 'tal' still hits 'tallac', 'for' still hits 'ford'; ticklist harness 'coul' unchanged. Reword DEVELOPING.md's explorer contract and CONTENT_GUIDE.md:395 ('Every word typed has to appear somewhere' -> 'has to start a word'). Does not remove prefix noise such as 'sup' -> 'super' (gap3-01 ranks the paddle trips first) or 'mount' -> 'mountain biking' (61 rides; title hits still rank above).

**Files.** `assets/js/pages/explore.js`, `assets/js/pages/trips.js`, `assets/js/pages/ticklist.js`, `tests/trips_js_harness.js`, `tests/ticklist_js_harness.js`, `docs/DEVELOPING.md`, `docs/CONTENT_GUIDE.md`.

**Effort.** S. Visitor value 3, author value 1, confidence high.

**Risk.** A visitor who types the end of a word ('horn' for Matterhorn) loses that hit; mid-word hits were never promised by any label. The tick list shares the predicate, so its one-goal search changes the same way.

**Review note (condensed; the observation and proposal above are the revised text).** Reproduced every predicate: explore.js:46 (match), :51-53 (score), :64 (snippet) use indexOf; trips.js:41 (dayHits title/text) and :334 (bodyOnly) use indexOf; ticklist.js:37 matches() uses indexOf.

#### gap3-03. Index each trip's year, month names and ski season

**Observation.** search.entry() (search.py:47-65) indexes no date word although the date is content (content.py:557 reads date and end_date, :615 derives t['season'] via season_of at :539-545) and is already printed on every card. Measured over search.json: '2024' 1 hit (the PCT title), '2025' 0, 'june' 1 (the place 'June Lake Loop'), 'july' 0, 'september' 0. The ski page's season band shows '2025-26 season' with '22 REPORTS', then 2024-25, 2023-24, 2022-23 (_site/ski/index.html), yet that label typed into the Trips box normalizes to '2025 26' and finds nothing. The Year select exists, but the box is where a visitor types 'june 2025 tallac'.

**Evidence.** `tools/sitegen/search.py:47-65`; `tools/lib/content.py:539-545`; `tools/lib/content.py:558`; `tools/lib/content.py:615`; `_site/ski/index.html (season band labels)`; `docs/DEVELOPING.md:75-80`; `_site/trips/search.json (hit counts measured)`.

**Proposal.** In search.entry() append to 'k' the words derived from the trip's own date: the year (both years when date and end_date differ) and the full English month name of every month in date..end_date (a tuple of full names in search.py; 'jun' then prefixes 'june'). No day-of-month for trips (a bare digit prefixes every year) and no ski-season tokens (the season's second half is a bare two-digit number; the Year select and the month words cover it). DEVELOPING.md:75-80 forbids invented publication dates, not the trip's displayed date; say so in the rule. Appending to 'k' needs no JavaScript. Measured cost with one year and month per entry: about +1.7 KB raw, +35 B gzip. Tests: test_search.py entry tests (the 'k' pins at :199-214); CONTENT_GUIDE.md section 6 list. Effort S.

**Files.** `tools/sitegen/search.py`, `tests/test_search.py`, `docs/DEVELOPING.md`, `docs/CONTENT_GUIDE.md`.

**Effort.** S. Visitor value 3, author value 1, confidence high.

**Risk.** 'may' is also prose ('may' in write-ups); the keyword hit ranks above those. '2024' then finds what the Year select finds: the two overlap, which is fine. This is the typed vocabulary, not a Month filter control (ia-06, features-02, benchmark-01 cover that).

**Decision for Eric.** Whether to add season words (winter, spring, summer, fall) under a stated month convention. His write-ups call May ski days 'spring' ('spring conditions', 3 write-up hits today) and no report says 'winter'; default proposed: no season words, only the ski season label.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: search.entry() (search.py:47-65) indexes no date word; content.py:558 reads date/end_date and :615 derives season; re-measured '2024' 1, '2025' 0, 'june' 1, 'july' 0, 'september' 0. The trip's date is content already printed on every card, so DEVELOPING.md:75-80 (no invented publication dates) is not broken. Reproduced: search.entry() (47-65) indexes no date word; content.py reads date/end_date at line 557 (not 558) and derives t['season'] at 615; season_of at 539-545. Measured: '2024' 1 hit (PCT title), '2025' 0, 'june' 1 (the place 'June Lake Loop' on mount-wood), 'july' 0, 'september' 0, '2025 26' 0. _site/ski/index.html carries '2025-26 season' with '22 REPORTS' plus 2024-25, 2023-24, 2022-23 segments.

#### gap3-07. Index the route shape words (loop, out and back)

**Observation.** content.py:559 reads route_shape and core.trip_tags (core.py:373-374) shows it as a tag on cards and title rows (list rows carry it in the meta line); the front matter holds 71 'loop', 73 'out-and-back' and 15 'point-to-point' (14 published; the planned route is the 15th). search.entry() (search.py:47-65) leaves it out, so 'loop' finds 11 (8 titles with Loop, the place 'June Lake Loop', 2 write-ups) of 71 loops, 'out and back' finds 22 reports that happen to contain the three substrings (15 at word start; never all three outside a write-up), and 'point to point' finds 1, in a write-up.

**Evidence.** `tools/lib/content.py:559`; `tools/sitegen/search.py:47-65`; `content/trips/*/index.md (route_shape counts by grep)`; `assets/js/pages/explore.js:13`; `_site/trips/search.json (hit counts measured)`.

**Proposal.** Append normalize(route_shape) to 'k' ('loop', 'out and back', 'point to point'); 'loop' then finds all 71 loops at keyword score and 'out and back' ranks the 73 out-and-backs first under Best match. No change to tokens() or to explore.js. Tests: test_search.py entry tests (the 'k' pins at :199-214); CONTENT_GUIDE.md section 6 list; DEVELOPING.md:280-283 'k' contract. Effort S.

**Files.** `tools/sitegen/search.py`, `tests/test_search.py`, `docs/CONTENT_GUIDE.md`, `assets/js/pages/explore.js`, `tests/trips_js_harness.js`.

**Effort.** S. Visitor value 2.3, author value 1, confidence high.

**Risk.** Stop words change what 'the' alone does (filters nothing instead of 'every write-up with the'): harmless, but the tick list shares tokens(). The shape is content, not derived.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: content.py:559 reads route_shape; front matter holds 71 loop, 73 out-and-back, 15 point-to-point; 'loop' finds 11 today ('out and back' finds 22 under substring, 15 under word-start; 'point to point' 1, a write-up). Appending the shape to 'k' is content already shown as a tag, stdlib, S, no JS. Reproduced: content.py:559 reads route_shape; core.trip_tags (core.py:362-375, SHAPE at :358) shows it as a tag on title chip rows and list rows carry it in the meta line; front matter counts are 71 loop, 73 out-and-back, 15 point-to-point (one of the 15 is the planned route crystal-range-to-bayview, so 14 published); search.entry() leaves it out.

#### gap3-04. Let a journal day be found by its date

**Observation.** search.day_entry() (search.py:73-94) carries the day's date only as display text 'w' ('May 22, 2024'); trips.js dayHits (26-52) matches tokens on the day title 't', the write-up 'x' and the name 'day N' only, with the journal's words riding along. So 'june 2024', 'may 22' or 'pct june' list no PCT day, although journal.json holds 150 days across April (10), May (31), June (30), July (31), August (30) and September (18) 2024 and the journal page itself is indexed by month (series.py:235-255).

**Evidence.** `tools/sitegen/search.py:73-94`; `assets/js/pages/trips.js:26-52`; `assets/js/pages/trips.js:70-73`; `_site/trips/journal.json (150 entries; months counted from 'w')`; `tests/trips_js_harness.js:225-262`; `docs/DEVELOPING.md:326-335`.

**Proposal.** Add a 'd' field to day_entry: normalize of the full month name and day of month only ('may 22'), never the year, because dayHits (trips.js:43-44) treats a token found both in a day's own field and in 'q' as neither own nor riding, so a year in 'd' would let '2024' alone list all 150 days. Put the journal's year(s) into 'q' (for the PCT it is already there: q = 'pacific crest trail 2024 pct'), so '2024' alone finds the journal among the reports and no day. In dayHits treat a word-start hit in 'd' as the day's own (own = true, +1, below a title hit's 3). 'june 2024' then lists the 30 June days (five, then the existing 'Show all 30 journal days' button, trips.js:70-73); 'may 22' finds Day 31; 'pct june' works because 'pct' rides along (trips.js:38-47). journal.json (94,751 B today) grows about 2-3 KB raw. Harness: give the DAYS fixture (trips_js_harness.js:229-235) a 'd' and add cases including '2024' alone -> []; test_search.py day-entry contract; DEVELOPING.md:328-340 and CONTENT_GUIDE.md:425-446 list the day fields (CONTENT_GUIDE:439 'The place and the date are not searched' changes).

**Files.** `tools/sitegen/search.py`, `assets/js/pages/trips.js`, `tests/trips_js_harness.js`, `tests/test_search.py`, `docs/DEVELOPING.md`, `docs/CONTENT_GUIDE.md`.

**Effort.** M. Visitor value 2, author value 1, confidence high.

**Risk.** Day-of-month is safe here because every token must hit the same day. A month word that is also prose ('may') ranks a date hit and a write-up hit alike at +1; title hits stay above both.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: day_entry (search.py:73-94) carries the date only as display text 'w'; dayHits (trips.js:26-52) matches title, write-up and 'day N'; journal.json has 150 days (Apr 10, May 31, Jun 30, Jul 31, Aug 30, Sep 18). Observation reproduces: day_entry (search.py:73-94) writes the date only as display text 'w' (abbreviated, e.g. 'Apr 22, 2024'); dayHits (trips.js:26-52) matches on t, x and the 'day N' name, journal words at :42 only ride along; journal.json has 150 days: Apr 10, May 31, Jun 30, Jul 31, Aug 30, Sep 18 (2024); series.py:235-255 builds the month index; DAYS_SHOWN at trips.js:70-73.

#### gap3-05. Make the placeholder and description say what is searched

**Observation.** trips.py:127-128 writes the label 'Search trips' and the placeholder 'Search by name, place, region, activity or peak'; the page description (trips.py:188) adds 'write-up'; CONTENT_GUIDE.md:386-394 lists title, place and region, activity, peaks, write-ups and aliases. The write-ups are the largest field (the 'x' field sums to 23.2 KB of search.json's 67.7 KB) and 92 of 167 reports have one, but nothing on the page tells a visitor they can type words from them: 'spring' (3 hits), 'skied' (6) and 'super' (9) are found only in write-ups today, and 'powder' (3 'Powderhouse' titles + 1 write-up) and 'corn' (2 'Corner' titles + 2 write-ups) reach the real snow words only through write-ups. 'activity' is promised although only the label form works (gap3-01).

**Evidence.** `tools/sitegen/pages/trips.py:127-128`; `tools/sitegen/pages/trips.py:188`; https://esichak.github.io/personal-website/trips/ (live placeholder, identical); `docs/CONTENT_GUIDE.md:383-399`; `tests/test_a11y_static.py:3630-3634`; `_site/trips/search.json (field sizes measured)`.

**Proposal.** One sentence in one constant in trips.py, used by the placeholder and the description, true after gap3-01 and gap3-03: 'Search titles, places, peaks, activities, dates or write-ups' (write-ups last, since the ellipsis rule pinned at test_a11y_static.py:3630 cuts the placeholder on narrow boxes). Keep the sr label 'Search trips' and the noscript note (trips.py:136-137). Align CONTENT_GUIDE.md section 6's list with the same words; test_trips_page.py pins the new text.

**Files.** `tools/sitegen/pages/trips.py`, `tests/test_trips_page.py`, `docs/CONTENT_GUIDE.md`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Risk.** UI text only; no fact about a trip. A placeholder is not a label, so the sr label stays as the accessible name.

**Review note (condensed; the observation and proposal above are the revised text).** Reproduced: trips.py:127-128 label and placeholder; :188 description adds 'write-up'; the live page carries the identical placeholder; CONTENT_GUIDE.md:386-394 lists the fields; test_a11y_static.py:3630-3637 pins the ellipsis; 92 of 167 entries have an 'x'; 'x' sums to 23,187 B of 67,718 B (23.2 KB, not 23.5).

#### qa-07. Zero results should offer the nearest working query

**Observation.** `trips/?q=tallac&activity=climb` shows '0 OF 167 REPORTS' and 'No trips match these filters. · Clear filters' although `tallac` alone matches 16 reports and climbing alone 13; the only exit is to clear everything. (Drop the kennedy meadows sentence: with a journal hit the empty box is already hidden, trips.js:390, and the status line links the day.) Proposal: in trips.js, when a run yields 0 reports and no journal days, re-run the match once without the facet filters and once without the query, and render the non-zero counts as buttons in the empty box: '16 reports match ‘tallac’ in all activities' and '13 climbing reports without the search'; each applies that state through explore.js historyStep. Mirror in ticklist.js for its filter + search zero state. Cover in tests/trips_js_harness.js and tests/ticklist_js_harness.js. Files unchanged.

**Evidence.** `evaluate_script on https://esichak.github.io/personal-website/trips/?q=tallac&activity=climb (status, emptyText)`; `.cache/plan2/qa/d-trips-q-tallac.png (16 OF 167 for the query alone)`; `.cache/plan2/qa/d-trips-kennedy.png`; `tools/sitegen/pages/trips.py:145-154 (status row and empty state)`; `tools/sitegen/pages/trips.py status() (#trx-none markup)`; `assets/js/pages/trips.js:319-380 (render: k === 0 shows the one box)`; `_site/trips/index.html ("No trips match these filters.")`.

**Proposal.** in trips.js `render()`, when `k === 0`, run `facetOk`/`match` once more without the facet filters and once without the query, and when either count is non-zero add a button to `#trx-none` built from the live counts: "16 reports match ‘tallac’ in all activities" and "13 climbing reports without the search" (facet names from the existing chip labels in explore.js); each applies that state through the existing `historyStep` path, and the box keeps 'Clear filters'. When journal days matched, replace the box's sentence with "No reports, N journal days below" linking to `#trx-days`. Leave trips.py's no-JS markup as it is. Cover in tests/trips_js_harness.js (zero with query + facet, zero with journal hits). Files: assets/js/pages/trips.js, tests/trips_js_harness.js. Effort S-M. Risk: copy is built from live counts only; the no-JS state is unchanged.

**Files.** `assets/js/pages/trips.js`, `assets/js/pages/explore.js`, `assets/js/pages/ticklist.js`, `tools/sitegen/pages/trips.py`, `tests/trips_js_harness.js`, `tests/ticklist_js_harness.js`.

**Effort.** M. Visitor value 3, author value 1, confidence high.

**Also covers.** ia-17 (merged into this finding).

**Risk.** Copy is built from live counts only, never invented; keep the no-JS state unchanged.

**Review note (condensed; the observation and proposal above are the revised text).** Half true. The tallac+climb case holds: tools/sitegen/pages/trips.py:152-153 ships one box ('No trips match these filters.' + Clear filters) and trips.js render (319-390) only shows or hides it; nothing suggests a relaxed query. The dead end is real: trips.py:152-153 renders one box with only 'Clear filters', and trips.js:319-380 computes counts from the live match, so the suggested buttons can be built from facts only. The tallac part reproduces: _site/trips/search.json has 167 entries, 16 containing 'tallac', none of them climbing, 13 climbing in all; .cache/plan2/qa/d-trips-q-tallac.png shows '16 OF 167 REPORTS'; trips.py:145-154 status() holds the `#trx-none` box with 'No trips match these filters.' and 'Clear filters'; trips.js:319-390 render().

#### perf-08. Fetch the search indexes when the box is focused, not on the first keystroke

**Observation.** `trips.js` requests `search.json` and `journal.json` only when a query has at least one token (`mayLoad`, trips.js:133-136; `ask()`, 424-430; `loadIndex`/`loadDays`, 208-236). The two files are 17,435 and 19,398 bytes gzipped on the live site, so the first results of any search wait for two round trips plus about 37 KB on the network, after the visitor has already started typing; on the phone profile's Slow 4G that is on the order of a second with the box showing no results.

**Evidence.** `assets/js/pages/trips.js:133-136`; `assets/js/pages/trips.js:208-236`; `assets/js/pages/trips.js:424-430`; https://esichak.github.io/personal-website/trips/search.json (17,435 bytes gzipped); `_site/trips/journal.json (19,398 bytes gzipped)`.

**Proposal.** Add a `warm()` in trips.js that calls `loadIndex` and `loadDays` once when the search box receives `focus` or the form a `pointerdown`/`touchstart` (passive listeners), reusing the existing `indexState`/`daysState` guards so a request is never duplicated and the failure path (`failedFor`) is unchanged; pass a flag (or test `tokens(state.q).length`) so the warm path does not call `message(LOADING)` (trips.js:210) before the visitor has typed. Keep the first-token rule for pages that open with `?q=`. Extend `tests/trips_js_harness.js` with a focus-before-typing case that asserts one fetch per index and no status message. Visitors who only browse the cards still download nothing. Effort S.

**Files.** `assets/js/pages/trips.js`, `tests/trips_js_harness.js`, `tests/test_trips_js.py`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Risk.** A focus from the header's `trips/#search` link would fetch for visitors who then do not type; that is 37 KB at most, on a page whose purpose is search. Nothing changes without JavaScript.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible, specific, S, and on the one page whose purpose is search: `mayLoad` (trips.js:133-136) and `ask()` (424-430) confirm nothing is fetched until a token exists, and the Node harness already counts fetches (tests/trips_js_harness.js:875), so the test is cheap.

#### ia-02. Make the header's Search a real search box that lands on the explorer

**Observation.** The header's Search is a link to trips/#search (tools/sitegen/core.py:1650; trips.js:499-507 focuses the box after the page loads). Apart from trips/ and the tick list's own goal search (#tkl-q), no page has a search field: not the 404, the Map page or the region pages. trips.js already reads `q` from the query string on load (KEYS, trips.js:12-16) and the explorer's form submits to itself (action="", trips.py:126), so a plain GET form from any page would arrive with results.

**Evidence.** `tools/sitegen/core.py:1650 (nav-search link to trips/#search)`; `assets/js/pages/trips.js:12-16 (KEYS include q; parseState)`; `docs/DEVELOPING.md:288 (URL state keys, q first)`; `assets/css/base.css:178 (.nav .nav-search hidden without scripting)`.

**Proposal.** In core.header (tools/sitegen/core.py:1650) replace the desktop Search link with `<form class="nav-search" role="search" action="<core.link(here, 'trips/')>" method="get"><label class="sr" for="nav-q">Search trips</label><input id="nav-q" name="q" type="search" placeholder="Search" maxlength="200" autocomplete="off"><input type="hidden" name="sort" value="relevance"><button type="submit" aria-label="Search">icon</button></form>`; the hidden sort is needed because trips.js keeps a URL's sort and only flips to Best match for text typed into the page's own box (trips.js:125; harness tests/trips_js_harness.js:777-779), and clearing the box afterwards falls back to Newest through clearedSort (trips.js:142). Replace the menu's existing Search row (core.py:1663) with the same form (ids must differ: nav-q / menu-q). Keep the `.nav-search` class so base.css:178 still hides it under (scripting: none). On trips/ itself keep today's link (the page has its own box). Style: 36 px input of about 160 px that widens on focus, 44 px submit target; the header fits at 1140 px (brand + five links + 160 px box + units is under the 1092 px row). No base.js change. Update tests/test_nav.py:72, 111, 132 (link text assertions become form assertions, action relative via core.link), tests/test_a11y_static.py:2317-2330, 2408, 2441 (a.nav-search → form.nav-search; label present), and docs/DEVELOPING.md:399-400. Never echo q into HTML. Effort: M.

**Files.** `tools/sitegen/core.py`, `assets/css/base.css`, `assets/js/base.js`, `tests/test_nav.py`, `tests/test_a11y_static.py`.

**Effort.** M. Visitor value 3.3, author value 1, confidence high.

**Risk.** Submitting from a sub-page lands on trips/?q=… where trips.js sets sort to Best match (trips.js:125, 136): expected. Query values must go through URL encoding by the browser only; never echo q into HTML. Header width as in ia-01.

**Review note (condensed; the observation and proposal above are the revised text).** Not built; one detail of the observation is wrong. Verified: core.header builds the Search as '<a class="nav-search" href="trips/#search">' and the phone menu's Site column has the same link; trips.js KEYS include q and parseState reads it; the explorer form has action=""; base.css:178 hides .nav .nav-search under (scripting: none); _site/404.html and _site/map/index.html link trips/#search. Feasible and useful (a plain GET form needs no new script and lands on the existing explorer), but two facts are wrong and the effort is understated. Mostly reproduces: the Search link is core.py:1650 (not 1651), trips.js:12-16 holds KEYS with q, the explorer form is action="" (trips.py:126), base.css:178 hides .nav .nav-search without scripting, and trips.js:499-507 focuses the box for #search.

#### seo-14. A search box and a slug-based suggestion on the 404 page

**Observation.** The 404 page (served with status 404 for any missing path, checked live today) offers the home button, the five activity rows, Trips and Map (notfound.py:23-45); a visitor arriving from an old or mistyped trip link has no way to search from it. trips/?q= is a real URL the explorer reads (trips.js:13; the box is name="q", trips.py:128).

**Evidence.** `tools/sitegen/pages/notfound.py:23-45`; `assets/js/pages/notfound.js:1-16`; https://esichak.github.io/personal-website/trips/does-not-exist/ (404); `assets/js/pages/trips.js:13`; `tools/sitegen/pages/trips.py:128`; `_site/404.html`; https://esichak.github.io/personal-website/no-such-page/ (HTTP 404, H1 "Off route"); `tools/sitegen/pages/notfound.py:22-45 (links offered)`; `assets/js/pages/notfound.js:1-16 (fragment fix only)`; https://esichak.github.io/personal-website/trips/no-such-trip/deeper/; https://esichak.github.io/personal-website/Trips/; `tools/sitegen/pages/notfound.py:14-48`; `assets/js/pages/notfound.js:1-16`; `tools/sitegen/sitecheck.py:242-279`.

**Proposal.** Add to the 404 body a <form role="search" action="trips/" method="get"> with a 48 px name="q" box and a button (the existing <base> resolves it). notfound.js, when location.pathname contains /trips/<slug>/, prefills the box with the slug's words (hyphens to spaces) and shows 'Looking for "<words>"?' above it; the words come from the URL only, never from a guess at a trip. Keep noindex. Without JavaScript the form still submits to trips/, which lists every report with the browse links.

**Files.** `tools/sitegen/pages/notfound.py`, `assets/js/pages/notfound.js`, `assets/css/pages/notfound.css`, `tests/test_notfound_page.py`.

**Effort.** S. Visitor value 3, author value 1, confidence high.

**Also covers.** ia-03, resilience-05 (merged into this finding).

**Risk.** None; the suggestion is built from the URL, not from content.

**Review note.** Kept as written by all three skeptics.

#### ia-08. More like this prefers the same place or a shared name before the region

**Observation.** core.related ranks same region+activity, then region, then activity, nearest date first (core.py:1299-1322). On mount-tallac-2026-02-15 the three cards are 'Powderhouse lap before work' twice (two trips share the title) and 'Return to Emerald Chute', while five other ski tours named for Tallac exist (back-at-tallac, back-at-tallac-with-connor, bee-positive-5k-warm-up-tallac-tour, first-tallac-lap, tallac-cathedral-bowl-solo) and nine Tallac hikes; 13 of the 15 trips with 'tallac' in the title have no `place:`, so the shared fact is the title word. With 87 Lake Tahoe trips, nearest-in-date rarely means the same mountain.

**Evidence.** `tools/sitegen/core.py:1299-1322 (related tiers)`; `_site/trips/tallac-2026-09-24/index.html and _site/trips/mount-tallac-2026-02-15/index.html (rep-related cards)`; `content/trips/*/index.md grep: 15 titles contain tallac, 2 have place: Mount Tallac`; `tools/sitegen/core.py:1299-1337`; `_site/trips/back-to-clipless/index.html`; `phone-bare-ride.jpeg`; `desktop-bare-ride.jpeg`; `content/trips/back-to-clipless/index.md:7`.

**Proposal.** Add tier 0 in core.related (core.py:1299-1322): a candidate with the same activity that shares t's `place` (case-folded) or a `map.peaks` name, or whose title shares a word that is itself a word of some `place:` or `map.peaks` value anywhere in site['published'] (after search.normalize, five letters or more, so 'tallac' qualifies through place: Mount Tallac while 'south', 'season', 'sunrise' never do); nearest date within the tier as now. search.py imports only markdown (tools/sitegen/search.py:11-19), so core may import it without a cycle. related_block's meta line becomes 'SAME PLACE OR NAME AND ACTIVITY, THEN REGION AND ACTIVITY, THEN REGION, THEN ACTIVITY · NEAREST IN DATE'. Cases in tests/test_related.py (same place wins; a common title word does not pair; a different activity does not enter tier 0) and the meta-line assertions in tests/test_report_page.py. Effort M.

**Files.** `tools/sitegen/core.py`, `tests/test_related.py`, `tests/test_report_page.py`.

**Effort.** M. Visitor value 3.3, author value 1, confidence high.

**Also covers.** report-09 (merged into this finding).

**Risk.** Title-word matching can pair unrelated trips on a common word; the stop list and the five-letter floor limit it, and the rule stays stated in the meta line. Uses only titles, places and peaks from content.

**Review note (condensed; the observation and proposal above are the revised text).** Not built, but the counts and one evidence path are wrong. The observation holds (rel-powderhouse-lap-before-work-2026-02-13, rel-powderhouse-lap-before-work and rel-return-to-emerald-chute are the three cards in _site/trips/mount-tallac-2026-02-15/index.html; 15 titles contain 'tallac', 2 carry place: Mount Tallac) and a tier 0 is cheap. Core observation reproduces: core.py:1299-1322 ranks same region+activity, then region, then activity, nearest date; _site/trips/mount-tallac-2026-02-15/index.html's More like this is powderhouse-lap-before-work-2026-02-13, powderhouse-lap-before-work and return-to-emerald-chute; 87 index.md files carry region: Lake Tahoe.

#### ia-06. Add a Month filter to the explorer so time of year is findable

**Observation.** A visitor looking for 'ski tours near Tahoe in spring' can filter activity, region, year, format and write-up, but nothing answers a month: the ski page groups by season label ('2025-26', content.py:539-545), the search index holds no dates, and a search for 'spring' finds only the three write-ups that happen to use the word (hot springs, 'before spring', 'spring conditions'), none by season. Every trip has a `date:`; the 51 ski reports fall in Dec-May (Jan 10, Feb 19, Mar 10, Apr 10, May 1, Dec 1). The tick list already has a Month select for target months (ticklist.py:116).

**Evidence.** `tools/sitegen/pages/trips.py controls() (Region, Year, Format selects only)`; `assets/js/pages/trips.js:76-83 (facetOk: activity, region, year, format, writeup)`; `tools/lib/content.py:539-545 (season_of: ski seasons by July split)`; `_site/trips/search.json (no month or season words; 'spring' matches no entry)`; `_site/tick-list/index.html (Month select present)`; `assets/js/pages/trips.js:12-13`; `assets/js/pages/trips.js:153`; `tools/sitegen/core.py:1258-1295 (trip_card data-* line)`; `tools/sitegen/pages/trips.py:104-142 (form, select())`; `content/trips/*/index.md date: lines (grep 2026-10-13)`; https://stephabegg.com/trip-reports/chronology/; https://www.14ers.com/php14ers/tripmain.php; https://turns-all-year.com/trip-reports; `tools/sitegen/pages/trips.py:104-142`; `assets/js/pages/trips.js:12-14`; `assets/js/pages/trips.js:76-82`; `tools/sitegen/core.py:1282-1285`.

**Proposal.** core.trip_card: add `data-month="MM"` from t['date'] ('' when undated). trips.py controls(): a Month select (Any month, January … December, values 01-12) after Year. trips.js: add `month` to DEFAULTS/KEYS/LABELS (:12-14), FACETS (:153), allowed/names from the select (:171-173), facetOk (`st.month && d.month !== st.month`); explore.js needs no change (its parseState/serialize/chipLabel are generic). URL key `month=03`; journal days unchanged. Document the key in docs/DEVELOPING.md:288 and add harness cases in tests/trips_js_harness.js plus tests/test_trips_page.py. Files: tools/sitegen/core.py, tools/sitegen/pages/trips.py, assets/js/pages/trips.js, tests/trips_js_harness.js, tests/test_trips_page.py, docs/DEVELOPING.md. Risk: months are facts from `date:`; do not add a derived season facet. parseState keeps only values the select offers, so the select and the card attribute must use the same two-digit strings.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/trips.py`, `assets/js/pages/trips.js`, `assets/js/pages/explore.js`, `tests/trips_js_harness.js`, `tests/test_trips_page.py`, `docs/DEVELOPING.md`.

**Effort.** M. Visitor value 3, author value 1, confidence high.

**Also covers.** features-02, benchmark-01 (merged into this finding).

**Risk.** Months are facts from `date:`; do not add a derived "season" facet (Winter/Spring is an interpretation). parseState whitelists keys, so both scripts must change together or the key is dropped from the address.

**Review note (condensed; the observation and proposal above are the revised text).** Not built, but one sentence of the observation is false. Feasible and a fact-only facet (month from `date:`, present on all 167 reports), and the exact pattern already exists for the tick list's Month select (tools/sitegen/pages/ticklist.py:15, 116; assets/js/pages/ticklist.js:8-11, 46, 56, 95-97), so M is honest. Mostly reproduces: trips.py:104-142 controls() has Region, Year, Format selects only; trips.js:76-83 facetOk checks activity, region, year, format, writeup; content.py:539-545 season_of; _site/ski/index.html groups by '2025-26'; ticklist.py:116 builds a Month select; every trip has date:; the 51 ski reports fall Jan 10, Feb 19, Mar 10, Apr 10, May 1, Dec 1.

#### ia-07. Sort the explorer by distance and gain, unknowns last

**Observation.** The explorer sorts newest, oldest and best match only; cards carry data-date for ordering. The Map table shows Dist, Gain and GPS max columns but cannot be sorted. The 2026-10-08 plan deferred distance and elevation sorting until unknowns are handled; most bulk-imported rides have stats but no write-up, so a stats sort is one of the few ways to find them.

**Evidence.** `tools/sitegen/pages/trips.py:17 (SORTS)`; `tools/sitegen/core.py:1285 (card data-* facets, no distance)`; `assets/js/pages/trips.js:319-380 (render sorts by score or date)`; `docs/personal-website-improvement-plan.md:275 (deferred sorting)`; `assets/js/pages/trips.js:338-340`; `docs/personal-website-improvement-plan.md:275`; `tools/sitegen/core.py:1258-1295`; `content/trips/*/index.md stats: blocks (157, grep 2026-10-13)`.

**Proposal.** core.trip_card: add `data-km` (one decimal) and `data-gain` (meters, integer) from t['stats'] when present. trips.py: SORTS gains ('longest', 'Longest first') and ('gain', 'Most gain'). trips.js render(): numeric sort descending, cards without the value after all others; the sorted section heading reads 'Longest first' / 'Most gain first' with a Mono-S meta 'MULTI-DAY AND SERIES BY THEIR TOTALS' and, when any card lacks the value, 'N WITHOUT A DISTANCE, LISTED LAST' (or GAIN). URL key `sort=longest|gain` (add to the allowed list, trips.js:171; harness list tests/trips_js_harness.js:106). Values only from `stats`; display stays through core.U. Harness cases and tests/test_trips_page.py for the options; docs/DEVELOPING.md:288 for the new sort values. Effort M.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/trips.py`, `assets/js/pages/trips.js`, `tests/trips_js_harness.js`, `tests/test_trips_page.py`, `docs/DEVELOPING.md`.

**Effort.** M. Visitor value 3, author value 1, confidence medium.

**Also covers.** features-03 (merged into this finding).

**Already known.** docs/personal-website-improvement-plan.md:275 (deferred idea)

**Risk.** A series and multi-day trips sort by their totals, which dwarf single days; say so in the heading meta ("totals") or sort them in their own tail. Values must come from `stats` only (core.U rule stays for display).

**Review note (condensed; the observation and proposal above are the revised text).** Feasible, specific and worth a session: the values exist as facts (`distance_km`, `gain_m` in tools/lib/content.py:501, 515, 523-527; 157 of 168 folders have a stats: block), the render already orders by a card's data-date (trips.js:338-340), and the 2026-10-08 plan only deferred it until unknowns are handled (docs/personal-website-improvement-plan.md:275), which the proposal does.

#### benchmark-02. Add a has-photos filter and photo counts to cards

**Observation.** 14ers.com marks each listed report with a GPX icon and offers Report Type and 'GPX?' filters; Stav's All Hikes page is 'every trip report in order, presented visually', a photo per card. Here 106 of 168 trip folders have photos (398 photos: entries, 246 on index.md files and 152 in day files), but cards carry only `data-writeup` as a media facet (core.py:1285-1287) and the one media filter is 'Has a write-up' (trips.py:132); a card's stats line (core.row_stats_line, core.py:1152-1166) never says that a report has photos or how many.

**Evidence.** https://www.14ers.com/php14ers/tripmain.php; https://stavislost.com/hikes/; `tools/sitegen/core.py:1282-1285`; `tools/sitegen/pages/trips.py:136`; `content/trips/*/photos (106 folders)`; `content/trips/*/index.md photos: blocks (398 entries, counted with the loader 2026-10-13)`; `tools/sitegen/core.py:1258-1295 (data-* facets)`; `tools/sitegen/core.py:811-843 (cover_img) via pages map §2`; `tools/sitegen/pages/trips.py:104-142`; `content/trips/*/photos/*.th.webp (208 files, pipeline map §8)`.

**Proposal.** In core.trip_card add `data-photos="N"` (len of t['photos'] plus the sum over t['days'] photos: t['photos'] is empty for every multi-day trip and the series, whose photos sit in the day files). In trips.py (controls, line 132) add a second checkbox 'Has photos' (name `photos`) beside 'Has a write-up'; trips.js: FACETS gains `photos` (line 153), `facetOk` requires `d.photos !== '0'` (lines 78-82), chipLabel 'Has photos', URL `?photos=1`. In core.row_stats_line append a Mono-S 'N PHOTOS' item when N > 0: that covers explorer and home cards and 'More like this' (trip_card, core.py:1278 and 1337) and the phone list row (.trow-ps, shown below 560 px, base.css:537); for list rows at 560 px and up add the same count to stats_cells (core.py:1189-1197, the .trow-stats grid) or state that rows carry it on phones only. Harness cases in tests/trips_js_harness.js and page tests in tests/test_trips_page.py.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/trips.py`, `assets/js/pages/trips.js`, `tests/trips_js_harness.js`, `tests/test_trips_page.py`.

**Effort.** S. Visitor value 3, author value 1, confidence high.

**Also covers.** features-09 (merged into this finding).

**Risk.** None to the rules; one more URL key.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible and S: the writeup facet it mirrors is a closed pattern in tools/sitegen/core.py:1282-1285 (data-writeup), tools/sitegen/pages/trips.py:136 (checkbox) and assets/js/pages/trips.js:12-14, 76-81, 121, 164, 178, 285, 473 (state key, facetOk, chip, URL). Observation reproduces: 106 of 168 trip folders have photos/ (find), 398 photos: entries (246 index-level + 152 in day files via content.load_all), 208 .th.webp files; trip_card writes data-writeup as the only media facet (core.py:1285-1287); row_stats_line (core.py:1152-1166) prints only distance/gain/pitches/moving, never a photo count; 14ers tripmain.php has a 'GPX?' checkbox and a 'Report Type' select, Stav's hikes page says 'Every trip report in order, presented visually'.

#### qa-05. Trips list view fetches 800 px photos for 200 px thumbnails

**Observation.** With `?view=list` each card keeps `sizes="(min-width: 1200px) 400px, (min-width: 560px) calc((100vw - 104px) / 2), 112px"`, so at 1280 px the 200×150 row thumbnail loads `01.sm.webp` (800 px, ~74 KB) although a 427 px `.th` copy (~25 KB) exists; the `.th` is offered only in the phone `<source>`. Across 167 rows that is roughly 12 MB instead of 4 MB on a full scroll.

**Evidence.** `evaluate_script on https://esichak.github.io/personal-website/trips/?view=list : currentSrc 01.sm.webp, rendered width 200, the sizes string above, DPR 1`; `tools/sitegen/core.py:783 (CARD_PHONE_SIZES, phone-only '.th' source), core.py:811 (cover_img)`; `assets/css/pages/trips.css:93-104 (list thumbnails 112/160/200 px)`.

**Proposal.** keep the main `srcset` as it is (the card view and cover_preload share _cover_srcset) and have core.cover_img emit `data-srcset-list` (the .th, .sm and full candidates) and `data-sizes-list="(min-width:1200px) 200px, (min-width:560px) 160px, 112px"` beside the current attributes; trips.js swaps both `img.srcset` and `img.sizes` when the view changes and at load when `view=list`, and restores them for the card view. Measure before/after with the method in docs/DEVELOPING.md:1428 and record it in the log. Files: tools/sitegen/core.py, assets/js/pages/trips.js, tests/trips_js_harness.js, tests/test_cover.py (or tests/test_trips_page.py) in place of the nonexistent tests/test_home_cards.py. Relates to known: IMPLEMENTATION_REPORT.md 15.4.12 (Hiking page 800 px files for 114 px thumbnails).

**Files.** `tools/sitegen/core.py`, `assets/js/pages/trips.js`, `tests/trips_js_harness.js`, `tests/test_cover.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Risk.** None; the card view is unchanged.

**Review note (condensed; the observation and proposal above are the revised text).** Observation verified in code: tools/sitegen/pages/trips.py:15 TRX_SIZES is the quoted string; core.py:796-808 _card_source offers the .th copy only in `<source media="(max-width: 559.98px)">` (CARD_PHONE_MEDIA core.py:778) and the `<img>` srcset is .sm + full (core.py:788-794); assets/js/pages/trips.js:287 only toggles the trx--list class; trips.css:93-101 sets the list thumbnails at 112/160/200 px. The waste is real: TRX_SIZES (tools/sitegen/pages/trips.py:15) ends in 400px at ≥1200 px while the list thumbnail is 200 px (trips.css:103), and the `.th` copy is offered only in the phone <source> (core.py:797-808); the Matterhorn cover's 01.th.webp is 21 KB against 73 KB for 01.sm.webp. Observation reproduces: _site/trips/index.html gives every card `sizes="(min-width: 1200px) 400px, (min-width: 560px) calc((100vw - 104px) / 2), 112px"` (106 cards) with the `.th` copy only in the phone `<source>` (`sizes="106px"`, core.py:796-808, CARD_PHONE_SIZES at core.py:783); _cover_srcset (core.py:786-793) offers only .sm and full; trips.css:93-104 sizes the list thumbnails 112/160/200 px; matterhorn 01.sm.webp is 800×600 at 73,508 bytes and 01.th.webp 427×320 at 21,326 bytes (~21 KB, not ~25 KB).

#### copy-03. Cut excerpts at a sentence end when one fits

**Observation.** markdown.plain(limit) cuts at the limit on a word boundary and appends '…' (markdown.py:109-117). core.card_summary rule 2 uses it at 180 characters for every written trip's explorer card and 230 for the home cards (core.py:1110-1127, home.py:119); report.py:651 uses core.excerpt at 155 for the meta description; build.py:232 at 400 for the feed. Measured over the 82 reports with a trip-level write-up: 39 card excerpts at 180 characters end mid-sentence, and 37 of those have a complete sentence ending between 60 and 180 characters. Example: the Matterhorn description ends '…Conditions + slope angle had me pretty…' and its explorer card '…had me pretty spooked at the top, but…'.

**Evidence.** `tools/lib/markdown.py:109-117`; `tools/sitegen/core.py:1110-1127`; `tools/sitegen/pages/report.py:652`; `_site/trips/matterhorn-peak-west-couloir/index.html (meta description)`; `_site/trips/index.html (tcard-ex paragraphs)`.

**Proposal.** Add markdown.plain_sentences(text, limit, floor=0.5): the longest prefix that ends at '.', '!' or '?' followed by a space or the end, when that prefix is at least floor×limit long; otherwise the current word cut. Use it in core.card_summary (rule 2), core.excerpt_parts, the report description and build.feed. The result is a verbatim prefix of Eric's text, never a rewrite. Unit tests for abbreviations and for texts shorter than the floor.

**Files.** `tools/lib/markdown.py`, `tools/sitegen/core.py`, `tools/sitegen/pages/report.py`, `tools/build.py`, `tests/`.

**Effort.** S. Visitor value 3, author value 1, confidence high.

**Risk.** Write-ups stay verbatim (a prefix is verbatim); do not touch markdown.to_html.

**Review note (condensed; the observation and proposal above are the revised text).** Reproduced: markdown.plain cuts at a word boundary and appends '…' (markdown.py:109-117); core.card_summary rule 2 at core.py:1120-1123 with limit 180, home.py:119 passes 230; the description uses core.excerpt(t, 155) at report.py:651 (not 652) and the feed core.excerpt(t, 400) at build.py:232 (not 231).

#### a11y-13. Distinguish repeated trip titles in link names

**Observation.** the explorer lists 'Tallac' four times, 'Mount Glory' three times, 'Ride near Day Valley' seven times and nine other titles twice; Home repeats 'Tallac' and 'Tahoe Mountain Loop'. Trip cards (core.trip_card, core.py:1288-1289) name the link by the title alone (aria-describedby carries the date, which a screen reader's links list does not show), so the rotor shows identical links to different pages; Lighthouse's informative identical-links-same-purpose item on home is this case. Section pages are already distinct: core.trip_row (core.py:1194-1197) labels the row link by title and meta line. The <title> element already appends the date when a title repeats (report.py:649-650).

**Evidence.** `_site/trips/index.html (repeated H3 titles: Tallac ×4, Mount Glory ×3, Back at Tallac ×2 …)`; `tools/sitegen/core.py:1288-1289`; `tools/sitegen/pages/report.py:649-650`; `.cache/plan2/lh-home/report.json (identical-links-same-purpose: li.tcard > div.tcard-b > h3.tcard-t > a)`.

**Proposal.** in core.trip_card accept a repeated set computed per page (titles seen more than once in that list) and, for those trips only, append '<span class="sr">, Sep 24, 2026</span>' inside the title link, using core.trip_date(t, short=True); keep aria-describedby for the rest. Compute the set in trips.results (trips.py:176), home.recent (home.py:160-163) and region.page (region.py:97) and pass it down. Files: tools/sitegen/core.py, tools/sitegen/pages/trips.py, tools/sitegen/pages/home.py, tools/sitegen/pages/region.py, tests/test_trips_page.py, tests/test_home.py.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/trips.py`, `tools/sitegen/pages/home.py`, `tools/sitegen/pages/section.py`, `tests/test_trips_page.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Risk.** The appended date is the trip's own date (facts-only); the sr span must stay out of trips.js's snippet rewriting (it only rewrites .tcard-ex).

**Review note (condensed; the observation and proposal above are the revised text).** Partly done. Confirmed on the built pages: _site/trips/index.html repeats 'Ride near Day Valley' x7, 'Tallac' x4, 'Mount Glory' x3 and nine titles x2 as tcard h3 links; home repeats 'Tallac' and 'Tahoe Mountain Loop'. core.trip_card names the link by the title alone and puts the date in aria-describedby (core.py:1288-1289), and report.py:649-650 already appends the date to <title> for a duplicate, so the date is the trip's own fact. Partly reproduces. _site/trips/index.html (167 cards): 'Tallac' ×4, 'Mount Glory' ×3, 'Ride near Day Valley' ×7 and nine other titles ×2 (more than the 'six other titles twice' stated); home: 'Tallac' ×2, 'Tahoe Mountain Loop' ×2. core.py:1288-1289 names the card link by the title with aria-describedby on the meta line; report.py:649-650 appends the date to <title> for a repeated title; trips.js:311-316 rewrites only .tcard-ex; .cache/plan2/lh-home/report.json lists the Tallac card link under identical-links-same-purpose (an informative audit, score 1, one item).

#### ia-04. One region count on Trips and Map: leave the journal's own region out

**Observation.** Trips says "167 REPORTS · 15 REGIONS" because regions_of counts every `region:` value, including "Pacific Crest Trail", the series' own region; Map says "14 REGIONS" from rendered/site/meta.json `all_regions`, which has no entry for a series (a series is on no region map). On Trips the browse row "Pacific Crest Trail, 1 report" and the Region select option both lead to `?region=pacific-crest-trail`, a JS-only filter of one card.

**Evidence.** `_site/trips/index.html (trx-stats "15 REGIONS"; browse list with "Pacific Crest Trail, 1 report")`; `_site/map/index.html (arc-stats "14 REGIONS"; 14 region-* ids)`; `tools/sitegen/pages/trips.py regions_of() and browse() (href falls back to ?region=slug)`; `rendered/site/meta.json all_regions (14 names)`; `content/trips/pacific-crest-trail-2024/index.md:9 (region: Pacific Crest Trail)`; `docs/IMPLEMENTATION_REPORT.md:826 (15.4.9)`.

**Proposal.** In trips.py regions_of(pub) skip regions whose trips are all `kind: series` (the series already has the Format filter 'Series', its ALSO item on Home and its card on Map), so the head, the browse list and the Region select all show the 14 regions Map shows. Old addresses: trips.js:171 takes the allowed region values from the select's options and parseState (explore.js:28) drops any other, so either add the cards' data-region values to allowed.region in trips.js (then the old link still filters to the one card, and chipLabel shows the slug unless names.region gets the label) or accept that trips/?region=pacific-crest-trail opens the unfiltered explorer; say which. Update tests/test_trips_page.py (lines 39, 318, 529, 995, 1014 expect the PCT region) and docs/DEVELOPING.md:398 (the `?region=` fallback no longer used by the PCT). Files: tools/sitegen/pages/trips.py, assets/js/pages/trips.js (if the old address is kept), tests/test_trips_page.py, docs/DEVELOPING.md. Risk: without the trips.js change a shared trips/?region=pacific-crest-trail link silently shows all reports.

**Files.** `tools/sitegen/pages/trips.py`, `tests/test_trips_page.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1.3, author value 1, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.4 point 9

**Risk.** A shared link to trips/?region=pacific-crest-trail keeps working through the data-region facet; the chip label for an unknown region value in trips.js chipLabel must still render.

**Review note (condensed; the observation and proposal above are the revised text).** Specific, S, low risk, and the inconsistency is real (content has 15 distinct region: values including one 'Pacific Crest Trail' on the series; rendered/site/meta.json all_regions has 14; the browse fallback is tools/sitegen/pages/trips.py:90) and already listed as known (docs/IMPLEMENTATION_REPORT.md:823, 15.4.9). Observation reproduces: _site/trips/index.html says '15 REGIONS' and lists 'Pacific Crest Trail, 1 report' with href ?region=pacific-crest-trail plus the select option; _site/map/index.html says '14 REGIONS' with 14 region-* ids; rendered/site/meta.json all_regions has 14 names; content/trips/pacific-crest-trail-2024/index.md:9 is region: Pacific Crest Trail; trips.py:32-42 regions_of counts every region, :90 falls back to ?region=.

#### visual-02. Hide the Trips browse block once the explorer's form is live

**Observation.** On the desktop capture (1440 px wide for a 1280 CSS px viewport) the first card begins about 793 capture px, roughly 705 CSS px, down the page: H1 and counts, three rows of browse links (BY ACTIVITY 5, BY REGION with all 15 regions, BY YEAR 6, as built in _site/trips/index.html), the 48 px search box (trips.css:24), two rows of chips and selects, and the status line. With scripting the browse links repeat the activity chips and the Region and Year selects that the inline script reveals (trips.py:104-142), so every facet is on screen twice before any trip. The phone version is known (IMPLEMENTATION_REPORT.md 15.4 point 8; WEBSITE_IMPLEMENTATION_LOG.md lines 217-218 on the 15 repeated regions).

**Evidence.** `desktop-trips.jpeg`; `tools/sitegen/pages/trips.py:77-95`; `tools/sitegen/pages/trips.py:104-142`; `tools/sitegen/pages/trips.py:187`; `assets/css/base.css:177-183`; `tests/test_trips_page.py:325`.

**Proposal.** add to trips.css `@media (scripting: enabled) { .p-trips nav.trx-browse { display: none; } }`, the twin of the `(scripting: none)` rules at base.css:177-183. The scope is required: `div.trx-browse` is also the 'Other regions' block on every region page (region.py:118) and tests/test_a11y_static.py:3511 pins its display there. The nav stays in the DOM, so the `#y-YYYY` targets (trips.py:177), the Node harness that follows `.trx-browse [href="#y-…"]` (tests/trips_js_harness.js:1186) and the tests that locate `nav.trx-browse` (tests/test_trips_page.py:325, test_build_site.py:1419 and 1467, test_region_page.py:3304) keep working. If Eric prefers the links visible, instead move `browse(site)` after `results(site)` in trips.py:187 as a 'Browse by' index at the foot of the list; those tests locate the nav, not its position.

**Files.** `assets/css/pages/trips.css`, `tools/sitegen/pages/trips.py`, `tests/test_trips_page.py`.

**Effort.** S. Visitor value 2.7, author value 1.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.4.8; docs/WEBSITE_IMPLEMENTATION_LOG.md Phase 2 'Remaining issues' (browse block repeats the 15 regions)

**Risk.** Browsers without the `scripting` media feature (before 2023) keep today's layout; without JavaScript nothing changes; region-page links into Trips carry `?region=` and are unaffected.

**Decision for Eric.** Hide the browse block with scripting, or move it under the results.

**Review note (condensed; the observation and proposal above are the revised text).** The observation is right: browse() (trips.py:77-95) lists the same activities, regions and years that controls() (trips.py:104-142) offers as chips and selects, and the known-issue citations check out (IMPLEMENTATION_REPORT.md 15.4 item 8; WEBSITE_IMPLEMENTATION_LOG.md:217). The `(scripting: none)` twin exists (base.css:177, region.css:29, about.css:40, report.css:179). Observation reproduces: the trips-top crop (offset 1; sips treats offset 0 0 as unset) shows H1, counts, BY ACTIVITY / BY REGION / BY YEAR rows, the search box, two control rows, the status line and the first card at about y=793 in the 1440-px-wide capture, which is roughly 705 CSS px at the capture's 1.125 ratio, not 795 CSS px.

#### phone-02. Tick list and Trips: secondary filters behind one Filters button on phones

**Observation.** On a phone the tick list shows the search box, the activity chips, Region/Status, Priority, Month + Has a route, the five scope buttons on two rows, then Sort and Cards|List before '1 OF 1 GOAL': seven rows of controls, about 640 CSS px, ahead of the one goal. Trips shows two rows of chips plus Region, Year, Format, Has a write-up, Sort and the view toggle on its second screen. The explorer form is shared (.trx-*), so both pages pay the same cost.

**Evidence.** `phone-ticklist.jpeg (crop: top)`; `phone-trips.jpeg (crop: s2)`; `tools/sitegen/pages/ticklist.py:146-147`; `tools/sitegen/pages/trips.py:104-142 (controls)`; `assets/css/pages/trips.css:29-45`; `assets/css/pages/ticklist.css:7-10`; https://stephabegg.com/trip-reports/chronology/; https://stavislost.com/trip-reports/; `docs/personal-website-improvement-plan.md section 8.2, items 25-26`; `docs/IMPLEMENTATION_REPORT.md:822`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:216-218`; `tools/sitegen/pages/trips.py:77-95`; `tools/sitegen/pages/trips.py:104-142`.

**Proposal.** Add a shared disclosure for the explorer forms: below 760 px the <select>s, the checkbox/switch and the Sort control move into <div class="trx-more" hidden> behind a 44 px .btn 'Filters' with aria-expanded and a count of active filters (trips.js:382-387 and ticklist.js:171-176 already compute the chips); the search box, the activity chips and, on the tick list, the scope radios stay visible. Wire the toggle in trips.js and ticklist.js (or one helper in base.js keyed on .trx-form); explore.js stays DOM-free (it is a pure-function Node module for the harnesses), so at most the 'how many filters are active' helper goes there. Remember open/closed per session (sessionStorage, as series.js:113-114 does). Markup in trips.py controls() and ticklist.py controls(); CSS in trips.css; extend tests/trips_js_harness.js and tests/ticklist_js_harness.js so URL state still sets the hidden fields.

**Files.** `assets/js/pages/explore.js`, `tools/sitegen/pages/trips.py`, `tools/sitegen/pages/ticklist.py`, `assets/css/pages/trips.css`, `tests/trips_js_harness.js`, `tests/ticklist_js_harness.js`.

**Effort.** M. Visitor value 2.3, author value 1.3, confidence high.

**Also covers.** benchmark-12 (merged into this finding).

**Risk.** Hidden controls must still be set from the address and announced when changed; keyboard order stays the DOM order; without JS the whole form is hidden already, so nothing regresses there.

**Review note (condensed; the observation and proposal above are the revised text).** Observation checks out: the tick list crop (phone-ticklist.jpeg (crop: top)) shows search, chips, Region/Status, Priority, Month + Has a route, five scope buttons on two rows, Sort and Cards|List before '1 OF 1 GOAL', and phone-trips-s2.jpeg shows Year/Format, Has a write-up/Sort and the toggle; both forms are built in trips.py controls() (104-142) and ticklist.py controls() (77-118) with the shared .trx-* CSS (trips.css:29-45, ticklist.css:7-10). Observation reproduces: finder-phone/crops/phone-ticklist-top.jpeg shows search, activity chips, Region/Status, Priority, Month + Has a route, the five scope radios on two rows (SCOPES, ticklist.py:18), then Sort and Cards|List before '1 OF 1 GOAL' (the count line sits about 660 CSS px from the page top); phone-trips-top/-s2.jpeg show the two chip rows plus Region on screen one and Year, Format, Has a write-up, Sort and the view toggle on screen two.

#### visual-05. Tick list: no filter apparatus until there are goals to filter

**Observation.** with one active goal the page shows a 48 px search box, a form of 10 buttons, 5 selects and the search input in two rows (All · Hiking, Region, Status, Priority, Month, Has a route (GPX); Active · Shortlisted · Completed · Archived · All, Sort, Cards | List) and '1 OF 1 GOAL' before the single card; `controls(site)` and `status_row(site)` are always built (ticklist.py:79, 120, 146). ticklist.js:71-76 returns when `#search` is absent, so leaving the form out is safe for the script.

**Evidence.** `desktop-ticklist.jpeg`; `tools/sitegen/pages/ticklist.py:79-110`; `tools/sitegen/pages/ticklist.py:146-147`; `assets/js/pages/ticklist.js:71-76`.

**Proposal.** add `FILTERS_FROM = 6` to ticklist.py: below it `build` emits head + results only (the head's 'N ACTIVE GOALS · N SHORTLISTED · N COMPLETED' line stays); at or above it, today's form and status row. Because `site['goals']` is every planned route including archived and completed ones (build.py:257) and `results()` lists them all, with the script's default Active scope hiding the rest on load, the form-less page must apply the active rule server-side (goals.py:303) or say that it lists every goal. Document the threshold in docs/TICK_LIST_GUIDE.md. The existing fixtures are already above it (tests/test_ticklist_page.py: seven non-draft goals; tests/test_ticklist_js.py SITE at 457-478: eight), and the Node harness reads the form's chips, scopes and menus (page_model, line 479), so keep both at or above the threshold and add one small below-threshold case to test_ticklist_page.py. Risk: below the threshold a `?status=` address does nothing.

**Files.** `tools/sitegen/pages/ticklist.py`, `tests/test_ticklist_page.py`, `tests/ticklist_js_harness.js`, `docs/TICK_LIST_GUIDE.md`.

**Effort.** S. Visitor value 2, author value 2, confidence high.

**Risk.** Below the threshold a `?status=` address does nothing; the Node harness assumes the form exists, so its fixture must stay above the threshold.

**Decision for Eric.** The threshold, and whether archived goals count toward it.

**Review note (condensed; the observation and proposal above are the revised text).** The form is built unconditionally (ticklist.py:79-110, build at 146-147) and the script exits quietly without it (ticklist.js:76), so the change is feasible and S. Observation reproduces: the ticklist crop and the built form show the search box, two rows of controls and '1 OF 1 GOAL'; `controls(site)` and `status_row(site)` are always built (ticklist.py:79, 120, 146); ticklist.js:71-76 returns when `#search` is absent. Count wrong: the built form holds 10 buttons, 5 selects and the search input (16 controls), not eleven.

#### phone-05. Trips on phones: make List a dense view or hide the toggle

**Observation.** Below 560 px a trip card already is a 112 px-thumbnail row, and the explorer's List view is the same 112 px row with rules between rows, so switching Cards to List changes only separators and spacing. The toggle still takes a 44 px slot in the phone form and a URL state. The tick list has the same pair.

**Evidence.** `phone-trips.jpeg (crop: s2) (Cards | List toggle)`; `assets/css/base.css:293-316 (.tcard row below 560, column layout from 560)`; `assets/css/pages/trips.css:93-98 (.trx--list .tcard: 112 px row)`; `assets/css/pages/ticklist.css:35-38`; `assets/css/base.css:621-650 (the compact 72-88 px row idiom)`.

**Proposal.** Below 560 px give .trx--list .tcard a dense row: route glyph or 64 px thumb, title, 'icon · date · distance', no excerpt or tags, about 72 px per row, so List is the scan view and Cards the photo view. The `.rtab--compact` rules at base.css:621-650 describe exactly this row but are emitted by no page today (unused CSS), so either revive them for the list view or model the row on the Map page's live `.arc-table .rtab-r` layout (archive.css:166-178). If that is more than wanted, hide .trx-view below 560 and let trips.js keep the view in the URL but render cards there. Mirror the choice on the tick list (ticklist.css:35-38).

**Files.** `assets/css/pages/trips.css`, `assets/css/pages/ticklist.css`, `assets/js/pages/trips.js`.

**Effort.** S. Visitor value 2.3, author value 1, confidence high.

**Risk.** The view is shared URL state across widths; change presentation only. The dense row drops the excerpt, which the Cards view keeps.

**Review note (condensed; the observation and proposal above are the revised text).** The observation is correct: base.css:293 makes `.tcard` a 112 px-thumbnail row, base.css:313-317 switch it to a column only inside `.tgrid` from 560 px, trips.css:93-95 make `.trx--list .tcard` the same 112 px row with a rule, ticklist.css:35-38 do the same for `.gcard`, and nothing in trips.css hides `.trx-view` on phones; trips.js:13 keeps 'view' in the URL keys. Not built.

#### visual-07. Home Recent outings: show the write-up excerpt where one exists

**Observation.** Recent outings cards never carry a summary, while the same card on the Trips page does: 'Tallac' (Sep 17) shows its one-line write-up on Trips and nothing on home. `trip_card` already drops a facts-only summary, so bare rides would stay as they are and the cards would tell a visitor which outings have something to read.

**Evidence.** `desktop-home.jpeg (Recent outings cards without excerpts)`; `desktop-trips.jpeg (the same Tallac card with 'I guess my cardio isn't terrible')`; `tools/sitegen/pages/home.py:157-160`; `tools/sitegen/pages/trips.py:176`; `tools/sitegen/core.py:1279-1285`.

**Proposal.** call `core.trip_card(t, HERE, RECENT_SIZES, ns='rc', summary=True)` at home.py:160 (RECENT_SIZES at home.py:28) and reword the `rcard` docstring at home.py:157-159. No test pins the absence (tests/test_home.py has no excerpt assertion); update docs/DEVELOPING.md:184, which documents the recent cards as showing no summary. `.hom-rcards` is a grid (home.css:98-102), so uneven heights only lengthen a column; the excerpt is Eric's text, clipped at two lines by `.tcard-ex` (base.css:310). Files: tools/sitegen/pages/home.py, docs/DEVELOPING.md.

**Files.** `tools/sitegen/pages/home.py`, `tests/test_home.py`.

**Effort.** S. Visitor value 2.7, author value 1.3, confidence high.

**Risk.** Card heights in the 3-column grid become uneven, as on the Trips page; the excerpt is Eric's text, clipped at two lines by `.tcard-ex`.

**Review note (condensed; the observation and proposal above are the revised text).** Not built; the observation holds but one step of the proposal targets a test that does not exist. home.py:157-160 passes no summary and its docstring gives the reason ('a track-only outing has nothing to read'), but trip_card already drops a facts-only summary (core.py:1279-1282), so the stated reason does not block the change; trips.py:176 shows the same card with summary=True. The .hom-rcards grid (home.css:98-102) is a plain grid, so uneven heights only lengthen a row. Observation reproduces: home.py:157-160 (`rcard` calls trip_card without summary), trips.py:176 (summary=True), core.py:1279-1285 (facts-only summaries dropped); in the build the tallac-2026-09-17 card carries 'I guess my cardio isn't terrible' in `.tcard-ex` on trips/index.html and has no `.tcard-ex` on index.html; the home-mid crop shows the Tallac Sep 17 card with no excerpt.

**Gates.** The phase is done when every line below holds and is recorded in the log entry:

1. A stdlib script over the built trips/search.json and journal.json shows: 'lovers leap', "lover's leap" and 'lovers' each find the three Lover's Leap reports; 'skiing' finds all 51 ski reports and 'bike' all 61 rides at keyword score; 'ice' finds 1 report, not 'practice' or 'nice'; 'loop' finds all 71 loops; 'june 2024' lists the 30 June journal days and '2024' alone lists no day; search.json stays under 80 KB raw and 20 KB gzipped (today 67,718 B / 17,196 B).
2. The Node harnesses (tests/trips_js_harness.js, tests/ticklist_js_harness.js) pass with new cases: apostrophe normalization, word-start matching with 'matter', 'for' and 'coul' still passing, month facet parse/serialize/facetOk, sort=longest|gain with unknowns last, photos facet, zero-result buttons built from live counts, one fetch per index after a focus-before-typing, list-view srcset/sizes swap and restore; tests/run_orders.py still passes.
3. Every page except trips/ carries form.nav-search with a hidden sort=relevance input (ids nav-q and menu-q differ); submitting from a report lands on trips/?q=…&sort=relevance with results; the form is hidden under (scripting: none); tests/test_nav.py and tests/test_a11y_static.py updated and green; the 404 page's form posts to trips/ and the prefilled slug words come from the URL only.
4. In the build, mount-tallac-2026-02-15's More like this no longer lists 'Powderhouse lap before work' twice and offers other Tallac ski tours; the meta line names the new rule; tests/test_related.py has the same-place-wins, common-word-does-not-pair and different-activity cases.
5. Counted with the loader after copy-03: of the 39 explorer excerpts that ended mid-sentence, 37 now end at a sentence; the Matterhorn card excerpt ends at a full stop.
6. Trips says 14 REGIONS like map/ and trips/?region=pacific-crest-trail opens the unfiltered explorer (documented in DEVELOPING.md:398).
7. Phone captures at 390 px of trips/ and tick-list/ before and after: with scripting the first result card on trips/ starts within the first 844 px; selects, the switch and Sort sit behind a 44 px 'Filters' button that keeps URL state; the tick list with one goal shows the head and the card and no form (server-side active rule), and its fixture above FILTERS_FROM still renders the form; List view rows are about 72 px.
8. Two of the six home Recent outings cards carry Eric's excerpt (tallac-2026-09-17 and tahoe-mountain-loop today) and track-only cards stay bare; DEVELOPING.md:184 updated.
9. Both Pythons with -W error, python3 tools/build.py --check, and docs/CONTENT_GUIDE.md section 6 and DEVELOPING.md:280-335 describe the new 'k', 'd' and placeholder contracts.

**Tests to add.** New: none. Extended: `tests/norm_cases.json`, `tests/test_a11y_static.py`, `tests/test_cover.py`, `tests/test_home.py`, `tests/test_nav.py`, `tests/test_notfound_page.py`, `tests/test_related.py`, `tests/test_report_page.py`, `tests/test_search.py`, `tests/test_ticklist_page.py`, `tests/test_trips_js.py`, `tests/test_trips_page.py`, `tests/ticklist_js_harness.js`, `tests/trips_js_harness.js`. Plus the checks the gates name that no unit test covers: A stdlib script over the built `trips/search.json` and `journal.json` for the named queries; the Node harnesses; `tests/run_orders.py`; a phone capture at 390 px of trips/ and tick-list/.

**Screenshots to capture.** `trips/` and `tick-list/` at 390 px before and after (the before set is `phone-trips.jpeg` and `phone-ticklist.jpeg`); one report at 1280 px with the header search box; the 404 page; the home page's Recent outings at 1280 px after visual-07.

**Author inputs needed.** The activity word lists (gap3-01; defaults used if he says nothing); visual-02 against ia-05; the tick list's `FILTERS_FROM = 6` (visual-05).

### Phase 8. Publishing loop, CI and recovery

**Goal.** Replace the 14-action publish with one command that runs a linked check, stages by path, refuses conflict copies and unrendered trips, commits and (with --push) watches the deploy; write the rollback, lost-index, web-edit and new-Mac recipes; clean the checkout and settle where it lives; make a content push go live in about a minute, pin Node, parse the bundle in CI, and let a draft: true push take a trip off the site from anywhere.

**Prerequisites.** Phase 6 (publish.py refuses a slug that render.py --status names; the stale-map warnings). Eric's decisions: where the checkout lives, and 12.8 for gap7-03 (recommended yes).

**Decisions this phase waits on.**

- Where the checkout lives (move out of iCloud Drive, recommended, or stay with Keep Downloaded and tidy.py before commits)
- 12.8: the build drops a drafted or deleted trip's own pin and line itself (recommended yes)

**Findings in this phase** (23, in working order): authoring-01, authoring-02, authoring-17, gap7-01, gap7-02, gap7-10, gap7-07, gap7-04, gap7-06, gap7-05, authoring-16, gap10-05, authoring-12, authoring-14, authoring-11, authoring-20, authoring-19, authoring-03, perf-13, resilience-08, qa-12, a11y-11, gap7-03.

#### authoring-01. One publish command that runs the five publish steps and stops on failure

**Observation.** Publishing a single-day trip is 14 manual actions today: export and unzip the track, gather photos, cd, the add_trip command, edit index.md, fill every alt line, build --serve and open the browser, Ctrl+C, build --check, git add three paths, git status --short, read all three outputs, git commit, git push, then wait. ADDING-TRIPS.md:197 says the three publish commands 'run one after the other whatever each one answers, so a failed check does not stop the git add'; the author must also check the branch by hand (ADDING-TRIPS.md:249-254) and read the staged list for conflict-copy names (:242-247); README.md:37-60 repeats the same three commands. There is no tools/publish.py, no Makefile and no git hook (.git/hooks holds only *.sample files).

**Evidence.** `ADDING-TRIPS.md:190-214`; `ADDING-TRIPS.md:232-254`; `README.md:37-60`; `tools/add_trip.py:201-203`; `.git/hooks (samples only)`.

**Proposal.** Add tools/publish.py SLUG [SLUG…] [--message TEXT] [--dry-run]. It refuses unless `git branch --show-current` is main and nothing unrelated is already staged; runs build.py's check in-process as build.main(['--check', '--link']) (build.py:376; --check already runs checks.run through content_errors(), build.py:399, and --link keeps the check at about 4 s instead of copying 240 MB into _site/, docs/IMPLEMENTATION_REPORT.md:218-219) and stops on the first failure; stages exactly content/trips/<slug>, rendered/trips/<slug> when the folder exists, rendered/site when `git status --porcelain rendered/site` is non-empty, and content/home.json when changed; refuses any staged path for which sitecheck.conflict_copy(basename) (tools/sitegen/sitecheck.py:55) is true; refuses when the validator's `no rendered map` warning (checks.py:834) names the slug unless --allow-unrendered; prints the staged list; commits as `Add <title>` taken from the front matter (or `Update <title>` when the folder already had commits); pushes; then hands over to the deploy watch of authoring-02. --dry-run does everything but commit and push. Tests in tests/test_publish_cli.py against a temporary git repository with a synthetic trip, in the style of tests/test_build_cli.py (git is on the runner). Replace ADDING-TRIPS.md step 5 and README.md step 3 with the one command and move the manual steps under 'What it does'.

**Files.** `tools/publish.py`, `tests/test_publish_cli.py`, `ADDING-TRIPS.md`, `README.md`.

**Effort.** M. Visitor value 1, author value 4.3, confidence high.

**Risk.** A wrapper that runs git push: it must never use `git add -A`, must refuse on any branch but main, and must leave the manual path documented so a failure of the wrapper does not block publishing.

**Review note (condensed; the observation and proposal above are the revised text).** Observation verified: ADDING-TRIPS.md:195-197 says the three publish commands run whatever each answers, :249-254 is the manual branch check, :232-247 the conflict-copy reading; .git/hooks holds only *.sample files; add_trip.py:201-203 prints 'next: edit' regardless. Everything reproduces except one unverifiable count.

#### authoring-02. Watch the deploy from the terminal after the push

**Observation.** After `git push` the guide says the trip is 'live a few minutes later' (ADDING-TRIPS.md:249-250) and names no way to see whether the run passed; a failed run leaves the old site up silently unless the author opens github.com. The gh CLI is installed (/opt/homebrew/bin/gh) and already answers `gh run list` for this repository; the last five runs took 151-188 s, and the latest (38429837834) spent 113 s in unit tests, 4 s building, 10 s uploading and 15 s deploying.

**Evidence.** `ADDING-TRIPS.md:249-254`; `/opt/homebrew/bin/gh`; `gh run list (runs 38429837834, 38425104080, 38419203985, 38311617727, 38264950033)`; `gh run view 38429837834 --json jobs`.

**Proposal.** After `tools/publish.py --push` (authoring-01), find the run for HEAD with `gh run list --commit <sha> --json databaseId,status --limit 1` (retry for up to 30 s while it appears), then `gh run watch <id> --exit-status`; on success print the live URL of each published trip (core.SITE_URL + 'trips/<slug>/'); on failure print `gh run view <id> --log-failed` and the sentence that the old site is still up. Without gh, or when gh is not logged in, print the Actions URL and exit 0: the watch never fails a publish. If authoring-01 is not built, ship the same 30 lines as tools/deploy_watch.py. No `--status` subcommand: document `gh run list -L 3` in ADDING-TRIPS.md step 5 as the way to see the last runs and whether the newest succeeded.

**Files.** `tools/publish.py`, `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1, author value 3.3, confidence high.

**Risk.** Depends on gh being logged in; must degrade to a printed URL, never fail the publish.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: gh 2.97.0 is installed at /opt/homebrew/bin/gh and logged in; `gh run list` accepts `-c, --commit SHA` and `--json`, and `gh run watch` has `--exit-status` (gh --help output). ADDING-TRIPS.md:249-250 names no way to see the run.

#### authoring-17. Run both Pythons and the three checks with one developer command

**Observation.** DEVELOPING.md:1288-1295 asks for the suite on /usr/bin/python3 (3.9.6) and python3.12, both with -W error, before any change to tools/; python3.12 is installed (/opt/homebrew/bin/python3.12) and uv 0.9.25 is available, but nothing runs the pair, there is no pre-push hook, and the first deploy failed on a patch release the Mac does not have (log:945-951).

**Evidence.** `docs/DEVELOPING.md:1288-1302`; `/opt/homebrew/bin/python3.12`; `~/.local/bin/uv (0.9.25)`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:945-951`; `.git/hooks (samples only)`.

**Proposal.** tools/check.py (stdlib): runs `python3 tools/validate.py`, then `/usr/bin/python3 -W error -m unittest discover -s tests`, then the same on `python3.12` when it is on PATH (otherwise prints one line saying to install it and continues), then `python3 tools/build.py --check --out .cache/check --link`; one summary line per step with its wall time and a non-zero exit when any step fails; `--quick` skips the second Python. Document it in docs/DEVELOPING.md 'Checking your work' as the command to run before a push that touches tools/, tests/ or assets/. No hook. Effort S.

**Files.** `tools/check.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1, author value 3, confidence high.

**Risk.** No hook: a two-minute hook on every code push would be skipped or disabled; check.py is run by hand before a push that touches tools/, tests/ or assets/, and CI runs the same steps.

**Review note (condensed; the observation and proposal above are the revised text).** The wrapper is worth it: docs/DEVELOPING.md:1288-1295 already asks for the suite on both Pythons with -W error before a change to tools/, /opt/homebrew/bin/python3.12 (3.12.11) and ~/.local/bin/uv exist, and nothing runs the three steps together.

#### gap7-01. The written, rehearsed rollback

**Observation.** No guide says how to go back after a bad push: a grep of README.md, ADDING-TRIPS.md and docs/*.md for revert/rollback/undo finds only docs/IMPLEMENTATION_REPORT.md:864-866 ('Going back, not rehearsed'). Facts that fix the recipe: a push to main is live about 2.5 to 3 minutes later (the last five runs took 151 to 188 s; the deployments API shows 1cb9cf2 live at 16:23:53Z after a 16:21:32Z push); the github-pages environment admits runs whose ref is `main` only (custom branch policy, one entry: main, type branch); a workflow dispatch takes a branch or tag name, never a commit sha, there is no tag to dispatch, and a dispatch on a tag would be refused at the deploy job by that policy; deploy-pages ships only its own run's artifact, so nothing re-deploys an old artifact. Two paths remain: `gh run rerun <id of the last good run>` (whole run, not --failed) rebuilds that commit on main without a commit, is offered by GitHub only for 30 days after the run, and is undone by the next push; `git revert --no-edit <sha> && git push` is the durable one. Both take the same ~3 minutes and both sit in the `pages` concurrency group with cancel-in-progress (pages.yml:16-18), so a rollback push cancels a bad run still in flight. Force-push is ruled out by docs/PRIVACY_NOTES.md section 6. Any run before d7272e0 fails the tests on the runner's Python 3.12.15, so a re-run of an older run is not a rollback.

**Evidence.** `.github/workflows/pages.yml:6-18`; `.github/workflows/pages.yml:37-45`; `docs/IMPLEMENTATION_REPORT.md:864-866`; `docs/PRIVACY_NOTES.md:204-207`; `gh api repos/esichak/personal-website/environments/github-pages (2026-10-13: deployment_branch_policy custom_branch_policies, policies: main only)`; `gh run list --limit 12 (2026-10-13: runs 38429837834, 38425104080, 38419203985, 38311617727, 38264950033 completed in 161/171/188/174/151 s)`; `gh api repos/esichak/personal-website/deployments?environment=github-pages (latest sha 1cb9cf2, ref main, 2026-10-13T16:23:53Z)`; `git tag (empty)`; `gh run rerun --help (whole run / --failed / --job)`; `ADDING-TRIPS.md:313-332`.

**Proposal.** Add 'The site is wrong after a push' to ADDING-TRIPS.md 'If something goes wrong' (and a cross-reference from docs/DEVELOPING.md): (1) the durable fix is `git revert --no-edit <sha>` then `git push` (for several commits, revert each newest-first in one go); the deploy takes about three minutes; a push cancels a run still in progress (pages.yml concurrency), so do not wait for a bad deploy to finish; (2) the temporary fix with no commit is `gh run rerun <id>` with the id of the last good run from `gh run list` (the whole run, not --failed), which rebuilds that run's commit and is undone by the next push; (3) never force-push and never rewrite history (docs/PRIVACY_NOTES.md section 6); (4) watch with `gh run watch` or the Actions page. Rehearse it once on a harmless doc-only commit and write the measured minutes into the doc. No --undo tool. Effort S.

**Files.** `ADDING-TRIPS.md`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1, author value 3.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.5 'Going back, not rehearsed'

**Risk.** A revert of a trip commit also reverts its rendered/site maps, which is right, but a revert of a generator commit with later content on top can fail the build; the local --check before the push covers that. Never force-push (docs/PRIVACY_NOTES.md section 6). `gh` is needed only for the re-run path and the watch; the revert path is plain git.

**Decision for Eric.** Whether the rehearsal push on a harmless doc-only commit happens in the Phase 8 session (he must say yes to that push in his own words; otherwise the recipe is written and the rehearsal marked pending).

**Review note (condensed; the observation and proposal above are the revised text).** The gap is real and every fact checked out today: no guide mentions revert/rollback (grep of README.md, ADDING-TRIPS.md, docs/*.md hits only docs/IMPLEMENTATION_REPORT.md:864-866), pages.yml:16-18 has cancel-in-progress on the `pages` group, `gh api .../environments/github-pages` shows a custom branch policy with `main` as its only entry, `git tag` is empty, and the last five runs took 161-188 s. Observation reproduces in substance: grep of README.md, ADDING-TRIPS.md and docs/*.md for revert/rollback/undo finds only docs/IMPLEMENTATION_REPORT.md:865-866 ('Going back, not rehearsed'); `gh api .../environments/github-pages` shows custom_branch_policies true and `.../deployment-branch-policies` one entry {name: main, type: branch}; `gh run list` gives 161/171/188/174/151 s for the last five successful runs; deployments API shows 1cb9cf2 at 2026-10-13T16:23:53Z after the 16:21:32Z run start; `git tag` is empty; pages.yml:16-18 has group pages / cancel-in-progress true; docs/PRIVACY_NOTES.md:205-207 rules out a force push; `gh run rerun --help` lists --failed and --job.

#### gap7-02. Let a workflow dispatch build any past commit on main

**Observation.** `workflow_dispatch` is already on (pages.yml:9) but takes no input, and the checkout step (pages.yml:24, actions/checkout@v4 with no `ref`) always takes the pushed commit, so a manual run can only rebuild main's head. Because the github-pages environment admits runs whose ref is `main` (custom branch policy, one entry), the one commit-free rollback today is re-running an old run (every run so far is a push on main, run_attempt 1, e.g. 36460954002), which GitHub offers only for 30 days after the run's first attempt.

**Evidence.** `.github/workflows/pages.yml:6-9`; `.github/workflows/pages.yml:24`; `gh api repos/esichak/personal-website/environments/github-pages (deployment branch policy: main only)`; `gh api repos/esichak/personal-website/actions/runs/36460954002 (head_branch main, event push, run_attempt 1)`.

**Proposal.** Add `inputs: ref: {description: 'commit to build and deploy (empty: this branch)', required: false}` under `workflow_dispatch`, and `with: ref: ${{ inputs.ref || github.sha }}` on `actions/checkout@v4`. The run itself is still on `main`, which is what the environment policy checks, while the build job runs that commit's tests and `build.py --check` before deploying it. Command for the doc: `gh workflow run pages.yml -f ref=<sha>`; say that it is temporary (the next push re-deploys main's head) and must be followed by a revert (gap7-01), and that only someone with write access can dispatch it. Try it once with the current head's sha to confirm the environment gate accepts it before relying on it.

**Files.** `.github/workflows/pages.yml`, `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1, author value 2, confidence medium.

**Risk.** Reasoned from the environment policy, not tried: if the gate also looks at the checked-out commit the dispatch fails at the deploy job and nothing changes on the site. The workflow file read is main's, the tools are the old commit's; a mistyped ref fails at checkout.

**Decision for Eric.** Whether to add this path at all, or rely on re-run plus revert.

**Review note (condensed; the observation and proposal above are the revised text).** Observation reproduces: .github/workflows/pages.yml:9 is a bare `workflow_dispatch:` with no inputs and line 24 is `uses: actions/checkout@v4` with no `ref`; the environment's deployment-branch-policies list is one branch entry, main; `gh api .../actions/runs/36460954002` returns head_branch main, event push, run_attempt 1.

#### gap7-10. Turn 'If something goes wrong' into a recovery section

**Observation.** ADDING-TRIPS.md:313-332 'If something goes wrong' has six symptom bullets (cwebp, OSM busy, a changed title, a missing .th copy, Strava arguments, a missing render folder) and a seventh that points to the other docs; all six are hiccups before the push. Nothing covers what happens after a push or to the Mac. Four of the ten Actions runs on record failed (`gh run list --limit 12`, 2026-10-13): 36377313295, 36380232646 and 36433946532 at 21-44 s on 2026-09-27/28 at `actions/configure-pages` ('Get Pages site failed ... verify that the repository has Pages enabled and configured to build using GitHub Actions', a one-time repository setting that has not recurred), and 38263425621 on 2026-10-12 at the unit tests (docs/WEBSITE_IMPLEMENTATION_LOG.md:945-951). The deploy job was skipped in all four, so the old site stayed up each time. The guide says nowhere how to read the red X, that the old site stays up, or that a local build can take minutes while iCloud downloads offloaded files under rendered/ (docs/IMPLEMENTATION_REPORT.md:219-221); the iCloud index incident is at docs/IMPLEMENTATION_REPORT.md:476-484. No other doc (README.md, docs/DEVELOPING.md, docs/CONTENT_GUIDE.md) has a failed-run or recovery section.

**Evidence.** `ADDING-TRIPS.md:313-332`; `gh run list --limit 12 (2026-10-13: failures 38263425621, 36433946532, 36380232646, 36377313295)`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:945-951`; `docs/IMPLEMENTATION_REPORT.md:219-221`; `docs/IMPLEMENTATION_REPORT.md:476-484`.

**Proposal.** Rename the section 'When something goes wrong' and group it in three parts, each entry one symptom in bold and the fix in two or three lines. Before the push: the six existing symptom bullets, with the docs pointer kept as the section's last line. After the push: 'The Actions run shows a red X' (the old site stays up; open the run and see which step of the build job stopped: Unit tests, where the log's first `FAIL:` or `ERROR:` line names the test, fix locally, run `python3 -m unittest discover -s tests`, push again; Build, where the first `ERROR` or `BROKEN` line, or `link check: N problems`, names the file, fix locally, run `build.py --check`, push again; `actions/configure-pages`, where 'Get Pages site failed' means the repository's Pages setting on GitHub, Settings > Pages > Source: GitHub Actions, is off, nothing to fix locally); 'The site is wrong after a push' (gap7-01, with the timings and a note that `cancel-in-progress: true` in .github/workflows/pages.yml makes a second push cancel a run still going); 'I need an old version back for a moment' (re-run or gap7-02); 'A trip I drafted is still on the site' (gap7-03/04). The Mac: 'The build takes minutes instead of seconds' (iCloud offloaded rendered/: Finder's Keep Downloaded on the folder; name a doctor script only if another finding adds one, since tools/doctor.py does not exist today); 'git says the index is missing' (gap7-07); 'A map has no roads or names after a render' (move the existing OSM bullet here, plus gap7-09). Keep every entry to the symptom the author sees, as the present bullets do. Files: ADDING-TRIPS.md only.

**Files.** `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1, author value 3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.5

**Risk.** Documentation only; entries that depend on gap7-01/02/03/09 go in as those land, each quoting the exact command.

**Review revision (applies on top of the text above).** Observation (corrected): as stated, but note that three of the four failed runs were a one-time Pages configuration error at `configure-pages` (fixed the same day, run 36460954002), and only the 2026-10-12 failure at `Unit tests` is the recurring kind (a test or `build.py --check` failing on the runner). Proposal: rename the section 'When something goes wrong' and group it in three parts, one bold symptom per entry and the fix in two or three lines. Before the push: the seven existing bullets, unchanged, with the OSM bullet moved to The Mac. After the push, written now from the record: 'The Actions run shows a red X' (nothing was deployed and the old site stays up, as on 2026-10-12, docs/WEBSITE_IMPLEMENTATION_LOG.md:945-951; open the run on github.com, open the failed step (`Unit tests` or `Build`) and read its first `FAIL`, `ERROR` or `BROKEN` line (tools/sitegen/sitecheck.py:272-290 prints the `BROKEN` ones); fix locally, run `python3 -m unittest discover -s tests` and `python3 tools/build.py --check`, push again; a new push cancels a run still going, `.github/workflows/pages.yml:16-18`). The Mac: 'The build takes minutes instead of seconds' (iCloud has offloaded files under `rendered/`: right-click the folder in Finder and choose Keep Downloaded; docs/IMPLEMENTATION_REPORT.md 2.8 and 11) and 'git says the index is missing or unreadable' (the recovery of docs/IMPLEMENTATION_REPORT.md section 11: `git read-tree HEAD` rebuilds the index from the last commit and leaves the working tree alone; `git status --short` then shows the work as unstaged, nothing lost). Do not cite `tools/doctor.py` (it does not exist) and do not write a 'get an old version back' entry: docs/IMPLEMENTATION_REPORT.md 15.5 says going back was never rehearsed, and a re-run of any run before d7272e0 fails at the tests on the runner's Python (LOG 945-951). The entries for gap7-01, gap7-02, gap7-03/04 and gap7-09 are added by those findings when they land, each quoting the command it ships. Files: ADDING-TRIPS.md. Effort S for this standalone version.

**Review note (condensed; the observation and proposal above are the revised text).** Not built: ADDING-TRIPS.md:313-332 still has only the six pre-push bullets plus a pointer, and the Publish section (ADDING-TRIPS.md:240-247) describes only a passing run; README.md:114-129 and docs/DEVELOPING.md:1250-1302 explain CI's steps, not a failed run. Observation verified: ADDING-TRIPS.md:313-332 is seven bullets, all pre-push; step 5 (lines 248-255) says GitHub deploys 'when both pass' and never says what a failed run means. The observation reproduces almost entirely. ADDING-TRIPS.md:313-332 is the 'If something goes wrong' section (the file's last heading, 332 lines); `gh run list --limit 12` returns exactly ten runs, four of them failures with the cited IDs: 36377313295 (21 s), 36380232646 (21 s) and 36433946532 (44 s) on 2026-09-28 UTC (the first two are 2026-09-27 evening local), and 38263425621 (3 m 52 s) on 2026-10-12.

#### gap7-07. Document and detect the lost .git/index recovery

**Observation.** On 2026-10-10 iCloud removed `.git/index` while the disk was at 13 GB; the recovery (`git read-tree HEAD` after comparing the tree through a temporary index; history, branches, objects and working tree intact) is written only in docs/IMPLEMENTATION_REPORT.md:476-484, not in any author guide. `.git/` holds `index 2` to `index 9`, two of them made today (08:40 and 09:11), so iCloud is still copying the index.

**Evidence.** `docs/IMPLEMENTATION_REPORT.md:476-484`; `ls -la .git (index 2 to index 9, Sep 27 to Oct 13, 2026-10-13)`; `ADDING-TRIPS.md:313-332`.

**Proposal.** Add to ADDING-TRIPS 'If something goes wrong': '`git status` says the index is missing or unreadable': run `git read-tree HEAD`, then `git status --short`; nothing is lost but the staging list, so `git add` again what was staged; then free disk space before going on. doctor.py (gap7-05) flags a missing `.git/index` with that recipe and lists the stray `index N` copies with the `rm` line to run by hand after confirming each is not the live index.

**Files.** `ADDING-TRIPS.md`, `tools/doctor.py`.

**Effort.** S. Visitor value 1, author value 2.7, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 11 'Incident during this phase'

**Risk.** `git read-tree HEAD` discards only the staging list; the doc must say so. Deleting the copies is Eric's call (the report says they are the author's to delete).

**Review note.** Kept as written by all three skeptics.

#### gap7-04. Warn that drafting a trip on github.com can fail the deploy

**Observation.** ADDING-TRIPS.md:256-262 'Quick fixes from anywhere' says an edit to index.md on github.com redeploys the site on its own. Adding `draft: true` there to one of the 27 trips with a pin of its own fails `build.py --check` in CI, the trip stays up, and the only signal is the Actions page or its email; the guide's removal section (ADDING-TRIPS.md:264-284) describes the failure but never says that the web path is affected.

**Evidence.** `ADDING-TRIPS.md:256-262`; `ADDING-TRIPS.md:264-284`; `.github/workflows/pages.yml:28-31`; `rendered/site/meta.json (27 trips with a cluster of one, 2026-10-13)`.

**Proposal.** Until gap7-03 lands, add two sentences to 'Quick fixes from anywhere': a web edit that adds `draft: true` or links to another report can fail the check and change nothing on the site; look at the Actions page (or `gh run list --limit 1`) after a web edit. Add the same note to 'Taking a trip off the site'. After gap7-03, invert it: the web edit becomes the recommended way to take a trip off from a phone.

**Files.** `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1, author value 2.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 10 'Taking a trip off the site needs a render'

**Risk.** None; documentation only.

**Review note.** Kept as written by all three skeptics.

#### gap7-06. Write the new-Mac setup and what a fresh clone refetches

**Observation.** README.md:9-10 says nothing needs installing but cwebp, ADDING-TRIPS.md:19 hard-codes `~/Documents/"Claude Code"/personal-website`, and docs/DEVELOPING.md:1288-1302 wants python3.12 and node; no page lists the Xcode command-line tools (git and the 3.9.6 python3), Homebrew, `gh auth login`, the size of a clone (182.75 MiB pack plus 168 MB of content) or that `.cache/` (284 MB of Overpass answers, 77 MB of tiles) is git-ignored and refetched on the first render. On a new Mac `render.py` without `--force` redraws nothing (the hashes exclude OSM data), and `--site --force` redraws all 24 site maps from today's OSM; the git-ignored author file (report 12.12) and the Strava and Garmin exports are outside the repository and in no clone.

**Evidence.** `README.md:9-10`; `ADDING-TRIPS.md:16-20`; `docs/DEVELOPING.md:1288-1302`; `tools/lib/geo.py:14-17`; `.gitignore:2`; `tools/render.py:430-434`; `tools/render.py:638-645`; `git count-objects -vH (size-pack 182.75 MiB, 2026-10-13)`; `du -sh .cache/osm .cache/tiles (284M, 77M, 2026-10-13)`; `docs/IMPLEMENTATION_REPORT.md:520`.

**Proposal.** A 'Setting up a new Mac' section in README.md (eight lines): `xcode-select --install`; install Homebrew; `brew install webp gh node python@3.12` (the last two optional, say why); `gh auth login`; `git clone https://github.com/esichak/personal-website.git` into the folder authoring-16 settles on, never a Finder copy of the old folder (it would carry the conflict copies); `python3 tools/doctor.py`; `python3 -m unittest discover -s tests`; `python3 tools/build.py --check`. Then one paragraph: the first `render.py` downloads about 360 MB into `.cache/` and nothing re-renders until a track, title or map setting changes; `--site --force` redraws every region map from current OSM data. Close with what is not in the clone (the author file the privacy notes point to, the vendor exports; cross-reference authoring-20). Change ADDING-TRIPS.md:19 to 'the folder you cloned the site into'.

**Files.** `README.md`, `ADDING-TRIPS.md`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1, author value 2.3, confidence high.

**Already known.** docs/DEVELOPING.md 'Checking your work'

**Risk.** None beyond keeping Homebrew paths generic; does not decide where the checkout lives (authoring-16).

**Review revision (applies on top of the text above).** Proposal, amended: as written, plus change the identical `cd ~/Documents/"Claude Code"/personal-website` line at docs/TICK_LIST_GUIDE.md:139 to 'the folder you cloned the site into' as well (docs/IMPLEMENTATION_REPORT.md 15.4 point 1 lists both guides as the files that say where the checkout lives; cite it as known). Files: README.md, ADDING-TRIPS.md, docs/TICK_LIST_GUIDE.md, docs/DEVELOPING.md. Size note: the clone is a 182.75 MiB pack plus about 172 MB of content/ (du, 2026-10-13).

**Review note (condensed; the observation and proposal above are the revised text).** Not done, with one omission.

#### gap7-05. Add tools/doctor.py: one read-only check of the Mac

**Observation.** What the Mac needs is spread over README.md:9-10 (cwebp), ADDING-TRIPS.md:315, docs/DEVELOPING.md:1288-1302 (two Pythons; 53 tests skip without node), the workspace CLAUDE.md (conflict copies, offloaded files) and the incident in docs/IMPLEMENTATION_REPORT.md:476-484 (13 GB free, index gone); nothing checks any of it. Measured today: cwebp 1.5.0, node 25.8.2, /usr/bin/python3 3.9.6, python3.12 3.12.11, gh 2.97 signed in with the workflow scope, git identity set, 18 GiB free of 228, 6,136 conflict copies (0 tracked; 6,102 of them offloaded), 0 tracked files offloaded, eight stray `.git/index N` copies (`index 2` to `index 9`, two dated today), `.cache/` about 720 MB of which about 355 MB are evidence folders (p4, p5, plan2, preview, review). The macOS dataless flag (st_flags & 0x40000000) is readable with `os.lstat`, so offloaded files can be counted from Python.

**Evidence.** `README.md:9-10`; `ADDING-TRIPS.md:315`; `docs/DEVELOPING.md:1288-1302`; `docs/IMPLEMENTATION_REPORT.md:476-484`; `.gitignore:7-19`; `shell 2026-10-13: command -v cwebp sips node python3 python3.12 gh git brew; python3/python3.12/node/gh/cwebp --version; df -h .; git config user.name/user.email; ls -la .git (index 2 to index 9); du -sh .cache/*`; `python3 os.lstat(st_flags & 0x40000000) over rendered/ and git ls-files (6,102 dataless copies; 0 dataless tracked files)`.

**Proposal.** `python3 tools/doctor.py`, stdlib, 3.9-compatible, read-only, offline, one line per check (OK/WARN and the fix): disk free in GB, WARN under 30 GB citing the October incident; `.git/index` present, else the `git read-tree HEAD` recipe (gap7-07); stray `.git/index N` copies listed with the `rm` line to run by hand; branch is main, tree clean, ahead/behind origin/main from the tracking ref, identity set; conflict copies counted by top folder, with any under content/ or among staged files named; tracked files under rendered/ and content/ that are offloaded (macOS `os.lstat().st_flags & 0x40000000`, 'not checked' elsewhere), with Finder 'Keep Downloaded' as the fix; cwebp present (`brew install webp`), node and python3.12 optional with one clause each. Exit 1 only on what blocks a publish (not on main, dirty tree, index missing). No `--network`, no cache or validate probes. Tests: a synthetic repo in a temp folder for the git and copy checks, the disk and offload probes stubbed. Mention it in README 'Check, build and re-render', in ADDING-TRIPS 'If something goes wrong' and in the new-Mac section (gap7-06). Effort M.

**Files.** `tools/doctor.py`, `tests/test_doctor.py`, `README.md`, `ADDING-TRIPS.md`, `docs/DEVELOPING.md`.

**Effort.** M. Visitor value 1, author value 3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 11 'Incident during this phase'

**Risk.** Must never modify anything; prints no path outside the repository beyond the free-disk figure; the dataless probe is macOS-only and must degrade to 'not checked' elsewhere (CI, Linux).

**Review revision (applies on top of the text above).** Observation, corrected: What the Mac needs is spread over README.md:9-10 (cwebp), ADDING-TRIPS.md:315, docs/DEVELOPING.md:1288-1302 (two Pythons; 53 tests skip without node), the workspace CLAUDE.md (conflict copies, offloaded files) and the incident in docs/IMPLEMENTATION_REPORT.md:476-484 (13 GB free, index gone); nothing checks any of it. Measured 2026-10-13: cwebp 1.5.0, node 25.8.2, /usr/bin/python3 3.9.6, python3.12 3.12.11, gh 2.97 signed in with the workflow scope, git identity set, about 20 GB free of 228, 6,136 conflict copies (0 tracked; 6,102 of them offloaded), 0 tracked files offloaded, eight `.git/index N` copies (`index 2` to `index 9`, two dated today), `.cache/` about 690 MB of which about 355 MB are evidence folders. The macOS dataless flag (st_flags & 0x40000000) is readable with `os.lstat`, so offloaded files can be counted from Python.

**Review note (condensed; the observation and proposal above are the revised text).** Not built (no tools/doctor.py in tools/). The spread of requirements is as described: README.md:9-10, ADDING-TRIPS.md:315, docs/DEVELOPING.md:1288-1302, docs/IMPLEMENTATION_REPORT.md:476-484. The hazards are real and recurring, not generic: docs/IMPLEMENTATION_REPORT.md:476-484 records the index vanishing at 13 GB free, the disk is at 19 GB today, `.git/` holds `index 2` to `index 9` with two made this morning (08:40 and 09:11), rendered/ holds 6,136 conflict copies, and `stat.UF_DATALESS` is absent on this Python so the 0x40000000 flag would be hard-coded, which is fine. Observation reproduces except one count.

#### authoring-16. A tidy command for iCloud conflict copies, and a decision on where the checkout lives

**Observation.** On disk under rendered/ sit 6,134 conflict copies beside 3,393 tracked files (e.g. `meta 3.json`, `map-wide 4.webp`), plus `.git/index 2` … `index 9` and two empty `_site/* 2` folders made today; .gitignore:9-19 hides copies under rendered/ and assets/ only, the validator names those inside a trip folder (checks.py:559-576), and the 'never git add -A' rule and two pages of guidance exist because of them (README.md:54-57, ADDING-TRIPS.md:232-247). The cause is the checkout syncing through iCloud Drive with storage optimization, which also offloads half of rendered/ and once removed the git index (report section 11).

**Evidence.** `pipeline map section 6 (counts from find/ls)`; `.gitignore:7-19`; `tools/lib/checks.py:559-576`; `README.md:54-57`; `ADDING-TRIPS.md:232-247`; `docs/IMPLEMENTATION_REPORT.md:476-484`.

**Proposal.** tools/tidy.py (stdlib): list every file and folder that sitecheck.conflict_copy accepts under rendered/, assets/, content/ and _site/, and the `.git/index N` files, as one line each; for a copy under content/ compare bytes with its original and mark 'identical', 'older' or 'DIFFERS'. `--delete` removes only the copies under rendered/, assets/ and _site/, which .gitignore:9-19 already hides and which the renderer never writes (.gitignore:8); copies under content/ and the `.git/index N` files are reported with the instruction to delete them by hand after the comparison (ADDING-TRIPS.md:246). tests/test_tidy.py on a synthetic tree. No publish.py. Then one decision for Eric, with the trade-off stated: move the checkout out of iCloud Drive (e.g. ~/Sites/personal-website, GitHub being the backup of everything tracked; .cache/ and _site/ are rebuilt) or keep it there and run tidy.py before each commit; after a move, the conflict-copy paragraphs in README.md:54-57 and ADDING-TRIPS.md:232-247 shrink to one sentence. Effort S.

**Files.** `tools/tidy.py`, `tests/test_tidy.py`, `README.md`, `ADDING-TRIPS.md`, `docs/TICK_LIST_GUIDE.md`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1, author value 3.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 11

**Risk.** A copy of index.md may hold newer text than the original (ADDING-TRIPS.md:246), hence byte comparison and an opt-in --delete; the validator must keep naming copies under content/ because the loader would otherwise read an ignored `days/02 2.md`.

**Decision for Eric.** Whether the checkout stays in iCloud Drive (Keep Downloaded) or moves to a local folder with GitHub as the backup.

**Review note (condensed; the observation and proposal above are the revised text).** Counts verified: 6,136 conflict-named files under rendered/ beside 3,393 tracked (find, git ls-files), `.git/index 2` to `index 9` (two from today), `_site/regions 2` and `_site/trips 2`, zero copies under content/ and assets/ today; .gitignore:7-19 hides rendered/ and assets/ copies, checks.py:559-576 names those in a trip folder, and sitecheck.conflict_copy (sitecheck.py:55-59) is the shared rule.

#### gap10-05. Take the checkout's 1.4 GB out of iCloud's way; state fresh-Mac costs

**Observation.** The checkout lives under ~/Documents, which iCloud Drive syncs and offloads; on 2026-10-10 that deleted .git/index mid-build (docs/IMPLEMENTATION_REPORT.md:476-484), and .git/ still holds nine iCloud copies of the index (index 2 to index 9, the last two dated today). Measured today the checkout occupies about 1.4 GB: .git 222 MB (pack 182.75 MiB plus 36.42 MiB in 4,749 loose objects, which a `git gc` would pack into about 13 MB), the working tree 232 MB tracked plus 8 MB of rendered conflict copies, _site/ 240 MB (wiped and rewritten by every copying build, so iCloud re-uploads 240 MB per `build.py --check`), and .cache/ 717 MB, of which only 361 MB is render cache (osm 284 MB, tiles 77 MB) and 356 MB is phase evidence (review 166 MB, p4 110 MB, plan2 50 MB, p5 23 MB, preview 6.7 MB). A fresh Mac would transfer about 205 MB (GitHub serves the repacked history), write a 232 MB tree and a 205 MB .git before any build (205 MB is about 16 s at 100 Mbit/s and 65 s at 25 Mbit/s), then rebuild .cache on demand: a new trip fetches only its own OSM cells and tiles, a full forced round re-downloads the 361 MB. A blobless clone (`git clone --filter=blob:none`) saves little today because history is only 1.3x the tree; it becomes the right clone once the pack passes twice the tracked size. The documented path `cd ~/Documents/"Claude Code"/personal-website` (ADDING-TRIPS.md:19) and the workspace CLAUDE.md pin the location.

**Evidence.** `du -sh .git _site .cache rendered content and du -sh .cache/* on 2026-10-13`; `ls -la .git | grep index (index 2 .. index 9)`; `git count-objects -vH (loose 36.42 MiB, 4,749 objects); git pack-objects --stdout for HEAD = 204.7 MB`; `docs/IMPLEMENTATION_REPORT.md:476-484`; `docs/DEVELOPING.md:1264-1270 (a build outside iCloud Drive took 3 s)`; `ADDING-TRIPS.md:19`; `tools/build.py:264-318 (the output folder is emptied before each build)`; `.cache/review, .cache/p4, .cache/p5, .cache/plan2, .cache/preview listings (phase evidence)`.

**Proposal.** Three steps, docs and commands only. (1) One-time cleanup for Eric to run: delete `.git/index 2` to `index 9` (iCloud copies; the report already calls them his to delete); `git gc` once free disk is well above 20 GB, no build or render is running, and ideally after step (3), which packs the 4,749 loose objects (36 MiB) into about 13 MB; after the plan is accepted, move .cache/review, p4, p5, plan2 and preview (356 MB) to the scratchpad or delete them, and state in docs/DEVELOPING.md that .cache/ holds only the render caches osm/ and tiles/. (2) Document, under README.md:114 and docs/DEVELOPING.md:1264, the local commands that keep the 240 MB build out of iCloud using what build.py already has: `python3 tools/build.py --out ~/Library/Caches/personal-website/site --link --check` and the same with `--serve`; `_site/` stays the CI path. No new default, no env var. (3) Add the size angle to authoring-16's location decision: the checkout occupies about 1.4 GB of synced space of which 1.0 GB (.git loose objects, _site, .cache) is regenerable; moving it to a folder iCloud does not sync ends the offloading stalls (29-minute build, WEBSITE_IMPLEMENTATION_LOG.md:21-23) and the index copies; if moved, update ADDING-TRIPS.md:19, README.md and the workspace note, and leave the raw exports and the GPX archive where the tools reach them by path. Record the fresh-Mac numbers (about 205 MB to clone, 232 MB tree) and the rule 'use --filter=blob:none for a new clone once the pack exceeds twice the tracked size'. Files: README.md, docs/DEVELOPING.md, ADDING-TRIPS.md only if the checkout moves. Effort S.

**Files.** `README.md`, `docs/DEVELOPING.md`, `ADDING-TRIPS.md`, `docs/TICK_LIST_GUIDE.md`.

**Effort.** S. Visitor value 1, author value 3.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 11 (the incident) and 10.10 (the stale workspace note); docs/DEVELOPING.md:1270

**Risk.** Moving the checkout changes the path in three documents and the workspace note; a `git gc` is safe but must run while no build or render is writing. A default --out outside the checkout must still pass build.py's unsafe_out rules (tools/build.py:357-373). Nothing here touches content or published files.

**Decision for Eric.** Whether the checkout moves out of iCloud Drive, or stays and builds elsewhere.

**Review revision (applies on top of the text above).** Observation, corrected passages: '... and .git/ still holds eight iCloud copies of the index (index 2 to index 9, the last two dated today).' '... the working tree 232 MB tracked plus 6,134 untracked rendered conflict copies (97.7 MB logical, of which only about 6 MB is on disk today because iCloud has offloaded the rest; CLAUDE.md's ~6,300 duplicates), _site/ 240 MB ...'. Proposal (1), one addition: 'delete the 6,134 conflict copies under rendered/ as well (they are git-ignored and never built, but a fresh sync or Keep Downloaded brings 98 MB of them back onto the disk); `git status` and the ignore rules in .gitignore name the pattern'. Files and the other steps stand.

**Review note (condensed; the observation and proposal above are the revised text).** Partly known and one step would break a documented rule. The state is as described: .git holds index copies 'index 2' through 'index 9' (the last two dated today), .git is 222 MB with 4,749 loose objects (36.42 MiB), _site 240 MB, .cache 717 MB of which osm 284 MB and tiles 77 MB are render cache and review 166, p4 110, plan2 50, p5 23 and preview 6.7 MB are phase evidence; build.py:270-272 empties the output folder on every build, so a copying build really re-uploads 240 MB. Reproduced: du -sh gives .git 222M, _site 240M, .cache 717M, rendered 57M, content 172M; .cache/osm 284M + tiles 77M = 361 MB and review 166M + p4 110M + plan2 50M + p5 23M + preview 6.7M = 356 MB; count-objects 4,749 loose 36.42 MiB, pack 182.75 MiB; pack-objects of HEAD 204.7 MB, so a gc saves about 13 MB; IMPLEMENTATION_REPORT.md:476-484 is the incident; DEVELOPING.md:1266-1268 the 3 s build outside iCloud; ADDING-TRIPS.md:19 the cd line; build.py:272-273 rmtree of OUT, :357-373 unsafe_out (a folder under ~/Library/Caches passes it); pages.yml:35 path: _site; WEBSITE_IMPLEMENTATION_LOG.md:21-23 the 29 min 54 s build; section 10's tenth bullet is the stale workspace note.

#### authoring-12. Index the developer docs and add a repository CLAUDE.md

**Observation.** docs/DEVELOPING.md is 1,439 lines with one H1 and five H2 headings (lines 1, 58, 72, 1130, 1242, 1428); its Rules section runs from line 72 to 1129 (1,058 lines) as 35 top-level bullets with no sub-headings, no table of contents and lines up to 177 characters, so finding the rule for one page means scrolling. docs/CONTENT_GUIDE.md is 1,273 lines (11 numbered sections). The plan, report and log add 2,971 lines of history beside them. The workspace ../CLAUDE.md outside the repository is stale on three points (report 10.10) and the repository itself has no CLAUDE.md and no .claude/ folder, although ADDING-TRIPS.md:307-311 tells the author to let Claude Code run the steps.

**Evidence.** `docs/DEVELOPING.md:1,58,72,1130,1242,1428 (the six headings)`; `docs/DEVELOPING.md:72-1129`; `docs/CONTENT_GUIDE.md:1-1273`; `docs/IMPLEMENTATION_REPORT.md:472-474`; `ADDING-TRIPS.md:307-311`; `ls CLAUDE.md .claude (absent)`.

**Proposal.** (1) Give the Rules section of docs/DEVELOPING.md (lines 72-1129) `###` headings per topic (facts and dates, units, links, maps, photos, accessibility, per page type, JavaScript and no-JS) without moving or rewording any bullet; no generated ToC, no tools/doctoc.py, no test (GitHub renders a heading outline). (2) Add a tracked CLAUDE.md at the repository root: the publishing loop (validate, tests, build --check, stage by path, push to main), Python 3.9 locally and 3.12 in CI, never render in CI, never `git add -A`, pointers to README.md, ADDING-TRIPS.md, docs/DEVELOPING.md and docs/CONTENT_GUIDE.md; keep it free of private detail (public repository) and tell Eric to shorten the site section of the workspace ../CLAUDE.md to a pointer so its three stale sentences (docs/IMPLEMENTATION_REPORT.md:472-474) go. Leave the plan, report and log where they are. Effort S.

**Files.** `docs/DEVELOPING.md`, `CLAUDE.md`.

**Effort.** S. Visitor value 1, author value 3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 10 (stale workspace note)

**Risk.** Every `DEVELOPING.md:NNN` citation in the report, the log and the review maps goes stale; the public repository gains a CLAUDE.md, so keep it free of private detail.

**Review note (condensed; the observation and proposal above are the revised text).** Observation verified: docs/DEVELOPING.md has six H2 headings (lines 1, 58, 72, 1130, 1242, 1428), zero '###' headings, 35 top-level bullets between lines 72 and 1129, longest line 177 chars; docs/CONTENT_GUIDE.md is 1,273 lines; plan+report+log = 922+866+1,183 = 2,971 lines; no CLAUDE.md and no .claude/ in the repository; ADDING-TRIPS.md:307-311 'Or let Claude do it'; report 10.10 (docs/IMPLEMENTATION_REPORT.md:472-474) and the workspace ../CLAUDE.md ('a few seconds', 'build.py also copies them into _site/', 'git add -A', 'Last updated: 2026-10-07') confirm the three stale sentences. Observation verified: DEVELOPING.md is 1,439 lines with six H2s (lines 1, 58, 72, 1130, 1242, 1428), the Rules section 72-1129 has 35 top-level bullets and no sub-heading, longest line 177 characters; no CLAUDE.md or .claude/ in the repository (ls), while ADDING-TRIPS.md:307-311 tells the author to let Claude Code run the steps. Parts (1) sub-headings and (2) a repository CLAUDE.md are worth it and are S together. Everything reproduces except one count: docs/DEVELOPING.md line 1 is the H1 '# Developing the site'; the H2 headings are five (58, 72, 1130, 1242, 1428).

#### authoring-14. Document the one-module command and one honest timing

**Observation.** Measured today module by module (discover -p, Python 3.9.6): 81.4 s in all, of which the four Node harness modules take 40.5 s (test_trips_js 18.7 s for 27 tests, test_ticklist_js 14.7 s for 23, test_series_js 5.7 s for 33, test_maplist_js 1.4 s) because every harness run is its own node process and the stub-rejection tests loop over many wrong stubs (test_trips_js.py:201, 216, 247, 283): 203, 172, 58 and 22 Node starts, 455 in all, for 89 tests. test_a11y_static takes 9.6 s. On the runner the step took 113 s. `python3 -m unittest tests.test_report_page` fails with ModuleNotFoundError: helpers because tests/ is not a package and helpers is only found by `discover -s tests`; no document names the -p form. Four documents give four timings (pages.yml:3 'about a minute', report:255 25 s, DEVELOPING.md:1297 ~75 s, log:954 ~100 s).

**Evidence.** `the reviewer's timing of the test suite on 2026-10-13`; `tests/test_trips_js.py:148-187`; `docs/DEVELOPING.md:1288-1302`; `.github/workflows/pages.yml:3`; `docs/IMPLEMENTATION_REPORT.md:255`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:954`; `gh run view 38429837834 --json jobs`.

**Proposal.** In docs/DEVELOPING.md 'Checking your work' (around lines 1288-1302): name the one-module command `python3 -m unittest discover -s tests -p test_report_page.py` and say why the `tests.test_x` form fails (tests/ is not a package; helpers is found only by discover -s tests); replace the four timings with one sentence (about 80 s on this Mac and 100 s on the runner, half of it the Node harness tests) and delete the 'about a minute' from .github/workflows/pages.yml:3. No tests/run.py and no harness batching unless the suite passes about three minutes. Effort S.

**Files.** `docs/DEVELOPING.md`, `.github/workflows/pages.yml`.

**Effort.** S. Visitor value 1, author value 2, confidence high.

**Risk.** None today. If the suite ever passes about three minutes and a batched harness is built, it must still fail one case at a time and keep the order independence that tests/run_orders.py checks.

**Review note (condensed; the observation and proposal above are the revised text).** Not built, but the observation undercounts the Node starts. Timings verified from the reviewer's timing of the test suite on 2026-10-13 (81 s, the four Node modules 40.5 s) and docs/WEBSITE_IMPLEMENTATION_LOG.md:954 (about 100 s on the runner); I confirmed `python3 -m unittest tests.test_about_units` fails with an import error while `discover -s tests -p test_about_units.py` runs in 0.1 s, and no document names the -p form (grep of DEVELOPING.md).

#### authoring-11. A build diff that names the pages a change touched

**Observation.** Nothing shows which of the 357 pages a content or code edit changed; the compatibility gate compared two builds file by file by hand (report 5.3:327-339), and --only builds a subset that cannot be checked (DEVELOPING.md:1274-1278). A --link build takes 2-4 s, so two builds are cheap.

**Evidence.** `docs/IMPLEMENTATION_REPORT.md:327-339`; `docs/DEVELOPING.md:1264-1278`; `tools/build.py:1-8`.

**Proposal.** Add a paragraph 'Which pages did this change?' to docs/DEVELOPING.md 'Checking your work' (after the --out/--link bullet at 1264-1272): before the change `python3 tools/build.py --out .cache/base --link`, after it `python3 tools/build.py --out .cache/new --link`, then `diff -rq .cache/base .cache/new` for the list of pages and `diff -u .cache/base/<page> .cache/new/<page>` for one page; say that both folders are git-ignored, that --link symlinks the photos, maps and GPX so only pages, feed.xml, sitemap.xml and the search indexes can differ, and that the footer's © year (core.py:1698) is the one line that changes on its own at the new year. No tool, no tests. Effort S.

**Files.** `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1, author value 2, confidence medium.

**Risk.** Keep the base build out of iCloud's way (under .cache/, git-ignored) and small (symlinks).

**Review note (condensed; the observation and proposal above are the revised text).** Feasible, but a new tool with tests is M for what two existing commands already give. Builds are deterministic apart from the footer year (tools/sitegen/core.py:1696-1698 uses date.today().year; feed dates come from content at build.py:234), `.cache/` is not in build.py's _SOURCE_FOLDERS (tools/build.py:354) so `--out .cache/base --link` is accepted, and a --link build takes about 3 s (docs/DEVELOPING.md:1270-1271).

#### authoring-20. Say what is and is not in the repository

**Observation.** content/ (1,698 tracked files) and rendered/ (3,393) are pushed to GitHub (main == origin/main), so every published trip, its published track.gpx and the web photo copies are backed up; `git status --ignored --short` shows nothing outside _site/, .cache/, the rendered/ conflict copies and six Finder `.DS_Store` files, so no author data hides in the checkout. Not backed up by the repository: the original photos handed to --photos (add_trip.py:63-78 writes only the 1600 px, 800 px and card-size WebP copies via tools/lib/photos.py:149-169, EXIF stripped), the original track file (add_trip.py:185 and :199 write a simplified track.gpx and never copy the .fit or source GPX), and the .cache/ downloads (about 700 MB, re-fetchable). The raw Garmin and Strava exports sit beside the repository in the iCloud-synced workspace with no git history. No document in the repository says any of this (no 'backup' in README.md, ADDING-TRIPS.md or docs/).

**Evidence.** `git status --ignored --short (nothing outside rendered/, _site/, .cache/)`; `tools/lib/photos.py:149-169`; `README.md:130-135`; `pipeline map section 8 (.cache size)`.

**Proposal.** One short 'What is and is not in the repository' paragraph in README.md beside the Privacy section and one sentence in ADDING-TRIPS.md step 5 saying add_trip.py never copies the originals, so the source photos and the track file should stay wherever Eric keeps them, and naming the author-only file under .cache/ as the one thing to back up himself. No originals/ folder in the checkout (GPS-bearing originals in a public checkout under iCloud pressure), no new flag, no .gitignore or privacy_audit.py change.

**Files.** `README.md`, `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1, author value 2.7, confidence medium.

**Risk.** No originals/ folder in the checkout: GPS-bearing originals would sit in a public checkout under iCloud pressure; the source photos and track files stay wherever Eric keeps them.

**Decision for Eric.** Where the photo originals and raw exports should be kept (external disk, Time Machine, or nowhere).

**Review note (condensed; the observation and proposal above are the revised text).** Not built and not previously decided: add_trip.py has no --keep-originals (tools/add_trip.py:110-126), .gitignore has no originals/ entry, and no README/ADDING-TRIPS/docs file mentions backups, Time Machine or originals (grep over README.md, ADDING-TRIPS.md, docs/*.md); README.md:130-135 is the Privacy section with nothing on backups; docs/IMPLEMENTATION_REPORT.md and the log have no mention. The documentation half is verified and worth doing: `git status --ignored --short` shows only the rendered/ conflict copies, .DS_Store files, _site/ and .cache/; add_trip.py writes only the stripped WebP copies (tools/lib/photos.py:149-169, tools/add_trip.py:63-78) and a simplified track (tools/add_trip.py:148 `tracks.simplify(pts, 2.0)`, :185 `write_gpx(... simple ...)`), so neither the original photos nor the original .fit/.gpx are in the repository, and no document says so (README.md:130-135 is privacy only; grep finds no 'backup' in README, ADDING-TRIPS or docs/). Mostly reproduces. content/ (1,698 tracked files) and rendered/ (3,393) are tracked and origin is github.com/esichak/personal-website with main == origin/main (git ls-files, git remote -v, git status -sb). add_trip.py never copies the source photos: add_photos (tools/add_trip.py:63-78) calls photolib.web_copies, which writes only the 1600 px, 800 px (.sm) and card (.th) WebP copies with EXIF stripped (tools/lib/photos.py:149-169).

#### authoring-19. Defer the local upload desk; the command-line path covers it

**Observation.** The 2026-10-08 plan describes an optional 'local upload desk' (docs/personal-website-improvement-plan.md:840 in section 20.8, lines 834-844; section 18, :597-603): a loopback-bound browser form with GPX drag/drop, route title, activity, validation, preview and author status/research editing that must call the same importer, bind to loopback only, validate Host/Origin, use a per-session write token, restrict file access to goal data, bound uploads and be excluded from the deployed output. It was never built (docs/WEBSITE_IMPLEMENTATION_LOG.md:362, :694; the only server in tools/ is build.py --serve, tools/build.py:411-414). It is a Phase 2T tick-list feature: its inputs are what `tools/ticklist.py add --title --activity --gpx --notes` already takes (tools/ticklist.py:600-612), and the plan (:595) and docs/TICK_LIST_GUIDE.md:517 already say to ask Claude Code to run that importer; for trips, tools/add_trip.py:108-127 takes the track, title, activity and photos and ADDING-TRIPS.md:307-311 offers 'Or let Claude do it'. Building the desk means a local HTTP server, a token, Host/Origin checks, upload bounds, exclusion from the build and tests for all of it, to replace one terminal command on either path.

**Evidence.** `docs/personal-website-improvement-plan.md:834-844`; `docs/personal-website-improvement-plan.md:597-603`; `ADDING-TRIPS.md:307-311`; `tools/add_trip.py:108-127`.

**Proposal.** Leave the desk out of the new plan and spend the effort on the command-line authoring improvements (publish command, render status, instant preview, validated entry). Record the decision, with the reason above, in the new plan document (not by editing the 2026-10-08 plan). If Eric later wants to add a goal or trip from a browser on the Mac, build it as tools/desk.py under every constraint of plan section 20.8. FILES: the new plan document.

**Files.** `docs/personal-website-improvement-plan.md`.

**Effort.** S. Visitor value 1, author value 1.7, confidence high.

**Already known.** docs/personal-website-improvement-plan.md sections 18 and 20.8

**Risk.** None if deferred; if built, every constraint in plan 20.8 (loopback only, token, no credentials in shipped files) applies.

**Decision for Eric.** Whether a browser form on the Mac is wanted at all, given add_trip.py and Claude Code cover the same inputs.

**Review note (condensed; the observation and proposal above are the revised text).** Not built: no tools/desk.py (tools/ holds add_trip, build, privacy_audit, render, thumbs, ticklist, validate), no upload or form code in tools/sitegen or assets/js, and the history map (b):55 lists the desk with implementation 'none'. But two parts of the observation are off. The deferral itself is right and verified: plan:840 describes the loopback-bound desk and plan:603 calls it optional; the history map (b) line 55 lists it as never built; ADDING-TRIPS.md:307-311 offers the Claude route; tools/add_trip.py:110-127 already takes the track, title, activity, place, party and photos. Two corrections. The core observation reproduces: docs/personal-website-improvement-plan.md:840 (section 20.8, lines 834-844) describes a loopback-only browser form with a per-session token, Host/Origin checks, bounded uploads and exclusion from deployed output, calling the same importer; :603 (section 18) calls it an optional enhancement; it was never built (the review's history map; docs/WEBSITE_IMPLEMENTATION_LOG.md:362 and :694; the only HTTP server in tools/ is build.py --serve at tools/build.py:411-414).

#### authoring-03. Run the unit tests in CI only when code changed; skip docs-only pushes

**Observation.** pages.yml runs the whole suite before every build (.github/workflows/pages.yml:28-31); in the latest run (38429837834) the Unit tests step took 113 s of a 137 s build job, the build itself 4 s. The tests build synthetic trips in temp folders and never read content/ (tests/helpers.py:1-6; no test opens the checkout's content/), so a push that adds a trip or fixes a typo waits almost two minutes for tests it cannot affect. A docs-only commit also triggers a full test, build and deploy of an unchanged site (:6-9). One test does read repository files outside tools/ and tests/: tests/test_privacy_audit.py checks docs/PRIVACY_NOTES.md (:1337-1340) and the workflow files (:1331-1334).

**Evidence.** `.github/workflows/pages.yml:6-9`; `.github/workflows/pages.yml:28-31`; `tests/helpers.py:1-6`; `gh run view 38429837834 --json jobs`.

**Proposal.** In .github/workflows/pages.yml: checkout with enough history to diff (`fetch-depth: 0`, or a `git fetch --depth=1 origin ${{ github.event.before }}` step before the diff); a step `changed` that sets `code=true` when `git diff --name-only ${{ github.event.before }} ${{ github.sha }}` touches tools/, tests/, assets/, .github/ or docs/PRIVACY_NOTES.md, when that diff fails, when `github.event.before` is all zeros (first push, force push), or when the event is workflow_dispatch or schedule; `Unit tests` gets `if: steps.changed.outputs.code == 'true'`. Add `paths-ignore` under `on.push` for docs and Markdown but keep docs/PRIVACY_NOTES.md out of it (a paths-ignore entry for `docs/**` must be paired with a `paths` or a narrower list such as `docs/IMPLEMENTATION_REPORT.md`, `docs/WEBSITE_IMPLEMENTATION_LOG.md`, `docs/personal-website-improvement-plan.md`, `*.md`), and never content/ or rendered/. Keep a weekly `schedule` that runs the full workflow with tests so the suite still runs on the runner's current Python. Document in docs/DEVELOPING.md:1247-1251. Expected: a content push live in about a minute instead of three.

**Files.** `.github/workflows/pages.yml`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1, author value 2.3, confidence high.

**Risk.** A code change can only reach main through a push whose diff names it, so every code commit is still tested; the paths-ignore must not list content/ or rendered/.

**Review note (condensed; the observation and proposal above are the revised text).** pages.yml:28-31 runs the whole suite before every build, with no path filter (pages.yml:6-9): verified. The observation holds: .github/workflows/pages.yml:6-9 triggers on every push to main (plus workflow_dispatch) and :28-31 runs the full suite before the 4 s build; run 38429837834 spent 113 s of a 137 s build job in Unit tests; tests/helpers.py:1-6 says the fixtures never touch content/, and no test opens the real content/ (grep over tests/ finds only temp-dir 'content/trips' paths and a path-constant assertion at tests/test_build_site.py:471-473).

#### perf-13. Pin Node in CI

**Observation.** `pages.yml` pins Python to 3.12 but runs the Node test harnesses on whatever Node the runner image ships (unpinned; report 15.4.5), and the deploy job ends when `deploy-pages` returns, with nothing checking that the published pages are the ones just built. The first deploy failed on a runner patch release (log 945-951), which the docs flag as the class of failure to watch for. A push publishes in 151-188 s (last five runs), so a wrong deploy is also fast.

**Evidence.** `.github/workflows/pages.yml:21-45`; `docs/IMPLEMENTATION_REPORT.md:811-813`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:945-951`; `pipeline map section 5 (151-188 s per run)`; `.github/workflows/pages.yml:24-31`; `docs/IMPLEMENTATION_REPORT.md:811-813`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:945-955`; `docs/DEVELOPING.md:1288-1302`.

**Proposal.** Add `actions/setup-node@v4` with `node-version: '22'` (the version the harness was last verified on, per docs/IMPLEMENTATION_REPORT.md:809-811) before the 'Unit tests' step in .github/workflows/pages.yml (lines 24-29), and note the pinned version beside the Node sentence in docs/DEVELOPING.md (about line 1300). Nothing else: no build sha in the pages and no post-deploy curl. Effort S (under half an hour).

**Files.** `.github/workflows/pages.yml`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1, author value 2.3, confidence high.

**Also covers.** authoring-04 (merged into this finding).

**Already known.** IMPLEMENTATION_REPORT.md 15.4.5 (pin Node); pipeline map section 7 item 13

**Risk.** A pinned major must be bumped on purpose: Phase 15's yearly checklist (gap10-06) carries it. No build sha in the pages (it would make every local build differ from live) and no post-deploy curl.

**Review note (condensed; the observation and proposal above are the revised text).** None of the three parts is built: .github/workflows/pages.yml:24-31 pins Python 3.12 and has no setup-node step; the deploy job ends at actions/deploy-pages@v4 (pages.yml:44-45) with no verification; no GITHUB_SHA, rev-parse or meta name="build" appears in tools/ (grep), and the built pages carry only viewport, description and theme-color metas. Half of this is right and tiny: .github/workflows/pages.yml:24-31 pins Python 3.12 and runs the Node-dependent tests on whatever Node the runner ships, and report 15.4 item 5 (docs/IMPLEMENTATION_REPORT.md:809-811) already names pinning Node as the open fix; three lines with actions/setup-node. The other half is low value and has a cost the finding missed. Observation reproduces: pages.yml:25-27 pins Python 3.12, no setup-node step exists, and the deploy job ends at deploy-pages (lines 44-45) with nothing checking the live pages; IMPLEMENTATION_REPORT.md:811-813 says the runner's Node 22 is untested and asks to pin it; WEBSITE_IMPLEMENTATION_LOG.md:945-951 records the first deploy failing on the runner's Python 3.12.15 patch release; DEVELOPING.md:1288-1302 is the both-Pythons rule; steps.deployment.outputs.page_url is already referenced at pages.yml:42.

#### resilience-08. Parse the script bundle in CI

**Observation.** `build.js_bundle()` concatenates base.js and eight page scripts into one site.js (build.py:93-99); one SyntaxError anywhere stops the whole file, taking the menu, units switch, lightbox and every page script with it on every page. The Node harnesses run base.js, explore.js, trips.js, ticklist.js, series.js and archive.js through `vm` (tests/*_harness.js; `node --check` runs on the harness files, tests/test_maplist_js.py:107-109, test_ticklist_js.py:110-112); section.js is read only by the Python static reader in tests/test_a11y_static.py (`class Script` :793, :1988), multiday.js and notfound.js by no test, and nothing parses the built bundle with a JavaScript engine (`node --check _site/assets/site.js` passes today, run by hand; the scripts are ES5, so an old browser is not the risk, a typo is). `sitecheck.check()` (:698-711) covers links, anchors, ids, metadata, sitemap, feed, indexes and GPX bytes; the accessibility invariants (alt on every img, a name on every link and button, one h1, hidden links out of the tab order) are asserted on a fixture only (tests/test_a11y_static.py:1863-1932). A scan of today's real build found no violation, so both are guards for the next change, not fixes.

**Evidence.** `tools/build.py:93-99`; `tests/test_maplist_js.py:108`; `tests/test_ticklist_js.py:111`; `tools/sitegen/sitecheck.py:698-711`; `tests/test_a11y_static.py:1863-1932`; `_site/assets/site.js`.

**Proposal.** Add one unit test (pattern: tests/test_maplist_js.py:100-109, skipped when node is not on PATH) that writes build.js_bundle() to a temporary file and runs node --check on it, and runs node --check on each assets/js/pages/*.js, so section.js, multiday.js, notfound.js and the concatenation itself are parsed in CI. No sitecheck line, no Python fallback parser, no second a11y pass over the built site (tests/test_a11y_static.py:1863-1932 already asserts those invariants on every generated page type). Effort S.

**Files.** `tests/test_build_cli.py` (or a new `tests/test_js_bundle.py`).

**Effort.** S. Visitor value 1, author value 2.3, confidence high.

**Risk.** Adds one or two seconds to CI; the test skips with a note when node is absent rather than guessing with a Python parser.

**Review revision (applies on top of the text above).** Observation (replace the harness sentence): The Node harnesses run base.js, explore.js, trips.js, ticklist.js, series.js and archive.js through `vm` (tests/page_standin.js:263-264, maplist_js_harness.js:200-202, series_js_harness.js:475), and `node --check` runs on the harness files only (tests/test_maplist_js.py:108, test_ticklist_js.py:111). section.js is read as text by tests/test_a11y_static.py:1978-2031 through the Python `Script` helper (:793), which blanks comments and matches braces but does not parse JavaScript; multiday.js and notfound.js appear in no test; nothing parses the built bundle (`node --check _site/assets/site.js` passes today, run by hand). The rest of the observation stands as written.

**Review note (condensed; the observation and proposal above are the revised text).** Not built, with one correction to the observation: section.js is read by tests/test_a11y_static.py through its own Python static reader (`class Script` at :793, used at :1978 and :1988), so it is not 'loaded by no test', though nothing parses it with a JavaScript engine; multiday.js and notfound.js are read by no test (grep of tests/). Part (1) is real and specific: build.js_bundle() joins base.js and the page scripts with a bare newline (tools/build.py:93-99), so a missing semicolon at the end of one file before the next IIFE is a hazard a per-file check cannot see; the Node tests run --check only on the harness files and on mutated copies of single scripts (tests/test_trips_js.py:282, test_ticklist_js.py:828, test_series_js.py:1041) and nothing parses the built bundle (node --check _site/assets/site.js passes today, run read-only); section.js is only read through the regex mask Script class in tests/test_a11y_static.py:793-815 and :2026-2031, not parsed, and multiday.js and notfound.js by nothing. Mostly reproduces: build.py:93-99 concatenates base.js and the eight page scripts (assets/js/pages/ holds archive, explore, multiday, notfound, section, series, ticklist, trips); `node --check` runs only on the harness files (tests/test_maplist_js.py:108, test_ticklist_js.py:111); `node --check _site/assets/site.js` passes today (node v25.8.2 on PATH; CI is ubuntu-latest, pages.yml:22); sitecheck.check() at sitecheck.py:698-711 covers links, anchors, duplicate ids, metadata, sitemap, feed, indexes, GPX; the a11y invariants are tests/test_a11y_static.py:1863-1932 (one h1, skip link, alt on every img, no nested interactive, a name on every link and button, hidden link not a tab stop) on a fixture site (setUpClass :1716; the alt regex expects 'Synthetic ...').

#### qa-12. Smoke-test the built site in headless Chrome during CI

**Observation.** Every interaction I ran in Chrome today passed (units, explorer URL state and Back/Forward, lightbox, copy link, menu, PCT toggle, tick list, 404 skip link; no console errors on 14 pages; Lighthouse accessibility 100 on trips/ and map/ mobile), but none of it is exercised in a real browser by the repository: the Node harnesses run against tests/page_standin.js, and the docs record Safari, Firefox, a real phone and screen readers as never run. The next regression in trips.js or base.js would reach the live site unseen.

**Evidence.** `Lighthouse reports .cache/plan2/qa/lh-trips/report.json and lh-map/report.json (accessibility 100)`; `list_console_messages on home, trips, ski, map, regions/eastern-sierra, the Matterhorn report and its map page, PCT, tick list, the goal page, Chamonix-Zermatt, other/, hiking/, 404: no errors`; `docs/IMPLEMENTATION_REPORT.md:853-856 (never run in a real browser), tests/page_standin.js, .github/workflows/pages.yml:21-35`.

**Proposal.** add `tools/smoke.py` (stdlib: `subprocess`, `http.server` on a thread, `shutil.which('google-chrome')`) that serves `_site/` and runs `google-chrome --headless=new --disable-gpu --virtual-time-budget=4000 --enable-logging=stderr --dump-dom <url>` for a short list (`trips/?q=tallac&activity=hike`, `map/#region-oregon`, `ski/#season-2022-23`, one report with photos, the PCT page), asserting on DOM text only (status count, selected tab, revealed season, dialog markup) and failing on any `CONSOLE(` error line in stderr; it exits 0 with a notice when Chrome is absent. Run it in pages.yml as its own job after `build` with `continue-on-error: true` (or a separate workflow on push and `workflow_dispatch`), so it reports but never blocks the deploy; document the local run and the Chrome-only scope in docs/DEVELOPING.md, stating that Safari, Firefox, a real phone and screen readers (IMPLEMENTATION_REPORT.md 15.5) remain unrun. Files: tools/smoke.py, .github/workflows/pages.yml, docs/DEVELOPING.md. Effort M. Risk: runner Chrome drift; text assertions only, and the job never gates publishing.

**Files.** `tools/smoke.py`, `.github/workflows/pages.yml`, `docs/DEVELOPING.md`.

**Effort.** M. Visitor value 1, author value 2.3, confidence medium.

**Already known.** IMPLEMENTATION_REPORT.md 15.5 (never run: Safari, Firefox, a real phone, screen readers)

**Risk.** Runner Chrome versions drift; keep assertions on text, not pixels, and make the step non-blocking for a first week before it gates the deploy.

**Decision for Eric.** Whether a failed smoke test may block a deploy.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible within the rules: stdlib `subprocess` + `http.server`, Chrome is present on ubuntu-latest, and `--headless=new --dump-dom` with `--virtual-time-budget` gives the post-script DOM.

#### a11y-11. Check ARIA id references and heading order in build.py --check

**Observation.** sitecheck.py verifies links, anchors, duplicate ids, metadata, sitemap, feed and GPX bytes, but nothing about ARIA: an aria-labelledby, aria-describedby or aria-controls that names a missing id, a role="radio" outside a radiogroup, a role="tab" without its panel, or a heading level that skips (a11y-08) passes the check. The static a11y tests cover a synthetic fixture, not the real pages, and they exist only for the rules Phase 4 wrote.

**Evidence.** `tools/sitegen/sitecheck.py (grep for 'aria' and headings: no matches)`; `tests/test_a11y_static.py:1863-1932`; `docs/DEVELOPING.md:96-101`; `pipeline map section 3.5`.

**Proposal.** Add sitecheck.aria(pages): with html.parser collect ids per page and report ARIA-REF for every aria-labelledby/aria-describedby/aria-controls token that resolves to no id, ARIA-ROLE for radio/option outside their container role and for a role="tab" whose aria-controls resolves to nothing (not 'no tabpanel': map/'s panels get role=tabpanel from archive.js:31 at runtime), HEADING for a level jump of more than one, and NAME for an <a>/<button> whose text, aria-label, aria-labelledby and inner <title>/alt are all empty (the same rule tests/test_a11y_static.py:1921-1930 applies to the fixture). Print at most 40 lines with the other checks' prefix style (BROKEN, DUPLICATE IDS, META …) and document them in docs/CONTENT_GUIDE.md section 5.4's table. Stdlib only, runs in CI on every push. Risk: today's build passes all four rules as scoped here (0 heading jumps, 0 unresolved references across the 355 built pages), so no fix has to land first; keep the tab rule tied to aria-controls or it fails map/.

**Files.** `tools/sitegen/sitecheck.py`, `tests/test_sitecheck.py`, `docs/CONTENT_GUIDE.md`, `docs/DEVELOPING.md`.

**Effort.** M. Visitor value 1, author value 2.3, confidence high.

**Risk.** A new check can fail the current build (the hiking heading order, a11y-08) and so must land after or together with its fixes; keep it warning-only for one deploy if needed.

**Review note (condensed; the observation and proposal above are the revised text).** The observation about sitecheck is right (grep for aria/heading/role in tools/sitegen/sitecheck.py: no matches; its functions are links, anchors, duplicate_ids, metadata, sitemap, feed, indexes, gpx), and the static tests do run on a synthetic fixture, not the build (tests/test_a11y_static.py:64-65). Confirmed: tools/sitegen/sitecheck.py has no 'aria' or heading check (grep returns nothing; its checks are links, anchors, duplicate_ids, metadata, sitemap, feed, indexes at :242-544), and tests/test_a11y_static.py runs on a synthetic fixture (:64-65), not the built site. Feasible with the HTMLParser sitecheck already uses, stdlib, runs in CI. Observation holds: grep -i 'aria|<h[1-6]|heading' in tools/sitegen/sitecheck.py returns nothing; its checks are links/anchors/duplicate_ids/metadata/sitemap/feed/indexes/gpx (:242-698) with prefixes BROKEN, BROKEN ANCHOR, DUPLICATE IDS, META, SITEMAP, FEED, INDEX, GPX; tests/test_a11y_static.py:64 says the fixture is synthetic, and :1921-1930 already has a NAME check (test_every_link_and_button_has_a_name) on that fixture; docs/CONTENT_GUIDE.md 5.4 (:331-345) is the check table; tests/test_sitecheck.py exists.

#### gap7-03. Build drops a gone trip's pin and line from the region maps

**Observation.** rendered/site/meta.json shows 160 trips drawn on the site maps; 27 of them have a pin of their own on at least one map (a cluster of one), 133 only ever merge into a numbered cluster. Drafting or deleting one of the 27 fails `build.py --check` with `BROKEN map/index.html -> ../trips/<slug>/` until `render.py` has run with the internet, so the trip stays up; the other 133 pass but keep their line. The overlay markup makes this a build-time job: each pin is `<a class="mk-pin" href="@@ROOT@@trips/<slug>/" data-key="<slug>">`, each line a `<g class="mk-cat" data-key="<slug>">` with no nested `<g>`, each cluster `<g class="mk-cluster" data-keys="a b c"><title>…</title>…<text>N</text></g>`, every such fragment passes through `core.frag()`, and meta.json lists `trips` and `clusters[].keys` per map. The validator's `_site_map_findings` only warns; the report names the build-side drop as decision 12.8, not built.

**Evidence.** `rendered/site/meta.json (maps[*].trips, maps[*].clusters[].keys/n: 160 drawn, 27 with an own pin, 133 merged, 2026-10-13)`; `rendered/site/region-oregon-desktop.svg.html (mk-pin, mk-cat markup)`; `rendered/site/region-lake-tahoe-desktop.svg.html (mk-cluster data-keys and title)`; `tools/lib/mapkit.py:1531`; `tools/lib/mapkit.py:1538`; `tools/render.py:655-656`; `tools/render.py:673-690`; `tools/sitegen/core.py:450-462`; `tools/sitegen/core.py:484-527`; `tools/sitegen/core.py:99-117`; `tools/lib/checks.py:988-1019`; `tools/sitegen/pages/home.py:217-230`; `tools/sitegen/pages/home.py:273-299`; `tools/sitegen/pages/section.py:359-382`; `tests/test_checks_site_maps.py:90-100`; `ADDING-TRIPS.md:264-290`; `docs/IMPLEMENTATION_REPORT.md:512-514`.

**Proposal.** (1) Prune in one place that every reader shares. Today the site meta is read four separate ways: build.py:271 passes an uncached `core.read_site_meta()` to `register_site`; home.py:279/307 and `core.region_groups(meta=None)` use the cached `core.site_meta()` (core.py:66-70); archive.py:18-20 `site_meta()` re-reads the file for archive.build (archive.py:379) and region.build (region.py:194); and `core.map_block(site_maps=True)` reads rendered/site/meta.json itself (core.py:492-494). So in `core.register_site(site, meta)` compute `gone` = every key in `maps[*].trips` and `clusters[].keys` that is not a listed trip with a track (`core.has_track`) and not an active planned goal, build the pruned meta there (drop the keys, decrement `n`, delete empty clusters), make it what `core.site_meta()` returns, and route `archive.site_meta()` and `map_block(site_maps=True)` through it instead of re-reading the file; keep `read_site_meta()` as the raw on-disk reader for build.py and checks. Then `region_groups`, home's `region_key`, archive's `legend` and region's `map_trips` all see the pruned lists. (2) Give `core.frag(path, here, ns, drop=None)` the set, passed from `map_block(site_maps=True)`: remove `a.mk-pin[data-key in drop]`, remove the balanced `g.mk-cat` or `g.mk-planned` group with that data-key (walk `<g`/`</g>` depth), rewrite each cluster's `data-keys`, its `<title>` (rebuilt from the remaining keys' titles via `site['by_slug']`, joined with '; ' as mapkit.py:1539 does) and its `<text>` count, dropping a cluster that reaches 0; a cluster left with one key stays a cluster of one until the next render. Warn once per map when a key in `drop` is not found in the fragment. (3) `checks._site_map_findings` keeps a WARNING with new wording: the build leaves the trip's pin and line out; run `python3 tools/render.py --site` when online so the frame and merged pins are redrawn; update tests/test_checks_site_maps.py and the docs/CONTENT_GUIDE.md row at line 212. (4) Tests: a synthetic overlay built from mapkit's exact strings through `frag(drop=…)`, a test that the pruned meta reaches archive, region, home and the ski panel, and a built-site check that a drafted own-pin trip passes `--check`. (5) ADDING-TRIPS 'Taking a trip off the site' shrinks to: add `draft: true` or delete the folder, `build.py --check`, commit, push, from anywhere; the render only tidies later.

**Files.** `tools/sitegen/core.py`, `tools/lib/checks.py`, `tests/test_checks_site_maps.py`, `tests/test_site_map_prune.py`, `ADDING-TRIPS.md`, `docs/CONTENT_GUIDE.md`, `README.md`.

**Effort.** M. Visitor value 1, author value 3.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 10 'Taking a trip off the site needs a render' and section 12 decision 8

**Risk.** The parser must stay in step with mapkit's output; the unfound-key warning and the synthetic test guard that. The map keeps the frame it was rendered with and a cluster of one looks like a cluster until the next render. Facts-only and verbatim rules are untouched; taking a trip off faster is a privacy gain, and the removal policy in docs/PRIVACY_NOTES.md section 6 is unchanged.

**Decision for Eric.** Decision 12.8 itself: whether the build should leave a drafted or deleted trip's pin and line out by itself (new behavior).

**Review note (condensed; the observation and proposal above are the revised text).** The observation is exact: rendered/site/meta.json has 24 maps, 160 trips drawn, 27 with a cluster of one somewhere and 133 only ever merged (counted today); mapkit.py:1531 and :1538-1539 emit the quoted pin and cluster markup; core.frag (core.py:450-462) does plain string replacement with no drop; checks.py:987-1018 only warns; the report's decision 12.8 (docs/IMPLEMENTATION_REPORT.md:512-514) names this as not built. Observation reproduces exactly: a script over rendered/site/meta.json (24 maps) finds 160 drawn trips, 27 with a cluster of one on at least one map, 133 only ever merged; rendered/site/region-oregon-desktop.svg.html has `<a class="mk-pin" href="@@ROOT@@trips/<slug>/" data-key="<slug>" aria-label=…>` and `<g class="mk-cat" data-key="<slug>" …>` with no nested <g>; region-lake-tahoe-desktop.svg.html has `<g class="mk-cluster" aria-hidden="true" data-keys="a b c"><title>…` and an mk-planned group; the strings come from tools/lib/mapkit.py:1531 and 1538-1539 (titles joined with '; ', `<text>` count); tools/lib/checks.py:989-991's own docstring says the check fails when a map still has a pin of the trip's own, and 1012-1017 only warns; docs/IMPLEMENTATION_REPORT.md:512-514 is decision 12.8 'not built'; ADDING-TRIPS.md:271-276 documents the BROKEN lines; tests/test_checks_site_maps.py:90-100 and the CONTENT_GUIDE row (docs/CONTENT_GUIDE.md:212) exist; core.has_track (core.py:1035), site['by_slug'] (home.py:218), archive.legend (archive.py:107) and region.map_trips (region.py:166) exist.

**Gates.** The phase is done when every line below holds and is recorded in the log entry:

1. tests/test_publish_cli.py runs against a temporary git repository with a synthetic trip: refuses off main, refuses when unrelated paths are staged, refuses a conflict-copy name, refuses an unrendered slug without --allow-unrendered, stages exactly content/trips/<slug>, rendered/trips/<slug>, rendered/site when changed and content/home.json when changed, commits 'Add <title>', --dry-run writes nothing, and grep finds no 'git add -A' or 'git add .' in tools/publish.py; the check it runs is build.main(['--out', '.cache/publish-site', '--link', '--check']) and takes about 4 s.
2. With gh signed in, publish.py --push finds the run for HEAD, watches it, and prints the live URL of each trip on success or 'gh run view <id> --log-failed' plus 'the old site is still up' on failure; without gh it prints the Actions URL and exits 0.
3. python3 tools/check.py runs validate.py, the suite on both Pythons with -W error and the linked --check, printing one summary line per step with its time, and exits non-zero when any step fails; --quick skips the second Python.
4. tools/tidy.py lists the conflict copies under rendered/, assets/, content/ and _site/ and the .git/index N files, marks a content/ copy identical/older/DIFFERS by byte comparison, and --delete removes only the git-ignored copies (tests/test_tidy.py on a synthetic tree); after Eric runs it, deletes .git/index 2..9 and runs git gc, git count-objects -v reports loose objects under 1,000 and git status shows no ' 2'/' 3' names.
5. tools/doctor.py is read-only (running it twice leaves the tree byte-identical), finishes in under 2 s, and flags: free disk under 30 GB, a missing .git/index with the read-tree recipe, stray index copies with the rm line, branch/clean-tree/ahead-behind/identity, conflict copies by top folder, offloaded tracked files under rendered/ and content/ (macOS only; 'not checked' elsewhere), cwebp absent; tests/test_doctor.py on a synthetic repo.
6. ADDING-TRIPS.md 'When something goes wrong' has the Before the push, After the push and The Mac parts (red X by failing step, site wrong after a push, index missing or unreadable, slow build, map without roads), the github.com draft warning sits under Quick fixes, and the rollback (git revert and gh run rerun within 30 days, never force-push) was rehearsed once on a doc-only commit with the measured minutes written into the doc; gh workflow run pages.yml -f ref=<HEAD sha> was tried once and the github-pages environment accepted it.
7. README.md has 'Setting up a new Mac' (xcode-select, Homebrew, brew install webp gh node python@3.12, gh auth login, git clone, doctor, tests, --check; the first render fetches about 360 MB into .cache/; what is not in the clone), a 'What is and is not in the repository' paragraph, the --out ~/Library/Caches build commands, and the upload-desk deferral; ADDING-TRIPS.md:19 and docs/TICK_LIST_GUIDE.md:139 no longer hard-code the iCloud path; a tracked CLAUDE.md at the repository root names the three checks, stage-by-path, 3.9/3.12 and never-render-in-CI; DEVELOPING.md's Rules section has ### headings, names the one-module command (discover -s tests -p test_x.py), gives one timing sentence, and the two-builds diff recipe.
8. pages.yml: actions/setup-node@v4 at node-version 22 before the tests; a docs-only push (Markdown outside docs/PRIVACY_NOTES.md) triggers no run, a content-only push skips the Unit tests step and deploys in about a minute (one run checked with gh run list), a push touching tools/, tests/, assets/, .github/ or PRIVACY_NOTES.md runs them; tools/smoke.py runs as a non-gating job (continue-on-error) against trips/?q=tallac&activity=hike, map/#region-oregon, ski/#season-2022-23, one report and the PCT page and exits 0 when Chrome is absent.
9. A unit test runs node --check on build.js_bundle() output and on each assets/js/pages/*.js (skipped without node); sitecheck's ARIA-REF and HEADING rules report 0 findings on today's 355 built pages and fail on fixtures with a dangling aria-controls and a skipped heading level.
10. gap7-03: a fixture region map with a cluster-of-one pin for a trip set draft: true passes build.py --check without a render, the pin and its mk-cat line are absent from the built overlay, cluster titles and counts are unchanged, an unknown key in drop warns once, and the validator's reworded WARNING names 'render.py --site when online'; ADDING-TRIPS 'Taking a trip off the site' shrinks to draft: true or delete, --check, commit, push.

**Tests to add.** New: `tests/test_doctor.py`, `tests/test_publish_cli.py`, `tests/test_site_map_prune.py`, `tests/test_tidy.py` (and `tests/test_js_bundle.py` only if resilience-08's test does not fit `tests/test_build_cli.py`). Extended: `tests/test_build_cli.py`, `tests/test_checks_site_maps.py`, `tests/test_sitecheck.py`. Plus the checks the gates name that no unit test covers: A temporary git repository for `tests/test_publish_cli.py`; one real content push timed with `gh run list`; `gh workflow run pages.yml -f ref=<sha>` tried once; the smoke job's first run checked in the Actions log.

**Screenshots to capture.** None of the site. Keep `gh run list` output for the one-minute content deploy, the rehearsed rollback's timings, and `git count-objects -v` before and after the tidy in the log entry.

**Author inputs needed.** Where the checkout lives (decision 1) and whether the build drops a gone trip's pin itself (decision 2); the rollback rehearsal on a doc-only commit; `gh auth login` on the Mac.

### Phase 9. Content: inventory, editing a published trip, and places for Eric's words

**Goal.** Give Eric a per-trip table of what each report lacks and the places, titles and taxonomy to fix, tools to change a published trip without hand surgery (a better recording, new photos, titles without a 76-file render, dates), and the dormant slots for his own words (About body and portrait, region introductions, summits, year totals, home region maps) that show nothing until he writes.

**Prerequisites.** Phase 6 (the add_trip tests, the frontmatter fix, --retime). Eric's decisions: region and place merges, retitling the 24 Strava titles, the published_at rule, the summits vocabulary, --update's stats default; an afternoon from Eric for the 79 place: lines.

**Decisions this phase waits on.**

- Region and place merges (copy-16): recommended Idaho into Boise and Kingsbury Grade into Kingsbury (keep the spelling that has a page), Yosemite stays
- Retitle the 24 Strava default titles by hand (copy-05): recommended yes
- published_at: empty line from add_trip, filled on the day of the push, feed and sitemap use it when set, old reports left without (12.5, 12.6)
- Summits field vocabulary summit / turned-around / traverse (features-05)
- --update replaces stats by default with --keep-stats to keep hand corrections; no --strip-times on update while PRIVACY_NOTES 6.2 is open (gap8-02)
- Which two regions the home page maps (ia-15): recommended keep Lake Tahoe and Eastern Sierra, the latter carries the PCT days
- Calendar years for the By-year block, the ski row linking the explorer (features-01)

**Findings in this phase** (18, in working order): copy-07, copy-05, copy-17, copy-16, ia-16, gap8-02, gap8-03, gap8-09, gap8-04, seo-10, copy-01, features-11, visual-16, features-17, features-05, features-01, ia-19, ia-15.

#### copy-07. A per-trip content report: which trips lack what

**Observation.** validate.py -v lists 467 notes: 79 'no place', 75 'no write-up', 61 'no photos', 109 'no title' (PCT days) and 143 'N photos without a caption' (checks.py:723, 838-845), as one line per finding with no per-trip view. Nothing reports that 164 of 167 covers are automatic picks (3 cover_photo lines in content/), that card_summary is set on 0 trips, that 89 trips have a place and 13 name a party, or which titles are Strava defaults. CONTENT_GUIDE.md:98-99 says 'An automatic pick is a fallback, not an editorial choice' but gives Eric no list to work from.

**Evidence.** `tools/validate.py -v (run today: 0 errors, 1 warning, 467 notes)`; `tools/lib/checks.py:723`; `tools/lib/checks.py:838-845`; `docs/CONTENT_GUIDE.md:88-99`; `docs/CONTENT_GUIDE.md:142-162`; `content/trips/*/index.md (grep counts: cover_photo 3, card_summary 0, place 89, party 13)`.

**Proposal.** tools/content_report.py (stdlib, read-only, reuses content.load_all and content.resolve_cover): one row per published trip, newest first: date · slug · title flag (Strava default / shared ×N) · write-up chars · photos · cover (explicit / auto / none) · place · party · card_summary. Options --missing place|writeup|photos|cover|summary and --markdown (writes .cache/content-report.md, git-ignored). Correct the observation to '103 of the 106 photo covers are automatic picks; 61 trips have no photo'. Demote checks.py:723's per-trip 'photos without a caption' note to one count line so -v stays readable. Document in docs/CONTENT_GUIDE.md next to :98-99. Defer --featured and --taxonomy. The tool never writes to content/. Effort M.

**Files.** `tools/content_report.py (new)`, `tools/lib/checks.py`, `docs/CONTENT_GUIDE.md`, `tests/`.

**Effort.** M. Visitor value 1, author value 3.7, confidence high.

**Risk.** The tool must never write to content/; it reads and prints. Place names it prints are already public on the site.

**Review note (condensed; the observation and proposal above are the revised text).** The validator counts reproduce (validate.py -v: 79 no place, 75 no write-up, 61 no photos, 109 no title, 143 photos without a caption, 467 notes; checks.py:723 and :838-845 emit one line per finding), and the front-matter counts hold (cover_photo 3, card_summary 0, party 13). validate.py -v run today: 0 errors, 1 warning, 467 notes; counts reproduce exactly (79 'no place', 75 'no write-up', 61 'no photos', 109 'no title', 143 '… without a caption'), written at checks.py:723 and 838-845. CONTENT_GUIDE.md:98-99 says 'An automatic pick is a fallback, not an editorial choice'.

#### copy-05. Flag Strava default titles for retitling, and warn on import

**Observation.** 24 published titles are Strava's automatic names: 'Ride near Day Valley' (7), 'Ride near Santa Cruz', 'Ride near South Lake Tahoe', 'Hike near South Lake Tahoe', 'Paddle near Incline Village' (2 each), nine more 'Ride/Hike/Paddle near …' and 'Morning Stroll' (grep of title: lines). On a card the place then appears twice ('DEC 5, 2021 · DAY VALLEY' over 'Ride near Day Valley'); seven pages share one H1 and are told apart only by the date that report.py:647-650 adds to the <title>. add_trip.py's clean_title (add_trip.py:45-49) passes these names through unchanged.

**Evidence.** `content/trips/*/index.md title: lines (grep count)`; `tools/sitegen/pages/report.py:647-650`; `tools/add_trip.py:45-49`; `_site/trips/index.html (card data-slug="ride-near-day-valley-2021-12-05")`; `_site/trips/ride-near-day-valley/index.html (<title>)`.

**Proposal.** (a) The content report of copy-07 lists titles matching ^(Morning|Afternoon|Evening|Lunch|Night)?\s?(Ride|Hike|Walk|Run|Paddle|Swim|Stroll)( near .+)?$ and titles shared by two or more trips, so Eric can retitle in index.md (the folder name is the URL, so a new title changes no address). (b) add_trip.py prints `note: title looks like a Strava default; pass --title` when the name it took from a Strava export's activities.csv or from a GPX file matches. Never retitle automatically. FILES: tools/content_report.py (new), tools/add_trip.py, ADDING-TRIPS.md (repository root; there is no docs/ADDING-TRIPS.md).

**Files.** `tools/content_report.py (new)`, `tools/add_trip.py`, `ADDING-TRIPS.md`.

**Effort.** S. Visitor value 1.3, author value 2, confidence high.

**Risk.** Titles are Eric's facts: the tools only list and warn.

**Decision for Eric.** Whether to retitle the 24 trips at all; a Strava name is also a true title.

**Review note (condensed; the observation and proposal above are the revised text).** Reproduced: 24 published titles match the Strava-default pattern ('Ride near Day Valley' ×7, 'Hike near South Lake Tahoe', 'Paddle near Incline Village', 'Ride near South Lake Tahoe', 'Ride near Santa Cruz' ×2 each, nine more 'near …' titles and 'Morning Stroll'); the explorer card for ride-near-day-valley-2021-12-05 reads 'DEC 5, 2021, DAY VALLEY' over 'Ride near Day Valley'; seven folders share the H1 and the <title> adds the date ('Ride near Day Valley, Dec 5, 2021 · Eric Sichak', report.py:647-650); clean_title (add_trip.py:45-49) only strips emoji and normalizes dashes.

#### copy-17. List the cover and featured photos' alt texts for Eric's review

**Observation.** All 246 trip photos and 152 day photos carry alt text (counted: one alt: per file: entry), 74-129 characters for trip photos and 75-131 for day photos, in one style ('Wind-sculpted snowy ridges and scattered trees stretch to distant white peaks under a deep blue sky.', content/trips/mount-glory-2026-03-03/index.md:23); they arrived in the bulk-import commit 6abc634 ('Add 144 trips … alt text for all photos'), not trip by trip. The cover's alt is also published as og:image:alt and twitter:image:alt (_site/trips/matterhorn-peak-west-couloir/index.html) and read in the photo viewer ('Photo N of M. <alt>', base.js:317). An alt that misdescribes a scene is an invented fact on the page.

**Evidence.** `content/trips/*/index.md alt: lines (count 246, lengths 83-138)`; `git log -S 'Wind-sculpted' (commit 6abc634 message)`; `_site/trips/matterhorn-peak-west-couloir/index.html (og:image:alt)`; `assets/js/base.js:317`; `tools/sitegen/core.py:1514-1522`.

**Proposal.** content_report.py --alt prints, for the home featured trips, each region page's Featured picks and every explicit or automatic cover, the photo file and its alt text, so Eric can correct the ones most seen; CONTENT_GUIDE.md notes that alt text is a factual description he owns. No automatic rewriting.

**Files.** `tools/content_report.py (new)`, `docs/CONTENT_GUIDE.md`.

**Effort.** S. Visitor value 1.3, author value 2, confidence medium.

**Risk.** None; the tool reads only.

**Decision for Eric.** Whether to review the bulk-written alt texts.

**Review revision (applies on top of the text above).** Observation as written, minus the guide: CONTENT_GUIDE.md:562-563 and 911-912 already state that the cover's alt is the description Eric publishes. Proposal: a read-only listing (content_report.py --alt if copy-07 lands, else a small tools/alt_list.py) of the photo file and alt text for the home featured trips (content/home.json), each region page's Featured picks and every explicit or automatic cover, so Eric can correct the most-seen descriptions first; no automatic rewriting and no new guide text. Effort S. Risk: none; the tool reads only.

**Review note (condensed; the observation and proposal above are the revised text).** Evidence verified: 246 trip-photo and 152 day-photo alt lines (my count, lengths 74-131 without quotes); commit 6abc634 wrote them in bulk ('alt text for all photos'); _site/trips/matterhorn-peak-west-couloir/index.html carries og:image:alt and twitter:image:alt from the cover alt via core.share_photo (core.py:1514-1522); base.js:317 reads it aloud in the viewer. Feasible, read-only, S. Counts hold: 246 alt: lines for 246 file: entries in content/trips/*/index.md and 152 of each in days/*.md. The length range is wrong: measured on the alt value the trip photos run 74-129 characters and day photos 75-131; 83-138 is the whole line including the 9-character '    alt: ' prefix.

#### copy-16. Show Eric the region and place inventory before the head lines expose it

**Observation.** front matter uses 15 region values, including 'Boise' (5 trips) beside 'Idaho' (1), and places 'Kingsbury' (4) beside 'Kingsbury Grade' (3); 79 trips have no place, so their cards and rows print the region instead (core.py:1180, 1274); the section head shows regions for Ski but places for Climbing because all climbs share one region (section.py:50-61); checks.py:948-965 warns on case variants of a region only; CONTENT_GUIDE.md:607 asks only for one spelling. Known: IMPLEMENTATION_REPORT.md section 14.6.

**Evidence.** `content/trips/*/index.md region: and place: values (counts via tools/lib/content.load_all and grep)`; `tools/sitegen/pages/section.py:49-71`; `tools/lib/checks.py:949-985`; `_site/ski/index.html and _site/climbing/index.html (sec-head text)`; `tools/sitegen/core.py:1273`.

**Proposal.** a listing of every region and place with its count and slugs (content_report.py --taxonomy if copy-07 lands, else a 20-line tools/taxonomy.py), and one paragraph in docs/CONTENT_GUIDE.md: region = the map grouping, place = the named area inside it. Eric decides the merges. Rules for a merge: keep the spelling that has a region page (regions/boise/ and regions/eastern-sierra/ exist; idaho and yosemite have none), run `render.py --site --force`, and check the build for DUPLICATE IDS. Effort S. Risk: merging into the name without a page retires a region URL.

**Files.** `tools/content_report.py (new)`, `tools/sitegen/pages/section.py`, `docs/CONTENT_GUIDE.md`.

**Effort.** S. Visitor value 1.7, author value 2.7, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 14.6 (a region spelled two ways is two regions)

**Risk.** Region changes touch rendered/site and the region pages; half-done renames fail the build with DUPLICATE IDS.

**Decision for Eric.** Which regions and places to merge or keep.

**Review revision (applies on top of the text above).** Same observation and proposal, with two additions: (1) ADDING-TRIPS.md:39-40 already lists the 15 region names by hand ('Regions already on the site: …'), without counts, slugs or places; content_report.py --taxonomy should either generate that list or the doc should point at the tool, so the two do not drift. (2) The region/place rule belongs beside ADDING-TRIPS.md:31-32, which today defines --place as 'The specific spot' and --region as an existing name spelled exactly, as well as in docs/CONTENT_GUIDE.md. The merges (Boise/Idaho, Eastern Sierra/Yosemite, Kingsbury/Kingsbury Grade) remain Eric's decision; nothing in the plan, log or report decided them.

**Review note (condensed; the observation and proposal above are the revised text).** Counts verified by loading tools/lib/content.load_all(): 168 trips, 15 regions (Lake Tahoe 87, Santa Cruz 45, Eastern Sierra 7, Bay Area 5, Boise 5, Alps 4, Tetons 4, Oregon 3, Utah 2, Arizona/Idaho/Minnesota/Pacific Crest Trail/Washington/Yosemite 1 each), places Kingsbury 4 and Kingsbury Grade 3, 79 trips with no place. Counts verified from content/trips/*/index.md: 15 regions, Boise 5 / Idaho 1, Eastern Sierra 7 / Yosemite 1, Kingsbury 4 / Kingsbury Grade 3, 79 trips without a place; section.py:50-71 area_names switches from regions to places when every report shares one region; checks.py:948-965 warns on case variants only; core.py:1180 and 1274 fall back to the region; IMPLEMENTATION_REPORT.md:662 is the known 'two ways is two regions' limit; CONTENT_GUIDE.md:607 says only to spell a region the same way, so a region-vs-place paragraph is new.

#### ia-16. Close the search index's place and peak gaps with author tooling

**Observation.** The search index holds title, place+region, activity+aliases+peaks and write-ups (search.py:47-70). 79 of 168 trips have no `place:` (ski 28, hike 20, mtb 19, climb 9, other 3); 75 of the 167 published reports have no write-up at all (the 75 entries with empty write-up text in trips/search.json; 85 have an empty index.md body, the rest carry theirs in days/); 11 carry `map: peaks:` (16 names) and one alias exists in all content (PCT). The placeholder promises search "by name, place, region, activity or peak", but a peak or trailhead that is in none of those fields or the write-up finds nothing; "lovers leap" fails on the apostrophe (known: normalize() turns Lover's into 'lover s', CONTENT_GUIDE.md:397-398 documents it, WEBSITE_IMPLEMENTATION_LOG.md:215-216 lists it).

**Evidence.** `tools/sitegen/search.py:47-70 (entry fields)`; `content/trips/*/index.md counts (grep: place set on 89, peaks on 11, search_aliases on 1)`; `_site/trips/search.json (75 entries with empty write-up text; 'spring' no hits)`; `docs/CONTENT_GUIDE.md:391-416 (what is searched; aliases)`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:215-216 (lovers leap)`.

**Proposal.** (1) tools/lib/checks.py: a NOTE per published trip without `place:` and per trip whose title contains Peak, Mount, Mountain, Couloir, Chute, Bowl or Lake but has no `map: peaks:`; `validate.py -v` already prints the notes (validate.py:55), so no new flag; Claude Code fills `place:` only from Eric's answers, names not addresses (PRIVACY_NOTES level). (2) search.py normalize(): drop apostrophes (ASCII and U+2019) before splitting, mirrored in explore.js norm() with a case in tests/norm_cases.json and tests/test_search.py; rewrite the apostrophe paragraph at docs/CONTENT_GUIDE.md:397-399 and close the log item. (3) CONTENT_GUIDE: a short 'what makes a report findable' checklist (place, peaks, an alias for nicknames). Effort M. Part (2), the apostrophe rule, lands in Phase 7 as resilience-03; this phase builds (1) and (3) only, with a checks test for the peaks note.

**Files.** `tools/lib/checks.py`, `tests/test_checks.py`, `docs/CONTENT_GUIDE.md`.

**Effort.** M. Visitor value 3.3, author value 3, confidence high.

**Already known.** docs/WEBSITE_IMPLEMENTATION_LOG.md Phase 2 "Remaining issues" (lovers leap)

**Risk.** Facts only: no place or peak is ever inferred by the tool. A `place:` that names a trailhead or town is already visible on the map; keep to names, not addresses (PRIVACY_NOTES level). normalize() and norm() must stay identical.

**Review revision (applies on top of the text above).** Proposal: (1) unchanged (checks.py NOTEs; `tools/validate.py --places` table; Claude Code fills `place:` only from Eric's answers). (2) search.py normalize(): drop apostrophes before splitting (lover's -> lovers) and mirror it in assets/js/pages/explore.js norm() (the shared helper that trips.js:15 and the tick list take from `Explore`; trips.js has no norm() of its own), with a case in tests/norm_cases.json (shared by tests/test_search.py), and rewrite CONTENT_GUIDE.md:397-398, which today documents the apostrophe as a word break and tells the author to add an alias. (3) unchanged. FILES: tools/lib/checks.py, tools/validate.py, tools/sitegen/search.py, assets/js/pages/explore.js, tests/norm_cases.json, tests/test_search.py, docs/CONTENT_GUIDE.md.

**Review note (condensed; the observation and proposal above are the revised text).** Part of (1) already exists: tools/lib/checks.py:836-838 emits 'NOTE …: no place' for every published trip without a place (79 today, listed by python3 tools/validate.py -v), alongside 'no write-up' and 'no photos' notes; there is no peaks note (checks.py:467-478 only validates the shape of map.peaks) and no --places flag (validate.py takes --content, --site, --strict, --json, -q, -v, --today). Counts verified in content (place on 89 of 168, peaks on 11, one alias, 86 empty bodies) and the apostrophe rule is real: search.py:30-37 turns every non-alphanumeric run into a space and explore.js:9-10 mirrors it; docs/CONTENT_GUIDE.md:397-399 documents the workaround and the log lists it as open (WEBSITE_IMPLEMENTATION_LOG.md:215-216). Core observation holds but three numbers and one file are wrong.

#### gap8-02. add_trip.py --update: replace the track, keep the words and photos

**Observation.** The frequent change is not a new trip but a changed one: a better recording (a Garmin file after a Strava GPX), a corrected time zone, a track with timestamps stripped. Everything derived from the track (date, start_time, timezone, route_shape, stats) is written once at import (tools/add_trip.py:147-149, :186-191) and nothing recomputes it for an existing folder; the only tool path is --force, which erases the author's text (gap8-01). strava_id, written on 156 trips, is read by nothing (tools/lib/checks.py:60), although it is exactly what would locate the activity in a newer Strava export. tools/ticklist.py:92-99 (write_index) is the one existing helper that replaces an index.md through frontmatter.render, and the split->render round trip reproduces all 352 index.md and days/*.md files byte for byte (measured today).

**Evidence.** `tools/add_trip.py:147-149`; `tools/add_trip.py:186-198`; `tools/lib/checks.py:60`; `tools/ticklist.py:92-99`; `tools/lib/frontmatter.py:13-21`; `tools/lib/frontmatter.py:154-185`; `tools/render.py:430-434`.

**Proposal.** Add `python3 tools/add_trip.py TRACK --update SLUG [--photos ...] [--keep-stats] [--timezone Z] [--dry-run] [--no-render]`, and `--strava-export DIR --update SLUG` that finds the activity by the trip's own strava_id (strava.Export.by_id, tools/lib/strava.py:59) when --strava-id is absent. Steps: read index.md with frontmatter.split; compute date, start_time, route_shape and stats from the new track (strava.stats_from when the record has them; untouched with --keep-stats); timezone: the existing line wins unless --timezone is given; update the existing dict in place so dumps keeps the file's key order; every other key and the body stay verbatim (the placeholder comment is replaced only by a Strava description, and only while the body is still the placeholder); photos: keep the list, number new files from the highest existing NN + 1 using add_photos(start=...) and alt: ''; rewrite track.gpx through tracks.simplify/write_gpx with the trip's title and activity. --dry-run prints difflib.unified_diff of index.md plus the files that would be written and touches nothing. After writing: run checks.run() (tools/lib/checks.py:1211) filtered to the file and print its findings, then render.py SLUG unless --no-render, saying the maps are redrawn because the track bytes are in the render hash. Refuse a folder with days/ (gap8-08 covers days). Tests in tests/test_add_trip.py on the tests/test_thumbs.py model (mock.patch.object recorders in place of photolib.web_copies and subprocess.run, since add_trip calls sips directly at :72; test_thumbs itself patches thumb_copy and have_cwebp, not web_copies): keeps body/alt/beta/map/cover/card_summary; replaces stats and route_shape; appends photos with the next number; --dry-run writes nothing and prints a diff; unknown slug exits with a message. An optional --strip-times on update (rewrite the GPX without timestamps; the page keeps date and start time) touches the privacy policy and is Eric's call. Add the command to ADDING-TRIPS.md (gap8-09), README.md's 'Add a trip' command block (:16-27) and the file list in docs/DEVELOPING.md (:6-37).

**Files.** `tools/add_trip.py`, `tests/test_add_trip.py`, `ADDING-TRIPS.md`, `README.md`, `docs/DEVELOPING.md`, `docs/PRIVACY_NOTES.md`.

**Effort.** M. Visitor value 1, author value 3.3, confidence high.

**Risk.** Facts only: every replaced value comes from the track or the Strava record; the write-up stays verbatim; the folder is never renamed so URLs hold. A replaced track changes the render hash, so rendered/trips/<slug> must be committed with it.

**Decision for Eric.** Whether --update may replace stats Eric corrected by hand (proposed default: replaces; --keep-stats keeps them), and whether --strip-times belongs on it (docs/PRIVACY_NOTES.md section 6).

**Review note (condensed; the observation and proposal above are the revised text).** The gap is real and already documented as a limit: docs/PRIVACY_NOTES.md section 6.1 says of a published track that 'nothing recomputes what the import wrote down' and lists the hand edits (start_time, stats, date, then render). Observation reproduced: date/start_time/timezone/route_shape/stats are written once at :147-149 and :186-191; strava_id is on 156 of 168 index.md files and checks.py:60 says nothing reads it; split->render reproduced all 352 index.md and days/*.md files byte for byte in a run today; ticklist.write_index is at :93-100 (cited 92-99).

#### gap8-03. trip_photos.py: add or remove photos on a published trip

**Observation.** add_photos() (tools/add_trip.py:63-80) is reached only from the new-trip path (:193) and --day-of (:167). docs/CONTENT_GUIDE.md:308 says of a photo copied in by hand: add_trip.py writes the 800 px copy for the photos it imports and 'no tool adds one afterwards'; ADDING-TRIPS.md has no step for adding photos to a trip that is on the site. So today it means sips and cwebp by hand for the three copies (tools/lib/photos.py:149-169), reading the pixel size and typing a photos: entry with w and h. Removal is the mirror: delete the entry and the three files, because a file left in photos/ is published all the same (tools/build.py:189-190 copies every file; tools/lib/checks.py:731-735 only warns). thumbs.py covers the .th copy alone (tools/thumbs.py:1-18). 106 of 168 trips have photos.

**Evidence.** `tools/add_trip.py:63-80`; `tools/add_trip.py:167`; `tools/add_trip.py:193`; `docs/CONTENT_GUIDE.md:308`; `tools/lib/photos.py:149-169`; `tools/build.py:188-189`; `tools/lib/checks.py:733-736`; `tools/thumbs.py:1-18`.

**Proposal.** New `tools/trip_photos.py SLUG FILE|DIR... [--day NN] [--cover] [--dry-run]`. Move collect_photos and add_photos out of add_trip.py into tools/lib/photos.py as import_photos(folder, files, prefix='', start=1) so add_trip.py and the new tool share one implementation. The tool numbers after the highest existing NN for the prefix ('' for index.md, 'dNN-' for a day) across .webp and .jpg, writes the three copies through web_copies (HEIC/PNG through sips as add_trip.py:70-73 does), appends {file, w, h, alt: ''} to photos: of index.md or days/NN.md through frontmatter.split/render (byte-identical round trip verified on all 352 files), --cover sets cover_photo to the first added file (its .th copy is already written by web_copies), and ends by listing the alt lines to fill and the validator's findings for the file. --dry-run names the files and the entry and writes nothing. Removing a photo stays hand work: delete the entry and the three files; the validator warns about any file left undeclared (checks.py:733-736), and docs/PRIVACY_NOTES.md section 6 already says the history keeps it. Docs: ADDING-TRIPS.md section 'Adding photos to a trip that is on the site' (stage the trip folder only; no render), the README tool table, docs/DEVELOPING.md's tool list, the CONTENT_GUIDE.md:308 row. Tests tests/test_trip_photos.py on the tests/test_thumbs.py model (web_copies replaced by a recorder that writes placeholder files; temp trips through helpers.make_trip): numbering after 03 gives 04; the dNN- prefix; --cover; --dry-run writes nothing.

**Files.** `tools/trip_photos.py`, `tools/lib/photos.py`, `tools/add_trip.py`, `tests/test_trip_photos.py`, `ADDING-TRIPS.md`, `README.md`, `docs/DEVELOPING.md`, `docs/CONTENT_GUIDE.md`.

**Effort.** M. Visitor value 1, author value 3.3, confidence high.

**Risk.** Privacy: removal does not reach git history, and the tool must say so. Facts: alt stays empty until Eric writes it; the validator already warns per empty alt.

**Review revision (applies on top of the text above).** Proposal: as written, except the docs line: ADDING-TRIPS.md section 'Adding or removing photos on a trip that is on the site' with the git add path (the trip folder only; no render), README.md's 'Check, build and re-render' command block (:116-123; README has no tool table), the docs/DEVELOPING.md file list (:6-37), and the CONTENT_GUIDE.md:308 row.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: add_photos is reached only from the new-trip and --day-of paths (add_trip.py:63-80, :167, :193); docs/CONTENT_GUIDE.md:308 says no tool adds an 800 px copy afterwards; photos.web_copies (tools/lib/photos.py:149-169) is the only writer of the three copies; thumbs.py writes the .th copy alone (:1-18). Observation reproduced: add_photos is called only at :167 (--day-of) and :193 (new trip); docs/CONTENT_GUIDE.md:308 says 'no tool adds one afterwards'; web_copies at photos.py:149-169 writes the three copies via sips/cwebp; checks.py:731-735 only warns about an undeclared file; tools/thumbs.py:1-18 is .th only; content.load_all gives 106 of 168 trips with photos; no .jpg remains under content/trips/*/photos (1,004 .webp).

#### gap8-09. ADDING-TRIPS.md: one section for changing a trip on the site

**Observation.** The guide is organized around adding (headings at ADDING-TRIPS.md:7-313). The rules for a change are scattered: which paths to stage (:216-225), edits on github.com (:256-262), taking a trip off (:264-305), 'Changed a trip's title or map settings' (:318-319), thumbs.py after a cover change (:320-325 and README.md:71), photos copied in by hand (docs/CONTENT_GUIDE.md:308). The staging table names 'changing a track' (:221) but no procedure for a new recording exists; nothing covers adding photos later, and 'timezone' appears nowhere in ADDING-TRIPS.md or CONTENT_GUIDE.md (add_trip.py's --timezone and --force flags, tools/add_trip.py:122 and :126, are missing from the option table at :27-37). The README front-matter table (README.md:62-82) says what each field means and, for cover_photo (:71), region_days (:74) and draft (:77), what a change requires, but not for title (:66), region (:67), stats (:69) or map (:81), which are the fields a render depends on (tools/render.py:432 and :620-642).

**Evidence.** `ADDING-TRIPS.md:216-225`; `ADDING-TRIPS.md:256-262`; `ADDING-TRIPS.md:264-305`; `ADDING-TRIPS.md:318-324`; `README.md:62-80`; `docs/CONTENT_GUIDE.md:308`.

**Proposal.** Add '## Changing a trip that is on the site' between step 5 and 'Quick fixes from anywhere' in ADDING-TRIPS.md, as one table: change -> what to run -> needs the internet? -> paths for git add. Take the 'needs a render?' answer from trip_inputs() in tools/render.py (line 432): a change to title, activity, kind, map, stats, route_shape or a track file needs `python3 tools/render.py <trip-name>` (internet) and the three paths of step 5; anything else in the front matter or the write-up needs no render and stages the trip folder alone. Rows for what exists today: write-up or photo alt text (edit index.md; stage the folder); title, activity, route_shape, map: peaks/places/water_labels, or a stats value (render.py <trip-name>; stage all three); place, party, beta, card_summary, search_aliases, featured (no render; stage the folder); region (one spelling; render.py --site --force; stage rendered/site with the folder; link CONTENT_GUIDE 11.4); cover photo (thumbs.py <trip-name>; stage the .th file with the folder; link README's cover_photo row); draft or removal (link 'Taking a trip off the site'). Add a row for a replacement recording, new photos, a time zone fix or a replaced day only when a tool for it exists (gap8-02, 03, 06, 07, 08 if adopted); until then say in one line that these are done by hand and point at CONTENT_GUIDE.md:308 for photos. Point add_trip.py's --force help text (tools/add_trip.py:126) at the section. Add one link to it from README.md's front-matter table intro and from docs/CONTENT_GUIDE.md:308. Keep the guide's register; verify each row against the tool before writing it, as the guides' existing lines were.

**Files.** `ADDING-TRIPS.md`, `README.md`, `docs/CONTENT_GUIDE.md`, `tools/add_trip.py`.

**Effort.** S. Visitor value 1, author value 3.3, confidence high.

**Risk.** None; the table must be kept in step as the tools above land, so write rows only for what exists at each step.

**Review revision (applies on top of the text above).** Proposal: as written, with these corrections: the title row stages rendered/trips/<slug> and rendered/site because `render.py SLUG` also refreshes the site maps when their hash changed (render.py:762-763); the 'map: peaks or stats' row should also name activity and route_shape, which are in the same render key (render.py:432); the region row's `render.py --site --force` matches checks.py:984 and CONTENT_GUIDE.md:316 ('without --force the run can end before it rewrites the list of regions'); the README link belongs beside the table at README.md:62-82, and the add_trip.py pointer goes in the --force help text at tools/add_trip.py:126.

**Review note (condensed; the observation and proposal above are the revised text).** Not built and never decided against: no tracked Markdown has a changing-a-trip section (git ls-files '*.md' grep for change/edit/update a trip hits only ADDING-TRIPS.md:35 and :318), no commit ever contained one (git log -S for 'Changing a trip', 'Editing a trip', 'Updating a trip', 'Change a trip', 'Edit a trip' returns nothing; the guide's history is c46949e, fb425ab, dbce17b, e8d44dc), and history.md, docs/IMPLEMENTATION_REPORT.md and docs/WEBSITE_IMPLEMENTATION_LOG.md record no decision about it. Feasible and cheap: docs only, no constraint touched, S is honest for the rows that exist today (one table of about eight rows, three cross-links, one help string). Observation reproduces in substance: ADDING-TRIPS.md headings are 1 Get the track, 2 Add, 3 Write, 4 Preview, 5 Publish, Quick fixes, Taking a trip off, Or let Claude, If something goes wrong; the staging table is at :216-225, github.com edits at :256-262, taking a trip off at :264-305, title/map at :318-319, thumbs.py at :320-325; docs/CONTENT_GUIDE.md:308 is the 'copied into photos/ by hand ... no tool adds one afterwards' row; 'timezone' appears nowhere in ADDING-TRIPS.md or CONTENT_GUIDE.md and the guide's option table (:27-37) omits add_trip.py's --timezone and --force (tools/add_trip.py:122,126).

#### gap8-04. Write titles into map labels at build time, not at render time

**Observation.** tools/render.py:430-434 hashes title, activity, kind, map, stats and route_shape with the track bytes, and :638-641 puts every trip's title into the site-map hash; render_site runs after any slug render unless --no-site (:764). The title, route shape and two stats reach the rendered files only as text: the overlay root's aria-label 'Map of <title>, out and back, 12.8 miles, high point 11,952 ft' (aria_for :176-186; tools/lib/mapkit.py:1748-1752), 'Elevation profile of <title>' (:285; mapkit.py:2276), the day-map and series arias (:362, :419) and the region maps' pin aria-label and <title> (:656; mapkit.py:1531-1539); verified in rendered/trips/matterhorn-peak-west-couloir/map-wide.svg.html and rendered/site/region-lake-tahoe-desktop.svg.html. So retitling the 24 Strava default titles (copy-05) costs 24 trip renders of 16 files plus all 24 region and ski maps (76 files, 2.4 MB) with the internet, and a title changed on github.com (ADDING-TRIPS.md:256-262) leaves the old name in every label with no warning (gap8-05). Stats, unlike the title, change the drawing (mile markers scaled to the published distance and the GPS-max label, render.py:76-81), so they must stay hashed.

**Evidence.** `tools/render.py:176-186`; `tools/render.py:285`; `tools/render.py:430-434`; `tools/render.py:638-641`; `tools/render.py:656`; `tools/render.py:764`; `tools/render.py:76-81`; `tools/lib/mapkit.py:1531-1539`; `tools/lib/mapkit.py:1748-1752`; `tools/lib/mapkit.py:2276`; `tools/sitegen/core.py:451-462`; `rendered/trips/matterhorn-peak-west-couloir/map-wide.svg.html`; `rendered/site/region-lake-tahoe-desktop.svg.html`; `ADDING-TRIPS.md:223`; `ADDING-TRIPS.md:318-319`.

**Proposal.** Site maps only. In core.map_block when site_maps=True, after frag(): rewrite each `<a class="mk-pin" ... data-key="SLUG" aria-label="..."><title>...</title>` from site['by_slug'][SLUG]['title'] (escaped as mapkit.esc does) and each `<g class="mk-cluster" ... data-keys="..."><title>...</title>` from the titles of its keys joined with '; ' (mapkit.py:1531-1539 is the source of both). Then drop t['title'] from the trip tuples in the site hash at render.py:638 (the journal titles at :639 stay, since mapkit:647 and meta.json's 'journals' carry them); no VERSION bump, since old renders carry a correct string that the build now overwrites. Keep title and route_shape in trip_inputs (:432): a retitle still re-renders the trip's own 16 files, which gap8-05 says to do, but no longer all 76 site files. Gate: a build of today's content must be byte-identical before and after (the substituted strings equal the rendered ones), checked once by hand on the real content and asserted on a fixture in tests/test_build_site.py (a rendered/site/ fragment with a pin and a cluster; a retitled fixture trip's pin and cluster carry the new name). ADDING-TRIPS.md:223 and :318: a title change needs render.py <slug>, not --site; rendered/site is staged only when the trip's own render changed it.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tools/sitegen/pages/series.py`, `tools/sitegen/pages/archive.py`, `tools/render.py`, `tests/test_build_site.py`, `ADDING-TRIPS.md`, `README.md`, `docs/DEVELOPING.md`.

**Effort.** M. Visitor value 1, author value 2.3, confidence high.

**Risk.** Accessibility strings must stay identical to today's; the byte-for-byte build comparison catches drift. Changing the hash inputs makes nothing re-render by itself.

**Review revision (applies on top of the text above).** Observation: as written, except replace 'So retitling the 24 Strava default titles (copy-05) costs 24 trip renders of 16 files plus all 24 region and ski maps (76 files, 2.4 MB) with the internet' with 'So each retitled trip (copy-05 lists the candidates) costs that trip's render of 16 files plus all 24 region and ski maps (rendered/site: 76 files, 2.4 MB) with the internet'. Proposal: core.frag already rewrites each fragment at build time (route color, ids, @@ROOT@@; tools/sitegen/core.py:450-462). Add a build-side label step: (1) core.aria_for(t, what) producing the identical string (same '%.1f miles' and thousands-separated ft) and have map_block and chart_block replace the root <svg ... aria-label="..."> of per-trip map, profile and speed fragments (keep reading the speed chart's smoothing text at core.py:587-593 before replacing); day maps and the series overview likewise from the day dicts, passed in by multiday.py (:389, :732) and series.py (:296). (2) In core.map_block's site_maps branch (:492-497; called from home.py:323, archive.py:226/388, section.py:371, region.py:188) rewrite each <a class="mk-pin" ... data-key="SLUG" aria-label="..."><title>...</title> and each cluster's <title> (data-keys) from site['by_slug'] titles, skipping keys that are not slugs: the journal's pins and <a class="mk-line"> links carry a region_days part key and the name 'Part: Journal title, Day N' (render.py:564-568, :604-606; mapkit.py:646-647) and the journal's title stays hashed at render.py:639. (3) Drop 'title' and 'route_shape' from trip_inputs (render.py:432) and t['title'] from the site hash (:638); no VERSION bump, since old renders carry a correct string that the build now overwrites. (4) ADDING-TRIPS.md:223 and :318, README.md's field table note at :77 and docs/DEVELOPING.md no longer list a title change as a reason to render. Gate: a build of today's content must be byte-identical before and after (the substituted strings equal the rendered ones), asserted on a fixture in tests/test_build_site.py, plus a fixture where a retitled trip's map, profile and region pin carry the new name. Limit to document: track.gpx's own <name> (tools/lib/tracks.py:72-73) keeps the old title (156 of 157 match today; the planned route is the exception); rewriting it changes the published bytes and so the hash, so either leave it or hash only the trackpoint lines. Files: tools/sitegen/core.py, tools/sitegen/pages/multiday.py, tools/sitegen/pages/series.py, tools/render.py, tests/test_build_site.py, ADDING-TRIPS.md, README.md, docs/DEVELOPING.md (report.py and archive.py need no change if the substitution lives in map_block/chart_block).

**Review note (condensed; the observation and proposal above are the revised text).** Facts verified: title and route_shape reach the renders only as text (render.py:177-186, :285, :362, :419; mapkit.py:1531-1539, :1748-1752, :2276; the strings are in rendered/trips/matterhorn-peak-west-couloir/map-wide.svg.html and rendered/site/region-lake-tahoe-desktop.svg.html), both hashes carry the title (:432, :638), a trip render is 16 files and the site maps 76 files, 2.4 MB (counted). Reproduced: trip_inputs (:430-434) hashes title and route_shape; the site hash (:638-641) includes t['title']; render_site runs after slug renders unless --no-site (:763-764).

#### seo-10. Honest publication dates for new reports: add_trip, feed pubDate, sitemap lastmod

**Observation.** No report states published_at (0 of 168), so the feed's pubDate is the trip date at 12:00 UTC (build.py:231-234, a pinned legacy rule at DEVELOPING.md:78-80): a report written up weeks after the trip reaches feed readers as old news, and the sitemap has no lastmod (build.py:243-246). Git cannot supply dates (all trips arrived in two bulk commits, 6abc634 and a742ad1, and CI checks out at depth 1); CONTENT_GUIDE.md:957 forbids guessing, and add_trip.py:186-198 writes the front matter without the field.

**Evidence.** `tools/build.py:231-234`; `tools/build.py:243-246`; `docs/DEVELOPING.md:76-80`; `docs/CONTENT_GUIDE.md:849-850`; `docs/CONTENT_GUIDE.md:957`; `tools/add_trip.py:186-198`; `git log -- content/trips (6abc634, a742ad1)`; `.github/workflows/pages.yml:24`; `docs/IMPLEMENTATION_REPORT.md:506-507`; `content/trips (0 index.md with published_at)`.

**Proposal.** (1) add_trip.py --published [YYYY-MM-DD] writes published_at (today when the flag has no value) and ADDING-TRIPS.md section 5 'Publish' (line 186) says to set it on the day you push; (2) build.feed takes pubDate from published_at when stated (content.py:610 stores the text as written, so parse it with the content module's date parser), else the trip date as now, and orders items by that same moment; (3) build.sitemap writes <lastmod> from updated_at, else published_at, only when stated. Existing reports stay without dates (decision 12.5). Update the feed and sitemap tests in test_metadata.py (test_pub_date_is_the_trip_date_at_noon_utc at :1944, the byte-pinned feed at :2022) and the legacy note at DEVELOPING.md:78-80.

**Files.** `tools/add_trip.py`, `tools/build.py`, `ADDING-TRIPS.md`, `docs/DEVELOPING.md`, `docs/CONTENT_GUIDE.md`, `tests/test_metadata.py`.

**Effort.** S. Visitor value 1.3, author value 2.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md §12.5 and §12.6

**Risk.** No invented dates: only stated ones are used; feed order changes for new reports; pinned tests change.

**Decision for Eric.** Whether add_trip.py writes published_at by default (the day the report is created) or only when asked.

**Review note (condensed; the observation and proposal above are the revised text).** The observation is accurate and the work is not built: `grep -rl published_at content/trips` returns 0 files (and 0 for updated_at); tools/add_trip.py:186-198 writes the front matter without the field; build.feed takes pubDate from the trip date at 12:00 UTC (tools/build.py:231-234) and build.sitemap writes <loc> only (build.py:243-246; tests/test_metadata.py:2070 pins 'no lastmod, changefreq or priority'); docs/DEVELOPING.md:76-80 calls it the legacy exception; git log -- content/trips shows the two bulk commits 6abc634 and a742ad1; decisions 12.5 and 12.6 are open (docs/IMPLEMENTATION_REPORT.md:506-507; history map rows 12.5/12.6 'open'). Mostly already built: published_at and updated_at are parsed and validated (tools/lib/content.py:56-119: not before the trip, not after today, updated_at needs published_at) and written into the JSON-LD and article: metas (core.py:1580-1594); only the feed ignores them by a pinned legacy rule (DEVELOPING.md:78-80) and add_trip.py:186-198 never writes the line. So the code is S and feasible. Observation holds: grep finds 0 index.md with published_at; build.py:231-234 builds pubDate from the trip date at 12:00 UTC; build.py:243-246 sitemap() writes <loc> only; DEVELOPING.md:78-80 states the pinned legacy exception; CONTENT_GUIDE.md:957 forbids setting it from a guess; add_trip.py:186-198 writes meta without the field; git shows all 168 trips added in a742ad1 (24) and 6abc634 (144); pages.yml:24 is actions/checkout@v4 with no fetch-depth (depth 1 by default).

#### copy-01. Derive the stats-source sentence from the content, not a constant

**Observation.** core.stats_note writes 'Stats from the GPS recording via Strava.' under every trip with a track (core.py:1045); multiday.py:348 and series.py:166 say 'recordings via Strava' unconditionally; about.py:100 states 'Tracks are GPS recordings exported through Strava.' Today the sentence is true of every published page: 156 of 168 index.md files carry strava_id, and the 12 that do not are the planned route (which shows no stats note) and 11 multi-day or series trips (AIARE 2, two haute routes, the ski-mountaineering course, six LTCC courses, the PCT) whose day files all carry one. The wording is a constant, though, not derived: docs/IMPLEMENTATION_REPORT.md:461-462 already records a trip imported from a Garmin file that gets the same sentence, and tools/add_trip.py writes no strava_id for a FIT or GPX import (no 'strava_id' in tools/add_trip.py or tools/lib/strava.py), so the next imported trip will say 'via Strava' with nothing in its content to support it.

**Evidence.** `tools/sitegen/core.py:1041-1063`; `tools/sitegen/pages/multiday.py:348`; `tools/sitegen/pages/series.py:166-167`; `tools/sitegen/pages/about.py:99-103`; `content/trips/back-to-clipless/index.md (strava_id line)`; `content/trips/pacific-crest-trail-2024/days/001.md:5`; `_site/trips/back-to-clipless/index.html (strip footnote text)`.

**Proposal.** Add content.has_strava(t): true when index.md has strava_id or every day file has one (a guard, not a fix: it changes no page today). Add an optional `source:` front-matter line (fixed list such as Strava, Garmin, CalTopo; checks.py rejects anything else) that supplies the 'via X' word; stats_note, the multi-day note and the series note say 'via <source>' when `source:` is set, 'via Strava' when has_strava, else 'Stats from the GPS recording.' add_trip.py writes `source:` on import (Strava for --strava-export, otherwise the file type) so new trips carry it. about.py's first method item becomes computed ('N of the M tracks came through Strava') or keeps the current sentence only while every published track has strava_id. Update docs/CONTENT_GUIDE.md and the strip tests in tests/.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/multiday.py`, `tools/sitegen/pages/series.py`, `tools/sitegen/pages/about.py`, `tools/lib/content.py`, `tools/lib/checks.py`, `docs/CONTENT_GUIDE.md`, `tests/`.

**Effort.** S. Visitor value 1, author value 1.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 10 ('via Strava' limit) and section 12 decision 10

**Risk.** Facts-only rule: the page may name a source only when the content states it; a wrong `source:` value must fail validation rather than publish.

**Decision for Eric.** Whether to add a `source:` line to the 11 non-Strava reports or let them say 'from the GPS recording' without a service name.

**A skeptic argued to drop it.** The observation's conclusion is false and the wording question is already on Eric's list. (condensed) The judges and the planner kept it; the proposal above is the reduced form they kept.

**Review note (condensed; the observation and proposal above are the revised text).** The observation overstates the gap: the 12 index.md files without strava_id are 10 multi-day trips, the PCT and the planned route, and every day file of those 10 multi-day trips carries strava_id (3/3, 6/6, 5/5, 2/2, 3/3, 4/4, 3/3, 3/3, 3/3, 2/2), while the planned route never shows the note (core.stats_note is called only from section.py:195, multiday.py:393 and :786, report.py:613 and :622; the goal page does not call it). The code and copy citations reproduce (core.py:1045 'via Strava' whenever has_track; multiday.py:348 and series.py:166 unconditional; about.py:100). The strava_id counts reproduce (156 of 168 index.md files carry it; 12 do not), but the 12 are six LTCC courses, not five, plus AIARE 2, the two haute routes, the ski-mountaineering course, the planned route and the PCT index.

#### features-11. Show the conditions: field the validator already accepts

**Observation.** checks.py accepts a conditions key in index.md with the comment 'read into the trip dict by content.load_trip; no page shows it yet' (checks.py:60); content.py loads it as a dict (content.py:561); no page module reads it (grep of tools/sitegen finds only the disclaimer sentence 'Reports describe past conditions, not advice', in the footer at core.py:1694 and the About page's method list at about.py:113). No trip uses it today (0 index.md files carry conditions:), so a field designed for snow, weather or water notes has nowhere to appear.

**Evidence.** `tools/lib/checks.py:53-61`; `tools/lib/content.py:561`; `tools/sitegen/pages/report.py (beta rail, pages map 3.7)`; `tools/sitegen/core.py:1694 (footer disclaimer)`.

**Proposal.** No new rail group. Document in docs/CONTENT_GUIDE.md that conditions notes go in beta: rows (labels such as Snow, Weather, Water level), which the Beta rail already renders with dotted leaders and stacked list values (report.py:239-253), under the report's own date. Retire the dead key: remove 'conditions' from INDEX_KEYS (checks.py:60) and from load_trip (content.py:561) so the validator rejects a field nothing shows, and update the 'Not searched' line at CONTENT_GUIDE:398-399. A test in tests/test_checks.py that `conditions:` is reported as an unknown key. Effort S. The plan's exclusion of weather and avalanche feeds is untouched: everything shown is typed by Eric on a dated report.

**Files.** `tools/lib/content.py`, `tools/lib/checks.py`, `tools/sitegen/pages/report.py`, `docs/CONTENT_GUIDE.md`, `tests/test_report_page.py`, `tests/test_checks.py`.

**Effort.** S. Visitor value 1.3, author value 1.7, confidence high.

**Risk.** Facts-only: shown only when typed; must carry the trip date so a reader cannot take it for a forecast (the plan excludes weather/avalanche feeds).

**Decision for Eric.** Whether he wants to record conditions per trip.

**Review note (condensed; the observation and proposal above are the revised text).** The observation is right (checks.py:60 accepts the key, content.py:561 loads it as a dict, no page reads it, 0 trips use it today), but the proposal builds a second rail group for what beta: rows already do: beta_list renders label/value rows with dotted leaders and stacked list values (report.py:239-253), so a 'Snow' or 'Weather' row can be written today with no code, the trip date heads every report, and the footer already says reports describe past conditions (core.py:1694). Observation reproduces in substance: checks.py:60 carries 'conditions' with the comment 'read into the trip dict by content.load_trip; no page shows it yet'; content.py:561 loads it as meta.get('conditions') or {}; grep '^conditions:' over content/trips finds 0 files; no module under tools/sitegen reads t['conditions'].

#### visual-16. About: a place for Eric's own words and a portrait

**Observation.** The About page is numbers (a 2x2 of figures, five activity rows), a computed lede, an at-a-glance list, the method and the units switch; no sentence on it is Eric's and there is no photograph, which is the one thing a first-rate journal's About page has. The two-column layout with the sticky numbers column is good and should stay. No `content/about*` exists, and the rule is that no bio is invented.

**Evidence.** `desktop-about.jpeg`; `tools/sitegen/pages/about.py:51-64`; `content/ (home.json and trips/ only)`; `docs/DEVELOPING.md:73`; `tools/sitegen/pages/about.py:1-6`; `tools/sitegen/pages/about.py:58-66`; `tools/sitegen/pages/about.py:99-110`; `tools/sitegen/pages/about.py:137-140`; `tools/sitegen/pages/home.py:339`; `tools/sitegen/pages/ticklist.py:14 (INTRO, the one tick-list sentence)`; `tools/sitegen/pages/ticklist.py:147 (the page description)`; `content/ (ls: home.json, trips)`; `docs/IMPLEMENTATION_REPORT.md:516-517`.

**Proposal.** Two steps, both dormant until Eric writes. (1) Optional `content/about.md`: its body, verbatim Markdown, replaces the computed lede in `.abo-intro` (about.py:51-64); absent file, today's page is unchanged. `tools/lib/content.py` loads it, `tools/lib/checks.py` validates it, `tests/test_about_units.py` covers both states, and docs/CONTENT_GUIDE.md gets a section. Effort S. (2) Only when Eric supplies a portrait: front matter `photo:` (a file beside the Markdown), `alt:` (required by the validator), `cover_focal_x/y`; the file goes through `photos.strip_metadata` and `photos.web_copies` (tools/lib/photos.py:69, 149) like a trip photo, build.py copies the WebP outputs, and about.css places it at 4:5 above the words in the words column. Effort S to M on top of step 1. Nothing is written for him, the about.py docstring's rule (lines 1-5) holds, and whether a portrait and a bio go on a public site is Eric's call (docs/PRIVACY_NOTES.md level).

**Files.** `tools/lib/content.py`, `tools/lib/checks.py`, `tools/sitegen/pages/about.py`, `assets/css/pages/about.css`, `tools/build.py`, `docs/CONTENT_GUIDE.md`, `tests/test_about_units.py`, `tests/test_checks.py`.

**Effort.** M. Visitor value 2.7, author value 3, confidence high.

**Also covers.** copy-15 (merged into this finding).

**Risk.** A portrait and a bio on a public site are Eric's privacy call (docs/PRIVACY_NOTES.md level); nothing is written for him and the page stays as it is until he writes it.

**Decision for Eric.** Whether to add a bio and a photo of himself.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: about.py:1-5 states 'No bio, portrait or email until Eric writes them', the page is a computed lede plus at-a-glance rows (about.py:51-64), content/ holds only home.json and trips/, and DEVELOPING.md:73 forbids invented bios, so the mechanism must stay dormant until Eric writes, which the proposal does.

#### features-17. Region introductions from content/regions/<slug>.md

**Observation.** Region pages are built from facts alone (region.py head(), counts and places) and the report records 'No region introduction; needs a place in content/' as open decision 14.7.3; the smallest pages (Oregon: a map and three rows) read thin (report 14.6). There is no content file type for a region today.

**Evidence.** `tools/sitegen/pages/region.py:60-105`; `docs/IMPLEMENTATION_REPORT.md 14.6 and 14.7`; `content/ (home.json, trips/ only; ls 2026-10-13)`.

**Proposal.** content/regions/<slug>.md, slug = content.slugify(region name) as core.region_groups computes it (core.py:106-107), with optional front matter title: (must equal the region name as spelled in trips when present) and a body rendered verbatim with markdown.to_html under the region H1 in region.py head() as a .prose t-body block; absent file, no block. checks.py: an error when the file's slug matches no region that gets a page (core.region_pages) and a warning when the region has lost its page since. Loaded in tools/lib/content.py beside the trips. Documented in CONTENT_GUIDE with the note that a region spelled two ways is two regions (14.6). No change to archive.py or the Map page. Effort M. Known: IMPLEMENTATION_REPORT.md 14.7.3.

**Files.** `tools/lib/content.py`, `tools/lib/checks.py`, `tools/sitegen/pages/region.py`, `tools/sitegen/pages/archive.py`, `docs/CONTENT_GUIDE.md`, `tests/test_region_page.py`, `tests/test_checks.py`.

**Effort.** M. Visitor value 2.3, author value 2.3, confidence high.

**Already known.** IMPLEMENTATION_REPORT.md 14.7.3

**Risk.** Write-ups verbatim; a region spelled two ways is two regions (14.6), so the file must key on the slug the renderer wrote in rendered/site/meta.json.

**Decision for Eric.** Which regions get an introduction and what it says.

**Review note (condensed; the observation and proposal above are the revised text).** This is a known open point carried correctly: IMPLEMENTATION_REPORT.md:678-680 (14.7.3: 'A region page has no prose. If you want one, it needs a place in content/'), marked open in the review's history map (review scratch, not in the repository); region.py head() (lines 67-75) builds facts only; 14.6 records that small regions read thin.

#### features-05. A summits: field, step 1 (the A-Z page waits)

**Observation.** The plan deferred a summit index until reports carry structured, author-reviewed summit names (plan:373-377). Today the only peak field is map: peaks: on 11 index.md files, which asks the renderer for a map label and feeds the search index (search.py entry(), the 'k' field); it is not a claim of a summit. The PEAK BAGGING SZN write-up names eight peaks in its own words, 10 trip slugs contain 'peak', and nothing lists which reports reach which summit.

**Evidence.** `docs/personal-website-improvement-plan.md:373-377`; `content/trips/*/index.md (11 'peaks:' lines, grep 2026-10-13)`; `content/trips/peak-bagging-szn/index.md (write-up first line)`; `tools/sitegen/search.py:47-70`; `tools/lib/checks.py:53-66`; https://stavislost.com/hikes/trail/old-man-mountain-and-black-buttes-loop/; https://www.14ers.com/php14ers/tripreport.php?trip=20579; https://www.snwburd.com/bob/; `content/trips/*/index.md (11 files with 'peaks:')`; `tools/sitegen/search.py:50-62`; `tools/lib/checks.py:466-479`; `docs/personal-website-improvement-plan.md:373-377`.

**Proposal.** Step 1 (S): optional `summits:` list in index.md and days/NN.md, each `- name:` with optional `outcome:` from a fixed set (summit, turned-around, traverse) and `route:`; add the key to INDEX_KEYS and DAY_KEYS (checks.py:53-62) with a rule (name required and text, outcome from the set, no duplicate names in one file). Show it as a 'Summits' row in the report's Beta rail through the existing beta_list markup (report.py:239-253, list values stack one per line) and add the names to the search 'k' field beside peaks (search.py:50-62) with a test in tests/test_search.py. Never derived from map.peaks, GPS max, titles or write-ups; a summit shown is one Eric typed. Document the field in docs/CONTENT_GUIDE.md. Step 2 (M, later, only after Eric has typed names on enough reports and settled spellings, the regions failure mode in IMPLEMENTATION_REPORT.md 14.6): tools/sitegen/pages/summits.py building summits/ A-Z with each name's reports (date, activity chip, outcome tag) and a count per name, no all-time total (plan:377). Until then the page is not built, so nothing empty ships.

**Files.** `tools/lib/content.py`, `tools/lib/checks.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/search.py`, `docs/CONTENT_GUIDE.md`, `tests/test_checks.py`, `tests/test_search.py`, `tests/test_report_page.py`.

**Effort.** M. Visitor value 3, author value 2.3, confidence high.

**Also covers.** benchmark-06 (merged into this finding).

**Already known.** IMPLEMENTATION_REPORT.md section 12, decision 14

**Risk.** Facts-only: a summit shown that the author did not type is an invented completion claim; two spellings of one peak become two entries (same failure mode as regions, IMPLEMENTATION_REPORT.md 14.6); the page must build empty-free when no report has the field.

**Decision for Eric.** Whether to publish summit claims at all, and the outcome vocabulary.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible and exactly what plan:373-377 asked for (author-typed names and outcomes, no inference from map.peaks, GPS max or titles, no all-time count), and search already carries map.peaks in the 'k' field (search.py:50-62), so adding summits there is a line.

#### features-01. A By-year block on About (a years/ page later)

**Observation.** Totals exist only site-wide: the About page sums Reports, Distance, Gain and the highest GPS max over every published report (about.py numbers()), and the Trips explorer's year sections carry only a report count (trips.py:171-183). The content already holds everything a year in review needs: 157 index.md files and all 150 PCT day files carry stats blocks with distance_km, gain_m, high_m, moving and elapsed (checks.py:64 STATS_KEYS), and every trip has a date. Loading the content today gives, for example, 2021 = 35 reports and 35 days out, 2024 = 5 reports but 165 days out once the journal's days are counted, 2026 = 58 reports and 70 days out; the high point and longest day per year come from the same fields.

**Evidence.** `tools/sitegen/pages/about.py (numbers(), activity_counts())`; `tools/sitegen/pages/trips.py:171-183`; `tools/lib/checks.py:53-64`; `content/trips/*/index.md (157 stats: blocks, grep 2026-10-13)`; `content/trips/pacific-crest-trail-2024/days/001.md`; `tools/lib/content.py:539-545 (season_of)`.

**Proposal.** First step (S): a 'By year' block on the About page beside 'By activity', built with the act_rows row markup (about.py:30-47): one row per calendar year, newest first, Reports · Days out · Distance · Gain, linking to trips/?year=YYYY (trips.js:13). Days out = distinct dates: a multi-day trip's and the journal's days count on their own dates, the parent is summed once (its stats are already the day sum, content.py:585). Verified today: 2021 35/35, 2024 5 reports/165 days, 2026 58/70. Every figure through core.U/core.distance/core.elev; a missing stat is absent, never 0. No ski-season split (season_of spans two years, content.py:539-545); the row links to the explorer rather than inventing a season total. Tests beside tests/test_about_units.py with a multi-day fixture that must not double count. Second step, only if wanted later: a years/ page registered in build.py PAGE_MODULES (build.py:32) with the month strip, longest day, highest GPS max and per-activity rows (M: new module, assets/css/pages/years.css, tests/test_years_page.py).

**Files.** `tools/sitegen/pages/about.py`, `assets/css/pages/about.css`, `tests/test_about_units.py`.

**Effort.** S. Visitor value 2.7, author value 2, confidence high.

**Risk.** Double counting a multi-day trip if both its parent stats and its days are summed; the ski season spans two calendar years (content.py season_of), so the ski row should say so or link to ski/#season-... rather than invent a season total; every figure must come from stats blocks, with a missing value shown as absent, never as 0.

**Decision for Eric.** Calendar years (one table for all activities) or ski seasons for the ski rows; whether years/ gets a header nav slot or stays linked from Trips and About.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible and the figures check out: a read-only load through content.load_all today gives 2021 35 reports/35 days out, 2024 5/165, 2026 58/70, and a day-kind trip's stats are already the sum of its days (content.py:585), so summing each published trip once is correct, as the About page does (about.py numbers()). The explorer reads `year` and `activity` from the URL (trips.js:13).

#### ia-19. About page as the site's guide: rows for Trips, Regions and Tick list; footnote links to the method

**Observation.** About's body lists the five activity rows and 'Open the map', explains the stats in 'How these reports are made' and holds the RSS section, but links neither the explorer (trips/), the region pages nor the tick list from its body: in _site/about/index.html the <main> links only the five sections, map/ and feed.xml (about.py:30-46, 93-95, 132-140). The header nav and footer both link Trips and Tick list; no page chrome links the 8 region pages, which are reachable only from map/ and trips/. Every recorded single-day report's footnote reads 'Stats from the GPS recording via Strava.' with no link to that explanation (core.py:1041-1061; 156 built report pages, none with an <a> in .strip-note); multi-day pages carry a plural copy from multiday.py:345 with the same gap.

**Evidence.** `tools/sitegen/pages/about.py numbers() and method() (act_rows + Open the map; abo-how-h)`; `tools/sitegen/core.py:1041-1046 (stats_note text)`; `_site/index.html footer (Trips, Tick list, Map & archive, About, RSS)`.

**Proposal.** about.py numbers(): after act_rows() add rows in the same .abo-act markup (about.css:69-78; rows are shared with the 404 page via notfound.py:39, so add them in numbers(), not act_rows(), and use a neutral glyph instead of core.disc) for Trips ('SEARCH AND FILTER', to trips/), Regions ('8 REGIONS', count from core.region_pages(site, meta); link map/ since no regions/ index page exists) and Tick list ('N ACTIVE GOALS' from site['active_goals'], build.py:258, as about.py:79 already does). core.stats_note: add a `here` parameter and append a link 'How these stats are made' built with core.link(here, 'about/#abo-how-h') (the id exists; sitecheck.py:275-276 verifies cross-page fragments); update the callers report.py:613 and :622 (phone copy, keep the link short or omit it there) and section.py:195 (featured trip on section pages); give multiday.stats_note (multiday.py:345, called at :393 and :786) the same link so multi-day pages match. Tests: update the exact-HTML pins in tests/test_track_rules.py:260-402 and tests/test_report_page.py:2285-2320, 2885-2908; add an About rows test (tests/test_about_units.py covers only the Units block, so a new test file or a new class there). FILES: tools/sitegen/pages/about.py, tools/sitegen/core.py, tools/sitegen/pages/report.py, tools/sitegen/pages/section.py, tools/sitegen/pages/multiday.py, tests/test_track_rules.py, tests/test_report_page.py, tests/test_about_units.py (or a new About test). RELATES_TO_KNOWN: docs/IMPLEMENTATION_REPORT.md section 12 item 10 (line 516): the 'via Strava' wording is an open decision and is unchanged here.

**Files.** `tools/sitegen/pages/about.py`, `tools/sitegen/core.py`, `tests/test_report_page.py`, `tests/test_about_units.py`.

**Effort.** M. Visitor value 1.7, author value 1, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md 12.10 (wording of the footnote) for the adjacent text

**Risk.** The footnote is copied onto the phone map caption (report.py); the link must be omitted or kept short there. The 'via Strava' wording is an open decision (report 12.10) and unchanged here.

**Review note (condensed; the observation and proposal above are the revised text).** Observation verified: the About body links only the five section pages, map/ and feed.xml (tools/sitegen/pages/about.py:90-95; _site/about/index.html and the live page both list hrefs ../ski/ ../climbing/ ../hiking/ ../mountain-biking/ ../other/ ../map/ ../feed.xml and nothing to trips/, regions or tick-list/); the footer carries Trips, Tick list, Map & archive, About, RSS (_site/index.html footer); id="abo-how-h" exists (about.py:116); the footnote 'Stats from the GPS recording via Strava.' has no link (core.py:1045 and :1061; live _site/trips/matterhorn-peak-west-couloir/ strip-note). Observation verified (about.py:90-95 body links only the five sections and map/; built about footer has Trips, Tick list, Map & archive, About, RSS; core.py:1041-1059 footnote has no link; id abo-how-h exists at about.py:116; sitecheck.py:275-276 checks cross-page fragments; 12.10 is the via-Strava wording). The core observation reproduces: in _site/about/index.html the <main> links only ../ski/ ../climbing/ ../hiking/ ../mountain-biking/ ../other/ (act_rows), ../map/ (Open the map) and ../feed.xml (RSS); no trips/, regions/<slug>/ or tick-list/ link (about.py:30-46, 93-95, 132-140).

#### ia-15. Choose the home page's two region maps in home.json

**Observation.** "Where I've been" draws Lake Tahoe and Eastern Sierra, fixed in HOME_REGIONS in home.py. Santa Cruz is the site's second region (45 reports) and appears only in the ALSO line, while Eastern Sierra (7 reports) has a map. The ALSO line then lists six other mapped regions and "6 more regions" to map/#other-places.

**Evidence.** `tools/sitegen/pages/home.py:19 (HOME_REGIONS = ('Lake Tahoe', 'Eastern Sierra'))`; `_site/index.html (hom-also: Santa Cruz 45 · Bay Area 5 · Boise 5 · Alps 4 · Tetons 4 · Oregon 3 · 6 more regions)`; `content/home.json (featured_slugs only; tools/sitegen/curation.py:86-97 validates it)`; `desktop-home.jpeg (Where I've been: Lake Tahoe 86 reports, Eastern Sierra 7 reports; ALSO Santa Cruz 45)`; `tools/sitegen/pages/home.py:19`; `tools/sitegen/pages/home.py:306-312`; `rendered/site/meta.json (region-santa-cruz-desktop 45 trips, region-eastern-sierra-desktop 7)`; `content/home.json`; `README.md:84-94`.

**Proposal.** curation.py reads an optional `region_maps` list of exactly one or two region names from content/home.json, validated like featured_slugs: each must have a `region-<slug>-desktop` or `-phone` entry in rendered/site/meta.json (the check home.where already makes, home.py:310-315), errors naming the file and the value; home.where() uses it and falls back to HOME_REGIONS when the key is absent. Document it in README.md (home.json section) and docs/CONTENT_GUIDE.md. Tests: tests/test_curation.py, tests/test_home.py. Effort S. Note for Eric: the Eastern Sierra map now carries the PCT journal's days (commit 6c682ea), which may be why that pair was chosen.

**Files.** `tools/sitegen/curation.py`, `tools/sitegen/pages/home.py`, `content/home.json`, `README.md`, `docs/CONTENT_GUIDE.md`, `tests/test_curation.py`, `tests/test_home.py`.

**Effort.** S. Visitor value 1, author value 2.7, confidence high.

**Also covers.** visual-08 (merged into this finding).

**Risk.** A third map adds a lazy image pair to the home page; keep the cap at three. Region maps use the phone render on tablets (home.css) and the layout assumes two columns, so three needs a CSS rule.

**Decision for Eric.** Which regions the home page maps (for example Lake Tahoe and Santa Cruz)

**Review note (condensed; the observation and proposal above are the revised text).** Observation verified: HOME_REGIONS is a constant (home.py:19), content/home.json holds only featured_slugs, curation.py validates only that key (curation.py:80-100), and Santa Cruz (45 reports in front matter) has a region page and map while Eastern Sierra (7) is drawn. The key is S, facts-only and falls back to today's pair.

**Gates.** The phase is done when every line below holds and is recorded in the log entry:

1. python3 tools/content_report.py prints one row per published trip (167) with date, slug, title flag, write-up chars, photos, cover source, place, party and card summary plus provenance; --missing place lists 79 today, --missing cover lists the 103 automatic covers and 61 without photos, --alt lists the cover and featured alt texts, --taxonomy lists 15 regions with counts and the Kingsbury/Kingsbury Grade and Boise/Idaho pairs; a tree diff shows it writes nothing under content/; validate -v's 143 caption notes become one count line.
2. tests/test_add_trip.py: add_trip.py TRACK --update SLUG keeps the body, every alt, beta, map, cover_photo and card_summary byte-for-byte, replaces date/start_time/route_shape/stats (existing timezone wins unless --timezone), refuses days/ and an unknown slug, --dry-run prints a unified diff and writes nothing; tools/trip_photos.py numbers after 03 as 04, uses the dNN- prefix for a day, --cover sets cover_photo, --dry-run writes nothing, and ends with the alt lines to fill.
3. gap8-04: two --link builds of today's content before and after the change are byte-identical (diff -rq); a fixture retitle shows the new name in the region pin's aria-label and the cluster <title>; after a retitle render.py --status lists that trip alone and no site maps; ADDING-TRIPS.md:223 and :318 no longer say a title change needs rendered/site.
4. ADDING-TRIPS.md has '## Changing a trip that is on the site' as one table (change, what to run, needs the internet?, git add paths) keyed on trip_inputs, with rows only for tools that exist; add_trip.py's --force help says it rewrites index.md and points at the section; README.md:62-82 and CONTENT_GUIDE.md:308 link to it.
5. seo-10: add_trip.py writes an empty published_at: line; a fixture with published_at gives that pubDate in feed.xml and a <lastmod> in sitemap.xml, a fixture without stays as today; tests/test_metadata.py's pinned feed updated; DEVELOPING.md:78-80 rewritten.
6. copy-01 and features-11: a fixture with source: Garmin prints 'via Garmin', an unknown source fails validate, every published page today still prints 'via Strava'; conditions: is reported as an unknown key and CONTENT_GUIDE says conditions go in beta rows.
7. With no content/about.md, no content/regions/*.md, no summits: list and no region_maps key, the built site is byte-identical to before (diff -rq); with fixtures, About shows the verbatim body (and the portrait at 4:5 with alt required by the validator when a photo is named), a region page shows its intro under the H1, a report's Beta rail shows a Summits row and search.json's 'k' carries the names, an unknown region in home.json fails the build naming the file.
8. About carries a By-year block whose rows match content.load_all (2021: 35 reports / 35 days out, 2024: 5 / 165, 2026: 58 / 70) with every figure through core.U, plus Trips and Tick list rows in .abo-act markup; tests beside tests/test_about_units.py.
9. ia-16: validate -v prints a NOTE for every trip whose title contains Peak, Mount, Mountain, Couloir, Chute, Bowl or Lake without map: peaks; CONTENT_GUIDE has the 'what makes a report findable' checklist; after Eric's afternoon, content_report.py --missing place is recorded in the log with the new count.
10. After Eric's merges (if chosen), validate.py reports no region spelled two ways and the site render is queued for Phase 15; both Pythons with -W error and build.py --check pass.

**Tests to add.** New: `tests/test_content_report.py`, `tests/test_trip_photos.py`. Extended: `tests/test_about_units.py`, `tests/test_add_trip.py`, `tests/test_build_site.py`, `tests/test_checks.py`, `tests/test_curation.py`, `tests/test_home.py`, `tests/test_metadata.py`, `tests/test_region_page.py`, `tests/test_report_page.py`, `tests/test_search.py`, `tests/test_track_rules.py`. Plus the checks the gates name that no unit test covers: `diff -rq` of two `--link` builds before and after for the byte-identical gates; `python3 tools/validate.py -v` counts before and after Eric's afternoon.

**Screenshots to capture.** `about/` at 390 and 1280 px with the By-year block (and the body and portrait if Eric wrote them); one region page with an introduction; one report with a Summits row in the Beta rail. Before set: `phone-about.jpeg`, `desktop-about.jpeg`, `desktop-region-eastern-sierra.jpeg`.

**Author inputs needed.** Decisions 5 to 9 and 28; the 79 `place:` lines (an afternoon); the About body, which regions get an introduction, whether a portrait goes up; the first summit names if he wants the row.

### Phase 10. Report and multi-day pages: layout, facts, captions and the profile readout

**Goal.** Put the photo and the words where a reader lands (photo-only reports get their hero, written reports without photos lead with the words, multi-day pages get a lead photo and a day strip), make the facts strip and captions complete on phones (elapsed, clock times, contour interval, key rows that decode OSM trails), unify the section labels, and add the hover and touch readout on the elevation profile.

**Prerequisites.** Phase 9's ia-19 (the stats footnote link to about/#abo-how-h) for gap6-04, gap6-05 and the gate; without Phase 9, build that link here. Eric's decisions: the three layouts (report-01, report-02, report-11), the hero frame after a side-by-side preview (report-03), the two documented reversals (copy-04 'Track only' tag, visual-03 factual head), and times of day (report-04, report-05). maps-01 part 3 (contour labels in both units) waits for Phase 15.

**Decisions this phase waits on.**

- report-01, report-02, report-11 (recommended yes to all three)
- report-03 frame from the preview (recommended the 3:2 cap)
- copy-04 and visual-03 reversals (recommended yes)
- Times of day: elapsed plus the mile-table clock column; the derived finish time waits on PRIVACY_NOTES 6.2

**Findings in this phase** (20, in working order): report-02, report-01, report-11, report-03, resilience-06, visual-03, copy-09, copy-04, report-04, report-05, report-10, gap6-04, gap6-05, gap6-06, maps-01, maps-02, benchmark-11, a11y-09, visual-19, maps-04.

#### report-02. Give photo-only reports their lead photo

**Observation.** 35 single-day reports have photos and no write-up. narrative() needs both a write-up and a cover (report.py:23-26), so they keep the compact order and their photos come after the strip, map and chart (report.py:639-642). Their cover is still the card image and the share image (core.share_photo, core.py:1514-1522), so a reader who opens a shared link lands on a page whose photo is below the fold. 27 of the 35 have a cover that passes report.lead_photo (at least 6:5, report.py:29-37); the other 8 have a portrait or square cover and would stay as they are.

**Evidence.** `tools/sitegen/pages/report.py:23-26`; `tools/sitegen/pages/report.py:588-594`; `tools/sitegen/pages/report.py:635-642`; `tools/sitegen/core.py:1514-1522`; `tools/lib/content.py:278-321`.

**Proposal.** Show the hero whenever lead_photo(t) exists, whether or not there is a write-up: title, hero, strip, map, profile, remaining photos. In page(): show_hero = (story or has_gallery) and not lone and lead_photo(t) is not None; the cover leaves the grid as now (report.py:591-594), photos_anchor=not has_gallery still covers a single landscape photo, and the map preload gives way to cover_preload (report.py:657-660). Bottom bar unchanged (compact path, report.py:342-351: Map · Profile, or Beta · Photos · GPX). Add a photo-only case to tests/test_report_page.py (test_photos_without_a_writeup_stay_compact at :410 asserts today's behavior) and a line to DEVELOPING.md:481-491 (the three cases become four). Risk: the hero becomes the largest image on 27 pages; Phase 4 measured the same change for stories (IMPLEMENTATION_REPORT.md 2.2), but re-measure one page with the method in DEVELOPING.md:1428-1439.

**Files.** `tools/sitegen/pages/report.py`, `docs/DEVELOPING.md`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 3.3, author value 1.3, confidence high.

**Risk.** The hero becomes the largest image on 35 pages; Phase 4 measured the same change for stories (IMPLEMENTATION_REPORT.md 2.2) and it held, but re-measure one page with the method in DEVELOPING.md:1428-1439.

**Decision for Eric.** Whether a report he wrote nothing for should still open with its photo rather than its map.

**Review note (condensed; the observation and proposal above are the revised text).** Observation reproduces: 35 single-day reports have photos and no body_md (count.py); narrative() at report.py:23-26 needs both; the compact order at :639-642 appends the gallery after the profile; core.share_photo at core.py:1514-1522 returns the cover for any trip with one.

#### report-01. Lead with the write-up on reports that have words but no photos

**Observation.** 21 single-day reports have a write-up and no photos (counted over content/trips/*/index.md). They take the compact map-first order: title, strip, full-bleed map, elevation profile with its table, and only then 'Trip report' (report.py:639-640; the built hit-the-three-piece page prints the write-up after the elevation table). The title action 'Read the report' (report.py:602-603) exists to jump past the apparatus, which shows how far down the words are. DEVELOPING.md:457-461 records this as the Phase 3 decision.

**Evidence.** `tools/sitegen/pages/report.py:23-26`; `tools/sitegen/pages/report.py:598-603`; `tools/sitegen/pages/report.py:635-642`; `_site/trips/hit-the-three-piece/index.html`; `docs/DEVELOPING.md:457-470`; `content/trips/hit-the-three-piece/index.md`.

**Proposal.** In report.page, use the story order without a hero only when has_report, no photos, and the write-up clears core.STRUCTURED_MIN_CHARS (100 characters, core.py:30, the floor the site already uses to decide a report has a real write-up): strip, section row (Report · Route · Trip details via section_nav with has_gallery=False), .rep-body, map, profile; keep every id (#stats #map #profile #beta #report). The phone bottom bar takes the existing story branch without a gallery (report.py:333-341). Reports whose note is shorter than the floor (11 of the 21 are under 40 words) keep the compact map-first order, as do track-only and photo-only reports. Add body class p-report--written so report.css reuses the .p-report--story spacing (report.css:139-147). Update DEVELOPING.md:457-470 (the decision reverses the Phase 3 note at WEBSITE_IMPLEMENTATION_LOG.md:405-406; say why) and the layout tests in tests/test_report_page.py. Effort S.

**Files.** `tools/sitegen/pages/report.py`, `assets/css/pages/report.css`, `docs/DEVELOPING.md`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 3, author value 1.3, confidence high.

**Risk.** Reorders 21 published pages; no URL or anchor changes. Reverses a documented Phase 3 decision, so say why in the log. The map stops being the eager LCP image on those pages (the preload stays, as on stories).

**Decision for Eric.** Whether his words should sit above the map on a report that has no photo.

**Review revision (applies on top of the text above).** Observation, add: the compact order for written reports without photos is a rule of the 2026-10-08 plan itself (plan 9.1, docs/personal-website-improvement-plan.md:309: 'For track-only entries or reports without photos, retain a compact map/data-first layout instead of manufacturing editorial content'), carried into Phase 3 (docs/WEBSITE_IMPLEMENTATION_LOG.md:405; docs/DEVELOPING.md:457-461; narrative() docstring, report.py:23-26). Its reason, not manufacturing editorial content, does not apply here: the write-up is Eric's own text, and the proposal reorders existing sections only. Proposal unchanged, except: the log entry must record the reversal against plan 9.1 as well as DEVELOPING.md:457-470, and the test update covers the three-way split (compact for track-only and photo-only, written-no-photo order, story).

**Review note (condensed; the observation and proposal above are the revised text).** Not built, observation true: 21 single-day index.md files have a write-up and no photos (counted); narrative() needs body_md and a cover (report.py:23-26); page() takes the compact branch body += [strip_, map_, profile, rep_body] (report.py:639-640); the built _site/trips/hit-the-three-piece/index.html has body class p-report and id="report" after id="profile" (offsets 136466 vs 102399) with a 'Read the report' title action (report.py:601-603). Observation verified: 21 single-day reports have a write-up and no photos (census with content.load_all), the compact order is report.py:639-640, 'Read the report' is report.py:602-603, and the Phase 3 log (WEBSITE_IMPLEMENTATION_LOG.md:405-406) records the compact order for them without a stated reason, so reversing it is open.

#### report-11. Lead photo and a photo strip for multi-day pages

**Observation.** Multi-day pages keep the map-first order with no lead photo and no section row (multiday.py:778-799; DEVELOPING.md:534-535), a decision the Phase 3 log left open (log:549-550), and the review rated the first photograph as 6.7 phone screens down on the Haute Route (IMPLEMENTATION_REPORT.md:845-847). Nine of the ten multi-day trips with day files have day photos (49 photos), and resolve_cover already picks a day photo as the card and share image (content.py:278-321, source 'day'), so a shared link previews a photo the page itself buries under the map, the day nav, the stitched profile and the stage table.

**Evidence.** `tools/sitegen/pages/multiday.py:778-799`; `docs/DEVELOPING.md:534-535`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:549-550`; `docs/IMPLEMENTATION_REPORT.md:845-847`; `tools/lib/content.py:278-321`; `content/trips/chamonix-zermatt-haute-route/days/03.md`; `desktop-multiday-hauteroute.jpeg`; `desktop-multiday-hauteroute.jpeg`; `tools/sitegen/pages/multiday.py:784-787`; `tools/sitegen/pages/report.py:46-58`; `tools/sitegen/pages/series.py:511`; `tools/lib/content.py:278-283`; `docs/CONTENT_GUIDE.md:76`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:549-550`.

**Proposal.** Reuse report.hero on multi-day pages when report.lead_photo(t) exists (the cover resolved from the day photos; cover_focal_* apply), placed after the title block and before the strip, with cover_preload in place of the overview map preloads. Add to overview() a photo strip under the stage table: one .th square per day with photos (the series' thumbs idiom, series.py:321-338), each linking to #day-N, so the pictures are visible before the chapters. No section row: the day nav already is one. Add the multi-day case to the hero tests.

**Files.** `tools/sitegen/pages/multiday.py`, `assets/css/pages/multiday.css`, `docs/DEVELOPING.md`, `tests/test_report_page.py`.

**Effort.** M. Visitor value 3.3, author value 1.3, confidence high.

**Also covers.** visual-06 (merged into this finding).

**Already known.** docs/WEBSITE_IMPLEMENTATION_LOG.md Phase 3 'Remaining issues' (549-550); docs/IMPLEMENTATION_REPORT.md 15.4.12

**Risk.** Reverses the Phase 3 decision; the hero becomes the LCP image on those pages (measure one). The .th copies exist only where thumbs.py was run (208 tracked), so fall back to the .sm copy as thumbs() does.

**Decision for Eric.** Whether multi-day pages should open with a photo like single-day stories do.

**Review note.** Kept as written by all three skeptics.

#### report-03. Stop cropping a third of every 4:3 lead photo on desktop

**Observation.** The lead photo frame is 3:2, 4:3 under 560 px and 2:1 from 1200 px, with object-fit: cover (report.css:129, 135, 138). 43 of the 45 stories that have a lead photo use a 4:3 photo (w/h under 1.4 in their index.md), so at 1248 px a 1600×1200 photo is drawn 1248×624 and loses a third of its height; on the Matterhorn report the focal point (cover_focal_y: 40) keeps the spires and drops the sky and snowfield (desktop-report-matterhorn.jpeg, top 1500 px). The same rule crops the PCT lead (series.py:509-511 reuses report.hero).

**Evidence.** `assets/css/pages/report.css:126-138`; `tools/sitegen/pages/report.py:42-54`; `tools/sitegen/core.py:811-830`; `content/trips/matterhorn-peak-west-couloir/index.md:13-14`; `desktop-report-matterhorn.jpeg`; `tools/sitegen/pages/series.py:508-511`.

**Proposal.** Let the desktop hero keep more of the photo's own shape. Build three variants on Matterhorn and the PCT and show them side by side before choosing (memory rule): (a) a one-line CSS change of the 1200+ cap from 2:1 to 3:2 (report.css:138), which cuts a 4:3 photo's crop from a third to about 11 percent; (b) natural shape clamped: hero() writes style="--ar:<w>/<h>" on .rep-hero-a from the photo entry's w and h, and report.css sets .rep-hero .cover-img { aspect-ratio: var(--ar, 3 / 2); max-height: min(72vh, 840px); object-fit: cover }, noting that on a 900 px-tall window 72vh is 648 px, close to today's 624, so this variant shows its gain only on tall windows; (c) today's 2:1. Phones keep 4:3 (a 4:3 photo then shows whole) and object-position keeps the focal point. Pin the chosen variant with a test on the emitted style (if b) or a CSS check in tests/test_report_page.py. Effort S.

**Files.** `assets/css/pages/report.css`, `tools/sitegen/pages/report.py`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 2.3, author value 1.7, confidence high.

**Risk.** A 4:3 hero at 1248 px is 936 px tall, so the strip and write-up move about 300 px further down on desktop; the hero preload sizes (HERO_SIZES) stay valid.

**Decision for Eric.** Which frame he wants: the photo as shot (clamped), 3:2, or the current 2:1 band.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: report.css:129, 135, 138 set 3:2, 4:3 under 560 and 2:1 from 1200 with object-fit cover; 43 of the 45 story pages with a lead photo have a cover under 1.4 (census), Matterhorn has cover_focal_y: 40 (index.md:14), and series.py:511 reuses report.hero. Feasible: a style attribute from hero() plus CSS, no render.

#### resilience-06. Let phone galleries keep a panorama's or tall portrait's shape

**Observation.** Under 760 px the gallery grid gives every landscape a 3:2 box and every portrait a 3:4 box (solo 4:5) with `object-fit: cover` (base.css:470-478), whatever the photo's shape; the `--ar` custom property that `photo_rows` writes on each link (core.py:930-935) is used only by the desktop rows. Content holds 7 landscapes wider than 2:1 (up to 3.14:1; e.g. half-dome photos/02 at 1600×566 and bryce-canyon photos/02 at 1600×572) and 5 portraits narrower than 0.6 (derailleur-down photos/01 at 738×1600, counted over the 398 photos with sizes): on a phone a 2.8:1 panorama shows about half its width and a 0.46 portrait about 60% of its height until the viewer is opened. The story hero crops the same way at 4:3 under 560 px (report.css:133-136), though no written report's lead is wider than 2:1 today. PCT thumbnails are square contact sheets by design.

**Evidence.** `assets/css/base.css:460-478`; `tools/sitegen/core.py:905-935`; `assets/css/pages/report.css:129-138`; `content/trips/half-dome/index.md`; `content/trips/bryce-canyon/index.md`; `content/trips/derailleur-down/index.md`.

**Proposal.** In the phone block of base.css (lines 470-478): .jph--l img { aspect-ratio: var(--ar) } so a full-width landscape keeps its own shape (the ratio is inline on the link, core.py:930-931, so the box is sized before the file arrives), and .jph--solo img { aspect-ratio: max(var(--ar), 0.6) } so a lone portrait keeps its shape down to 0.6 (if max() inside aspect-ratio proves unsupported in the cascade reader or a browser, emit a clamped --arp from photo_rows instead). Keep 3:4 for paired portraits. Add one cascade case in tests/test_a11y_static.py for the two selectors at 390 px. Leave .rep-hero and photo_partition alone: no written report's lead photo is wider than 2:1 today. Effort S.

**Files.** `assets/css/base.css`, `assets/css/pages/report.css`, `tools/sitegen/core.py`, `tests/test_report_page.py`, `tests/test_a11y_static.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Already known.** IMPLEMENTATION_REPORT.md 10.7 (the .th copy and panoramas; a different component)

**Risk.** `sizes` (PHONE_FULL) and the 800 px `.sm` copy stay as they are; a 3:1 panorama on a 3x phone is drawn from an 800 px file (known 10.7). No layout shift since the ratio is inline.

**Review note (condensed; the observation and proposal above are the revised text).** The gallery half is verified and cheap: base.css:470-478 gives every phone landscape a 3:2 box and every solo portrait 4:5 with object-fit: cover; photo_rows writes --ar inline on each .jph link (core.py:930-931), so a child img rule can use var(--ar) with no Python change and no layout shift; the counts hold (over 398 sized photos: 7 landscapes wider than 2:1, the widest 3.14:1 on the PCT and 2.83:1 half-dome/02; 5 portraits under 0.6, derailleur-down/01 at 0.46).

#### visual-03. 'More like this' head: a factual label instead of the selection rule

**Observation.** on every report with a region and a Newer/Older neighbour the section head's meta reads SAME REGION, THEN ACTIVITY · NEAREST IN DATE · NEWER / OLDER NOT REPEATED (core.py:1332-1334; a region-less report reads SAME ACTIVITY, and the third item appears only with a pager neighbour): three mono-caps items that document how the cards were picked rather than what they are. On the Matterhorn page the three cards are all Eastern Sierra backcountry-ski days (`data-region="eastern-sierra" data-act="ski"` in the built page).

**Evidence.** `desktop-report-matterhorn.jpeg (More like this head)`; `desktop-bare-ride.jpeg (More like this head)`; `tools/sitegen/core.py:1325-1338`; `tests/test_related.py:418-427`; `tools/sitegen/core.py:1325-1337`; `_site/trips/back-to-clipless/index.html (More like this section)`; `.cache/plan2/shots/phone-bare-ride.jpeg`.

**Proposal.** in `related_block` (core.py:1325), derive the meta from what the picked reports share with the page: all share region and activity → `<REGION> · <ACTIVITY WORD>` (e.g. EASTERN SIERRA · BACKCOUNTRY SKI); region only → the region; activity only → the activity word; otherwise `N REPORTS`. Region comes from `x['region']` and the activity word from `core.NAV` / `core.ACT`, so the facts-only rule holds. Keep the picking rule in the docstring; update docs/DEVELOPING.md:544-545 and docs/CONTENT_GUIDE.md:604-605, which both spell out today's wording; retarget tests/test_related.py:418-427 (test_rule_line_says_how_the_reports_were_chosen, test_rule_line_without_a_region). Files: add docs/CONTENT_GUIDE.md.

**Files.** `tools/sitegen/core.py`, `tests/test_related.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 2, author value 1.3, confidence high.

**Also covers.** copy-06 (merged into this finding).

**Risk.** Tests pin the current wording; the 'NEWER / OLDER NOT REPEATED' note disappears from the page (it stays in the docs).

**Review note (condensed; the observation and proposal above are the revised text).** Observation reproduces: core.py:1325-1338 builds the rule line; the matterhorn-bottom and bareride-bottom crops both show SAME REGION, THEN ACTIVITY · NEAREST IN DATE · NEWER / OLDER NOT REPEATED; the Matterhorn page's three related cards are all `data-region="eastern-sierra" data-act="ski"` (_site/trips/matterhorn-peak-west-couloir/index.html); the built back-to-clipless page carries the same line.

#### copy-09. One name per report section in the row, the bottom bar and the headings

**Observation.** The same anchors carry different names: the story section row says Report · Photos · Route · Trip details (report.py:76-92; 'Trip details' goes to #beta or #stats); the phone bottom bar says Report · Map · Photos · GPX on a story page and Map · Profile (or Beta / Stats) · Report · GPX on a compact one (report.py:323-358); the blocks are headed 'Beta' (report.py:251), 'Elevation' or 'Speed' (report.py:225, 211) and 'Trip report' (the write-up's H2), and the map has no heading. The row's order is the plan's, not the page's: the story page's sections run report, map, profile, photos (docs/IMPLEMENTATION_REPORT.md:516-517, section 12 decision 10).

**Evidence.** `tools/sitegen/pages/report.py:76-92`; `tools/sitegen/pages/report.py:323-358`; `tools/sitegen/pages/report.py:258`; `_site/trips/back-to-clipless/index.html (bottom bar Map · Profile · GPX)`; `docs/IMPLEMENTATION_REPORT.md:516-517`; `tools/sitegen/pages/report.py:76-92`; `tools/sitegen/pages/report.py:239-253`; `tools/sitegen/pages/report.py:323-358`; `assets/css/pages/report.css:59-65`; `desktop-report-matterhorn.jpeg`.

**Proposal.** One table in report.py used by section_nav and bottom_bar: #report 'Report', #map 'Map', #profile 'Elevation' (or 'Speed'), #photos 'Photos', #beta 'Beta', #stats 'Stats'; both lists in page order (story: Report · Map · Elevation · Photos; compact: Map · Elevation · Beta · Report · Photos); 'Trip details' and 'Route' retired; the write-up H2 'Trip report' and the row's 'Report' reconciled to one word. Anchor ids unchanged. multiday.py keeps its own Map · Days · Report · GPX bar but takes the Map, Report and GPX labels from the same table. Update tests/test_report_page.py (section_nav :627-722, bottom_bar :167-185).

**Files.** `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 2.3, author value 1, confidence high.

**Also covers.** report-17 (merged into this finding).

**Already known.** docs/IMPLEMENTATION_REPORT.md section 12 decision 10 (section row order)

**Risk.** Ids and URLs stay; only labels and order change.

**Decision for Eric.** 'Map' or 'Route' for the map; 'Beta' or 'Details' for the rail.

**Review note (condensed; the observation and proposal above are the revised text).** Not built, but partly a recorded decision and the labels were the plan's own. Reproduced in the built pages and the crop of desktop-report-matterhorn.jpeg: the section row reads Report · Photos · Route · Trip details (report.py:76-92, 'Trip details' to #beta or #stats at :90); the Matterhorn bottom bar reads Report · Map · Photos · GPX and back-to-clipless Map · Profile · GPX (report.py:323-358); the blocks are headed 'Beta' and 'Elevation'/'Speed' and the map has no h2 heading (h2 list of _site/trips/matterhorn-peak-west-couloir/index.html).

#### copy-04. Label track-only trips on cards and rows, as the journal already does

**Observation.** 39 published trips (25 rides, 7 hikes, 4 ski, 3 other) have no write-up and no photos (counted with tools/lib/content.load_all, day files included). Their explorer and home cards show DATE · PLACE, the title, the activity chip and distance/gain, and nothing says what is missing: data-writeup="0" is the only marker (_site/trips/index.html, the back-to-clipless card). List rows get .trow--brief with no words (core.py:1188). Only a home featured card says 'View trip' instead of 'Read the report' (home.py:98-101). The PCT journal already labels such days 'TRACK ONLY' in its rows and month index (series.py:35-48). Cards also drop the route shape that rows carry in their meta line (core.py:1183 vs trip_tags(shape=False) at core.py:1292).

**Evidence.** `tools/sitegen/core.py:1169-1197`; `tools/sitegen/core.py:1258-1293`; `tools/sitegen/pages/home.py:98-101`; `tools/sitegen/pages/series.py:35-48`; `_site/trips/index.html (li.tcard data-slug="back-to-clipless")`; `_site/trips/back-to-clipless/index.html`.

**Proposal.** Add a 'Track only' status tag in core.trip_tags for a single-day trip (kind 'trip') with no write-up and no photos, so it appears on explorer and home cards (trip_card calls trip_tags(t, shape=False), core.py:1291), list rows (trip_row, core.py:1196) and the compact report's title block, next to the existing Multi-day/Series/Planned tags. No new Mono-S line, no repeated shape or moving time, no CSS change (.tag exists). Keep 'View trip' (home.py:101) and the 'Has a write-up' filter. Tests in tests/test_cards_extra.py and the row tests. Effort S.

**Files.** `tools/sitegen/core.py`, `assets/css/base.css`, `tests/`.

**Effort.** S. Visitor value 2.3, author value 1, confidence high.

**Risk.** Facts only: every item comes from front matter or stats; the wording of the label is site copy.

**Decision for Eric.** The label word: 'Track only', 'Recording only' or 'No write-up'.

**Review revision (applies on top of the text above).** Observation (corrected): 39 single-day trips have no write-up and no photos. Their explorer and home cards show DATE · PLACE, the title, the activity chip and the stats line, with data-writeup="0" as the only marker (core.py:1258-1293); list rows get .trow--brief with no words (core.py:1169-1197) but already show the route shape in the meta line (:1181-1182) and moving time in the stats cells (:1066-1089); the compact report page has no status tag. The PCT journal labels such days 'TRACK ONLY' (series.py:35-48, :141). The empty slot is a documented choice (docs/CONTENT_GUIDE.md:164; home.py:159; plan:154, 309), so this is a reversal for Eric to decide. Proposal: on cards, when a single-day trip has no write-up and no photos, add a Mono-S line built only from fields, 'TRACK ONLY · OUT‑AND‑BACK · 2:03 MOVING' (SHAPE_CAPS, core.hm); on list rows add only the 'TRACK ONLY' word, since shape and moving time are already shown; on the compact report page add core.tag('Track only') to the title-block tags via a new trip_tags status; keep 'View trip' and the 'Has a write-up' filter; update docs/CONTENT_GUIDE.md:164 and the home.py:159 docstring; tests beside tests/test_home.py:166-172 and tests/test_cards_extra.py.

**Review note (condensed; the observation and proposal above are the revised text).** Not built, but the empty slot is a documented and tested choice, and the proposed row line duplicates what rows already show. The count holds (39 trips with no write-up and no photos: 25 mtb, 7 hike, 4 ski, 3 other, all kind 'trip'), the journal precedent is real (series.py:35-48 'TRACK ONLY'), and the card's only marker is data-writeup="0" (core.py:1285-1287). The count reproduces exactly: 39 published non-series trips with no write-up and no photos at trip or day level (25 mtb, 7 hike, 4 ski, 3 other) via content.load_all. The back-to-clipless explorer card carries data-writeup="0" and shows only DATE · PLACE, title, chip and distance/gain (_site/trips/index.html).

#### report-04. Show elapsed time, finish time and pace from facts already recorded

**Observation.** All 156 single-day index.md files carry start_time, moving and elapsed, but the page shows only Moving with 'Start h:mm AM' as a sub-line (core.py:983-989); elapsed is loaded as elapsed_s (content.py:503) and used nowhere under tools/sitegen (grep). Phones hide every strip sub-line (report.css:48), so a phone reader never sees the start time (phone-bare-ride.jpeg: 'MOVING 2:03 h:mm', no START line). MTB gets Avg speed and flat water Avg pace, hikes and ski tours get no pace (core.py:997-1023).

**Evidence.** `tools/sitegen/core.py:983-989`; `tools/sitegen/core.py:997-1023`; `tools/sitegen/core.py:1041-1063`; `tools/lib/content.py:503`; `assets/css/pages/report.css:46-48`; `content/trips/matterhorn-peak-west-couloir/index.md:5-18`; `phone-bare-ride.jpeg`; `tools/sitegen/pages/multiday.py:603-627`.

**Proposal.** In _cell_moving (core.py:983-989): value stays the moving time; sub-line becomes meta_items(['ELAPSED 9:34', 'h:mm AM - h:mm PM']) where the finish is start_time plus elapsed_s (both from index.md; show only when both exist). core.strip (core.py:1026-1033) writes every cell as <div class="strip-c"> with no per-cell class, so extend the cell tuple with a modifier class (strip-c--time) there before adding to report.css, inside the phone block at :37-51: body.p-report .rep-strip .strip-c--time .strip-s { display: block }. Or append 'h:mm AM - h:mm PM' to the map caption's 'As recorded on …' item (report.map_caption, report.py:158). Add 'Avg pace' (min/mi via _pace, core.py:991) as a fifth cell for hiking in strip_cells (core.py:997-1023), so the strip rule reads: MTB speed, flat water and hiking pace, ski none. stats_note (core.py:1041-1063) gains 'Elapsed includes stops.' Mirror elapsed in multiday.rail_stats (multiday.py:603-627, whose START sub-line is the same pattern) and as a title on the stage table's Moving cells (multiday.py:553). Tests in tests/test_report_page.py.

**Files.** `tools/sitegen/core.py`, `assets/css/pages/report.css`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tests/test_report_page.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 2.3, author value 1, confidence high.

**Already known.** docs/PRIVACY_NOTES.md section 6 (timestamps)

**Risk.** Times of day: the start time is already printed on every report and every published GPX carries its timestamps, so nothing new becomes public, but a finish time is one more plain-text line; PRIVACY_NOTES.md section 6 lists timestamps as the author's decision. A derived finish (start + elapsed) must be labeled as such or read from the last GPX fix.

**Decision for Eric.** Show finish times, or only elapsed; and whether hikes get a pace cell.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: _cell_moving shows Moving with a 'Start' sub-line only (core.py:983-989), elapsed_s is loaded (content.py:503) and unused anywhere under tools/sitegen (grep), all 156 single-day index.md files carry elapsed, phones hide every strip sub-line (report.css:48, confirmed on the built Matterhorn page where 'Start h:mm AM' is a .strip-s). Feasible in Python. Observation reproduces: all 156 single-day trips have start_time, moving_s and elapsed_s (count.py); _cell_moving at core.py:983-989 prints Moving with a 'Start …' sub-line only; content.py:503 loads elapsed_s and grep finds no use of it under tools/sitegen; report.css:48 sits inside the phone block opened at :37 (@media (max-width: 759.98px)) and hides .strip-s; the crop of phone-bare-ride.jpeg shows MOVING 2:03 h:mm with no Start line while _site/trips/back-to-clipless/index.html carries 'Start h:mm AM' in a strip-s; strip_cells at core.py:997-1023 gives pace to flat water and speed to MTB only; multiday.rail_stats at multiday.py:603-627 has the same START pattern.

#### report-05. Add clock time to the elevation table and the GPS max

**Observation.** elevation_table (report.py:172-198) reads the track with fit_reader.read_gpx, which returns a timestamp per point (fit_reader.py:129-149), and 156 of 157 single-day tracks carry <time>, but the table prints Mile · Elevation only (the built Matterhorn page: 14 rows, two columns). The profile marks the GPS max but not when it was reached (report.py:222-223).

**Evidence.** `tools/sitegen/pages/report.py:172-198`; `tools/sitegen/pages/report.py:218-228`; `tools/lib/fit_reader.py:129-149`; `_site/trips/matterhorn-peak-west-couloir/index.html`; `content/trips/matterhorn-peak-west-couloir/index.md:5-6`.

**Proposal.** In elevation_table keep the point index j and, when tr.raw[j][3] is set, add a third column 'Time' in the trip's zone (zoneinfo.ZoneInfo(t['timezone']), formatted by core.ftime); omit the column when no point has a time or the zone cannot be loaded (never fall back to UTC). In profile_section append 'AT h:mm AM' to the GPS MAX item from the timestamp of tr.imax, under the same conditions. Single-day pages only; a multi-day day's GPS max lives in rail_stats (multiday.py:608-611), so do the same there as a sub-line only after the time-zone item in IMPLEMENTATION_REPORT.md section 12 (item 12) is settled, since a wrong zone would print wrong clock times. Tests: a fixture track with times and one without, in tests/test_report_page.py. Effort S.

**Files.** `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Risk.** Same time-of-day consideration as report-04. CI's Ubuntu has tzdata; a missing zone must fall back to omitting the column, never to UTC.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: elevation_table prints Mile and Elevation only (report.py:172-198; the built Matterhorn page), fit_reader.read_gpx keeps a timestamp per point (fit_reader.py:129-149), 156 of 157 single-day tracks carry <time>, all 156 declare timezone, and zoneinfo resolves America/Los_Angeles on the local 3.9.6 (tracks.py:11 already imports it with a fallback). Feasible at build time, no render.

#### report-10. Mark the days with words and photos in the multi-day day nav

**Observation.** The Haute Route has 6 days, 2 with a write-up and 3 with photos (days/01-06.md); across the ten multi-day trips with day files, 17 of 34 days are written up. The sticky day nav chip shows the day number, sparkline, date and distance (multiday.py:398-413) and the stage table Day, Date, From → To, numbers and GPX (multiday.py:517-571); neither says which days have words or photos, so a reader scrolls six chapters (desktop-multiday-hauteroute.jpeg is 11,528 px tall, the phone capture 34,797) to find the two with text. The bottom bar's Report item jumps to the first written day only (multiday.py:753-763).

**Evidence.** `tools/sitegen/pages/multiday.py:398-413`; `tools/sitegen/pages/multiday.py:517-571`; `tools/sitegen/pages/multiday.py:574-591`; `tools/sitegen/pages/multiday.py:753-763`; `content/trips/chamonix-zermatt-haute-route/days/01.md`; `desktop-multiday-hauteroute.jpeg`; `phone-multiday-hauteroute.jpeg`.

**Proposal.** In day_nav add a Mono-S item after the distance ('WRITE-UP', '3 PHOTOS', both when both; nothing otherwise) and an is-written class that draws a small ink dot in the chip; under 760 show the dot only (the row scrolls horizontally, multiday.css:66, so keep chips short). In day_index (phones) add the same words to .mul-di-m. Add the counts to the Overview's shead meta via days_meta ('6 DAYS · 5 HUT NIGHTS · 2 WRITE-UPS · 7 PHOTOS'). Leave the stage table as it is. Tests on the emitted chips and the meta line in tests/test_report_page.py's MultiDayPageTests (there is no tests/test_multiday_page.py; today only tests/test_a11y_static.py touches day_nav). Effort S.

**Files.** `tools/sitegen/pages/multiday.py`, `assets/css/pages/multiday.css`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Risk.** The chip row on phones gets longer; keep the item short (a dot only under 760).

**Review note (condensed; the observation and proposal above are the revised text).** Verified: Haute Route has 6 days, 2 written, 3 with photos (7 photos: days 04, 05, 06), 17 of 34 multi-day days are written up (ten trips with day files, counted), day_nav shows D#, sparkline, date and distance only (multiday.py:398-413), the stage table has no such column (517-571), the bottom bar's Report item goes to the first written day (753-763), and the captures are 11,528 and 34,797 px tall (sips).

#### gap6-04. On phones, put the stats footnote under the strip as a disclosure

**Observation.** Phones hide .strip-note under the strip (report.css:48, multiday.css:24) and show a second copy, .rep-note-ph, under the map caption (report.py:613-622, report.css:50; multiday.py:393). In the story layout the map follows the Beta rail and the write-up (built Matterhorn page: #stats at byte 17,831, #report at 20,132, #map at 20,635), so the first explanation of GPS MAX a phone reader can see, a term on the first screen, is at byte 40,922 of 84,758 (live page identical); on Chamonix-Zermatt it is at 52,546 of 308,600. Only the goal page (report.css:212-214) and the series page (no rule hides body.p-series's note; series.py:166) keep their note under the strip on phones.

**Evidence.** `assets/css/pages/report.css:35-51`; `assets/css/pages/report.css:212-214`; `assets/css/pages/multiday.css:19-25`; `tools/sitegen/pages/report.py:613-622`; `tools/sitegen/pages/multiday.py:345-350`; `tools/sitegen/pages/multiday.py:393`; `_site/trips/matterhorn-peak-west-couloir/index.html`; `_site/trips/chamonix-zermatt-haute-route/index.html`; `tests/test_report_page.py:2480`; `tests/test_report_page.py:2656`; `tests/test_track_rules.py:331-335`.

**Proposal.** Add a shared helper in core (e.g. core.strip_more(note_html, other_units_html)) that wraps a note in <details class="strip-more"> right after <dl class="strip"> inside #stats: the summary is a 44 px row 'About these numbers' styled like .eltab summary (report.css:68-69), the body is one Mono-S line of the other unit (the values hidden in .strip-s, e.g. 20.6 KM · 1,616 M · 3,643 M · START h:mm AM) followed by the footnote sentences (and gap6-05's glosses and About link). Call it from report.py:613 with core.stats_note(t) and from multiday.py with its own stats_note() (or, if gap6-05 lands, core.stats_note); leave series and goal pages as they are. Show it below 760 only (the inline <p> shows from 760); delete the rep-note-ph emission at report.py:622 and multiday.py:393 and the .rep-note-ph rule at report.css:50. No JavaScript. Update tests/test_report_page.py:2656 and :2721 (they expect the rep-note-ph copy in the map section; :2480 asserts its absence and keeps passing) and tests/test_track_rules.py:331-335 (the cls argument of core.stats_note).

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tools/sitegen/pages/series.py`, `assets/css/pages/report.css`, `assets/css/pages/multiday.css`, `tests/test_report_page.py`, `tests/test_track_rules.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Risk.** Adds a 44 px row to the Phone-Report-A first screen (report.css:35-36 names the strip → map rhythm); the summary label is new interface copy for Eric to confirm; the km line inside the details duplicates nothing visible on phones.

**Review note (condensed; the observation and proposal above are the revised text).** The observation is confirmed: in the built Matterhorn page rep-note-ph is at byte 40,940 of 84,758, after #report (20,132) and #map (20,635), so a phone reader meets GPS MAX on the first screen and its explanation far down the page; phones hide .strip-note (report.css:48, multiday.css:24). The mechanism reproduces: report.css:48 and multiday.css:24 hide .strip-note on phones, report.css:50 shows .rep-note-ph, report.py:613 emits the strip note and :622 the rep-note-ph copy, multiday.py:393 likewise, report.css:214 keeps the goal's note, and DOM order on the Matterhorn page is #stats → .rail-b#beta → h2#report-h + write-up → #map (the write-up text sits between the two ids).

#### gap6-05. One glossary feeds the footnote and About, with a link between them

**Observation.** The strip footnote (core.stats_note, core.py:1041-1064) explains the source ('via Strava'), a Track note from the beta, pace (flat trips), average speed (mtb) and GPS max, but never 'Moving' (6:34 h:mm, core.py:983-988), which is defined nowhere on a report; About's method item 02 says only that moving time 'comes from that recording' (about.py:103-104), while the real rule drops stops (tracks.py:121-127: gaps of at most 120 s moved at 0.3 m/s or more; Strava imports take Strava's Moving Time, strava.py:50). The generator has no <abbr>, <dfn> or title on any term (one title= at multiday.py:538) and nothing links to About's 'How these reports are made' (#abo-how-h, about.py:116). Proposal unchanged; note that the 'via Strava' wording of the same note is already an open author decision (IMPLEMENTATION_REPORT.md section 12.10), so the glossary sentences should be settled together with it.

**Evidence.** `tools/sitegen/core.py:1041-1064`; `tools/sitegen/core.py:983-988`; `tools/sitegen/pages/about.py:98-116`; `tools/lib/tracks.py:118-127`; `tools/lib/strava.py:50`; `tools/sitegen/pages/multiday.py:538`; `tools/sitegen/core.py:636-658`; `_site/trips/matterhorn-peak-west-couloir/index.html`; `tests/test_report_page.py:2320`; `tests/test_track_rules.py:331-335`.

**Proposal.** Add a GLOSS mapping in one module (copy-19's strings module if it is built, else core.py beside KEY_SYMBOLS at core.py:636): moving → 'Moving is time spent moving; stops are left out.', gps_max / avg_speed / pace → the sentences stats_note already has (core.py:1047-1060), vertical → 'The profile's heights are drawn stretched ×N' (gap6-06). core.stats_note(t, here) appends the moving sentence when moving_s is set and ends with '<a href="about/#abo-how-h">How these numbers are made</a>' built with core.link; about.method() (about.py:98-117) composes its item 02 from the same strings so the two never drift. No title tooltips (touch cannot show them). The multi-day note (multiday.py:345-350) and the series note (series.py:166) take the same sentences; section.py:195 already calls core.stats_note and follows. Update the sentence constants at tests/test_report_page.py:2285-2288 and tests/test_track_rules.py:44-47 (used by :331-335), and any assertion that counts the strip's focus stops.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/about.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tools/sitegen/pages/series.py`, `tools/sitegen/pages/section.py`, `tests/test_report_page.py`, `tests/test_track_rules.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Risk.** The Moving sentence is a definition, not a trip fact, but it must match both sources (the tool's rule and Strava's both drop stops); a link inside the footnote adds a focus stop to the strip; the desktop note grows by about one line.

**Decision for Eric.** The exact wording of the Moving sentence.

**Review note (condensed; the observation and proposal above are the revised text).** Proposal verified not built: core.stats_note (core.py:1041-1064) has no sentence for Moving and no link; the built Matterhorn page contains neither 'moving time' nor 'Moving is' (grep: 0); the only title= in the generator is multiday.py:538 and there is no <abbr>/<dfn>; 'abo-how' appears only in about.py:116; tools/sitegen/ has no strings module (ls: no strings.py). The two places that explain GPS max already say the same words (about.py:104-105 and core.py:1059 are identical), so a shared GLOSS module across six page modules guards against a drift that has not happened and is effort M for little return. What has real value and is missing is the link: nothing outside about.py points at #abo-how-h (grep), and a reader of a report has no route to the method section. Observation reproduces: core.stats_note (core.py:1041-1064) explains GPS max, pace and average speed only; _cell_moving (core.py:983-988) emits 'Moving … h:mm' with no definition; about.py:103-104 (item 02 of method()) says only 'Distance, gain and moving time come from that recording'; tracks.py:121-127 counts only steps of 0 < dt ≤ 120 s at ≥ 0.3 m/s and strava.py:50 takes Strava's 'Moving Time'; grep finds no <abbr>/<dfn> in tools/sitegen/, one title= tooltip at multiday.py:538 (core.py's two title= hits are a parameter and the RSS <link>), and 'abo-how-h' only in about.py:116; KEY_SYMBOLS at core.py:636-658 decode skin/ski at :638-639 and :653-654.

#### gap6-06. Rename the chart item 'VERTICAL ×N' to 'VERTICAL SCALE ×N'

**Observation.** Every elevation chart head carries VERTICAL ×N, one item per rendered width (core.vx_line, core.py:556-574): the built Matterhorn head holds ×1.4 (wide), ×1.9 (col) and ×2.9 (phone), shown one at a time by the .vx--wide/col/phone classes, and a Haute Route day chart reads 7.7 MI · +2,700 FT · −1,821 FT · VERTICAL ×2.6 / ×4.0 (col / phone; multiday.py:647, phone-multiday-hauteroute.jpeg). Nothing on any page says what the figure means: the word 'exaggeration' appears only in code (the comment at multiday.py:507, the docstring at core.py:557, and the hillshade parameter in mapkit.py:330/798 and render.py:416). No test pins the string (grep VERTICAL in tests/: none) and docs/DEVELOPING.md does not mention it.

**Evidence.** `tools/sitegen/core.py:556-574`; `tools/sitegen/pages/multiday.py:506-507`; `tools/sitegen/pages/multiday.py:647`; `tools/sitegen/pages/report.py:223`; `tools/sitegen/pages/section.py:209`; `_site/trips/matterhorn-peak-west-couloir/index.html`; `.cache/plan2/shots/phone-multiday-hauteroute.jpeg`.

**Proposal.** In core.vx_line change the item text to nb('VERTICAL SCALE ×%.1f' % v); the callers at report.py:223, multiday.py:506 and :647 and section.py:209 inherit it, and the .vx--wide/col/phone classes stay. Check the 358 px phone chart head still wraps per item (meta_items, core.py:266-284). Add the vertical gloss through gap6-05 if that lands.

**Files.** `tools/sitegen/core.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Risk.** One wider item in the phone chart's Mono-S line; it wraps at separators, never mid-item.

**Review note (condensed; the observation and proposal above are the revised text).** The string reproduces: core.vx_line (core.py:556-574) writes nb('VERTICAL ×%.1f'); the built Matterhorn chart head carries three items, vx--wide ×1.4, vx--col ×1.9 and vx--phone ×2.9 (CSS shows one per width), and the Haute Route page's day chart reads '7.7 MI · +2,700 FT · −1,821 FT · VERTICAL ×2.6 / ×4.0' with ×4.0 the phone item (multiday.py:647 caller); report.py:223, multiday.py:506 and section.py:209 are the other callers; grep VERTICAL in tests/ finds nothing.

#### maps-01. Name the contour interval and keep in-map units honest under KM

**Observation.** Report maps label contours as bare numbers in feet ('8,000', '11,000') outside the MI|KM groups (map-wide.svg.html: three text.mk-cl, none inside the u-mi/u-km groups, which hold only the scale bar), so with KM selected the profile and scale bar switch to meters while the contours stay in feet. The rendered interval (meta.json maps.*.interval_ft: 200 wide, 400 col, 500 phone) is stated nowhere on the page. Mile discs and their key item ('Mile' / 'Mile, outbound', core.py:644-645) also stay imperial under KM. This is a documented rule today: docs/DEVELOPING.md:87-88 says 'Mile discs and contour labels stay imperial', so the change is a decision for Eric and the doc line must change with it.

**Evidence.** `rendered/trips/matterhorn-peak-west-couloir/map-wide.svg.html (three <text class="mk-cl"> labels without a u-mi/u-km group; the scale bar has both groups)`; `rendered/trips/matterhorn-peak-west-couloir/meta.json (maps.*.interval_ft 200/400/500)`; `tools/lib/mapkit.py:38 (.mk-cl), tools/lib/mapkit.py:1793-1800 (scale_bar_compact draws both units)`; `tools/sitegen/core.py:712-731 (map_caption), tools/sitegen/core.py:644-646 (KEY_SYMBOLS mile/mile_out)`; `docs/DEVELOPING.md:86-88 (fragments carry both units)`; `.cache/plan2/shots/desktop-report-matterhorn.jpeg (map at 1700-3100 px: contour labels and key row)`.

**Proposal.** (1) core.map_caption (core.py:712) takes an optional per-variant item built from meta['maps'][name]['interval_ft']: 'Contours every 200 ft' | '61 m' through core.U, one (html, cls) item per rendered width using the same .vx--wide|col|phone classes core.vx_line emits (core.py:556-575, base.css:394-396), so only the visible map's interval shows; report.map_caption (report.py:158), section.map_caption (section.py:89) and the goal map (via report.py:702) pass it, and the multi-day day caption (multiday.py:734-735, a plain ml() list) appends the same item itself. (2) KEY_SYMBOLS 'mile' and 'mile_out' labels go through core.U: 'Mile' | 'Mile (1.6 km)'. (3) In the renderer batch (maps-16): mapkit.contours_svg writes each contour label twice inside <g class="u-mi"> / <g class="u-km"> as scale_bar_compact does (mapkit.py:1792-1798), and the mile loop (mapkit.py:1079-1106) adds a kilometer disc set in a u-km group. Update docs/DEVELOPING.md:87-88 to describe the new behavior.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/section.py`, `tools/sitegen/pages/multiday.py`, `tools/lib/mapkit.py`, `tools/render.py`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Risk.** Every measured value must go through core.U (DEVELOPING.md rules); the caption grows one item per map; part (3) needs a re-render, so land it with maps-16.

**Review note (condensed; the observation and proposal above are the revised text).** Observation confirmed: rendered/trips/matterhorn-peak-west-couloir/map-wide.svg.html has three <text class="mk-cl"> labels (8,000 / 11,000 / 11,000) with no u-mi/u-km group while the scale bar has both (mapkit.py:1793-1800 scale_bar_compact); mapkit.contours_svg writes fmt_int(k * interval_ft) once (mapkit.py:427-437); meta.json interval_ft 200/400/500 is read nowhere in tools/sitegen (grep 'interval' in core.py and pages/*.py returns only the base-layer comments at core.py:517,535), and _site/trips/matterhorn-peak-west-couloir/index.html contains neither 'contour' nor 'interval'; KEY_SYMBOLS 'mile'/'mile_out' are plain strings (core.py:644-646); the mile loop adds one disc set (mapkit.py:1085-1106). Parts (1) and (2) are feasible and S: core.map_caption already takes (html, cls) items (core.py:712-722, the 'mapcap-2' items) and base.css:394-396 has the .vx--wide|col|phone display rules, so a per-variant 'Contours every 200 ft | 61 m' item built from meta['maps'][name]['interval_ft'] (verified in rendered/trips/matterhorn-peak-west-couloir/meta.json: 200/400/500) goes through core.U with no new machinery. Observation reproduces: rendered/trips/matterhorn-peak-west-couloir/map-wide.svg.html has exactly three <text class="mk-cl"> labels (8,000 / 11,000 / 11,000) and none sits inside the one u-mi and one u-km group (those hold only the scale bar, mapkit.py:1792-1798); meta.json maps.* interval_ft is 200/400/500; _site/trips/matterhorn-peak-west-couloir/index.html never contains the word 'contour'; the desktop key row reads 'Mile, outbound' from KEY_SYMBOLS at core.py:644-645; the crop of desktop-report-matterhorn.jpeg at 1700-3100 shows bare '8,000'/'11,000' labels and a 'MILE, OUTBOUND' key item.

#### maps-02. Key rows decode the base layer's trails and roads

**Observation.** Report maps draw OSM paths as gray dashed lines (.mk-trail, mapkit.py:47) and roads as white-on-gray casing pairs (.mk-roadc/.mk-road at mapkit.py:43-44, .mk-minorc/.mk-minor at 45-46) in the cached base layer, right beside the red dashed skin leg of a ski route, but the key row decodes only the route symbols (skin/ski or route, start · end, GPS max, mile): five items on the Matterhorn report's keyrow--d. A visitor cannot tell the gray dashes from a route and the key never says which lines are trails. The Matterhorn wide and col base layers carry one mk-trail and one mk-minor/mk-minorc path; the phone base has neither (render.SMALL sets trails=False and road_levels down to tertiary, render.py:38-40; mapkit.py:871).

**Evidence.** `tools/lib/mapkit.py:43-47 (.mk-road, .mk-minor, .mk-trail dashed gray)`; `rendered/trips/matterhorn-peak-west-couloir/map-wide.base.svg (contains class="mk-trail" and class="mk-minor" paths)`; `_site/trips/matterhorn-peak-west-couloir/index.html (keyrow--d: five items, none for trails or roads)`; `tools/sitegen/pages/report.py:133-156 (key_items), tools/sitegen/core.py:689-709 (feature_key reads the overlay only)`; `.cache/plan2/shots/desktop-report-matterhorn.jpeg (map at 1700-3100 px: gray dashed trail next to the red dashed ascent)`.

**Proposal.** Add KEY_SYMBOLS 'trail' ('Trail (OSM)': 0.75-1.5 px #8F8A7E, dash 3 2) and 'road' ('Road': a white line on a gray casing, drawn like the minor road since that is what report maps mostly carry). Add core.base_draws(t, name, pattern) that reads rendered/trips/<slug>/<name>.base.svg (or rendered/site/<name>.base.svg for site maps) the way core.drawn_ends (core.py:579-584) reads the overlay, matching class="mk-trail" for 'trail' and class="mk-road"|class="mk-minor" for 'road'. report.key_items (report.py:133), multiday.key_items (multiday.py:111) and day_map_keys (630), core.feature_key (core.py:689) and archive.legend (archive.py:107) append 'trail' / 'road' after the route symbols when the visible render's base layer contains them, so phone rows stay short. Tests with fixture base files for both cases in tests/test_report_page.py.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tools/sitegen/pages/archive.py`, `tools/sitegen/pages/section.py`, `tests/test_report_page.py`.

**Effort.** M. Visitor value 2.3, author value 1, confidence high.

**Risk.** Desktop key rows grow to seven items; keep the order route symbols first and let .keyrow wrap as it already does.

**Review note (condensed; the observation and proposal above are the revised text).** The observation holds: every one of the 157 map-wide.base.svg files contains a class="mk-trail" path and 101 contain class="mk-road", while 0 of the 157 map-phone.base.svg files draw a trail (render.py:40-41, SMALL trails=False), so the key gap is real on desktop and absent on phones. Reading the base layer at build time mirrors core._draws/drawn_ends (core.py:579-585, 680-686) and stays stdlib. Observation reproduces: mapkit.py:43-47 define .mk-roadc/.mk-road/.mk-minorc/.mk-minor/.mk-trail (trail = #8F8A7E 0.75 px dash 3 2); rendered/trips/matterhorn-peak-west-couloir/map-wide.base.svg and map-col.base.svg each contain one mk-trail and one mk-minor/mk-minorc path (map-phone.base.svg has none, consistent with SMALL's trails=False at render.py:38-40 and the gate at mapkit.py:871); the built page's keyrow--d has five items (Skin, Ski, Start · end, GPS max, Mile, outbound) and nothing for trails or roads; the crop of desktop-report-matterhorn.jpeg at 1700-3100 shows gray dashed OSM lines beside the red dashed skin leg.

#### benchmark-11. Beta rows and a references list that can link out

**Observation.** bikepacking.com route pages end with 'Additional Resources', a list of external links (trail hub, MTB Project, Trailforks, an FAQ); Stav's reports link out to directions; 14ers.com links the peak page. A report's Beta rows are label + value text only (checks.py:67 BETA_KEYS) and beta_list escapes the value (report.py:238-255), so a guidebook, forecast or trail-association link has nowhere to go but the write-up; goals already carry a `references` list with label and url (goals.py:165-176).

**Evidence.** https://bikepacking.com/routes/tahoe-twirl/; https://stavislost.com/hikes/trail/old-man-mountain-and-black-buttes-loop/; `tools/lib/checks.py:67`; `tools/lib/checks.py:80`; `tools/sitegen/pages/report.py:238-255`; `tools/lib/goals.py:165-176`.

**Proposal.** Allow an optional `url:` on a beta row (BETA_KEYS + 'url'; checks.py validates it with LINK_SCHEMES and the write-up link rules); `beta_list` (report.py:239-254) renders the value as `<a rel="noopener">` when `url` is set, marked with a new 16 px external-link glyph added to tools/lib/icons.py PATHS (none exists today; the goal page's references, report.py:446-455, are bare links and would take the same glyph). Add an optional top-level `references:` list on reports mirroring goal.json's rows minus id/checked_at, rendered as a 'References' block under Beta in the rail (and left as it is on goal pages). docs/CONTENT_GUIDE.md. Files: tools/lib/checks.py, tools/lib/icons.py, tools/sitegen/pages/report.py, tools/lib/content.py, docs/CONTENT_GUIDE.md, tests/test_checks.py, tests/test_report_page.py.

**Files.** `tools/lib/checks.py`, `tools/sitegen/pages/report.py`, `tools/lib/content.py`, `docs/CONTENT_GUIDE.md`, `tests/test_checks.py`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 2, author value 2, confidence high.

**Risk.** External links are Eric's choice; the validator keeps schemes to http/https/mailto.

**Review note (condensed; the observation and proposal above are the revised text).** Half of it is already covered and half rests on a wrong claim. Observation reproduces: BETA_KEYS = ('label', 'value') at checks.py:67, LINK_SCHEMES at checks.py:80, beta_list (report.py:239-254) escapes every value and emits no <a>, goals.py:165-180 validates a references list with id/label/url/checked_at/note; bikepacking.com/routes/tahoe-twirl/ ends with 'Additional Resources' linking Trailforks, MTB Project and a TAMBA FAQ; Stav's report has 'Route map and directions'; the 14ers report links /peaks/10349/13er-matterhorn-peak.

#### a11y-09. Offer 'View as table' under every elevation and speed chart

**Observation.** The mile-by-mile 'View as table' disclosure exists only on single-day reports (report.elevation_table). The six per-day profiles of a multi-day trip, its stitched profile, the section pages' featured chart and the speed charts are role="img" SVGs whose only text is their label ('Elevation profile of day 3'), so a non-sighted reader gets no shape of the day.

**Evidence.** `tools/sitegen/pages/report.py:172-198, 228`; `tools/sitegen/pages/multiday.py (no eltab emitter; grep)`; `tools/sitegen/pages/section.py:210-218`; `_site/trips/chamonix-zermatt-haute-route/index.html (six 'Elevation profile of day N' role=img, no table)`; `tools/lib/mapkit.py:2470`; `tools/sitegen/pages/report.py:172-198 (elevation_table), :205-228 (profile_section with the table)`; `tools/sitegen/pages/multiday.py:496-512 (stitched_profile), :634-651 (day_profile); grep finds no eltab in multiday.py`; `assets/css/pages/report.css:53-76 (.eltab styles)`.

**Proposal.** Move elevation_table into core (core.elevation_table(t_or_day, track_path, stats)) and call it in multiday.day_profile (tools/sitegen/pages/multiday.py:634-651, the function chapter() at :741 places under each day's map; the day's file is d['track']) and in section.profile_block (tools/sitegen/pages/section.py:199-212, under the chart that featured() at :173 emits); add a speed variant (3-minute average per mile, the same series render_speed_chart plots) for report.profile_section's speed branch and section.speed_block. Keep it a <details> so the page stays compact; the stage table (#stages, multiday.stage_table at :517) already covers the stitched profile, so link to #stages there instead of a second table. Files: tools/sitegen/core.py, tools/sitegen/pages/report.py, tools/sitegen/pages/multiday.py, tools/sitegen/pages/section.py, tests/test_report_page.py (MultiDayPageTests at :1967 holds the multi-day page tests; there is no tests/test_multiday_page.py).

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tools/sitegen/pages/section.py`, `tests/test_report_page.py`, `tests/test_build_site.py`.

**Effort.** M. Visitor value 1.7, author value 1, confidence high.

**Also covers.** maps-14 (merged into this finding).

**Risk.** Values come from the GPX via the same smoothing as the chart (facts-only holds); each table adds a few KB to the 300 KB multi-day pages. Units go through core.U so the MI|KM toggle applies.

**Review note (condensed; the observation and proposal above are the revised text).** Evidence holds: elevation_table exists only in report.py:172-198 and is called once at :228; multiday.day_profile (:634-651) and section.profile_block (:210-213) emit role=img charts with no table, and _site/trips/chamonix-zermatt-haute-route/index.html has six 'Elevation profile of day N' SVGs and zero class="eltab". Observation reproduces: tools/sitegen/pages/report.py:172-198 defines elevation_table and only profile_section (:228) calls it; grep finds no eltab/elevation_table in multiday.py or section.py; _site/trips/chamonix-zermatt-haute-route/index.html has 12 <svg role="img" aria-label="Elevation profile of day N"> (col + phone variant per day), one 'Stitched elevation profile of all 6 days', no <title>/<desc> inside, 0 'eltab', and id="stages" exists; the Matterhorn single-day page has 1 eltab; mapkit.py:2470 is the speed chart's role=img svg.

#### visual-19. Goal page: say the distance once, and size a one-cell strip

**Observation.** The planned-route title block puts '≈ 17.4 MI' in the chip row's date slot and the strip directly under it opens with 'DISTANCE ≈ 17.4 mi / 27.9 KM' as its only cell, a lone value under a 1,248 px pair of rules. Reports show the date in the chip row and the distance only in the strip.

**Evidence.** `desktop-goal-crystal-range.jpeg`; `tools/sitegen/pages/report.py:100`; `tools/sitegen/pages/report.py:363-391`; `assets/css/base.css:407-410`; `assets/css/base.css:422-433`.

**Proposal.** On the goal page drop the `≈ distance` from the title block when the strip follows: `date_slot` (report.py:95-101) feeds both the chip row's `.t-mono-s` (≥760) and `.rep-pdate` (phones, report.css:41-42), so the planned branch returns '' there while goal cards and tick-list rows keep their `≈` figures. When a strip has one or two cells cap each cell at a column width: `core.strip` (core.py:1025-1033) adds `strip--1`/`strip--2` beside the existing `strip--5`, and base.css gets `.strip--1 .strip-c, .strip--2 .strip-c { max-width: 294px }` from 760, rules spanning as now, so the value sits on the grid rather than floating; phones keep the 2x2 strip rules. Update tests/test_ticklist_page.py:641-644 (it pins the chip-row distance) and add a strip-class assertion beside its goal_strip tests (:714-718). Files: tools/sitegen/pages/report.py, tools/sitegen/core.py, assets/css/base.css, tests/test_ticklist_page.py.

**Files.** `tools/sitegen/pages/report.py`, `tools/sitegen/core.py`, `assets/css/base.css`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Risk.** Tests that pin the goal chip-row text; the strip's `--cells` class must gain the `strip--1`/`strip--2` variants in `core.strip`.

**Review note (condensed; the observation and proposal above are the revised text).** Reproduces: _site/trips/crystal-range-to-bayview/index.html has '≈ 17.4 MI' in the chip row's .t-mono-s slot and again in .rep-pdate, and the strip is `<dl class="strip" style="--cells:1">` with the single 'Distance ≈ 17.4 mi / 27.9 KM' cell; at ≥760 base.css:422-433 makes the strip `repeat(var(--cells, 4), minmax(0, 1fr))`, so that one cell spans the 1,248 px pair of rules, as desktop-goal-crystal-range.jpeg shows. report.py:95-101 date_slot returns the distance for a planned route, goal_strip at report.py:363-391 builds the cell, core.strip at core.py:1025-1033 writes --cells and already adds strip--5.

#### maps-04. Hover and touch readout on the profile, with a dot on the map

**Observation.** The elevation profile is a static SVG: the only way to read a value is the 'View as table' disclosure (0.5/1/2-mile rows, report.py:172-200) and the GPS max label, and nothing links a point of the profile to the map. The build already reads the GPX to make the table, meta.json stores the chart's axis mapping (y_lo, y_hi, pad_l, total_mi, h), the overlay is inline SVG, and mapkit carries a static 'scrub' readout (mapkit.py:2243-2267) that tools/render.py never calls.

**Evidence.** `tools/sitegen/pages/report.py:172-198 (elevation_table reads the GPX at build time), tools/sitegen/pages/report.py:205-228 (profile_section)`; `rendered/trips/matterhorn-peak-west-couloir/meta.json (charts.profile-*: y_lo, y_hi, pad_l, total_mi, h, vx)`; `tools/lib/mapkit.py:2240-2258 (scrub_mi / scrub options; no caller in tools/render.py)`; `assets/js/base.js (no chart code), assets/css/base.css:328-335 (.cv, overflow visible)`; `.cache/plan2/shots/desktop-report-matterhorn.jpeg and .cache/plan2/shots/phone-report-matterhorn.jpeg (profile sections)`; `tools/sitegen/core.py:484-527`; `tools/sitegen/core.py:596-607`; `rendered/trips/matterhorn-peak-west-couloir/meta.json`; `tools/render.py:212-262`; `tools/render.py:31`; `assets/js/base.js:136-204`; `desktop-report-matterhorn.jpeg`; https://www.komoot.com/smarttour/e1219367799/tahoe-rim-trail-loop-north-lake-tahoe; `rendered/trips/matterhorn-peak-west-couloir/meta.json (charts.profile-wide gx 732.76, pad_l 72, total_mi 12.78; maps.map-wide.outbound_only true)`; `rendered/trips/matterhorn-peak-west-couloir/profile-wide.svg.html (one path.pf-line)`; `rendered/trips/matterhorn-peak-west-couloir/map-wide.svg.html (path.mk-trk)`; `tools/lib/mapkit.py:1059`; `tools/sitegen/pages/report.py:168-198`; `tools/sitegen/pages/report.py:220-236`; `assets/js/base.js:136-204`.

**Proposal.** report.profile_section passes about 150 evenly spaced (km, m) samples from the same Track the table uses (about 1.5 KB) into core.chart_block (core.py:596-607) via a new attrs parameter so the .chart element carries data-pf, data-pf-w/pad/total. A new block in base.js (or assets/js/pages/profile.js): on pointermove over the visible .cv, map x to distance with pad_l and the chart width, pick the nearest sample, show a 1 px ink crosshair and a Mono-S label (reads html.km for the unit pair, both values prepared by core.U), and move a 7 px disc along the map's route. On non-ski maps that is the single path.mk-trk with getPointAtLength(fraction * getTotalLength()); a ski out-and-back overlay has two mk-trk paths, the dashed skin leg (trailhead to far point) and the solid ski leg (far point back), each offset 4 px (mapkit.py:746-749), so the script picks the leg by whether the distance is before or after the far point, or the first pass limits the map dot to non-ski overlays. Skip the dot when the map has several routes. Hide on pointerleave/Escape; touch-action: pan-y so scrolling still works on phones. Single-day reports first, the multi-day stitched profile later with per-day data. The table stays the accessible alternative; without JavaScript nothing changes. Add a Node harness like tests/maplist_js_harness.js.

**Files.** `tools/sitegen/pages/report.py`, `assets/js/base.js`, `assets/css/pages/report.css`, `tests/test_report_page.py`, `tests/profile_js_harness.js`.

**Effort.** M. Visitor value 3.3, author value 1, confidence high.

**Also covers.** report-07, benchmark-03 (merged into this finding).

**Risk.** Values must come from the GPX only (facts rule); the readout must not capture vertical scroll on phones; about 1.5 KB more HTML per report; the map dot is approximate where a route overlaps itself.

**Review note (condensed; the observation and proposal above are the revised text).** The profile readout is feasible and the strongest reading improvement in this set: report.elevation_table already builds a Track from the GPX at build time (report.py:172-198), meta.json carries pad_l/total_mi/w/h per chart variant (verified for profile-wide/col/phone), JavaScript is progressive enhancement with the table as the no-JS alternative, and samples from the GPX keep the facts rule. Observation reproduces: report.elevation_table (report.py:172-200) reads the GPX at build time and profile_section (209-232) emits the static chart plus the table; meta.json charts.profile-* carry y_lo, y_hi, pad_l, total_mi, h, vx, gx; mapkit's scrub readout sits at mapkit.py:2243-2267 and grep finds no 'scrub' in tools/render.py; assets/js/base.js has no chart/profile code; base.css:334 gives .cv > svg overflow: visible; core.chart_block is core.py:596-607; profile-wide.svg.html has one path.pf-line.

**Gates.** The phase is done when every line below holds and is recorded in the log entry:

1. tests/test_report_page.py rewritten: a photo-only fixture gets the hero (27 live pages change; list them in the log), a written fixture without photos and over core.STRUCTURED_MIN_CHARS takes the story order without a hero (count the live pages), one under the floor stays compact, a multi-day fixture has report.hero plus a thumb strip linking #day-N; DEVELOPING.md:457-497 describes four cases and records the reversal of plan 9.1 and the Phase 3 multi-day note.
2. Measured with the DEVELOPING.md:1428 method on one photo-only report and the Haute Route: phone LCP under 2.5 s and the image bytes recorded before and after.
3. report-03: the three variants (natural clamped, 3:2 cap, today's 2:1) built at 1280 px for the Matterhorn report and the PCT and shown side by side before the pick; the chosen frame pinned by a CSS or style test.
4. Strip and table: the Moving cell's sub-line shows ELAPSED and START and is visible at 390 px (strip-c--time rule); the elevation table has a Time column on the 156 timed tracks and none on the untimed one; the profile meta carries 'GPS MAX … AT hh:mm'; the stats footnote ends with a link to about/#abo-how-h that sitecheck verifies, and on phones the note shows under the strip instead of under the map caption (rep-note-ph gone from the build).
5. Captions and keys: 'Contours every 200 ft' | '61 m' per visible variant through core.U; the key row's Mile item reads 'Mile (1.6 km)' under KM; 'Trail (OSM)' and 'Road' key items appear only where the visible render's base layer draws them (fixture base files for both cases); 'VERTICAL SCALE ×N' in every chart head.
6. One label table drives section_nav, bottom_bar and multiday's bar; 'Trip details' and 'Route' no longer appear in any built page (grep); the 39 bare trips show a 'Track only' status tag on cards, rows and the title block; More like this heads read e.g. 'EASTERN SIERRA · BACKCOUNTRY SKI'; tests/test_related.py:418-427 retargeted.
7. maps-04: tests/profile_js_harness.js covers the readout; data-pf adds about 1.5 KB per report (measured); Chrome touch emulation shows the page still scrolls over the chart (touch-action: pan-y) and the readout hides on pointerleave and Escape; the map dot is left for later.
8. A beta row with url: renders <a rel="noopener"> and a non-http scheme fails validate; every multi-day day chart and the section featured chart carry a 'View as table' details with core.U units; the goal page says ≈ distance once and its one-cell strip is capped (strip--1).
9. Phone galleries: a 2.8:1 landscape and a 0.46 portrait fixture keep their --ar at 390 px in the cascade test; multi-day day chips show WRITE-UP / N PHOTOS and the Overview meta counts them.
10. Both Pythons with -W error and build.py --check pass; before/after captures at 390 and 1280 px of the Matterhorn report, back-to-clipless, hit-the-three-piece and the Haute Route are kept in .cache/plan2.

**Tests to add.** New: `tests/profile_js_harness.js`, `tests/test_profile_js.py`. Extended: `tests/test_a11y_static.py`, `tests/test_build_site.py`, `tests/test_cards_extra.py`, `tests/test_checks.py`, `tests/test_related.py`, `tests/test_report_page.py`, `tests/test_ticklist_page.py`, `tests/test_track_rules.py`. Plus the checks the gates name that no unit test covers: Phone LCP on one photo-only report and the Haute Route by the `docs/DEVELOPING.md:1428` method; Chrome touch emulation for the readout; `grep` of the built site for the retired labels.

**Screenshots to capture.** The Matterhorn report, `back-to-clipless`, `hit-the-three-piece` and the Haute Route at 390 and 1280 px before and after (before set: `phone-report-matterhorn.jpeg`, `desktop-report-matterhorn.jpeg`, `phone-bare-ride.jpeg`, `desktop-bare-ride.jpeg`, `phone-multiday-hauteroute.jpeg`, `desktop-multiday-hauteroute.jpeg`); report-03's three variants side by side at 1280 px for the Matterhorn report and the PCT page; the profile readout at 390 px under touch emulation.

**Author inputs needed.** Decisions 10 to 13; the pick from the report-03 side-by-side; the list of the 27 photo-only pages that gain a hero goes into the log for Eric to glance at.

### Phase 11. The PCT journal, the photo viewer and the full-screen map

**Goal.** Show the journal's 98 written-day photos as photos, tell a reader where an entry sits in the hike and let them come back to it, fix the dead July and August tabs, make the photo viewer behave on phones (Back closes it, swipes stick, the first photo is announced, the share sheet opens), and let the full-screen map open on the route with a scale and disclaimer in view, before any script runs.

**Prerequisites.** Phase 10 (core.photo_rows is the row component report-18 reuses; the label table). The session decides report-18's sizes cap from the measurement; no decision from Eric.

**Decisions this phase waits on.** None.

**Findings in this phase** (13, in working order): report-18, a11y-07, features-07, benchmark-10, features-08, visual-20, resilience-10, gap1-07, a11y-14, phone-06, gap1-02, maps-10, resilience-13.

#### report-18. Show journal photos as photos, not squares, on written days

**Observation.** Every journal day's photos are a contact sheet of 1:1 crops from the 320 px .th copies (series.py:321-338; series.css:181-189, .ser-ph img aspect-ratio 1 / 1 with object-fit: cover), 3 to 6 columns wide. The 32 written days hold 98 of the series' 103 day photos (the other 5 sit on three track-only days, 049, 050 and 059), so the journal shows nearly every photo cropped square and small until it is opened (desktop-series-pct.jpeg, Day 1 and Day 15 entries), while single-day reports lay the same kind of photo out in justified rows at up to 624 px (core.photo_rows, core.py:890).

**Evidence.** `tools/sitegen/pages/series.py:321-338`; `assets/css/pages/series.css:140-243`; `tools/sitegen/core.py:890-940`; `content/trips/pacific-crest-trail-2024/days/015.md:15-23`; `desktop-series-pct.jpeg`.

**Proposal.** For written days (series.py:98 written(); the thumbs call at series.py:413) use core.photo_rows(t, here, d['photos'], per_row=3, col=620, jmax=400, jmin=200, ns='d'+id) inside .ser-body, and in series.css add `.ser-body .jrows { max-width: 620px; --jmax: 400px; --jmin: 200px; }` so the block matches the write-up's 620 px measure (.ser-wu, series.css:178; .ser-body itself is about 930 px wide at ≥ 1200, base.css:123 and series.css:233) and the sizes core.photo_rows declares are the widths actually drawn (the clamp is base.css:460-461, which photo_rows's col/jmax/jmin do not change). A landscape then shows at the column width and portraits pair up, with the .sm copies via the existing sizes/srcset logic; keep the square .th sheet for the three track-only days with photos (they have no text to match); under 760 px base.css:469-475 already turns .jrow into the 2-column grid. The viewer groups a .jrows block's a.jph links as it does on reports (base.js:296 LINKS, :323-331 grouping). Update tests/test_series_page.py:900 and :911, which assert the .ser-body children as ['ser-wu', 'ser-phs', 'ser-wnav'] and ['ser-phs']. Re-measure the journal page's image bytes on the phone profile (the photo-days are hidden by default, so the first load changes little). Files: tools/sitegen/pages/series.py, assets/css/pages/series.css, tests/test_series_page.py. Risk: larger photo requests on the journal page when all days are shown (the .sm 800 px copies instead of 320 px squares); the page's HTML grows a little. tests/series_js_harness.js has no .ser-phs assertion.

**Files.** `tools/sitegen/pages/series.py`, `assets/css/pages/series.css`, `tests/test_series_page.py`.

**Effort.** M. Visitor value 3.3, author value 1.7, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md 12.1 (phone photo copy sizes)

**Risk.** Larger photo requests on the journal page when all days are shown (the .sm 800 px copies instead of 320 px squares); the page's HTML grows a little. The series JS harness (tests/series_js_harness.js) may assert the .ser-phs markup.

**Review note (condensed; the observation and proposal above are the revised text).** Not built and not decided against, but the observation miscounts and the proposal includes work the site already does. Feasible and worth doing: series.py:321-338 serves every journal photo as a square .th crop (series.css:200-205 aspect-ratio 1/1, object-fit: cover, 3-6 columns), core.photo_rows (core.py:890-940) already produces justified rows with the sizes logic, base.js:328 already groups a viewer by .jrows, and all 103 day photos carry w/h (checked content/trips/pacific-crest-trail-2024/days/*.md). Observation reproduces in the main: tools/sitegen/pages/series.py:321-338 (thumbs) emits one <ul class="ser-phs"> of a.ser-ph links whose <img> is the .th copy (built page: 25 such lists, src=…d001-01.th.webp); assets/css/pages/series.css:181-189 makes it a 3/4/5/6-column grid with .ser-ph img aspect-ratio 1 / 1 and object-fit: cover (:185); core.THUMB_EDGE = 320 (core.py:737); core.photo_rows (core.py:890) uses jmax=624; desktop-series-pct.jpeg shows Day 1 as four square placeholders in a six-column grid, Day 4 and Day 8 as six per row.

#### a11y-07. Stop disabling PCT month tabs under the write-ups filter

**Observation.** With 'Show days with write-ups only' on (the default), series.js sets aria-disabled="true" and tabindex="-1" on the month links whose month has no write-up (July, August) and series.css removes their pointer events, so neither a mouse nor a keyboard can open those months from the sticky bar, and a screen reader hears 'July, Days 71-101, link, dimmed' with no reason. Yet series.js already knows how to reveal a hidden month when its hash is followed (reveal() on hashchange turns the filter off and announces).

**Evidence.** `assets/js/pages/series.js:87-99`; `assets/css/pages/series.css:119-120`; `assets/js/pages/series.js:101-109, 126-130`; `tools/sitegen/pages/series.py:464-472`; `_site/trips/pacific-crest-trail-2024/index.html (nav.ser-mnav aria-label=Months)`.

**Proposal.** In series.js apply(): instead of aria-disabled/tabindex, add a class .is-empty and an .sr suffix ', no write-ups' to the month link; keep the lighter color via .ser-mnav a.is-empty (replacing series.css:119-120). A press then follows the hash, reveal() unchecks the box, announces 'Showing all 150 days' through #ser-live, and scrolls to the month. No test pins the month links' aria-disabled today (the Node harness covers only the pure helpers), so add a check that no .ser-mnav link carries aria-disabled or tabindex after apply(), and update the filter description at docs/DEVELOPING.md:660. Files: assets/js/pages/series.js, assets/css/pages/series.css, tests/test_series_js.py, tests/series_js_harness.js, docs/DEVELOPING.md.

**Files.** `assets/js/pages/series.js`, `assets/css/pages/series.css`, `tests/series_js_harness.js`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 2.3, author value 1, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.4 point 6 (the journal's default view)

**Risk.** Pressing an empty month now changes the reader mode for the session (series.js remembers only explicit choices, so keep that: a reveal is not stored). Known 15.4.6 (hash into a hidden day overrides the stored choice) stays as is.

**Review note (condensed; the observation and proposal above are the revised text).** Observation reproduces: series.js:87-99 apply() sets aria-disabled="true" and tabindex="-1" on month links with data-wu="0" while the box is checked; series.css:119-120 removes their pointer events; reveal() at 101-109 and the hashchange listener at 126-130 already turn the filter off and announce; series.py:464-472 writes nav.ser-mnav aria-label="Months"; in _site/trips/pacific-crest-trail-2024/index.html July (Days 71-101) and August (Days 102-132) are the two data-wu="0" months, data-default="wu" and data-total="150" match the default and the proposed announcement.

#### features-07. Journal rows show recorded distance so far

**Observation.** Each journal day row shows Distance, Gain and Moving for that day (series.py stats_dl, :341-350) and the strip gives the total, but no row says how far along the journey a day is. Every one of the 150 days has distance_km (the first three days sum to 65.5 km), and the page already explains gaps with 'DAYS N · NO RECORDING' rows, so a running sum of recorded distance is a fact the content states.

**Evidence.** `tools/sitegen/pages/series.py:341-350`; `tools/sitegen/pages/series.py:146-169 (strip)`; `content/trips/pacific-crest-trail-2024/days/001.md`; `content/trips/pacific-crest-trail-2024/days/*.md (150 stats: blocks)`.

**Proposal.** In series.py compute the cumulative recorded distance in day order and add a fourth cell 'So far' to stats_dl (series.py:341-350) through core.U in both units, with the column header text 'recorded so far' in .ser-cols so it never reads as trail mileage. CSS: a tenth column in --ser-c at both breakpoints (series.css:202, 228) and a fourth column in .ser-st (series.css:216, 230); on phones .ser-st already wraps with · separators (series.css:160-164), so the new cell follows the three with no new rule; keep the per-day stats first. No SVG line. Tests in tests/test_series_page.py: the running sum, both units, and that gap rows (gap_row, series.py:447-449) do not change it.

**Files.** `tools/sitegen/pages/series.py`, `assets/css/pages/series.css`, `tests/test_series_page.py`.

**Effort.** S. Visitor value 2.3, author value 1, confidence high.

**Risk.** The phone day cards are already dense (design map §8); the 1000 px grid header row has fixed columns; keep the per-day stats first.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible and factual: all 150 day files carry distance_km (grep today), stats_dl is the one place to add a cell (series.py:341-350), and the strip already calls the total 'Distance recorded' (series.py:151).

#### benchmark-10. Journal entries say their place in the hike

**Observation.** Postholer heads each entry 'Entry 18 of 18' with First / Previous / Next / Last links; bucktrack's headers carry running progress ('265 Miles/10% of the PCT Done!'). The PCT page's month heads give the month's days, write-ups and distance (series.py:452-462) and a written entry links only to the previous and next write-up (series.py:380-396); nothing says how far along the recording a day is or which write-up of the 32 the reader is on.

**Evidence.** https://www.postholer.com/user/Opus/1301; https://bucktrack.com/PCT.html; `tools/sitegen/pages/series.py:146-169`; `tools/sitegen/pages/series.py:380-396`; `tools/sitegen/pages/series.py:452-471`.

**Proposal.** series.py: written_nav adds one Mono-S item 'WRITE-UP 12 OF 32' (index in the written-days list it already builds); month_section meta and the month_index rows add 'N MI SO FAR' (cumulative recorded distance through the month's last day, core.U, computed by one prefix sum over t['days']). No First/Last links, no per-day sub-line. series.css for the two items; tests/test_series_page.py checks the counter and that the last month's figure equals the strip's total.

**Files.** `tools/sitegen/pages/series.py`, `assets/css/pages/series.css`, `tests/test_series_page.py`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Risk.** Cumulative figures must sum the day files in day order and skip gaps as the strip note already describes.

**Review note (condensed; the observation and proposal above are the revised text).** The gap is real: written_nav (tools/sitegen/pages/series.py:380-396) links only previous and next write-up, month_section's meta (452-462) and month_index rows (235-255) give per-month distance, and nothing says a cumulative mile. Cumulative recorded distance is a prefix sum of km_of over t['days'] in order, and the proposal rightly refuses an official trail length (not in content).

#### features-08. Local 'Continue reading' bookmark on the PCT journal

**Observation.** The plan listed a local-only Continue reading bookmark as a later convenience (plan:359); series.js remembers only the write-ups-only choice, in sessionStorage keyed by path (series.js:112-114). The journal has 32 written days over 150 recordings, and the only entry action is 'Read the first written entry' (series.py title actions), so a returning reader scrolls or searches for where they stopped.

**Evidence.** `docs/personal-website-improvement-plan.md:359`; `assets/js/pages/series.js:100-153`; `tools/sitegen/pages/series.py:395-423 (day_article, written_nav)`; `content/trips/pacific-crest-trail-2024/days/*.md (32 written, counted 2026-10-13)`; `.cache/plan2/shots/phone-series-pct.jpeg (390×42104 at 1x)`; `assets/js/pages/series.js:50-72 (month scrollspy), 112-114 (sessionStorage for the filter)`; `tools/sitegen/pages/series.py:497-506 (title actions)`; `_site/trips/pacific-crest-trail-2024/index.html (article ids day-N)`; `docs/personal-website-improvement-plan.md:359 (local-only bookmark listed for later)`.

**Proposal.** series.py emits, beside the title actions (series.py page(), :497-506), a hidden alink <a class="alink ser-continue" hidden> with an empty label. series.js: on a deliberate open (click on a month-nav link, a day anchor, a prev/next write-up link, or arrival with a #day-N hash) store 'ser-last:' + pathname = the day anchor in localStorage inside try/catch (the units pattern, base.js:7-27); on load, when the stored anchor exists on the page, fill the link's text with 'Continue reading: Day N · title' (text taken from that day's own heading) and unhide it; the link's click reveals the day if the filter hides it (existing reveal(), series.js:102). Nothing is shown without JavaScript or without a stored entry. Harness cases in tests/series_js_harness.js, whose own window object (:447-456) already stubs sessionStorage (:450) and needs a matching localStorage stub honouring the FAULT 'store' case; tests/page_standin.js serves only the trips and ticklist harnesses and is not touched. Files: tools/sitegen/pages/series.py, assets/js/pages/series.js, tests/series_js_harness.js.

**Files.** `tools/sitegen/pages/series.py`, `assets/js/pages/series.js`, `tests/series_js_harness.js`, `tests/page_standin.js`.

**Effort.** M. Visitor value 2.3, author value 1, confidence high.

**Also covers.** phone-17 (merged into this finding).

**Already known.** history map (b): bookmark deferred at plan:359; IMPLEMENTATION_REPORT.md decision 14

**Risk.** Per-device only; must not be described as a reading position synced anywhere; private-mode storage throws (wrap every access).

**Review note (condensed; the observation and proposal above are the revised text).** Feasible and listed for later at plan:359; the storage patterns exist (sessionStorage in try/catch at series.js:112-114, localStorage at base.js:10), reveal() exists for a hidden day (series.js:98-105), and the day's own heading text is on the page (series.py:415-420). Nothing shows without JavaScript or a stored entry, so the no-JS rule holds. Observation reproduces: plan:359 lists the local-only bookmark; series.js keeps only 'ser-only:' + pathname in sessionStorage (assets/js/pages/series.js:112-114), scrollspy at :50-72, reveal() at :102; series.py written_nav ends at :395, day_article :398-423, page() actions at :497-506 with 'Read the first written entry' at :503 (the other action, 'Browse all recordings', goes to #days, not an entry); 32 PCT days have write-up text; sips reports phone-series-pct.jpeg at 390×42104; base.js setUnits wraps localStorage in try/catch (:8-20); _site/trips/pacific-crest-trail-2024/index.html has 150 <article id="day-N"> anchors.

#### visual-20. PCT landing: one primary action among the three

**Observation.** The series title block offers three outline buttons of equal weight (Read the first written entry, Browse all recordings, Copy link), while every other page type marks one primary action in ink (Browse all trips on home, Download GPX on reports, Download all GPX on multi-day pages, Download planned GPX on goals). The rest of the landing (lead photo, strip, tall overview map beside the By month index with its distance bars, sticky month bar, table rows with contact sheets) is the strongest page on the site and should stay.

**Evidence.** `desktop-series-pct.jpeg (title actions)`; `desktop-report-matterhorn.jpeg (Download GPX in ink)`; `desktop-multiday-hauteroute.jpeg (Download all GPX in ink)`; `tools/sitegen/pages/series.py:503-505`.

**Proposal.** Give the first action `btn btn--ink` in series.py:503 (reading is the series' primary act, as downloading is a report's) and keep the other two outline; nothing else changes.

**Files.** `tools/sitegen/pages/series.py`, `tests/test_series_page.py`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Risk.** A series test may pin the button classes.

**Review note.** Kept as written by all three skeptics.

#### resilience-10. Photo viewer: Back closes it, a failed photo says so

**Observation.** The viewer is a `<dialog>` opened with `showModal()` (base.js:288-363). It pushes no history entry, so on a phone the system Back gesture leaves the page instead of closing the viewer. A photo that fails to load (`lbImg.src = a.getAttribute('href')`, base.js:311, no `error` listener) shows the broken-image glyph with no message and no way to the file; the bar holds previous, next and close only (core.py:1701-1710). Single-photo pages behave (both arrows hidden, 'PHOTO 1 / 1'), and the no-JS path opens the file.

**Evidence.** `assets/js/base.js:288-363`; `tools/sitegen/core.py:1701-1710`; `assets/css/base.css:718-730`.

**Proposal.** On open, try { history.pushState({lb: true}, '') } catch (e) {}; close the viewer on popstate when it is open; when closed by the button, Escape or a tap outside, call history.back() only if history.state && history.state.lb, with a flag so the popstate-driven close does not call back() again. Add an error listener on .lb-img that writes 'This photo could not be loaded' into .lb-cap and reveals a link to the href ('Open the file') only then; no fourth always-visible control, since the viewer already shows the full-size file. Cover open, close, Back and the error path in a Node harness case against tests/page_standin.js (its history model at lines 185-289 needs no change). Effort S; confirm the Back gesture on a real phone (known 15.5).

**Files.** `assets/js/base.js`, `tools/sitegen/core.py`, `assets/css/base.css`, `tests/page_standin.js`, `tests/maplist_js_harness.js`.

**Effort.** S. Visitor value 2.3, author value 1, confidence medium.

**Already known.** IMPLEMENTATION_REPORT.md 15.5 (a real phone never run)

**Risk.** A `popstate` from an unrelated hash change must not close a viewer that is not open; test on a real phone (15.5), since the Back-gesture behavior was reasoned, not observed.

**Review revision (applies on top of the text above).** Proposal (last sentence): Cover open/close/back and the error path in a Node harness case: tests/maplist_js_harness.js is the harness that loads base.js, and tests/page_standin.js already models history and popstate (its header at :14-17, the implementation from :185), so no new stand-in is needed. Files: assets/js/base.js, tools/sitegen/core.py, assets/css/base.css, tests/maplist_js_harness.js, tests/page_standin.js (only if the maplist harness is switched to it).

**Review note (condensed; the observation and proposal above are the revised text).** Not built, but one step of the proposal is already in place. The viewer (assets/js/base.js:290-363) has no `history.pushState`, no `popstate` listener and no `error` listener on `.lb-img` (grep of base.js), and the bar holds previous, next and close only (core.py:1704-1709). Verified: the viewer (assets/js/base.js:288-363) pushes no history entry and closes only via lb.close() on the button, Escape or a tap outside, so a phone Back gesture leaves the page; lbImg.src is set at base.js:311 with no error listener; the bar holds previous, next and close only (core.py:1704-1707). Reproduces: the viewer is base.js:290-363 (`dialog.lb`, `showModal()` at ~342); `grep -n 'pushState\|popstate\|history\|error' assets/js/base.js` returns nothing; `lbImg.src = a.getAttribute('href')` at ~:310 with no error listener; core.py:1701-1710 renders prev, next, close only; base.css:719-730 the viewer styles; single-photo pages hide both arrows (`lbPrev.hidden = at === 0; lbNext.hidden = at === group.length - 1`).

#### gap1-07. Make the photo viewer's swipe reliable on touch screens

**Observation.** the viewer reads a swipe from pointerdown/pointerup with a 40 px threshold (base.js:345-356). The dialog declares no `touch-action` (none anywhere in base.css; the .lb rules are base.css:719-730), nothing locks the document's scroll while the modal is open (`body.menu-open { overflow: hidden }` at base.css:230 serves the menu only), and `pointercancel` is not handled (no match in base.js). In touch browsers a one-finger drag the browser may treat as a page scroll ends in pointercancel rather than pointerup, so a swipe with vertical drift is dropped and the page behind can move. The viewer was checked for keyboard operation and focus return only (IMPLEMENTATION_REPORT.md:295, :301); the touch replay at :752 covered the history rules on Trips and the Tick list, not the viewer; nothing ran on a device (:853-855). Proposal as written (`.lb { touch-action: pinch-zoom; }`, `html:has(dialog.lb[open]) { overflow: hidden; }`, setPointerCapture on pointerdown next to base.js:346, reset `sx` on pointercancel, ignore non-primary pointers), with the :has() precedent cited as base.css:110 only.

**Evidence.** `assets/js/base.js:288-363`; `assets/css/base.css:718-730`; `docs/IMPLEMENTATION_REPORT.md:752`; `docs/IMPLEMENTATION_REPORT.md:853-855`; `assets/css/base.css:110`; `assets/css/base.css:195`; `assets/js/base.js:345-356`; `assets/css/base.css:719-730 (.lb rules, no touch-action)`; `tools/sitegen/core.py:1701-1710 (lightbox markup)`; `docs/IMPLEMENTATION_REPORT.md:855 (never run on a real phone)`.

**Proposal.** In base.css: `.lb { touch-action: pinch-zoom; }` (one-finger drags reach the script; pinch-to-zoom stays) and `html:has(dialog.lb[open]) { overflow: hidden; }` (the stylesheet already relies on :has(), base.css:110 and :195). In base.js at :346-356: ignore non-primary pointers (`if (!e.isPrimary) return;` on both handlers), add `lb.addEventListener('pointercancel', function () { sx = null; })`, and nothing else; do not call setPointerCapture (click retargeting would break the bar's buttons and trip the tap-outside close at :358, and the full-viewport dialog already keeps the pointer). Verify in Chrome's touch emulation on a report with three or more photos (swipe with vertical drift, pinch, tap prev/next/close, tap outside), and note the device check for the next iPad session in the log. Files: assets/js/base.js, assets/css/base.css. Effort S.

**Files.** `assets/js/base.js`, `assets/css/base.css`.

**Effort.** S. Visitor value 2.3, author value 1, confidence medium.

**Also covers.** phone-08 (merged into this finding).

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.5 (no real device)

**Risk.** Locking the document while the dialog is open changes nothing for keyboard users; the pointercancel case is inferred from the code and the standard pointer-event model, not observed on a device.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: base.js:346-356 reads pointerdown/pointerup only, no pointercancel and no isPrimary; base.css:719 declares no touch-action; showModal (base.js:335) does not lock the page behind. The touch-action, pointercancel, isPrimary and scroll-lock parts are small and standard. The code observation reproduces: the swipe is read from pointerdown/pointerup with a 40 px threshold at base.js:345-356; grep finds no touch-action, pointercancel, setPointerCapture or isPrimary in base.css or base.js; the .lb rules at base.css:719-730 set overflow hidden on the dialog only and the one document lock is `body.menu-open` for the menu (base.css:230); the lightbox markup is core.py:1701-1710.

#### a11y-14. Announce the first photo when the viewer opens

**Observation.** base.js announces 'Photo N of M. <alt>' through #lb-live only when the viewer moves (announce=true); on opening it calls show(i) without announce and focuses the Close button, so a screen-reader user hears 'Photo viewer, dialog, Close, button' and must navigate backwards to find the image and its description. The dialog also has no way to reach the full-size file (the link's href) from inside.

**Evidence.** `assets/js/base.js:298-318`; `assets/js/base.js:334-336`; `tools/sitegen/core.py:1704-1710`; `evaluate_script on the Matterhorn report: dialog open, counter "PHOTO 1 / 7", focused 'button.lb-close', after ArrowRight "PHOTO 2 / 7" with lb-live text, after Escape focus on 'a.jph.rep-hero-a'`; `.cache/plan2/qa/d-matterhorn-lightbox.png`; `tools/sitegen/core.py:1701-1710 (lightbox markup), assets/js/base.js:288-363 (viewer)`.

**Proposal.** On open, call show(index, true) (or set lbLive.textContent in the open path) after showModal() so the first photo's 'Photo 1 of N. <alt>' is announced, and give the dialog aria-describedby="lb-live". Keep Escape, focus return and the bar as they are; do not add an 'Open file' link. Check for double-speaking with the a11y-12 VoiceOver pass before committing, and update the comment at base.js:297. Add one assertion in tests/test_a11y_static.py for the describedby. Effort S.

**Files.** `assets/js/base.js`, `tools/sitegen/core.py`, `assets/css/base.css`, `tests/test_a11y_static.py`.

**Effort.** S. Visitor value 1.3, author value 1, confidence high.

**Also covers.** qa-11 (merged into this finding).

**Risk.** A second live announcement right after the dialog's own announcement may double-speak in some readers; test with VoiceOver (a11y-12). The extra bar link needs room at 320 px (counter + caption + four 44 px buttons).

**Review note (condensed; the observation and proposal above are the revised text).** Confirmed in assets/js/base.js: show(i) is called without announce on open and focus goes to Close (:325-328), and the comment at :297 says the first open deliberately does not announce, so the live region is empty while the dialog opens (core.py:1704-1710). Fixing the open announcement is S and low-risk if VoiceOver confirms it does not double-speak.

#### phone-06. Share a report through the phone's share sheet

**Observation.** On phones the only sharing control is 'Copy link to this page' at the end of a report (and the Copy link button in the PCT actions), which writes the address to the clipboard or shows a field to copy by hand. Phones have a native share sheet (navigator.share) that reaches messages, mail, AirDrop and other apps in one tap; the site never offers it.

**Evidence.** `assets/js/base.js:365-426 (copy link handler)`; `tools/sitegen/pages/report.py:70 (share_row)`; `assets/css/pages/report.css:158-179`; `phone-bare-ride.jpeg (crop: s2) ('Copy link to this page')`; `phone-series-pct.jpeg (crop: top) ('Copy link' button)`; `assets/css/pages/report.css:46`; `tools/sitegen/pages/report.py:70-73`; `assets/js/base.js:365-426`; `tools/sitegen/core.py:1340-1349`; `phone-bare-ride.jpeg`.

**Proposal.** In the base.js click handler, when navigator.share exists and navigator.canShare({url}) passes, call navigator.share({title: document.title, url}) inside the click and fall back to the clipboard path only when it rejects with anything but AbortError; at load, when navigator.share is present and (hover: none) matches, relabel the control 'Share this page' and swap the icon (add 'share' to tools/lib/icons.py). The markup keeps 'Copy link' for desktops and the control stays hidden without scripting. Apply to the per-entry copy links on the PCT page too.

**Files.** `assets/js/base.js`, `tools/lib/icons.py`, `tools/sitegen/core.py (copy_link)`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 2.3, author value 1.3, confidence high.

**Also covers.** report-13 (merged into this finding).

**Risk.** navigator.share needs https and a user gesture (both true on GitHub Pages). The receiving app draws the page's og tags, so the 62 reports without an og:image show a text card (report 12.4). Desktop browsers also expose navigator.share; the (hover: none) gate keeps the clipboard behavior there.

**Decision for Eric.** Whether the share sheet replaces Copy link on phones or sits beside it.

**Review note.** Kept as written by all three skeptics.

#### gap1-02. Show 'Open the full map' as a link beside the key row below 1440 px

**Observation.** The full-screen page trips/<slug>/map/ (report.py:683-705, 168 pages) shows the 1440×640 wide render at 1:1 in a pannable region that base.js scrolls to the route (base.css:370-379; base.js:431-458), but the only link to it is the 44 px button that core.map_block emits inside the phone variant alone (core.py:523-524) and base.css:351 hides from 560 px. So at 560-1199 a visitor sees the 718 render at 688-860 px, and at 1200-1439 the wide render scaled to the viewport (.bleed 100% up to 1440, base.css:124), with no way to the 1440 version that would give 1.7-2.1× the map pixels on a tablet and 1.0-1.2× on a small laptop. The button cannot simply be shown at larger widths: only the phone render reserves its top-left 60×60 corner for it (render.py:242), so an overlay at ≥ 560 would cover map content.

**Evidence.** `tools/sitegen/pages/report.py:683-705`; `tools/sitegen/core.py:521-526`; `assets/css/base.css:343-351`; `assets/css/base.css:370-379`; `assets/js/base.js:428-459`; `assets/css/base.css:123-124`; `tools/render.py:236-243`; `_site/trips/matterhorn-peak-west-couloir/map/index.html`; `tests/test_report_page.py:2507-2510`; `tests/test_report_page.py:2633`.

**Proposal.** Add one helper in core.py, e.g. `map_full_link(href)` returning `<a class="alink map-full" href="...">Open the full map<icon expand></a>` (icons.py:16 already has 'expand'), and emit it right after the key rows wherever fullscreen_href is passed: report.py:618-622, the goal map report.py:398-400, multiday.py:389-391 and series.py:296-307. In base.css beside :351: `.map-full { display: none; } @media (min-width: 560px) and (max-width: 1199.98px) { .map-full { display: inline-flex; } }`, so phones keep the in-map button, 560-1199 gets the text link (1.25-2.1x the map pixels on the fs page) and >= 1200, where the report already shows the wide render near 1:1, shows nothing. Keep core.map_caption untouched (core.py:717). Extend tests/test_report_page.py (the fs href assertion at :2633 and the track-less case at :2507-2510, which must still find no map/ link) and tests/test_series_page.py:1197; the sitecheck link pass covers the href. Files: tools/sitegen/core.py, tools/sitegen/pages/report.py, multiday.py, series.py, assets/css/base.css, tests/test_report_page.py, tests/test_series_page.py. Effort S.

**Files.** `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tools/sitegen/pages/series.py`, `tools/sitegen/core.py`, `assets/css/base.css`, `tests/test_report_page.py`, `tests/test_series_page.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Risk.** Adds one link per map section; the fs page stays index=False and noindex. New link text is UI copy, not a fact. The series fs page upsizes its 560×860 render to 840 px (base.css:378), the same as phones already get.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: the fs page exists for every map (report.py:683-705), its button is emitted in the phone variant only (core.py:523-524) and hidden from 560 (base.css:351), and the fs page shows the wide render at 1:1 (base.css:376), so a tablet at 560-1199 has no way to a map with 1.7-2.1x the pixels. Worth one link.

#### maps-10. Full-screen phone map keeps a scale, key and disclaimer in view

**Observation.** The full-screen page scrolls a 1440 px render inside a box; the scale bar sits in the render's corner and the key row and caption are below the box, so while panning there is no scale, no key and no "Not for navigation" on screen.

**Evidence.** `tools/sitegen/pages/report.py:683-705 (fullscreen_page)`; `assets/css/base.css:370-379 (.fs-map, .map width 1440)`; `assets/js/base.js:428-459 (initial scroll to the route)`; `tools/lib/mapkit.py:1441-1473 (scale bar placed in a corner of the render)`; `rendered/trips/matterhorn-peak-west-couloir/map-wide.svg.html (scale groups at x about 1280, y 616)`.

**Proposal.** In report.fullscreen_page only (multiday and series already call it: multiday.py:377, series.py:542): extract the <g class="u-mi">…</g> and <g class="u-km">…</g> scale groups from the fs render with a regex that excludes the <tspan class="u-mi"> unit labels, translate them by the first <rect>'s x/y so they start at 0, and put them in a 160×24 inline SVG as a second line of .fs-bar together with a Mono-S 'Not for navigation'; raise the 140 px in base.css:374 by that line's height. The key row stays in .fs-foot (there is no room for it beside the Back button on a 390 px screen). The MI|KM classes keep the toggle working. One test in tests/test_report_page.py that the bar holds both scale groups and the disclaimer. Effort S.

**Files.** `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tools/sitegen/pages/series.py`, `assets/css/base.css`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Risk.** None; the page is noindex and phone-only today.

**Review note (condensed; the observation and proposal above are the revised text).** Observation verified: the scale groups sit at x≈1280,y=616 in the 1440×640 overlay (rendered/trips/matterhorn-peak-west-couloir/map-wide.svg.html), the box is max-height calc(100svh - 140px) (assets/css/base.css:374) and the key row and 'Not for navigation' caption are in .fs-foot under it (tools/sitegen/pages/report.py:697-702, tools/sitegen/core.py:721).

#### resilience-13. Open the full-screen map on the route without JavaScript

**Observation.** The full-screen map page (`trips/<slug>/map/`, linked from the phone map's expand button, core.py:523-524) is a scrollable region (`div.fs-map`, `overflow:auto`, base.css:374) holding the 1440 px wide render (`.map` width 1440px, base.css:376; see _site/trips/back-to-clipless/map/index.html). base.js:428-459 scrolls it to the route's bounding box or start after the deferred bundle runs; nothing else sets the scroll position, so without JavaScript, or before the script runs on a slow phone, the map opens at its left edge (also noted in the pages map 3.11). Parsing the first `.mk-trk` path of the 157 rendered trip overlays, 141 have the route start right of x=390 and 98 have the whole route right of x=390, so on a 390 px phone the opening view shows no route at all for most trips. On back-to-clipless the route spans x 173..1267 of 1440 and starts at x=1267: a tail is visible at the left edge, the start is 877 px off-screen.

**Evidence.** `assets/js/base.js:428-459`; `tools/sitegen/core.py:523-524`; `_site/trips/back-to-clipless/map/index.html`; `rendered/trips/back-to-clipless/meta.json`.

**Proposal.** In `core.map_block` (core.py:484-527), when `'fs' in sizes`, find the route start in the inlined overlay (`core.frag`, core.py:450-462): the first `M x y` of the first `.mk-trk` path that is neither dashed (`stroke-dasharray`, the ski ascent, mapkit.py:971) nor faded (`stroke-opacity: .35`, the multi-day ghost, mapkit.py:979), preferring the dashed ascent's start on ski maps since it is the trip start (mapkit.py:969 writes the descent first). Emit inside the `.mv` (position:relative, base.css:330) an empty `<span id="route-start" style="position:absolute;left:X%;top:Y%">` with X = x / m['w'] * 100 and Y = y / m['h'] * 100 (the viewBox equals w x h). Return from map_block whether the span was emitted and append `#route-start` to the expand link's href at core.py:524 only then, since sitecheck.py:275-276 fails any cross-page fragment missing from the target page's ids and the PCT series fs page has no `.mk-trk` at all (its route is `.gl-trk`/`.mk-cat`); that covers all four callers (report.py:400, report.py:620, multiday.py:390, series.py:297) without touching them. In base.css give the span `scroll-margin-right: 50vw` and `scroll-margin-top: calc((100svh - 140px) / 2)` (the fragment scroll aligns block:start and inline:nearest, so these are what land the start mid-screen inside the `.fs-map`, whose max-height is `calc(100svh - 140px)`, base.css:374). base.js:428-459 then only refines to the bounding box and adds `is-pannable`, and should skip dashed and faded paths the same way. Do not take the render.py route: meta.json records each map's w/h and the start lat/lon but no pixel, and rewriting it would re-render all 168 committed meta.json files. Add to tests/test_report_page.py (which already covers trips/<slug>/map/ at lines 1300-1311 and 3197-3231): the span's left/top lie within 0..100% for a rendered single-day report, a ski report's span uses the ascent start, the link carries `#route-start` exactly when the span exists, and `build.py --check` passes on the series fs page. FILES: tools/sitegen/core.py, assets/css/base.css, assets/js/base.js, tests/test_report_page.py (tools/sitegen/pages/report.py only if fullscreen_page needs to pass anything through).

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/report.py`, `assets/css/base.css`, `assets/js/base.js`, `tests/test_report_page.py`.

**Effort.** M. Visitor value 1.7, author value 1, confidence medium.

**Risk.** Fragment scrolling of an overflow container is reliable in current browsers but older Safari centers on the element only vertically; the script path stays as the main route.

**Review note (condensed; the observation and proposal above are the revised text).** The observation holds and is worse than stated. base.js:428-459 is the only thing that moves the full-screen scroller; the expand link is `core.py:523-524` and is phone-only (base.css:351 hides `.mv-fs` from 560 px), so every visitor to `trips/<slug>/map/` is on a narrow screen. Observation reproduces: the expand link is built at core.py:523-524; `div.fs-map` is `overflow:auto` (base.css:374) around a 1440 px `.map` (base.css:376), confirmed in _site/trips/back-to-clipless/map/index.html (`<div class="fs-map" ...><div class="map map--fs"><div class="mv mv--fs" style="aspect-ratio:1440/640">`); base.js:428-459 sets scrollLeft/scrollTop after the deferred bundle runs and nothing else sets them, so without JS the view sits at scrollLeft 0 (also stated in the review's scratch file files/pages.md 3.11, not in the repository).

**Gates.** The phase is done when every line below holds and is recorded in the log entry:

1. Journal page: written days render core.photo_rows inside .ser-body with .ser-body .jrows capped at 620 px and --jmax/--jmin overrides, the three track-only days keep the square sheet, tests/test_series_page.py:900 and :911 updated; journal image bytes on the phone profile measured in the default write-ups-only view before and after and recorded in the log (today the .th copies total 3.2 MB and the .sm copies 9.4 MB for all 103 photos).
2. July and August are pressable in the default view: no .ser-mnav link carries aria-disabled or tabindex after apply(), a press reveals the month and #ser-live announces 'Showing all 150 days'; the Node test asserts it.
3. written_nav shows 'WRITE-UP 12 OF 32'; month heads and By-month rows show 'N MI SO FAR' and the last month's figure equals the strip's total (test); the day rows' 'So far' cell sums day files in order and gap rows do not change it.
4. Continue reading: tests/series_js_harness.js gains a localStorage stub and cases for store-on-open, show-on-return, hidden-when-absent and a private-mode throw; nothing renders without JavaScript or a stored entry.
5. Viewer: harness cases for pushState on open, popstate closing, Escape not over-popping, and the error state ('This photo could not be loaded' with the file link); Chrome touch emulation shows a swipe with vertical drift changes the photo, the page behind does not scroll, pinch still zooms, buttons still answer; opening announces 'Photo 1 of N. <alt>' and the dialog has aria-describedby="lb-live".
6. Share: under (hover: none) the control reads 'Share this page' and calls navigator.share inside the click with the clipboard path as fallback; the desktop copy-link path is unchanged (harness).
7. Full-screen map: a script over the 157 built report map/ pages finds the #route-start span inside the viewBox on every map with a .mk-trk and none on the series page (whose link stays bare); the ski ascent leg's start is used on ski maps; sitecheck passes with the #route-start fragments; the fs bar carries the u-mi/u-km scale groups and 'Not for navigation'; 'Open the full map' appears after the key rows at 560-1199 px only (cascade test) and the track-less fixture still has no map/ link.
8. PCT landing's first action is btn btn--ink; the Back gesture and the swipe are looked at on a real phone once and the result logged (15.5).
9. Both Pythons with -W error and build.py --check pass.

**Tests to add.** Extended: `tests/maplist_js_harness.js`, `tests/page_standin.js`, `tests/series_js_harness.js`, `tests/test_a11y_static.py`, `tests/test_report_page.py`, `tests/test_series_page.py`. Plus the checks the gates name that no unit test covers: Journal image bytes on the phone profile before and after; Chrome touch emulation for the swipe; the Node harnesses with a localStorage stub; a script over the 157 built report `map/` pages for `#route-start`; a real phone for Back and swipe.

**Screenshots to capture.** The PCT series at 390 and 1280 px before and after (before set: `phone-series-pct.jpeg`, `desktop-series-pct.jpeg`); the viewer open on a phone with the first photo announced in the accessibility tree; the Matterhorn full-screen map page at 667 by 375 px landing on `#route-start`.

**Author inputs needed.** None to decide. One look at the Back gesture and the swipe on a real phone, logged (closes part of 15.5).

### Phase 12. Maps on pages: landing on a trip, legends, touch, sticky columns

**Goal.** Let a report link to its own row on the region map and the PCT to the maps that draw its days, make cluster taps and legend toggles answer on map/ and region pages, give touch devices a select-then-open gesture on pins and lines, fold the 168-row list on phones, give phone region maps a full-screen page, and keep the stuck region map, ski panel, chapter rail and month bar inside common laptop and landscape-phone windows with one documented rule.

**Prerequisites.** None hard (gap4-04 can land before Phase 11). Eric looks at previews for gap1-01's 1005 px cap, qa-04's dimmed map and gap2-01's fit; decides whether 'See on the map' is also a fourth title action (recommended no) and whether region maps get full-screen pages (recommended yes).

**Decisions this phase waits on.**

- gap1-01's 1005 px map column at 1000-1199 and the strip hung from the column (after a preview at 1024 and 1180)
- qa-04: the season band dims the ski map (after a side-by-side)
- gap2-05: release the month bar with the one rule (recommended yes, as a consequence of gap2-07)
- gap4-03 as a fourth title action (decision 29; recommended no)
- qa-06 full-screen pages for region maps (decision 30; recommended yes)

**Findings in this phase** (24, in working order): gap1-01, gap4-01, gap4-02, gap4-03, gap4-04, ia-09, ia-10, ia-12, qa-02, maps-07, gap1-03, phone-03, qa-06, phone-04, gap2-01, gap2-02, gap2-03, gap2-04, gap2-05, gap2-06, gap2-07, qa-04, a11y-06, gap1-05.

#### gap1-01. Let the report map column use the 1000-1199 band instead of stopping at 860

**Observation.** At 560-1199 the map, key rows, caption and profile share a column of min(860px, 100% − 2·40px) hung from the left margin (report.css:23-26; --col-max base.css:18; --m is 40 px from 760, base.css:21). Computed from that cascade the map is 688 px at 768, 754 at 834, and 860 from 940 up, so at 1024 / 1100 / 1180 the wrap is 944 / 1020 / 1100 px and 84 / 160 / 240 px of paper sit to the map's right while the stats strip above it (a full .wrap, report.py:613) runs the whole width; the 1440-px wide render is inlined in the page but hidden there (the Matterhorn page holds mv--wide, mv--col and mv--phone, _site/trips/matterhorn-peak-west-couloir/index.html). The multi-day overview and stitched profile (rep-map mul-map, multiday.py:391; report.css:25; multiday.css:18) and the section featured map (section.css:110) carry the same cap, and the multi-day day maps stop at 718 px between 760 and 999 (multiday.css:241) while the overview above them runs to 860, so the two maps on one page have different right edges from 800 px up. The series intro needs no change: its 390×600 phone render sits at 1.03-1.24× between 1000 and 1199 (series.css:39-42) and its hillshade is drawn at 1.5× (render.py:415), and the narrow 760-849 column is a documented trade-off (series.css:37-38).

**Evidence.** `assets/css/pages/report.css:21-33`; `assets/css/base.css:14-22`; `assets/css/base.css:123-124`; `tools/sitegen/pages/report.py:613-622`; `assets/css/pages/multiday.css:231-267`; `tools/sitegen/pages/multiday.py:389-391`; `assets/css/pages/section.css:108-110`; `assets/css/pages/series.css:31-45`; `tools/render.py:236-243`; `tools/render.py:413-420`; `_site/trips/matterhorn-peak-west-couloir/index.html`.

**Proposal.** (1) No-regret, CSS only: in multiday.css:241 change `.mul-dmap-w, .mul-dp { max-width: 718px; }` to `max-width: var(--col-max)` so the day map and day profile share the overview's right edge at 760-999 (the col render scales at most 1.2x, exactly as the overview does under report.css:22). (2) Eric's choice after one side-by-side preview at 1024 and 1180 (today's 860 beside the alternative, per the preview rule): (a) hang the stats strip from the map column (`.rep-strip { width: min(var(--col-max), 100% - 2 * var(--m)); margin-inline: var(--m) auto; }` in the 560-1199 block of report.css; the multi-day strip shares the class), and (b) raise the cap for 1000-1199 to 1.4x of the 718 render (`--col-max: 1005px` under `@media (min-width: 1000px) and (max-width: 1199.98px)` in base.css; the 2x hillshade at render.py:239 stays sharp, only vector label size and stroke weight grow). Each of (a) and (b) can be taken or left on its own. If (b) is taken, rewrite the rule at report.css:21-22 and the breakpoint note at docs/DEVELOPING.md:69. The wide render is not an option below 1200 (0.69-0.83x). Files: assets/css/pages/multiday.css, assets/css/pages/report.css, assets/css/base.css, docs/DEVELOPING.md. Effort S.

**Files.** `assets/css/pages/report.css`, `assets/css/pages/multiday.css`, `assets/css/pages/section.css`, `assets/css/base.css`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Risk.** Upscaling the 718 render past 1.2× brushes the rule written at report.css:22 ('the 718 renders never scale past 1.2×'), which is why the preview comes first; the strip change narrows the 4-5 Data-XL cells to 172-215 px at 860, still wider than the longest value. No Python, preload or render change.

**Decision for Eric.** Raise the 1000-1199 map column to 1.4× of the col render (preview at 1024 and 1180 against today's 860), or keep 860 and wait for a tablet-sized render if maps-16 adds one.

**Review revision (applies on top of the text above).** Observation as written, with the series figure corrected to 1.03-1.26x between 1000 and 1199 (the .ser-intro wrap is 920-1119 wide, minus the 40 px gap, x5/11; series.css:39-43, series.py:305). Proposal as written with one scoping fix: `rep-strip` is emitted by report.py:613 and :390, multiday.py:786 and series.py:169, and the series map is not in the 860 column, so write the strip rule as `body:not(.p-series) .rep-strip { width: min(var(--col-max), 100% - 2 * var(--m)); margin-inline: var(--m) auto; }` in the 560-1199 block of report.css:23-26 (page CSS is bundled after base.css, build.py:81-86, so it overrides .wrap at equal specificity). The rest stands: multiday.css:241 to `max-width: var(--col-max)`; the 1000-1199 `--col-max: 1005px` option after a preview (718 x 1.4; the col hillshade is 1436 px at png_scale=2.0, render.py:239; the 11 px .mk-lbl/.mk-gps labels at mapkit.py:59-60 would show at about 15 px); section.css:110 and report.css:25 take the new value through the variable; update DEVELOPING.md:69 and the comment at report.css:21-22.

**Review note (condensed; the observation and proposal above are the revised text).** The cascade arithmetic is right (report.css:23-26, base.css:18/21, multiday.css:241, render.py:239) and the changes are CSS-only, so S is honest. But the strip change is not 'no-regret': today the 4-5 stat cells share the full .wrap by design (report.py:613) and narrowing them at 940-1199 is a visual choice, so it belongs in the preview with the cap, not before it. Observation reproduces: report.css:23-26 hangs .rep-map .bleed/.wrap at min(var(--col-max), 100% - 2*var(--m)) with --col-max 860 (base.css:18) and --m 40 from 760 (base.css:21), so the column is 688/754/860 at 768/834/940+ and the wrap (base.css:123) leaves 84/160/240 px at 1024/1100/1180; the strip is a full .wrap (report.py:613); the Matterhorn page holds mv--wide, mv--col, mv--phone and base.css:338-339 shows only mv--col at 560-1199; multiday.py:391 reuses rep-map, multiday.css:241 caps day maps at 718 between 760 and 999 (max-width none from 1000, :258) inside the same wrap left edge (multiday.py:742); section.css:110 uses the same variable; render.py:239 png_scale=2.0 and :415 png_scale=1.5; .mk-lbl/.mk-gps are 11 px (mapkit.py:59-60).

#### gap4-01. Give every region-list row a stable id, arc-row-<slug>

**Observation.** Rows in a region's 'In this region' list carry data-key but no id (archive.py:138-140 for reports, :201-203 for journal parts); the built Lake Tahoe page has 89 li.arc-row and none with an id. The map's pins have no id either (mapkit.py:1531), and any id inside the inlined SVG is rewritten per variant by core.frag (core.py:450-462: the page holds 234 ids of the form rg-lake-tahoe-region-lake-tahoe-desktop-desktop-…), so an SVG id could never be a stable address. archive.js already opens the tab that contains any hash target (archive.js:37-41) and scrolls to it after load (:64-68): an id on the row is all a URL needs to land on one trip.

**Evidence.** `tools/sitegen/pages/archive.py:127-141`; `tools/sitegen/pages/archive.py:182-204`; `tools/sitegen/pages/archive.py:278-303`; `tools/lib/mapkit.py:1531`; `tools/sitegen/core.py:433`; `tools/sitegen/core.py:450-462`; `assets/js/pages/archive.js:14-16`; `assets/js/pages/archive.js:37-41`; `assets/js/pages/archive.js:64-68`; `_site/regions/lake-tahoe/index.html (89 li.arc-row, 0 with id; 0 mk-pin with id; 234 rg-… namespaced ids)`; `tools/sitegen/sitecheck.py:242-294`; `tools/lib/content.py:28-32`; `tests/test_region_page.py:1482-1496`; `docs/DEVELOPING.md:1119-1123`.

**Proposal.** In tools/sitegen/pages/archive.py add id="arc-row-<slug>" to region_row (the trip slug; a trip sits in one region's rows, so the id is unique on map/ as on a region page) and give journal_row an id that carries the region as well as the part: id="arc-row-<region slug>-<content.slugify(part['key'])>" (region_panel already holds the region's slug; pass it to journal_row). The region is needed because a part's key is unique within one region only (content.py:472-473): today the Lake Tahoe and Eastern Sierra parts share the key pacific-crest-trail-2024:pacific-crest-trail (content/trips/pacific-crest-trail-2024/index.md:18, :21) and map/ lists both rows (archive.py:315 passes site= to every panel), so a region-less id would fail DUPLICATE IDS on map/ as the content stands. slugify (content.py:28-32) turns '<journal>:<part>' into '<journal>-<part>'; an untitled part's key is the journal's slug alone (content.py:461). other_places reuses region_row, so the rows of unmapped regions get ids too. Keep the prefix 'arc-row-' distinct from the list id 'arc-rows-<region>'. sitecheck.duplicate_ids (:294) guards collisions and sitecheck.links (:242-279) verifies every cross-page '#arc-row-…' link, so a report that links a row which is not on the page fails build.py --check instead of shipping. Tests: tests/test_region_page.py:1485-1496 builds its expected rows from region_row itself and keeps passing; :1648-1660 compares a region page's rows with its map/ panel's to the byte, which these ids keep equal (neither depends on the page); tests/test_region_days.py:874-875 finds journal rows by the prefix '<li class="arc-row arc-row--journal"', so put the id after data-key; add one assertion per row kind, add the id to tests/test_archive_page.py's fragment test (:258), and list it among the ids shared by map/ and region pages in docs/DEVELOPING.md:1119-1123. Without JavaScript a '#arc-row-…' URL lands on the row (every row is shown, archive.js:1-3); with JavaScript the right tab opens. The fold is gap4-02.

**Files.** `tools/sitegen/pages/archive.py`, `tests/test_region_page.py`, `tests/test_archive_page.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1.3, author value 1, confidence high.

**Risk.** A trip slug equal to a journal part's slugified key would duplicate an id; the DUPLICATE IDS check catches it. No existing URL or anchor moves.

**Review note (condensed; the observation and proposal above are the revised text).** Not built, verified: _site/regions/lake-tahoe/index.html has 89 li.arc-row and 0 with an id, 0 a.mk-pin with an id, and 234 id="rg-…" per-variant ids; archive.py:138 and :201 write data-key only; archive.js:37-41 and :64-68 already open the tab that holds a hash target and scroll to it. No doc or log entry decided against row anchors (grep of the plan, report, log, DEVELOPING.md). Feasible (stdlib, static, relative links, no-JS: every row shows without JS, archive.js:1-3) and S is honest, but the proposal as written breaks the build. Observation reproduces exactly: _site/regions/lake-tahoe/index.html has 89 li.arc-row, none with an id, 0 mk-pin with an id (mapkit.py:1531 writes none) and 234 ids prefixed rg-lake-tahoe-region-lake-tahoe-desktop-desktop-… from core.frag (core.py:450-462); archive.js:14-16 reads the hash, :37-41 opens the containing panel, :64-68 scrolls to the target.

#### gap4-02. Landing on a trip reuses the cluster-click sequence

**Observation.** archive.js reads the hash first (:14-16) and folds rows 9 and on behind 'Show all N' afterwards (:71-85; SHOW = 8 at archive.py:13; .arc-rows.arc-collapsed .arc-more is display:none, archive.css:77), so a link to a folded row would open the right tab and then hide the row: on the Lake Tahoe page 79 of 89 rows are folded. base.js's highlight() and markRows() (:137-160) run only on hover and focus, and the off handlers clear them (:162-172, :177-182); hashchange is handled only by the bottom-bar scrollspy (:256-260). So even with row ids nothing marks the trip among the Lake Tahoe map's 8 pins, 13 clusters and 2 journal lines (desktop) or 5, 11 and 2 (phone), and a journal part's line (a.mk-line, mapkit.py:636-648) is no better off.

**Evidence.** `assets/js/pages/archive.js:14-16`; `assets/js/pages/archive.js:45-49`; `assets/js/pages/archive.js:71-85`; `assets/css/pages/archive.css:41`; `assets/css/pages/archive.css:68-69`; `assets/css/pages/archive.css:77`; `assets/js/base.js:137-160`; `assets/js/base.js:162-172`; `assets/js/base.js:174-204`; `assets/js/base.js:256-260`; `assets/css/base.css:352-368`; `assets/css/base.css:42-44`; `tools/lib/mapkit.py:636-648`; `tools/lib/mapkit.py:984`; `tools/sitegen/pages/archive.py:13`; `_site/regions/lake-tahoe/index.html (desktop variant 8 pins, 13 clusters, 2 lines; phone 5, 11, 2; 79 arc-more rows)`; `tests/maplist_js_harness.js:1-30`; `tests/maplist_js_harness.js:264-389`; `tests/test_maplist_js.py:80-136`.

**Proposal.** Nothing beyond gap4-01's fold-opening lines in archive.js: before adding arc-collapsed (:71-85), if the hash target sits inside that ol and has .arc-more, open the list the way the button does (aria-expanded, 'Show fewer') instead of folding it; a hash target that is an .arc-row then goes through the same open-fold, scroll, focus sequence as the cluster marker's click (base.js:188-202), and the existing focusin handler marks the trip on the map while focus stays. No persistent pick state, no window global, no is-picked CSS, no Escape or hashchange handling. One sentence beside the map-list wiring in docs/DEVELOPING.md (:1092). For a trip whose start is in a cluster, .map.is-hl .mk-cluster.hl drops the marker to opacity .2 (base.css:364), so the trip shows by its track in route red; say so in the docs.

**Files.** `assets/js/pages/archive.js`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Risk.** For a trip whose start is in a cluster, .map.is-hl .mk-cluster.hl drops the marker to opacity .2 (base.css:363), so the trip is shown by its track in route red rather than by its marker: say so in the docs rather than redesign the cluster.

**Review note (condensed; the observation and proposal above are the revised text).** Not built, verified: archive.js reads the hash at :14-16 and then adds arc-collapsed to every list with a Show-all button regardless of the target (:71-85; archive.css:77 hides .arc-more); base.js's mouseleave/focusout handlers call highlight(map, null) and markRows(map, null) (:165-170, :178-179); the only hashchange listener is the bottom-bar scrollspy (:256-260); no 'is-picked' or 'siteMap' exists in any JS or CSS (grep of assets/). The observation is right (archive.js:14-16 reads the hash before :71-85 folds; base.js:162-172 and :177-182 clear the highlight on mouseleave/focusout; nothing handles a hash row). Observation reproduces: archive.js:14-16 reads the hash before :71-85 adds arc-collapsed (SHOW = 8 at archive.py:13; archive.css:77 hides .arc-more), and the built Lake Tahoe page has 79 arc-more rows of 89; split per SVG variant the map has exactly 8 pins, 13 clusters, 2 a.mk-line and 1 planned line on desktop and 5, 11, 2, 1 on phone; base.js:137-159 highlight/rowsFor/markRows run only from the hover and focus handlers at :160-170 and :172-182, whose off handlers call highlight(map, null); the only hashchange listener in base.js is the scrollspy at :256 (series.js, trips.js and ticklist.js listen too, but not on map/ or region pages); no 'pick' or 'is-picked' exists in assets/js or assets/css; base.js is bundled first (build.py:93-99); the harness stubs location.hash as '' (tests/maplist_js_harness.js:193) so it can play a landing.

#### gap4-03. 'See on the <Region> map' from every report, landing on its row

**Observation.** A report's only link to its place is the breadcrumb (report.py:116-118), which goes to regions/<slug>/ or map/#region-<slug> (core.py:73-85, :149-154), is hidden below 760 px (report.css:39) and lands at the top of a page whose map draws every pin of the region with nothing marking this trip (the Matterhorn page's crumb is ../../regions/eastern-sierra/). The Route section (#map, report.py:617-622) ends with the key rows and the caption 'As recorded on … · full track, not trimmed · North up' (report.py:158-168); the phone share row holds only 'Copy link to this page' (report.py:70-73, shown below 760 by report.css:160-162). The multi-day overview map (multiday.py:381-395), the full-screen map page ('Back to report' only, report.py:683-705) and the goal pager's region cell (report.py:428-437) have the same gap. ia-09, phone-07 and report-16 ask for a region link on phones; this goes one step further and lands on the trip.

**Evidence.** `tools/sitegen/pages/report.py:104-130`; `tools/sitegen/pages/report.py:70-73`; `tools/sitegen/pages/report.py:158-168`; `tools/sitegen/pages/report.py:428-437`; `tools/sitegen/pages/report.py:580-665`; `tools/sitegen/pages/report.py:683-705`; `tools/sitegen/pages/multiday.py:381-395`; `tools/sitegen/pages/multiday.py:778-799`; `tools/sitegen/core.py:73-85`; `tools/sitegen/core.py:149-154`; `tools/sitegen/core.py:712-723`; `assets/css/pages/report.css:37-51`; `assets/css/pages/report.css:160-162`; `assets/css/base.css:325-326`; `_site/trips/matterhorn-peak-west-couloir/index.html (crumb ../../regions/eastern-sierra/; rep-actions = View route, Download GPX, Copy link)`; `_site/trips/chamonix-zermatt-haute-route/index.html (crumb ../../regions/alps/, one rep-share row)`; `tests/test_report_page.py:4457-4494`; `tests/test_report_page.py:4558-4622`; `tools/sitegen/sitecheck.py:242-279`.

**Proposal.** core.py: add region_row_href(here, t): region_page_href(here, region) + '#arc-row-' + t['slug'] when the region has a page and t is one of core.listed_trips(site) (a completed or archived goal keeps its page but is in no region list, core.py:86-94, :118-121, DEVELOPING.md:950-957: for it return the plain region link); else, when the region is only in 'Not on a region map', region_map_href's address with the fragment '#arc-row-<slug>' (those rows are built from the same listed trips, archive.py:278-303, so the anchor exists whenever the region anchor does and the trip is listed); else None. report.py: append an .alink 'See on the <Region> map' with the arrow icon to the Route section's .wrap after the caption and the phone-only stats note (report.py:617-622), at every width (44 px row, base.css:325-326), and the same link to share_row beside 'Copy link' on phones; gate both on core.has_track(t) (core.py:1035) so a report the map cannot draw does not promise one. Use region_row_href in region_cell for the goal and planned pagers (the planned line carries the slug as its key, mapkit.py:1026, so gap4-02 picks it out), add the link to fullscreen_page's fs-foot, and to multiday.overview_map's caption row. Tests: tests/test_report_page.py:4457-4504 (the assertion at :4494-4504 that the crumb is the only thing a region page changes on a report must change), one test per placement including a completed goal that gets the region link without a fragment, and build.py --check proves every link lands (sitecheck.links, :242-279). Document the helper under Region pages in docs/DEVELOPING.md (:981-986 lists the region links today). The phone crumb being hidden is report.css:39-40; it is not an open point of docs/IMPLEMENTATION_REPORT.md §15.5, so cite the sibling findings ia-09, phone-07 and report-16 instead.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `assets/css/pages/report.css`, `tests/test_report_page.py`, `docs/DEVELOPING.md`.

**Effort.** M. Visitor value 3, author value 1, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md §15.5 (on a phone a report shows no link to its region page; .rep-title .crumbs hidden under 760 px)

**Risk.** A region spelled two ways or newer than the last render has no page: the helper falls back to the map/ anchor as the crumb does (DEVELOPING.md:946-957 describes those states), and a region not in rendered/site/meta.json gets no link, as today. The phone share row grows from one control to two. Depends on gap4-01 for the anchors.

**Decision for Eric.** Whether the link also becomes a fourth title action at >= 1000 px (the row holds View route · Download GPX · Copy link today) or stays in the Route section and the phone share row only.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: a report's only region link is the crumb (report.py:116-118), hidden under 760 px (report.css:39); the Matterhorn page's crumb is ../../regions/eastern-sierra/ and nothing else on the page links into regions/; the phone share row holds one control (report.py:70-73). Observation reproduces: report.py:116-118 adds the only region link, to regions/<slug>/ or map/#region-<slug> (core.py:73-85, :149-154); report.css:39 hides .rep-title .crumbs below 760; the built Matterhorn page's sole href into regions/ is ../../regions/eastern-sierra/ and its rep-actions are View route, Download GPX, Copy link; the Route section (report.py:617-622) holds the map, key rows, caption ('As recorded on Jan 17, 2026, full track, not trimmed, North up' on that page) and a phone-only stats note; share_row (report.py:70-73) is one copy-link control shown below 760 (report.css:160-162), one per page on the Haute Route; multiday.overview_map (:381-395), fullscreen_page (:683-705, 'Back to report' only) and region_cell (:428-437) have no trip-level link; the test at test_report_page.py:4494-4504 asserts the crumb href is the only difference a region page makes, so it must change.

#### gap4-04. The PCT page names the region maps that draw its days

**Observation.** The Lake Tahoe and Eastern Sierra maps draw the journal's days as lines that link to the day (a.mk-line → trips/pacific-crest-trail-2024/#day-67 on the built Lake Tahoe page) and list each part as a row (archive.py:182-204), but the journal page links to no region: its built HTML has no href into regions/ and its breadcrumb stops at Hiking. The content for the link is already parsed: t['region_days'] gives one part per line with region, title, key and days (content.py:363-378; key format at :476), and the region page's panel receives site= so the part rows are there (region.py:181, archive.py:207-256).

**Evidence.** `_site/trips/pacific-crest-trail-2024/index.html (no href into regions/; crumb Reports / Hiking)`; `_site/regions/lake-tahoe/index.html (a.mk-line → ../../trips/pacific-crest-trail-2024/#day-67 and #day-146)`; `tools/sitegen/pages/archive.py:182-204`; `tools/sitegen/pages/region.py:181`; `tools/lib/content.py:363-378`; `tools/lib/content.py:476`; `tools/sitegen/pages/series.py:396-420`; `tools/sitegen/pages/series.py:452-462`; `tools/sitegen/pages/series.py:123-137`; `tools/sitegen/pages/series.py:466-471`; `tools/sitegen/core.py:149-154`.

**Proposal.** series.py: under the overview map's caption in the intro row (series.py:294-308, inside .ser-intro-map after map_caption) add a Small/Mono-S line built from t['region_days'], one item per part, e.g. for the Lake Tahoe PCT part 'Days 67-76 · Lake Tahoe map (Pacific Crest Trail)' (the range from the existing label_range helper, series.py:123, over part['days']; the Lake Tahoe part is days 67-69, 72-74, 76 in content/trips/pacific-crest-trail-2024/index.md:18, so no fixed numbers in code or docs), linking to core.region_page_href(here, part['region']) + '#arc-row-<region slug>-' + content.slugify(part['key']), the region-qualified row id of gap4-01 (needed because the Lake Tahoe and Eastern Sierra parts share one key, index.md:18 and :21). Fallback: when the region has no page but a map panel, core.region_map_href with the same row fragment (map/'s panels list the parts too, archive.py:315); when it has no map, no item (the 'Not on a region map' block lists no journal, archive.py:286). Optional second step: in day_article (series.py:396-420) add the same link to the ser-n meta (:418) of the first day of each part only, not to every day. Tests in tests/test_series_page.py (one part, a titled and an untitled part whose key is the journal's slug alone per content.py:461, a region without a page, a region without a map); build.py --check verifies the anchors against the region pages and map/. Document in docs/DEVELOPING.md's series section.

**Files.** `tools/sitegen/pages/series.py`, `assets/css/pages/series.css`, `tests/test_series_page.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Already known.** docs/WEBSITE_IMPLEMENTATION_LOG.md journal-days entry (days south of the Eastern Sierra map are on no region map)

**Risk.** Days on no region map (the JMT days, WEBSITE_IMPLEMENTATION_LOG.md:1017-1018) get no item, which is the truth. The labels are UI copy built from content fields, not new text about the trip. Depends on gap4-01 for the part-row anchors.

**Review note (condensed; the observation and proposal above are the revised text).** Not built, verified: _site/trips/pacific-crest-trail-2024/index.html has 0 hrefs containing 'regions/' and its breadcrumb is Reports / Hiking only (the journal's own 'region: Pacific Crest Trail', content/trips/pacific-crest-trail-2024/index.md:9, has no map panel, so title_block adds no crumb; report §15.4.9 notes that region); series.py has no reference to region_days (grep), and intro() (series.py:294-308) holds the map block, key rows, caption, lede and month index. Observation reproduces: _site/trips/pacific-crest-trail-2024/index.html has zero hrefs into regions/ and its crumb is Reports / Hiking (title_block appends a region crumb only when the region is on map/, and 'Pacific Crest Trail' is not); the built Lake Tahoe page's a.mk-line links go to ../../trips/pacific-crest-trail-2024/#day-67 and #day-146; journal_row is archive.py:182-204; region.py:181 passes site=; content.py:363-378 documents region_days and :476 builds '<slug>:<key>' (:461 gives an untitled part the journal's slug).

#### ia-09. Link a report's region and year from the place line at every width

**Observation.** The report breadcrumb Reports / Activity / Region is hidden under 760 px, and the place line "MOUNT TALLAC, LAKE TAHOE · WITH …" and the date are plain text, so on a phone a report links to its activity (chip) but not to its region, and no report at any width links to its year. The planned-route pager has a region cell; the report pager (Newer/Older within the activity) has none.

**Evidence.** `assets/css/pages/report.css:37-39 (.rep-title .crumbs hidden below 760)`; `tools/sitegen/pages/report.py title_block() (crumbs; place via core.place_line)`; `tools/sitegen/core.py:393-406 (place_line: text items only)`; `tools/sitegen/pages/report.py pager() (activity neighbours only)`; `assets/css/pages/report.css:37-39 (.rep-title .crumbs hidden)`; `tools/sitegen/core.py:393-404 (place_line)`; `tools/sitegen/core.py:149 (region_page_href)`; `phone-report-matterhorn.jpeg (crop: top) ('SAWTOOTH RIDGE, EASTERN SIERRA · WITH ADAM', no link)`; `phone-multiday-hauteroute.jpeg (crop: top) (chips on two rows)`; `tools/sitegen/core.py:362 (trip_tags shape=True)`; `assets/css/pages/report.css:37-39`; `tools/sitegen/pages/report.py:104-130`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:962-964`; `phone-bare-ride.jpeg`; `phone-report-matterhorn.jpeg`.

**Proposal.** core.place_line(t, here, items=True): make the region part of the location item an <a> to core.region_page_href(here, region) or core.region_map_href(here, region) (the crumb's target, report.py:116), keeping the place text plain; the date item on phones (rep-pdate, report.py:122) and the chip-row date (report.py:129) link to map/#yr-YYYY (the static year group, ids yr-2021…yr-2026 on map/). Pass `here` into place_line at its three call sites: report.py:122 (title_block, shared by single-day, planned, multi-day and series pages) and section.py:165 and :312. Tests: tests/test_report_page.py (region link present on compact and story layouts). Files: tools/sitegen/core.py, tools/sitegen/pages/report.py, tools/sitegen/pages/section.py, tests/test_report_page.py.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tools/sitegen/pages/series.py`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 2.3, author value 1, confidence high.

**Also covers.** phone-07, report-16 (merged into this finding).

**Already known.** Listed under the publication entry of docs/WEBSITE_IMPLEMENTATION_LOG.md (2026-10-12) per the history map: on a phone a report shows no link to its region page

**Risk.** The .ml meta line clips its leading separators (base.css:99-110); a link inside an item must not change the item's box. Keep 44 px hit areas via the existing ::before technique.

**Review revision (applies on top of the text above).** Observation: unchanged (crumbs hidden under 760 px at report.css:37-39; place line and date are plain text via core.place_line; no report links its year; pager() has no region cell while planned_pager() does, report.py:427 region_cell). Proposal: core.place_line(t, items=True, here=None): when here is given, make the region part of the location item an <a> to core.region_page_href(here, region) or core.region_map_href (the crumb's target), keeping the place text plain; the date item on phones (rep-pdate) and the chip-row date in report.title_block link to map/#yr-YYYY (the static year group). Callers to update: report.py:122 title_block (shared by single-day, planned, multi-day and series pages) and section.py:165 and :312; multiday.py and series.py need no change. Tests: tests/test_report_page.py (region link present on compact and story layouts, on a multi-day page through title_block) and the section-page test for the featured row. Files: tools/sitegen/core.py, tools/sitegen/pages/report.py, tools/sitegen/pages/section.py, tests/test_report_page.py. Known: docs/WEBSITE_IMPLEMENTATION_LOG.md:962 (publication entry) and docs/IMPLEMENTATION_REPORT.md 15.5.

**Review note (condensed; the observation and proposal above are the revised text).** Not built; the proposal's caller list is wrong. The region link on phones is a real, known gap (assets/css/pages/report.css:38 hides .rep-title .crumbs below 760; docs/WEBSITE_IMPLEMENTATION_LOG.md:964 lists it) and the fix is small. Observation reproduces: assets/css/pages/report.css:37-39 hides .rep-title .crumbs below 760 px; report.py:104-130 title_block builds the crumbs and a plain place line via core.place_line (core.py:393-404, text items only); the three built report pages checked (matterhorn-peak-west-couloir, mount-tallac-2026-02-15, back-to-clipless) have zero links to #yr-/#y- anchors; report.py:292-307 pager has Newer/Older only while planned_pager (:310-320) adds region_cell (:427); the crop phone-report-matterhorn-top.jpeg shows the plain 'SAWTOOTH RIDGE, EASTERN SIERRA · WITH ADAM' line; docs/WEBSITE_IMPLEMENTATION_LOG.md:963-964 records the known gap; map/ has id="yr-2021"…"yr-2026".

#### ia-10. Region pages: per-activity entry points with a shareable address

**Observation.** regions/lake-tahoe/ heads with '86 REPORTS · INCL. 8 MULTI-DAY · + 1 PLANNED ROUTE · 2022-2026 · TAHOMA · …' and no activity breakdown; the activity chips under All reports are JS-only and write nothing to the address (archive.js:48 stores only the region tab hash). A per-activity view of a region is shareable today only through the explorer (trips/?region=lake-tahoe&activity=ski, JS-only), which the region page links to without an activity.

**Evidence.** `_site/regions/lake-tahoe/index.html (reg-stats line; reg-find and reg-more links)`; `tools/sitegen/pages/region.py head(), featured(), page() (find link)`; `assets/js/pages/archive.js:14,48 (hash only for tabs; the filter keeps no state)`; `tools/sitegen/pages/archive.py archive_section() (chips hidden until JS)`; `.cache/plan2/qa/d-map-allreports-ski.png (head meta unchanged, year counts 22/20/4/4/1)`; `evaluate_script on map/: live "Showing 51 backcountry ski reports", url unchanged; sameDocHashChange → selected still "Oregon, 3 reports"`; `assets/js/pages/archive.js:1-70 (hash read once at load, tabs use replaceState)`.

**Proposal.** region.py head(): after the counts and years, a Mono-S line of activity items with counts (disc + word + count, from core.NAV and the region's `pub`; items with zero reports omitted), each linking to the explorer's existing address `trips/?region=<slug>&activity=<key>` (the keys trips.js:13 already reads). Without JS the explorer shows its full list by year (trips.js:6), the same fallback the page's two existing explorer links accept; apply the page's `.reg-x` rule to these links only if hiding a filter promise without JS is preferred. No change to archive.js or the harness. Tests: tests/test_region_page.py for the line and its hrefs. Effort S.

**Files.** `assets/js/pages/archive.js`, `tools/sitegen/pages/region.py`, `tools/sitegen/pages/archive.py`, `tests/maplist_js_harness.js`, `tests/test_region_page.py`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Also covers.** qa-03 (merged into this finding).

**Risk.** The archive section is shared by map/ and the region pages; the query key must not collide with the `#region-<slug>` tab logic. The region page's reg-x links are hidden without JS; the new head links are static, so they must not promise a filter without JS (land on #all-reports).

**Review note (condensed; the observation and proposal above are the revised text).** Not built on the region page: region.py head() renders counts + years + places only (no activity items), and archive.js writes nothing but the tab hash (replaceState at :48) while apply() keeps filter state in the DOM only. Part (1) duplicates an address that already exists: trips.js keeps `activity` and `region` in the explorer's URL (assets/js/pages/trips.js:13), so trips/?region=lake-tahoe&activity=ski is already shareable, and the region page links to the explorer twice (tools/sitegen/pages/region.py:102 and :177).

#### ia-12. Section pages: a region band and linked region names

**Observation.** The Ski page's head names its regions as plain caps ("51 REPORTS · INCL. 5 MULTI-DAY · LAKE TAHOE · EASTERN SIERRA · ALPS · TETONS"; the Mountain Biking head likewise: "61 REPORTS · SANTA CRUZ · LAKE TAHOE · BAY AREA · 2 MORE") and the ski panel's region labels are plain `<p class="t-label sec-rp-l">` text; the Mountain Biking page (61 rides) and Hiking page have only a year band (one data-filter-nav 'Filter by year'; segments #year-2026 …), and list rows (core.trip_row, core.py:1169-1181) name the place, showing the region only for a trip with no place. A visitor on Mountain Biking cannot narrow to Santa Cruz (45 of the site's reports) without leaving for the explorer or a region page.

**Evidence.** `_site/ski/index.html (sec-stats line; '<p class="t-label sec-rp-l">Lake Tahoe</p>')`; `_site/mountain-biking/index.html (one data-filter-nav band; segments #year-2026 …)`; `tools/sitegen/pages/section.py header(), band(), ski_panel()`; `assets/js/pages/section.js:8-87 (apply() toggles every [data-f] item in scope from one band)`; `tools/sitegen/core.py:1169-1180 (trip_row names the place only)`.

**Proposal.** section.py: in totals_line (section.py:75-80, via areas()/area_names()) each item that is a region links to core.region_page_href or core.region_map_href (climbing's items are places and stay plain; pass (html, cls) tuples through core.meta_items); ski_panel(): the panel label at section.py:375 links the same way. No second band, no section.js change. On Mountain Biking that gives the Santa Cruz path (regions/santa-cruz/, which has the activity chips). Tests: the section-page cases in tests/test_build_site.py and tests/test_a11y_static.py (crumb and link rules). Effort S.

**Files.** `tools/sitegen/pages/section.py`, `tests/test_build_site.py`, `tests/test_a11y_static.py`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Risk.** Two bands on phones add a second 42 px row above the featured block; the Other page already has a sub-type band and should keep one band only. Deep links: a region segment's href leaves the page without JS, which must be stated in the band's aria-label.

**Review revision (applies on top of the text above).** Proposal: unchanged in substance ((1) header()/ski_panel() region links; (2) a second band via band() with region segments linking to the region page or map/#region-<slug>, rows get `data-f="<year-or-season> <region-slug>"`; (3) section.js keeps one active key per band and sets is-off when any band's key is neither all nor in the item's keys; CSS stacks a second .sec-band). Tests: the section-page tests live in tests/test_build_site.py (SectionDescriptionTests and the featured-block cases) and tests/test_a11y_static.py; add a Node harness for section.js only if one is created (none exists today). FILES: tools/sitegen/pages/section.py, assets/js/pages/section.js, assets/css/pages/section.css, tests/test_build_site.py, tests/test_a11y_static.py.

**Review note (condensed; the observation and proposal above are the revised text).** Mostly not built: section.py areas() emits region names as core.nb(esc(x).upper()) with no link, ski_panel() labels are plain <p class="t-label sec-rp-l"> (verified in _site/ski/index.html), the only bands are Filter by season (Ski), Filter by year (Hiking, Mountain Biking) and Filter by type (Other); Climbing has none; the Ski region tabs switch the map panel only and the list follows the hover (section.js tablist/follow), they never filter the rows. Part (2) helps one page. Mostly reproduced: _site/ski/index.html sec-stats is plain caps and the panel labels are <p class="t-label sec-rp-l">; mountain-biking/ and hiking/ each have one data-filter-nav band ('Filter by year', segments #year-2026 …), other/ has 'Filter by type'; section.js:8-87 applies one key per band to every [data-f] in scope and splits keys on spaces (line 45). Two details are wrong.

#### qa-02. Make a cluster click select its reports, not just the first row

**Observation.** On map/ (Lake Tahoe) the "22" cluster near the Tallac trailheads stands for 22 trips. Clicking it scrolls to the first matching row ("Tallac", Sep 24) and focuses it; the `is-map-hl` marks on the other 21 rows exist only while the pointer is over the cluster, 79 of the 86 rows sit behind "Show all 86", and the cluster is an aria-hidden `<g>` with no keyboard access. A touch or keyboard visitor never learns which 22 reports the number means; a pointer visitor sees one highlighted row.

**Evidence.** `.cache/plan2/qa/d-map-cluster-click.png`; `evaluate_script on https://esichak.github.io/personal-website/map/ : cluster data-keys list of 22 slugs, scrollAfter 108, hlRows 0 after the click`; `assets/js/base.js:176-204 (cluster click handler: find first row, open fold, scrollIntoView, focus)`; `assets/js/base.js:183-203 (cluster click: first matching row only)`; `rendered/site/region-lake-tahoe-desktop.svg.html (<g class="mk-cluster" data-keys="..."> with 22 keys and a joined <title>)`; `tools/lib/mapkit.py:1536-1541 (cluster markup, aria-hidden)`; `docs/IMPLEMENTATION_REPORT.md section 15.4.7 (cluster count includes a planned route)`.

**Proposal.** in base.js, on click and on Enter/Space, give each `.mk-cluster` `role="button"`, `tabindex="0"`, `aria-label="N reports start here"` AND remove its `aria-hidden` attribute at runtime (mapkit.py:1538 writes it); keep `is-map-hl` on the cluster's rows, open the fold, add a new `.is-off` class (archive.css) to the panel's other rows, write "22 reports start here · Show all" into the panel's count line (give the `count_line(ts, 'ml--end')` span built at archive.py:43 and placed at archive.py:240-247 an id), and clear the selection on Escape, on 'Show all' (archive.js), or on a second press of the same cluster. Region pages share region_panel(page=True) so they get it too. Extend the cluster cases in tests/maplist_js_harness.js (lines 12-13, 224-225) with the selection and clear cases. Files unchanged.

**Files.** `assets/js/base.js`, `assets/js/pages/archive.js`, `assets/css/pages/archive.css`, `tools/sitegen/pages/archive.py`, `tests/maplist_js_harness.js`.

**Effort.** M. Visitor value 3, author value 1, confidence high.

**Also covers.** maps-08 (merged into this finding).

**Risk.** The cluster markup comes from rendered/site (mapkit.py), so add the role, name and tabindex in base.js at runtime rather than in the renderer, or a `render.py --site --force` becomes necessary. The base.js comment about dead tab stops applies to unnamed `<g>`s only; with a role and a name they are meaningful stops.

**Review note (condensed; the observation and proposal above are the revised text).** Not built, observation verified: assets/js/base.js:188-203 handles a cluster click by finding the first matching row, opening the fold, scrolling and focusing it; tools/lib/mapkit.py:1538 emits `<g class="mk-cluster" aria-hidden="true" data-keys=...>`; rendered/site/region-lake-tahoe-desktop.svg.html holds a 22-key cluster. Verified: base.js:183-203 scrolls to the first matching row only, and the cluster markup is an aria-hidden <g> (tools/lib/mapkit.py:1536). The sticky selection is feasible at runtime and valuable on map/, whose purpose is exactly 'which reports start here'. Observation reproduces: assets/js/base.js:174-204 handles a cluster click by finding the first matching row, opening the fold, scrollIntoView and focus; `is-map-hl` rows are set only in the mouseenter/mouseleave handlers (base.js:178-181); tools/lib/mapkit.py:1538 writes `<g class="mk-cluster" aria-hidden="true" data-keys=...><title>…</title>`; rendered/site/region-lake-tahoe-desktop.svg.html has 13 clusters, one with 22 keys; the live map/ has 42 clusters, all aria-hidden, and 'Show all 86' (SHOW = 8 at archive.py:13); .cache/plan2/qa/d-map-cluster-click.png shows only the first 'Tallac · Sep 24' row outlined.

#### maps-07. Legend as an activity filter on region maps

**Observation.** The Map page and region pages draw a region's tracks in five activity colors beside a static legend; the only activity filter is on the All-reports table further down. Every drawn track and pin already carries data-key="<slug>", list rows carry data-act, base.js highlights by key, and archive.py already rewrites the map fragment at build time (share_casings).

**Evidence.** `tools/sitegen/pages/archive.py:107-124 (legend), tools/sitegen/pages/archive.py:207-256 (region_panel), tools/sitegen/pages/archive.py:58-78 (share_casings)`; `rendered/site/region-lake-tahoe-desktop.svg.html (<g class="mk-cat" data-key=...>, <a class="mk-pin" ... data-key=...>, clusters with data-keys)`; `assets/js/pages/archive.js:88-162 (activity filter for the table only), assets/js/base.js:136-205 (highlight by key)`; `.cache/plan2/shots/desktop-map.jpeg (first panel at 150-1550 px: legend beside the map)`.

**Proposal.** At build, archive.region_panel injects data-act="<activity>" onto every g.mk-cat[data-key], a.mk-pin[data-key] and journal a.mk-line (slug to activity from site['by_slug']; clusters get data-acts="ski hike"). Under JavaScript the legend items become 44 px toggle buttons (aria-pressed); archive.js sets data-filter on the .map and hides non-matching rows; CSS dims .mk-cat/.mk-pin that do not match to opacity .15 and clusters whose acts all miss; the panel's live region announces "N of M reports". Without JavaScript the legend stays a list. Reuse on map/, regions/<slug>/ and, if wanted, the two home region blocks (home.py:323).

**Files.** `tools/sitegen/pages/archive.py`, `assets/js/pages/archive.js`, `assets/css/pages/archive.css`, `assets/css/base.css`, `tests/maplist_js_harness.js`, `tests/test_a11y_static.py`.

**Effort.** M. Visitor value 3, author value 1, confidence high.

**Risk.** Keep the forced-colors rule for the legend discs (archive.css, DEVELOPING.md accessibility notes) and the 44 px target rule; the cluster count text is unchanged.

**Review note.** Kept as written by all three skeptics.

#### gap1-03. On touch screens, a first tap on a pin or line selects it; a second tap opens it

**Observation.** Everything that names or highlights a map marker runs on mouseenter/mouseleave/focusin/focusout (base.js:174-187): the pin's `<title>` tooltip and aria-label (mapkit.py:1531) and the journal line's (mapkit.py:644-647) only show to a pointer that hovers. A pin and a journal line are `<a>` elements, so on an iPad a tap navigates at once and the visitor never learns which trip a pin is; the cluster marker is the one map element whose click already answers a tap (base.js:188-202). `(pointer: coarse)` appears nowhere in CSS or JS and the only touch rule is section.css:240; the log records 'there is no hover on touch' (WEBSITE_IMPLEMENTATION_LOG.md:1076). This holds at every width on a touch device, including the desktop layout a 13-inch iPad gets in landscape (≥ 1200 CSS px), and the journal line's invisible hit stroke is 14 px (LINE_HIT, mapkit.py:633), 12 px at the 0.87× panel scale of 1000-1199 (archive.css:44-47).

**Evidence.** `assets/js/base.js:136-204`; `tools/lib/mapkit.py:633-648`; `tools/lib/mapkit.py:1514`; `tools/lib/mapkit.py:1531-1539`; `assets/css/pages/section.css:240`; `assets/css/base.css:352-368`; `assets/css/pages/archive.css:39-49`; `tools/sitegen/pages/home.py:323-330`; `docs/DEVELOPING.md:1182-1187`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:1076`; `tests/maplist_js_harness.js:1-30`.

**Proposal.** In base.js, inside the pin/line loop at :174, when `window.matchMedia && matchMedia('(hover: none)').matches` and `rowsFor(map).length` is non-zero, add a click listener on `.mk-pin[data-key]` and `.mk-line[data-key]`: if the element is not the current selection, `preventDefault()`, call highlight(map, keys) and markRows(map, keys), mark it `is-sel` (clearing any other), and reuse the cluster-click body at :190-202 (open a folded list, `row.scrollIntoView({block: 'center'})`, focus the row's link) so the marked row names the trip. A second tap on the selected marker navigates; a tap on the map paper clears the selection. Maps without rows (home.py:323-330) are left as they are. In base.css under `@media (pointer: coarse)`: `.mk-line .mk-hit { stroke-width: 28px !important; }` (pins lie above lines and still answer first, DEVELOPING.md:1184). Tests: give tests/page_standin.js a `matchMedia` stub (none today) and add a coarse-pointer run to tests/maplist_js_harness.js (tap, tap again, tap elsewhere, a map without rows). No Python change. Do not touch the cluster-click rule or the legend. Files: assets/js/base.js, assets/css/base.css, tests/page_standin.js, tests/maplist_js_harness.js. Effort M (the harness stub is most of it).

**Files.** `assets/js/base.js`, `assets/css/base.css`, `tools/sitegen/pages/archive.py`, `tools/sitegen/pages/home.py`, `tools/sitegen/pages/section.py`, `tests/maplist_js_harness.js`, `tests/test_region_page.py`, `tests/test_archive_page.py`, `tests/test_home.py`.

**Effort.** M. Visitor value 2.3, author value 1, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.5 (no real phone or tablet run); log 2026-10-12 'no hover on touch'

**Risk.** Gate on (hover: none), never on width, so mouse and keyboard paths and an iPad with a trackpad keep today's behavior; the pin stays a real link without JS. 'Open →' is new UI copy. Do not touch the cluster-click rule (maps-08/qa-02) or the legend (maps-07).

**Review revision (applies on top of the text above).** Proposal as written, except the tests: tests/maplist_js_harness.js does not load tests/page_standin.js (that stand-in serves only tests/trips_js_harness.js and tests/ticklist_js_harness.js); it builds its own vm sandbox at lines 192-200 (`sandbox.window = sandbox`, no matchMedia). Add the `matchMedia` stub to that sandbox (returning {matches: false} by default and {matches: true} for '(hover: none)' in a coarse-pointer run), add the tap / tap again / tap elsewhere run there, and drop tests/page_standin.js from the files. Hold the `.map-sel` hook in tests/test_region_page.py, tests/test_archive_page.py and tests/test_home.py as written.

**Review note (condensed; the observation and proposal above are the revised text).** The gap is real and affects phones as well as tablets: pins and journal lines are plain links (mapkit.py:1531, :644) wired to mouseenter/focusin only (base.js:174-187), and nothing in CSS or JS tests for a coarse pointer (grep: only section.css:240; no matchMedia in tests/). Select-then-open is a known touch pattern and the cluster click (base.js:188-202) already does the second half. Observation reproduces: base.js:172-187 wires .mk-pin[data-key] and .mk-line[data-key] on mouseenter/mouseleave/focusin/focusout only, and the cluster click at :188-202 is the only tap-answering map element; pins (mapkit.py:1531-1532) and lines (mapkit.py:644-647) are <a> with <title> and aria-label; LINE_HIT=14 at :633 and the 1000-1199 8+4 grid at archive.css:44-47 (14 x 0.87 = 12); grep finds no (pointer: coarse) or matchMedia in assets/css or base.js, the only touch rule is section.css:240, and docs/WEBSITE_IMPLEMENTATION_LOG.md:1076 says 'there is no hover on touch'; home.py:323 builds the home maps with map_block(None, ...) and no list; archive.py:226 and section.py:381 are the map_block calls named.

#### phone-03. Map page on phones: collapse the All-reports years

**Observation.** The map page is about 17,000 CSS px tall on a phone (the capture is 1170x51048 at 3x, roughly 20 screens). The Lake Tahoe panel and the 'Not on a region map' list take the first ~3.8 screens; the rest is 'All reports': 168 rows at 72 px minimum (base.css:564; 80 px from 560, archive.css:183) in six year groups plus a Planned group. The year index above it only jumps, it cannot shorten the page, and the same section is reused on every region page (region.py:183).

**Evidence.** `.cache/plan2/shots/phone-map.jpeg (1170×51048)`; `phone-map.jpeg (crop: s1) (compact rows)`; `_site/map/index.html (168 a.rtab-r rows, ids yr-2026…yr-2021)`; `tools/sitegen/pages/archive.py:349-363`; `assets/css/pages/archive.css:166-178`; `assets/css/base.css:621-650`.

**Proposal.** In archive_section(), wrap each year group in <details class="arc-yr" id="yr-YYYY" open> with the <summary> holding the .arc-yr-h row (year label and count, marker removed); give the h3 its own id (e.g. yr-YYYY-h) so the <ol>'s aria-labelledby (archive.py:356) still names it; archive.js closes every group but the first below 760 px and reopens a group when a year link, the activity filter (archive.js:88-145, which rewrites .arc-yr-n and the index counts) or a hash inside it needs it. Keep the year ids on the details element so index links and sitecheck's anchor check land on a visible summary; without JS the groups stay open. region.py:183 reuses the section, so region pages get it for free. Extend tests/test_archive_page.py and add filter/group coverage to tests/maplist_js_harness.js (it has none today).

**Files.** `tools/sitegen/pages/archive.py`, `assets/js/pages/archive.js`, `assets/css/pages/archive.css`, `tests/test_archive_page.py`, `tests/maplist_js_harness.js`.

**Effort.** M. Visitor value 2.3, author value 1, confidence high.

**Risk.** The summary must keep the .arc-yr-h flex layout in every browser (Safari draws its own marker on display: flex summaries unless list-style is reset); the activity filter rewrites counts inside summaries; sitecheck's anchor check must still find #yr-YYYY.

**Review note (condensed; the observation and proposal above are the revised text).** The proposal is not built (archive.py:358-359 wraps each group in div.arc-yr; archive.js:91-140 only filters rows and rewrites counts, nothing folds; region.py:183 reuses archive_section), and the page height is right (.cache/plan2/shots/phone-map.jpeg is 1170x51048 at 3x = 17,016 CSS px; _site/map/index.html has 168 class="rtab-r" rows). The measurements hold: .cache/plan2/shots/phone-map.jpeg is 1170x51048 at 3x (about 17,000 CSS px), _site/map/index.html has 168 .rtab-r rows in 7 .arc-yr groups (six years + Planned), and region.py:183 reuses archive_section, so region pages repeat their rows (REPORT 15.4 point 12 already notes the smallest page lists its reports twice). Mostly reproduces: .cache/plan2/shots/phone-map.jpeg is 1170x51048 (17,016 CSS px at 3x); _site/map/index.html has 168 <a class="rtab-r"> rows with ids yr-2021..yr-2026 plus a seventh yr-planned group; the year index is anchor links only (archive.py:359-363); region.py:183 reuses archive_section(). Two details are wrong.

#### qa-06. Give region maps a full-screen page on phones

**Observation.** On a 390 px phone the Lake Tahoe map carries 5 pins and 11 clusters (48 px targets) of which 9 pairs overlap (the "32" cluster sits over others); the phone render has no "Open the full map" button and no larger view exists, whereas every report map has the 44 px button and a `trips/<slug>/map/` page that opens on the route.

**Evidence.** `.cache/plan2/qa/p-map-top.png (overlapping clusters)`; `evaluate_script on map/ (phone): pins 5, clusters 11, overlappingPairs 9, no full-screen button in the panel`; `tools/sitegen/core.py:523-524 (report full-screen button), tools/sitegen/pages/report.py:683-705 (the page), tools/sitegen/pages/archive.py:226 (region map_block without the button)`; `.cache/plan2/qa/p-fsmap.png (the report version working on a phone)`; `tools/sitegen/core.py:523-524 (full-screen button only with fullscreen_href)`; `tools/sitegen/pages/archive.py:226-227 and tools/sitegen/pages/home.py:323 (region map_block without it)`; `tools/sitegen/pages/report.py:683-706 (fullscreen_page)`; `rendered/site/meta.json (region-*-desktop 718×620, region-*-phone 390×480)`; `phone-map.jpeg (crop: top) (clusters 32, 9, 9, 8, 6, 6, 4, 3, 2)`; `phone-section-ski.jpeg (crop: top) (13, 10)`; `tools/lib/mapkit.py:1514 (pin hit radius 22 on desktop renders)`.

**Proposal.** build `map/<region-slug>/` (noindex, index=False) in archive.py with the report page's `.fs-map` shell (report.py:683-706) around the existing `region-<slug>-desktop` render, and pass fullscreen_href on the archive.py:226 map_block call (which map/ and regions/<slug>/ share through region_panel) and on home.py:323 so the 44 px `.mv-fs` button (base.css:346-351) appears on phone region maps; 'Back' returns to `map/#region-<slug>`. In base.js, give the region fs page its own branch (e.g. `data-fs="region"` on `.fs-map`): skip the `.mk-trk` logic, since the Lake Tahoe render carries the planned route as a `.mk-trk`, and center both axes on the whole map; the present fallback only centers horizontally. region.py needs a change only if its Back target differs; sitecheck.py already accepts noindex pages (sitecheck.py:168-169) and `map/#region-x` anchors (274), so keep it in the list only for any new check the page needs. Files otherwise unchanged.

**Files.** `tools/sitegen/pages/archive.py`, `tools/sitegen/core.py`, `tools/sitegen/pages/region.py`, `tools/sitegen/pages/home.py`, `assets/css/base.css`, `assets/js/base.js`, `tools/sitegen/sitecheck.py`, `tests/test_archive_page.py`.

**Effort.** M. Visitor value 2.3, author value 1, confidence high.

**Also covers.** phone-19 (merged into this finding).

**Risk.** Eight new noindex URLs; no new render (the desktop pair exists); each page inlines the region overlay SVG again (~100 KB).

**Decision for Eric.** Whether region maps deserve their own full-screen pages.

**Review note (condensed; the observation and proposal above are the revised text).** The limit is real (16 clusters on the Lake Tahoe phone render per rendered/site/meta.json, overlapping in the phone capture) and the fix reuses existing pieces: `fullscreen_page` (report.py:683-705), the `fs` variant of `map_block` (core.py:484-490) and the 718×620 desktop renders, so no render is needed. Observation reproduces: the top crop of .cache/plan2/qa/p-map-top.png shows 11 clusters (2, 2, 2, 6, 9, 9, 32, 8, 3, 6, 4) and 5 pins with the 32 sitting over the 6/8 group; no full-screen button appears because core.py:523-524 emits `.mv-fs` only with fullscreen_href, which archive.py:226 and home.py:323 never pass (region pages go through archive.region_panel, region.py:181); rendered/site/meta.json maps region-*-desktop 718×620 and region-*-phone 390×480; report.py:683-706 is fullscreen_page.

#### phone-04. Region maps on phones: two-line caption and a compact key

**Observation.** Under the Lake Tahoe map a phone shows a five-line caption (pins, full tracks · North up, Terrain, Map data, Not for navigation), then a seven-item LEGEND in two columns, then the IN THIS REGION head: about 400 CSS px (half a screen) between the map's bottom and the first report row, on map/ and on every region page, where a report map keeps a two-line caption and puts the credit in the in-map tag. The home page shows the same region maps with a one-row compact key.

**Evidence.** `phone-map.jpeg (crop: top)`; `phone-map.jpeg (crop: s2)`; `phone-region-eastern-sierra.jpeg (crop: top)`; `assets/css/pages/archive.css:36 (.mapcap-2 kept on phones)`; `tools/sitegen/pages/archive.py:226-229 (attrib=False)`; `assets/css/pages/archive.css:52-59 (legend lists)`; `tools/sitegen/pages/home.py:246 (region_key), assets/css/pages/home.css:180-183`; `assets/css/base.css:343-351, 389-391, 404`; `tools/sitegen/pages/archive.py:226-229 (map_block attrib=False, map_caption with credits)`; `assets/css/pages/archive.css:36 (.arc-cap .mapcap-2 { display: block } under 560)`; `tools/render.py:668-671 (phone site specs reserve (w-208, h-36, w, h))`; `tools/sitegen/core.py:508-512 (the tag when attrib and a phone variant)`; `assets/css/base.css:343-351 (.mv-attrib), docs reader design map §8.2 item 17 (three caption lengths)`; `.cache/plan2/qa/p-map-top.png and p-map-oregon-reload.png`; `evaluate_script on map/ (phone): mapBottom 707, legendTop 843, firstRowTop 1109, inMapTag false`; `.cache/plan2/qa/p-matterhorn-scrolled.png (report map with the in-map tag)`; `tools/sitegen/pages/archive.py:226 ('attrib=False'), assets/css/base.css:343-351 and :404 (in-map tag; '.mapcap-2' hidden under 560)`.

**Proposal.** Pass attrib=True for the region map_block call at archive.py:226 (the .mv-attrib tag is phone-only already, base.css:351, and render.py:669-670 reserves its corner) and delete the archive.css:36 override so the credit lines hide under 560 px as on reports. On home.py:323 either leave attrib=False or also hide .hom-attr under 560, since home.py:338 prints the credit line at every width. Below 760 px replace the vertical .arc-legend lists with the home page's compact key row (discs with icon + word, planned line, cluster symbol); the existing keyrow--d/--p pair switches at 560 (base.css:390-391), so the 760 cut needs its own rule. Same for region pages (archive.py region_panel(page=True)).

**Files.** `tools/sitegen/pages/archive.py`, `tools/sitegen/pages/home.py`, `assets/css/pages/archive.css`, `tests/test_archive_page.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Also covers.** maps-18, qa-09 (merged into this finding).

**Risk.** The OSM credit must stay visible on every page that draws a map (the in-map tag and the footer carry it); the compact key must keep icon + word so color is never the only cue (DEVELOPING.md rule).

**Review revision (applies on top of the text above).** Observation: as written, except the Lake Tahoe legend is an eight-row list. Proposal: Pass attrib=True for the region map_block call at archive.py:226 (core.py:521 draws the `.mv-attrib` tag on the phone variant only; render.py:671 already reserves its corner) and delete the archive.css:36 override so the credit line hides under 560 px as it does on reports. Below 760 px replace the vertical .arc-legend lists with the home page's compact key row (discs with icon + word, planned line, cluster symbol) via a keyrow--p / keyrow--d pair (base.css:389-391), keeping the full legend from 760. Region pages get it through archive.region_panel(page=True). For home.py:323 only do the same if `.hom-attr` (home.css:184) is hidden under 560 px in the same change; otherwise leave the home maps as they are, since they already carry a credit line.

**Review note (condensed; the observation and proposal above are the revised text).** Verified not built and the observation holds: archive.py:226 passes attrib=False; core.py:521 emits the `.mv-attrib` tag only when attrib is true and a phone variant is drawn; _site/map/index.html contains 0 'mv-attrib'; archive.css:36 shows `.mapcap-2` under 560 px against base.css:404 which hides it elsewhere; phone-map.jpeg (crop: top) shows the five-line caption; render.py:671 reserves the bottom-right 208×36 of phone renders, so the tag has room; home.py:246 region_key and base.css:389-391 keyrow--p/--d give the compact-key pattern. Verified: core.map_caption (core.py:712-724) adds the three credit items, archive.css:36 shows them under 560 where base.css:404 hides them on reports, archive.py:226 and home.py:323 pass attrib=False, the .mv-attrib tag is phone-only and emitted only when a phone variant exists (core.py:521, base.css:343-351), the phone region renders reserve a 208x36 bottom-right slot (render.py:668-671) so the tag has room, the legend is seven rows (phone-map-s2.jpeg, archive.py:107-125, archive.css:52-59), and home has the compact key via region_key (home.py:246-271, 'keyrow keyrow--compact hom-rkey'). The caption and legend facts reproduce: phone-map-top.jpeg and phone-region-eastern-sierra-top.jpeg show the five caption lines; phone-map-s2.jpeg shows the seven legend items (in two columns) then IN THIS REGION; archive.py:226-227 passes attrib=False and :229 builds the caption with credits; archive.css:36 forces .mapcap-2 back on under 560 against base.css:404; home.py:246-271 emits one keyrow--compact row; render.py:669-670 reserves the phone render's bottom-right 208x36 for the tag, so the in-map tag fits.

#### gap2-01. Fit the stuck region map to the viewport on map/ and region pages

**Observation.** archive.css:39-43 makes .arc-mapcol sticky at ≥1000 px with top: calc(var(--header-h) + 24px) and no height guard; the column holds the 718×620 desktop render (rendered/site/meta.json) plus a two-line caption (archive.py:229 → core.map_caption, six items: base.css:397-398, 12 + 2×20 = 52 px). Written out: at 1366×768 (683 px viewport) the map is 718 wide and 620 tall, stuck from y=96 to 716, so the bottom 33 px (the compact scale bar's '10 mi' label sits at y=591 of 620 in rendered/site/region-lake-tahoe-desktop.svg.html) and the whole caption are off-screen; at 1280×720 (~620 px) the map is 681×588, stuck 96..684, 64 px cut plus the caption; at 1152×720 (a 1440×900 Mac at 125 %, the 1000-1199 band, 8/12 columns) it is 707×610 at top 80, 60 px cut; only at 1024×768 does the map fit (537 tall) with just the caption clipped. A visitor on map/ reaches that state after about 204 px of scrolling (the map's top is near y=300: header 72 + head 40 + 56 (.t-d1 at ≥1200, base.css:68) + 12 + 20 + 32 + tabs 44 + 24) and stays in it for the whole opened Lake Tahoe list (89 rows at 61 px ≈ 5,400 px after 'Show all 86'); folded, the sticky range is only ~154 px (side column ≈ 826 px vs map column 672). The ski panel already solves the same problem by scaling its map to 100vh and going static under 600 px (section.css:275-284); About's column sticks only at min-height 880 (about.css:14). The first-round captures are full-page, so no one has seen this stuck state.

**Evidence.** `assets/css/pages/archive.css:39-49`; `tools/sitegen/pages/archive.py:229-250`; `tools/sitegen/core.py:712-723`; `rendered/site/meta.json (region-lake-tahoe-desktop 718×620, -phone 390×480)`; `rendered/site/region-lake-tahoe-desktop.svg.html (scale label y=591, viewBox 0 0 718 620)`; `tools/lib/mapkit.py:1438,1793`; `assets/css/pages/section.css:275-287`; `assets/css/pages/about.css:13-14`; `assets/css/base.css:17-22,150`; `_site/map/index.html (89 .arc-row in #region-lake-tahoe, 'Show all 86', caption items)`; `tools/sitegen/pages/region.py:179-182`.

**Proposal.** Model the fix on section.css:277-284. In archive.css at >=1000 px: `.arc-mapv .mv { width: min(100%, calc((100svh - var(--header-h) - 24px - 52px - 12px) * 718 / 620)); }` (52 px is the two-line caption: 12 + 2x20; the credit line fits the 707 px column at 1000-1199, so one budget serves both bands; if the browser check shows it wrapping there, add a band override with 72 px). The stuck column is then header + 24 + map + caption + 12 to spare: 606 px wide (0.84x) at 683 px, 556 (0.77x) at 640, 563 (0.80x) at 1152x630. Add `@media (min-width: 1000px) and (max-height: 599.98px) { .arc-mapcol { position: static; } .arc-mapv .mv { width: 100%; } }`, the same release as the ski panel. The inline aspect-ratio on .mv keeps the height in step; region pages reuse the panel (region.py:181) and are fixed by the same rules. Extend ShortViewportTests (tests/test_a11y_static.py:2731) with .arc-mapcol at (1366,683) sticky + width containing '100svh', and (1300,599) static. Check in a browser at 1366x768 and 1280x720 that the scale bar and caption stay visible while the list scrolls.

**Files.** `assets/css/pages/archive.css`, `tests/test_a11y_static.py`, `docs/DEVELOPING.md`.

**Effort.** M. Visitor value 2.3, author value 1, confidence high.

**Risk.** Scaling the inline SVG scales its 11-12 px labels (mapkit.py MAP_CSS) to 9-10 px at 683 px; below 0.75× they are hard to read, hence the static release at 600. A narrower map leaves a gap before the 5/12 side column (as the ski panel accepts). Hover/row highlighting (base.js) is unaffected. No content or URL change.

**Decision for Eric.** Whether to release the sticky map under 600 px of height (ski-panel rule) or under ~656 px, where the map falls under 0.8× of its render.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: archive.css:41 sticks .arc-mapcol at >=1000 with no height guard; the render is 718x620 (rendered/site/meta.json maps/region-lake-tahoe-desktop); the scale label sits at y=591 of a 0 0 718 620 viewBox; the caption is 6 .mi items on two lines; the Lake Tahoe panel holds 89 li.arc-row and 'Show all 86'; region.py:181 reuses region_panel(page=True) so both page types share the rule. Reproduces almost entirely: archive.css:39-43 makes .arc-mapcol sticky at >=1000 with top header+24 and no height guard; rendered/site/meta.json gives region-lake-tahoe-desktop 718x620 and -phone 390x480; the caption is six items (archive.py:229 + core.py:712-723) at 12 + 2x20 = 52 px (base.css:397-398); the viewBox is 0 0 718 620 and the '10 mi' label sits at y=591 (rendered/site/region-lake-tahoe-desktop.svg.html); mapkit.py:1438 and :1793 are the compact scale bar; _site/map/index.html has 89 .arc-row in #region-lake-tahoe and 'Show all 86'; rows are 60 min-height + 1 px border (archive.css:66-67); the column widths (718 / 681 / 707 / 621 at 1366 / 1280 / 1152 / 1024, using --m 48 or 40 and --header-h 72 or 56 from base.css:14-22) and the derived heights check out; section.css:275-284 and about.css:14 are as stated; region.py:181 reuses region_panel(page=True), and core.py:525 writes the inline aspect-ratio that keeps height in step, so the proposal's width rule in archive.css mirrors section.css:281 correctly, and tests/test_a11y_static.py:2731-2755 has the ShortViewportTests pattern to extend.

#### gap2-02. Ski page: show the phone-shaped panel render on short desktop windows

**Observation.** At ≥1200 px the ski page's sticky region panel scales the 506×680 render to `(100vh − 72 − 24 − 45 − 12 − 72 − 12) × 506/680` (section.css:281) and goes static only under 600 px (section.css:284). Written out: a 1366×768 laptop (683 px viewport) gets a 332 px wide map (0.66× of the render), 1280×720 (~640) gets 300 px (0.59×), and at 600 px it is 270 px (0.53×); the map's labels are 11-12 px in the render (tools/lib/mapkit.py:35-82 .mk-cl, .mk-rl, .mk-lbl, .mk-peak, .mk-place) and so read at 6.5-8 px on the two most common laptop sizes. The 390×480 phone-shaped render exists for the same regions (rendered/site/meta.json ski-*-phone) and is already the desktop-approved variant at 760-1199 px (section.css:257, 272, 'shows at 1:1' at 1100-1199, :286-287); with the same budget it would be 362 px wide (0.93×) at 683 and 327 (0.84×) at 640. The full-page capture desktop-section-ski.jpeg shows the season rows with an empty right column, since a sticky panel is drawn only at its in-flow position, so the shrunken state was never looked at.

**Evidence.** `assets/css/pages/section.css:257,272,275-287`; `tools/lib/mapkit.py:35-82`; `rendered/site/meta.json (ski-lake-tahoe-desktop 506×680, ski-lake-tahoe-phone 390×480)`; `tools/sitegen/pages/section.py:359-382`; `.cache/plan2/shots/desktop-section-ski.jpeg (rows beside an empty panel column)`.

**Proposal.** Add to section.css: `@media (min-width: 1200px) and (max-height: 759.98px) { .sec-maps .mv--desktop { display: none; } .sec-maps .mv--phone { display: block; } .sec-maps .mv { width: min(100%, calc((100svh - var(--header-h) - 24px - 45px - 12px - 72px - 12px) * 390 / 480)); } }` (760 is where the 506 render falls under 0.77×). Keep the static release under 600 px. The phone variant is `loading="lazy"` and fetched once shown (core.py:502-509); the ski panel has no preload (section.py:525 preloads the featured map only), so nothing else changes. Switch the two existing rules (section.css:277, 281) from 100vh to 100svh at the same time. Add a ShortViewportTests case in tests/test_a11y_static.py for `.sec-maps .mv--phone` display at (1366,683) and (1366,900). Verify at 1366×768 that the region labels read and the whole panel (tabs, map, caption) fits.

**Files.** `assets/css/pages/section.css`, `tests/test_a11y_static.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Risk.** Two renders of the same map may both load if a window is resized across 760 px of height (one extra ~40-90 KB image). The phone render's frame is narrower, so a few regions may crop differently from the desktop one; the tablet band already shows it, so nothing new is exposed.

**Review note.** Kept as written by all three skeptics.

#### gap2-03. Compact the sticky multi-day chapter rail on short windows

**Observation.** multiday.css:246 makes the chapter rail sticky at ≥1000 px with top: header + --dnav-h + 24 = 72 + 80 + 24 = 176 px (≥1200) or 56 + 72 + 24 = 152 (1000-1199), with no height guard. The rail holds the 96/88 px day number (multiday.css:248), label (12/16, base.css:76) + title (18/24; 3 of 12 columns ≈ 294 px wide at 1248, so 7 of the 34 chapter titles in the build are over 28 visible characters and wrap to two lines, 6 of them on the Haute Route page), a hut line on 5 of that page's 6 days, five 48 px stat rows (Distance, Gain, Loss, GPS max, Moving; multiday.css:250-253, min-height 48 with the 1 px border inside it under base.css:24's border-box, above the list's own 1 px top border; Loss shows from 760, :238) and the 44 px 'Day N GPX' button (multiday.css:196 .mul-dgpx, a .btn, base.css:320). Written out: 88 + 12 + 16 + 4 + 24 + 32 + 20 + 241 + 16 + 44 ≈ 497 px with a one-line title, 521 with two. At 683 px (1366×768) the rail bottom is at 673-697, so the GPX button is cut on the two-line days; at 640 (1280×720) 33-57 px are cut on every day, at 600 73-97 px; at 1152×630 (1000-1199 band, a 250 px rail that also stacks the hut label over its name, :177-180, and wraps more titles) roughly 20-45 px or more. The day bar above it already has a short-viewport rule (multiday.css:34, static under 480 px). The proposal's compact rows save 8 px each, so it takes 28 + 40 + 8 = 76 px off the rail (421-445 px, bottom at 597-621 at ≥1200).

**Evidence.** `assets/css/pages/multiday.css:3-5,34,165-170,197,244-253,264-267`; `_site/trips/chamonix-zermatt-haute-route/index.html (.mul-rail: 5 .mul-ds-r rows, .mul-hut, .mul-dgpx; 6 titles over 28 chars)`; `assets/css/base.css:17-22`.

**Proposal.** Add `@media (min-width: 1000px) and (max-height: 719.98px) { .mul-num { font-size: 64px; line-height: 60px; } .mul-ds-r, .mul-ds-r.pc-r, .mul-ds-r:first-child { min-height: 40px; padding: 4px 0; } .mul-ds { margin-top: 12px; } }` in multiday.css, which takes 28 + 45 + 8 = 81 px off the rail (420-444 px, bottom at 596-620 at ≥1200), so the GPX button is in view down to a 620 px viewport; under that add `@media (min-width: 1000px) and (max-height: 599.98px) { .mul-rail { position: static; } }`, the same release as the ski panel. Extend ShortViewportTests in tests/test_a11y_static.py with .mul-rail at (1366,683) sticky and (1300,599) static. Check the Haute Route page at 1366×768 and 1280×720.

**Files.** `assets/css/pages/multiday.css`, `tests/test_a11y_static.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence medium.

**Risk.** The rail's compact stat rows must keep the 44 px target of the GPX button and the 18/24 value size; the day number at 64 px on short windows differs from the 96 px of taller ones, which is a deliberate step, not a bug. No markup or URL change.

**Review note (condensed; the observation and proposal above are the revised text).** The observation holds but three details are wrong.

#### gap2-04. Full-screen map page: give a landscape phone the height back

**Observation.** The full-screen map page (trips/<slug>/map/, report.py:683-705, reached only from the phone map's button, core.py:523-524) sizes its pannable box with `max-height: calc(100svh - 140px)` (base.css:374): header 56 + the 'Back to report' bar (12 + 44 + 12 = 68) + 16 to spare. Written out: a 390×844 phone gets a 704 px box (83 % of the height, enough for the 640 px tall wide render); a 667×375 phone turned sideways, the natural move to see more of a map, gets 235 px (63 %), 844×390 gets 250, 932×430 gets 290, with the 124 px of fixed header and bar above it and the 1440×640 render panning both ways inside. The multi-day day bar already releases under 480 px of height (multiday.css:34); the header on this utility page has no such rule.

**Evidence.** `assets/css/base.css:150,370-379`; `tools/sitegen/pages/report.py:683-705`; `tools/sitegen/core.py:521-526`; `assets/js/base.js:428-459`; `assets/css/pages/multiday.css:34`.

**Proposal.** In base.css under the fs-map rules add `@media (max-height: 480px) { .p-fsmap .site-h { position: static; } .p-fsmap .fs-map { max-height: calc(100svh - 68px); } }`, so once the 56 px header scrolls away the Back bar and the box fill the screen: 307 px of map at 667x375 (82%), 322 at 844x390. base.js's initial scroll to the route (base.js:428-459) works on the box's clientWidth/Height and needs no change. Add the (max-height) case to ShortViewportTests in tests/test_a11y_static.py and look at it on a real phone in landscape, which docs/IMPLEMENTATION_REPORT.md:855 lists as never run. Known: section 15.4.12 (landscape-phone chrome, rated and left). Do not change the fs page's layout at other sizes.

**Files.** `assets/css/base.css`, `tests/test_a11y_static.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 15.4.12 (landscape-phone chrome, rated and left) and 15.5 (no real phone run)

**Risk.** With a static header the page scrolls 56 px before the map is full height; a visitor who taps 'Back to report' then lands back on the report's #map as before. 100svh is already relied on by this rule and the lightbox (base.css:719-722).

**Decision for Eric.** Static header under 480 px (small change) or the Back button overlaid on the map at every size.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: base.css:374 caps .fs-map at calc(100svh - 140px) (header 56 + bar 12+44+12 + 16), the fs page is reached only from the phone map's .mv-fs button (core.py:523-524; shown below 560, base.css:351), and base.js:428-459 sets scrollLeft/Top on the box so a static header changes nothing in the script. The two-line (max-height: 480px) rule is feasible, S, and mirrors multiday.css:34.

#### gap2-05. PCT journal: release the sticky month bar on short viewports

**Observation.** The journal's month bar is sticky at top: var(--header-h) (series.css:107) at 52 px on phones and 64 px from 760 (series.css:4-5), with no (max-height) rule; the multi-day day bar got one at 480 px in Phase 4 (multiday.css:34) and tests/test_a11y_static.py:2752-2755 pins that the month bar was deliberately 'not touched'. Written out: a 667×375 phone reads the day log under 56 + 52 = 108 px of fixed chrome (29 % of the height); on a 1366×768 laptop the log sits under 72 + 64 = 136 px (20 %). The scroll-padding concern is already handled: html's padding knows the header only (base.css:25-26, the `--sticky-extra` hook there is a comment no page sets), but series.css:132, 143-147 give .ser-month, .ser-day and every control in .ser-log a scroll margin of the bar's height + 8, and all 63 in-page links on the built page and the two journal rows on map/ target #day-N articles, so by CSS nothing lands under the bar.

**Evidence.** `assets/css/pages/series.css:4-5,107-130,132,143-147`; `assets/css/pages/multiday.css:34`; `assets/css/base.css:25-26`; `tests/test_a11y_static.py:2733-2755`; `docs/DEVELOPING.md:140-146`; `docs/IMPLEMENTATION_REPORT.md:293`; `_site/trips/pacific-crest-trail-2024/index.html (150 article#day-N, 6 section#month-*, 63 href="#day-N")`; `_site/map/index.html (journal rows → ../trips/pacific-crest-trail-2024/#day-67, #day-146)`.

**Proposal.** Only if gap2-07's rule 'bars release under 480 px of height' is adopted: give the month bar the day bar's rule, `@media (max-height: 480px) { .ser-mnav { position: static; } .ser-log :is(a, button, input, summary), .ser-month, .ser-day { scroll-margin-top: 0; } }` in series.css, so a sideways phone reads the log under the header alone. Update test_the_journals_month_bar_is_not_touched (tests/test_a11y_static.py:2752) to expect static at 480 and 375 and sticky at 844, and the sentence 'the journal's month bar is unchanged there' in docs/DEVELOPING.md:146. Leave base.css:25-26 alone (the scroll-padding declaration is pinned by tests/test_a11y_static.py:2549). If gap2-07's rule is not adopted, record the month bar as the one deliberate exception in the sticky-parts table instead of changing it. Known: IMPLEMENTATION_REPORT.md 15.4.11 and :293.

**Files.** `assets/css/pages/series.css`, `assets/css/base.css`, `tests/test_a11y_static.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 15.4.11 ('journal label links land under the sticky month bar', not reproducible from the CSS) and 2.x landscape row at :293

**Risk.** On a short window the month scrollspy's aria-current still updates but the bar scrolls out of view, as the day bar does today. The bar was left sticky on purpose in Phase 4 (its chrome share, 29 %, is under the 32.5 % accepted for the multi-day page), so this is a parity choice, not a defect fix.

**Decision for Eric.** Keep the month bar sticky on a sideways phone (current, deliberate) or release it like the day bar.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: series.css:107 sticks .ser-mnav at top: var(--header-h) with no max-height rule; :132, 143-147 give the log's controls their own scroll margins; tests/test_a11y_static.py:2752-2755 pins the bar sticky at 480 and 375; docs/DEVELOPING.md:146 says it is unchanged there; IMPLEMENTATION_REPORT.md:293 shows Phase 4 measured it and left it on purpose.

#### gap2-06. Keep a one-line map key beside the stuck region map

**Observation.** On map/ and region pages the legend (five activity discs, 'Planned route', the numbered cluster 'Several reports start here'; 7 items, archive.py:244-250 legend(), archive.css:52-59, about 190 px tall) sits at the top of the scrolling side column, not in the sticky map column (archive.py:239-246). At ≥1000 px it scrolls away after roughly its own height while the map stays stuck for the rest of the list (~5,400 px when 'Show all 86' is open), so the colors of the lines and the meaning of a numbered circle have no key on screen while the visitor is matching rows to the map; the rows carry an activity icon + word (archive.py:201-203) but nothing explains the cluster numbers. The home page already renders a compact one-line key under its region maps (home.py:306-340, home.css:166-224, core.key_row).

**Evidence.** `tools/sitegen/pages/archive.py:239-250`; `assets/css/pages/archive.css:39-59`; `tools/sitegen/pages/home.py:306-340`; `assets/css/pages/home.css:166-224`; `tools/sitegen/core.py:661-690`; `_site/map/index.html (#region-lake-tahoe legend: 7 li, 2 ul)`.

**Proposal.** In archive.py region_panel, emit a compact key row inside .arc-mapcol under the caption, built the way home.region_key builds the home page's (home.py:246-271: core.disc for each activity the map draws, core.KEY_SYMBOLS['planned_site'] for the planned line, the cluster symbol), not with core.key_row, which only knows core.KEY_SYMBOLS (core.py:661-669) and has no disc or cluster entry; lift that item logic into archive.py or core so home and map/ share it. Give the row `display: none` below 1000 px and hide the vertical .arc-legend in .arc-side at ≥1000 px by CSS alone; make the two one element moved by grid placement where possible, or keep the hidden one out of the accessibility tree. Add the archive counterpart of home.css:181-183 (row padding, 9 px disc icons) and extend the forced-colors rule at archive.css:58 to the row's discs. Budget its height (32 px, or 56 when it wraps to two lines in the 7/12 column) in the fit formula of gap2-01, i.e. `- 52px - 56px` instead of `- 52px`, which costs about 0.09× of map width at 683 px (0.75× instead of 0.84×). Do this only together with gap2-01, since without the fit the extra row pushes more of the map off-screen.

**Files.** `tools/sitegen/pages/archive.py`, `assets/css/pages/archive.css`, `tests/test_archive_page.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence medium.

**Risk.** A second legend in the markup must stay aria-hidden or the two must be one element moved by CSS (grid-row placement), or screen readers hear the key twice. The forced-colors rule for the discs (archive.css:58) must cover the compact row too. Not maps-07 (the legend as a filter): this is placement only.

**Decision for Eric.** Whether a smaller stuck map with its key beside it beats a larger one without; the home page's compact key row is the precedent.

**Review revision (applies on top of the text above).** Observation: unchanged, except that the home page's compact key is home.region_key (tools/sitegen/pages/home.py:246-274, emitted by where() at home.py:340 as <ul class="keyrow keyrow--compact hom-rkey">), built from core.disc, core.KEY_SYMBOLS['planned_site'] and archive.CLUSTER_SYM with the activity set read from the map's clusters in rendered/site/meta.json; core.key_row (core.py:661-670) knows only KEY_SYMBOLS and cannot draw activity discs. Proposal: move home.region_key (and the disc/planned/cluster item logic it shares with archive.legend) into archive.py or core.py so map/, the region pages and Home draw the same compact row from the same meta; in archive.region_panel emit that row inside .arc-mapcol under the caption, display: none below 1000 px and without JS, and hide the vertical .arc-legend in .arc-side at >=1000 px with JS on, keeping one of the two out of the accessibility tree (aria-hidden, or a single element moved by grid-row placement). Budget its height (32 px, or 56 when it wraps in the 7/12 column) in the gap2-01 fit formula, i.e. '- 52px - 56px' instead of '- 52px', about 0.09x of map width at 683 px. Extend the forced-colors rule at archive.css:58 to the compact row's discs (home.css:179 sizes them at 9 px). Do this only together with gap2-01. Tests: tests/test_archive_page.py for the markup, and the existing home key tests for the shared helper.

**Review note (condensed; the observation and proposal above are the revised text).** The placement is not built: archive.py:239-246 puts legend(key_ts, md) first inside .arc-side, before .arc-inreg, and .arc-mapcol holds only the map and the caption (archive.py:241-242 and :254), on map/ and on region pages alike (region.py:181 calls region_panel(page=True)); the Lake Tahoe legend on _site/map/index.html has 7 li in 2 ul (Activities, Map symbols) and archive.css:52-59 styles it as a vertical list with the forced-colors rule at :58. Verified: archive.py:239-246 puts legend() (7 li in 2 ul on the Lake Tahoe panel) at the top of .arc-side while .arc-mapcol is the sticky column; at >=1000 it scrolls away after ~190 px and the map stays stuck for the 89-row list; home.py region_key (:246) and home.css .hom-rkey (:181-183) already draw the same items as a compact row. The observation holds: archive.py:241-242 and :250-252 put legend(key_ts, md) first in .arc-side, not in .arc-mapcol; the built Lake Tahoe panel's .arc-legend has 2 ul and 7 li (five activities, 'Planned route', 'Several reports start here'); archive.css:52-59 style it; region_row (:138-141) and journal_row (:201-204) carry icon + word; home.py:339 calls region_key (defined :246-271) and home.css:180-183 style the compact row.

#### gap2-07. One documented rule and one test class for every sticky part

**Observation.** The site has eight sticky parts with five different height policies: the header (base.css:150, static only without JS under 480 px wide), .arc-mapcol (archive.css:41, no guard), .sec-panel-in (section.css:265, scaled to 100vh, static under 600 px), .abo-nums (about.css:14, sticks only at min-height 880), .mul-dnav (multiday.css:29/34, static under 480 px), .mul-rail (multiday.css:246, no guard), .rep-rail (report.css:86, no guard, harmless: the tallest Beta rail in the build has 3 rows, ~130 px), .ser-mnav (series.css:107, no guard). docs/DEVELOPING.md:140-146 documents only the second-bar scroll margins and the day bar's 480 px rule; tests/test_a11y_static.py's D5 ShortViewportTests (:2730-2755) cover the day bar and pin the month bar. The static CSS evaluator there (computed(node, prop, rules, env(width, height))) can already evaluate any of these at 1366×683 or 1280×620, so the laptop sizes that were never measured (brief) can be asserted without a browser.

**Evidence.** `assets/css/base.css:150,374`; `assets/css/pages/archive.css:41`; `assets/css/pages/section.css:265,277,281,284`; `assets/css/pages/about.css:14`; `assets/css/pages/multiday.css:29,34,246`; `assets/css/pages/report.css:86`; `assets/css/pages/series.css:107`; `docs/DEVELOPING.md:140-146`; `tests/test_a11y_static.py:1-30,2730-2755`; `_site/trips/*/index.html (89 .rep-rail blocks, max 3 dt, matterhorn-peak-west-couloir)`.

**Proposal.** Add a 'Sticky parts' table to docs/DEVELOPING.md (element, sticks from which width, top value, what it holds and how tall, the guard or fit rule, the test) and state the rule once: a stuck element fits header + 24 + its content inside 100svh on a 683 px viewport or scales/releases, with 480 px (bars) and 600 px (columns) as the two release heights. Extend ShortViewportTests in tests/test_a11y_static.py with one subTest table over (1366,683), (1280,620), (1152,630), (1440,790), (667,375) for .arc-mapcol, .sec-panel-in, .abo-nums, .mul-dnav, .mul-rail, .ser-mnav and .p-fsmap .fs-map's max-height, asserting position and, for the fitted ones, that the width declaration contains '100svh'. This is the regression net for gap2-01 to gap2-05.

**Files.** `docs/DEVELOPING.md`, `tests/test_a11y_static.py`.

**Effort.** S. Visitor value 1, author value 2, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 15.5 (measurements only at 390×844 and 1440×900)

**Risk.** None to the site; the static evaluator does not compute calc(), so the tests assert declarations, not pixels, and a browser check at 1366×768 remains the final word.

**Review note.** Kept as written by all three skeptics.

#### qa-04. Let the ski season band dim the region map as well

**Observation.** On ski/ choosing "2023-24" hides every other season's rows (4 reports shown, URL `#season-2023-24`) while the "Ski map by region" panel still reads "Lake Tahoe 37" and draws all 37 pins; the panel only follows the hovered row's region after 220 ms. The band filters the list, the map ignores it.

**Evidence.** `.cache/plan2/qa/d-ski-season.png (band on 2023-24, panel "Lake Tahoe 37" with every pin)`; `evaluate_script on ski/#season-2023-24: rows 4, off 3, groups hidden except season-2023-24`; `assets/js/pages/section.js (band → '.is-off' on '[data-f]'), assets/js/base.js:137-153 ('highlight()' dims everything but the given keys)`.

**Proposal.** after a band change, section.js collects the `data-key`s of the rows still shown and calls the shared highlight(map, keys) (expose it on window or dispatch a custom event base.js listens to) so pins and tracks outside the season dim with the existing `.is-hl` styling (base.css:359-364); on mouseleave restore the season dim instead of clearing. For the per-region season count on the tab label (built in ski_panel, section.py:364-369), derive each row's region from the tabpanel whose `.mk-cat[data-key]` holds its key, as tabFor() at section.js:118-122 already does, or write a `data-region` attribute in section.py row() (line 230); rows whose trip is not drawn on the panel map stay as they are (highlight() dims only when it has a hit). Add a harness test for season + hover composition. Files unchanged.

**Files.** `assets/js/pages/section.js`, `assets/js/base.js`, `assets/css/base.css`, `tools/sitegen/pages/section.py`.

**Effort.** M. Visitor value 2, author value 1, confidence medium.

**Risk.** The dimmed-map state must read as "filtered", not broken; preview before deciding (memory rule: render options side by side).

**Decision for Eric.** Whether a season filter should dim the map or only annotate the counts.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: section.js:40-50 toggles `.is-off` on `[data-f]` groups and never touches the map; `highlight()` (base.js:137-153) is a closure whose `off` clears to null. Dimming the pins outside the chosen season reuses the existing `.is-hl` styling (base.css:359-364) and is a coherent, modest-effort change. Observation reproduces: .cache/plan2/qa/d-ski-season.png shows the band on 2023-24 with '4 REPORTS' and the panel still 'Lake Tahoe 37' with every pin; assets/js/pages/section.js apply() (lines 38-62) toggles `.is-off` on `[data-f]` only and never touches the map; follow() at section.js:128-135 switches the tab after 220 ms; base.js:137-155 highlight() dims via `.is-hl` and is not exported (no `window.` assignment in base.js).

#### a11y-06. Draw a CSS-only focus halo on journal lines on region maps

**Observation.** A journal part on a region map is a focusable link (a.mk-line) whose only focus indicator is the highlight base.js applies on focusin; base.css sets .mk-line:focus-visible { outline: none }. Without JavaScript (which the site supports everywhere else) or before the deferred bundle runs, a keyboard user tabbing the Lake Tahoe map lands on an invisible stop.

**Evidence.** `assets/css/base.css:355-358`; `tools/lib/mapkit.py:636-648`; `assets/js/base.js:173-187`; `docs/DEVELOPING.md:146-151`.

**Proposal.** The link's <use class="mk-hit"> strokes are transparent copies of the line paths, but their stroke is an inline style in the committed rendered fragment (mapkit.py:643-644, written by render_map), so add in base.css: .mk-line:focus-visible .mk-hit { stroke: var(--ink) !important; stroke-opacity: .35; } (Highlight under forced colors, beside .mk-pin:focus-visible at base.css:743). That draws a 14 px halo along the whole part with no script; base.js's highlight still layers on top. Dropping the inline stroke from mapkit.line_links instead would let the rule work without !important but needs a render.py run (VERSION bump), so keep that for the next re-render. Add an assertion to tests/test_a11y_static.py that the rule exists and carries !important. Files: assets/css/base.css, tests/test_a11y_static.py.

**Files.** `assets/css/base.css`, `tests/test_a11y_static.py`.

**Effort.** S. Visitor value 1.3, author value 1, confidence high.

**Risk.** None to layout; the halo must not swallow pins drawn over the line (keep opacity under .4).

**Review note (condensed; the observation and proposal above are the revised text).** Observation verified: base.css:357 sets .mk-line:focus-visible { outline: none } with the comment that base.js picks the lines out, no stylesheet has a .mk-hit rule (grep of assets/css), the pin keeps a CSS-only ring at base.css:359 while the line has none, and DEVELOPING.md:146-151 records the JS highlight as the line's focus indicator (a design note from e84e11b, not a rejection of a CSS fallback). Confirmed: base.css:356-357 removes the outline and leaves the focus cue to base.js (base.js:173-187), so without scripting the journal links on region maps have no visible focus. Observation reproduces: base.css:357 sets .mk-line:focus-visible { outline: none } with a comment that base.js picks the lines out; base.js:173-187 adds the focusin/focusout highlight; mapkit.line_links (636-648) writes <a class="mk-line"> with <use class="mk-hit"> transparent strokes; DEVELOPING.md:146-151 documents the script highlight as the only indicator, and the site's no-JS rule is at DEVELOPING.md:126/156/557/660; _site/regions/lake-tahoe/index.html carries two a.mk-line links.

#### gap1-05. Rethink the Ski page's sticky 360 px panel for touch tablets at 960-1199

**Observation.** From 960 the Ski page splits into the list and a sticky 360 px panel (390 px from 1100) that shows the 390×480 phone render, sized by the viewport height (section.css:260-278, 286). Its two reasons to be beside the list are that the panel follows the hovered row (section.js:131-141) and that rows highlight their track (base.js:162-171); on a touch tablet neither fires (gap1-03/04), so the column only costs the rows width: the list is 496 px at 960 and 560 at 1024 (wrap 880/944 minus 360 minus the 24 px gap), the row text column 316/380 px after the 160 px tile (section.css:266), and the four stat columns designed at 120 px (base.css:519) get 79/95 px, which at 960-980 is at or under a five-digit Data-M value with its unit at the 16 px size section.css:271 sets. The tabs themselves work by tap (section.js:104-107), and at 760-959 the page already has a stacked arrangement (panel above the list, tabs and caption left, map right; section.css:250-259).

**Evidence.** `assets/css/pages/section.css:208-295`; `assets/js/pages/section.js:89-143`; `assets/css/base.css:506-519`; `tools/sitegen/pages/section.py:359-382`; `tools/sitegen/pages/section.py:402`; `assets/css/base.css:14-22`.

**Proposal.** Cheapest: a new query beside the 960-1199 block at section.css:269-278, `@media (min-width: 960px) and (max-width: 1099.98px) { .sec-list .trow-stats { grid-template-columns: repeat(2, minmax(0, 120px)); row-gap: 8px; } }` (from 1100 the 390 px panel at section.css:286 leaves the four columns 106-120 px, so the 2x2 grid is for 960-1099 only). Then Eric's choice: (a) keep the sticky column and make it earn its place on touch through gap1-04's row control (tap -> region tab + highlighted track; section.js changes only), or (b) under `@media (hover: none) and (min-width: 960px) and (max-width: 1199.98px)` reuse the 760-959 stacked rules (section.css:250-259) so a touch tablet gets full-width rows and a tabbed map at the top while pointer devices keep the follow. Files: section.css and section.js; section.py only if option (a) needs the row control's markup. Build both at 1024 and 1180 with touch emulation and show them side by side before choosing.

**Files.** `assets/css/pages/section.css`, `assets/js/pages/section.js`, `tools/sitegen/pages/section.py`.

**Effort.** S. Visitor value 1.3, author value 1, confidence medium.

**Risk.** Option (b) forks layout by input capability, which is unusual and must be documented in docs/DEVELOPING.md; the computed widths come from the cascade, not from a device, so verify at 960 and 1024 before and after.

**Decision for Eric.** Keep the sticky ski panel on touch tablets with a tap control, or stack it above the list for (hover: none) at 960-1199.

**Review note (condensed; the observation and proposal above are the revised text).** The widths check out from the cascade: wrap 880/944 at 960/1024, minus the 360 panel and 24 gap (section.css:260) gives a 496/560 list, minus the 160 tile and 20 gap (:266) a 316/380 text column, so the four minmax(0, 120px) stat columns (base.css:519) get 79/95 px. The cheap 2x2 stats fix is CSS-only and specific. Arithmetic reproduces from the cascade: from 960 .sec-split is minmax(0,1fr) 360px with a 24 px gap (section.css:261), 390 px from 1100 (:286), so the list is 880-384 = 496 at 960 and 944-384 = 560 at 1024; the 160 px tile plus 20 px gap (:266) leaves 316/380 for the text column, and four minmax(0,120px) columns (base.css:519) get 79/95 px at the 16 px size section.css:271 sets; the panel shows the 390x480 phone render (render.py:637, section.css:272-277); the 760-959 stacked arrangement is at :250-259 and the tabs answer a click (section.js:104-107); the sticky panel is :262-265.

**Gates.** The phase is done when every line below holds and is recorded in the log entry:

1. Every li.arc-row carries id arc-row-<slug>, journal rows arc-row-<region>-<part>; build.py --check reports no DUPLICATE IDS on map/ and no BROKEN ANCHOR for any 'See on the <Region> map' link on the 168 report pages; a completed-goal fixture gets the plain region link; the PCT intro lists its parts with label_range ranges and links that land.
2. tests/maplist_js_harness.js: a hash to a folded row opens the list, scrolls and focuses it (reusing the cluster-click sequence); a cluster press selects its rows with .is-off on the rest and 'N reports start here · Show all' in the count line (N counts reports, not the planned route), Escape, Show all or a second press clears; aria-hidden removed and role=button added only on linked clusters (rule D4 revised); legend toggles filter rows and dim non-matching markers with forced-colors discs kept; coarse-pointer run with a matchMedia stub: tap selects, second tap opens, tap elsewhere clears, a map without rows is untouched; a focused journal line shows the CSS halo without base.js.
3. Region pages show a Mono-S activity line with counts linking trips/?region=&activity=; the section heads link their region names; the place line links the region at every width (tests/test_report_page.py, both layouts) and the goal pager's region cell lands on the planned line's row.
4. Phone captures at 390 px: map/ folds every year after the first behind the Show-all idiom and a year link or hash unfolds it; region maps carry the in-map credit tag and a compact key row (home maps unchanged or with .hom-attr hidden under 560); map/<region-slug>/ exists for the 8 regions (noindex, index=False) with the 44 px button on phone region maps, the fscol width and whole-map centering; region pages share it.
5. ShortViewportTests in tests/test_a11y_static.py has a subTest table over (1366,683), (1280,620), (1152,630), (1440,790) and (667,375) for .arc-mapcol, .sec-panel-in, .abo-nums, .mul-dnav, .mul-rail, .ser-mnav and .p-fsmap .fs-map asserting position and a '100svh' width where fitted; DEVELOPING.md has the 'Sticky parts' table and the one rule (bars release at 480 px of height, columns at 600).
6. Browser checks recorded with captures: at 1366×768 and 1280×720 the stuck Lake Tahoe map shows its scale bar and caption with a one-line key beside it while the 89-row list scrolls; the ski panel shows the phone render under 760 px of height with readable labels; the Haute Route rail's 'Day N GPX' button is visible at 683 px; a 667×375 landscape phone gets about 82% of the full-screen map page as map; the journal's month bar releases under 480 px of height.
7. Day maps and day profiles share the overview's right edge at 760-999 px (multiday.css max-width var(--col-max)); the Ski list's stat cells go two by two at 960-1099 px; the season band dims pins outside the chosen season after the preview (season beside All shown to Eric).
8. Both Pythons with -W error and build.py --check pass; tests/test_region_page.py, test_archive_page.py and test_region_days.py updated for the ids.

**Tests to add.** New: none. Extended: `tests/maplist_js_harness.js`, `tests/test_a11y_static.py`, `tests/test_archive_page.py`, `tests/test_build_site.py`, `tests/test_home.py`, `tests/test_region_days.py`, `tests/test_region_page.py`, `tests/test_report_page.py`, `tests/test_series_page.py`. Plus the checks the gates name that no unit test covers: The Node harness for maplist.js with a coarse-pointer matchMedia stub; `build.py --check` for duplicate ids and broken anchors; browser captures at the five short-viewport sizes in the ShortViewportTests table.

**Screenshots to capture.** `map/` and `regions/eastern-sierra/` at 390 and 1280 px before and after (before set: `phone-map.jpeg`, `desktop-map.jpeg`, `phone-region-eastern-sierra.jpeg`, `desktop-region-eastern-sierra.jpeg`); the stuck Lake Tahoe map at 1366 by 768 and 1280 by 720; the ski panel under 760 px of height; the Haute Route rail at 683 px; the full-screen map page at 667 by 375; the gap1-01 report frame at 1024 and 1180 px; qa-04's dimmed map beside today's.

**Author inputs needed.** Decision 27's three previews (gap1-01, qa-04, gap2-05) and decisions 29 and 30 (gap4-03 as a fourth action, qa-06 full-screen region pages).

### Phase 13. Phone, tablet, accessibility and copy polish

**Goal.** A sweep of small CSS, markup and wording fixes in three sessions: the header, menu and units switch; legibility and touch (12 px floor, no stuck hover, text-zoom-safe chips, year heads, card tiles, section list headers, print sheet); then accessibility and copy (home target size, heading order, forced colors, spoken units, contrast mode, meta-line dot, consistent labels), ending with the tablet capture profile and Eric's first VoiceOver pass.

**Prerequisites.** Eric's decisions on the units switch (gap6-02 in the menu, recommended, or gap6-01 in the header), the km default by browser language, and the site words (copy-11, copy-14, ia-13). visual-01 step 2 (a 400 px tile) waits for Phase 15.

**Decisions this phase waits on.**

- Units switch on phones: gap6-02 (Units row first in the menu, keeps plan 8.1; recommended) or gap6-01 (beside the menu button, reverses 8.1)
- Start in kilometers when navigator.language does not start with 'en' (gap6-03; recommended yes)
- 'Backcountry Ski' to 'Backcountry Skiing' (copy-11; recommended yes)
- PCT aria-label 'PCT journal' and keep the menu button named 'Menu' (copy-14, 12.10)
- Crumb root stays Reports to home; labels unified only (ia-13)

**Findings in this phase** (33, in working order): phone-09, phone-10, phone-12, phone-13, phone-15, gap1-06, gap1-08, gap6-02, gap6-03, a11y-10, visual-04, visual-17, visual-01, visual-11, visual-09, visual-10, visual-13, qa-10, copy-13, copy-20, gap6-07, a11y-03, a11y-08, a11y-04, a11y-05, a11y-15, qa-01, a11y-12, ia-13, copy-14, copy-11, resilience-01, copy-12.

#### phone-09. Stop iOS zooming on the selects and the copy field

**Observation.** iOS Safari zooms the page when a form control with a font size under 16 px takes focus. The Trips and Tick-list <select>s are 15 px and the copy-by-hand field is 13 px mono (and base.js focuses and selects it), so on an iPhone a tap on Region, Year, Format or Sort, or the fallback copy field, can zoom the page and leave it zoomed. The search box is already 16 px and unaffected.

**Evidence.** `assets/css/pages/trips.css:32-34 (select font 15px)`; `assets/css/pages/trips.css:24-25 (.trx-q 16px)`; `assets/css/pages/report.css:176-177 (.copy-url 13px)`; `assets/js/base.js:411-415 (inp.focus(); inp.select())`.

**Proposal.** Below 760 px set `.trx-sel select { font-size: 16px; }` and `.copy-url { font-size: 16px; }` (keep the faces; widen the field's min() cap by a few ch); add enterkeyhint="search" to #trx-q in trips.py and to the tick-list box so the phone keyboard's return key reads Search.

**Files.** `assets/css/pages/trips.css`, `assets/css/pages/report.css`, `tools/sitegen/pages/trips.py`, `tools/sitegen/pages/ticklist.py`.

**Effort.** S. Visitor value 2, author value 1, confidence medium.

**Risk.** None beyond a slightly taller select text; the custom chevron padding may need 2 px more.

**Review note.** Kept as written by all three skeptics.

#### phone-10. Short and notched phones: reclaim the fixed chrome

**Observation.** A report keeps 56 px of header (base.css:17, 150) and a 65 px bottom bar (report.css:185-187: border + 4 + 56 + 4; the footer reserves 72) on screen, 121 px; on a small phone held sideways (667x375) that is a third of the height, which the review rated and left (IMPLEMENTATION_REPORT.md 15.4 point 12). The bar's safe-area padding is inert because the viewport meta (core.py:1734) has no viewport-fit=cover, so env(safe-area-inset-bottom) is always 0. At phone widths only the multi-day day bar has a short-viewport rule, and only under 480 px (multiday.css:34). base.css:186-190 already sets --header-h: 0px and .site-h { position: static } for the no-script case, so the same flip under (max-height: 500px) has a precedent; the menu's inset (base.css:212) reads --header-h too.

**Evidence.** `assets/css/base.css:150-151 (sticky header)`; `assets/css/pages/report.css:185-198 (fixed bar, env(safe-area-inset-bottom))`; `assets/css/pages/multiday.css:34 (max-height: 480px rule)`; `assets/css/pages/series.css:107 (sticky month bar)`; `tools/sitegen/core.py:1734 (viewport content without viewport-fit)`; `docs/IMPLEMENTATION_REPORT.md:845-846`.

**Proposal.** Add `@media (max-width: 759.98px) and (max-height: 500px)` rules only: `.site-h { position: static }` with `--header-h: 0px` on :root (scroll padding and the sub-bars' top follow), `.bbar a { height: 40px; flex-direction: row; gap: 8px }` with body.p-report .site-f padding and the scroll-padding-bottom reduced to match, and `.ser-mnav, .mul-dnav { position: static }` (raise multiday.css:34's 480 to 500). Leave the viewport meta and the env() padding as they are. Relates to REPORT 15.4 point 12. Effort S.

**Files.** `assets/css/base.css`, `assets/css/pages/report.css`, `assets/css/pages/multiday.css`, `assets/css/pages/series.css`, `tools/sitegen/core.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence medium.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.4 point 12 (landscape phone: header and bar take a third of the height)

**Risk.** viewport-fit=cover lets content run under the notch in landscape, so the safe-area paddings must land in the same commit and be checked once on a real iPhone (15.5). The :root --header-h flip must not break the menu's inset or the sticky sub-bars.

**Decision for Eric.** Whether to accept viewport-fit=cover (content extends under the notch and home indicator) for the native-looking bar.

**Review note (condensed; the observation and proposal above are the revised text).** Observation verified: base.css:150 sticky header, report.css:185-186 fixed bar with env(safe-area-inset-bottom), report.css:197 scroll padding, multiday.css:34 the only short-viewport rule (max-height: 480px), series.css:107 sticky month bar with none, core.py:1734 viewport meta without viewport-fit, and IMPLEMENTATION_REPORT.md:845-846 (15.4 point 12) records the landscape case as rated and left, which the finding already cites. The facts hold: sticky 56 px header (base.css:17, 150-151), fixed bar of 56 px links plus 8 px padding with 72 px footer padding (report.css:185-198), no viewport-fit=cover in core.py:1734 so env(safe-area-inset-bottom) is 0, multiday.css:34's 480 px rule, and REPORT 15.4 point 12 rated the landscape case and left it. Mostly reproduces: --header-h is 56px (base.css:17) and the header is sticky (base.css:150); the viewport meta at core.py:1734 has no viewport-fit, so env(safe-area-inset-bottom) in report.css:186 and :197 is 0; multiday.css:34 is the only phone-width short-viewport rule (section.css:284 has one, but only from 960 px wide); IMPLEMENTATION_REPORT.md:845-846 is 15.4 point 12.

#### phone-12. Add a Home row to the phone menu

**Observation.** Below 1140 px (assets/css/base.css:171) the brand name is the only link home, and on phones (< 760 px) the report, multi-day and series pages hide it once the H1 has scrolled under (base.css:195-196) while the app bar that replaces it links to #title (tools/sitegen/core.py:1669). The menu's Site column (core.py:1660-1666; _site/map/index.html) lists Trips, Tick list, Map & archive, PCT, About and Search but not Home, so mid-report on a phone the way home is the footer.

**Evidence.** `tools/sitegen/core.py:1660-1666 (site_rows: main nav + Search)`; `_site/map/index.html menu rows: Trips, Tick list, Map & archive, PCT, About, Search`; `assets/css/base.css:196-197 (body.past-title .site-h .brand hidden)`; `tools/sitegen/core.py:1669 (a.ab-trip href="#title")`.

**Proposal.** Prepend a 'Home' row (a 'home' icon added to tools/lib/icons.py, which has none; aria-current="page" on the home page) to site_rows in core.header; update tests/test_nav.py, whose lines 72, 120 and 131-132 assert the Site column's hrefs and labels. Files: tools/sitegen/core.py, tools/lib/icons.py, tests/test_nav.py (there is no tests/test_core_header.py).

**Files.** `tools/sitegen/core.py`, `tools/lib/icons.py`, `tests/test_nav.py`, `tests/test_ticklist_page.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Risk.** None; one more 64 px row in a panel that already scrolls.

**Review note (condensed; the observation and proposal above are the revised text).** Not built. core.header builds the Site column from main_nav() + Search only (tools/sitegen/core.py, site_rows loop); _site/index.html and _site/map/index.html list Trips, Tick list, Map & archive, PCT, About, Search and no Home. assets/css/base.css:196-197 hides .brand under body.past-title below 760 px, and a.ab-trip links to #title, so mid-report on a phone the way home is the footer. tools/lib/icons.py has no 'home' icon (grep empty). Real and cheap, but two facts in it are wrong. Observation reproduces: base.css:171 shows the nav only from 1140 px; core.py:1660-1666 builds site_rows from main_nav() + Search with no home entry and _site/map/index.html's Site column is Trips, Tick list, Map & archive, PCT, About, Search; base.css:195-196 hides .brand under body.past-title (phones < 760 only); core.py:1669 is a.ab-trip href="#title". icons.py has no 'home' key.

#### phone-13. Title bar with back-to-top on the long index pages

**Observation.** The phone app bar (route glyph + title, tap = back to #title) is emitted only when core.header gets a trip (tools/sitegen/core.py:1667-1670) and base.js observes the H1 only when .ab-trip exists (assets/js/base.js:279-285). Report, multi-day and series pages have it, the PCT journal included (_site/trips/pacific-crest-trail-2024/index.html carries a.ab-trip href="#title"). Trips (about 31 screens of 844 px, phone-trips.jpeg 390×26627 at 1x), Map & archive (about 20, phone-map.jpeg 1170×51048 at 3x), the Ski section (about 12, phone-section-ski.jpeg 1170×30873), the region pages (no .ab-trip in _site/regions/eastern-sierra/index.html) and the tick list have no in-page way back to the top, the search box or the region tabs once the reader is deep in the list; _site/trips/index.html and _site/map/index.html contain no back-to-top link.

**Evidence.** `assets/js/base.js:278-286 (observer only with .ab-trip)`; `tools/sitegen/core.py:1667-1670 (app bar only with a trip)`; `.cache/plan2/shots/phone-trips.jpeg (390×26627 at 1x)`; `.cache/plan2/shots/phone-map.jpeg (1170×51048 at 3x)`; `.cache/plan2/shots/phone-section-ski.jpeg (1170×30873)`; `.cache/plan2/shots/phone-series-pct.jpeg (390×42104)`.

**Proposal.** Generalise the app bar: core.header gains a page_title argument and emits a.ab-page (page title + up-arrow icon, href to the page's H1 id, which exist in the build: #trips-title, #arc-title, #sec-title, #reg-title, #tkl-title) for Trips, Map, the section, region and tick-list pages; base.js observes that H1 (data-ab-title on the heading) with the same 52 px root margin and toggles body.past-title. On Trips point the link at #search (the form is `hidden` until trips.js runs; the bar needs JS anyway). Ship with phone-12, since the brand hides while past the title. Files unchanged. Risk: decide per page module which pages get the bar rather than by a two-screen rule (About is about 3.3 screens at 390 px, the goal page about 2.2).

**Files.** `tools/sitegen/core.py`, `assets/js/base.js`, `assets/css/base.css`, `tools/sitegen/pages/trips.py`, `tools/sitegen/pages/archive.py`, `tools/sitegen/pages/section.py`, `tools/sitegen/pages/region.py`, `tools/sitegen/pages/ticklist.py`.

**Effort.** M. Visitor value 2.3, author value 1, confidence high.

**Risk.** Header markup tests across page modules; the bar must not appear on pages shorter than two screens (About, 404, goal page).

**Review note (condensed; the observation and proposal above are the revised text).** Partly contradicted. core.header emits a.ab-trip whenever it receives a trip, and its docstring says report, multi-day and series pages get it; _site/trips/pacific-crest-trail-2024/index.html contains class="ab-trip" (1 match, href="#title") and the journal also has a sticky month bar (assets/css/pages/series.css:107), so the PCT journal already has an in-page way back to the top and must leave the list. Feasible and specific (it reuses the existing app-bar mechanism; no new dependency, no-JS reading unaffected because the bar is a progressive addition). Evidence checked: base.js:278-286 observes #title only when .ab-trip exists; core.py:1667-1670 emits the bar only with a trip; the four screenshots measure 390x26627, 1170x51048, 1170x30873 and 390x42104 as claimed. Mostly reproduces: core.py:1667-1670 emits the app bar only with a trip; base.js:279-285 observes #title only when .ab-trip exists; screenshot sizes are as cited (trips 390×26627 at 1x ≈ 31 screens, map 1170×51048 at 3x ≈ 20, ski 1170×30873 ≈ 12); _site/trips and _site/map have no back-to-top link; the H1 ids trips-title, arc-title, sec-title, reg-title and tkl-title exist and the five page modules exist.

#### phone-15. Raise the 11 px text floor on phones to 12 px

**Observation.** On phones the map key rows (.keyrow, assets/css/base.css:381-382), every .t-label (base.css:63), the in-map credit tag (.mv-attrib, base.css:344), card tags (base.css:307, archive.css:147, ticklist.css:25), the multi-day day ruler (base.css:501), multi-day tags (multiday.css:107) and the tick list's 'no map' note (ticklist.css:17) are set at 11 px (mono or sans caps), the smallest size on the site and at the floor of iOS's own guidance. Only .t-label and .keyrow step up to 12 px, and only from 760 px (base.css:76, :385), where screens are held farther away, the opposite of what the reading distance suggests; the tags, credit tag, day ruler and note stay 11 px at every width, and multiday.css:229 pins the day-map key to 11 px under 560 px.

**Evidence.** `assets/css/base.css:63 (.t-label 11/14, 12 from 760 at :76)`; `assets/css/base.css:382 (.keyrow 11/14, 12 at :385)`; `assets/css/base.css:344 (.mv-attrib 11px)`; `assets/css/base.css:307, 501 (card tags, day ruler 11px)`; `assets/css/pages/multiday.css:107, 229`; `assets/css/pages/ticklist.css:17, 25`; `phone-report-matterhorn.jpeg (crop: s2) (ROUTE (GPX) · START · END · GPS MAX)`; `phone-bare-ride.jpeg (crop: top) (© OSM · NOT FOR NAVIGATION)`.

**Proposal.** make 12/16 the base of .t-label (base.css:63), .keyrow (:382), .mv-attrib (:344), .tcard-act .tag (:307), .trow-dr span (:501), .mul-tag (multiday.css:107), .gcard-map--none note and .gcard-tags .tag (ticklist.css:17, 25) and .arc-table .tag (archive.css:147); delete the 760 px step-ups at base.css:76 and :385 and the 11 px phone override at multiday.css:229, which would otherwise undo it on the day maps. .keyrow already wraps (base.css:381), so only check at 360 px that no key runs to a third line, and that the in-map .mv-attrib tag still clears the scale bar. Files: assets/css/base.css, assets/css/pages/multiday.css, assets/css/pages/ticklist.css, assets/css/pages/archive.css. Effort S.

**Files.** `assets/css/base.css`, `assets/css/pages/multiday.css`, `assets/css/pages/ticklist.css`, `assets/css/pages/archive.css`.

**Effort.** S. Visitor value 2.3, author value 1, confidence high.

**Risk.** A key row that wraps on 360 px phones; the in-map tag grows by about 10 px in width over the scale bar's corner. No facts change.

**Review note (condensed; the observation and proposal above are the revised text).** Not built. Every cited rule checks out (base.css:63/76 .t-label 11 then 12 from 760; :382/385 .keyrow; :344 .mv-attrib; :307 card tag; :501 day ruler; multiday.css:107 .mul-tag; ticklist.css:17,25) and the change is CSS only, no facts touched, S effort, and it removes two breakpoint steps rather than adding one. Every cited line reproduces: base.css:63 .t-label 11/14 and :76 12 px from 760; :381-382 .keyrow 11/14 and :385 12 px from 760; :344 .mv-attrib 11px; :307 card .tag 11px; :501 .trow-dr span 11px; multiday.css:107 .mul-tag 11px and :229 keyrow 11px under 560; ticklist.css:17 and :25; archive.css:147 .arc-table .tag 11px. The two crops show the key row and the © OSM tag.

#### gap1-06. Guard decorative :hover rules with @media (hover: hover)

**Observation.** The stylesheets carry hover styling on rows, cards, tabs, bars and plain links with no `(hover: hover)` guard anywhere (grep: the only hover media query is section.css:240). Touch browsers keep an element in :hover after a tap until the next tap, so in-page controls that do not navigate keep their hover look: a tapped day chip stays paper-colored among surface siblings (multiday.css:40), a tapped month tab likewise (series.css:114), a month row keeps its fill and underline after a jump (series.css:54-55), a ski tab keeps ink (section.css:232), the cluster ring stays red after the cluster click scroll (base.css:365-366, base.js:190-202), and after Back a row or link can sit highlighted or route-red (base.css:33, 484-485; archive.css:68-69). Never checked on a device (IMPLEMENTATION_REPORT.md:853-855).

**Evidence.** `assets/css/base.css:33`; `assets/css/base.css:298`; `assets/css/base.css:364-368`; `assets/css/base.css:464`; `assets/css/base.css:484-485`; `assets/css/pages/archive.css:68-69`; `assets/css/pages/archive.css:93-94`; `assets/css/pages/section.css:90`; `assets/css/pages/section.css:232`; `assets/css/pages/section.css:240`; `assets/css/pages/series.css:54-55`; `assets/css/pages/series.css:114`; `assets/css/pages/series.css:186`; `assets/css/pages/multiday.css:40`; `assets/css/pages/home.css:40`; `assets/css/pages/home.css:107`; `assets/css/pages/home.css:141`; `assets/css/pages/home.css:175`; `assets/css/pages/trips.css:62`; `assets/css/pages/report.css:130`; `assets/css/pages/report.css:144`; `docs/IMPLEMENTATION_REPORT.md:853-855`.

**Proposal.** Wrap the purely decorative :hover rules listed in the evidence in `@media (hover: hover) { ... }` blocks in base.css and the page stylesheets (build.py:81-86 bundles base.css then pages/*.css as-is, so no tooling change), but split the rules whose selector list mixes :hover with a state that must stay: archive.css:68-69 (`.arc-row a:hover` beside `.arc-row.is-map-hl a`, and the .arc-row-t twin) and section.css:44 (`.sec-seg-a:is([aria-checked="true"], [aria-current="true"])` beside its :hover twin), keeping the .is-map-hl and aria-checked/aria-current declarations outside the media query. Leave :focus-visible rules and the JS-driven .is-hl and .is-map-hl states (base.css:359-368) unconditional. Mouse users see no difference; touch users stop seeing stuck highlights. Check with Chrome's touch emulation on the multi-day day bar (multiday.css:36 and :40) and the PCT month bar (series.css:114), then add a line to docs/DEVELOPING.md's accessibility rules saying hover styling lives under (hover: hover).

**Files.** `assets/css/base.css`, `assets/css/pages/archive.css`, `assets/css/pages/section.css`, `assets/css/pages/series.css`, `assets/css/pages/multiday.css`, `assets/css/pages/home.css`, `assets/css/pages/trips.css`, `assets/css/pages/report.css`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1.7, author value 1, confidence medium.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.5 (Safari, Firefox and a real phone never run)

**Risk.** The stuck-hover behavior is the standard touch-browser behavior, not something observed on this site on a device; forced-colors rules (base.css:732-744) are unaffected.

**Review note (condensed; the observation and proposal above are the revised text).** Observation reproduces: grep of assets/css finds every cited :hover rule at the cited line (base.css:33, :298, :365-366, :464, :484-485; archive.css:68-69, :93-94; section.css:90, :232; series.css:54-55, :114, :186; multiday.css:40; home.css:40, :107, :141, :175; trips.css:62; report.css:130, :144) and the only hover media query in the stylesheets is section.css:240; the day chips sit on a var(--surface) bar (multiday.css:36) and turn var(--paper) on hover (:40); IMPLEMENTATION_REPORT.md:853-855 lists a real phone as not run; forced-colors rules are at base.css:732-745.

#### gap1-08. Add 768, 1024 and 1180 px captures and a touch pass to the review method

**Observation.** the page-load method (docs/DEVELOPING.md:1428-1439) has two profiles only, 390x844 at 3x with touch and 1440x900; the evidence pack for this review holds 1280 and 390 px captures (the review brief (review scratch, not in the repository) lines 90-95); the earlier walks loaded 768 and 1024 only to confirm there was no horizontal scrolling (IMPLEMENTATION_REPORT.md:292) and the before/after capture set is 1440 and 390 (:304). Touch has been emulated, but only on the 390 phone profile and in the history replay on Trips and the Tick list (:752); no coarse-pointer pass has covered the map wiring (pins, lines, rows, clusters) or any tablet width, where every page has its own rules (report.css:23-26, section.css:250-278, archive.css:44-49, series.css:39-42, multiday.css:56-62). Proposal as written, with the review gate's capture set cited as IMPLEMENTATION_REPORT.md:304.

**Evidence.** `docs/DEVELOPING.md:1428-1439`; `docs/IMPLEMENTATION_REPORT.md:286-306`; `docs/IMPLEMENTATION_REPORT.md:853-858`; `assets/css/pages/report.css:21-26`; `assets/css/pages/section.css:250-278`; `assets/css/pages/archive.css:44-49`; `assets/css/pages/series.css:37-45`; `assets/css/pages/multiday.css:55-62`.

**Proposal.** Extend the 'Measuring' section of docs/DEVELOPING.md (around :1428) with a tablet profile: 768×1024 and 1024×768 (iPad), 1180×820 (iPad landscape), touch emulation on, no CPU throttle; capture the single-day report, the multi-day page, the Ski page, map/, one region page and the PCT intro at each width, and run one coarse-pointer walk of the map wiring (tap a pin, a line, a row, a cluster; open and swipe the viewer). Add the same three widths to the review gate's before/after capture set (IMPLEMENTATION_REPORT.md:299 lists 1440 and 390) and to the `.cache/plan2`-style evidence folders future reviews use. Record the first run in docs/WEBSITE_IMPLEMENTATION_LOG.md so gap1-01 to gap1-07 can be verified against pictures rather than cascade arithmetic.

**Files.** `docs/DEVELOPING.md`, `docs/WEBSITE_IMPLEMENTATION_LOG.md`.

**Effort.** S. Visitor value 1, author value 2, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.5 (never run: a real phone, Safari, Firefox)

**Risk.** None to the site; the captures are evidence only and stay out of git (.cache/ is ignored, .gitignore:2).

**Review note (condensed; the observation and proposal above are the revised text).** Partly true, overstated. Mostly reproduces: docs/DEVELOPING.md:1428-1439 is the page-load method with two profiles only (390x844 at 3x with touch, 1440x900); the evidence pack is desktop (1280) and phone (390) captures (the review brief (review scratch, not in the repository) lines 90-95, ls .cache/plan2/shots/); IMPLEMENTATION_REPORT.md:292 records 768 and 1024 only for 'no horizontal scrolling'; the tablet rules cited exist (report.css:23-26, section.css:250-278, archive.css:44-49, series.css:39-42, multiday.css:56-62); .cache/ is ignored (.gitignore:2); :853-858 lists what was not run.

#### gap6-02. Move the menu's Units row above the fold of the open phone menu

**Observation.** In the #menu panel the Units row comes after the Reports list (5 rows) and the Site list (6 rows: Trips, Tick list, Map & archive, PCT, About, Search). With rows of min-height 64 px plus a 1 px rule (base.css:217-218), the panel's 16 px top padding (base.css:212-213), two labels of 16+14+8 px (base.css:215, t-label 11/14), two 1 px list rules and the row's own 24 px margin (base.css:224), the control's top sits about 833 px below the header; the panel is inset: var(--header-h) 0 0 0, i.e. 788 px tall on a 390×844 phone and less in Safari with its toolbars, so a phone reader who opens the menu to find units has to scroll the menu first. On tablets the two-column menu (base.css:226-229) puts it beside the lists, above the fold. phone-12's Home row would add another 65 px. No open-menu capture is in the evidence pack; these are computed from the stylesheet.

**Evidence.** `assets/css/base.css:212-229`; `assets/css/base.css:205`; `tools/sitegen/core.py:1676-1680`; `tests/test_nav.py:130-135`; `tests/test_a11y_static.py:2609`.

**Proposal.** Only if gap6-01 is declined: emit .menu-units first inside .menu nav (a 44 px row 'Units  [MI|KM]' under its own rule, before .menu-c1) so a phone reader sees it without scrolling the menu. From 760 px keep the two-column layout by placing it explicitly: .menu-c1 { grid-column: 1; grid-row: 1 } .menu-c2 { grid-column: 2; grid-row: 1 } .menu-units { grid-column: 2; grid-row: 2 } (no grid-template-areas exist to name). The menu's open handler still focuses the first link (base.js:124), so the focus order and inert handling are unchanged; the switch is reachable with Shift+Tab or in the normal tab order. Update tests/test_nav.py:133-135 (the row now precedes .menu-c1) and tests/test_a11y_static.py:2609 (count unchanged at two). If gap6-01 ships, this finding is void: remove .menu-units instead.

**Files.** `tools/sitegen/core.py`, `assets/css/base.css`, `tests/test_nav.py`, `tests/test_a11y_static.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence medium.

**Risk.** None to content; the menu's focus order and inert handling must still begin at its first row.

**Review note (condensed; the observation and proposal above are the revised text).** Observation verified from the stylesheet and the markup: the menu panel is Reports list (5 rows), Site list (6 rows), then .menu-units (core.py:1676-1678); .menu padding 16px top and inset var(--header-h) 0 0 0 (base.css:212-213) with --header-h 56px below 1200 (base.css:17), .menu-l margin 16px 0 8px (:215), .menu-list border-top 1px (:216), rows min-height 64px + 1px rule (:217-218), .menu-units margin-top 24px (:224): 16+38+1+5x65+38+1+6x65+24 = 833 px to the control, in a 844-56 = 788 px panel on a 390x844 phone, so it is below the fold; the tablet grid (base.css:226-229) does put it beside the lists. The fold arithmetic holds from the stylesheet: --header-h is 56 px (base.css:17), the panel is inset from it (base.css:212), and 16 px padding + two labels + two rules + 11 rows of 65 px (base.css:216-218) + the 24 px margin (base.css:224) put the Units row about 833 px down a 788 px panel.

#### gap6-03. Start in kilometers when the browser's language is not US English

**Observation.** The pre-paint script only honours a stored choice: try{if(localStorage.getItem("units")==="km")…} (core.py:1745), and base.js:20 reads that class on load, so every first-time reader starts in miles and feet whatever their browser's language, and on a phone the control is in the menu (gap6-01, gap6-02). About states 'Distances and heights are shown in miles and feet by default' (about.py:127). The Alps and Haute Route trips and readers abroad are the metric audience; nothing on a phone's first screen shows a kilometer (bare-first-screen.jpeg).

**Evidence.** `tools/sitegen/core.py:1745`; `assets/js/base.js:7-27`; `tools/sitegen/pages/about.py:120-128`; `assets/css/base.css:47-49`; `tests/test_sitecheck.py:763`; `phone-bare-ride.jpeg (first-screen crop)`.

**Proposal.** Eric's decision, flagged as such. Extend the pre-paint script: when no 'units' value is stored and navigator.language is set and does not start with 'en' (case-insensitive), add the km class; base.js:20 then shows the control in the right state and a click still stores the choice (base.js:9). English of any region stays miles (en-GB, en-AU, bare 'en'); every non-English browser starts in km. The no-JS case stays miles (base.css:47-49). Keep About's first sentence as it is (it is true without JavaScript) and extend the .abo-units-how span, which is hidden without JavaScript (about.css:40): 'Browsers set to a language other than English start in kilometers and meters. The MI | KM switch changes every page, and this browser remembers the choice.' Update tests/test_about_units.py (SWITCH constant) and DEVELOPING.md's units rule. tests/test_sitecheck.py:763 needs no change.

**Files.** `tools/sitegen/core.py`, `assets/js/base.js`, `tools/sitegen/pages/about.py`, `tests/test_about_units.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Risk.** A reader with a non-US browser language who wants miles starts in km (one tap, remembered); bare 'en' is treated as US; About's sentence must state the rule truthfully. Uses the existing html.km mechanism and core.U unchanged.

**Decision for Eric.** Whether the site's default should follow the reader's browser language at all, or stay miles and feet for everyone.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible in the one-line pre-paint script (core.py:1745) and base.js:20 already reads the class; navigator.language stays in the browser. But the value is small (4 of 168 trips are in the Alps by region: front matter; the rest are in the western US) and the rule as written misfires for English-speaking regions with mixed usage (en-GB road miles) and for US readers with a non-English browser language.

#### a11y-10. Let controls grow with text zoom and wrap at 320 px

**Observation.** several text-bearing boxes use a fixed height (chip--title 28 px for 13/16 text, .tag 28 px, card tags 22 px, .trx-chip 32 px, .ser-mnav links at --ser-nav-h) so a text-only zoom (Firefox, Android font scaling) overflows them. The compact report rows of map/ and the region pages (.arc-table, archive.css:166-176) already use the short date without a weekday (core.py:1231) and keep date and distance on one nowrap line that, by Geist Mono metrics, needs about 206 of the 208 px a 320 px screen leaves, so they want a browser check rather than a new date form; .rtab--compact (base.css:619-647) is emitted by no page.

**Evidence.** `assets/css/base.css:257, 266, 307`; `assets/css/pages/trips.css:58`; `assets/css/pages/series.css:112`; `assets/css/base.css:621-647`; `docs/DEVELOPING.md:69`.

**Proposal.** swap height for min-height on .chip--title, .tag, .tcard-act .tag, .gcard-tags .tag, .arc-table .tag and .trx-chip (keep the sticky bars' height variables, which scroll margins depend on); verify the arc-table rows at 320 px and at 200 % zoom with the DEVELOPING.md screenshot method and, only if a row overflows, let the distance item wrap below 360 px; delete the dead .rtab--compact block or mark it as unused. Files: assets/css/base.css, assets/css/pages/trips.css, assets/css/pages/ticklist.css, assets/css/pages/archive.css (not tools/sitegen/core.py).

**Files.** `assets/css/base.css`, `assets/css/pages/trips.css`, `assets/css/pages/ticklist.css`, `assets/css/pages/archive.css`, `tools/sitegen/core.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence medium.

**Risk.** The 320 px overflow is computed from font metrics, not seen in a browser; confirm before changing the date format. min-height can add 1 px to a chip if line-height exceeds the old height.

**Review note (condensed; the observation and proposal above are the revised text).** Half true. The fixed heights are real: .chip--title 28 px (assets/css/base.css:257), .tag 28 px (:266), .tcard-act .tag 22 px (:307), .trx-chip 32 px (assets/css/pages/trips.css:58), .ser-mnav a height var(--ser-nav-h) (assets/css/pages/series.css:112); and only browser zoom was ever run (IMPLEMENTATION_REPORT.md:294, '… at 2x'), never text-only zoom. The fixed heights are real: .chip--title 28px (base.css:257), .tag 28px (:266), .tcard-act .tag 22px (:307), .trx-chip 32px (trips.css:58), .ser-mnav a at var(--ser-nav-h) (series.css:112). Swapping height for min-height on the non-sticky chips is S, CSS-only and safe. The fixed-height half reproduces: base.css:257 .chip--title height 28px with 13/16 text, :266 .tag height 28px, :307 .tcard-act .tag height 22px, trips.css:58 .trx-chip height 32px, series.css:112 .ser-mnav a height var(--ser-nav-h) (52/64px at series.css:4-5, with scroll-margin-top depending on it at :133-146), ticklist.css:25 .gcard-tags .tag 22px, archive.css:147 and :212 .arc-table .tag.

#### visual-04. Give year group heads in long lists a readable size

**Observation.** On the Trips page a year boundary is a 12 px caps label (`h2.t-label` '2026' with '58 REPORTS') over a 1 px rule, the only landmark between 58 cards on a 26,000 px page; the Map page's year groups use the same `h3.t-label`. The PCT journal's month heads are 22-24 px and read as chapters; the ski page's season dividers are 12 px too but sit under a season band that already names the season.

**Evidence.** `desktop-trips.jpeg (the 2026 head above the first cards)`; `desktop-map.jpeg (All reports, 2026 group)`; `desktop-series-pct.jpeg (April 2024 month head)`; `tools/sitegen/pages/trips.py:177`; `tools/sitegen/pages/archive.py:358`; `assets/css/pages/series.css:137-139`; `assets/css/pages/section.css:215`; `assets/js/pages/trips.js:348`.

**Proposal.** style the Trips and Map year heads like the journal's month heads with page-scoped rules, because the tick list reuses `.trx-yr-h > h2.t-label` for its region heads and its sorted 'Goals' head (ticklist.py results) and site.css is one bundle: `.p-trips .trx-yr-h h2, .p-archive .arc-yr-h h3 { font: 650 22px/28px var(--sans); font-stretch: 108%; letter-spacing: -0.01em; text-transform: none; }` with 24/30 from 760 (body classes at trips.py:189 and archive.py:389; the Trips page's hidden 'Results' head at trips.py:181 follows, which is wanted). Count meta stays Mono-S, the ink rule stays. Gaps: trips.css:79 already sets 40 px from 760 and archive.css:139 already gives 48 px between year groups, so only the phone value at trips.css:72 (32 px) could rise to 40. No script change: trips.js:348 rewrites only `.trx-yr-n`. Leave the section pages' `.sec-div-t` as it is.

**Files.** `assets/css/pages/trips.css`, `assets/css/pages/archive.css`.

**Effort.** S. Visitor value 2.3, author value 1, confidence high.

**Risk.** Heading levels do not change; tests/test_a11y_static.py reads selectors but pins no size here.

**Review note (condensed; the observation and proposal above are the revised text).** Not built; observation correct, two details of the proposal are off. CSS-only and accurate: trips.py:177 emits h2.t-label, archive.py:358 h3.t-label, the heads are styled at trips.css:73-74 and archive.css:140-141, and trips.js:348 rewrites only .trx-yr-n. Observation reproduces: trips.py:177 (h2.t-label), archive.py:358 (h3.t-label), t-label 11 px / 12 px from 760 (base.css:63, 76), the ink rule (trips.css:73, archive.css:140), '58 REPORTS' for 2026 in the built page on a 26,454-px capture (trips-yearhead crop), month heads 22/28 and 24/30 (series.css:137-139), `.sec-div-t` 12 px (section.css:215), trips.js:348 rewrites only `.trx-yr-n`, and test_a11y_static.py references neither class.

#### visual-17. Tablet landscape: show the full header nav from 1000 px

**Observation.** The main nav appears only from 1140 px (base.css:171), but the two-column desktop grids start at 1000 px (report body rail and write-up report.css:84-88, About about.css:6-11, Map page panel archive.css:39-43, the 12-column footer base.css:246). An iPad in landscape (1024-1180 px) therefore gets desktop content layouts under a hamburger header. The row fits at 1000: the header row is 920 px wide (base.css:151, --m 40 px at base.css:21); the brand column is about 210 px, set by its mono caption (`.brand-c`, 12 px, shown from 760, base.css:155/170) rather than the name; the five 15 px links with 28 px gaps about 310 px, the separator and its gaps about 57 px, Search about 72 px and the units switch about 90 px, roughly 790 px in all.

**Evidence.** `assets/css/base.css:171`; `assets/css/base.css:157-159`; `assets/css/pages/report.css:84-88`; `assets/css/pages/about.css:6-11`; `assets/css/pages/archive.css:39-43`; `assets/css/base.css:246`; `assets/js/base.js:133`; `tests/test_a11y_static.py:2454-2494`; `docs/DEVELOPING.md:70`.

**Proposal.** Move the header's breakpoint to 1000: `@media (min-width: 1000px) { .nav { display: flex; } .menu-btn { display: none; } }` with `.nav, .nav-l { gap: 20px }` at 1000-1139 (28 px from 1140), hide `.brand-c` below 1140 if the row is tight; change the 1140 in base.js:133 (menu closes on resize) to 1000; update the pinned widths in tests/test_a11y_static.py at 2453-2454 (the with-scripting table), 2493-2494 (NS_WIDTHS and its comment) and 2630 (`'flex' if width >= 1140 else 'none'`), and DEVELOPING.md:70. Check 1000, 1024 and 1139 with and without scripting (the no-JS wrap rules, base.css:177-183).

**Files.** `assets/css/base.css`, `assets/js/base.js`, `tests/test_a11y_static.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1.7, author value 1, confidence medium.

**Risk.** A long brand caption plus the units switch could crowd the row at 1000; the static a11y test pins the 1139/1140 pair and must move with it.

**Review note (condensed; the observation and proposal above are the revised text).** All cited breakpoints verified: nav from 1140 (base.css:171), desktop grids from 1000 (report.css:84-88, about.css:6-11, archive.css:39-43, footer base.css:246), base.js:133 closes the menu at >= 1140, tests pin 1139/1140 (tests/test_a11y_static.py:2452-2456 and NS_WIDTHS at 2494), DEVELOPING.md:69-70 states 1140; the no-JS wrap rules are at base.css:177-183. Reproduces: base.css:171 shows .nav and hides .menu-btn only from 1140 px, while the 12-column grids start at 1000 (report.css:84-88 rail + write-up, about.css:6-11, archive.css:39-43 map + side column, base.css:246 footer); base.js:133 closes the menu at innerWidth >= 1140; DEVELOPING.md:70 says 1140; the live header has five links (Trips, Tick list, Map, PCT, About), a separator, Search and MI|KM; .brand-c (base.css:156, shown from 760) and .nav-l (base.css:158, gap 28px) exist; the no-JS wrap rules are base.css:177-183; .wrap at 1000 px with 40 px margins gives the 920 px row.

#### visual-01. Fill photo-less card slots with the route tile, no inset frame

**Observation.** In Recent outings and the Trips grid a photo card runs edge to edge, while a card without a photo shows a bordered --surface box with the 200x152 tile at 64% width inside it; the tile carries its own map-paper rect, so the card reads as a frame inside a frame and visibly lighter than its neighbours (home.css uses 56% for the featured fallback). The goal card already fills its slot with the tile and reads as one map surface. The photo cards themselves (3:2 crop, Mono-S DATE · PLACE, title, inline chip and stats line) are strong and should stay as they are.

**Evidence.** `desktop-home.jpeg (Recent outings, second row: Tahoe Mountain Loop and Ride near McCall tiles beside photo cards)`; `desktop-trips.jpeg (first card rows)`; `desktop-ticklist.jpeg (goal card tile fills its slot)`; `assets/css/base.css:299-300`; `assets/css/pages/home.css:42-43`; `assets/css/pages/ticklist.css:14-15`; `tools/lib/mapkit.py:2322-2341`; `tools/sitegen/core.py:1266-1272`.

**Proposal.** Step 1 (CSS only): in base.css change `.tcard-img--tile` to `background: var(--map-paper); border: 0;` (`--map-paper` is #EEECE6 at base.css:9, the same as the rect render_tile adds at mapkit.py:2335) and set `.tcard-img--tile .gl { width: 100%; height: 100%; object-fit: contain; }` so the 200x152 tile (it carries a viewBox, so it scales) fills the 3:2 grid slot (base.css:314) and the 4:3 row slot (base.css:294) with matching paper bands and reads as one surface; same for `.hom-card-img--tile` in home.css:42-43; extend the `.tcard-img:hover .cover-img { filter: brightness(1.04) }` rule (base.css:298) to the tile. Step 2 (next time Eric runs render.py): add a `card` drawing at 400x267 (3:2) to `GLYPH_SIZES` (core.py:610), render it in render.py with `render_tile` strokes tuned for that size, have `trip_card` (core.py:1269-1271) and the home featured fallback (home.py:114-115) use it, add it to build.py's drawing list at build.py:180 (`for name in ('tile', 'g112', 'g64')`) and to the non-scaling-stroke exception at build.py:130, and list it in DEVELOPING.md:1219-1224. Risk unchanged: until then the 200 px tile is scaled about 1.76x (height-limited) in the 400x267 desktop slot, so its 2.5 px route and contour strokes thicken; keep `.tcard-img--none` unchanged.

**Files.** `assets/css/base.css`, `assets/css/pages/home.css`, `tools/sitegen/core.py`, `tools/render.py`, `tools/lib/mapkit.py`, `tools/build.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 2.7, author value 1.7, confidence high.

**Risk.** Until the render-side card tile exists the 200 px tile is scaled about 1.8x in a 400 px slot, so its 2.5 px route and contour strokes thicken; step 2 needs the internet on the Mac and commits about 168 new SVGs; keep `.tcard-img--none` (the activity disc) unchanged.

**Review note (condensed; the observation and proposal above are the revised text).** Not built and not decided against. Step 1 holds: base.css:299-300 draws the tile at 64% inside a bordered --surface box while ticklist.css:14-15 fills the goal slot; --map-paper (#EEECE6, base.css:9) matches the rect render_tile injects (mapkit.py:2334), so a CSS-only fix is feasible and S. Observation reproduces: base.css:294 (.tcard-img 4:3 row slot), :299-300 (surface box, border, .gl at 64%), :314 (3:2 from 560); home.css:42-43 (56%); ticklist.css:14-15 (goal tile at 100%/100%); mapkit.py:2335 (render_tile adds its own #EEECE6 rect); core.py:1266-1272; the home-mid and trips-top crops show the lighter bordered box with the tile inside it beside edge-to-edge photo cards, and the ticklist crop shows the goal tile filling its slot.

#### visual-11. Section lists: one column header per group, not labels on every row

**Observation.** Every list row on the section pages repeats DIST · GAIN · GPS MAX · MOVING as 12 px labels above its values; the 2025-26 ski season alone prints 88 labels on 22 rows, one extra line per row, where the Map page's table shows the same columns once in a header. The row component (tile, Mono-S meta, title, Data-M values with mono units, day ruler) is right and should stay.

**Evidence.** `desktop-section-ski.jpeg (2025-26 season rows)`; `desktop-map.jpeg (All reports: TRACK · ACTIVITY · TITLE · DATE · DIST MI · GAIN FT · GPS MAX FT header)`; `tools/sitegen/core.py:1066-1090`; `assets/css/base.css:519`; `assets/css/base.css:558-561`; `tools/sitegen/pages/section.py:264`; `tools/sitegen/pages/section.py:395`.

**Proposal.** From 760 px, where the four stat columns are fixed at 120 px (base.css:519), add the labels once to each group divider (`.sec-div` of a ski season, section.py:395, or a hiking/MTB/climbing year, section.py:264): a grid on the divider's right aligned with the rows' text column (200 px tile + 24 px gap per base.css:511-512, then `repeat(4, 120px)`; on the ski page from 960 the `.sec-list` grid is 160 px + 20 px, section.css:266-267), and give the rows' `<dt>` the `.sr` treatment (base.css:39) at ≥ 760 so readers still hear the labels. The header's label set comes from the group's rows: DIST · GAIN · GPS MAX · MOVING for ski, hiking and MTB; DIST · GPS MAX · MOVING for climbing (its rows have three cells, no Pitches today). Only for groups whose rows share one cell set; the Other page mixes flat-water cells (`stats_cells` pace branch, core.py:1083-1088) and keeps per-row labels. Each row loses 16-20 px. No test covers `trip_row` or the section lists today, so add one (a new tests/test_section_page.py, or beside the `stats_cells` tests in tests/test_ticklist_page.py:998-1017).

**Files.** `tools/sitegen/pages/section.py`, `tools/sitegen/core.py`, `assets/css/pages/section.css`, `assets/css/base.css`, `tests/test_section_page.py` (new).

**Effort.** M. Visitor value 2.3, author value 1, confidence medium.

**Risk.** 560-759 uses four equal columns, so the header must stay ≥ 760; at 960-1199 the ski list sits beside the sticky panel with 16 px data (section.css:266-271) and the header has to follow that grid.

**Review note (condensed; the observation and proposal above are the revised text).** Observation verified: _site/ski/index.html 2025-26 season has 22 rows and 88 <dt class="t-label"> (core.py stats_cells emits one per cell); base.css:519 fixes four 120px columns from 760, base.css:514-516 four equal columns at 560-759; .sr exists (base.css:39). Observation reproduces exactly: _site/ski/index.html season-2025-26 has 22 <li> rows and 88 <dt class="t-label"> (Dist, Gain, GPS max, Moving), and _site/map/index.html has one .rtab-h header (Track · Activity · Title · Date · Dist · Gain · GPS max); confirmed in ski-rows and map-table crops of the captures. core.py:1066-1090 is stats_cells, base.css:519 the ≥760 repeat(4, 120px) rule, base.css:558-561 the .rtab-h rule, section.py:264/395 the year and season .sec-div, .sr exists at base.css:39.

#### visual-09. One hover idiom: route red stays on the route

**Observation.** Datum reserves route red for the GPX line and 3 px active bars (DEVELOPING.md:59), yet every plain link, the breadcrumbs, the featured title, the Trips count link, the active-filter chip icons and the activity-tile arrows turn `--route-ink` (`#B8300F`, the darker companion of `--route`, base.css:8) on hover, while cards, rows and tiles hover as ink plus underline and list rows add a surface fill: three idioms for one gesture.

**Evidence.** `docs/DEVELOPING.md:59`; `assets/css/base.css:33`; `assets/css/base.css:146`; `assets/css/pages/section.css:90`; `assets/css/pages/section.css:172`; `assets/css/pages/trips.css:55`; `assets/css/pages/trips.css:62`; `assets/css/pages/home.css:141`; `assets/css/base.css:305`; `assets/css/base.css:484-485`.

**Proposal.** make inline text links hover as ink plus a 1 px underline at 3 px offset (the `.prose a` idiom, base.css:116), scoped to the containers that actually hold plain links in the built pages: `.prose a`, `.hom-also a`, `.hom-reg-n a` (its underline rule is home.css:175; the red comes from base.css:33), `.f-nav a`, `.menu-list a`, `.crumbs a`, the multi-day day links (`.c-day a`, `.mul-di a`, `.mul-st-r a`), `.ser-mnav a` and `.goal-refs a` (already underlined at report.css:209). `.mapcap`, `.f-note` and `.strip-note` carry no links (core.py:722, 1694-1696, 1061), so leave them out. Replace `a:hover { color: var(--route-ink) }` (base.css:33) with ink; set `.crumbs a`, `.sec-feat-t a`, `.sec-ser .shead-t a` and `.trx-count a` to ink plus underline; `.trx-chip:hover .ic` and `.hom-tile:hover .hom-arr` to `--ink`; delete the six remaining `--route-ink` hover rules (base.css:146, section.css:90 and 172, trips.css:55 and 62, home.css:141). Block links keep their own hover (`.trow-a` base.css:484-485, `.rtab-r` 566, `.tcard-img` 298, `.hom-tile` home.css:106-107, `.nav a` 160). The maps' red labels are hardcoded (#B8300F in `.mk-gps`, mapkit.py:60; core.py:647 is the day-label legend swatch), so after this the `--route-ink` token at base.css:8 has no CSS user: delete it or keep it only as a documented value. Note the idiom in DEVELOPING.md:59. Risk unchanged: check the built pages for underlined cards and tiles after the change.

**Files.** `assets/css/base.css`, `assets/css/pages/section.css`, `assets/css/pages/trips.css`, `assets/css/pages/home.css`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1.7, author value 1.3, confidence high.

**Risk.** A too-broad `a:hover` underline would hit block links; check the built pages for underlined cards and tiles after the change.

**Review note (condensed; the observation and proposal above are the revised text).** Not built; the inconsistency is real but one sentence of the proposal is inaccurate. Observation reproduces: DEVELOPING.md:59; base.css:33 global `a:hover` red; base.css:146, section.css:90 and 172, trips.css:55 and 62, home.css:141 (seven route-ink hover rules in all: one replaced, six deleted, consistent with the proposal); the ink-plus-underline idiom at base.css:305 and home.css:106-107; the surface-fill idiom at base.css:484-485 and 566.

#### visual-10. Fold duplicate type, tag and control sizes into named classes

**Observation.** five page-specific lede styles (`.hom-lead` home.css:11, `.sec-intro` section.css:10, `.abo-lead` about.css:17-18, `.nf-line` notfound.css:6, `.ser-lede` series.css:47, the last sans), about ten distinct semibold sans title sizes, nine re-declarations of the `t-label` overline (base.css:559, series.css:140, multiday.css:93 and 111, archive.css:107, report.css:73, home.css:137 and 169, section.css:215), tag heights of 28/22/20 px (base.css:266, 307, multiday.css:106), control heights of 28/32/44/48 px, several selected-state idioms (`[aria-current]`, `[aria-checked]`, `[aria-selected]`: base.css:161-162, 210, 280, 734-737), dead CSS (`.t-h4` base.css:58, listed at DEVELOPING.md:65 but used by no page; `.photos` 455-457; `.prow` 546-554, used only by `core.phone_row` core.py:1246-1252, which only tests/test_report_page.py:2998 calls) and `.abo-dl` (about.css:24-28) duplicating `.dl-leader` (base.css:710-716). None is visible as a defect today, but every later change has to find all of them.

**Evidence.** `assets/css/base.css:58`; `assets/css/base.css:455-457`; `assets/css/base.css:546-554`; `assets/css/base.css:266`; `assets/css/base.css:307`; `assets/css/pages/home.css:11`; `assets/css/pages/section.css:10`; `assets/css/pages/about.css:17-18`; `assets/css/pages/notfound.css:6`; `assets/css/pages/series.css:47`; `assets/css/pages/multiday.css:106-107`; `assets/css/pages/about.css:24-28`; `tools/sitegen/core.py:1246`.

**Proposal.** (1) add `.t-lede` to base.css (serif 17/27 → 19/30 → 20/32, ink-2) and use it for `.hom-lead`, `.sec-intro`, `.abo-lead`, `.nf-line` and `.ser-lede` (the last moves from sans to serif). (2) Replace the nine overline re-declarations with the `t-label` class in the markup, keeping a color override where today's rule is ink (`.mul-st tfoot th`, `.arc-oreg-n`, `.hom-reg-n`, `.sec-div-t`), as `.trx-yr-h .t-label` does at trips.css:74; `.hom-tile-u` is already uppercased by `.hom-tile-c` (home.css:116). (3) Add `.tag--sm` (22 px, 11 px type) and use it in place of base.css:307, ticklist.css:25 and archive.css:147, retiring `.mul-tag` (multiday.py:538). (4) Delete `.t-h4`, `.photos`, `.prow`, `core.phone_row` and its entry in the drawings test at tests/test_report_page.py:2998. (5) `.abo-dl` (about.py:64) → `.dl-leader`. (6) List the surviving classes in DEVELOPING.md:64-66. Compare `_site/assets/site.css` and the built pages before and after; do this before any visible change so diffs stay readable. Risk: thousands of tests pin class names; tests/test_a11y_static.py reads every selector of the bundle (lines 52-56) but does not fail on an unused class, so the deletions are safe there.

**Files.** `assets/css/base.css`, `assets/css/pages/home.css`, `assets/css/pages/section.css`, `assets/css/pages/about.css`, `assets/css/pages/notfound.css`, `assets/css/pages/series.css`, `assets/css/pages/multiday.css`, `assets/css/pages/archive.css`, `assets/css/pages/report.css`, `tools/sitegen/core.py`, `tools/sitegen/pages/section.py`, `tools/sitegen/pages/home.py`, `tools/sitegen/pages/archive.py`, `tests/test_a11y_static.py`, `tests/test_report_page.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1, author value 2, confidence high.

**Risk.** Thousands of tests pin class names and test_a11y_static walks every selector of the bundle; a renamed class without its test update fails CI.

**Review note (condensed; the observation and proposal above are the revised text).** Not built; most claims verified, one sub-step contradicts the design rule and two need qualifying. Parts are verified dead: .t-h4 (base.css:58) is never emitted, .photos (base.css:455-457) has no `class="photos` in tools/, .prow (base.css:546-554) is emitted only by core.phone_row (core.py:1246-1252), which only tests/test_report_page.py:2998 calls, and .abo-dl (about.css:24-28) duplicates .dl-leader (report.py:251, 510). Observation mostly reproduces: `.t-h4` (base.css:58) is used by no page but listed at DEVELOPING.md:65; `.photos` (455-457) unused; `.prow` (546-554) used only by `core.phone_row` (core.py:1246-1252), which only tests/test_report_page.py:2998 calls; `.abo-dl` (about.css:24-28) duplicates `.dl-leader` (base.css:710-716) with small differences; nine overline re-declarations found (base.css:559, series.css:140, multiday.css:93 and 111, archive.css:107, report.css:73, home.css:137 and 169, section.css:215); tag heights 28/22/20 (base.css:266, 307, multiday.css:106); about ten distinct semibold sans sizes.

#### visual-13. A print stylesheet for reports

**Observation.** The bundle has no `@media print` rule (grep of assets/css, 2026-10-13), so a printed report carries the sticky header, the nav, the MI | KM switch, the section row, More like this, the pager and the four-column footer. The column map variant already prints on Letter and A4 in either orientation, since `.mv--col` shows from 560 to 1199.98 px (base.css:339); only a tabloid landscape sheet would get `.mv--wide`.

**Evidence.** `assets/css (grep '@media print': no match, 2026-10-13)`; `assets/css/base.css:150`; `assets/css/pages/report.css:140-146`; `assets/css/pages/report.css:185`; `tools/build.py:80-90`; `assets/css/base.css`; `assets/css/pages/report.css`; `tools/sitegen/core.py:484-527`; `tools/sitegen/core.py:1713-1750`; `_site/trips/matterhorn-peak-west-couloir/index.html`; `assets/css/*.css and assets/css/pages/*.css (no '@media print', grep 2026-10-13)`; `assets/css/pages/report.css:185`; `tools/sitegen/core.py:484-527`; `assets/css/pages/report.css:37-51`; `assets/css/pages/report.css:185-198`; `assets/css/base.css:150`; `assets/css/base.css:212`; `assets/css/base.css:723`; `assets/css/base.css:460-461`; `tools/sitegen/pages/report.py:196`.

**Proposal.** Add `assets/css/print.css` and append it last in `css_bundle` (tools/build.py:80-90, after the page sheets so equal-specificity rules win; the static tests' media matcher knows media types, tests/test_a11y_static.py:257 and 309, so a print block does not alter their screen results): `@media print { .site-h, .site-f, .bbar, .menu, .skip, .rep-actions, .rep-toc, .rep-share, .rep-related, .pager, .copy { display: none } body { background: #fff; color: #000 } .mv--wide, .mv--phone { display: none } .mv--col { display: block } .map, .chart, .strip, .photo, .jrow { break-inside: avoid } .jrow { height: auto; display: grid; grid-template-columns: 1fr 1fr } .prose a[href^="http"]::after { content: " (" attr(href) ")" } }`. Then check Chrome's and Safari's print preview on a report and a multi-day page, in particular that the lazy-loaded photos and day maps (`loading="lazy"`, core.py:617-622 and the gallery) are fetched before printing; if Safari prints them blank, say so in DEVELOPING.md rather than adding script. Note the sheet in DEVELOPING.md. Effort S.

**Files.** `assets/css/print.css`, `tools/build.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Also covers.** report-14, features-13, resilience-02 (merged into this finding).

**Risk.** The `.mv` variants are also gated by width media queries that apply in print; check Chrome's and Safari's print preview on a report and a multi-day page.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: no '@media print' in assets/css or tools/sitegen (grep 2026-10-13); css_bundle concatenates base, mapkit, then the page sheets (tools/build.py:80-90), so an appended sheet wins at equal specificity; every class in the proposal exists in the stylesheet or the built Matterhorn page (.site-h, .site-f, .bbar, .menu, .skip, .rep-actions, .rep-toc, .rep-share, .rep-related, .pager, .copy, .mv--col/wide/phone, .map, .chart, .strip, .photo, .jrow, .prose).

#### qa-10. Give the scrolling filter bands a fade and scroll-into-view

**Observation.** On a 390 px phone the ski season band is 471 px wide (the "2022-23" segment ends at 454 px), hiking's year band 502 px ("2021" at 485) and Other's 651 px; `.sec-band-in` scrolls with `scrollbar-width: none` and has no fade or arrow, so the last seasons and years are cut at the screen edge with nothing saying the row scrolls. The `.tabs-x` rows have a 32 px paper fade and scroll the current tab into view; the band does not, so a deep link like `ski/#season-2022-23` checks a segment that is off-screen.

**Evidence.** `.cache/plan2/qa/p-ski-band.png and p-other-top.png (segments cut at the right edge)`; `evaluate_script on ski/, hiking/, other/ (phone): scrollWidth 471/502/651 vs clientWidth 390, lastVisible false, no '::after' content`; `assets/css/pages/section.css:28-29, 59-61; assets/css/base.css:695-703 ('.tabs-x' fade); assets/js/base.js:73-99 (tab scroll-into-row)`.

**Proposal.** give the band the `.tabs-x` treatment in its own markup: an absolutely positioned paper-fade `::after` on the non-scrolling `.sec-band` wrapper (copy of base.css:698-703), `scroll-snap-type: x proximity` on `.sec-band-in`, and in section.js (or by generalizing the base.js:75-99 block beyond `[role="tablist"]`) the ResizeObserver/scroll handler that toggles `is-scroll`/`is-end`; after a change and after a deep link, bring the checked segment into the row by adjusting `.sec-band-in.scrollLeft` as base.js:85-88 does, not scrollIntoView, so the page itself never moves (base.js:75, section.js:97). Verify on the three bands at 390 px. Files unchanged.

**Files.** `assets/css/pages/section.css`, `assets/css/base.css`, `assets/js/pages/section.js`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Risk.** None.

**Review note (condensed; the observation and proposal above are the revised text).** Verified: `.sec-band-in` scrolls with `scrollbar-width: none` and no fade (section.css:28-29), while `.tabs-x` has the 32 px fade (base.css:698-703) and base.js:73-99 keeps the selected tab in view. Observation reproduces: the top crops of .cache/plan2/qa/p-ski-band.png and p-other-top.png show the segments cut at the right screen edge ('2023-24 4 | 202…' and 'Rafting 2 | [icon]') with no fade; section.css:28-29 gives `.sec-band-in` overflow-x: auto with the scrollbar hidden and 59-61 run it edge to edge on phones; section.css has no `::after`/fade for the band; section.js:97-105 applies a deep-link key without moving the band; base.css:698-703 and base.js:75-99 are the `.tabs-x` treatment.

#### copy-13. One capitalization for 'Full track, not trimmed' in every caption

**Observation.** The report caption reads 'As recorded on Dec 11, 2021 · full track, not trimmed · North up · Terrain: AWS Terrain Tiles · …' (report.py:155-168; the lowercase item sits between two capitalized ones); section.py:25 FULL_TRACK, series.py:178 ('full tracks, not trimmed') and multiday.py:369 repeat it lowercase, while map/ and region captions say 'Pins mark each start and link to the report · Full tracks, not trimmed · North up' (archive.py:229). Five copies of one phrase, two spellings.

**Evidence.** `tools/sitegen/pages/report.py:155-168`; `tools/sitegen/pages/section.py:25`; `tools/sitegen/pages/series.py:178`; `tools/sitegen/pages/multiday.py:369`; `tools/sitegen/pages/archive.py:229`; `_site/trips/back-to-clipless/index.html (map caption text)`.

**Proposal.** One constant in core (FULL_TRACK = 'Full track, not trimmed', FULL_TRACKS for the plural) used by all five callers, and a static test in tests/test_a11y_static.py or a new tests/test_copy.py that every caption item passed to core.map_caption starts with a capital letter or a digit.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/section.py`, `tools/sitegen/pages/series.py`, `tools/sitegen/pages/multiday.py`, `tools/sitegen/pages/archive.py`, `tests/`.

**Effort.** S. Visitor value 1, author value 1, confidence high.

**Risk.** None.

**Review revision (applies on top of the text above).** Same observation. Proposal: move section.py:25's FULL_TRACK to core (FULL_TRACK = 'Full track, not trimmed', FULL_TRACKS = 'Full tracks, not trimmed') and use it at report.py:167, section.py:95, series.py:178, multiday.py:369 and archive.py:229; add one test (tests/test_a11y_static.py or a new tests/test_copy.py) that every item passed to core.map_caption starts with a capital letter or a digit. Risk: tests/test_report_page.py asserts the lowercase form about 15 times (lines 1262-1374, 2727) and tests/test_region_page.py:137,1436 the capitalized one; all must be updated in the same commit. Effort S.

**Review note (condensed; the observation and proposal above are the revised text).** Evidence verified: report.py:167 appends 'full track, not trimmed' between 'As recorded on ...' and 'North up'; section.py:25 FULL_TRACK (used at section.py:95); series.py:178 'full tracks, not trimmed'; multiday.py:369; archive.py:229 'Full tracks, not trimmed'. Feasible and S.

#### copy-20. Keep the tick list's public empty state free of shell commands

**Observation.** When no goal exists, tick-list/ renders 'No goals yet. Add one with python3 tools/ticklist.py add.' (ticklist.py:140) on the public page, while ticklist.js shows 'No goals yet.' for the empty scope (ticklist.js:90-91). Today one goal exists so the line is unseen; it will show the day the last goal is completed or archived and the page goes empty.

**Evidence.** `tools/sitegen/pages/ticklist.py:138-141`; `assets/js/pages/ticklist.js:87-91`; `_site/tick-list/index.html (1 GOAL)`.

**Proposal.** Public text 'Nothing on the list yet.' in ticklist.results; the command belongs in docs/TICK_LIST_GUIDE.md and the tool's own output. Reuse the same sentence for ticklist.js NONE.all. Update tests/test_ticklist*.py.

**Files.** `tools/sitegen/pages/ticklist.py`, `assets/js/pages/ticklist.js`, `tests/`.

**Effort.** S. Visitor value 1, author value 1, confidence high.

**Risk.** None.

**Review note.** Kept as written by all three skeptics.

#### gap6-07. Footer: label AIARE 2 the way About already does

**Observation.** The footer's Mono-S line reads BASED IN LAKE TAHOE · AIARE 2 on every page (core.footer, core.py:1686-1698, string at :1697); About labels the same fact 'Avalanche training: AIARE 2' (about.py:54). A first-time reader meets the bare acronym in every footer before reaching About; no test pins the footer line (grep AIARE / BASED IN in tests/: none).

**Evidence.** `tools/sitegen/core.py:1686-1698`; `tools/sitegen/pages/about.py:54`.

**Proposal.** Change the footer item to nb('AVALANCHE TRAINING: AIARE 2'), the About page's own label, so no new fact is written; or make the item a link to about/ with that text. One string in core.footer.

**Files.** `tools/sitegen/core.py`.

**Effort.** S. Visitor value 1, author value 1, confidence high.

**Risk.** None; the wording is Eric's own from About.

**Review note.** Kept as written by all three skeptics.

#### a11y-03. Give the home region name link a real 24 px box

**Observation.** The Lake Tahoe / Eastern Sierra names under 'Where I've been' are 16 px high inline-blocks whose 44 px hit area is a ::before pseudo-element; Lighthouse measures the element's own rects (118.5×16 px) and fails target-size, the second of the two home-page failures. Pseudo hit areas work for fingers but never satisfy the audit.

**Evidence.** `assets/css/pages/home.css:170-174`; `.cache/plan2/lh-home/report.json (audit target-size: div.hom-reg > div.hom-reg-h > h3.hom-reg-n > a, 118.5px by 16px)`; `tests/test_a11y_static.py:34, 3290-3294`; `docs/IMPLEMENTATION_REPORT.md:670-674`.

**Proposal.** Replace the ::before hit area on .hom-reg-n a with padding that the element itself owns and negative margins that cancel it: .hom-reg-n a { display:inline-block; padding-block:14px; margin-block:-14px; position:relative; z-index:1 } (box 44 px, layout unchanged). Then update the P5/R3 assertions in tests/test_a11y_static.py that expect the pseudo-element. Apply the same to the two other pseudo-only targets the report lists (short region crumb, 'Open the map' at 1200 px) only if the audit flags them.

**Files.** `assets/css/pages/home.css`, `tests/test_a11y_static.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Already known.** the review brief's Lighthouse line (review scratch, not in the repository); docs/IMPLEMENTATION_REPORT.md 14.6 'small things'; design map section 9

**Risk.** Negative margins on an inline-block can change line-box height in some engines; compare the home capture before and after at 390 and 1280 px.

**Review note.** Kept as written by all three skeptics.

#### a11y-08. Nest year-group rows one heading level under their year

**Observation.** On Hiking and Mountain biking, 'More hikes/rides' is an H2, each year an H3 (section.py:263-264), and every row's title is also an H3 (core.trip_row always writes <h3>, core.py:1192), so screen-reader heading navigation reads '2026, Tallac, PEAK BAGGING SZN, ..., 2025, Green Creek ...' as siblings. Other has no year groups and the Ski page nests correctly because its seasons are H2s (section.py:394-395). DEVELOPING.md:96 asks for headings in order.

**Evidence.** `_site/hiking/index.html (H2 More hikes → H3 2026 → H3 Tallac … → H3 2025)`; `tools/sitegen/pages/section.py:263-264`; `tools/sitegen/pages/section.py:394-395`; `tools/sitegen/core.py:1192`; `docs/DEVELOPING.md:96`.

**Proposal.** Give core.trip_row a level parameter (default 3), pass it through section.row() and call row(..., level=4) from section.year_groups (section.py:266) so rows under a year are H4 (keep class t-h3 for the look); or promote the year heads to H2 like the ski seasons and drop the 'More hikes' H2 wrapper. Add a heading-order assertion to the fixture walk in tests/test_a11y_static.py (see a11y-11). Files: tools/sitegen/core.py, tools/sitegen/pages/section.py, tests/test_build_site.py, tests/test_report_page.py, tests/test_a11y_static.py.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/section.py`, `tests/test_a11y_static.py`, `tests/test_build_site.py`.

**Effort.** S. Visitor value 1.3, author value 1, confidence high.

**Risk.** Tests that locate rows by <h3 class="trow-t"> need the tag made flexible; no visual change.

**Review note (condensed; the observation and proposal above are the revised text).** Partly wrong scope. Verified on the built pages: hiking/ and mountain-biking/ have H2 'More hikes'/'More rides' then year H3s (2026, 2025, 2023, 2022, 2021 as h3.sec-div-t) with every row also an H3 (core.trip_row writes <h3 class="t-h3 trow-t">, core.py:1192; section.py:263-264 writes the year as <h3>), so years and rows are heading siblings. Confirmed in the build: _site/hiking/index.html reads H2 'More hikes' → H3 2026 → H3 row titles → H3 2025, from section.py:263-264 (year H3) and core.py:1192 (row H3), while the Ski page nests under H2 seasons (section.py:394-395). Cheap and real for heading navigation. Reproduces for Hiking and Mountain biking: _site/hiking/index.html reads H2 'More hikes' → H3 '2026' → H3 'Tallac', 'PEAK BAGGING SZN', ... → H3 '2025' (5 sec-year sections) and _site/mountain-biking/index.html the same under 'More rides'; section.py:263-264 writes the year head as <h3 class="sec-div-t">, section.py:394-395 the ski seasons as <h2>, core.py:1192 always <h3 class="t-h3 trow-t">; DEVELOPING.md:96 asks for headings in order.

#### a11y-04. Keep activity colors in forced-colors mode wherever they key a map

**Observation.** Only .arc-legend .disc opts out of forced colors. The same inline-styled discs appear in the home region key (home.py:263), the section-page head (section.py:123), the About and 404 activity rows, the phone menu, and the explorer/map filter chips' swatches (trips.py:115); in Windows High Contrast their backgrounds are erased while the SVG maps beside them keep the activity colors, so the key no longer matches the map. The PCT month-index bars (.ser-rl, background-colored) vanish too.

**Evidence.** `tools/sitegen/core.py:378-381`; `tools/sitegen/pages/home.py:263`; `tools/sitegen/pages/section.py:123`; `tools/sitegen/pages/trips.py:114-116`; `assets/css/pages/archive.css:58`; `assets/css/base.css:733-744`; `tools/sitegen/pages/series.py:209-211`; `assets/css/pages/series.css:61-63`.

**Proposal.** In the @media (forced-colors: active) block of base.css add `.hom-rkey .disc, .fchip .chip-sw { forced-color-adjust: none; }` (the home region key, home.py:263, and the explorer's filter chips whose swatches key the map view's activity colors, trips.py:114-116). Leave the section-head disc, the title chip swatch, the menu, About and 404 discs forced: each sits beside its word and keys no map. In series.css add `.ser-rl i { forced-color-adjust: none; outline: 1px solid CanvasText }` under forced colors so the write-up/track-only bars survive. Style the dimmed month links with whichever class a11y-07 settles on (today `.ser-mnav a[aria-disabled="true"]`, series.css:119-120) in GrayText there. Check with Chrome's forced-colors emulation as Phase 4 did; record the rule in DEVELOPING.md beside lines 61-62. Effort S.

**Files.** `assets/css/base.css`, `assets/css/pages/series.css`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1.3, author value 1, confidence medium.

**Risk.** Opting a swatch out of forced colors must never be the only cue: every chip already carries icon + word, so the rule in DEVELOPING.md:61-62 holds.

**Review note (condensed; the observation and proposal above are the revised text).** Confirmed: only assets/css/pages/archive.css:58 opts a disc out of forced colors; core.disc (core.py:378-380) and the chip swatch (core.py:346) are inline backgrounds that forced colors erase, and base.css:733-744 has no rule for them; .ser-rl bars are background-only (series.css:61-63). Cheap and safe.

#### a11y-05. Speak units in full and in the chosen unit system

**Observation.** core.table_row already adds screen-reader text ('miles', 'feet') to its numbers (core.py:1224-1229), but the Mono-S stats lines on cards and phone rows ('12.8 MI · 5,302 FT GAIN', core.py:292-306 and 1152-1166), the stat cells' and series day stats' unit spans (' mi', ' ft': core.py:249, 255, 1073-1076; series.py:345-347) and the units switch ('MI' / 'KM' buttons, core.py:1480-1483) carry only abbreviations. The map's aria-label is a fixed miles/feet string ('Map of ..., out and back, 12.8 miles, high point 11,952 ft', built by render.aria_for at tools/render.py:178-186) and the speed chart's says 'in miles per hour' (mapkit.py:2470) even when the reader has switched to KM; the elevation profile's label ('Elevation profile of <title>', render.py:285, 311) names no unit.

**Evidence.** `tools/sitegen/core.py:231-236`; `tools/sitegen/core.py:292-306`; `tools/sitegen/core.py:1152-1166`; `tools/sitegen/core.py:1224-1229`; `tools/sitegen/core.py:1480-1483`; `_site/trips/matterhorn-peak-west-couloir/index.html (svg role=img aria-label='Map of …, out and back, 12.8 miles, high point 11,952 ft')`; `tools/lib/mapkit.py:2470`; `assets/js/base.js:15-18`.

**Proposal.** Add core.unit_word(abbr) returning '<span aria-hidden="true">MI</span><span class="sr">miles</span>' (mi/km/ft/m/mph) and use it in U(), plain_stats, row_stats_line, series.stats_dl and the units control (aria-label="MI: miles and feet" / "KM: kilometers and meters" keeps the visible text in the name). For the static SVG labels, render both systems ('12.8 miles / 20.6 km, high point 11,952 ft / 3,643 m') in render.aria_for (tools/render.py:178-186) and in mapkit.render_speed_chart's label (mapkit.py:2470); this rewrites committed rendered/ fragments and needs a render.py run on Eric's Mac (VERSION bump at render.py:31), so schedule it with the next map re-render rather than alone. Files: tools/sitegen/core.py, tools/sitegen/pages/series.py, tools/render.py, tools/lib/mapkit.py, tests/test_about_units.py, tests/test_a11y_static.py.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/series.py`, `tests/test_a11y_static.py`, `tests/test_about_units.py`.

**Effort.** M. Visitor value 1.7, author value 1, confidence medium.

**Risk.** Facts-only rule: the added words are unit names, never values. The aria-label change touches committed rendered/ assets and needs render.py (internet, Mac only). Keep the sr spans out of the search index text.

**Review note (condensed; the observation and proposal above are the revised text).** Partly done. Already present: core.table_row speaks units and labels ('Distance', 'miles'/'kilometers', 'about', 'none') via .sr spans (core.py:1220-1229, 1241), and the units switch announces 'Showing kilometers and meters' / 'Showing miles and feet' through the #units-live region when changed (base.js:15-18, 26). The HTML half is confirmed and worthwhile: core.U (core.py:231-236) emits bare abbreviations, plain_stats and row_stats_line write 'MI'/'FT GAIN' (core.py:292-306, 1152-1166), the units switch is 'MI'/'KM' (core.py:1480-1483), while table_row already speaks 'miles'/'feet' (core.py:1224-1229). Observation mostly reproduces: core.table_row adds sr unit words (core.py:1224-1229); plain_stats and row_stats_line write 'MI' / 'FT GAIN' only (core.py:292-306, 1152-1166); the stat cells and series.stats_dl use bare ' mi' / ' ft' spans (core.py:249, 255, 1073-1076; series.py:345-347); units_control is 'MI' / 'KM' buttons (core.py:1480-1483); base.js:15-18 announces the switch; _site/trips/matterhorn-peak-west-couloir/index.html has aria-label="Map of ..., out and back, 12.8 miles, high point 11,952 ft" and mapkit.py:2470 hard-codes 'in miles per hour'.

#### a11y-15. Add a prefers-contrast: more block for the small gray type

**Observation.** Measured ratios: --ink-2 on paper 8.22:1, on surface 8.89, on sunk 7.44; --ink-3 on paper 4.93, on surface 5.33, on sunk 4.47, on profile-fill 4.18; --rule-strong borders on paper 3.05. So every text pair passes AA, but the workhorse 11-12 px caps labels (t-label, t-mono-s, keyrow, crumbs, 79 + 55 emitters) sit just above 4.5:1 in ink-3, chart axis labels in #66686D would fall under 4.5 wherever they cross the fill, and the control borders are at the 3:1 floor. Activity colors never carry text (ski 3.13:1 on paper appears only on 14-16 px icons beside a word).

**Evidence.** `assets/css/base.css:5-10, 62-66`; `tools/lib/mapkit.py:59, 68, 83`; `assets/css/base.css:275-276, 320-321`; `contrast ratios computed in this review from the token values`.

**Proposal.** Add to base.css: @media (prefers-contrast: more) { :root { --ink-3: var(--ink-2); --rule-strong: #5F5D57; } .pf-ax, .mk-lbl { fill: var(--ink-2); } } so all Mono-S/label text, control borders and the chart/map axis labels step up without touching the default design. The .pf-ax/.mk-lbl override works today because the rendered fragments carry classes only and their rules come from mapkit.MAP_CSS, which build.py:81-85 bundles into site.css; put the override in MAP_CSS (mapkit.py) or base.css, no re-render needed. Two places cannot follow page CSS: the glyph/tile SVGs served as <img> (build.py:120-134 inlines their rules into each file) and the key-row symbols with inline hex at core.KEY_SYMBOLS (core.py:649-655), which would need classes; state both limits in DEVELOPING.md. Leave --route alone (it colors only the nav/tab accent bars; the track's red is substituted at build time) and leave the default palette as is. Files: assets/css/base.css, tools/lib/mapkit.py, tools/sitegen/core.py (optional, KEY_SYMBOLS), docs/DEVELOPING.md.

**Files.** `assets/css/base.css`, `tools/lib/mapkit.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Already known.** design map section 8.1 item 2 (color literals outside the tokens)

**Risk.** Hex literals inside rendered SVGs cannot follow the media query without a re-render; state that limit in DEVELOPING.md.

**Review note (condensed; the observation and proposal above are the revised text).** The ratios check out against the tokens at base.css:5-10 (ink-2 on paper 8.22, ink-3 on paper 4.93, on surface 5.33, on sunk 4.47, rule-strong on paper 3.05, computed in this review), and no prefers-contrast block exists (only forced-colors at base.css:733). A three-token override is S, CSS-only and leaves the default design untouched, so it is cheap for a public journal read on phones with 'Increase contrast' on. The ratios reproduce exactly from the tokens at base.css:5-9 (ink-2 on paper/surface/sunk 8.22/8.89/7.44; ink-3 4.93/5.33/4.47 and 4.18 on --profile-fill; rule-strong 3.05; ski 3.13), the fill colors at mapkit.py:59 (.mk-lbl) and :68 (.pf-ax) are #66686D, :83 is the phone .pf-ax size, .fchip and .btn borders use --rule-strong (base.css:275-276, 320-321), and tools/sitegen has 55 t-label and 79 t-mono-s emitters.

#### qa-01. Silence the generated meta-line dot for screen readers

**Observation.** Every `.ml` meta line draws its separator with `.ml > .mi::before { content: "·" }` and also carries a visually hidden ", " per item. Chrome exposes the generated dot in the accessibility tree, so the home card links are described as "· SAT, JAN 17, 2026 · , SAWTOOTH RIDGE" and the Trips head reads "· 167 REPORTS · , 15 REGIONS · , 2021-2026": two separators per item, one of them a stray dot before the first item.

**Evidence.** `accessibility snapshot of https://esichak.github.io/personal-website/ (link "Matterhorn Peak - West Couloir" description "· SAT, JAN 17, 2026 · , SAWTOOTH RIDGE")`; `.cache/plan2/qa/snap-trips-filtered.txt lines 25-30 (StaticText "·" then "," before each item)`; `assets/css/base.css:101 (the '::before' dot) and :108 (its .ml--end repositioning)`; `tools/sitegen/core.py:275 (the sr-only ", ")`.

**Proposal.** add the alternative-text form `content: "·" / "";` after the existing declaration in `.ml > .mi::before` (base.css:101); the `.ml--end > .mi::before` rule at :108 only repositions and inherits the content, so it needs no change unless it is given its own `content`; apply the same `/ ""` form to the compact-table dot at base.css:643. Everything else as proposed.

**Files.** `assets/css/base.css`.

**Effort.** S. Visitor value 1.3, author value 1, confidence high.

**Risk.** None for sighted visitors; engines without the slash syntax keep reading the dot as today.

**Review note (condensed; the observation and proposal above are the revised text).** Not built, observation true. assets/css/base.css:101 is `.ml > .mi::before { content: "·"; ... }` with no alternative text; tools/sitegen/core.py:275 adds the sr-only ', ' per item; .cache/plan2/qa/snap-trips-filtered.txt lines 25-30 show StaticText '·' before every item including the first. Real and cheap. The dot is drawn by `.ml > .mi::before { content: "·" }` at assets/css/base.css:101 (not 99) and the sr-only ', ' is at tools/sitegen/core.py:275 as cited. Reproduces: assets/css/base.css draws the dot with `.ml > .mi::before { content: "·" }` and `.ml--end > .mi::before`, tools/sitegen/core.py:275 adds `<span class="sr">, </span>` before every item but the first, `.sr` is clipped at base.css:39, .cache/plan2/qa/snap-trips-filtered.txt lines 25-30 show StaticText "·" then "," per item with a stray "·" before "167 REPORTS", and .cache/plan2/qa/snap-p-home.txt line 40 (review scratch, not in the repository) has the Matterhorn link description "· SAT, JAN 17, 2026 · , SAWTOOTH RIDGE".

#### a11y-12. Run and record a VoiceOver pass per page type

**Observation.** every phase entry of the log (docs/WEBSITE_IMPLEMENTATION_LOG.md:87, 173, 272, 356, 476, 652) and the report (docs/IMPLEMENTATION_REPORT.md:242-243, 652, 853-856) say screen readers were never run; the four region-map entries of 2026-10-12/13 (log :1007, 1076, 1130, 1183) list Safari, Firefox and a real phone as not run. All accessibility verification so far is static text checks (tests/test_a11y_static.py on a synthetic fixture), Lighthouse and Chrome emulation. Eric's Mac and iPhone ship VoiceOver, and a VoiceOver pass in macOS Safari is also the Safari test the report lists as missing.

**Evidence.** `docs/IMPLEMENTATION_REPORT.md:853-855`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:1007, 1076, 1130, 1183 (via the review's history map, review scratch)`; `docs/DEVELOPING.md:1428-1439`.

**Proposal.** Add docs/CHECKING_WITH_A_SCREEN_READER.md: a 20-minute script for VoiceOver on macOS Safari and iOS (rotor by headings and landmarks on home, trips/, a report, the Haute Route, the PCT page, map/; the explorer with keyboard only; opening and closing the photo viewer; the phone menu; the units switch; the MI/KM live announcement), with a table to record what was heard and the date. Run it once now, log the result in WEBSITE_IMPLEMENTATION_LOG.md, and repeat it in the review gate of each later phase. No code; the findings feed a11y-02/05/07/14.

**Files.** `docs/CHECKING_WITH_A_SCREEN_READER.md`, `docs/WEBSITE_IMPLEMENTATION_LOG.md`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1.7, author value 2, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.5

**Risk.** Only Eric can run it (a Claude Code session cannot drive VoiceOver); the plan should schedule it as his step with the script ready.

**Review note (condensed; the observation and proposal above are the revised text).** Observation holds but two of the three evidence citations do not say what is claimed. docs/IMPLEMENTATION_REPORT.md:853-856 (section 15.5) does list 'screen readers' among what was not run, as do :242-243 and :652.

#### ia-13. One vocabulary for Reports, Trips, Map and PCT across header, crumbs and footer

**Observation.** The same destinations carry different names: header "Map" vs menu, footer and page title "Map & archive"; header "PCT" vs the page "Pacific Crest Trail 2024"; the crumb root "Reports" links to the home page on section, report and region pages, while the header calls the explorer "Trips" and the menu and footer column named "Reports" holds the five activities; the 404 describes Trips as "SEARCH AND FILTER" and Map & archive as "ALL 167 REPORTS".

**Evidence.** `tools/sitegen/core.py:1618-1624 (labels Trips, Tick list, Map, PCT, About)`; `tools/sitegen/core.py:1663-1666 (menu word 'Map & archive' for key map)`; `tools/sitegen/core.py:1686-1698 (footer columns Reports / Site)`; `tools/sitegen/pages/section.py header() and tools/sitegen/pages/report.py title_block() (crumb 'Reports' -> home)`; `tools/sitegen/pages/notfound.py:30-38`; `tools/sitegen/core.py:1618-1624`; `tools/sitegen/core.py:1663`; `tools/sitegen/core.py:1673`; `tools/sitegen/core.py:1686-1698`; `tools/sitegen/pages/section.py:118`; `tools/sitegen/pages/region.py:68`; `tools/sitegen/pages/report.py:113`; `tools/sitegen/pages/home.py:166-171`; `tools/sitegen/pages/notfound.py:35`; `_site/ski/index.html (crumb <a href="../">Reports</a>)`.

**Proposal.** Settle the words as core.py constants and apply them: header and menu/footer both 'Map & archive' (or rename the page and H1 'Map'); PCT_LABEL 'PCT 2024' or 'PCT journal'; the menu and footer column 'Reports' becomes 'By activity'; the 404's two lines use the same words. Update tests/test_nav.py:72,132 and tests/test_a11y_static.py. Effort S. Separately, as a decision for Eric: retarget the crumb root 'Reports' (home) to 'Trips' (trips/), which changes a documented target on every section, report and region page (DEVELOPING.md:1003-1004) and must pass the crumb hit-area test (tests/test_a11y_static.py:3048; 'TRIPS' is about 38 px at the crumbs' 12 px mono, near the 36 px rule at DEVELOPING.md:1101-1103); with it, M.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/section.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/region.py`, `tools/sitegen/pages/notfound.py`, `tests/test_nav.py`, `tests/test_report_page.py`, `tests/test_region_page.py`.

**Effort.** S. Visitor value 2.3, author value 1.3, confidence high.

**Also covers.** copy-10 (merged into this finding).

**Risk.** Changing the crumb root target from home to trips/ changes a documented link target on 180 pages; keep the home link in the brand. Copy rules in DEVELOPING.md (no copy invented) are respected since these are labels of existing pages.

**Decision for Eric.** The words themselves: Map vs Map & archive; PCT vs PCT journal; whether the crumb root is Trips or Home

**Review note (condensed; the observation and proposal above are the revised text).** The label split is real and the fix is S: header 'Map' (core.py:1619) against menu and footer 'Map & archive' (core.py:1663, :1686) and the page title/H1 (_site/map/index.html); PCT_LABEL 'PCT' (core.py:38) against the page's 'Pacific Crest Trail 2024'; the menu and footer column 'Reports' (core.py:1686) holding the activities; the 404's two descriptions (notfound.py:35-38).

#### copy-14. Name the open menu button and expand 'PCT' for assistive tech

**Observation.** The menu button is aria-label="Menu" (core.py:1676) and base.js only flips aria-expanded and the icon (base.js:122-128), so an open menu's close control is still announced 'Menu' (report section 12 decision 10). The nav item 'PCT' (core.py:36-37 PCT_LABEL) carries no expansion anywhere; the menu row gives it the hiking icon and the same three letters (core.py:1659-1664).

**Evidence.** `tools/sitegen/core.py:36-37`; `tools/sitegen/core.py:1659-1664`; `tools/sitegen/core.py:1676`; `assets/js/base.js:101-134`; `docs/IMPLEMENTATION_REPORT.md:516-517`.

**Proposal.** base.js sets aria-label 'Close menu' when opening and 'Menu' when closing (the visible icon already changes). Give the PCT link an aria-label that contains its visible text ('PCT journal' or 'PCT: Pacific Crest Trail journal') in main_nav/header, or change PCT_LABEL to 'PCT journal' if Eric prefers it visible. Tests: tests/test_a11y_static.py and the header tests.

**Files.** `assets/js/base.js`, `tools/sitegen/core.py`, `tests/test_a11y_static.py`.

**Effort.** S. Visitor value 1.3, author value 1, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 12 decision 10 (menu button name)

**Risk.** aria-label must include the visible text (Lighthouse label-content-name-mismatch).

**Decision for Eric.** Whether the nav shows 'PCT' or 'PCT journal'.

**Review revision (applies on top of the text above).** Observation as written. Proposal: (1) PCT: give the header link and the menu row (core.py:1622, 1659-1664) an aria-label that contains the visible text, 'PCT journal', or change PCT_LABEL to 'PCT journal' if Eric prefers it visible (tests/test_nav.py:66,72,132 then change). (2) Menu button: present as Eric's decision 10, with the trade-off stated: aria-expanded already announces open/closed, so the current 'Menu' name is valid; switching the label to 'Close menu' while open is an alternative some screen-reader users find clearer and others find confusing. Tests: tests/test_a11y_static.py for whichever he picks. Effort S. Risk: an aria-label must contain the visible text (Lighthouse label-content-name-mismatch).

**Review note (condensed; the observation and proposal above are the revised text).** Evidence verified: core.py:1676 aria-label="Menu" with aria-expanded; base.js:121-128 toggles aria-expanded only; core.py:38 PCT_LABEL = 'PCT' with no expansion in main_nav (core.py:1620-1622) or the header (core.py:1649); IMPLEMENTATION_REPORT.md:516 decision 10 already lists the open menu button's name as Eric's decision.

#### copy-11. Make the five activity names parallel ('Backcountry Ski' among gerunds)

**Observation.** content.py:19-23 labels the activities 'Backcountry Ski', 'Climbing', 'Hiking', 'Mountain Biking', 'Other'. The ski label reaches the menu, chips, the section H1 and <title> 'Backcountry Ski trip reports · Eric Sichak' (section.py:534), the home tiles and About rows, and lower-cased into descriptions: '51 backcountry ski trip reports' (_site/ski/) and '(backcountry ski, climbing, hiking, mountain biking, paddleboarding and rafting)' (_site/regions/lake-tahoe/, region.py:154-156). The tagline itself says 'Backcountry skiing' (core.py:24). 'Other trip reports · Eric Sichak' (_site/other/) is the one title that names no activity.

**Evidence.** `tools/lib/content.py:17-23`; `tools/sitegen/core.py:24`; `tools/sitegen/pages/section.py:534`; `tools/sitegen/pages/region.py:154-156`; `_site/ski/index.html (<title> and meta description)`; `_site/regions/lake-tahoe/index.html (meta description)`; `_site/other/index.html (<title>)`.

**Proposal.** Eric's decision: if he wants parallel names, change the ski label in both content.py:18 (ACTIVITIES) and core.py:36 (NAV) to 'Backcountry Skiing' (URLs and the 'ski' folder unchanged), leave tools/lib/strava.py:8 alone (it is Strava's sport-type name), update the 10 label assertions in tests/ and the two JS harnesses, and check the derived strings (section.MORE 'More ski tours' at section.py:21, region.activity_words at region.py:124). Leave the '%s trip reports' <title> pattern (section.py:534) and the Other title as they are. Effort S.

**Files.** `tools/lib/content.py`, `tools/sitegen/pages/section.py`, `tools/sitegen/search.py`, `tests/`.

**Effort.** S. Visitor value 1.3, author value 1, confidence high.

**Risk.** Search index words change with the label; run the trips.js harness. URLs unchanged.

**Decision for Eric.** The name: 'Backcountry Skiing', 'Ski touring', or keep 'Backcountry Ski'.

**Review note (condensed; the observation and proposal above are the revised text).** Not built and no document or decision addresses the name (grep of docs/ for 'Backcountry Ski' naming finds nothing), but the proposal's 'one place' is wrong and the change reaches tests it does not list. The inconsistency is real ('Backcountry Ski' in content.py:18 beside four gerunds; TAGLINE at core.py:24 says 'Backcountry skiing'; built <title> 'Backcountry Ski trip reports · Eric Sichak' in _site/ski/index.html; '51 backcountry ski trip reports' in its description).

#### resilience-01. Cover the script-failed state: header menu and search forms

**Observation.** The no-JS header rules live only under `@media (scripting: none)` (base.css:177-191), which matches when scripting is disabled and only in Safari 17+, Chrome 120+ and Firefox 113+. `assets/site.js` is loaded with `defer` and no `onerror` (core.py:1747). If it fails to download, is blocked by an extension, or the browser predates that media feature, no rule applies: `.nav` is `display: none` below 1140 px (base.css:157, 171), so the menu button (core.py:1676) is the only navigation and it does nothing; on trips/ and tick-list/ the inline `core.reveal` script (core.py:1501-1507) has already un-hidden the search form (trips.py:104-142), whose box, chips and selects then do nothing while the `<noscript>` note stays hidden. The Map page is fine: its tabs and chips ship `hidden` and archive.js reveals them (archive.py:319, 367).

**Evidence.** `assets/css/base.css:157`; `assets/css/base.css:171`; `assets/css/base.css:177-191`; `tools/sitegen/core.py:1676`; `tools/sitegen/core.py:1745-1747`; `tools/sitegen/core.py:1501-1507`; `tools/sitegen/pages/trips.py:104-142`; `tools/sitegen/pages/archive.py:319`; `assets/js/pages/archive.js:1-8`; `tests/test_a11y_static.py:1-30`.

**Proposal.** In the existing inline head script (core.py:1746) also add a js class to <html>, and put onerror="document.documentElement.classList.remove('js')" on the site.js tag (core.py:1747). Give each of the five @media (scripting: none) blocks an html:not(.js) twin selector list with the same declarations (base.css:177-191 including the 479.98px block, report.css:179, region.css:29, about.css:40), keeping the media query. Add one test that every (scripting: none) rule has its html:not(.js) twin (the rule list is already read by scripting_none() in tests/test_a11y_static.py:2287-2320). Update docs/DEVELOPING.md:139 and :557-559, which currently describe the old-browser gap as accepted. Leave the trips/ and tick-list/ search forms as they are (their noscript notes stay correct with scripting off; a failed download is rare and the footer links still navigate). Effort S.

**Files.** `tools/sitegen/core.py`, `assets/css/base.css`, `assets/css/pages/report.css`, `assets/css/pages/region.css`, `assets/css/pages/about.css`, `tools/sitegen/pages/trips.py`, `tools/sitegen/pages/ticklist.py`, `tests/test_a11y_static.py`.

**Effort.** S. Visitor value 1.3, author value 1, confidence high.

**Already known.** IMPLEMENTATION_REPORT.md 15.5 (never run outside Chromium)

**Risk.** The documented no-JS behavior (DEVELOPING.md) must stay identical with scripting off; the class rules are a superset of the media-query rules, so verify both states with the cascade reader. A SyntaxError in the bundle is not caught by onerror (see resilience-08).

**Review revision (applies on top of the text above).** Observation (append): The half of this that concerns browsers without the `scripting` media feature is a documented limit: docs/DEVELOPING.md:139 ('A browser that does not know the `scripting` media feature shows the header as it is with JavaScript') and :557-559 (the copy button). The failed-download case (`defer`, no `onerror`, core.py:1747) is not documented. relates_to_known: DEVELOPING.md:139 and :557-559; IMPLEMENTATION_REPORT.md 15.5 (never run outside Chromium).

**Review note (condensed; the observation and proposal above are the revised text).** The observation is accurate (base.css:157 and :171 hide .nav below 1140 px; the fallback lives only under @media (scripting: none) at base.css:177-191; core.py:1747 loads site.js with defer and no onerror; core.reveal at core.py:1501-1507 un-hides the trips/ and tick-list/ forms before the bundle arrives). Reproduces: base.css:157 `.nav { display: none }`, :171 shows it only from 1140 px, :177-191 the two `(scripting: none)` blocks; core.py:1676 the menu button, :1745 the inline units script, :1747 `<script src=... defer>` with no onerror; core.reveal at core.py:1501-1507 un-hides `#search` (trips.py:128-142, ticklist.py:99-117) while the `<noscript>` note (trips.py:136, ticklist.py:111) stays hidden; archive.py:319 and :367 ship the tabs and filter `hidden`; the other scripting blocks are at report.css:179, region.css:29, about.css:40.

#### copy-12. One verb per destination for action links

**Observation.** The same kind of link, one that leaves the page for a report, journal, goal or map, is worded seven ways: 'Read the report' and 'View trip' (home.py:101), 'Read report' (section featured, section.py:184), 'Explore the journal' (home series card, home.py:100), 'Read the series' (section.py:326, archive.py:274), 'View goal' (core.py:1405), 'Open the map' (home region blocks home.py:329, about.py:94, report pager report.py:434). The series title actions 'Browse all recordings' and 'Read the first written entry' (series.py:503-505) are in-page jumps (href '#days' and a day anchor) and stay as they are. The design map (maps/design.md #30) notes the one .alink style serves links, in-page jumps and the copy button.

**Evidence.** `tools/sitegen/pages/home.py:100-101`; `tools/sitegen/pages/section.py:184`; `tools/sitegen/pages/section.py:326`; `tools/sitegen/pages/archive.py:274`; `tools/sitegen/core.py:1405`; `tools/sitegen/pages/about.py:94`; `_site/index.html, _site/hiking/index.html, _site/map/index.html (link texts grepped: 'Read the report', 'Read report', 'Read the series', 'Explore the journal')`.

**Proposal.** A short table in docs/DEVELOPING.md and the code: a written report → 'Read the report'; a track-only trip → 'View the trip'; the journal → 'Open the journal'; a goal → 'Open the goal'; the map → 'Open the map'; lists → 'All N reports'. Replace 'Read report', 'Explore the journal', 'Read the series', 'View goal' accordingly; keep in-page jumps ('Previous / Next write-up') and the copy control as they are.

**Files.** `tools/sitegen/pages/home.py`, `tools/sitegen/pages/section.py`, `tools/sitegen/pages/archive.py`, `tools/sitegen/core.py`, `docs/DEVELOPING.md`, `tests/`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Risk.** None.

**Review note (condensed; the observation and proposal above are the revised text).** Not built: no verb table exists (grep 'verb|action link|link text' in docs/DEVELOPING.md matches nothing) and all six wordings are live as cited: 'Explore the journal' / 'Read the report' / 'View trip' (tools/sitegen/pages/home.py:100-101, not 97-100), 'Read report' (section.py:184), 'Read the series' (section.py:326, archive.py:274), 'View goal' (core.py:1406), 'Open the map' (about.py:94, report.py:434, home.py:329), 'Read the first written entry' / 'Browse all recordings' (series.py:503,505), 'All %d reports' (home.py:171). Evidence verified: home.py:98-101 ('Read the report' / 'View trip' / 'Explore the journal'), section.py:184 ('Read report'), section.py:326 and archive.py:274 ('Read the series'), core.py:1406 ('View goal'), about.py:94 and report.py:434 ('Open the map'). Feasible (string edits in Python, 3.9, no render). The wording spread reproduces: home.py:100 'Read the report'/'View trip' and :97 'Explore the journal'; section.py:184 'Read report'; section.py:326 and archive.py:274 'Read the series'; core.py:1405 'View goal'; about.py:94, report.py:434 and home.py:329 'Open the map'.

**Gates.** The phase is done when every line below holds and is recorded in the log entry:

1. Lighthouse mobile on the live home after the deploy: accessibility 100 (.hom-reg-n a measures 44 px high with layout unchanged in before/after captures at 390 and 1280 px); the Matterhorn report stays 100/100/100.
2. Cascade tests: no 11 px text rule applies at 390 px (t-label, keyrow, mv-attrib, tags, day ruler, rtab-h, eltab th, arc-table tag; multiday.css:229 removed); .trx-sel select and .copy-url are 16 px under 760 and both search boxes carry enterkeyhint=search; .chip--title, .tag and .trx-chip use min-height; the header nav shows from 1000 px (three pinned widths updated) and base.js closes the menu at 1000; the menu has a Home row first and the Units row above the lists; under 500 px of height the header is static and the bottom bar is one row; a js class and onerror fallback give the same header when the bundle is blocked (checked in Chrome with site.js blocked).
3. Every decorative :hover rule sits under @media (hover: hover) with the mixed selector lists split; Chrome touch emulation shows a tapped day chip and month tab do not stay highlighted; no --route-ink hover rule remains and the token is deleted or documented; the year heads on trips/ and map/ read at 22/28 (24/30 from 760) scoped to .p-trips and .p-archive while the tick list's heads are unchanged.
4. Card tiles fill their slot with map-paper bands (base.css and home.css rules, 62 photo-less trips), section lists show one column header per group from 760 px with .sr labels on the rows (Other page excluded), dead CSS (.t-h4, .photos, .prow, core.phone_row) is gone and .abo-dl is .dl-leader, and the print sheet is appended last in css_bundle and checked in Chrome and Safari print preview on a report and a multi-day page.
5. Accessibility: rows under a year are H4 on Hiking and Mountain biking with a nesting assertion; units_control buttons carry aria-labels and U(), plain_stats and row_stats_line speak unit words (table_row's own sr words removed); a @media (prefers-contrast: more) block raises --ink-3 and --rule-strong and overrides .pf-ax/.mk-lbl; the home key discs and filter-chip swatches keep their color under forced colors and the journal bars survive; an accessibility snapshot of the home page shows no '·' StaticText in the cards; the filter bands fade at the edge and scroll the checked segment into the row by scrollLeft.
6. Copy: header, menu, footer and 404 use one word per destination ('Map & archive' and 'PCT' consistent; the crumb root stays Reports to home); 'Backcountry Skiing' if chosen with the 10 test lines and two harnesses updated and strava.py untouched; the PCT link carries an aria-label containing its text; the destination verb table is in DEVELOPING.md and 'Read report', 'Explore the journal', 'Read the series', 'View goal' are gone from the build; every map caption uses the shared FULL_TRACK constant and a test checks caption items start with a capital or digit; the tick list's empty state and the footer's 'AVALANCHE TRAINING: AIARE 2' read as proposed.
7. docs/CHECKING_WITH_A_SCREEN_READER.md exists with the 20-minute script and Eric's VoiceOver run on macOS Safari and iOS is logged in WEBSITE_IMPLEMENTATION_LOG.md; DEVELOPING.md's Measuring section gains the tablet profile (768×1024, 1024×768, 1180×820, touch emulation) and the first run's captures sit in .cache/plan2 with a coarse-pointer walk of the map wiring noted.
8. Both Pythons with -W error and build.py --check pass; tests/test_a11y_static.py, test_nav.py, test_home.py and test_ticklist_page.py updated.

**Tests to add.** New: `tests/test_section_page.py` (13B, visual-11). Extended: `tests/test_a11y_static.py`, `tests/test_about_units.py`, `tests/test_build_site.py`, `tests/test_home.py`, `tests/test_nav.py`, `tests/test_region_page.py`, `tests/test_report_page.py`, `tests/test_ticklist_page.py`, `tests/test_trips_page.py`, `tests/ticklist_js_harness.js`, `tests/trips_js_harness.js`. Plus the checks the gates name that no unit test covers: Lighthouse mobile on the live home after the deploy (accessibility 100 expected); the cascade tests; Chrome touch emulation for stuck hover; an accessibility snapshot of the home page; forced-colors emulation; print preview in two browsers; VoiceOver on two devices.

**Screenshots to capture.** Home at 390 and 1280 px before and after (a11y-03's layout must not move; before set: `phone-home.jpeg`, `desktop-home.jpeg`); the open phone menu with the Home and Units rows; the tablet profile at 768 by 1024, 1024 by 768 and 1180 by 820 for home, trips, a report and map; print preview of a report and the Haute Route in Chrome and Safari; the header with `site.js` blocked.

**Author inputs needed.** Decisions 14 and 15; twenty minutes with VoiceOver on macOS Safari and iOS following `docs/CHECKING_WITH_A_SCREEN_READER.md`, logged.

### Phase 14. Loading, metadata, sharing, follow and contact

**Goal.** Make each report an honest search result and share card (activity and place in the title, whole descriptions, og:site_name and breadcrumbs), close the ten-minute stale-stylesheet window, self-host the fonts if Eric agrees, fix the two measured image misses, give readers a Follow section and a way to reach Eric, and set up Search Console and the first real share preview.

**Prerequisites.** Phase 7 (markdown.plain_sentences, which seo-02 reuses). Eric's decisions: the fonts (12.3), the contact path and a public alias he will keep, which profile links, the share-image path (12.4) after the real preview check; Search Console is his account work.

**Decisions this phase waits on.**

- Self-host the fonts with display: swap and measure (12.3; recommended yes; 'optional' only after a later measurement)
- Contact path: a dedicated public alias as a plain mailto (recommended), with 'Ask about this trip' on reports and the footer row; no obfuscation, no hosted form, no newsletter service
- Which profile links, if any (recommended only the Strava profile if he wants one; nothing is guessed)
- Search Console set-up (recommended yes) and whether to make the esichak.github.io user-site repository for a root robots.txt (optional)
- Share image for the 62 photo-less reports (12.4): keep the text card unless the real preview check shows a defect

**Findings in this phase** (21, in working order): perf-02, perf-01, perf-07, perf-14, seo-01, seo-02, seo-03, seo-06, seo-12, seo-13, seo-04, seo-08, seo-11, seo-09, phone-16, gap5-01, gap5-08, gap5-03, gap5-05, gap5-07, gap5-02.

#### perf-02. Self-host the three fonts and preload the two above the fold

**Observation.** Every page loads a render-blocking stylesheet from fonts.googleapis.com (core.py:32-33, 1742) which, fetched as Chrome, is 8,416 bytes with 21 `@font-face` blocks; the Latin files it names weigh 90,096 B (Archivo variable), 48,704 B (Source Serif 4 regular), 50,560 B (Source Serif 4 italic) and 23,108 B (Geist Mono), 212 KB in all, from a second origin (fonts.gstatic.com). The report measured that on desktop first paint followed that stylesheet's arrival by 39-89 ms in all 25 runs, and the stylesheet itself arrived 236-347 ms after navigation start (section 2.3), so two cross-origin connections sit on the critical path of every page. The build copies only top-level `assets/*.*` (build.py:300-303), so a fonts folder needs a copy step, as the 2026-10-08 plan noted. All three faces are SIL OFL (Geist: GitHub API spdx_id OFL-1.1; Archivo and Source Serif 4 publish OFL.txt).

**Evidence.** `the Google Fonts stylesheet as served on 2026-10-13 (21 @font-face blocks, 8,416 bytes)`; https://fonts.gstatic.com/s/archivo/v25/k3kQo8UDI-1M0wlSfdnoLmvDIaI.woff2 (90,096 bytes); https://fonts.gstatic.com/s/sourceserif4/v15/vEFF2_tTDB4M7-auWDN0ahZJW3IX2iZPwg3BucvUtfykDXr4Y3qwzQ.woff2 (48,704 bytes); `tools/sitegen/core.py:32-33`; `tools/sitegen/core.py:1740-1743`; `tools/build.py:300-303`; `docs/IMPLEMENTATION_REPORT.md:141-147`; `docs/IMPLEMENTATION_REPORT.md:501-503`; `docs/personal-website-improvement-plan.md:409`.

**Proposal.** Add `tools/fonts.py` (stdlib `urllib`, run once on the Mac with internet) that downloads the four Latin woff2 files Google serves today into `assets/fonts/` with the three OFL license texts, and writes `assets/css/fonts.css` holding four `@font-face` rules (`font-display: swap`, the same `wdth`/`wght`/`ital` ranges as the Google URL, `unicode-range` for Latin). Bundle `fonts.css` first in `css_bundle()`; extend the asset copy in `build.py` to `assets/fonts/`; in `core.document()` drop the Google stylesheet and the two `preconnect` links and emit `<link rel="preload" as="font" type="font/woff2" crossorigin>` for Archivo and Source Serif 4 regular only (italic and mono load on demand). Add a test that every `@font-face` src names a copied file. Measure desktop first paint and phone LCP with the method of DEVELOPING.md:1428 before and after; expect first paint to move to the arrival of `site.css`. Second step, only after measuring: try `font-display: optional` on the Tick list, where the swap costs CLS 0.107 (report 2.5).

**Files.** `tools/fonts.py`, `assets/fonts/`, `assets/css/fonts.css`, `tools/build.py`, `tools/sitegen/core.py`, `tests/test_build_site.py`.

**Effort.** M. Visitor value 2.7, author value 1.7, confidence high.

**Already known.** IMPLEMENTATION_REPORT.md section 12 decision 3 and section 2.5; history map (b) 'Self-hosting the fonts'

**Risk.** Adds about 212 KB of binary font files to the repository (once; Google's file names are versioned, so updates are deliberate). License texts must ship with the fonts. Keep `display: swap` first so nothing changes visually; `optional` is a visible change (a slow first visit keeps the fallback fonts) and is Eric's call.

**Decision for Eric.** Whether to take the fonts into the repository (OFL permits it), and later whether `font-display: optional` is acceptable on a slow first visit.

**Review note.** Kept as written by all three skeptics.

#### perf-01. Put a content hash in the bundle file names

**Observation.** Every page links `assets/site.css` and `assets/site.js` by bare name (core.py:1740-1747), and GitHub Pages sends `cache-control: max-age=600` with an ETag on both (live headers fetched 2026-10-13, 17:07 UTC). A visitor who loaded the stylesheet within ten minutes before a deploy receives new HTML with the old stylesheet, which the report records as an open point. The site check already strips `?` and `#` from hrefs (sitecheck.py:263-267), so either a hashed name or a query string passes it.

**Evidence.** https://esichak.github.io/personal-website/assets/site.css (curl -D: cache-control: max-age=600, etag W/"6ace5b25-21b03"); `tools/sitegen/core.py:1740-1747`; `tools/build.py:296-299`; `tools/sitegen/sitecheck.py:263-267`; `docs/IMPLEMENTATION_REPORT.md:862-863`; `tools/sitegen/core.py:1744`; `tools/sitegen/core.py:1747`; `tools/build.py:264-297`; `tools/sitegen/sitecheck.py:263`; `docs/IMPLEMENTATION_REPORT.md:862-863`; `tools/sitegen/core.py:1742-1747`; `assets/js/pages/trips.js:214`; `assets/js/pages/trips.js:232`; https://esichak.github.io/personal-website/assets/site.css.

**Proposal.** In `build.py` build the two bundles before the page loop, take the first 8 hex of SHA-1 over each bundle's bytes and set `core.ASSET_VERSION = {'css': h1, 'js': h2}` (default `{}` so `document()` called directly in tests still emits the bare names); `core.document()` appends `?v=<hash>` to `assets/site.css` and `assets/site.js` when set. Keep the file names: the CDN serves `assets/site.css?v=x` with the same 200 / ETag / max-age=600 headers as the bare name (curl 2026-10-13), the site check strips `?` (sitecheck.py:263-267), the 404 page already goes through core.document (notfound.py:44), and a cached old page keeps resolving its `?v=old` link to the live file instead of 404-ing on a hashed name that the rebuilt `_site/` no longer holds. Update the tests that pin the exact href (tests/test_build_site.py, test_sitecheck.py, test_ticklist_page.py, test_privacy_audit.py) and the DEVELOPING.md line. Because the new query string is a guaranteed cache miss, a deploy can never pair new pages with an old stylesheet. Effort S.

**Files.** `tools/build.py`, `tools/sitegen/core.py`, `tests/test_build_site.py`, `tests/test_sitecheck.py`, `tests/test_ticklist_page.py`, `tests/test_privacy_audit.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 2, author value 2, confidence high.

**Also covers.** authoring-05, resilience-11 (merged into this finding).

**Already known.** IMPLEMENTATION_REPORT.md 15.5 (asset addresses carry no version); pipeline map section 7 item 15

**Risk.** The 404 page uses `<base href>` and links the bundles too; keep the bare copies so nothing that hard-codes `assets/site.css` breaks. No URL of a report, GPX or map changes.

**Review note (condensed; the observation and proposal above are the revised text).** The problem is real and documented (docs/IMPLEMENTATION_REPORT.md:862-863; live headers max-age=600) and the fix is S, but a hashed file name adds a failure the site does not have today: `build()` empties `_site/` on every deploy (tools/build.py:273-275), so a visitor whose cached old page still names `site.<old>.css` gets a 404 for it once that file has left their cache, i.e. an unstyled page instead of a slightly stale one.

#### perf-07. Preload the ski page's region map like the other section pages

**Observation.** Climbing, hiking, mountain-biking and other each preload their featured map's hillshade and base layer for the col and phone breakpoints (four `<link rel="preload">` per built page; section.py:525), but `ski/index.html` has none: the ski page has no featured block and its first image is the sticky 'Ski map by region' panel, built with `eager=sel` (section.py:371-372), which only adds `fetchpriority="high"` to an image that is still `loading="lazy"`. That image (ski-lake-tahoe-desktop.webp, 60,818 bytes; phone 34,548) is therefore requested only after the stylesheet has arrived and layout has run, while every other map-led page fetches its map from the preload scanner.

**Evidence.** `_site/ski/index.html (0 rel=preload; first img: ski-lake-tahoe-desktop.webp loading="lazy" fetchpriority="high")`; `_site/hiking/index.html (4 rel=preload; climbing/, mountain-biking/ and other/ the same)`; `tools/sitegen/pages/section.py:371-372`; `tools/sitegen/pages/section.py:525`; `tools/sitegen/core.py:534-553`; `rendered/site/ski-lake-tahoe-desktop.webp (60,818 bytes)`.

**Proposal.** In `section.py`'s ski branch, build `extra_head` with `core.map_preloads(None, here, [('ski-<first>-desktop', 'desktop'), ('ski-<first>-phone', 'phone')], 'assets/maps/', site_maps=True)` for the initially selected region, exactly as the featured block does at section.py:525. Leave `loading="lazy"` on the panel's images: the hiking page's preloaded featured map keeps it (`_site/hiking/index.html`), and core.py:505-507 relies on it so the hidden breakpoint's raster is never fetched. Add a test asserting the ski page head carries the two media-scoped preload pairs. Expected: the ski page's largest image starts downloading with the HTML instead of after CSS and layout, the same path the hiking page already takes. Effort S.

**Files.** `tools/sitegen/pages/section.py`, `tests/test_build_site.py`.

**Effort.** S. Visitor value 2, author value 1, confidence high.

**Risk.** Preloads carry `media` attributes so only one breakpoint's pair is fetched; keep that pattern or phones would download the desktop raster too.

**Review revision (applies on top of the text above).** Proposal: unchanged (`PRELOAD_MEDIA` at core.py:529-530 already maps `desktop` and `phone`, and `map_preloads(..., site_maps=True)` reads `rendered/site/meta.json`), with the test placed in tests/test_build_site.py beside the other section-page assertions (SECTIONS, line 94). FILES: tools/sitegen/pages/section.py, tools/sitegen/core.py, tests/test_build_site.py. EVIDENCE correction: _site/hiking/index.html (4 rel=preload), and the same on climbing, mountain-biking and other.

**Review note (condensed; the observation and proposal above are the revised text).** Not built: `_site/ski/index.html` has 0 `rel="preload"` where climbing, hiking, mountain-biking, other, both region pages and map/ have 1 each; its first `<img>` is `../assets/maps/ski-lake-tahoe-desktop.webp` (60,818 B; phone 34,548 B) with `loading="lazy" fetchpriority="high"`, from section.py:371-372 `eager=sel` and core.py:503-505. section.py:525 builds the preload only in the non-ski branch (`else:` at :499); the ski branch sets `extra_head = NOSCRIPT` at :498, which the new preloads must be appended to, not replace. The gap is real: `_site/ski/index.html` has 0 `rel="preload"` where the other four section pages have one group each, its first image is `ski-lake-tahoe-desktop.webp loading="lazy" fetchpriority="high"`, and section.css:219-222 puts the panel before the list below 960 px, so the map is near the top on phones too. The core observation reproduces: _site/ski/index.html has no `rel="preload"` and no `sec-feat` block, and its first `<img>` is `../assets/maps/ski-lake-tahoe-desktop.webp` with `loading="lazy" fetchpriority="high"`, from section.py:371-372 (`eager=sel`, `sel = i == 0` at 367); section.py:525 calls `core.map_preloads` for the featured map; map_preloads is core.py:534-553 and `PRELOAD_MEDIA` (529-530) has `desktop` and `phone` entries, so the proposed call works; the rasters are 60,818 and 34,548 bytes.

#### perf-14. Serve the Hiking page's journal thumbnails from the card copies

**Observation.** The hiking page's PCT block shows the first photo of three days through core.photo with sizes="(min-width: 1200px) 224px, (min-width: 560px) 15vw, 30vw" and a srcset of the 800 px and 1600 px files only (section.py:302-304; built srcset d001-01.sm.webp 800w, d001-01.webp 1600w). For a 224 px slot every screen takes the 800 px copy (62,680, 67,536 and 98,796 bytes, 229 KB together), while each of those photos has a 320 px-short-edge .th copy of 19,960, 21,018 and 31,382 bytes (72 KB together) that would serve 1x and 2x screens at that width. About 229 KB per view goes to 72 KB, a saving of about 156 KB. Already listed as open in the report (IMPLEMENTATION_REPORT.md:850).

**Evidence.** `tools/sitegen/pages/section.py:302-304`; `_site/hiking/index.html (srcset 800w/1600w, sizes ... 224px)`; `content/trips/pacific-crest-trail-2024/photos/d001-01.sm.webp (62,680 bytes) and d001-01.th.webp (19,960 bytes)`; `docs/IMPLEMENTATION_REPORT.md:850`.

**Proposal.** Give core.photo an optional thumb=True that, when the photo has a .th copy, adds it as the first srcset candidate at thumb_width(p) (core.py:771; 427w for a landscape) so the browser's own selection picks it for slots up to about 213 px at 2x; use it in the hiking series block. Add a test that the hiking page's three journal images name the .th file first, in tests/test_build_site.py (which builds the section pages; there is no test_section_page.py) or a new tests/test_section_page.py. No new files: all 103 PCT photos have .th copies. FILES: tools/sitegen/core.py, tools/sitegen/pages/section.py, tests/test_build_site.py (or a new tests/test_section_page.py).

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/section.py`, `tests/test_build_site.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Already known.** IMPLEMENTATION_REPORT.md 15.4.12 (Hiking page loads 800 px files for 114 px journal thumbnails)

**Risk.** A 3x phone at 30vw of 390 px (117 px) wants 351 px and would still take the 427 px landscape copy; a portrait first photo's 320 px copy is 5% under, the same trade the cards already make (core.py:783).

**Review note (condensed; the observation and proposal above are the revised text).** Not built, and known: _site/hiking/index.html's three journal figures carry srcset 'd00N-01.sm.webp 800w, d00N-01.webp 1600w' with sizes '(min-width: 1200px) 224px, (min-width: 560px) 15vw, 30vw' (section.py:302-304); core.photo (core.py:751-764) has no thumbnail option, and the only code that offers a .th copy is _card_source (core.py:789-808), which applies solely to card sizes strings ending in CARD_PHONE_SLOT; the .th files exist at the stated sizes (ls: d001-01.th.webp 19,960; d002-01 21,018; d003-01 31,382; the .sm copies 62,680/67,536/98,796) and all 103 PCT originals have a .th copy. The code, markup and byte counts reproduce exactly: section.py:302-304 calls core.photo with sizes '(min-width: 1200px) 224px, (min-width: 560px) 15vw, 30vw'; the built hiking page's three journal <img> carry srcset 'd00N-01.sm.webp 800w, d00N-01.webp 1600w'; the .sm files are 62,680 / 67,536 / 98,796 bytes and the .th files 19,960 / 21,018 / 31,382; thumb_width (core.py:771-774) returns 427 for a 1600x1200 photo; all 103 PCT base photos have .sm and .th copies; IMPLEMENTATION_REPORT.md:850 lists the 114 px thumbnails as open.

#### seo-01. Put the activity and place into every trip page's title tag

**Observation.** Every trip page's <title> and og:title are '{title} · Eric Sichak' (core.py:1723), with the date added only when a title repeats (report.py:649-650). About 33 of the 167 published titles contain their place or region word, 12 titles are shared by several reports ('Tallac' by four), and titles such as 'Good fun · Eric Sichak' or 'AIARE 2 · Eric Sichak' tell a searcher or a browser-tab reader nothing about what the page is. The H1 is verbatim, so the title tag is the only place facts can go.

**Evidence.** `tools/sitegen/core.py:1723`; `tools/sitegen/pages/report.py:649-650`; `tests/test_metadata.py:1640-1656`; `_site/trips/back-to-clipless/index.html`; `_site/trips/matterhorn-peak-west-couloir/index.html`; `content/trips (load_all count: 167 published, 12 repeated titles)`.

**Proposal.** Add core.page_title(t, dup) and use it for full_title in report.py (single-day at report.py:661 and goal at :566), multiday.py:797 and series.py:527: '{title} · {core.act_word(t)}, {place or region}' plus ', {short date}' when dup, then ' · Eric Sichak'; fall back to today's form when place and region are both absent (79 trips lack a place, none lacks a region, so this never fires today). Activity, place and region come from index.md only. og:title takes the same string; the H1 and the BlogPosting headline stay the title as written. Leave home, section and region titles as they are. Tests: both test_the_title_tag_and_og_title_are_escaped (tests/test_metadata.py:1640-1645, which pins the exact '<title> · Eric Sichak' form on three trip pages) and the twin-title test (1647-1659) change. Docs: DEVELOPING.md has no title note today; add one beside the share-metadata notes (docs/DEVELOPING.md:736-752) and in CONTENT_GUIDE §9 (docs/CONTENT_GUIDE.md:896), and update the comment at report.py:647-648.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tools/sitegen/pages/series.py`, `tests/test_metadata.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 3, author value 1.7, confidence high.

**Risk.** Facts-only: every word comes from front matter. Titles over 60 characters are cut in search results, but the trip title leads so nothing important is lost. Tests pin the current form and must change with it.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible, facts-only and S-honest: core.act_word (core.py:336), fdate(d,'short') (core.py:173) and the dup rule (report.py:649-650) already exist, and only test_metadata.py pins the title form (five '· Eric Sichak' asserts, including test_the_title_tag_and_og_title_are_escaped at 1640-1644, which checks every URL in self.urls). Observation reproduces: core.py:1723 builds '<title> · Eric Sichak'; report.py:649-650 adds the short date only when title_counts > 1; content.load_all gives 167 published, exactly 33 titles containing their place or region string, 12 repeated titles ('ride near day valley' x7, 'tallac' x4); built heads read 'Good fun · Eric Sichak' and 'AIARE 2 · Eric Sichak'.

#### seo-02. Stop meta descriptions ending mid-sentence on 118 trip pages

**Observation.** report.py:651-654 clips 'summary + excerpt' to 155 characters with core.clip_words (core.py:307-312), so 118 of the 168 trip pages end in '…', often inside the facts: the bare ride's description ends 'with map, elevation…' and the Matterhorn's cuts the write-up mid-phrase. multiday.description (multiday.py:766-775) already does it right: the facts whole, an excerpt only when it fits.

**Evidence.** `tools/sitegen/pages/report.py:651-654`; `tools/sitegen/core.py:307-312`; `tools/sitegen/pages/multiday.py:766-775`; `_site/trips/back-to-clipless/index.html`; `_site/trips/matterhorn-peak-west-couloir/index.html`; `_site/trips (168 heads scanned: 118 descriptions end in …)`; `tools/sitegen/core.py:1432-1478`; `tools/sitegen/pages/report.py:647-654`; `_site/trips/back-to-clipless/index.html (meta description, 152 chars)`; `_site/trips/ride-near-day-valley/index.html (meta description)`; `tools/build.py:225-240 (feed uses the same summary)`.

**Proposal.** Add core.describe(t, limit=160) and use it on single-day and goal pages (report.py:651-654 and :563), replacing multiday.description (multiday.py:766-775) with the same function: when the page is facts-led (track-only, caption-length write-up, or a repeated title) write core.summary(t) whole regardless of limit, as multiday.description already does (summaries run 116-220 characters today, median 166, so a 160 limit cannot hold them), and append the excerpt only when its first sentence fits in the room left; when a write-up leads, cut at the last sentence end between 80 and 160 characters, and only then fall back to the word cut with '…'. Keep summary() itself unchanged (the feed uses it) unless Eric would rather shorten the facts for everyone. Tests in tests/test_metadata.py for the three shapes (the existing test_the_description_is_the_factual_summary_then_the_start_of_the_write_up at 1956 changes); the share-preview sheet (seo-13) counts descriptions that still end in '…'.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tests/test_metadata.py`.

**Effort.** S. Visitor value 2.3, author value 1.3, confidence high.

**Also covers.** copy-02 (merged into this finding).

**Risk.** None to facts or write-ups; description tests change.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible and worth it: report.py:651-654 clips summary + excerpt to 155 with clip_words (core.py:307-312) and 118 of the 168 built trip pages end in '…' (counted in _site/trips today; back-to-clipless ends 'with map, elevation…'), while multiday.description (multiday.py:766-775) already keeps the facts whole. Observation reproduces: report.py:651-654 clips summary + excerpt with core.clip_words (core.py:307-312, limit 155); a scan of the 168 _site/trips/*/index.html heads finds 118 descriptions ending in '…'; back-to-clipless's is 152 characters ending 'with map, elevation…' and the Matterhorn's ends 'had me pretty…'; multiday.description (multiday.py:766-775) writes the summary whole and adds 'Day N: …' only when it fits; build.feed uses summary() (build.py:225-240).

#### seo-03. Add og:site_name, og:locale and article:section/tag from facts

**Observation.** core.document writes og:type, og:title, og:description, og:url and the image tags (core.py:1735-1741, 1536-1557) and nothing else: no og:site_name, no og:locale, and article pages carry article:* tags only when published_at is set, which no report has. Previewers that show a site name fall back to the host 'esichak.github.io'.

**Evidence.** `tools/sitegen/core.py:1735-1741`; `tools/sitegen/core.py:1536-1557`; `_site/index.html`; `_site/trips/matterhorn-peak-west-couloir/index.html`; `docs/DEVELOPING.md:740-749`; `tools/sitegen/sitecheck.py:469`.

**Proposal.** In core.document add <meta property="og:site_name" content="Eric Sichak"> and <meta property="og:locale" content="en_US"> on every page. In core._report_head add article:author (core.AUTHOR_URL), article:section (the activity label from core.ACT) and one article:tag per region and per name in map.peaks, all from index.md. Optionally <meta name="robots" content="max-image-preview:large"> so Google may show the full share image. sitecheck already leaves other head tags alone (sitecheck.py:469); update DEVELOPING.md:740-749 and the head tests in tests/test_metadata.py.

**Files.** `tools/sitegen/core.py`, `tests/test_metadata.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Risk.** Facts-only: tags come from region and map.peaks. No URL or rule changes.

**Review note.** Kept as written by all three skeptics.

#### seo-06. WebSite, Person and BreadcrumbList schema where the page already shows it

**Observation.** The only JSON-LD is one BlogPosting on written reports; DEVELOPING.md:81-85 states that as the rule and sitecheck fails any other @type or a second block. The home has no WebSite entity although trips/?q= is a working search URL (trips.py:128 name="q"; trips.js:13 reads q), About has no Person, and the visible breadcrumbs on report, region and section pages (report.py:110-124, region.py:68-71, section.py:118) have no BreadcrumbList. Lighthouse leaves structured data as a manual check.

**Evidence.** `docs/DEVELOPING.md:81-85`; `tools/sitegen/sitecheck.py:400-457`; `tools/sitegen/pages/home.py:353`; `tools/sitegen/pages/about.py:151`; `tools/sitegen/pages/trips.py:128`; `assets/js/pages/trips.js:13`; `tools/sitegen/pages/report.py:110-124`; `tools/sitegen/pages/region.py:68-71`; `tools/sitegen/pages/section.py:118`; `_site/index.html`; `.cache/plan2/lh-home/report.json (structured-data: manual)`.

**Proposal.** Give core.document an ld=[...] list and write one BreadcrumbList on report, multi-day, series, goal, region and section pages, built from the same list that renders the visible crumbs (names as shown, hrefs made absolute with SITE_URL). No WebSite/SearchAction (trips/?q= is JavaScript-only and the sitelinks search box no longer exists) and no Person on About (the BlogPosting already names the author with the About URL). sitecheck: allow @types BlogPosting and BreadcrumbList, at most one of each per page, each valid JSON; update the Rules in DEVELOPING.md:81-85 and CONTENT_GUIDE §9; tests in test_metadata.py and test_sitecheck.py. After deploy, Eric runs one report through Google's Rich Results Test. Effort M.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/home.py`, `tools/sitegen/pages/about.py`, `tools/sitegen/pages/report.py`, `tools/sitegen/pages/region.py`, `tools/sitegen/pages/section.py`, `tools/sitegen/sitecheck.py`, `tests/test_metadata.py`, `tests/test_sitecheck.py`, `docs/DEVELOPING.md`, `docs/CONTENT_GUIDE.md`.

**Effort.** M. Visitor value 1.7, author value 1, confidence high.

**Risk.** Changes a stated rule (one BlogPosting only); every value must mirror something already on the page; the SearchAction is honest only while trips.js keeps the q parameter.

**Review note (condensed; the observation and proposal above are the revised text).** The breadcrumbs exist today in report.py:110-124 (title_block), region.py:68-71 and section.py:118, Lighthouse leaves structured data as a manual audit (.cache/plan2/lh-home/report.json: scoreDisplayMode 'manual'), and sitecheck.py:446-457 plus DEVELOPING.md:81-85 pin 'one BlogPosting only', so a BreadcrumbList is a real, bounded addition that mirrors visible page content.

#### seo-12. A Search Console verification hook and a documented submission step

**Observation.** Nothing in README.md or docs/ mentions Search Console or Bing Webmaster Tools (grep: no hits), and core.document (core.py:1713-1750) has no site-wide place for a verification meta tag: its extra_head parameter is per call (only the 404 page uses it, notfound.py:42-44) and the home page passes none. Without a verified property Eric cannot see which pages are indexed, submit the sitemap (the robots route is closed, seo-11), or read crawl errors and field Core Web Vitals for a site that has no analytics.

**Evidence.** `tools/sitegen/core.py:1713-1750`; `README.md and docs/*.md (grep for 'search console': no hits)`; `tools/sitegen/sitecheck.py:469`; `docs/IMPLEMENTATION_REPORT.md:853-858`.

**Proposal.** Add core.VERIFY_TAGS = () (pairs of name and content, empty by default) written as <meta name=… content=…> into every head by core.document; sitecheck leaves unknown metas alone. README gains a 'Search Console' section: add a URL-prefix property for https://esichak.github.io/personal-website/, verify with the google-site-verification tag, submit sitemap.xml, inspect one report URL, then import the property into Bing Webmaster Tools (msvalidate.01 tag). Eric does the account steps; the tokens are public values and can be committed. A test checks the tags are written only when set.

**Files.** `tools/sitegen/core.py`, `README.md`, `tests/test_metadata.py`.

**Effort.** S. Visitor value 1.3, author value 3.3, confidence high.

**Risk.** None; verification tokens are not secrets.

**Decision for Eric.** Whether to set up Search Console at all (Google-account work outside the repository).

**Review note (condensed; the observation and proposal above are the revised text).** grep -rniE 'search console|webmaster' over README.md, docs/ and ADDING-TRIPS.md finds nothing; no analytics in core.py or base.js; sitecheck.py:469 says everything else in a head is left alone and _page_metadata (:402-456) has no unknown-meta check, so a new meta would pass. core.document is at core.py:1713-1750.

#### seo-13. A local share-card preview sheet for every page

**Observation.** Share tags are checked for form (sitecheck META) but no card has ever been seen: report 15.5 and the publication entry list 'a real share preview' as never run, and CONTENT_GUIDE §9 tells Eric to grep og:image out of a built page. With seo-01, seo-02 and seo-04 changing titles, descriptions and images, 186 pages need eyes before a deploy.

**Evidence.** `docs/IMPLEMENTATION_REPORT.md:245`; `docs/IMPLEMENTATION_REPORT.md:853-858`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:962-964`; `docs/CONTENT_GUIDE.md:896-922`; `tools/sitegen/sitecheck.py:400-457`.

**Proposal.** tools/share_preview.py [--site _site]: reads every indexable page's head and prints one line per page (og:title, og:description, image path, pixel size and type) with a flag list at the top: no image, description ending in '…', title over 60 characters, image not JPEG or PNG, portrait image. Text output only, never written into _site/; a small test in tests/ over a built fixture. README.md gains a post-deploy step: paste three representative addresses (a single-day report with photos, a bare ride such as back-to-clipless, the PCT landing) into opengraph.xyz, the Facebook Sharing Debugger and an iMessage or Slack thread, and replace the og:image grep in CONTENT_GUIDE.md:918-921 with the tool. Effort S.

**Files.** `tools/share_preview.py`, `README.md`, `docs/DEVELOPING.md`, `tests/test_share_preview.py`.

**Effort.** S. Visitor value 1, author value 2.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.5 (a real share preview never run)

**Risk.** None to the site; a local tool only.

**Review note (condensed; the observation and proposal above are the revised text).** The premise overstates the need: every share tag comes from one template (core._share_tags and _report_head, core.py:1580-1594 and document at 1713-1750) and sitecheck checks every page's og tags for form and that the image exists at its declared size (sitecheck.py:426-435; log:961-962), so 186 pages do not each need eyes; three or four representative pages do.

#### seo-04. Share a 1200x630 JPEG crop of each cover instead of the 4:3 WebP

**Observation.** Every share image is the cover's full WebP: of the 106 covers, 70 are exactly 1600x1200 (72 within a pixel of 4:3) and 24 are portrait 1200x1600 (one more is 738x1600). Facebook, LinkedIn, Slack and iMessage draw a 1.91:1 card and crop whatever they get, so a portrait cover's subject can be cut, and the log notes some previewers may not draw WebP at all; no real share preview has ever been looked at. The cards already use a focal point per cover (core.cover_img, core.py:811-822, from content.resolve_cover's 'focal') that a crop could reuse.

**Evidence.** `tools/sitegen/core.py:1536-1557`; `tools/sitegen/core.py:1514-1523`; `tools/sitegen/core.py:811-822`; `tools/lib/photos.py:124-169`; `tools/thumbs.py:1-18`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:962-964`; `docs/IMPLEMENTATION_REPORT.md:853-858`; `_site/trips/matterhorn-peak-west-couloir/index.html`; `content/trips (cover sizes: 71 at 4:3, 24 portrait)`; `sips --help (cropToHeightWidth, padToHeightWidth, padColor)`.

**Proposal.** Step 1 (Eric, S): paste one landscape report (matterhorn-peak-west-couloir) and one portrait-cover report into a public share debugger (Facebook Sharing Debugger, LinkedIn Post Inspector or opengraph.xyz) and into iMessage/Slack, and record what each draws; this closes the 'no real share preview' gap of IMPLEMENTATION_REPORT.md 15.5. Step 2, only if a previewer does not draw the WebP or a portrait cover's subject is cut (M): extend tools/thumbs.py with --share (and add_trip.py for new covers) to write photos/<name>.og.jpg at 1200x630 from the 1600 px source with sips --cropToHeightWidth placed around cover_focal_x/y; portrait covers padded onto paper #F2F1EC with --padToHeightWidth --padColor; metadata stripped as today. Start with the 25 portrait covers and extend to the 81 landscape ones only if step 1 showed WebP itself failing. core.share_photo returns the .og.jpg (1200x630, image/jpeg, the cover's alt) when the file exists, else the WebP as now; the validator notes a cover without a share copy like the .th copy today; CONTENT_GUIDE §9 and the README cover step (README.md:71) name the command.

**Files.** `tools/thumbs.py`, `tools/lib/photos.py`, `tools/add_trip.py`, `tools/sitegen/core.py`, `tools/lib/checks.py`, `docs/CONTENT_GUIDE.md`, `README.md`, `tests/test_metadata.py`.

**Effort.** M. Visitor value 2.7, author value 1.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.5 (WebP share images, no real share preview)

**Risk.** More committed derivatives; a crop that ignores the focal point would misdescribe the photo; a Mac-only step like the .th copies, so a missing file must fall back cleanly.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible on the Mac: sips has --cropToHeightWidth, --cropOffset, --padToHeightWidth and --padColor (sips --help today), the focal point is a content field (content.py:164-165, 287) and photos.py already strips metadata. The counts hold (106 covers: 72 at 4:3, 9 other landscape, 25 portrait). Observation reproduces apart from one count: share_photo (core.py:1514-1523) returns the cover's full WebP with its recorded size; of 106 covers, 70 are exactly 1600x1200 (72 within a pixel of 4:3: 1600x1197 and 1600x1201), 24 are 1200x1600 portrait plus one 738x1600; the log at docs/WEBSITE_IMPLEMENTATION_LOG.md:962-964 notes WebP previews and that no real share preview was run (also IMPLEMENTATION_REPORT.md:853-858). cover_img (core.py:811-822) reads c['focal'] from content.resolve_cover (content.py:278-287) and cover_focal_x/y are documented fields (README.md:71). thumbs.py:1-18 and photos.thumb_copy (photos.py:124-150) are the right extension points; the .th warning lives in tools/lib/checks.py:727-728 as the proposal says; sips --help lists --cropToHeightWidth, --padToHeightWidth and --padColor; sitecheck.py:433-437 already verifies an og:image file is in the build.

#### seo-08. Decide how search engines treat the 39 track-only pages

**Observation.** 39 published reports have neither a write-up nor a photo (75 have no write-up); their page text is the stats strip, map labels, the mile-by-mile elevation table and 'More like this', about 2,100 characters of mostly numbers on back-to-clipless. They sit in the sitemap and are indexed like written reports. The Page.index flag and the noindex pattern already exist for the full-screen map pages (core.py:46-51, report.py:704-705).

**Evidence.** `content/trips (load_all count: 167 published, 39 without write-up or photo, 75 without write-up)`; `_site/trips/back-to-clipless/index.html`; `tools/sitegen/core.py:46-51`; `tools/sitegen/pages/report.py:704-705`; `_site/sitemap.xml`.

**Proposal.** Keep the 39 track-only reports indexed and in the sitemap; they become honest results through seo-01 (activity and place in the title), seo-02 (a whole factual description) and seo-03 (article:section). Add one sentence to the Rules in docs/DEVELOPING.md (a report without a write-up or photo is indexed like any other; noindex and Page(index=False) are for helper pages such as trips/<slug>/map/ only) and one test in tests/test_metadata.py that a synthetic track-only report has no robots meta and appears in sitemap.xml. No core.thin(), no noindex option. Effort S.

**Files.** `tools/sitegen/pages/report.py`, `tools/sitegen/core.py`, `tests/test_metadata.py`, `docs/DEVELOPING.md`.

**Effort.** S. Visitor value 1.3, author value 1.3, confidence high.

**Risk.** noindex removes pages people may search for by route name; nothing is invented either way.

**Decision for Eric.** Index the track-only pages (with better titles) or mark them noindex,follow.

**Review note (condensed; the observation and proposal above are the revised text).** The observation is true and no decision is recorded, but the proposal's default is already pinned by a test. Verified from content/: 167 published, 75 without a write-up, 39 with neither a write-up nor a photo; _site/sitemap.xml lists trips/back-to-clipless/ and that page carries no robots tag. The counts hold (75 of 167 published reports have no write-up, 39 also have no photo, measured with content.load_all) and the noindex pattern exists (core.py:46-51, report.py:704-705), but it exists for the duplicate full-screen map pages, not for pages with unique content.

#### seo-11. A root robots.txt through a user-site repository, or sitemap submission

**Observation.** robots.txt is written at /personal-website/robots.txt (build.py:314-315) while https://esichak.github.io/robots.txt and https://esichak.github.io/ both answer 404 today. Crawlers read robots.txt only at the host root, so the Sitemap: line is never seen (report §8 and §12.7, log:962) and Lighthouse marks the robots audit not applicable.

**Evidence.** `tools/build.py:314-315`; https://esichak.github.io/robots.txt (404); https://esichak.github.io/ (404); https://esichak.github.io/personal-website/robots.txt (200); `docs/IMPLEMENTATION_REPORT.md:424-426`; `docs/IMPLEMENTATION_REPORT.md:508-509`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:962`; `.cache/plan2/lh-home/report.json (robots-txt: notApplicable)`.

**Proposal.** Record under Publishing in README.md that robots.txt at the project path is not read by crawlers (IR §12.7) and that the sitemap is submitted directly in Search Console and Bing (seo-12), which closes the gap. Option for Eric, outside this repository: a public repository esichak/esichak.github.io with robots.txt ('User-agent: *', 'Allow: /', 'Sitemap: https://esichak.github.io/personal-website/sitemap.xml') and an index.html that links and meta-refreshes to /personal-website/, so the bare host stops being a 404. No Disallow lines. A custom domain (seo-16) makes the robots part moot.

**Files.** `README.md`.

**Effort.** S. Visitor value 1, author value 1.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md §12.7

**Risk.** A second repository to remember; the work is outside this repository.

**Decision for Eric.** Create the user-site repository, or rely on sitemap submission alone.

**Review note (condensed; the observation and proposal above are the revised text).** The observation is verified (live: esichak.github.io/robots.txt and / answer 404, the project-path file 200; Lighthouse robots-txt audit notApplicable in .cache/plan2/lh-home/report.json) and it is the known IR §12.7 decision (docs/IMPLEMENTATION_REPORT.md:508-509).

#### seo-09. Full write-ups and covers in the RSS feed, with a write-ups-only option

**Observation.** feed.xml carries 30 items (build.py:225-240) with title, link, guid, pubDate, one category and a plain-text description of the facts plus a 400-character excerpt; 16 of today's 30 items are facts only (track-only trips), no item carries an image or the whole write-up, and the About page says 'New reports go out on the RSS feed' (about.py:137). Tests pin the item tag order and one feed's exact bytes (test_metadata.py:1940, 2022).

**Evidence.** `tools/build.py:225-240`; `_site/feed.xml (30 items, 16 summary-only)`; `tools/sitegen/pages/about.py:133-140`; `tests/test_metadata.py:1905-1913`; `tests/test_metadata.py:1940`; `tests/test_metadata.py:2022`; `tools/lib/markdown.py:50`; https://bikepacking.com/feed/; `tools/build.py:225-240`; `_site/feed.xml`; `tools/build.py:225-240`; `_site/feed.xml`; `tools/sitegen/pages/report.py:647-650`; `_site/about/index.html`; https://esichak.github.io/personal-website/feed.xml; `tools/sitegen/sitecheck.py:523`.

**Proposal.** Add xmlns:content to the channel and, for every item whose trip has a write-up, a <content:encoded> holding markdown.to_html of the trip write-up, followed for a kind: multi-day trip by each written day under a 'Day N' heading, the trip's photos as absolute URLs of the .sm copies with their alt text, and links to the page and the GPX. A trip with days and no trip-level write-up keeps the summary alone, as build.feed does today (build.py:226-227). Keep the one feed and the existing 400-character description for readers that ignore content:encoded; no second feed, no enclosure, no dc:creator, no About change. pubDate as decided in seo-10. Update the item-order and byte-pinned tests in tests/test_metadata.py and the feed note at DEVELOPING.md:78-80.

**Files.** `tools/build.py`, `tools/sitegen/core.py`, `tools/sitegen/pages/about.py`, `tests/test_metadata.py`, `docs/DEVELOPING.md`, `docs/CONTENT_GUIDE.md`.

**Effort.** M. Visitor value 2.7, author value 1, confidence high.

**Also covers.** benchmark-09, resilience-04 (merged into this finding).

**Risk.** Write-ups stay verbatim (same renderer as the pages); the feed grows by the 30 write-ups; byte-pinned tests change.

**Decision for Eric.** One feed for everything or a second write-ups-only feed.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible with the stdlib (markdown.to_html exists, tools/lib/markdown.py:50; photos have .sm copies; os.path.getsize is enough) and the renderer keeps write-ups verbatim.

#### phone-16. Home-screen icon and a minimal web manifest

**Observation.** The site ships one SVG favicon and no manifest (tools/sitegen/core.py:1739-1740 emit theme-color and the SVG icon link only; assets/ holds css/, js/ and favicon.svg; tools/build.py:300 copies assets/*.* into the build). iOS 'Add to Home Screen' looks for apple-touch-icon and shows a page snapshot without one; Android Chrome's menu still offers 'Add to Home screen' for any page but makes a plain shortcut with a generated letter tile, and its install prompt needs a manifest with icons.

**Evidence.** `tools/sitegen/core.py:1739-1740 (theme-color and the SVG favicon only)`; `assets/ (css, favicon.svg, js)`; `tools/build.py (assets/*.* copied to the site)`; `tools/sitegen/core.py:1740`; `assets/ (favicon.svg only)`; `tools/build.py:300`; `/usr/bin/qlmanage (SVG to PNG checked)`.

**Proposal.** Add assets/apple-touch-icon.png (180×180) and assets/icon-512.png rendered from favicon.svg with sips (sips -s format png -z 180 180 assets/favicon.svg works; qlmanage -t -s 512 also does), plus assets/site.webmanifest with name, short_name, start_url under the project path, display: browser, background_color and theme_color #F2F1EC and the icons; emit <link rel="apple-touch-icon"> and <link rel="manifest"> in core.document. sitecheck reads every double-quoted href (tools/sitegen/sitecheck.py:244), so the two new hrefs are verified in the build. Files unchanged.

**Files.** `assets/apple-touch-icon.png`, `assets/icon-512.png`, `assets/site.webmanifest`, `tools/sitegen/core.py`, `tools/build.py`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Also covers.** seo-15 (merged into this finding).

**Risk.** start_url must carry the /personal-website/ prefix; keep display: browser (no app shell or offline cache is wanted).

**Review note (condensed; the observation and proposal above are the revised text).** Feasible and nearly free: core.py:1739-1740 emits only theme-color and the SVG favicon; build.py:300-303 copies every assets/*.* file (so a PNG and a manifest need no build change, contrary to the file list); sitecheck reads every double-quoted href (sitecheck.py:244), so the new links are verified; favicon.svg is a simple mark that rasterises cleanly. Observation reproduces: core.py:1739-1740 emit only theme-color #F2F1EC and the SVG icon link, no manifest or apple-touch-icon anywhere in tools/; assets/ holds css/, js/ and favicon.svg; build.py:300 copies assets/*.* into the build.

#### gap5-01. Add a Get-in-touch line to About and the footer, driven by a content file

**Observation.** The About page's only external hrefs in the build are Google Fonts and its own canonical, and its Follow section is RSS alone (about.py:132-140); about.py:4 states "No bio, portrait or email until Eric writes them." The footer (core.py:1686-1698) carries the brand, the two hard-coded facts BASED IN LAKE TAHOE · AIARE 2, the Reports and Site lists, RSS, the disclaimer, map credits and the copyright, and no mailto: or profile link exists anywhere in tools/sitegen (grep); the review check recorded "No email address ... or third-party account link anywhere in the build" (IMPLEMENTATION_REPORT.md:776-777). A partner or route searcher who finds a report has no way to ask about it. The footer's two facts fit the audience (region and avalanche training) and the one-sentence who-I-am already exists as the tagline on Home and About (core.py:25, about.py:61-62), so what the footer lacks is an action, not a sentence.

**Evidence.** `tools/sitegen/pages/about.py:4`; `tools/sitegen/pages/about.py:132-140`; `tools/sitegen/core.py:1686-1698`; `tools/sitegen/core.py:25-31`; `docs/IMPLEMENTATION_REPORT.md:776-777`; `_site/about/index.html (external hrefs: fonts.googleapis.com, fonts.gstatic.com only)`; `.cache/plan2/shots/desktop-about.jpeg`; `.cache/plan2/shots/phone-about.jpeg`; `docs/PRIVACY_NOTES.md:141-207 (section 6, decision 6: history is never rewritten)`.

**Proposal.** Decision for Eric first: publish an alias address he is willing to keep public for good (PRIVACY_NOTES section 6, decision 6; about.py:4 deferred this to him). Only on a yes: create content/author.json with keys email (optional string) and links (list of {label, url}, used by gap5-03), read by a small strict loader tools/sitegen/author.py modeled on curation.load_manifest (unknown keys, non-strings and duplicates stop the build naming the file; a missing file means no contact row and no warning). Validate with AUTHOR_KEYS beside HOME_KEYS (checks.py:68) and _author_findings beside _home_findings (checks.py:906). Render: the About Follow section becomes "Follow & contact" with a .btn mailto: link plus the address written out as text (as the feed URL is at about.py:137-138); the footer .f-brand block gets one 44 px row under the two facts (base.css:234-252). Leave the BASED IN / AIARE 2 literals where they are and add no newsletter key. Document in README.md beside "Feature a trip on the home page" and in CONTENT_GUIDE.md; PRIVACY_NOTES gains one line saying an email is published. Tests: extend tests/test_nav.py (footer) and add tests/test_about_follow.py with a fixture address on example.test (IMPLEMENTATION_REPORT.md:789). Effort M.

**Files.** `content/author.json (new)`, `tools/sitegen/author.py (new)`, `tools/sitegen/core.py`, `tools/sitegen/pages/about.py`, `tools/lib/checks.py`, `assets/css/base.css`, `assets/css/pages/about.css`, `README.md`, `docs/CONTENT_GUIDE.md`, `docs/PRIVACY_NOTES.md`, `tests/test_nav.py`, `tests/test_about_follow.py (new)`.

**Effort.** M. Visitor value 2.7, author value 2.3, confidence high.

**Risk.** An address committed to the public repository stays in git history for good (PRIVACY_NOTES section 6, decision 6), so it should be an alias Eric is willing to keep public; PRIVACY_NOTES.md needs a line saying an email is published. The renderers must emit nothing when the file is absent or the key is empty, and the footer row must keep the 44 px target rule (base.css:238-243).

**Decision for Eric.** Which path: (A) a plain mailto: with a dedicated public alias (simplest, works without JavaScript, readable by friends; bots will scrape it); (B) an obfuscated address (HTML entities stop no bot, and a JS-assembled address hides it from no-JS readers against the site's no-JS rule; not recommended); (C) a hosted contact form (the first third-party endpoint on the site, needs spam control, every message passes through a provider); (D) none, relying on the repository issue link (gap5-02) and profile links (gap5-03). Also whether the footer carries the address on every page or About alone, and whether BASED IN and AIARE 2 move into the content file as proposed.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible and in the repo's own pattern: a stdlib JSON file with a strict loader like curation.load_manifest (curation.py:45-58), validated beside HOME_KEYS (checks.py:68) and _home_findings (checks.py:906), rendering nothing when absent; the footer brand column is 4 of 12 columns from 1000 px (base.css:248) so one 44 px row fits; sitecheck already skips mailto: (sitecheck.py:230).

#### gap5-08. Put an "Ask about this trip" link on every report once an address exists

**Observation.** The visitors the brief names (partners, people searching for a route or a peak) arrive on a report page, not on About. The report's actions are View route or Read the report, Download GPX and Copy link (report.py:104-131, .rep-actions), on phones the rep-share row holds Copy link alone (report.py:70-73) and the bottom bar the sections and GPX; none reaches the author, and About, two taps away through the menu, holds no contact either (gap5-01). Multi-day and series pages share the same title block (multiday.py:785, series.py:507).

**Evidence.** `tools/sitegen/pages/report.py:70-73`; `tools/sitegen/pages/report.py:104-131`; `tools/sitegen/pages/report.py:607`; `tools/sitegen/pages/multiday.py:785`; `tools/sitegen/pages/series.py:507`; `assets/css/pages/report.css:160-179`; https://esichak.github.io/personal-website/feed.xml (several items titled Tallac on different dates).

**Proposal.** When content/author.json carries email (gap5-01), add to the actions passed to report.title_block on single-day, planned, multi-day and series pages (report.py:607 and :561, multiday.py:785, series.py:507) an .alink "Ask about this trip" whose href is mailto:<email>?subject=<title> (<date>), with the subject built from the trip's own title and date (facts from content; a planned route uses its name and PLANNED) and urllib.parse.quote'd so an apostrophe or ampersand in a title cannot break the href, then esc()'d. Phones differ by page type: single-day and planned pages hide the title actions through body.p-report .rep-actions{display:none} (report.css:46) and multi-day pages through body.p-multiday .rep-actions{display:none} (multiday.css:23); all three render report.share_row (report.py:644, :561; multiday.py:793), so there the same link also goes in the rep-share row outside the .copy span, because report.css:179 hides .copy and the whole row without scripting; give the row its own rule so the mailto stays visible without JavaScript. The series page keeps its title actions visible on phones (series.css:12-16) and renders no share row, so on the PCT page the link lives in the title actions only. Leave the bottom bar alone (Map · Beta · Report · GPX, report.py:324-326). Render nothing when no email is configured. Tests in tests/test_report_page.py (single-day and multi-day pages; there is no separate multi-day test module) and tests/test_series_page.py. Risk, corrected: the same address appears on the 168 pages that carry the title block (grep of _site/trips/*/index.html for class="rep-title"); that is no exposure beyond gap5-01 but makes scraping certain, so the alias choice there matters. The date in the subject is needed because titles repeat (the live feed lists four items titled exactly 'Tallac' on different dates); it is the trip date already shown on the page, nothing new.

**Files.** `tools/sitegen/pages/report.py`, `tools/sitegen/pages/multiday.py`, `tools/sitegen/pages/series.py`, `assets/css/pages/report.css`, `tests/test_report_page.py`.

**Effort.** S. Visitor value 2.3, author value 1.7, confidence high.

**Risk.** The same address appears on 170-plus pages; that is no exposure beyond gap5-01 but makes scraping certain, so the alias choice there matters. The date in the subject is needed because titles repeat (the live feed lists several reports titled Tallac on different dates); it is the trip date already shown on the page, nothing new.

**Decision for Eric.** Depends on gap5-01's choice of path; whether the link reads Ask about this trip or a wording of his own, and whether multi-day and journal pages carry it too.

**Review note (condensed; the observation and proposal above are the revised text).** The observation reproduces: share_row at report.py:70-73 holds the copy control alone; title_block's actions at report.py:104-131; the single-day page's actions are View route / Read the report, Download GPX and copy_link (report.py:600-607); multiday.py:785 and series.py:507 share title_block; report.css:160-179 and the live feed has seven items titled Tallac or a variant (four exactly 'Tallac').

#### gap5-03. Profile links with rel=me on About and in the footer, only those Eric names

**Observation.** Strava is named on the About page (about.py:100: tracks are "exported through Strava") and under every stats strip (core.py:1045: "Stats from the GPS recording via Strava."), yet nothing links to a profile there or anywhere else: no Strava, Instagram, GitHub or other profile href exists in tools/sitegen (grep). The BlogPosting author is a Person with only a name and the About URL (core.py:1577), so About is the identity page a reader lands on, and it offers no way onward. seo-06's sameAs only makes sense once such links are on the page; this finding supplies them.

**Evidence.** `tools/sitegen/pages/about.py:98-105`; `tools/sitegen/core.py:1041-1045`; `tools/sitegen/core.py:1570-1580`; `tools/lib/icons.py (icon names: no brand marks)`; `.cache/plan2/shots/desktop-about.jpeg`.

**Proposal.** Use the links list of content/author.json (gap5-01): [{"label": "Strava", "url": "https://..."}], validated as https only, at most six, unique labels. Render on the About "Follow & contact" section only, as a row of outline .btn links by word with the existing arrow-right icon, each rel="me noopener". The footer stays as gap5-01 leaves it. Nothing renders while the list is empty, and the list stays empty until Eric names the services and handles himself. seo-06's sameAs reads the same list once it exists. Depends on gap5-01 being accepted. Effort S.

**Files.** `content/author.json`, `tools/sitegen/author.py (new)`, `tools/sitegen/pages/about.py`, `tools/sitegen/core.py`, `assets/css/base.css`, `assets/css/pages/about.css`, `tools/lib/checks.py`, `tests/test_about_follow.py (new)`, `tests/test_nav.py`.

**Effort.** S. Visitor value 2, author value 1.3, confidence high.

**Risk.** A profile link invites cross-referencing the dated, timed tracks here with whatever the profile makes public elsewhere; the site itself publishes nothing new, so PRIVACY_NOTES stays at its level, but the decision is Eric's. Never guess a service or handle: the list is empty until he fills it.

**Decision for Eric.** Which services, if any. Strava: the site already names it as the source, and one link makes following or messaging him one tap, but the profile shows what Strava makes public (followers, segment times, the activity list) which the site does not. GitHub: the person profile is one step beyond the repository link of gap5-02. Instagram or others only if Eric names them.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible and cheap once gap5-01's loader exists (S is honest), content-driven, empty until Eric fills it, and the word-only rendering is right because tools/lib/icons.py has no brand marks (verified: download, expand, arrow-right, ... rss, north, link). The identity page argument holds: BlogPosting's author is a Person with only a name and the About URL (core.py:1577), so About is where a reader lands.

#### gap5-05. Land the RSS links on a Follow section instead of raw XML

**Observation.** The footer "RSS" link (core.py:1689) and the About "RSS feed" button (about.py:139) both open feed.xml directly. Live, GitHub Pages serves it as content-type: application/xml (curl -I https://esichak.github.io/personal-website/feed.xml on 2026-10-13), so a browser, phone Safari included, shows XML rather than a subscribe flow; a real phone was never tried (IMPLEMENTATION_REPORT.md 15.5). Feed readers do not need that link: every page head carries <link rel="alternate" type="application/rss+xml"> (core.py:1740, _site/index.html). The About section already prints the address as text (about.py:137-138; desktop-about.jpeg), but nothing says what to do with it.

**Evidence.** https://esichak.github.io/personal-website/feed.xml (curl -I: content-type application/xml); `tools/sitegen/core.py:1689`; `tools/sitegen/core.py:1740`; `tools/sitegen/pages/about.py:132-140`; `tools/sitegen/core.py:1340-1351`; `assets/js/base.js:397`; `assets/css/pages/report.css:179`; `tools/sitegen/sitecheck.py:281`; `.cache/plan2/shots/desktop-about.jpeg`; `.cache/plan2/shots/phone-about.jpeg`.

**Proposal.** Give the About section id="follow" and point the footer link (core.py:1688-1689) at about/#follow, labeled "Follow" with the RSS icon kept; the built-site check verifies a link into another page's section in sitecheck.links() (sitecheck.py:243-278, the BROKEN ANCHOR line at :276-277), while anchors() at :281 covers same-page href="#x" only. In the section: one plain sentence, paste this address into a feed reader (name two or three, e.g. NetNewsWire, Feedly, Reeder, after checking they are current); the address in a core.copy_link(feed_url, 'Copy feed address', cls='btn') control (core.py:1340; base.js:394 reads data-copy, so it is not tied to page URLs; without scripting the control hides per report.css:179, which is in the one site-wide bundle, and the text address at about.py:138 stays); and the raw link kept as "Open feed.xml" with type="application/rss+xml" for browser extensions and desktop readers that act on a feed link. Do not take the XSLT route (an xml-stylesheet that renders the feed as a page): Chromium has announced the removal of XSLT support, so verify its status in the session before relying on it. Tests: tests/test_nav.py for the footer href and tests/test_about_follow.py for the block. EVIDENCE CORRECTION: the <link rel="alternate" type="application/rss+xml"> is at core.py:1741.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/about.py`, `assets/css/pages/about.css`, `tests/test_nav.py`, `tests/test_about_follow.py (new)`.

**Effort.** S. Visitor value 2, author value 1, confidence medium.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.5 (a real phone never tried)

**Risk.** A feed-savvy visitor who right-clicks the footer link to copy the feed address now gets the About anchor; the section answers that with the copy control and the raw link, so keep both. Reader names are site copy, not facts about trips; keep them to a short list Eric approves.

**Decision for Eric.** Whether the footer word stays RSS (familiar to feed users) or becomes Follow, and which reader apps, if any, to name.

**Review note (condensed; the observation and proposal above are the revised text).** Not built: core.py:1689 links the footer RSS to feed.xml, about.py:139 links the button to feed.xml, no id="follow" or #follow exists in tools/ or assets/ (grep), and the live feed answers content-type application/xml (curl -I 2026-10-13). core.document emits <link rel="alternate" type="application/rss+xml"> (core.py:1741); core.copy_link takes any URL via data-copy (core.py:1340-1349, base.js:393); report.css:179 hides .copy without scripting; IMPLEMENTATION_REPORT.md:855 confirms no real phone was tried. The observation reproduces: curl -I on the live feed.xml returns content-type: application/xml; the footer RSS link is core.py:1688-1689 and the About button about.py:139, both to feed.xml; the address is printed as text at about.py:137-138 with no instruction; every page head has <link rel="alternate" type="application/rss+xml"> (seen in _site/index.html), and IMPLEMENTATION_REPORT.md:853-854 lists a real phone among what was not run.

#### gap5-07. Decide the email path: reader-side RSS-to-email now, a hosted list only if chosen

**Observation.** The 2026-10-08 plan called an email newsletter a separate decision (docs/personal-website-improvement-plan.md:601) and no first-round finding takes it up. The site has no third-party endpoint besides Google Fonts and no analytics (IMPLEMENTATION_REPORT.md:776-777; the About build's external hrefs are fonts.googleapis.com and fonts.gstatic.com only). The feed is the only follow path, and each item is the factual summary plus up to 400 characters of the write-up (build.py:230-233), so an email built from it would be a stub that links to the page, which is the right shape for a static site and needs no new content.

**Evidence.** `docs/personal-website-improvement-plan.md:597-601`; `docs/IMPLEMENTATION_REPORT.md:776-777`; `tools/build.py:225-240`; `tools/sitegen/pages/about.py:132-140`; `_site/about/index.html (external hrefs)`.

**Proposal.** Record the email question as a decision for Eric with the two paths and trade-offs: (1) reader-side RSS-to-email, no service, no addresses held; (2) an Eric-run list through an RSS-to-email provider, which adds the site's first third-party endpoint, subscriber data he is responsible for, a form that can die when the provider changes, and a PRIVACY_NOTES section. Build only path 1, as one sentence in gap5-05's Follow section ("prefer email? an RSS-to-email service turns this feed into messages"), naming at most two long-running services Eric approves after their current status is verified in the session. Add no author.json key, no validator rule and no separate test file for path 2 until he names a provider. Effort S.

**Files.** `tools/sitegen/pages/about.py`, `content/author.json`, `tools/sitegen/author.py (new)`, `tools/lib/checks.py`, `docs/PRIVACY_NOTES.md`, `tests/test_about_follow.py (new)`.

**Effort.** S. Visitor value 1, author value 1.3, confidence high.

**Already known.** docs/personal-website-improvement-plan.md section 18 (plan:601)

**Risk.** Path 2 adds a service that can change terms or lapse, and a dead form on a static page is worse than none; sign-up spam needs the provider's protection; subscriber emails become data Eric is responsible for. Path 1 names outside services in site copy, so keep the names few and checked.

**Decision for Eric.** Path 1 (zero cost, no data held, readers do the work), Path 2 (a provider, its cost at the subscriber counts Eric expects, double opt-in, a subscriber list he holds), or none. For Path 2 also which provider and whether its form may be the first third-party request on the site.

**Review note (condensed; the observation and proposal above are the revised text).** The brief allows a newsletter to be proposed as Eric's decision with trade-offs, and the plan left it open (plan:601), so the decision framing is fair. Path 1 is feasible but is one sentence of copy naming outside services that may lapse, which belongs inside gap5-05's Follow section rather than as its own build with a validator key and a test file. The observation holds: docs/personal-website-improvement-plan.md:601 says 'Dark mode, an email newsletter, analytics, and a custom domain are separate decisions.'; IMPLEMENTATION_REPORT.md:776-777 records no third-party endpoint but Google Fonts; build.py:230-233 builds each feed item from core.summary plus core.excerpt(t, 400); follow() at about.py:132-140 is the only follow path and _site/about/index.html's external hrefs are the two Google Fonts hosts.

#### gap5-02. Link the public repository and an issue path from the footer and About

**Observation.** No page links to the repository: grep of tools/sitegen finds no github.com href, and the About build's only external hrefs are Google Fonts. The repository is public with issues enabled and discussions off (gh repo view esichak/personal-website --json hasIssuesEnabled,isPrivate,hasDiscussionsEnabled on 2026-10-13: true, false, false). A reader who finds a broken link or a mis-named peak has no path to say so except guessing the repository from the site's URL, which already contains the GitHub user name, so a link adds no exposure. The site check skips links to other sites (sitecheck.py:230), so an external link can be added without touching the checker.

**Evidence.** `tools/sitegen/core.py:1686-1698`; `tools/sitegen/sitecheck.py:230`; `_site/about/index.html (external hrefs)`; https://github.com/esichak/personal-website (gh repo view, 2026-10-13: public, issues enabled); `tests/test_nav.py:153-154`.

**Proposal.** Add REPO_URL = 'https://github.com/esichak/personal-website' beside SITE_URL in core.py and append "Source on GitHub" to the footer Site list after RSS (core.py:1687-1688; tests/test_nav.py:153 asserts the list starts with Trips, so append). In the About method list (about.py:98-117) add one item: the site is built from a public repository; to report a broken link or a wrong name, open an issue (REPO_URL + '/issues/new'), with the honest note that it needs a GitHub account and is for problems with the site, not private questions. Add a test that REPO_URL's owner matches the host of SITE_URL so a renamed repository is caught locally. No per-page "Report a problem" link. Effort S.

**Files.** `tools/sitegen/core.py`, `tools/sitegen/pages/about.py`, `tools/sitegen/pages/report.py`, `tests/test_nav.py`, `tests/test_about_follow.py (new)`.

**Effort.** S. Visitor value 1.3, author value 1.7, confidence high.

**Risk.** None for privacy (the repository is already public and named by the site's own URL). A dead link to a renamed repository would not be caught by build.py --check; hence the test. Issues are public, so the About wording should say the issue path is for problems with the site, not for private questions (gap5-01 covers those).

**Decision for Eric.** Whether the code and content folder should be one click from the site at all, and whether to prefill an issue title per page.

**Review note (condensed; the observation and proposal above are the revised text).** The footer link and the About item are feasible, S and honest: the repository is public with issues on (gh repo view on 2026-10-13: isPrivate false, hasIssuesEnabled true), the site URL already names the GitHub user, the check skips other sites (sitecheck.py:230), and tests/test_nav.py:153-158 only pins the first Site link so appending is safe.

**Gates.** The phase is done when every line below holds and is recorded in the log entry:

1. Every trip page's <title> and og:title read '{title} · {activity}, {place or region}[, short date] · Eric Sichak' with the skip-when-already-in-the-title rule; test_metadata.py's two title tests updated; the no-two-indexable-pages-share-a-title test still passes.
2. 0 of the 168 trip descriptions end in '…' when facts lead (summary written whole), and written-led ones cut at a sentence end between 80 and 160 characters; python3 tools/share_preview.py prints one line per indexable page with the flag counts (no image 62 today, description ending in '…' 0, titles over 60 characters N, WebP image, portrait image) and is named in the README as a pre-deploy step; CONTENT_GUIDE's og:image grep replaced by the tool.
3. og:site_name and og:locale on every page, article:author/section/tag on reports from index.md fields, a BreadcrumbList on report, multi-day, series, goal, region and section pages built from the visible crumbs; sitecheck allows BlogPosting and BreadcrumbList, at most one each; DEVELOPING.md:81-85 and CONTENT_GUIDE §9 updated; Eric runs one report and the home through Google's Rich Results Test after deploy and logs it.
4. Asset versioning: every page links assets/site.css?v=<8-hex> and assets/site.js?v=<hex>; document() called without the version still emits the bare names (tests); curl -I on the live versioned asset answers 200 with max-age=600; sitecheck strips '?'.
5. Fonts (if yes): the four Latin woff2 files and the three OFL texts are committed under assets/fonts/ by tools/fonts.py, fonts.css is first in the bundle with font-display: swap and Latin unicode-range, build.py copies assets/fonts/, the head preloads Archivo and Source Serif 4 regular only and no request goes to fonts.googleapis.com or fonts.gstatic.com on the live page; desktop first paint (25 runs, DEVELOPING.md:1428 method) now follows site.css, with the ms before and after recorded; a test checks every @font-face src names a copied file.
6. The ski page head carries the two media-scoped preload pairs (4 preloads like the other section pages, loading=lazy kept); the hiking page's three journal thumbnails name the .th file first in srcset (229 KB to 72 KB measured on the phone profile).
7. feed.xml carries content:encoded with the verbatim write-up, day sections and .sm photo URLs on written items, validates in the W3C feed validator once, and the byte-pinned test is updated; assets/apple-touch-icon.png (180×180 from favicon.svg) is linked from every head; README has the Search Console section and VERIFY_TAGS is written only when set; Eric has a verified property with sitemap.xml submitted and the note that a project-path robots.txt is not read (user-site repository optional); DEVELOPING.md records that track-only reports stay indexed and a test pins no robots meta on them.
8. Contact (only after Eric names an alias): with no content/author.json the build is byte-identical; with it, About's 'Follow & contact' shows a mailto .btn and the address as text, the footer gains one 44 px row, every title block (168 pages, per-page-type phone placement) carries 'Ask about this trip' with the title and date URL-encoded in the subject, rel=me profile links appear on About only for the services he named, a one-sentence RSS-to-email note sits in the Follow section, the footer's RSS link lands on about/#follow with a copy-feed-address control and the raw feed link kept, 'Source on GitHub' is appended after RSS (test_nav's list still starts with Trips) and PRIVACY_NOTES states that an email is published; tests/test_about_follow.py and test_nav.py green.
9. A real share preview was looked at once: the Matterhorn report, a portrait-cover report and the home pasted into the Facebook Sharing Debugger or opengraph.xyz and an iMessage thread, with what each drew written in the log (closes 15.5's item); seo-04's 1200×630 crops are built only if a previewer failed to draw the WebP or cut a portrait cover.
10. Both Pythons with -W error and build.py --check pass; the compatibility rule holds (titles in H1 and BlogPosting headline unchanged).

**Tests to add.** New: `tests/test_about_follow.py`, `tests/test_share_preview.py`. Extended: `tests/test_build_site.py`, `tests/test_metadata.py`, `tests/test_nav.py`, `tests/test_privacy_audit.py`, `tests/test_report_page.py`, `tests/test_series_page.py`, `tests/test_sitecheck.py`, `tests/test_ticklist_page.py`. Plus the checks the gates name that no unit test covers: `curl -I` on the live versioned asset; the W3C feed validator once; Google's Rich Results Test on one report and the home; desktop first paint over 25 runs before and after the fonts; the share previews looked at by a person.

**Screenshots to capture.** The Facebook Sharing Debugger or opengraph.xyz result and an iMessage thread for the Matterhorn report, a portrait-cover report and the home; About's Follow & contact section at 390 and 1280 px; the footer row with the new link; the ski page's network panel showing the two preloads.

**Author inputs needed.** Decisions 16 to 20: the fonts, a public alias he will keep, which profile links, Search Console on his Google account, the share image after the preview check.

### Phase 15. Renderer round and storage budget

**Goal.** Land every surviving renderer change in one VERSION bump with a safety net built first (offline golden and contract tests, a before/after contact sheet, a resumable budgeted run, the renderer version recorded in meta.json, a bounded tile cache), re-render on Eric's Mac over one evening with warm caches, commit rendered/ by path, and write the storage budget, size report and yearly checklist.

**Prerequisites.** Phases 6 (render staging folder, caches out of iCloud) and 8 (publish by path, tidy); the page phases landed so one round carries everything, including maps-01 part 3 (contour labels in both units), visual-01 step 2 (the 400×267 card tile) and copy-16's region merges (a site render). Eric's decisions: the hillshade quality from a side-by-side preview, and the evening for the run.

**Decisions this phase waits on.**

- Hillshade WebP quality from the side-by-side (perf-05; recommended q80 if it passes, else keep 88)
- When to run the round (recommended: one evening after Phases 10-14 land, warm caches, --jobs 2; then once a year)

**Findings in this phase** (18, in working order): maps-16, gap9-01, gap9-02, gap9-04, gap9-05, gap9-08, gap9-09, maps-03, maps-05, maps-15, maps-06, perf-05, copy-18, gap10-01, gap10-02, gap10-03, gap10-04, gap10-06.

#### maps-16. Batch every renderer change into one VERSION bump and re-render

**Observation.** Each renderer change (maps-01 part 3, 03, 05, 06, 11, 12, 15) needs tools/render.py on Eric's Mac and a commit of rendered/ (3,393 tracked files, 48.6 MiB, beside about 6,100 iCloud conflict copies that .gitignore:7-12 keeps out of git); a VERSION bump (tools/render.py:31) re-renders everything. One more renderer nit belongs in the same bump: the wide map's scale bar is capped at 120 px (tools/lib/mapkit.py:1441), so the 12.8-mile Matterhorn map shows a '0 to 0.5 mi' bar 64 px long in a 1440 px frame. Evidence correction: the terrain-only fallback is tools/render.py:153-166 (fetch_osm records OSM_FAILED) and :475-476 (meta hash set to None).

**Evidence.** `tools/render.py:31 (VERSION = 7), tools/render.py:430-434 and :455-458 (hash per trip), :638-645 (site hash)`; `tools/lib/mapkit.py:1441 (cap_px = min(80 if w <= 400 else 120, ...))`; `rendered/trips/matterhorn-peak-west-couloir/map-wide.svg.html (scale rects 32 + 32 px)`; `tools/lib/geo.py:178-219 and :458-482 (tile and OSM caches keyed by tile and query), tools/render.py:153-166 (terrain-only fallback sets meta.hash None)`; `docs/DEVELOPING.md:1219-1241 (rendered names and sizes)`.

**Proposal.** Keep as the single gate for whichever renderer findings survive: land them on one branch, bump VERSION once, raise cap_px to 200 for w >= 1200 (mapkit.py:1441) so 1 mi / 2 km bars fit, add tools/render.py --dry-run that lists which trips and site jobs would re-render and which hash input changed (trip_inputs at render.py:430-434, the site hash at :638-645) before anything is written, then run render.py with warm caches, git diff --stat rendered/ to confirm the hillshade .webp files are unchanged and only .svg.html and meta.json moved, grep rendered for '"hash": null' (render.py:475-477, :694-695 write it after an OSM failure, Overpass timeout 160 s at geo.py:505) and re-run those trips before committing, stage rendered/trips and rendered/site by path and read git status --short for ' 2'/' 3'/' 4' names, then update the names and sizes in DEVELOPING.md:1219-1241 and the timing in ADDING-TRIPS.md:63. Effort M for the code and docs; the render run is wall-clock, one evening, never in CI.

**Files.** `tools/render.py`, `tools/lib/mapkit.py`, `docs/DEVELOPING.md`, `ADDING-TRIPS.md`, `rendered/`.

**Effort.** M. Visitor value 1, author value 3.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 10 (drafts and off-site renders) and the workspace CLAUDE.md render notes

**Risk.** A full re-render is long (Overpass retries, 180 s cap per fetch) and can commit terrain-only maps silently; disk pressure during the run (iCloud offloading has broken the git index before); never run render.py in CI.

**Review revision (applies on top of the text above).** Proposal: as written, except drop the 'read git status --short for " 2"/" 3" names' step (those names are ignored, so neither git add -A nor git status shows them); keep staging rendered/trips and rendered/site by path as a habit. The rest stands: one branch, VERSION 8, cap_px 200 for w >= 1200, warm-cache render, git diff --stat rendered/ to confirm .webp files unchanged, check no meta.json has hash null, update DEVELOPING.md names and sizes and ADDING-TRIPS.md:63 timings, and add tools/render.py --dry-run.

**Review note (condensed; the observation and proposal above are the revised text).** Everything checkable is verified: VERSION = 7 feeds both the trip hash and the site hash (tools/render.py:31, :434, :638), a failed OSM fetch leaves hash None so the next run retries (render.py:475-477 and :694-695, not :153-166 as cited, which only records the failure), there is no --dry-run among the flags (render.py:703-709), cap_px is min(120, 0.25·w) for wide maps (tools/lib/mapkit.py:1441, SCALE_MAX_FRAC at :1761) and the Matterhorn wide map shows a 32 + 32 px bar for 0.5 mi. Almost everything reproduces: VERSION = 7 at render.py:31; trip_inputs hashes VERSION at :430-434 and render_trip compares it at :457; the site hash at :638-645; cap_px = min(80 if w <= 400 else 120, SCALE_MAX_FRAC * w) at mapkit.py:1441 with SCALE_MAX_FRAC 0.25 (:1761); the Matterhorn wide render (1440x640, 20.57 km = 12.8 mi) carries '0 / 0.5 mi' rects of 32 + 32 px; geo.py caches tiles by (z, x, y) and Overpass answers by sha1(query) (:461-462); 3,393 tracked files under rendered/ totalling 51.0 MB (48.6 MiB); ADDING-TRIPS.md:63 says a render takes about a minute; render.py has no --dry-run (:702-709).

#### gap9-01. Offline golden test for render_map, render_profile, render_tile and render_glyph

**Observation.** The tests touch mapkit only through MAP_CSS, Track and line_links (tests/test_build_site.py:608, tests/test_gpxroute.py:600-610, tests/test_region_days.py:587-613), and tests/test_render_goals.py stubs render_map, fetch_osm, render_single and optimize_images (docstring, lines 1-7); tests/ holds GPX fixtures but no DEM tile or Overpass answer. A probe written for this review (the review's scratch files/probe.py) replaced geo.get_tile with a synthetic 2 km hill and passed a five-element Overpass dict as spec['osm_data'], and render_map (map-wide, map-col, map-phone), render_profile, render_tile, render_glyph and render_sparkline all ran offline: 16.3 s on Python 3.9.6, 9.7 s on Homebrew 3.12.11. The 21 output files (overlays, base.svg, palette PNGs, per-map meta.json) were byte-identical across PYTHONHASHSEED 0, 4242 and 7 and across 3.9 vs 3.12; the only sets in render_map (mapkit.py:1158, 1238/1546/1604 `_prio_done`, 1366, 1536, 1645-1646, 1679) are built for membership tests and never iterated, mapkit imports no time, datetime or random, and cwebp is optional (render.py:50-53), so the renderer is deterministic from its inputs.

**Evidence.** `a reviewer's probe script run against tools/render.py on 2026-10-13`; `that probe's recorded output`; `that probe's recorded output`; `tests/test_render_goals.py:1-7`; `tests/test_build_site.py:608-609`; `tests/test_gpxroute.py:600-610`; `tests/test_region_days.py:587`; `tools/lib/mapkit.py:782`; `tools/lib/geo.py:179-217`; `tools/render.py:50-53`; `tools/lib/mapkit.py:1756`.

**Proposal.** Add tests/render_fixtures.py (a ground(lat, lon) hill around the invented spot 38.9 N 120.1 W of tests/gpx_fixtures.py, a synth_tile(z, x, y) that fills a 256x256 Terrarium-style list from it, and one hand-written Overpass dict with a named lake, a primary road with a ref, a path, a named peak and a village) and tests/test_mapkit_golden.py with golden files under tests/golden/render/<case>/. Three cases: a hike loop (render_map map-wide, map-col, map-phone; render_profile; render_tile; render_glyph; render_sparkline), an mtb out-and-back (is_out_and_back, outbound_only, chevrons) and a two-segment planned route (gpxroute.as_tracks of gf.MULTISEG). Build the specs from render.REPORT and render.SMALL exactly as render_single does (render.py:224-233), with mock.patch.object(geo, 'get_tile', synth_tile) and mapkit.FRAG = mapkit.MAPPNG = a temp dir. Hillshade only on the hike loop's map-phone (2.4 s in the probe) and hillshade=False everywhere else, so the module adds about 10 s on 3.9 and less in CI. Compare the .svg.html and .base.svg text exactly, the per-map .meta.json with floats rounded to 2 dp, and for the PNG only width, height and a sha1 of png_read()'s pixel bytes (never the WebP: cwebp is absent in CI and its version changes bytes). UPDATE_GOLDEN=1 rewrites the goldens; a failure prints a unified diff of the SVG split at '>'. If the first CI run on Ubuntu differs from the Mac goldens in a last digit, compare path numbers with a 0.11 px tolerance instead of exact text. Document the command under 'Checking your work' in docs/DEVELOPING.md (line 1242) with the rule that a renderer change ships with regenerated goldens and a reviewed diff. A ski case (skin=True) and a flat 'other' case with times (render_speed_chart) can be added when a finding touches those paths. Effort: M.

**Files.** `tests/test_mapkit_golden.py`, `tests/render_fixtures.py`, `tests/golden/render/`, `docs/DEVELOPING.md`, `tools/lib/geo.py`, `tools/lib/mapkit.py`.

**Effort.** M. Visitor value 1, author value 3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 4 ('The map renderer' was never run) and 15.5

**Risk.** Goldens change with every intended renderer change (maps-01 to maps-18, report-08, perf-03 to 05, seo-05, visual-12 each regenerate them), which is the point but adds a review step. Linux libm in CI could in rare cases flip a 0.1 px digit against the Mac goldens; if that happens, compare path numbers with a 0.11 tolerance instead of exact text. Fixture coordinates are the synthetic spot of gpx_fixtures.py: no real trip, no privacy specifics.

**Review revision (applies on top of the text above).** Proposal: unchanged except: build the specs from render.REPORT and render.SMALL exactly as render_single does at render.py:236-243; hillshade=False is honoured at mapkit.py:782-800. Files: tests/test_mapkit_golden.py, tests/render_fixtures.py, tests/golden/render/, docs/DEVELOPING.md (tools/lib/geo.py and tools/lib/mapkit.py are only patched at test time, not changed).

**Review note (condensed; the observation and proposal above are the revised text).** Feasible and proven: the probe's 21 files are byte-identical across PYTHONHASHSEED 0 and 4242 and across Python 3.9.6 and 3.12.11 (run-a, run-b, run-312 _probe.json compared this session), it is stdlib-only, needs no network, and CI never renders so the test is the only coverage mapkit's 2,473 lines of drawing code would get. Reproduced: the probe (finder-gap9/probe.py) wrote 21 files in run-a (seed 0), run-b (seed 4242) and run-312 (Python 3.12.11, seed 7), and every sha1 matches across the three runs; timings sum to 16.27 s on /usr/bin/python3 3.9.6 and 9.72 s on 3.12. tests/test_render_goals.py:1-7 names the stubs; tests touch mapkit only through MAP_CSS (test_build_site.py:608), Track (test_gpxroute.py:600-610) and line_links/LINE_HIT (test_region_days.py:587-613); tests/ holds no tile, DEM, Overpass or golden fixture; mapkit imports no time/datetime/random; cwebp optional at render.py:50-53; hillshade=False skips the PNG (mapkit.py:782-800).

#### gap9-02. Before/after contact sheet of a fixed map sample (tools/render_sheet.py)

**Observation.** A map on the site is three files assembled by core.map_block (hillshade webp img, base.svg img, overlay .svg.html inlined; core.py:484-530), so git diff cannot show what a re-render changed, and render.py deletes mapkit's per-map .meta.json, which held base_gz_kb, bytes and m_per_px (render.py:472-474, mapkit.py:1739, 1756). The two commits that rewrote most of rendered/ touched 2,604 and 2,831 files under it (git diff-tree -r 6abc634 -- rendered; a9baab9); rendered/ is 3,393 tracked files, and the three journal-overlay renders of 10-12/13 were checked by comparing pictures side by side in Chrome by hand (log:1004-1006). maps-16 batches a dozen renderer findings into one VERSION bump, but nothing gives Eric a way to look at the result before git add.

**Evidence.** `tools/sitegen/core.py:484-530`; `tools/render.py:472-474`; `tools/lib/mapkit.py:501`; `tools/lib/mapkit.py:1739`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:1005-1011`; `tools/build.py:177-190`.

**Proposal.** Add tools/render_sheet.py: `python3 tools/render_sheet.py [--base HEAD] [--all] [SLUG ...] --out .cache/render-sheet/`. It writes one HTML page with a row per sample and two columns, before (the files of `git show <base>:rendered/...`, binaries through `git cat-file -p`, extracted into the out folder) and after (the working copy), each map stacked exactly as core.map_block stacks it (reuse core.frag and map_block with a temporary t['rendered']), for map-wide, map-col and map-phone, then profile-wide, tile and g112. Fixed sample: the newest trip of each activity, matterhorn-peak-west-couloir (the tall route report-08 names), gran-paradiso-haute-route overview-wide and day-01-col, pacific-crest-trail-2024 overview-tall, region-lake-tahoe-desktop and ski-lake-tahoe-desktop, plus any slug given; --all lists every changed trip as a thumbnail row. Under each pair print bytes before and after, gzip KB of base.svg against BASE_GZ_KB_PHONE / BASE_GZ_KB (40 / 80, mapkit.py:501) and 'unchanged' when the sha1 is equal; a header line counts changed, unchanged, new and removed files under rendered/ from `git status --porcelain rendered`, skipping iCloud conflict copies with build.conflict_copy. No network, stdlib plus git; ends with `open` of the page. Add the step to ADDING-TRIPS.md step 5 ('after a render with no trip name, look at the sheet before git add rendered').

**Files.** `tools/render_sheet.py`, `tools/sitegen/core.py`, `ADDING-TRIPS.md`, `docs/DEVELOPING.md`.

**Effort.** M. Visitor value 1, author value 3.3, confidence high.

**Already known.** memory note 'Previews before visual decisions'; log 2026-10-12 checks ('Before and after pictures were compared side by side')

**Risk.** Reads git objects and the working tree only; the page is local and git-ignored under .cache/. The base.svg column needs the standalone file as an <img>, which it already is. Nothing about trips is stated, only drawn.

**Review revision (applies on top of the text above).** Observation, corrected: A map on the site is three files assembled by core.map_block (hillshade webp img, base.svg img, overlay .svg.html inlined; core.py:484-530), so git diff cannot show what a re-render changed, and render.py deletes mapkit's per-map .meta.json, which held base_gz_kb, bytes and m_per_px (render.py:472-474, mapkit.py:1739, 1756). The last two full renders each touched thousands of files under rendered/ (git show --stat 6abc634 -- rendered: 2,604 files; a9baab9 -- rendered: 2,831 files); rendered/ is 3,393 tracked files, and the three journal-overlay renders of 10-12/13 were checked by comparing pictures side by side in Chrome by hand (log:1005-1011). maps-16 batches a dozen renderer findings into one VERSION bump, but nothing gives Eric a way to look at the result before git add. Proposal: unchanged.

**Review revision (applies on top of the text above).** Proposal: as written, with one addition: map_block reads rendered/site/meta.json through ROOT when site_maps=True (core.py:492-493), so give map_block an optional base folder argument (default unchanged) and pass the extracted 'before' folder for both trip and site maps; nothing in the built site changes.

**Review revision (applies on top of the text above).** Proposal: unchanged (tools/render_sheet.py; core.frag, core.map_block, core.read_json and build.conflict_copy all exist; note that map_block's <img src> is site-relative via core.link(here, asset_dir), so the sheet must copy or symlink each version's PNG/WebP and base.svg under its own asset folder in .cache/render-sheet/). Add the step to ADDING-TRIPS.md '## 5. Publish' (line 186).

**Review note (condensed; the observation and proposal above are the revised text).** Not built: there is no tools/render_sheet.py (ls tools/), no commit in git log --all mentions a contact sheet, and the memory note previews-before-visual-decisions.md records exactly the side-by-side habit the finding cites. Feasible (stdlib plus git, local, git-ignored output) and the value is specific to this plan: maps-16 re-renders 168 trips and 24 site maps in one go, a map is three stacked files that git diff cannot show (core.py:484-530), and the log records that the last three renders were checked by hand in Chrome (log:1005-1006). Effort M is honest. Reproduced: core.map_block (core.py:484-530) stacks the hillshade img, the base.svg img and the inlined .svg.html; render.py:472-474 deletes every per-map .meta.json, which mapkit writes at 1756 with base_gz_kb (1739), bytes and m_per_px (probe run-a/map-wide.meta.json shows all three); rendered/ has 3,393 tracked files (git ls-files); the log's side-by-side check is at docs/WEBSITE_IMPLEMENTATION_LOG.md:1004-1006; build.conflict_copy exists (build.py:72), core.frag (450) and read_json (442) exist, and every sample name exists (region-lake-tahoe-desktop, ski-lake-tahoe-desktop in rendered/site/meta.json; gran-paradiso-haute-route overview-wide and day-01-col; pacific-crest-trail-2024 overview-tall; content/trips/matterhorn-peak-west-couloir).

#### gap9-04. Make the full re-render a resumable, budgeted job with an end-of-run summary

**Observation.** --budget stops starting new trips (render.py:708, 752-754, 760) but --force re-renders every trip regardless of meta.json (render.py:762; in the pool path pending is every trip when a.force, render.py:733-746), so a second `--force --budget` run starts again from the first trip: a full re-render cannot be split across evenings. A VERSION bump (render.py:31, folded into every hash at render.py:434 and 638) is what makes a plain `render.py --budget` resumable, but no document says so: ADDING-TRIPS.md:44 and docs/DEVELOPING.md:781, 812 mention --force only for --site. What a full run costs today: about a minute per single-day trip (ADDING-TRIPS.md:63-64), 113 s for the journal and 267 s for gran-paradiso-haute-route, and 12 to 328 s per site-map job (.cache/render_rest.log: seven of the twelve jobs, two maps each, took 763 s together), so 157 single-folder trips (156 reports and the planned route), 10 multi-day trips, the journal and 24 site maps are about 3.5 to 4 hours serial on Python 3.9; the probe ran 40 percent faster under Homebrew python3.12 with byte-identical output. With --budget the run returns before render_site when trips remain, in the pool path (render.py:752-754) and the serial loop (759-761) alike, so a resumed job must end with one more run for the site maps; nothing prints progress or a summary.

**Evidence.** `tools/render.py:31`; `tools/render.py:434`; `tools/render.py:638`; `tools/render.py:708`; `tools/render.py:733-746`; `tools/render.py:752-754`; `tools/render.py:760-764`; `ADDING-TRIPS.md:44`; `ADDING-TRIPS.md:63-64`; `docs/DEVELOPING.md:781`; `docs/DEVELOPING.md:812`; `.cache/render_rest.log`; `that probe's recorded output`.

**Proposal.** (a) Document the full re-render in docs/DEVELOPING.md and ADDING-TRIPS.md: bump VERSION in tools/render.py (never --force for a full run: --force re-renders every trip on every run, render.py:733-736 and 762-764, while a VERSION bump makes `--budget` resumable through the hash), run `python3 tools/render.py --jobs 2 --budget 3600` as often as needed until it reports nothing pending (--jobs 4 once gap9-08 has shrunk the per-worker tile cache; the Mac has 16 GB of RAM), then `python3 tools/render.py --site`, then the sheet of gap9-02, then `git add rendered`; note that `/opt/homebrew/bin/python3.12 tools/render.py` gave byte-identical files 40 percent faster in the probe and that the tools stay 3.9-compatible. (b) When `--force` is given without slugs, print 'a full re-render is a VERSION bump plus --budget; --force redraws every trip on every run' and continue. (c) Print one progress line every 10 trips (done/pending, mean seconds per trip, estimated remaining) and a final summary: rendered N, skipped M (hash unchanged), failed K (names), OSM missing J, site maps drawn or not. (d) A `--list` flag that only prints which trips the hash check would re-render and why (VERSION, track, title, map:, stats) so the cost is known before the run. Tests in tests/test_render_goals.py for --list and the summary with the existing stubs.

**Files.** `tools/render.py`, `docs/DEVELOPING.md`, `ADDING-TRIPS.md`, `tests/test_render_goals.py`.

**Effort.** M. Visitor value 1, author value 3.3, confidence high.

**Already known.** maps-16 (one VERSION bump); authoring-09 (render.py --status)

**Risk.** None to the site. The progress file lives in .cache/ (git-ignored). The python3.12 note must say the tools stay 3.9-compatible (CLAUDE.md) and that 3.12 is optional.

**Review revision (applies on top of the text above).** Observation, corrected last sentence: With --jobs and --budget the run returns before render_site when trips remain (render.py:752-754), so a resumed job must end with one more run for the site maps; the only progress output is one line per finished trip with its seconds (render.py:480) and, in the pool path, 'budget used up; N trips left' (753): no done/pending count, no estimate of time remaining, and no end-of-run summary of rendered, skipped, failed and OSM-missing trips. --budget and --jobs are documented nowhere (README.md, ADDING-TRIPS.md, docs/). Proposal (a)-(d): unchanged.

**Review note (condensed; the observation and proposal above are the revised text).** Not built, with one overstatement. --force skips the hash check in both paths: the pool path's pending list includes every trip when a.force (render.py:735-736) and the serial loop calls render_trip(t, force=a.force) for every trip (762), so a second --force --budget run starts from the first trip again; --budget returns before render_site in both the pool path (752-754) and the serial path (759-761); VERSION = 7 at render.py:31 is folded into trip_inputs at 434 and the site hash at 638. The problem is real and measured: --force re-renders every trip regardless of meta.json (render.py:733-736, 762-764), a full run is 3.5 to 4 hours serial (render_rest.log: 113 s for the journal, 267 s for the haute route, 12 to 328 s per site map), and nothing prints progress or a summary. (a), (c) and (d) are specific and cheap. Reproduced: --budget at render.py:708, 752-754 and 760; --force re-renders regardless of meta.json (762; pending is every trip when a.force, 733-735); VERSION = 7 at line 31 folded into trip_inputs (434) and the site hash (638); ADDING-TRIPS.md:44 and docs/DEVELOPING.md:781, 812 mention --force only for --site; ADDING-TRIPS.md:63-64 says about a minute; .cache/render_rest.log shows pacific-crest-trail-2024 113 s, gran-paradiso-haute-route 267 s, seven site-map jobs 12-328 s summing to 763 s; rendered/site/meta.json has 24 maps; the probe ran 40 percent faster on 3.12 with identical hashes; /opt/homebrew/bin/python3.12 is 3.12.11.

#### gap9-05. Record renderer, Python and cwebp versions in meta.json; warn on a mixed render

**Observation.** rendered/trips/<slug>/meta.json holds an opaque hash that folds VERSION in (render.py:430-434) plus maps, charts, start, end and bbox (sample: rendered/trips/3-bears-x-2-lots-of-vert/meta.json); rendered/site/meta.json holds hash, maps, regions, all_regions. Nothing records which VERSION, Python or cwebp drew a folder, so after a VERSION bump a half-finished re-render is visible only to render.py's own hash check: the validator's render findings stop at 'meta.json is missing' (checks.py:832-834) and the stale site-map cases (checks.py:987-1018). Today all 168 trip folders have a non-null hash (scanned with a script: 168 with meta, 0 null, 0 osm_failed). optimize_images keeps PNGs silently when cwebp is missing (render.py:50-53), so a render on a Mac without cwebp would commit palette PNGs (92 KB for the probe's map-wide against 54 KB for the committed WebP of a comparable map) and the page would serve them.

**Evidence.** `tools/render.py:430-434`; `tools/render.py:476-479`; `tools/render.py:50-53`; `rendered/trips/3-bears-x-2-lots-of-vert/meta.json`; `rendered/site/meta.json`; `tools/lib/checks.py:832-834`; `tools/lib/checks.py:987-1018`; `that probe's recorded output`.

**Proposal.** Write meta['renderer'] = {'version': VERSION, 'python': platform.python_version(), 'cwebp': the first line of `cwebp -version` or null, 'date': today, 'osm': 'cached' | 'fetched' | 'missing'} in both render_trip and render_site, and keep base_gz_kb per map in meta['maps'] (mapkit computes it at mapkit.py:1739; render.py drops it at :251) for gap9-02's sheet. In checks.py add one site-wide warning when the trip folders disagree on renderer.version, or the site meta's version is older than the newest trip's: 'N of 168 renders are at renderer version 7 and M at 8: the re-render is unfinished; run python3 tools/render.py' naming the first five slugs; a folder without a renderer record counts as the oldest version. Make render.py stop before drawing when cwebp is missing unless --allow-png is given. Tests in tests/test_checks_site_maps.py and tests/test_render_goals.py (the stubbed render_single writes a meta the checks read). Effort: M.

**Files.** `tools/render.py`, `tools/lib/checks.py`, `tests/test_checks_site_maps.py`, `tests/test_render_goals.py`, `docs/DEVELOPING.md`.

**Effort.** M. Visitor value 1, author value 2.3, confidence high.

**Already known.** authoring-09 (render.py --status) would read these fields

**Risk.** Every re-render already rewrites meta.json (new hash), so the date adds no extra churn. A Python and cwebp version string in a public file reveals nothing about trips. The budget warning must stay a warning, never an error, or an old render could block a content-only build.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible and useful during the plan's re-render: nothing records which VERSION drew a folder (sample rendered/trips/3-bears-x-2-lots-of-vert/meta.json holds only hash, slug, kind, maps, charts), so a half-finished re-render that reaches main is invisible to the validator (checks.py:832-834 stops at a missing meta.json), and optimize_images silently keeps PNGs without cwebp (render.py:50-53).

#### gap9-08. Cap the in-memory tile cache: array storage and an LRU

**Observation.** Every decoded terrain tile stays in geo._tile_cache for the life of the process as a 65,536-element list of Python floats (geo.py:179, 213-217); measured with tracemalloc: 2.10 MB per tile as a list against 0.53 MB as array('d'). The on-disk cache holds 2,524 tiles, so a full serial re-render that touches them all holds about 5 GB, and `--jobs 4` keeps four such long-lived worker processes (ProcessPoolExecutor with fork, render.py:741-746) on a Mac with 19 GB of free disk for swap. Nothing evicts.

**Evidence.** `tools/lib/geo.py:179`; `tools/lib/geo.py:213-217`; `tools/lib/geo.py:221-235`; `tools/render.py:741-746`; `a reviewer's probe script run against tools/render.py on 2026-10-13`.

**Proposal.** In geo.get_tile build `array.array('d')` (or 'f') instead of a list; DEM.sample's indexing (geo.py:225-235) is unchanged. Keep _tile_cache as an OrderedDict LRU of 256 tiles (about 135 MB as 'd') and move the oldest out when full. Add a case to the golden test (gap9-01): a DEM.sample through a stubbed tile gives the same value from an array as from a list, and the hillshade PNG bytes are unchanged, so the goldens prove the change is invisible.

**Files.** `tools/lib/geo.py`, `tests/test_mapkit_golden.py`.

**Effort.** S. Visitor value 1, author value 2.3, confidence medium.

**Risk.** The per-tile size is measured; the 5 GB figure is arithmetic over the cache, not an observed peak, since no full render was run for this review. An LRU too small for a wide region map (region-santa-cruz took 328 s) would re-decode tiles; 256 tiles covers a 1440 px frame at any zoom with margin.

**Review note.** Kept as written by all three skeptics.

#### gap9-09. Contract test: render.py's output is what build.py and core.py read

**Observation.** The page modules read fixed render names from meta.json and the render folder: map-wide/map-col/map-phone (pages/report.py:395, 564, 614), overview-wide/col/phone and day-NN-col/phone, day-NN-profile-col/phone, spark-NN (pages/multiday.py:308-309, 354, 493, 631, 636, 732), overview-tall/overview-phone (pages/series.py:296), profile-* and speed-col (pages/section.py:166-174, 220; core.py:587-592), and tile/g112/g64 (core.py:610-633, build.py:180-187, which also copies *.png, *.webp and *.base.svg). render.py writes them (render.py:251, 275-287, 304-311, 347-354, 365-375, 379-380, 402-405, 420, and render_site's region-/ski-<slug>-desktop/phone at 633-640, 680). No test runs render.py's output through those readers: tests/test_render_goals.py:1-7 and 55-60 stub render_map, fetch_osm and optimize_images, and tests/test_build_site.py:255-313 and tests/test_report_page.py:294-299 hand-write the fixed names. So a rename in render.py passes every test, and the built site then drops the map silently (map_block skips a missing meta key, core.py:500-501) or leaves a '<!-- missing ... -->' comment where a fragment was (core.frag, core.py:450-453); 'Map not rendered yet' appears only for a planned goal (pages/report.py:404, core.py:1379). The finder's probe (finder-gap9/probe.py, run-a/run-b/run-312/_probe.json) called mapkit.render_map, render_profile, render_tile, render_glyph and render_sparkline offline with geo.get_tile replaced by a synthetic DEM and a hand-written Overpass dict: one single-day trip's three maps took 9.7 s on Python 3.12 (16.3 s on 3.9), and every output file was byte-identical across PYTHONHASHSEED 0, 4242 and 7 and across both Pythons.

**Evidence.** `tools/sitegen/core.py:450-453`; `tools/sitegen/core.py:469-483`; `tools/sitegen/core.py:582-631`; `tools/build.py:177-190`; `tools/render.py:251`; `tools/render.py:347-354`; `tools/render.py:375`; `tools/render.py:420`; `tests/test_render_goals.py:1-7`; `that probe's recorded output`.

**Proposal.** Add tests/test_render_contract.py, gated with unittest.skipUnless(os.environ.get('CI') or os.environ.get('RENDER_TESTS')) so it runs on GitHub (CI=true) and on request locally. With gap9-01's fixture (geo.get_tile patched, since geo.dem_grid calls it by name at geo.py:233; render.fetch_osm patched to return the Overpass dict) and render.OUT in a temp dir (render_trip itself writes to t['rendered'], render.py:460; render_site to OUT/site, 611), call render.render_trip on a synthetic single-day trip, a two-day trip with one content transfer and one gap, and a short series (tests/helpers.py:103 make_series gives the days the dates render_series needs, render.py:407-412), and render.render_site on a three-trip region (MIN_REGION_TRIPS is 3, render.py:34) with one journal part, reusing tests/test_region_days.py's journal()/walks() builders (lines 304-317). Assert the exact set of files each folder holds; every meta key that core.render_meta, core.map_block, core.map_preloads, core.chart_block, pages/section.py profile_block, the chart readers in pages/report.py:204-221 and pages/multiday.py:493-498, 636, and core._drawing will ask for; no '<!-- missing' in the report, multi-day, series, region and map pages built from that folder by build.py's page modules; that build.copy_trip_assets (build.py:174-187) publishes exactly the WebP-or-PNG, base.svg and tile/g112/g64.svg files; and that each base layer is under mapkit.py:501's budgets (40 KB gzipped for phone renders, 80 KB otherwise). base_gz_kb is not in the trip's meta.json (render.py:251 keeps only w/h/png/base/interval_ft/outbound_only, and render_trip deletes every <name>.meta.json at 472-474; today mapkit.py:1740-1741 only prints a warning), so take it from a wrapped render_map's return value or gzip the .base.svg in the test. Roughly 14 maps at 1.4 to 5.3 s each on 3.12 (the probe's per-map times): about 50 s on CI, unverified. Note the gate in docs/DEVELOPING.md 'Checking your work' (line 1242), whose line 1289-1290 says the suite ran 'with no test skipped': say that this file is skipped unless CI or RENDER_TESTS is set. Files: tests/test_render_contract.py, tests/render_fixtures.py (gap9-01), docs/DEVELOPING.md. tools/render.py needs no change for this test: fetch_osm, OUT and optimize_images are module globals that tests/test_render_goals.py:55-60 already patches. Risk unchanged: render_trip calls optimize_images, a no-op without cwebp (render.py:52-53) and, with it, PNG removed and meta['png'] renamed to .webp (61-64), so the test accepts either.

**Files.** `tests/test_render_contract.py`, `tests/render_fixtures.py`, `docs/DEVELOPING.md`, `tools/render.py`.

**Effort.** M. Visitor value 1, author value 2.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 4 ('The map renderer')

**Risk.** Adds about a minute to the CI job (today about a minute of tests plus the build). render.render_trip calls optimize_images, which is a no-op without cwebp (render.py:52-53): the test must accept .png or .webp in meta['png']. Depends on gap9-01's fixture module.

**Review note (condensed; the observation and proposal above are the revised text).** Not built and not decided against: no test runs the real drawing (tests/test_render_goals.py:1-7 and 50-57 stub render_map, fetch_osm and optimize_images; tests/test_region_days.py:24-25 reuses that fixture), tests/render_fixtures.py and tests/test_render_contract.py do not exist, git log --all has no render-contract commit, and docs/IMPLEMENTATION_REPORT.md section 4 says the renderer was never run and its tests stub the drawing. Observation verified: core.map_block skips a name absent from meta.json with no output (tools/sitegen/core.py:505-507), core.frag leaves only an HTML comment (core.py:453), and sitecheck has no map rule at all (tools/sitegen/sitecheck.py:11-12 lists only BROKEN and BROKEN ANCHOR), so a rename on either side passes build.py --check and ships pages without maps; tests/test_render_goals.py:35-58 stubs render_map, fetch_osm and optimize_images, so nothing today runs the writer against the reader. The core observation reproduces: nothing in the suite runs render.py's real output through core/build (tests/test_render_goals.py:1-7 and setUp lines 55-60 stub render_map, fetch_osm, optimize_images and patch render.OUT; tests/test_build_site.py:255-313 and tests/test_report_page.py:294-299 hand-write files named map-wide etc.), and the finder's probe (finder-gap9/probe.py; run-a, run-b, run-312 _probe.json) shows mapkit's drawing is byte-identical across PYTHONHASHSEED 0/4242/7 and Python 3.9/3.12, in 16.3 s (3.9) and 9.7 s (3.12) for one single-day trip's three maps.

#### maps-03. Frame tall routes in a taller wide and column map

**Observation.** Every single-day report draws map-wide at 1440x640 and map-col at 718x400 whatever the route's shape (render.py:237-243). On Matterhorn Peak the track box (meta.json bbox) is about 6.1 km north-south by 1.0 km east-west, so the route is a thin vertical line in the middle of a 2.25:1 frame and most of the map is context terrain. Counted over rendered/trips/*/meta.json on 2026-10-13: 157 maps with a map-wide render (156 single-day reports and the planned route), 34 with a track box taller than 1.4:1 and 15 taller than 2.25:1. core.map_block takes w/h from meta.json as an inline aspect-ratio (core.py:522-523) and .mv has no fixed height (base.css:329-334), so a taller render needs no CSS change.

**Evidence.** `tools/render.py:237-243 (fixed w/h per variant)`; `rendered/trips/matterhorn-peak-west-couloir/meta.json (bbox about 6.15 km N-S by 0.98 km E-W)`; `rendered/trips/*/meta.json bbox fields, counted on 2026-10-13 (157 / 34 / 15)`; `tools/sitegen/core.py:484-527 (map_block takes w/h from meta.json as an inline aspect-ratio)`; `assets/css/base.css:329-341 (.mv sized by aspect ratio; no fixed heights)`; `.cache/plan2/shots/desktop-report-matterhorn.jpeg (map at 1700-3100 px)`; `tools/render.py:212-262`; `tools/render.py:93-107`; `tools/render.py:36-37`; `rendered/trips/matterhorn-peak-west-couloir/meta.json`; `tools/sitegen/core.py:484-527`; `desktop-report-matterhorn.jpeg`; `phone-report-matterhorn.jpeg`.

**Proposal.** In render.render_single choose the wide and col frames from the track box's ground aspect (height/width): up to 1.0 keeps 1440x640 / 718x400; 1.0-2.0 gets 1440x800 / 718x500; above 2.0 gets 1440x960 / 718x600 (cap so a report never shows more than about two thirds of a 1440 viewport of map). Fold the chosen frame into trip_inputs() (render.py:430-434; it must read the track's bbox, which the file hash alone does not expose) so only tall-route trips re-render instead of a VERSION bump; optimize_images (the PNG-to-WebP step, render.py:50-64) and map_preloads (core.py:534) stay unchanged. The section featured block shows map-col in an 860 px column (section.css:108), so a 718x600 still fits; the multi-day day maps (render.py:355-370) can take the same rule later. Update the sizes at docs/DEVELOPING.md:1220 and add a frame-rule test to tests/test_render_goals.py (nothing asserts the sizes today).

**Files.** `tools/render.py`, `docs/DEVELOPING.md`, `tests/test_render_goals.py`, `tools/sitegen/pages/section.py`.

**Effort.** M. Visitor value 2.7, author value 1.3, confidence high.

**Also covers.** report-08 (merged into this finding).

**Risk.** A taller hillshade is a larger LCP image on those pages (map-wide.webp about 80 KB today); the bleed map pushes the write-up further down on story pages; needs render.py on Eric's Mac and a commit of about 34 trips' rendered folders (stage by path, watch for iCloud conflict copies).

**Review note (condensed; the observation and proposal above are the revised text).** Feasible under the constraints (render.py on Eric's Mac, static output, URLs unchanged) and the count is right in substance: my tally of rendered/trips/*/meta.json bboxes gives 156 single-day maps, 33 taller than 1.4:1 and 14 taller than 2.25:1, against the finding's 157/34/15. Observation reproduces: render.py:237-243 fix map-wide 1440x640, map-col 718x400, map-phone 390x336 for every single-day render; Matterhorn meta.json bbox is 6.15 km N-S by 0.98 km E-W (ground aspect 6.3); recounting rendered/trips/*/meta.json today (conflict copies excluded) gives 157 maps with a map-wide (156 kind 'trip' + the planned route), 34 with ground aspect > 1.4 and 15 > 2.25; core.map_block writes meta w/h as an inline aspect-ratio (core.py:522-523) and .mv has no fixed height (base.css:329-334); the crop of desktop-report-matterhorn.jpeg at 1700-3100 shows the thin vertical route in the wide frame; map-wide.webp is 82,438 bytes.

#### maps-05. Keep the numbered day squares on phone overview maps

**Observation.** On a multi-day report the desktop overview map shows D1-D6 labels, numbered hut squares with hut names and the GPS max (overview-wide.svg.html: five mk-day squares, five mk-hut labels); the phone overview (390x260, render.py:348-354: hut_end=None, gpsmax=False, day_labels=False) draws the route, the transfer and the overall start and end only, so a phone reader cannot tell which part of the line is which day.

**Evidence.** `tools/render.py:339-345 (overview-phone: hut_end=None, gpsmax=False, day_labels=False)`; `tools/render.py:323-336 (ov_tracks with hut_end for the desktop renders)`; `.cache/plan2/shots/phone-multiday-hauteroute.jpeg (map at 1200-3600 px: no day marks) vs .cache/plan2/shots/desktop-multiday-hauteroute.jpeg (map at 500-1900 px: D1-D6, squares 1-5)`; `tools/sitegen/pages/multiday.py:111-130 (key_items), tools/sitegen/pages/multiday.py:381-393 (overview_map, key_rows desk/phone)`.

**Proposal.** Keep hut_end on the overview-phone tracks as {'n': i + 1} without 'label' (mapkit draws the 20 px numbered square and adds the hut name only when 'label' is set, mapkit.py:1029-1048) and leave day_labels off; widen the phone reserve (render.py:351) so squares clear the scale bar and the attribution tag; mapkit already merges squares that fall within 22 px (mapkit.py:1032-1040). No key-row change: multiday.drawn() detects the squares from class="mk-day" (multiday.py:91-106), so key_items(t, ['overview-phone']) adds 'End of day' on its own and core.key_rows swaps rows at 560. Re-render the 10 multi-day trips with python3 tools/render.py <slug> (OSM and tile caches are warm). Tests in tests/test_report_page.py (where the multi-day page is built today).

**Files.** `tools/render.py`, `tools/sitegen/pages/multiday.py`, `rendered/trips/<multi-day slugs>/overview-phone.*`, `tests/test_report_page.py` (MultiDayPageTests).

**Effort.** S. Visitor value 2.3, author value 1, confidence high.

**Risk.** Six to eight squares on a 390 px map can crowd a short day; needs a render and a commit of the 11 overview-phone files.

**Review note (condensed; the observation and proposal above are the revised text).** Observation confirmed: the overview-phone spec is dict(SMALL, ..., day_labels=False, tracks=[dict(e, hut_end=None, gpsmax=False) for e in ov_tracks()], ...) and ov_tracks(huts=True) adds hut_end for the desktop renders (render.py:325-337). Feasible and cheap: the overview-phone spec drops the squares with hut_end=None (render.py:339-340) while the desktop specs keep them (render.py:323-336); mapkit draws the 20 px square and merges squares within 22 px regardless of small_markers (mapkit.py:1029-1047), and multiday.key_items decodes whatever the fragment draws (drawn() tests class="mk-day", multiday.py:102), so the phone key row updates by itself and core.key_rows swaps at 560. Observation reproduces: the crop of desktop-multiday-hauteroute.jpeg at 500-1900 shows D1-D6, squares 1-5 with hut names and the GPS max; the crop of phone-multiday-hauteroute.jpeg at 1200-3600 shows the route, TRANSFER and start/end only; rendered/trips/chamonix-zermatt-haute-route/overview-phone.svg.html has no mk-day or mk-hut element while overview-wide has five of each.

#### maps-15. Activity maps by region for hiking and mountain biking

**Observation.** Only the Ski page has a region map panel (tabs per region, hover highlights a row's track); the renderer draws ski-<region> pairs for regions with at least two ski trips. The Mountain biking page lists 61 rides and the Hiking page 34 hikes with no map of their own beyond the one featured trip's map.

**Evidence.** `tools/render.py:634-637 (ski jobs only; 506x680 and 390x480)`; `tools/sitegen/pages/section.py:359-382 (ski_panel), :482-537 (per-activity layouts)`; `rendered/site/ (ski-alps, ski-eastern-sierra, ski-lake-tahoe, ski-tetons pairs only)`; `.cache/plan2/shots/desktop-section-ski.jpeg (panel at 900-2300 px)`; `brief: 61 mountain-bike and 34 hiking trips`.

**Proposal.** Generalise the job at tools/render.py:635-637 to <act>-<region> for every activity with at least two trips in a region, capped to the activity's three largest regions to bound rendered/site (the four ski pairs are 724 KB today); section.ski_panel (section.py:359-382) becomes section.activity_panel(act, ts) with a per-activity map id, and the Mountain biking and Hiking branches of section.page (:482-537) place it where Ski does, giving their list wrapper data-map-target="<that id>" as section.py:402 does for ski-map (rows already carry data-key through core.trip_row, core.py:1190, which base.js:157 resolves); checks._site_map_findings (tools/lib/checks.py:987, today reading region-* entries only at :1039) and the DEVELOPING.md names list (docs/DEVELOPING.md:1230-1231) take the new keys. Tests: tests/test_section_page.py (Phase 13's visual-11 creates it; nothing covers ski_panel today) plus the fixture keys in tests/test_checks_site_maps.py:48-50. Requires python3 tools/render.py --site --force.

**Files.** `tools/render.py`, `tools/sitegen/pages/section.py`, `assets/css/pages/section.css`, `tools/lib/checks.py`, `rendered/site/`, `docs/DEVELOPING.md`, `tests/test_section_page.py`.

**Effort.** M. Visitor value 2.7, author value 1, confidence high.

**Risk.** About 2 MB more in rendered/site and larger section HTML (the Ski page is 249 KB with its four inlined overlays); a site render.

**Review note (condensed; the observation and proposal above are the revised text).** Observation verified: tools/render.py:636-637 adds ski-<region> jobs for regions with at least two ski trips, section.ski_panel at tools/sitegen/pages/section.py:359-382 draws them, and the four ski pairs total 724 KB tracked (723,999 bytes over the 24 git ls-files rendered/site ski-* files); the Ski page is 249 KB against 193 KB for Mountain biking and 142 KB for Hiking (_site/*/index.html). The observation holds: render.py:635-637 adds a ski-<region> job only for regions with at least two ski trips (506x680 desktop, 390x480 phone); section.ski_panel (section.py:359-382) builds the tabbed panel with the hover caption, and page() at :482-537 places it only for act == 'ski'; rendered/site has exactly the ski-alps, ski-eastern-sierra, ski-lake-tahoe and ski-tetons pairs (724 KB); the Ski page is 249,153 bytes, Mountain biking 193 KB and Hiking 142 KB; the ski-section crop at 900-2300 px shows the panel.

#### maps-06. Month labels along the PCT overview map

**Observation.** The journal's overview map (560x860 and 390x600) carries exactly two date labels, 'APR 22' at the start and 'SEP 21' at the end (render.py:410-416 overall_labels; mapkit.py:1476-1488). The By-month rows highlight their month's days on pointer hover or keyboard focus (series.py:235-255, base.js), neither of which a phone offers, so the 3,167-mile line shows no order or season between its ends.

**Evidence.** `rendered/trips/pacific-crest-trail-2024/overview-tall.svg.html (two mk-lbl texts APR 22 / SEP 21; one data-key="m-..." group per month)`; `tools/render.py:404-416 (render_series: overall_labels=ends)`; `tools/lib/mapkit.py:1476-1480 (overall start/end date labels)`; `tools/sitegen/pages/series.py:235-255 (month_index rows with data-key, hover only)`; `.cache/plan2/shots/desktop-series-pct.jpeg (intro map at 700-2100 px)`.

**Proposal.** render.render_series passes point_labels=[(lat, lon, 'MAY'), ...] for the first recorded day of each month after the first (content dates, nothing invented); mapkit.render_map gains a small point-label layer next to the overall labels (class mk-lbl text with the paper halo, a 6 px leader tick, placed with the existing collision boxes and skipped when nothing fits); both overview renders get the set, the phone one at 12 px. Optionally key each label to its month: base.js highlight() (base.js:137-151) toggles .hl only on .mk-cat[data-key], .mk-pin[data-key] and .mk-cluster, so either place the label inside the month's <g class="mk-cat" data-key="m-YYYY-MM"> group or extend that selector. tests/test_render_goals.py stubs render_map, so its test checks the point_labels render_series passes; a mapkit unit test covers the placement.

**Files.** `tools/render.py`, `tools/lib/mapkit.py`, `rendered/trips/pacific-crest-trail-2024/overview-tall.*`, `rendered/trips/pacific-crest-trail-2024/overview-phone.*`, `docs/DEVELOPING.md`, `tests/test_render_goals.py`.

**Effort.** M. Visitor value 2, author value 1, confidence high.

**Risk.** Labels crowd where the route doubles back; needs a render of the series (python3 tools/render.py pacific-crest-trail-2024).

**Review note (condensed; the observation and proposal above are the revised text).** Observation reproduces: rendered/trips/pacific-crest-trail-2024/overview-tall.svg.html has exactly two date mk-lbl texts (APR 22, SEP 21; the other four mk-lbl are the scale bar) and one data-key="m-2024-04".."m-2024-09" group per month; meta.json gives overview-tall 560x860 and overview-phone 390x600; render_series passes overall_labels=ends (render.py:410-416) and mapkit places them at 1476-1488; series.month_index rows carry data-key (series.py:235-255); the page shows 3,167 mi; the crop of desktop-series-pct.jpeg at 700-2100 shows the two labels only.

#### perf-05. Encode hillshade rasters at WebP quality 75-80 instead of 88

**Observation.** `render.py` converts every hillshade PNG with `cwebp -q 88 -m 5` (render.py:50-64). Decoding three shipped rasters and re-encoding them at q75 roughly halves them: region-lake-tahoe-desktop 81,848 (78,294 after a q88 pass) → 42,986 bytes, matterhorn map-wide 82,438 (77,898) → 44,502, map-phone 36,982 (34,726) → 20,082 (q80: 58,514 / 57,406 / 26,120). The report measured the region map as the largest element on the region pages and the Map page (IMPLEMENTATION_REPORT.md:607), and the hillshade is the heavier of that map's two image layers; `rendered/` holds 595 map rasters, 23.9 MB. The estimate is from a second lossy pass over the shipped WebP, so the real figure from the PNG will be close but not identical.

**Evidence.** `tools/render.py:50-64`; `the reviewer's q75 re-encode of region-lake-tahoe-desktop.webp: 42,986 bytes)`; `rendered/site/region-lake-tahoe-desktop.webp (81,848 bytes)`; `rendered/trips/matterhorn-peak-west-couloir/map-wide.webp (82,438 bytes)`; `docs/IMPLEMENTATION_REPORT.md:578-616`.

**Proposal.** Make the quality a constant `HILLSHADE_Q` at the top of `render.py` (default 88 until decided), add `-m 6` to cwebp, and render two or three site maps at q75, q80 and q88 into a scratch folder with `--site` targeted at a temp output; show Eric the three versions side by side at 1x and 2x (the memory rule: preview before a visual decision). If q75 or q80 passes, set the constant and run `render.py --site --force` first (24 files, the home/map/region pages), then re-render trip maps in batches with `render.py SLUG … --force` as time allows. Do not bump `VERSION`: it is part of both render hashes (render.py:434, :638), so a bump also forces every chart and glyph and makes the next plain `render.py` a full re-render. Unchanged trips keep q88 until their batch, which is harmless. Expected per page: about 35-40 KB less for the desktop map and 15 KB for the phone map before anything else loads; a full pass adds roughly 12 MB of new binaries to git history. Effort M.

**Files.** `tools/render.py`, `rendered/site/`, `rendered/trips/`.

**Effort.** M. Visitor value 2.7, author value 1.7, confidence medium.

**Risk.** Smooth shading can band at lower quality; decide only from a side-by-side preview. A full re-render adds roughly 12 MB of new binaries to git history (the pack is already 183 MB). Needs the internet and Eric's Mac.

**Decision for Eric.** Which quality setting looks acceptable, from a side-by-side preview.

**Review revision (applies on top of the text above).** Proposal: unchanged except: raise `-m 5` to `-m 6`, and `VERSION` is at render.py:31. EVIDENCE correction: the review's scratch files/hs-75.webp (20,082 bytes) is the re-encode of matterhorn map-phone.webp, and hs-88.webp (34,726) its q88 pass; the Lake Tahoe re-encodes are reproduced in the second reviewer's re-encodes lt-75.webp (42,986), lt-80.webp (58,514), lt-88.webp (78,294).

**Review note (condensed; the observation and proposal above are the revised text).** Worth it: render.py:50-64 encodes at q88 `-m 5`; the finder's re-encodes (the reviewer's re-encodes: hs-75 20,082, hs-80 26,120, hs-88 34,726 bytes against the shipped matterhorn map-phone.webp at 36,982) support the halving within a few percent; the hillshade is the LCP image on map, region and compact report pages, and 35-40 KB on the Slow 4G profile is close to a second; the side-by-side preview follows the memory rule. render.py:50-64 (`optimize_images`, `cwebp -q 88 -m 5`) and `VERSION = 7` at line 31 reproduce; 595 WebPs under rendered/ (all map rasters: map-wide/col/phone, day, overview, region, ski) total 23,887,418 bytes = 23.9 MB; size-pack is 182.75 MiB.

#### copy-18. Cluster pin tooltips: a count and a few titles, not 22 titles

**Observation.** mapkit.py:1539 writes a cluster's <title> as every member title joined by '; ': on the home Lake Tahoe map one cluster's tooltip is 22 titles joined, several of them the same word (_site/index.html), and a two-member cluster repeats its one shared title. The key beside the map says 'Several reports start here' (home.py:268, archive.py:122). The group is aria-hidden, so this is the hover tooltip only.

**Evidence.** `tools/lib/mapkit.py:1538-1539`; `_site/index.html (svg <title> elements inside .mk-cluster)`; `tools/sitegen/pages/home.py:268`; `tools/sitegen/pages/archive.py:122`.

**Proposal.** In mapkit's cluster markup set the <title> to '%d reports start here: %s' with up to three distinct titles and ' and N more'. Takes effect after `python3 tools/render.py --site --force` on Eric's Mac and a commit of rendered/site.

**Files.** `tools/lib/mapkit.py`, `tools/render.py`, `rendered/site/`.

**Effort.** S. Visitor value 1.7, author value 1, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 15.4 point 7 (pin counts the planned route)

**Risk.** Needs a render (internet, Eric's Mac) and re-commits every region map; a planned route is counted as a report in that number (known 15.4.7).

**Review note.** Kept as written by all three skeptics.

#### gap10-01. Write the storage budget into DEVELOPING.md: weights, horizons, caps

**Observation.** Nothing in the repository states what the site and its history weigh or how fast they grow, although every re-render and every photo copy is committed for good (README.md:6-10). Measured 2026-10-13 at 1cb9cf2: the tracked tree is 231.9 MB in 5,212 files (photos 144.5 MB in 1,004 files: 398 full copies 103.9 MB, 398 .sm 28.8 MB, 208 .th 5.1 MB; GPX 31.4 MB in 341 files; rendered/ 51.0 MB in 3,393 files: hillshade WebP 23.9, .base.svg 16.0, .svg.html 10.8, meta 0.3). History holds 303.2 MB of blobs in 9,168 objects, stored as a 182.75 MiB pack plus 36.42 MiB of loose objects (4,749), 204.7 MB after a repack. _site/ is 240 MB in 3,414 files (HTML 25.8 MB). Photos and WebP never delta-compress (143.3 MB and 24.9 MB in the pack, zero deltas); SVG and GPX shrink to about 40 % and 17 %. The 2026 trips (58 reports dated 2026 in content/trips/*/index.md, 1 Jan to 13 Oct) added 161 photos (57.5 MB of copies), 70 GPX files (3.3 MB) and 1,108 rendered files (14.1 MB): about 95 MB of tracked bytes a year at that pace, roughly 86 MB of pack and 103 MB of published site (each trip also adds ~110 KB of HTML). GitHub's documented limits: published Pages site no larger than 1 GB, deployment timeout 10 minutes, soft bandwidth 100 GB a month, source repository recommended 1 GB; repositories ideally under 1 GB and strongly under 5 GB; a file over 50 MiB warns and over 100 MiB is blocked (LFS only, and the brief notes Pages cannot serve LFS files). At the 2026 pace the published site reaches 1 GB in about 7.4 years and the repository's recommended 1 GB in 7 to 9 years depending on how many forced render rounds happen; 100 GB a month equals more than 400 complete crawls of the whole site, and the deploy ran 151-188 s against a 10-minute timeout.

**Evidence.** `git count-objects -vH and git verify-pack -v .git/objects/pack/*.idx, run 2026-10-13 (pack 182.75 MiB, 4,749 loose objects 36.42 MiB)`; `git ls-tree -r -l HEAD summed by path kind (231,910,934 bytes)`; `git rev-list --objects HEAD | git pack-objects --stdout | wc -c = 204,699,598`; `content/trips/*/index.md date: lines counted by year (58 trips in 2026)`; `tools/lib/photos.py:149-169`; `README.md:6-10`; `.github/workflows/pages.yml:21-45`; https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits (fetched 2026-10-13); https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github (fetched 2026-10-13); `the actions/upload-pages-artifact README, lines 70-72 (fetched 2026-10-13)`.

**Proposal.** Add '## Storage budget' to docs/DEVELOPING.md after 'Measuring page loads' (after line 1439) and one pointer line under README.md:114. Contents: (1) the measured table, dated 2026-10-13 at 1cb9cf2, in ONE unit (decimal MB from byte counts, with the converting command beside it: git ls-tree -r -l HEAD summed by kind; git count-objects -vH, whose MiB are converted; du -sh _site .cache): tracked 231.9 MB / 5,212 files (photos 144.5 MB: 398 full 108.9, 398 .sm 30.2, 208 .th 5.4; GPX 31.4; rendered 51.0: hillshade WebP 23.9, .base.svg 16.0, .svg.html 10.8, meta 0.3), history 204.7 MB repacked, _site 240 MB; (2) per-trip costs: a single-day trip's render is a median 241 KB in 16 files, each photo about 267 + 74 + 25 KB; photos and WebP never delta-compress; (3) GitHub's limits with the docs URL and the date read (site 1 GB, deploy 10 min, bandwidth 100 GB/month, repository 1 GB recommended, file 100 MiB blocked) and the trailing-year horizons (site 1 GB in about 7 years, pack 1 GB in 7-9 years), stated as 'no pressure today; the point is to keep it that way'; (4) three rules for a session: do not re-encode existing photos or hillshades tree-wide for a saving under 30 % of their tracked size (old blobs stay in the pack, new rasters never delta); batch renderer changes so a forced render round happens as rarely as possible, with its measured cost beside render.py's VERSION (gap10-03); anything build.py can derive with the standard library (combined GPX, bundles, indexes) is never committed; a phase that adds more than 25 MB to tracked files says so in its WEBSITE_IMPLEMENTATION_LOG.md entry with before/after numbers from the commands above (or tools/size_report.py if gap10-02 lands). Files: docs/DEVELOPING.md, README.md. Effort S.

**Files.** `docs/DEVELOPING.md`, `README.md`.

**Effort.** S. Visitor value 1, author value 2.3, confidence high.

**Risk.** Numbers in a document go stale; the section must carry its date and the commands, and the yearly checklist (gap10-06) re-measures. No site behavior changes.

**Decision for Eric.** Accept the four caps as rules for future phases, or set his own thresholds.

**Review revision (applies on top of the text above).** Observation, corrected passages: '... photos 144.5 MB in 1,004 files: 398 full copies 108.9 MB, 398 .sm 30.2 MB, 208 .th 5.4 MB (decimal MB throughout) ...'. '... a file over 50 MiB warns and over 100 MiB is blocked (Git LFS only; neither GitHub page read today says whether Pages serves LFS-tracked files, so LFS is not assumed to be a way out).' 'The 2026 trips (58 reports whose date: lies in 2026, 9 Jan to 24 Sep; the pace below divides their bytes by the 286 days from 1 Jan to 13 Oct) added 161 photos (57.5 MB of copies: 44.0 MB full + .sm + .th) ...'. '... and the whole deploy workflow (unit tests, build, deploy jobs) ran 151-188 s on its five successful runs since 2026-10-12 (`gh run list --workflow pages.yml`), against deploy-pages' own 10-minute timeout.' Proposal (2): 'per photo, about 274 + 76 + 26 KB of copies (decimal)'. Add to evidence: 'gh run list --workflow pages.yml --limit 12 --json createdAt,updatedAt,conclusion, 2026-10-13'. Files and placement stand: docs/DEVELOPING.md after line 1428 (its last section) and README.md under line 114.

**Review note (condensed; the observation and proposal above are the revised text).** Not built: docs/DEVELOPING.md has only the headings at lines 58, 72, 1130, 1242 and 1428 (no storage section), and `grep -r -i 'storage budget|count-objects|git gc' docs README.md tools tests` matches nothing. Feasible, docs-only, and S is honest. The measurements reproduce exactly: git ls-tree -r -l HEAD sums to 231,910,934 B in 5,212 files; photos 144.5 MB/1,004 files (398 full, 398 .sm, 208 .th); GPX 31.4 MB/341; rendered 50.96 MB/3,393 (raster 23.9, .base.svg 16.0, .svg.html 10.8, meta 0.3); git count-objects -vH: 4,749 loose 36.42 MiB, pack 182.75 MiB; 9,168 blobs 303.2 MB raw; pack-objects --stdout = 204,699,971 B; _site 240M, 3,414 files, HTML 25.79 MB; verify-pack: photos 143.3 MB and rasters 24.9 MB with 0 deltas, SVG 40.6 %, GPX 16.5 %; 58 trips dated 2026 with 161 full photos, 57.5 MB of copies, 70 GPX 3.3 MB, 1,108 rendered files 14.1 MB; median single-day render 240,577 B in 16 files (webp 45.6 %, base.svg 32.7 %, svg.html 21.2 %); limits as quoted in the saved pages-limits.html and large-files.html; README.md:6-10 and :114 and DEVELOPING.md:1428 ('Measuring page loads', the last section) are as cited.

#### gap10-02. Add tools/size_report.py: tracked, history and site sizes with a projection

**Observation.** No tool in tools/ measures size (tools/ holds add_trip, build, privacy_audit, render, thumbs, ticklist, validate and the libraries; grep for size_report, count-objects or 'storage budget' finds nothing in tools, tests or docs). The numbers in gap10-01 took a dozen hand-written git and Python commands to assemble, and the brief's own estimate for a VERSION bump (~51 MB) was the uncompressed tracked size, not the measured history cost (9.7 MB, gap10-03). Without a tool, the next plan will guess again, and a phase that adds 60 MB of photo copies (phone-14 as proposed) would not be noticed as 0.6 years of growth.

**Evidence.** `ls tools/ on 2026-10-13 (no size tool)`; `grep -r -i -l 'size_report|storage budget|git gc|count-objects' tools tests docs README.md ADDING-TRIPS.md: no match`; `tools/validate.py:1-16 (the pattern of a read-only reporting tool with --json)`; `tools/privacy_audit.py:1-14 (counts-only author tool, never run by CI)`; `docs/DEVELOPING.md:1242-1250 (the three checks a session runs)`.

**Proposal.** Write tools/size_report.py (stdlib, read-only, no git write, 3.9-compatible, under about 150 lines): 'tracked' from `git ls-tree -r -l HEAD` grouped by kind (photos full/.sm/.th by the suffixes of tools/lib/photos.py; GPX; rendered by .webp/.png, .base.svg, .svg.html, meta.json; everything else); 'history' from `git count-objects -v` only (pack and loose sizes; no verify-pack); 'site' by walking _site/ or --site DIR by the same kinds; 'growth' by loading tools/lib/content.load_all(), taking each trip's first date, and summing its photos, GPX and rendered/trips/<slug> bytes per calendar year, printed as a table with the LIMITS (values, docs URL, date read) and 'at the last full year's pace: site 1 GB in N.N years, pack 1 GB in N.N years', and one line saying the grouping is by trip date, not commit date. Skip conflict copies with sitecheck.conflict_copy as tools/build.py:72-77 does. --json prints the same as one object. Tests in tests/test_size_report.py on synthetic trips in a temp folder (tests/helpers.py style): the kind classifier, the per-year grouping, the horizon arithmetic; the git parts are exercised only if git and a repository are present, otherwise skipped. Document it in docs/DEVELOPING.md 'Checking your work' (line 1242 onward) and the file table, and as the first item of gap10-06's checklist. Effort S to M (one short session).

**Files.** `tools/size_report.py`, `tests/test_size_report.py`, `docs/DEVELOPING.md`, `README.md`.

**Effort.** M. Visitor value 1, author value 2, confidence high.

**Risk.** The git-based parts take tens of seconds on 10,000 objects (verify-pack behind a flag); the tool must never write or run gc. A projection from trip dates differs from commit dates (the September import added five years of trips in one day), so the tool must say which it uses.

**Review revision (applies on top of the text above).** Observation, corrected sentence: 'The numbers in gap10-01 took a dozen hand-written git and Python commands to assemble, and the obvious proxy for a VERSION bump, the tracked size of rendered/ (51.0 MB), is five times the measured history cost of the one round on record (9.7 MB for a9baab9, gap10-03). Without a tool, the next plan will guess again, and a phase that adds 60 MB of photo copies (phone-14 as proposed) would not be noticed as 0.6 years of growth.' Proposal (d), one clarification: 'take each trip's date from tools/lib/content.load_all() (t["date"], which content.py:586 already sets to the first day's date for a multi-day trip or a series)'. Everything else stands.

**Review note (condensed; the observation and proposal above are the revised text).** Feasible under the stack (stdlib, 3.9, read-only, no network) and the gap is real: tools/ holds no size tool and the grep for size_report, storage budget, git gc or count-objects over tools, tests, docs, README.md and ADDING-TRIPS.md matches nothing. Reproduced: tools/ holds add_trip, build, privacy_audit, render, thumbs, ticklist, validate and lib/, sitegen/ (no size tool); `grep -r -i -l -E 'size_report|storage budget|git gc|count-objects' tools tests docs README.md ADDING-TRIPS.md` matches nothing; tools/validate.py:1-16 documents --json and read-only; tools/privacy_audit.py:1-14 says CI never runs it; DEVELOPING.md:1242-1250 lists the three checks; tools/build.py:72-77 is conflict_copy; tests/helpers.py exists; content.load_all is at content.py:620 and already sets a multi-day or series trip's date to its first day's (content.py:586), so the tool can read t['date'] as is; DEVELOPING.md:1288-1295 is the two-Pythons rule; the file table starts at line 5; the bulk import landed on one day (a742ad1, 2026-09-27).

#### gap10-03. Make a forced render round cost only what changed, and run one a year

**Observation.** tools/render.py keys every trip's render to a SHA-1 of its inputs plus VERSION = 7 (render.py:31, :434) and the site maps to VERSION too (:638); a bump rewrites all of rendered/ (3,393 files, 48.6 MB). render_trip deletes the trip's folder and redraws everything (render.py:459-461), so even files whose bytes come out identical get a new mtime and iCloud re-uploads them, and the run prints only per-trip seconds (render.py:480), never how many files changed or how much they weigh. The one full round on record, a9baab9 on 2026-09-28, rewrote 2,828 rendered files (28.0 MB of new bytes) and cost 9.7 MB of history after packing (measured read-only with git pack-objects --stdout for the old and new blobs); only 36 of its 595 hillshade WebPs changed bytes, because the raster is deterministic for the same tiles and parameters. A round that changes the raster output (a hillshade quality change, as perf-05 proposes, or a VERSION bump that alters the shading) costs about 24.9 MB more, since WebP blobs never delta-compress (0 deltas among 644 raster blobs in the pack). The brief's '~51 MB per VERSION bump' is therefore the ceiling for a round that changes every byte, not the measured cost. perf-05 and maps-16 as two separate rounds would rewrite the raster twice.

**Evidence.** `tools/render.py:31, :434, :455-480, :638`; `git diff-tree -r --diff-filter=M a9baab9~1 a9baab9 -- rendered (2,828 files: 593 .base.svg, 2,030 .svg.html, 169 meta.json, 36 .webp)`; `git pack-objects --stdout on the old vs old+new blobs of a9baab9: 9.7 MB incremental; raw 28.0 MB`; `git verify-pack -v .git/objects/pack/*.idx grouped by kind: rendered rasters 644 blobs, 0 deltas, 24.9 MB in pack`; `the reviewer's re-encodes of one hillshade at q88, q80, q75 and q70 (34,726 / 26,120 / 20,082 / 18,662 bytes from the same 399 KB PNG)`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:1004, 1073, 1127, 1180 (render --site --force runs since publication)`.

**Proposal.** Two parts, no renderer code. (1) Put the measured cost beside VERSION: a comment at tools/render.py:31 and a line in docs/DEVELOPING.md's file table (line 12-13) and the Storage budget section: 'a bump re-renders all 3,393 files; git keeps only the ones whose bytes change: 9.7 MB of packed history when only the SVG changes (a9baab9, 2026-09-28), about 35 MB when the hillshade rasters change too; after a round, `git diff --stat -- rendered | tail -1` is the cost, put it in the commit message'. (2) Sequence the plan so every renderer change that survives review (maps-16, perf-05's hillshade quality, and any other) lands in ONE `render.py --force` run committed as 'Render round <year>', with the --site maps regenerated in the same run; a second forced round in the same year needs a stated reason (a drawing defect on the live site). Files: tools/render.py (one comment), docs/DEVELOPING.md. Effort S.

**Files.** `tools/render.py` (one comment), `docs/DEVELOPING.md`, `README.md`.

**Effort.** S. Visitor value 1, author value 2.3, confidence high.

**Already known.** docs/WEBSITE_IMPLEMENTATION_LOG.md:1004, 1073, 1127, 1180 (forced site renders)

**Risk.** render.py cannot run in CI and must be exercised on Eric's Mac with the internet; a staging folder doubles a trip's disk use for a minute. The replace step must keep the delete-stale behavior at render.py:765-771 and the drafts rule (render.py:711). The commit history is never rewritten (docs/PRIVACY_NOTES.md section 6), so the saving is only for future rounds.

**Decision for Eric.** Schedule the single yearly render round (which season) and whether maps-16 and perf-05 wait for it.

**Review revision (applies on top of the text above).** Observation, corrected passages: '... a bump rewrites all of rendered/ (3,393 files, 51.0 MB).' '... The tracked size of rendered/ (51 MB) is therefore the ceiling for a round that changes every byte, not the measured cost.' Evidence line: 'docs/WEBSITE_IMPLEMENTATION_LOG.md:1004, 1073 (`render.py --site --force`), 1127, 1180 (`render.py --site`, all region and ski maps redrawn)'. Risk, corrected sentence: 'docs/PRIVACY_NOTES.md section 4 (line 117) records that no history was rewritten and section 6 leaves a rewrite as decision 6 for Eric, so the saving is only for future rounds unless he decides otherwise.' relates_to_known: 'docs/WEBSITE_IMPLEMENTATION_LOG.md:1004, 1073, 1127, 1180 (site renders since publication, two of them forced)'. Proposal unchanged.

**Review note (condensed; the observation and proposal above are the revised text).** Parts (2) and (3) are cheap and right; part (1), the M-effort part, rests on a false premise. The core observation reproduces exactly: render.py:31 VERSION = 7, :434 trip_inputs hashes VERSION, :638 the site hash does too, :459-461 rmtree then set_out, :480 prints only per-trip seconds; `git diff-tree -r --diff-filter=M a9baab9~1 a9baab9 -- rendered` = 2,828 files (593 .base.svg, 2,030 .svg.html, 169 json, 36 .webp), 27.96 MB of new blobs; packing the old rendered blobs (38.41 MB) against old+new (48.10 MB) gives 9.69 MB incremental; 595 .webp existed at a9baab9; verify-pack: 644 raster blobs, 0 deltas, 24.9 MB; hs-88/80/75/70.webp are 34,726/26,120/20,082/18,662 B from a 399,249 B PNG; a9baab9 dated 2026-09-28.

#### gap10-04. Decide where each new derived file lives and cap what it adds

**Observation.** The build runs on a runner whose software list names no cwebp, libwebp or ImageMagick (image 20261004.327.1: Ubuntu 24.04.5, Node 22.23.3, Python 3.12.3), the workflow installs nothing (pages.yml:21-35), and the stack is standard library only (README.md:9), so anything that needs cwebp, sips or the terrain tiles must be committed: today that is every photo copy (tools/lib/photos.py:149-169, thumbs.py) and every render. What the build can derive it already does without committing: the multi-day combined GPX (tools/build.py:196-222), search.json and journal.json. Costs of the first-round proposals at the measured per-file sizes: phone-14's 1200 px copy for 398 photos is about 58-65 MB ((1200/1600)^2 of 103.9 MB, or 2.25 x the .sm total of 28.8 MB), never deltas, and equals 0.6 years of growth; for the 106 covers alone it is about 16 MB. seo-04's JPEG share crop per cover: 106 x 80-150 KB = 9-16 MB. seo-05/visual-12's 62 route share images as 1200x630 rasters: 6-12 MB. perf-05's re-encode of 595 hillshades at q75 (the perf finder's sample: 34.7 KB -> 20.1 KB, -42 %) saves about 10 MB of tracked and served bytes but adds about 14 MB to history. features-12's per-region GPX bundles total 16.9 MB for the eight mapped regions (Santa Cruz 8.9 MB over 45 trips, Lake Tahoe 5.4 MB over 87) and cost nothing in git if build.py writes them like the combined multi-day file; but Pages serves GPX uncompressed (the live Matterhorn GPX answers application/gpx+xml with no content-encoding and content-length 121,334, while .base.svg and site.css arrive gzip), so a bundle is downloaded at full size. A .th copy for the 190 photos that lack one is about 5 MB. Together, as proposed, the findings add roughly 110-135 MB to history (1.2-1.5 years of growth) and about 90 MB to the published site.

**Evidence.** https://raw.githubusercontent.com/actions/runner-images/main/images/ubuntu/Ubuntu2404-Readme.md, lines 9-28 (grep for webp/imagemagick: no match); `.github/workflows/pages.yml:21-35`; `README.md:9`; `tools/lib/photos.py:149-169`; `tools/build.py:174-222`; `tools/sitegen/core.py:734-760 (PHONE_SLOT: phones take the 800 px copy)`; `curl -sI https://esichak.github.io/personal-website/trips/matterhorn-peak-west-couloir/matterhorn-peak-west-couloir.gpx (no content-encoding) and .../map/map-wide.base.svg (content-encoding: gzip), 2026-10-13`; `content/trips/*/index.md region: lines summed with the trips' GPX bytes (Santa Cruz 8.9 MB, Lake Tahoe 5.4 MB)`; `the reviewer's re-encodes of one hillshade at q88 and q75 (34,726 and 20,082 bytes)`.

**Proposal.** Docs only. In the Storage budget section (gap10-01) add a two-row rule table: committed derivatives (need cwebp, sips or the network: photo copies, share crops, route share images, renders) versus build-time derivatives (standard library: combined GPX, GPX bundles, indexes, standalone glyph SVGs; written by build.py, never committed, and checked by sitecheck.gpx the way the combined multi-day file is, tools/sitegen/sitecheck.py:664). Then, in the plan itself, attach these caps to the named findings IF they are kept, as conditions in their text rather than as a separate phase: phone-14: a 1200 px copy only for cover and lead photos (about 16 MB), and only after a 3x-phone measurement shows the 800 px copy visibly short; seo-04/seo-05: one raster per trip at 1200x630, JPEG via sips quality 74 or WebP, EXIF stripped, capped at 150 KB each and 20 MB in all, made only from already-published photos; features-12: bundles written by build.py, offered only where a region's bundle is under 5 MB (Santa Cruz at 8.9 MB keeps per-trip files only), with the size printed from the built file's length; perf-05: only inside the year's single forced render round (gap10-03); .th for the 190 photos without one: fine at about 5 MB. If none of those findings survives, this item reduces to the rule table. Files: docs/DEVELOPING.md. Effort S.

**Files.** `docs/DEVELOPING.md`, `tools/lib/photos.py`, `tools/build.py`, `tools/sitegen/core.py`, `tools/lib/content.py`.

**Effort.** S. Visitor value 1, author value 2, confidence medium.

**Already known.** docs/IMPLEMENTATION_REPORT.md section 12.1 (1200 px copy) and 12.4 (share image for reports without a photo)

**Risk.** Caps are policy, not code; the implementing findings must read them. A build-time bundle must pass the GPX byte check in sitecheck (tools/sitegen/sitecheck.py:664) the way the combined multi-day file does. Share rasters must keep EXIF stripped (photos.py strip_metadata) and come only from already-published photos.

**Decision for Eric.** Whether phone sharpness is worth 16 MB (covers only) or 60 MB (every photo), or nothing; and whether a region bundle over 5 MB should exist at all.

**Review revision (applies on top of the text above).** Observation, corrected sentences: '... for the 106 covers (every trip with a photos/ folder; no index.md sets cover:, so the cover is the picked first photo) it is about 16 MB.' '... Together, as proposed, the findings add roughly 90-110 MB to history (1.0-1.2 years of growth) and about 90 MB to the published site.' Proposal (c), corrected: 'features-12: bundles are written by build.py in copy_trip_assets' style, never committed, and offered only where the region's bundle is under 6 MB (today Lake Tahoe at 5.4 MB, Alps, Eastern Sierra and the four small mapped regions Boise, Bay Area, Tetons and Oregon; Santa Cruz at 8.9 MB gets the per-trip files only), with the size printed next to the link from the built file's length.' Files and the rest of the proposal stand.

**Review note (condensed; the observation and proposal above are the revised text).** The facts hold: the runner image README fetched for the review lists no webp or ImageMagick, pages.yml:21-35 installs nothing, photos.py:149-169 needs cwebp, build.py:196-222 already derives the combined multi-day GPX without committing it, and the live site serves GPX with no content-encoding (content-length 121,334 for the Matterhorn file) while .base.svg arrives gzipped, so a GPX bundle really downloads at full size. Reproduced: the runner image README (saved as runner-ubuntu2404.md in the review scratch, not in the repository; the URL is in the evidence) lines 9-28 (24.04.5, image 20261004.327.1, Node 22.23.3, Python 3.12.3) and grep -i 'webp|imagemagick|magick' matches nothing; pages.yml:21-35 installs nothing; README.md:9; photos.py:149-169 web_copies and :142 sips quality 74, strip_metadata at :69; build.py:196-222 writes the combined GPX, search.json/journal.json are build-time (sitegen/search.py, pages/trips.py); core.py:734 PHONE_SLOT, cover_img :811 with eager, report.py:32 lead_photo; live HEAD with Accept-Encoding: GPX application/gpx+xml, no content-encoding, content-length 121334; map-wide.base.svg and site.css gzip; 398 full photos, 190 without .th; no index.md has a cover: field and 106 trips have a photos/ folder, so '106 covers' means the 106 auto-picked covers and 62 = 168 - 106 trips without photos; the eight mapped regions per rendered/site/meta.json are Lake Tahoe, Santa Cruz, Eastern Sierra, Boise, Bay Area, Tetons, Alps, Oregon, whose GPX sums to 16.9 MB (Santa Cruz 8.9 over 45 trips, Lake Tahoe 5.4 over 87); sitecheck.py:664 is gpx(); IMPLEMENTATION_REPORT section 12 items 1 and 4 are the 1200 px copy and the share image.

#### gap10-06. A yearly upkeep checklist with today's values written down

**Observation.** The deploy depends on things that change without a commit: five GitHub Actions pinned by major tag only (checkout@v4, setup-python@v5, configure-pages@v5, upload-pages-artifact@v3, deploy-pages@v4, pages.yml:24-45), the `ubuntu-latest` image (24.04.5 LTS, image 20261004.327.1 today, with Node 22.23.3 for the four Node harnesses and no pinned Node, a known open point), Python '3.12' (pages.yml:27; CPython 3.12 leaves support in October 2028), GitHub's Pages limits, the three Google Fonts families loaded from fonts.googleapis.com (core.py:32-33), the OSM Overpass endpoints and the AWS terrain bucket the renderer fetches from (geo.py:178, :458), and the attribution the map data licenses require (footer core.py:1698, captions core.py:720, the in-map tag core.py:521). The first deploy already failed on runner drift (a Python patch release, docs/WEBSITE_IMPLEMENTATION_LOG.md:945-951). The .cache/osm answers (284 MB) never expire, so region maps age until a forced render. Nothing in the docs lists what to check and when.

**Evidence.** `.github/workflows/pages.yml:21-45`; `the ubuntu-24.04 runner image README (actions/runner-images), lines 9-28, fetched 2026-10-13`; `tools/sitegen/core.py:32-33, :521, :720, :1696-1698`; `tools/lib/geo.py:178, :458-469`; `docs/WEBSITE_IMPLEMENTATION_LOG.md:945-951`; `docs/IMPLEMENTATION_REPORT.md:811-813`; https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits (fetched 2026-10-13); `the actions/deploy-pages README, line 52 (timeout 600000 ms)`.

**Proposal.** Add '## Yearly upkeep' to docs/DEVELOPING.md after the Storage budget section, a dated checklist with this year's value beside each item and one line 'if it changed, do this', plus a pointer under README.md:114 and a sentence in ADDING-TRIPS.md's closing notes tying it to the first trip of each year. Items: (1) size: run tools/size_report.py (or the three commands in the Storage budget) and `git count-objects -vH`; `git gc` when loose objects exceed 1,000. (2) workflow: for each `uses:` in pages.yml (checkout@v4, setup-python@v5, configure-pages@v5, upload-pages-artifact@v3, deploy-pages@v4) note the newest major and any deprecation notice; bump in one commit and prove it with `workflow_dispatch` (pages.yml:9) on a quiet day. (3) runner: read the ubuntu-latest image README (this year: 24.04.5, Node 22.23.3, Python 3.12.3 on the image, 3.12.15 installed by setup-python) and run the Node harnesses on the shipped Node; CPython 3.12 leaves support in October 2028, so plan the pages.yml bump before then and keep 3.9 while the Mac's system Python is 3.9.6. (4) limits: re-read the Pages limits page (site 1 GB, deploy 10 min, bandwidth 100 GB/month, repository 1 GB recommended) and update the budget table. (5) credits and endpoints: the caption credits are already tested (tests/test_report_page.py:82); add one assertion for the footer strings at core.py:1698 to an existing test file; confirm the terrain bucket (geo.py:178), both Overpass endpoints (geo.py:458) and the Google Fonts URL (core.py:32-33) still answer. (6) map data: OSM answers in .cache/osm never expire (geo.py:463); to refresh, delete .cache/osm before the year's single forced render round (gap10-03), not as a separate `--site --force`. (7) iCloud: look for conflict names under content/ (the validator warns), rendered/ and assets/ (git-ignored) and `.git/index N`. (8) run tools/validate.py and tools/privacy_audit.py and read the summaries. Files: docs/DEVELOPING.md, README.md, ADDING-TRIPS.md, one existing test file. Effort S.

**Files.** `docs/DEVELOPING.md`, `README.md`, `ADDING-TRIPS.md`, one existing test file.

**Effort.** S. Visitor value 1, author value 2.3, confidence high.

**Already known.** docs/IMPLEMENTATION_REPORT.md 15.4.5 (Node unpinned; report:811-813); docs/WEBSITE_IMPLEMENTATION_LOG.md:945-951 (runner drift on the first deploy)

**Risk.** A checklist nobody runs is a document; tie it to the first trip of each new year in ADDING-TRIPS.md's closing notes. Bumping action majors can change inputs (configure-pages, deploy-pages) and must be verified by a workflow_dispatch run before a trip depends on it.

**Review revision (applies on top of the text above).** Proposal item (6), corrected: 'once a year delete .cache/osm/ (or run with OSM_DIR pointing at an empty folder; geo.py:462-464 serves any cached answer for ever and no flag refreshes it), then run `render.py --site --force` so the region maps (2.3 MB tracked in rendered/site/) are drawn from a year of OSM edits, and reserve the single forced trip round for renderer changes (gap10-03)'. Item (7), corrected: 'look for iCloud conflict names under content/ (the validator reports them as errors, checks.py:571, and the build stops), rendered/ and assets/ (git-ignored, never built) and `.git/index N`'. Risk, corrected: 'tie it to the first trip of each new year in ADDING-TRIPS.md's last section, If something goes wrong (line 313), or a new short section after it'. The rest stands.

**Review note (condensed; the observation and proposal above are the revised text).** No such checklist exists (docs/DEVELOPING.md headings end at 'Measuring page loads', line 1428; README.md:114-124 lists only the check commands), and the facts hold: pages.yml:24-45 pins checkout@v4, setup-python@v5, configure-pages@v5, upload-pages-artifact@v3, deploy-pages@v4 and `python-version: '3.12'`; FONTS at tools/sitegen/core.py:32-33; credits at core.py:521 ('© OSM · Not for navigation'), :720 (caption) and :1698 (footer); TILE_URL at tools/lib/geo.py:178 and OVERPASS at :458. The dependencies are real and cited correctly: five actions pinned by major tag (pages.yml:24-45), Python '3.12' (pages.yml:27), Node unpinned (IMPLEMENTATION_REPORT.md:811-813), the Google Fonts URL (core.py:32-33), the terrain bucket and Overpass endpoints (geo.py:178, :458), the credits (core.py:521, :720, :1698), and the first deploy did fail on runner drift (WEBSITE_IMPLEMENTATION_LOG.md:945-951). Reproduced: pages.yml:24-45 pins checkout@v4, setup-python@v5, configure-pages@v5, upload-pages-artifact@v3, deploy-pages@v4, python-version '3.12' at :27, workflow_dispatch at :9; the runner image README (review scratch runner-ubuntu2404.md) lines 9-28 (24.04.5, image 20261004.327.1, Node 22.23.3); core.py:32-33 FONTS, :521 the in-map tag, :720 the caption credits, :1698 the footer credits, footer() at :1686 and map_caption() at :712; geo.py:178 TILE_URL and :458 OVERPASS; WEBSITE_IMPLEMENTATION_LOG.md:945-951 the runner-drift failure; IMPLEMENTATION_REPORT.md:811-813 is item 5 of 15.4 (Node unpinned); the actions/deploy-pages README (review scratch deploy-pages-README.md) line 52, timeout 600000; .cache/osm 284M.

**Gates.** The phase is done when every line below holds and is recorded in the log entry:

1. Before the bump: tests/test_mapkit_golden.py (hike loop, mtb out-and-back, two-segment planned route, about 10 s) and tests/test_render_contract.py (CI-gated, self-contained fixture, about 50 s) pass on 3.9 and 3.12 with -W error and the goldens are byte-identical across two PYTHONHASHSEED values; a DEM.sample through an array('d') tile equals the list result and the hillshade PNG bytes are unchanged; render_trip and render_site write meta['renderer'] (version, python, cwebp, date, osm) and the validator warns on a fixture whose folders disagree on the version; render.py stops without cwebp unless --allow-png.
2. Preview first: two or three site maps rendered at q75, q80 and q88 into a scratch folder and shown to Eric at 1x and 2x; the 1000-1199 and 1440 report frames, the phone overview squares and the card tile shown on the contact sheet of a fixed sample before the full run; if the quality changes, HILLSHADE_Q is set and the run starts with --site --force.
3. The run: VERSION bumped once; --list/--status lists every trip; python3 tools/render.py --jobs 2 --budget 3600 prints a progress line every 10 trips and an end summary (rendered, skipped, failed, OSM missing, site maps) and resumes across evenings through the hash, never through --force; .cache/osm answers used carry their 'fetched' date; the Overpass timeout stays 160 s.
4. After the run: no rendered/**/meta.json has hash null or osm_failed (grep); git diff --stat rendered/ shows .svg.html, .base.svg and meta.json only (and .webp only if the quality changed); the contact sheet in .cache/render-sheet/ reviewed by Eric; tall-route trips (34 with a track box over 1.4:1) show 1440×800 and 718×500 frames; the 10 multi-day phone overviews show numbered day squares; ski panels exist for Mountain biking (Santa Cruz, Lake Tahoe) and Hiking (Lake Tahoe) with the data-map-target wiring; the PCT overview carries month labels; cluster tooltips read 'N reports start here: …'; the Matterhorn wide map's scale bar reads 1 mi; contour labels carry u-mi/u-km tspans and the mile loop a km disc set; a 400×267 card tile is published and the cards use it; the region merges' pages build with no DUPLICATE IDS and the old region URLs with pages still answer.
5. Staged with git add by path (rendered/trips, rendered/site), git status shows no ' 2'/' 3' names, one commit 'Render round 2026' carrying the printed summary; git count-objects -vH before and after recorded; DEVELOPING.md's 'Storage budget' section holds the dated table in decimal MB with the commands beside each number, the per-trip costs, GitHub's limits with the URL and date, the committed-versus-build-time rule table and the caps attached to the derivative findings; tools/size_report.py (stdlib, read-only) reproduces those numbers and tests/test_size_report.py covers the classifier and per-year grouping; the 'Yearly upkeep' checklist exists with this year's values (actions, runner, limits, credits test, delete .cache/osm before the next round) and a comment beside VERSION states the measured cost of a round (9.7 MB packed for an SVG-only round, about 35 MB when the hillshades change).
6. Publish through Phase 8's publish.py and compare the live Matterhorn, Haute Route and map/ pages with the before captures; both Pythons and build.py --check pass; render.py is never run in CI.

**Tests to add.** New: `tests/render_fixtures.py`, `tests/golden/render/`, `tests/test_mapkit_golden.py`, `tests/test_render_contract.py`, `tests/test_size_report.py`. Extended: `tests/test_checks_site_maps.py`, `tests/test_render_goals.py`, `tests/test_report_page.py`, `tests/test_section_page.py`, one existing test file (gap10-06). Plus the checks the gates name that no unit test covers: Goldens byte-identical across two `PYTHONHASHSEED` values; `grep` of every `rendered/**/meta.json` for `hash: null` or `osm_failed`; `git diff --stat rendered/`; `git count-objects -vH` before and after; the contact sheet reviewed by Eric.

**Screenshots to capture.** The q75 / q80 / q88 side-by-side of two or three site maps at 1x and 2x; the contact sheet in `.cache/render-sheet/` before and after; the live Matterhorn report, Haute Route and `map/` against the before captures.

**Author inputs needed.** Decisions 21 and 22; one evening on the Mac with warm caches; a look at the contact sheet before the commit.

## 7. Findings register

All 265 findings, sorted by id. Visitor value and author value are the judges' averages; effort is S, M or L; the last column is the phase that holds the finding or "not planned" (reasons in section 8).

| Id | Area | Title | Effort | Visitor | Author | Phase |
| --- | --- | --- | --- | --- | --- | --- |
| a11y-01 | home | Name the home activity tiles by their whole content, not an id | S | 1.3 | 1 | not planned |
| a11y-02 | sections | Make the index row a titled link with a stretched hit area | M | 1.3 | 1 | not planned |
| a11y-03 | home | Give the home region name link a real 24 px box | S | 1.7 | 1 | Phase 13 |
| a11y-04 | maps-charts | Keep activity colors in forced-colors mode wherever they key a map | S | 1.3 | 1 | Phase 13 |
| a11y-05 | cross-site | Speak units in full and in the chosen unit system | M | 1.7 | 1 | Phase 13 |
| a11y-06 | regions | Draw a CSS-only focus halo on journal lines on region maps | S | 1.3 | 1 | Phase 12 |
| a11y-07 | pct | Stop disabling PCT month tabs under the write-ups filter | S | 2.3 | 1 | Phase 11 |
| a11y-08 | sections | Nest year-group rows one heading level under their year | S | 1.3 | 1 | Phase 13 |
| a11y-09 | multiday | Offer 'View as table' under every elevation and speed chart (also maps-14) | M | 1.7 | 1 | Phase 10 |
| a11y-10 | cross-site | Let controls grow with text zoom and wrap at 320 px | S | 1.7 | 1 | Phase 13 |
| a11y-11 | build-ci | Check ARIA id references and heading order in build.py --check | M | 1 | 2.3 | Phase 8 |
| a11y-12 | docs | Run and record a VoiceOver pass per page type | S | 1.7 | 2 | Phase 13 |
| a11y-13 | trips-explorer | Distinguish repeated trip titles in link names | S | 1.7 | 1 | Phase 7 |
| a11y-14 | photos | Announce the first photo when the viewer opens (also qa-11) | S | 1.3 | 1 | Phase 11 |
| a11y-15 | cross-site | Add a prefers-contrast: more block for the small gray type | S | 1.7 | 1 | Phase 13 |
| authoring-01 | authoring | One publish command that runs the five publish steps and stops on failure | M | 1 | 4.3 | Phase 8 |
| authoring-02 | build-ci | Watch the deploy from the terminal after the push | S | 1 | 3.3 | Phase 8 |
| authoring-03 | build-ci | Run the unit tests in CI only when code changed; skip docs-only pushes | S | 1 | 2.3 | Phase 8 |
| authoring-06 | authoring | Read Garmin's zip directly; no Garmin bulk-export path | S | 1 | 3 | Phase 6 |
| authoring-07 | authoring | List the Strava activities not yet on the site | S | 1 | 2.7 | Phase 6 |
| authoring-08 | authoring | Fix the two front-matter traps instead of warning about them | S | 1 | 3 | Phase 6 |
| authoring-09 | authoring | render.py --status: what a render would do, offline | S | 1 | 3.3 | Phase 6 |
| authoring-10 | authoring | Preview by symlink, open the new page, no traceback on Ctrl+C | S | 1 | 3.7 | Phase 6 |
| authoring-11 | authoring | A build diff that names the pages a change touched | S | 1 | 2 | Phase 8 |
| authoring-12 | docs | Index the developer docs and add a repository CLAUDE.md | S | 1 | 3 | Phase 8 |
| authoring-13 | authoring | Validate region and sub-type at entry and print the remaining steps | S | 1 | 3 | Phase 6 |
| authoring-14 | build-ci | Document the one-module command and one honest timing | S | 1 | 2 | Phase 8 |
| authoring-15 | build-ci | Tests for the import tools that have none | M | 1 | 3 | Phase 6 |
| authoring-16 | authoring | A tidy command for iCloud conflict copies, and a decision on where the checkout lives | S | 1 | 3.3 | Phase 8 |
| authoring-17 | build-ci | Run both Pythons and the three checks with one developer command | S | 1 | 3 | Phase 8 |
| authoring-18 | build-ci | An on-demand audit workflow: Lighthouse and screenshots, not a gate | M | 1 | 1.3 | not planned |
| authoring-19 | authoring | Defer the local upload desk; the command-line path covers it | S | 1 | 1.7 | Phase 8 |
| authoring-20 | authoring | Say what is and is not in the repository | S | 1 | 2.7 | Phase 8 |
| benchmark-02 | trips-explorer | Add a has-photos filter and photo counts to cards (also features-09) | S | 3 | 1 | Phase 7 |
| benchmark-05 | report | Let write-ups place photos inline | M | 2 | 2 | not planned |
| benchmark-08 | about | Year-by-year table on the About page | S | 2 | 1.3 | not planned |
| benchmark-10 | pct | Journal entries say their place in the hike | S | 2 | 1 | Phase 11 |
| benchmark-11 | report | Beta rows and a references list that can link out | S | 2 | 2 | Phase 10 |
| benchmark-13 | map-page | Pan-zoom region maps with a trips-in-view list | L | 2 | 1 | not planned |
| benchmark-14 | ticklist | Named lists with progress, linked to reports and goals | M | 2.3 | 2.7 | not planned |
| copy-01 | report | Derive the stats-source sentence from the content, not a constant | S | 1 | 1.3 | Phase 9 |
| copy-03 | trips-explorer | Cut excerpts at a sentence end when one fits | S | 3 | 1 | Phase 7 |
| copy-04 | trips-explorer | Label track-only trips on cards and rows, as the journal already does | S | 2.3 | 1 | Phase 10 |
| copy-05 | authoring | Flag Strava default titles for retitling, and warn on import | S | 1.3 | 2 | Phase 9 |
| copy-07 | authoring | A per-trip content report: which trips lack what | M | 1 | 3.7 | Phase 9 |
| copy-08 | authoring | Offer card_summary drafts made only of Eric's own sentences | S | 1 | 1.3 | not planned |
| copy-09 | report | One name per report section in the row, the bottom bar and the headings (also report-17) | S | 2.3 | 1 | Phase 10 |
| copy-11 | content | Make the five activity names parallel ('Backcountry Ski' among gerunds) | S | 1.3 | 1 | Phase 13 |
| copy-12 | cross-site | One verb per destination for action links | S | 1.7 | 1 | Phase 13 |
| copy-13 | maps-charts | One capitalization for 'Full track, not trimmed' in every caption | S | 1 | 1 | Phase 13 |
| copy-14 | nav-header-footer | Name the open menu button and expand 'PCT' for assistive tech | S | 1.3 | 1 | Phase 13 |
| copy-16 | regions | Show Eric the region and place inventory before the head lines expose it | S | 1.7 | 2.7 | Phase 9 |
| copy-17 | photos | List the cover and featured photos' alt texts for Eric's review | S | 1.3 | 2 | Phase 9 |
| copy-18 | maps-charts | Cluster pin tooltips: a count and a few titles, not 22 titles | S | 1.7 | 1 | Phase 15 |
| copy-19 | authoring | Gather the site's strings in one module with copy tests | L | 1 | 1 | not planned |
| copy-20 | ticklist | Keep the tick list's public empty state free of shell commands | S | 1 | 1 | Phase 13 |
| features-01 | content | A By-year block on About (a years/ page later) | S | 2.7 | 2 | Phase 9 |
| features-04 | content | Curated collections from a strict content manifest | M | 2 | 2 | not planned |
| features-05 | content | A summits: field, step 1 (the A-Z page waits) (also benchmark-06) | M | 3 | 2.3 | Phase 9 |
| features-06 | pct | PCT chapters: author-named day ranges with per-chapter stats | M | 2.3 | 2 | not planned |
| features-07 | pct | Journal rows show recorded distance so far | S | 2.3 | 1 | Phase 11 |
| features-08 | pct | Local 'Continue reading' bookmark on the PCT journal (also phone-17) | M | 2.3 | 1 | Phase 11 |
| features-10 | search | Make party names searchable; a partners facet is Eric's call | S | 2 | 1.3 | not planned |
| features-11 | report | Show the conditions: field the validator already accepts | S | 1.3 | 1.7 | Phase 9 |
| features-12 | regions | One GPX download for all tracks in a region | M | 2 | 1 | not planned |
| features-14 | cross-site | Dark mode: tokens are easy, the maps are the cost (also visual-14) | L | 2 | 1 | not planned |
| features-15 | about | Author-written pages: now and changelog from content/pages/ | S | 2 | 2.7 | not planned |
| features-16 | home | 'This week in past years' block on the home page (JavaScript only) | M | 2 | 1 | not planned |
| features-17 | regions | Region introductions from content/regions/<slug>.md | M | 2.3 | 2.3 | Phase 9 |
| gap1-01 | report | Let the report map column use the 1000-1199 band instead of stopping at 860 | S | 1.7 | 1 | Phase 12 |
| gap1-02 | maps-charts | Show 'Open the full map' as a link beside the key row below 1440 px | S | 1.7 | 1 | Phase 11 |
| gap1-03 | map-page | On touch screens, a first tap on a pin or line selects it; a second tap opens it | M | 2.3 | 1 | Phase 12 |
| gap1-04 | regions | Give list rows a tap target that highlights the track without leaving the page | M | 1.7 | 1 | not planned |
| gap1-05 | sections | Rethink the Ski page's sticky 360 px panel for touch tablets at 960-1199 | S | 1.3 | 1 | Phase 12 |
| gap1-06 | a11y | Guard decorative :hover rules with @media (hover: hover) | S | 1.7 | 1 | Phase 13 |
| gap1-07 | photos | Make the photo viewer's swipe reliable on touch screens (also phone-08) | S | 2.3 | 1 | Phase 11 |
| gap1-08 | docs | Add 768, 1024 and 1180 px captures and a touch pass to the review method | S | 1 | 2 | Phase 13 |
| gap10-01 | docs | Write the storage budget into DEVELOPING.md: weights, horizons, caps | S | 1 | 2.3 | Phase 15 |
| gap10-02 | build-ci | Add tools/size_report.py: tracked, history and site sizes with a projection | M | 1 | 2 | Phase 15 |
| gap10-03 | maps-charts | Make a forced render round cost only what changed, and run one a year | S | 1 | 2.3 | Phase 15 |
| gap10-04 | photos | Decide where each new derived file lives and cap what it adds | S | 1 | 2 | Phase 15 |
| gap10-05 | authoring | Take the checkout's 1.4 GB out of iCloud's way; state fresh-Mac costs | S | 1 | 3.3 | Phase 8 |
| gap10-06 | build-ci | A yearly upkeep checklist with today's values written down | S | 1 | 2.3 | Phase 15 |
| gap2-01 | map-page | Fit the stuck region map to the viewport on map/ and region pages | M | 2.3 | 1 | Phase 12 |
| gap2-02 | sections | Ski page: show the phone-shaped panel render on short desktop windows | S | 1.7 | 1 | Phase 12 |
| gap2-03 | multiday | Compact the sticky multi-day chapter rail on short windows | S | 1.7 | 1 | Phase 12 |
| gap2-04 | maps-charts | Full-screen map page: give a landscape phone the height back | S | 1.7 | 1 | Phase 12 |
| gap2-05 | pct | PCT journal: release the sticky month bar on short viewports | S | 1.7 | 1 | Phase 12 |
| gap2-06 | map-page | Keep a one-line map key beside the stuck region map | S | 1.7 | 1 | Phase 12 |
| gap2-07 | docs | One documented rule and one test class for every sticky part | S | 1 | 2 | Phase 12 |
| gap3-01 | search | Write the activity's inflections and synonyms into the keyword field | S | 3.3 | 1 | Phase 7 |
| gap3-02 | search | Match typed words at word starts, not inside words | S | 3 | 1 | Phase 7 |
| gap3-03 | search | Index each trip's year, month names and ski season | S | 3 | 1 | Phase 7 |
| gap3-04 | search | Let a journal day be found by its date | M | 2 | 1 | Phase 7 |
| gap3-05 | search | Make the placeholder and description say what is searched | S | 2 | 1 | Phase 7 |
| gap3-06 | trips-explorer | Status row names write-up-only matches and offers the activity filter | M | 2 | 1 | not planned |
| gap3-07 | search | Index the route shape words (loop, out and back) | S | 2.3 | 1 | Phase 7 |
| gap3-08 | trips-explorer | Keep the year groups when every best-match hit scores alike | S | 1 | 1 | not planned |
| gap4-01 | regions | Give every region-list row a stable id, arc-row-<slug> | S | 1.3 | 1 | Phase 12 |
| gap4-02 | map-page | Landing on a trip reuses the cluster-click sequence | S | 2 | 1 | Phase 12 |
| gap4-03 | report | 'See on the <Region> map' from every report, landing on its row | M | 3 | 1 | Phase 12 |
| gap4-04 | pct | The PCT page names the region maps that draw its days | S | 2 | 1 | Phase 12 |
| gap4-05 | maps-charts | A locator inset on the report, cut from the region map already rendered | M | 2.7 | 1 | not planned |
| gap4-06 | sections | Ski panel answers the same landing; home maps need not | S | 1 | 1 | not planned |
| gap5-01 | about | Add a Get-in-touch line to About and the footer, driven by a content file | M | 2.7 | 2.3 | Phase 14 |
| gap5-02 | nav-header-footer | Link the public repository and an issue path from the footer and About | S | 1.3 | 1.7 | Phase 14 |
| gap5-03 | about | Profile links with rel=me on About and in the footer, only those Eric names | S | 2 | 1.3 | Phase 14 |
| gap5-04 | report | Opt-in "View on Strava" link per report from the stored activity id | M | 2.3 | 1.3 | not planned |
| gap5-05 | about | Land the RSS links on a Follow section instead of raw XML | S | 2 | 1 | Phase 14 |
| gap5-06 | cross-site | Publish a JSON Feed beside feed.xml from the same item list | S | 1 | 1 | not planned |
| gap5-07 | about | Decide the email path: reader-side RSS-to-email now, a hosted list only if chosen | S | 1 | 1.3 | Phase 14 |
| gap5-08 | report | Put an "Ask about this trip" link on every report once an address exists | S | 2.3 | 1.7 | Phase 14 |
| gap6-01 | nav-header-footer | Show the MI/KM switch in the header at every width | M | 2.3 | 1 | not planned |
| gap6-02 | nav-header-footer | Move the menu's Units row above the fold of the open phone menu | S | 1.7 | 1 | Phase 13 |
| gap6-03 | cross-site | Start in kilometers when the browser's language is not US English | S | 1.7 | 1 | Phase 13 |
| gap6-04 | report | On phones, put the stats footnote under the strip as a disclosure | S | 1.7 | 1 | Phase 10 |
| gap6-05 | cross-site | One glossary feeds the footnote and About, with a link between them | S | 2 | 1 | Phase 10 |
| gap6-06 | maps-charts | Rename the chart item 'VERTICAL ×N' to 'VERTICAL SCALE ×N' | S | 2 | 1 | Phase 10 |
| gap6-07 | nav-header-footer | Footer: label AIARE 2 the way About already does | S | 1 | 1 | Phase 13 |
| gap6-08 | maps-charts | Map distance discs and their key follow the KM switch | L | 1.7 | 1 | not planned |
| gap7-01 | build-ci | The written, rehearsed rollback | S | 1 | 3.3 | Phase 8 |
| gap7-02 | build-ci | Let a workflow dispatch build any past commit on main | S | 1 | 2 | Phase 8 |
| gap7-03 | build-ci | Build drops a gone trip's pin and line from the region maps | M | 1 | 3.3 | Phase 8 |
| gap7-04 | docs | Warn that drafting a trip on github.com can fail the deploy | S | 1 | 2.3 | Phase 8 |
| gap7-05 | authoring | Add tools/doctor.py: one read-only check of the Mac | M | 1 | 3 | Phase 8 |
| gap7-06 | docs | Write the new-Mac setup and what a fresh clone refetches | S | 1 | 2.3 | Phase 8 |
| gap7-07 | docs | Document and detect the lost .git/index recovery | S | 1 | 2.7 | Phase 8 |
| gap7-09 | maps-charts | Guard the OSM cache against a corrupt answer | S | 1 | 2 | Phase 6 |
| gap7-10 | docs | Turn 'If something goes wrong' into a recovery section | S | 1 | 3 | Phase 8 |
| gap8-01 | authoring | Refuse --force on a trip that has a write-up or descriptions | S | 1 | 3.7 | Phase 6 |
| gap8-02 | authoring | add_trip.py --update: replace the track, keep the words and photos | M | 1 | 3.3 | Phase 9 |
| gap8-03 | authoring | trip_photos.py: add or remove photos on a published trip | M | 1 | 3.3 | Phase 9 |
| gap8-04 | maps-charts | Write titles into map labels at build time, not at render time | M | 1 | 2.3 | Phase 9 |
| gap8-05 | build-ci | Validator warns when a trip's maps are older than its inputs | S | 1.7 | 3.3 | Phase 6 |
| gap8-06 | authoring | edit_trips.py: set, unset or rename a key across many trips | S | 1 | 2 | not planned |
| gap8-07 | authoring | Fix a trip's time zone and recompute its date and start time | S | 1.7 | 2.3 | Phase 6 |
| gap8-08 | authoring | --day-of: replace a day, bump end_date, count day photos right | S | 1 | 2.3 | Phase 6 |
| gap8-09 | docs | ADDING-TRIPS.md: one section for changing a trip on the site | S | 1 | 3.3 | Phase 9 |
| gap9-01 | build-ci | Offline golden test for render_map, render_profile, render_tile and render_glyph | M | 1 | 3 | Phase 15 |
| gap9-02 | authoring | Before/after contact sheet of a fixed map sample (tools/render_sheet.py) | M | 1 | 3.3 | Phase 15 |
| gap9-03 | maps-charts | Render into a temp folder and swap, so a failed render keeps the last good map | S | 1 | 3.3 | Phase 6 |
| gap9-04 | authoring | Make the full re-render a resumable, budgeted job with an end-of-run summary | M | 1 | 3.3 | Phase 15 |
| gap9-05 | build-ci | Record renderer, Python and cwebp versions in meta.json; warn on a mixed render | M | 1 | 2.3 | Phase 15 |
| gap9-06 | authoring | Move the tile and OSM caches out of iCloud Drive and give answers an age (also gap7-08) | S | 1 | 3 | Phase 6 |
| gap9-07 | authoring | --offline, --prefetch and env-configurable terrain and Overpass endpoints | M | 1 | 1.3 | not planned |
| gap9-08 | performance | Cap the in-memory tile cache: array storage and an LRU | S | 1 | 2.3 | Phase 15 |
| gap9-09 | build-ci | Contract test: render.py's output is what build.py and core.py read | M | 1 | 2.3 | Phase 15 |
| ia-01 | nav-header-footer | Give the desktop header a path to the five activity pages | M | 1.7 | 1 | not planned |
| ia-02 | search | Make the header's Search a real search box that lands on the explorer | M | 3.3 | 1 | Phase 7 |
| ia-04 | trips-explorer | One region count on Trips and Map: leave the journal's own region out | S | 1.3 | 1 | Phase 7 |
| ia-05 | trips-explorer | Trips page: search above the browse block, browse trimmed and foldable (also phone-01, a11y-16, qa-08) | S | 2.7 | 1 | not planned |
| ia-06 | trips-explorer | Add a Month filter to the explorer so time of year is findable (also features-02, benchmark-01) | M | 3 | 1 | Phase 7 |
| ia-07 | trips-explorer | Sort the explorer by distance and gain, unknowns last (also features-03) | M | 3 | 1 | Phase 7 |
| ia-08 | report | More like this prefers the same place or a shared name before the region (also report-09) | M | 3.3 | 1 | Phase 7 |
| ia-09 | report | Link a report's region and year from the place line at every width (also phone-07, report-16) | S | 2.3 | 1 | Phase 12 |
| ia-10 | regions | Region pages: per-activity entry points with a shareable address (also qa-03) | S | 2 | 1 | Phase 12 |
| ia-11 | regions | A regions/ index page, linked from the footer, the menu and the crumbs (also benchmark-07) | M | 2 | 1 | not planned |
| ia-12 | sections | Section pages: a region band and linked region names | S | 2 | 1 | Phase 12 |
| ia-13 | nav-header-footer | One vocabulary for Reports, Trips, Map and PCT across header, crumbs and footer (also copy-10) | S | 2.3 | 1.3 | Phase 13 |
| ia-14 | ticklist | Show Tick list in the main nav once it holds a few goals | S | 1.7 | 1.7 | not planned |
| ia-15 | home | Choose the home page's two region maps in home.json (also visual-08) | S | 1 | 2.7 | Phase 9 |
| ia-16 | authoring | Close the search index's place and peak gaps with author tooling | M | 3.3 | 3 | Phase 9 |
| ia-18 | map-page | One archive: move the Map page's all-reports table into the explorer | L | 2 | 1 | not planned |
| ia-19 | about | About page as the site's guide: rows for Trips, Regions and Tick list; footnote links to the method | M | 1.7 | 1 | Phase 9 |
| maps-01 | maps-charts | Name the contour interval and keep in-map units honest under KM | S | 2 | 1 | Phase 10 |
| maps-02 | maps-charts | Key rows decode the base layer's trails and roads | M | 2.3 | 1 | Phase 10 |
| maps-03 | report | Frame tall routes in a taller wide and column map (also report-08) | M | 2.7 | 1.3 | Phase 15 |
| maps-04 | maps-charts | Hover and touch readout on the profile, with a dot on the map (also report-07, benchmark-03) | M | 3.3 | 1 | Phase 10 |
| maps-05 | multiday | Keep the numbered day squares on phone overview maps | S | 2.3 | 1 | Phase 15 |
| maps-06 | pct | Month labels along the PCT overview map | M | 2 | 1 | Phase 15 |
| maps-07 | map-page | Legend as an activity filter on region maps | M | 3 | 1 | Phase 12 |
| maps-09 | map-page | A locator map of all regions at the head of Map & archive | M | 2 | 1 | not planned |
| maps-10 | report | Full-screen phone map keeps a scale, key and disclaimer in view | S | 2 | 1 | Phase 11 |
| maps-11 | cross-site | Card-sized route tiles that fill the card frame | S | 2 | 1 | not planned |
| maps-13 | maps-charts | Zoomable topo on the full-screen map page, keyless tiles, loaded on demand | L | 3.7 | 1.3 | not planned |
| maps-15 | sections | Activity maps by region for hiking and mountain biking | M | 2.7 | 1 | Phase 15 |
| maps-16 | authoring | Batch every renderer change into one VERSION bump and re-render | M | 1 | 3.3 | Phase 15 |
| maps-17 | cross-site | A route-shape glyph beside the shape tag | S | 1 | 1 | not planned |
| perf-01 | cross-site | Put a content hash in the bundle file names (also authoring-05, resilience-11) | S | 2 | 2 | Phase 14 |
| perf-02 | cross-site | Self-host the three fonts and preload the two above the fold | M | 2.7 | 1.7 | Phase 14 |
| perf-03 | maps-charts | Shorten the id namespace of inlined map overlays | S | 1 | 1 | not planned |
| perf-04 | maps-charts | Move the overlay's repeated inline styles into map CSS classes | M | 1 | 1 | not planned |
| perf-05 | maps-charts | Encode hillshade rasters at WebP quality 75-80 instead of 88 | M | 2.7 | 1.7 | Phase 15 |
| perf-06 | home | Serve the home page's region maps as cached image overlays | M | 1.7 | 1 | not planned |
| perf-07 | sections | Preload the ski page's region map like the other section pages | S | 2 | 1 | Phase 14 |
| perf-08 | search | Fetch the search indexes when the box is focused, not on the first keystroke | S | 2 | 1 | Phase 7 |
| perf-09 | performance | Skip offscreen rendering work on the long list pages | S | 1.7 | 1 | not planned |
| perf-10 | performance | Load page scripts only on the pages that use them | M | 1.3 | 1 | not planned |
| perf-11 | performance | A small service worker for repeat visits and offline reading | L | 2.7 | 1 | not planned |
| perf-12 | authoring | Rebuild on change while serving the preview | S | 1 | 3.3 | Phase 6 |
| perf-13 | build-ci | Pin Node in CI (also authoring-04) | S | 1 | 2.3 | Phase 8 |
| perf-14 | sections | Serve the Hiking page's journal thumbnails from the card copies | S | 1.7 | 1 | Phase 14 |
| perf-15 | build-ci | Run each Node harness once per module instead of once per test | M | 1 | 2 | not planned |
| phone-02 | ticklist | Tick list and Trips: secondary filters behind one Filters button on phones (also benchmark-12) | M | 2.3 | 1.3 | Phase 7 |
| phone-03 | map-page | Map page on phones: collapse the All-reports years | M | 2.3 | 1 | Phase 12 |
| phone-04 | regions | Region maps on phones: two-line caption and a compact key (also maps-18, qa-09) | S | 1.7 | 1 | Phase 12 |
| phone-05 | trips-explorer | Trips on phones: make List a dense view or hide the toggle | S | 2.3 | 1 | Phase 7 |
| phone-06 | report | Share a report through the phone's share sheet (also report-13) | S | 2.3 | 1.3 | Phase 11 |
| phone-09 | trips-explorer | Stop iOS zooming on the selects and the copy field | S | 2 | 1 | Phase 13 |
| phone-10 | nav-header-footer | Short and notched phones: reclaim the fixed chrome | S | 1.7 | 1 | Phase 13 |
| phone-11 | nav-header-footer | Header that hides on scroll down, returns on scroll up | M | 1.7 | 1 | not planned |
| phone-12 | nav-header-footer | Add a Home row to the phone menu | S | 1.7 | 1 | Phase 13 |
| phone-13 | nav-header-footer | Title bar with back-to-top on the long index pages | M | 2.3 | 1 | Phase 13 |
| phone-14 | photos | A 1200 px photo copy for 3x phones | M | 2 | 1.3 | not planned |
| phone-15 | a11y | Raise the 11 px text floor on phones to 12 px | S | 2.3 | 1 | Phase 13 |
| phone-16 | seo-share | Home-screen icon and a minimal web manifest (also seo-15) | S | 1.7 | 1 | Phase 14 |
| phone-18 | multiday | Multi-day on phones: one sticky day navigation, not two | S | 1.7 | 1 | not planned |
| qa-01 | a11y | Silence the generated meta-line dot for screen readers | S | 1.3 | 1 | Phase 13 |
| qa-02 | map-page | Make a cluster click select its reports, not just the first row (also maps-08) | M | 3 | 1 | Phase 12 |
| qa-04 | sections | Let the ski season band dim the region map as well | M | 2 | 1 | Phase 12 |
| qa-05 | performance | Trips list view fetches 800 px photos for 200 px thumbnails | S | 1.7 | 1 | Phase 7 |
| qa-06 | map-page | Give region maps a full-screen page on phones (also phone-19) | M | 2.3 | 1 | Phase 12 |
| qa-07 | trips-explorer | Zero results should offer the nearest working query (also ia-17) | M | 3 | 1 | Phase 7 |
| qa-10 | sections | Give the scrolling filter bands a fade and scroll-into-view | S | 1.7 | 1 | Phase 13 |
| qa-12 | build-ci | Smoke-test the built site in headless Chrome during CI | M | 1 | 2.3 | Phase 8 |
| report-01 | report | Lead with the write-up on reports that have words but no photos | S | 3 | 1.3 | Phase 10 |
| report-02 | report | Give photo-only reports their lead photo | S | 3.3 | 1.3 | Phase 10 |
| report-03 | photos | Stop cropping a third of every 4:3 lead photo on desktop | S | 2.3 | 1.7 | Phase 10 |
| report-04 | report | Show elapsed time, finish time and pace from facts already recorded | S | 2.3 | 1 | Phase 10 |
| report-05 | maps-charts | Add clock time to the elevation table and the GPS max | S | 2 | 1 | Phase 10 |
| report-06 | photos | Place photos on the map and profile with mile and time captions (also maps-12, benchmark-04) | L | 2.7 | 1.7 | not planned |
| report-10 | multiday | Mark the days with words and photos in the multi-day day nav | S | 2 | 1 | Phase 10 |
| report-11 | multiday | Lead photo and a photo strip for multi-day pages (also visual-06) | M | 3.3 | 1.3 | Phase 10 |
| report-15 | ticklist | An approximate profile and gain for planned routes without elevation | S | 1.7 | 1.3 | not planned |
| report-18 | pct | Show journal photos as photos, not squares, on written days | M | 3.3 | 1.7 | Phase 11 |
| resilience-01 | nav-header-footer | Cover the script-failed state: header menu and search forms | S | 1.3 | 1 | Phase 13 |
| resilience-03 | search | Drop apostrophes in the search normalizer instead of adding aliases | S | 3.3 | 1.7 | Phase 7 |
| resilience-06 | photos | Let phone galleries keep a panorama's or tall portrait's shape | S | 1.7 | 1 | Phase 10 |
| resilience-07 | authoring | Publish only the photo files the front matter names | S | 1 | 1.3 | not planned |
| resilience-08 | build-ci | Parse the script bundle in CI | S | 1 | 2.3 | Phase 8 |
| resilience-09 | cross-site | Add fallbacks for CSS features older Safari and Firefox lack | S | 1.3 | 1 | not planned |
| resilience-10 | photos | Photo viewer: Back closes it, a failed photo says so | S | 2.3 | 1 | Phase 11 |
| resilience-12 | report | Show an honest empty box for a report whose map is not rendered | S | 1.3 | 2.3 | Phase 6 |
| resilience-13 | maps-charts | Open the full-screen map on the route without JavaScript | M | 1.7 | 1 | Phase 11 |
| seo-01 | seo-share | Put the activity and place into every trip page's title tag | S | 3 | 1.7 | Phase 14 |
| seo-02 | seo-share | Stop meta descriptions ending mid-sentence on 118 trip pages (also copy-02) | S | 2.3 | 1.3 | Phase 14 |
| seo-03 | seo-share | Add og:site_name, og:locale and article:section/tag from facts | S | 1.7 | 1 | Phase 14 |
| seo-04 | photos | Share a 1200x630 JPEG crop of each cover instead of the 4:3 WebP | M | 2.7 | 1.3 | Phase 14 |
| seo-05 | maps-charts | Render a route share image for the 62 photo-less report pages (also visual-12) | L | 2 | 1 | not planned |
| seo-06 | seo-share | WebSite, Person and BreadcrumbList schema where the page already shows it | M | 1.7 | 1 | Phase 14 |
| seo-07 | pct | Give the PCT journal's written days pages of their own (also report-12) | L | 2.7 | 1 | not planned |
| seo-08 | report | Decide how search engines treat the 39 track-only pages | S | 1.3 | 1.3 | Phase 14 |
| seo-09 | seo-share | Full write-ups and covers in the RSS feed, with a write-ups-only option (also benchmark-09, resilience-04) | M | 2.7 | 1 | Phase 14 |
| seo-10 | authoring | Honest publication dates for new reports: add_trip, feed pubDate, sitemap lastmod | S | 1.3 | 2.3 | Phase 9 |
| seo-11 | build-ci | A root robots.txt through a user-site repository, or sitemap submission | S | 1 | 1.3 | Phase 14 |
| seo-12 | seo-share | A Search Console verification hook and a documented submission step | S | 1.3 | 3.3 | Phase 14 |
| seo-13 | authoring | A local share-card preview sheet for every page | S | 1 | 2.3 | Phase 14 |
| seo-14 | cross-site | A search box and a slug-based suggestion on the 404 page (also ia-03, resilience-05) | S | 3 | 1 | Phase 7 |
| seo-16 | seo-share | A custom domain: what it changes, costs and fixes | M | 2 | 2.3 | not planned |
| visual-01 | home | Fill photo-less card slots with the route tile, no inset frame | S | 2.7 | 1.7 | Phase 13 |
| visual-02 | trips-explorer | Hide the Trips browse block once the explorer's form is live | S | 2.7 | 1.3 | Phase 7 |
| visual-03 | report | 'More like this' head: a factual label instead of the selection rule (also copy-06) | S | 2 | 1.3 | Phase 10 |
| visual-04 | trips-explorer | Give year group heads in long lists a readable size | S | 2.3 | 1 | Phase 13 |
| visual-05 | ticklist | Tick list: no filter apparatus until there are goals to filter | S | 2 | 2 | Phase 7 |
| visual-07 | home | Home Recent outings: show the write-up excerpt where one exists | S | 2.7 | 1.3 | Phase 7 |
| visual-09 | cross-site | One hover idiom: route red stays on the route | S | 1.7 | 1.3 | Phase 13 |
| visual-10 | cross-site | Fold duplicate type, tag and control sizes into named classes | S | 1 | 2 | Phase 13 |
| visual-11 | sections | Section lists: one column header per group, not labels on every row | M | 2.3 | 1 | Phase 13 |
| visual-13 | report | A print stylesheet for reports (also report-14, features-13, resilience-02) | S | 2 | 1 | Phase 13 |
| visual-15 | performance | Eager-load the first screen's route drawings and the pager glyphs | S | 1 | 1 | not planned |
| visual-16 | about | About: a place for Eric's own words and a portrait (also copy-15) | M | 2.7 | 3 | Phase 9 |
| visual-17 | nav-header-footer | Tablet landscape: show the full header nav from 1000 px | S | 1.7 | 1 | Phase 13 |
| visual-18 | home | Tablet: stop upscaling the phone render in the home region maps | S | 1.3 | 1 | not planned |
| visual-19 | ticklist | Goal page: say the distance once, and size a one-cell strip | S | 1.7 | 1 | Phase 10 |
| visual-20 | pct | PCT landing: one primary action among the three | S | 2 | 1 | Phase 11 |

## 8. Not planned and dropped

The 55 findings below are not in any phase. Each line gives the planner's reason; those marked as Eric's decision are built only if he says yes, and the alternatives are the losing half of a pair he picks in section 4.

| Id | Title | Why not planned |
| --- | --- | --- |
| maps-13 | Zoomable topo on the full-screen map page, keyless tiles, loaded on demand | Eric's decision; recommended not now: the site's first vendored runtime and a street-level view of each track's start, after the static map work; revisit after Phase 15. |
| benchmark-14 | Named lists with progress, linked to reports and goals | Needs Eric's decision and a first list before anything ships; the summits field (features-05) is the smaller cousin; build when he names a list. |
| features-15 | Author-written pages: now and changelog from content/pages/ | Superseded by visual-16 (the same content/about.md body slot). |
| report-06 | Place photos on the map and profile with mile and time captions | Existing photos and the Strava export carry no EXIF, so it serves only new trips; an L with a re-render for short write-ups; the caption: field already exists for Eric's words. |
| seo-16 | A custom domain: what it changes, costs and fixes | Eric's decision; recommended stay on github.io; the code is S if he decides later. |
| features-06 | PCT chapters: author-named day ranges with per-chapter stats | Needs Eric's chapter names and ranges first (plan:357); build the index with them in a later session. |
| features-04 | Curated collections from a strict content manifest | Ships empty until Eric curates; the explorer's filters and the region pages already reach the plan's example groupings; decision 14 stays open. |
| benchmark-05 | Let write-ups place photos inline | Write-ups are two or three sentences and the Photos section starts right under them; stripping the line from five excerpt paths is the real cost. |
| ia-05 | Trips page: search above the browse block, browse trimmed and foldable | Alternative to visual-02 (Phase 7); Eric picks one, recommended visual-02; its By-region trim can ride along if he prefers the links visible. |
| perf-11 | A small service worker for repeat visits and offline reading | Eric's decision; recommended no: a wrong cache pins stale pages for every returning visitor and nothing in CI can test it. |
| seo-07 | Give the PCT journal's written days pages of their own | Reverses plan:355 ('no day routes') and puts the same text on two URLs; only as an explicit decision, recommended no. |
| gap4-05 | A locator inset on the report, cut from the region map already rendered | Most Lake Tahoe trips start where several others do, so the inset dot would mark one spot for dozens, at two more images per report; gap4-03 gives the landing on the region map instead. |
| gap5-04 | Opt-in "View on Strava" link per report from the stored activity id | Eric's privacy decision (12.8): ties each timed track to his Strava page and a dead link cannot be detected by the build; recommended not now; build only on a yes. |
| ia-14 | Show Tick list in the main nav once it holds a few goals | Superseded by visual-05 (the form threshold); the nav entry stays per plan 20.2. |
| phone-14 | A 1200 px photo copy for 3x phones | Decision 12.1; 15-18 MB of derivatives for covers alone in an iCloud checkout; recommended not now, measure on a 3x phone first. |
| features-10 | Make party names searchable; a partners facet is Eric's call | Eric's privacy decision (PRIVACY_NOTES 6.5) reversing CONTENT_GUIDE:398; recommended no; one line if he says yes. |
| benchmark-08 | Year-by-year table on the About page | Superseded by features-01 (the same By-year block on About, Phase 9). |
| gap6-01 | Show the MI/KM switch in the header at every width | Alternative to gap6-02 (Phase 13) and reverses plan 8.1; Eric picks, recommended gap6-02. |
| gap8-06 | edit_trips.py: set, unset or rename a key across many trips | Superseded by authoring-08, which fixes the two parser traps instead of warning about them. |
| ia-11 | A regions/ index page, linked from the footer, the menu and the crumbs | Value too low for a new page module: regions/ is linked from nowhere and map/ lists every region; revisit if Search Console shows the 404 drawing visits. |
| ia-18 | One archive: move the Map page's all-reports table into the explorer | A third copy of 167 rows on a 384 KB page for a naming problem ia-13 settles; its Phase B retargets documented anchors. |
| report-15 | An approximate profile and gain for planned routes without elevation | Reaches one goal page and needs Eric to re-export the planned route with elevation first; the rule-compliant version (profile only when the file carries elevation) can follow then. |
| maps-09 | A locator map of all regions at the head of Map & archive | A contiguous-US frame collapses the Sierra pins into clusters and the continent-scale renderer draws no borders or names; the region tabs already order the regions. |
| maps-11 | Card-sized route tiles that fill the card frame | Duplicate of visual-01 (step 1 CSS in Phase 13, the 400 px tile in Phase 15). |
| perf-15 | Run each Node harness once per module instead of once per test | Harness surgery with a state-leak hazard for 30-40 s per run; not worth it under three minutes. |
| seo-05 | Render a route share image for the 62 photo-less report pages | A Mac-only composite for the 62 bare rides nobody shares; decision 12.4 closes with 'keep the text card' (Phase 14 records it). |
| features-12 | One GPX download for all tracks in a region | The first download control on region pages, about 17 MB per deploy, and one click collects every timed track of a region; a privacy weight the notes ask Eric to weigh. |
| features-14 | Dark mode: tokens are easy, the maps are the cost | Eric's decision; recommended not now: maps and photos stay light islands and two palettes must be kept in step forever. |
| features-16 | 'This week in past years' block on the home page (JavaScript only) | Generic blog furniture; would be the site's first JavaScript-only content block and a second fetch on the measured home page. |
| benchmark-13 | Pan-zoom region maps with a trips-in-view list | Clusters are baked into the render, so a CSS zoom enlarges the '22' badge rather than splitting it; the hover wiring already marks the rows. |
| gap3-06 | Status row names write-up-only matches and offers the activity filter | gap3-01 removes its main case and the per-card snippet already marks write-up-only hits; one more row above phone results (15.4.8). |
| phone-11 | Header that hides on scroll down, returns on scroll up | Hides the Phase 3 app bar's back-to-top and conflicts with the plan's motion limit for 56 px; recommended no. |
| phone-18 | Multi-day on phones: one sticky day navigation, not two | Trades the only one-tap day jump for 48 px; multiday.css:33-34 shows the three-bar stack was weighed. |
| ia-01 | Give the desktop header a path to the five activity pages | Reverses plan:629; only Map and Tick list lack body activity links and the footer covers them; an M on the sticky header. |
| perf-06 | Serve the home page's region maps as cached image overlays | Drops pin links and web fonts on the home maps for a saving below the fold. |
| perf-09 | Skip offscreen rendering work on the long list pages | Measure-first item: the default journal view lays out 32 rows, not 150; revisit only if a phone trace shows style plus layout over about 150 ms. |
| perf-10 | Load page scripts only on the pages that use them | 21 KB gzipped saved once per visit on a cached defer script; plan 12.3 says measure first and nothing has. |
| a11y-01 | Name the home activity tiles by their whole content, not an id | A weight-0 audit; the gain is voice control only and it reverses the recorded design note at home.py:203; revisit after a11y-12's VoiceOver pass. |
| a11y-02 | Make the index row a titled link with a stretched hit area | The same weight-0 audit on the row component every index list uses, with ten layout rules to move; rated and left in 15.4.12. |
| authoring-18 | An on-demand audit workflow: Lighthouse and screenshots, not a gate | Two third-party actions and a schedule for screenshots nobody reads; Phase 13's VoiceOver pass and Phase 14's real share check cover the gaps it names. |
| copy-08 | Offer card_summary drafts made only of Eric's own sentences | Folded into copy-07 (a column showing what each card says and its provenance); a suggested prefix is what the card already shows. |
| resilience-07 | Publish only the photo files the front matter names | The validator already warns about an undeclared photo and the repository is public, so a build-side filter unpublishes nothing. |
| resilience-09 | Add fallbacks for CSS features older Safari and Firefox lack | The cqw and :has() degradations are milder than stated; a two-line svh fallback is too small to carry and can ride with Phase 13 if the Safari check shows a collapsed viewer. |
| gap1-04 | Give list rows a tap target that highlights the track without leaving the page | A second control on every row of five page types for a map that is scrolled away on phones; gap1-03 covers the touch direction that matters. |
| gap9-07 | --offline, --prefetch and env-configurable terrain and Overpass endpoints | With warm local caches (gap9-06) a run barely waits on the network; --prefetch duplicates render_map's frame logic; the endpoints are stable with a fallback. |
| visual-15 | Eager-load the first screen's route drawings and the pager glyphs | The captures' empty boxes are an artifact; an unmeasured gain on 2.5 KB SVGs, against the measure-first rule. |
| maps-17 | A route-shape glyph beside the shape tag | Decoration beside a word that already says it, unreadable at 16x10 px; the map shows the shape anyway. |
| perf-03 | Shorten the id namespace of inlined map overlays | 12 KB raw but under 0.2 KB gzipped per overlay; a tidy-up that can ride along with other core.py work, not a phase item. |
| perf-04 | Move the overlay's repeated inline styles into map CSS classes | Stroke widths vary per map so one class is wrong for report maps; about 1 KB gzipped per overlay; needs a render. |
| copy-19 | Gather the site's strings in one module with copy tests | An i18n-style strings module for a one-language site; copy-12 and copy-13 carry their own tests. |
| gap3-08 | Keep the year groups when every best-match hit scores alike | 'All scores equal' almost never holds once a write-up mentions the word; Newest first is one select away. |
| gap4-06 | Ski panel answers the same landing; home maps need not | Nothing links to a ski-row id and section.js already follows a row to its tab. |
| gap5-06 | Publish a JSON Feed beside feed.xml from the same item list | Every reader consumes the RSS feed; a second format to keep stable for nobody. |
| gap6-08 | Map distance discs and their key follow the KM switch | Mile discs are labeled 'Mile' and DEVELOPING.md:87-88 records them as imperial by decision; converting them is a full re-render for a few metric trips. |
| visual-18 | Tablet: stop upscaling the phone render in the home region maps | Tablet-only cosmetic; decide after gap1-08's tablet captures in Phase 13, where 'leave it' is a real outcome. |

The skeptics dropped no finding outright (their verdicts were keep or modify, and the modified text is what section 6 prints), so every one of the 265 findings is either in a phase or in the table above.

## 9. Working rules for the Claude Code sessions

These restate what the repository's documents already require (`docs/DEVELOPING.md:1242-1278`, `README.md:41-59`, `ADDING-TRIPS.md:192`, `docs/WEBSITE_IMPLEMENTATION_LOG.md:3-4`, :14-15 and :677-680, `docs/IMPLEMENTATION_REPORT.md:327-348` and :476-484). Phase 8 writes them into a tracked `CLAUDE.md` at the repository root (authoring-12).

1. **One phase per session, on a branch from `main`, one commit per phase.** A session takes one phase on a branch `phase-N-<slug>` made from `main` (Phases 1 to 5 were built on `phase1-curated-homepage` and fast-forwarded onto `main` at publication, so `main` has no merge commits), never pushes, and ends with one commit (or a short series) per phase, staged by path, with the message `Phase N: <title>` (a second commit for the log entry is fine), its gates run and its log entry written. The build the gates compare against is a build of HEAD made before any edit. A phase that turns out to need another phase's item stops and says so.
2. **Stage by explicit path; never `git add -A` or `git add .`.** The iCloud conflict copies under `rendered/` and `assets/` (6,136 on disk today) are git-ignored (`.gitignore:7-19`), so `git add -A` would commit none of them; the rule exists because a copy under `content/` or anywhere else is not ignored (`git status --porcelain --untracked-files=all` lists 0 copies today, but a new one appears whenever iCloud resolves a conflict), and because the validator stops the build on a copy inside a trip folder (`tools/lib/checks.py:559-576`). Read `git status --short` for ` 2`, ` 3` and ` 4` names before every commit. Phase 8's `publish.py` and `tidy.py` make this mechanical; until then it is a habit.
3. **Push only when Eric asks.** No push, merge or deploy without his separate authorization; only a push to `main` publishes, and it publishes within about three minutes today (151-188 s over the last five runs; about a minute for a content push after Phase 8's authoring-03). Never rewrite history on `main`; a bad push is undone with `git revert` (Phase 8 writes and rehearses the recipe).
4. **Run the tests on both Pythons with warnings as errors**: `/usr/bin/python3 -W error -m unittest discover -s tests` (3.9.6) and the same on `python3.12`, which is what CI runs; keep every tool 3.9-compatible. Run the Node harnesses when `node` is present; CI's runner has it. When a change touches the build, compare two `--link` builds file by file (`diff -rq`).
5. **`tools/render.py` only on Eric's Mac, only when a track, a title or a `map:` setting changed, and only when Eric agrees.** It needs the internet and rewrites committed assets. CI never renders. Phase 6 adds `--status` so a session can say what a render would do without running it; Phase 15 is the one planned full round.
6. **Keep scratch copies tiny; never copy the checkout** (except the one worktree the review gate makes under the scratch folder and removes at the end). Build elsewhere with `python3 tools/build.py --out DIR --link --check` (about 4 s); `--out` refuses non-build folders and empties an earlier build; do not add `--check` to a partial `--only` build. Under 30 GB free (19 GB today), say so in the report, keep scratch builds linked, make no worktree, and ask Eric to clear space before Phase 15's render round; Phase 8's `doctor.py` prints the same WARN.
7. **Previews side by side before any visual decision.** For a choice about how the site looks (report-03's frame, gap1-01's column, qa-04's dimmed map, perf-05's hillshade quality, gap2-01's fit), build the variants into a scratch folder, capture them at the named width, and show Eric the set before asking him to pick. The variant that ships is pinned by a test.
8. **The three checks before every commit**: `python3 tools/validate.py`, the unit tests, `python3 tools/build.py --out <scratch> --link --check` (never a plain `--check`, which copies 240 MB into `_site/` and stalls on offloaded files). Phase 8's `check.py` runs them in one command with timings.
9. **Facts only from content; write-ups verbatim; no invented dates, captions, grades or copy.** "No copy was written for any page" heads every log entry. A missing optional field is a truthful fallback, never a reason to invent or to stop. Units go through `core.U`; links through `core.link`.
10. **Measure before optimizing**, by the method in `docs/DEVELOPING.md:1428-1439`, and record the numbers before and after in the log. A loading change without a measurement does not ship.
11. **Every phase writes its entry in `docs/WEBSITE_IMPLEMENTATION_LOG.md`**: changed files, behavior, the checks actually run with their results, the checks not run, remaining issues, author inputs needed and the next smallest step. A check that was not run is written as not run, never implied.
12. **Compatibility gate.** Every earlier output path, GPX byte, write-up, title, canonical URL and documented anchor survives each phase; compare builds file by file and walk the served site under `/personal-website/`.
13. **Privacy in writing.** The repository and this plan are public. Findings, log entries and commit messages stay at the level of `docs/PRIVACY_NOTES.md`: no home location, no start coordinates, no times when someone is away.

## 10. Test matrix additions

New test modules and extended ones per phase, taken from the findings' file lists (a module is "new" when it does not exist in `tests/` today), with the checks that need a browser, a device or a person beside them. A module is new in the first phase whose prompt creates it and extended after. Every phase also runs the three checks of section 9 rule 8 (`validate.py`, the suite on both Pythons, `build.py --out <scratch> --link --check`).

| Phase | New test modules | Existing modules extended | Checks beside the tests |
| --- | --- | --- | --- |
| 6 | `tests/test_add_trip.py`, `tests/test_fit_reader.py`, `tests/test_geo_cache.py`, `tests/test_strava_export.py`, `tests/test_tracks.py` | `tests/test_build_cli.py`, `tests/test_checks_site_maps.py`, `tests/test_frontmatter.py`, `tests/test_render_goals.py`, `tests/test_report_page.py` | Network off for the `--status` gate; a second terminal for `--watch`; `python3 tools/validate.py` before and after on today's content (0 errors, 1 warning today). |
| 7 | none | `tests/norm_cases.json`, `tests/test_a11y_static.py`, `tests/test_cover.py`, `tests/test_home.py`, `tests/test_nav.py`, `tests/test_notfound_page.py`, `tests/test_related.py`, `tests/test_report_page.py`, `tests/test_search.py`, `tests/test_ticklist_page.py`, `tests/test_trips_js.py`, `tests/test_trips_page.py`, `tests/ticklist_js_harness.js`, `tests/trips_js_harness.js` | A stdlib script over the built `trips/search.json` and `journal.json` for the named queries; the Node harnesses; `tests/run_orders.py`; a phone capture at 390 px of trips/ and tick-list/. |
| 8 | `tests/test_doctor.py`, `tests/test_publish_cli.py`, `tests/test_site_map_prune.py`, `tests/test_tidy.py` (and `tests/test_js_bundle.py` only if resilience-08's test does not fit `tests/test_build_cli.py`) | `tests/test_build_cli.py`, `tests/test_checks_site_maps.py`, `tests/test_sitecheck.py` | A temporary git repository for `tests/test_publish_cli.py`; one real content push timed with `gh run list`; `gh workflow run pages.yml -f ref=<sha>` tried once; the smoke job's first run checked in the Actions log. |
| 9 | `tests/test_content_report.py`, `tests/test_trip_photos.py` | `tests/test_about_units.py`, `tests/test_add_trip.py`, `tests/test_build_site.py`, `tests/test_checks.py`, `tests/test_curation.py`, `tests/test_home.py`, `tests/test_metadata.py`, `tests/test_region_page.py`, `tests/test_report_page.py`, `tests/test_search.py`, `tests/test_track_rules.py` | `diff -rq` of two `--link` builds before and after for the byte-identical gates; `python3 tools/validate.py -v` counts before and after Eric's afternoon. |
| 10 | `tests/profile_js_harness.js`, `tests/test_profile_js.py` | `tests/test_a11y_static.py`, `tests/test_build_site.py`, `tests/test_cards_extra.py`, `tests/test_checks.py`, `tests/test_related.py`, `tests/test_report_page.py`, `tests/test_ticklist_page.py`, `tests/test_track_rules.py` | Phone LCP on one photo-only report and the Haute Route by the `docs/DEVELOPING.md:1428` method; Chrome touch emulation for the readout; `grep` of the built site for the retired labels. |
| 11 | none | `tests/maplist_js_harness.js`, `tests/page_standin.js`, `tests/series_js_harness.js`, `tests/test_a11y_static.py`, `tests/test_report_page.py`, `tests/test_series_page.py` | Journal image bytes on the phone profile before and after; Chrome touch emulation for the swipe; the Node harnesses with a localStorage stub; a script over the 157 built report `map/` pages for `#route-start`; a real phone for Back and swipe. |
| 12 | none | `tests/maplist_js_harness.js`, `tests/test_a11y_static.py`, `tests/test_archive_page.py`, `tests/test_build_site.py`, `tests/test_home.py`, `tests/test_region_days.py`, `tests/test_region_page.py`, `tests/test_report_page.py`, `tests/test_series_page.py` | The Node harness for maplist.js with a coarse-pointer matchMedia stub; `build.py --check` for duplicate ids and broken anchors; browser captures at the five short-viewport sizes in the ShortViewportTests table. |
| 13 | `tests/test_section_page.py` (13B, visual-11) | `tests/test_a11y_static.py`, `tests/test_about_units.py`, `tests/test_build_site.py`, `tests/test_home.py`, `tests/test_nav.py`, `tests/test_region_page.py`, `tests/test_report_page.py`, `tests/test_ticklist_page.py`, `tests/test_trips_page.py`, `tests/ticklist_js_harness.js`, `tests/trips_js_harness.js` | Lighthouse mobile on the live home after the deploy (accessibility 100 expected); the cascade tests; Chrome touch emulation for stuck hover; an accessibility snapshot of the home page; forced-colors emulation; print preview in two browsers; VoiceOver on two devices. |
| 14 | `tests/test_about_follow.py`, `tests/test_share_preview.py` | `tests/test_build_site.py`, `tests/test_metadata.py`, `tests/test_nav.py`, `tests/test_privacy_audit.py`, `tests/test_report_page.py`, `tests/test_series_page.py`, `tests/test_sitecheck.py`, `tests/test_ticklist_page.py` | `curl -I` on the live versioned asset; the W3C feed validator once; Google's Rich Results Test on one report and the home; desktop first paint over 25 runs before and after the fonts; the share previews looked at by a person. |
| 15 | `tests/render_fixtures.py`, `tests/golden/render/`, `tests/test_mapkit_golden.py`, `tests/test_render_contract.py`, `tests/test_size_report.py` | `tests/test_checks_site_maps.py`, `tests/test_render_goals.py`, `tests/test_report_page.py`, `tests/test_section_page.py`, one existing test file (gap10-06) | Goldens byte-identical across two `PYTHONHASHSEED` values; `grep` of every `rendered/**/meta.json` for `hash: null` or `osm_failed`; `git diff --stat rendered/`; `git count-objects -vH` before and after; the contact sheet reviewed by Eric. |

Across the plan the suite gains a fixture-based test for the import tools (`tests/test_add_trip.py`), a temporary-git-repository test for the publish command (`tests/test_publish_cli.py`), an offline golden test and a CI-gated contract test for the renderer (`tests/test_mapkit_golden.py`, `tests/test_render_contract.py`), a sticky-parts table test (`ShortViewportTests` in `tests/test_a11y_static.py`), a profile-readout harness (`tests/profile_js_harness.js`) and new cases in the four existing Node harnesses. The checks that no test can replace stay listed in each phase: Lighthouse on the live home after Phase 13, a real phone in Phase 11, VoiceOver in Phase 13, a real share preview in Phase 14, and Eric's eyes on the contact sheet in Phase 15.
