# Claude Code prompt pack 3: the "Alpine" redesign (Phases 16 to 20)

Written 2026-10-25 against `main` at `6106f0a`, which is what https://esichak.github.io/personal-website/ serves today.
It follows `docs/claude-code-website-prompt-2.md` (Phases 6 to 15, published 2026-10-25) and keeps its working rules.
The look it describes is Concept C, "Alpine Editorial", chosen by Eric on 2026-10-25 from four concepts drawn on a
design canvas (https://claude.ai/artifact/5jRzDSk57coSqeLV8sRaXM, private to Eric; the canvas files
`project/C-Home.dc.html` and `project/C-Report-Phone.dc.html` are the source of the two mock-ups). The same two
mock-ups are in this folder as standalone HTML, with the images loaded from the live site:

- `reference/home-1280.html`: the home page at 1280 px (fluid; open it at any width).
- `reference/report-phone-390.html`: the Matterhorn Peak report at 390 px.

They are pictures of the intent, not code to copy: they hold no `core.U` units, no `core.link` links, no `srcset`,
none of the no-JavaScript, sticky, forced-colours or screen-reader rules the real pages carry. Section 2 below is the
specification; where a mock-up and section 2 disagree, section 2 wins; where section 2 is silent, the mock-up shows
the intent and the existing rule in `docs/DEVELOPING.md` decides the mechanics.

## How to use this file

- One phase per Claude Code session, in order, Phase 16 first. Start each session with one line and nothing else:

  `Read docs/redesign-c/PROMPT.md in full, then run Phase 16.`

  The session reads the standing instructions (section 1), the specification (section 2), the decisions (section 3)
  and the phase's prompt (section 4) itself; nothing needs pasting. To run them back to back, say instead
  `Read docs/redesign-c/PROMPT.md in full, then run Phases 16 to 19 without pausing`: the session then commits each
  phase, takes the default for every decision in section 3 that you have not answered, and starts the next; it still
  never pushes and never renders.
- Read each session's report and look at its contact sheet before the next phase. The Gate line under each phase says
  what must be true before you move on.
- Section 3 lists the decisions. Answer the ones you care about in the first message of a session; a default stands
  when you say nothing.
- Phase 20 is the review gate of prompt pack 2 ("Review gate before each publication",
  `docs/claude-code-website-prompt-2.md` from line 1438) with the additions written here, and it ends with a push only
  when you say so.

## 1. Standing instructions (every session)

```
You are working in the personal-website repository, in its checkout on Eric's Mac (git; main is the
published branch, and the work of a phase happens on a branch made from it). Before doing anything else, read the
repository's CLAUDE.md, the workspace CLAUDE.md one folder above it (../CLAUDE.md), README.md, docs/DEVELOPING.md in
full, the latest entries of docs/WEBSITE_IMPLEMENTATION_LOG.md (Phase 15, the review gate and the publication of
2026-10-25), and this file, docs/redesign-c/PROMPT.md, in full, including the two files under docs/redesign-c/reference/.
The hard rules are in docs/DEVELOPING.md under "Rules" (from line 120) and stay in force unchanged: facts only from the
content files, write-ups verbatim, no invented dates, captions, grades or conditions, every distance and height through
core.U / core.distance / core.elev with the MI|KM switch, relative links through core.link, static maps through
core.map_block, the accessibility rules (landmarks, one h1, heading order, 44 px targets, 12/16 px text on a phone,
4.5:1 contrast, visible focus, hover under @media (hover: hover), forced colours, prefers-contrast), what must work
without JavaScript, the sticky-parts table, the copy rules (one verb per destination, the caption wordings, Mono-S lines
in caps) and the privacy rules. The design section of docs/DEVELOPING.md ("Design: Datum", line 96) is what this pack
replaces: section 2 of this file is the new design, and Phase 16 rewrites that section of DEVELOPING.md to match.
Keep the tools compatible with Python 3.9 (the Mac's /usr/bin/python3 is 3.9.6; CI runs 3.12).

Working rules for this session:
1. Work on a branch redesign-N-<slug> made from main (the previous phases were built on a branch and fast-forwarded
   onto main at publication, so main has no merge commits) and never push, merge or deploy; a push happens only when
   Eric says so in his own words, in the Phase 20 session. End the phase with one commit on that branch, staged by
   path, message 'Phase N: <title>' (a second commit for the log entry is fine). The 'before' build the gates compare
   against is a build of HEAD made before any edit; keep it for the contact sheet.
2. Stage by explicit path (git add "assets/css/base.css" ...). Never run git add -A or git add . : the thousands of
   iCloud conflict copies under rendered/ and assets/ (named like 'meta 3.json', 'map-wide 4.webp' or 'trips 2.js')
   are git-ignored and never committed, but content/, tests/, tools/ and docs/ can hold copies ('CLAUDE 2.md',
   'tests/test_smoke 2.py', 'content/author 2.json') that are not ignored. Read git status --short before every commit
   and refuse any ' 2', ' 3', ' 4' name; python3 tools/tidy.py lists them. The untracked rendered/trips/*/map-wide.png
   and *.meta.json files are leftovers of Phase 15's render round: leave them alone and never stage them.
3. Never run tools/render.py. This redesign changes no track, no map setting and no renderer: the committed maps,
   hillshades, profiles, tiles and glyphs are reused as they are. The rendered fragments carry the old font stack
   ("Archivo, 'Helvetica Neue', system-ui, sans-serif") and the build rewrites it to var(--sans) (tools/build.py:91),
   so a new --sans reaches every map label without a redraw; keep that replacement string exactly as it is.
4. Never run tools/fonts.py without Eric's go-ahead in the session (it needs the internet and writes assets/fonts/ and
   assets/css/fonts.css). Until it has run, the pages load Google's stylesheet from core.FONTS as they do today when
   fonts.css is absent.
5. Keep scratch copies tiny. Never copy the checkout, except the one worktree the review gate makes under the scratch
   folder and removes at the end. Build with: python3 tools/build.py --out <scratch folder> --link --check (symlinks,
   a few seconds). The scratch folder is the session's scratchpad directory (named in the system prompt) or
   ~/Library/Caches/personal-website/; never --out _site/ (240 MB of copies that stall when iCloud has offloaded
   rendered/). A partial build (--only) must not carry --check. Under 30 GB free, say so in the report and make no
   worktree; python3 tools/doctor.py prints the same WARN.
6. Run the tests on both Pythons with warnings as errors before the phase ends: /usr/bin/python3 -W error -m unittest
   discover -s tests and python3.12 -W error -m unittest discover -s tests. One module: python3 -m unittest discover
   -s tests -p test_x.py. The Node harnesses run when node is on PATH. python3 tools/check.py runs all of it.
7. Facts only from content: no new sentence about a trip, no caption, no grade, no condition, no date. A count the
   page shows (167 reports, 86 in Lake Tahoe, since 2021) is computed from site['published'] at build time, never
   typed. Interface copy (labels, buttons, headings) is allowed and is listed in the report as copy Eric should read;
   the existing wordings of docs/DEVELOPING.md "Copy" stay unless this file changes one.
8. Previews before a visual decision: when a phase asks Eric to choose how something looks, build the options side by
   side (same page, same width) and show him the pictures before asking; never ask him to pick blind. Every phase ends
   with a contact sheet: the pages it touched, before and after, at 1440, 1024 and 390 px, captured with headless
   Chrome (the way tools/smoke.py drives it) or the session's browser pane, saved under .cache/redesign/<phase>/ and
   paired on one local HTML page there. Look at the sheet yourself before writing the report, and fix what is wrong.
9. Privacy: the repository is public. Write nothing into code, tests, docs or the log that names a home location,
   start coordinates, which trips share a start, or times someone is away. docs/PRIVACY_NOTES.md is the level of
   detail allowed. Fixtures are synthetic (tests/gpx_fixtures.py, tests/helpers.py); never a real write-up or a real
   recording in tests/. The reference mock-ups under docs/redesign-c/ load photos the site already publishes.
10. Cite what you touch: when you change a documented rule, say so in the log entry with the file and line of the
    rule, and change the documentation in the same commit (docs/DEVELOPING.md, docs/CONTENT_GUIDE.md where a content
    field's effect changes, README.md where a command changes).
11. Change the look, not the mechanics. Every id, anchor, landmark, ARIA attribute, data attribute, class a script or
    a test reads, URL, feed guid, sitemap address, JSON-LD block and meta tag stays as it is unless a phase says
    otherwise. The page scripts (assets/js) are not rewritten; where a class they read must move, keep the class and
    say so in the log. A test that pins an old value of the design (a colour, a family, a preload) is updated to the
    new value in the same commit; a test that pins a rule (contrast, target size, heading order, no-script header,
    sticky release) is made to pass, never loosened.
12. Write one entry in docs/WEBSITE_IMPLEMENTATION_LOG.md at the end of the phase, in the format of the Phase 15 entry
    ('## Phase N - <Title> (<date>)', '### Author inputs', '### Changed files' table, '### Behaviour' bullets,
    '### Where the work departs from the prompt', '### Review', '### Checks actually run' table ending with what was
    not run, '### Remaining issues and author inputs'). The checks table names only checks that actually ran, with the
    build they ran on (commit or 'working tree at <time>') and the Python version. Never claim a check you did not run.

Report format at the end of the phase (in the chat, after the log entry is written):
- Changed files: one line each, what changed.
- Commit: the branch and the sha of the phase's commit (and of the log commit, if separate).
- Behavior: what a visitor or Eric sees differently, page by page.
- Tests run and their results: the two Pythons with -W error (counts, time), build.py --out <scratch> --link --check
  (page and trip counts), the Node harnesses, and the numbers the gate asks for.
- The contact sheet: its path, and the views on it, with the width and page of each.
- Interface copy added or changed, for Eric to read.
- Problems met and how they were resolved, or left.
- Missing author inputs: decisions, text or files only Eric can supply.
- The next smallest step.
```

## 2. The design: "Alpine"

### 2.1 The idea

A white page, one serif that only ever appears large, a plain sans for everything that is read, a mono for everything
that is measured, and photographs that are allowed to be big. Where Datum put a warm paper behind everything and kept
the photos in frames, Alpine lets the lead photo fill the width with the title set over it, and keeps the rest of the
page quiet: hairline rules, no fills, no radii, no shadows, no colour besides the route line and the activity marks.
The site reads like a magazine's contents page that happens to carry a GPX track and a map on every story. Nothing a
visitor relies on today is removed: every list, filter, map, chart, download, key row and caption stays, restyled.

Name it "Alpine" in docs/DEVELOPING.md, in base.css's opening comment and in the log, so the old name stops meaning
"the current design".

### 2.2 Colour

Tokens in `assets/css/base.css:4-22`, replaced one for one; the names stay so that the page sheets keep working.

| Token | Datum | Alpine | Used for |
| --- | --- | --- | --- |
| `--paper` | `#F2F1EC` | `#FFFFFF` | the page |
| `--surface` | `#FAFAF7` | `#F7F7F5` | map paper behind a render, an image slot before it loads |
| `--sunk` | `#E8E6DF` | `#EFEFED` | the profile's fill, a pressed control, the explorer's list background |
| `--ink` | `#16171A` | `#111111` | text, strong rules, filled buttons |
| `--ink-2` | `#45474C` | `#5E5E5E` | secondary text (place lines, card summaries, captions): 7.0:1 on white |
| `--ink-3` | `#66686D` | `#6B6B6B` | labels, units, meta lines: 5.3:1 on white, so an 11 px label still passes |
| `--rule` | `#D6D4CC` | `#E6E6E6` | hairlines between rows, around a map from 560 px, under the header |
| `--rule-strong` | `#8C8A83` | `#111111` | the rule under a section head, above the footer, under the stats strip |
| `--route` | `#D2381A` | `#D2381A` (decision 3) | the GPX line, the 3 px active bars; nothing else |
| `--map-paper` | `#EEECE6` | `#F7F7F5` | the route tile behind a card without a photo |
| `--profile-fill` | `#E2DFD6` | `#EFEFED` | the area under the elevation line |
| `--water-ink`, `--ski`, `--clm`, `--hik`, `--mtb`, `--oth` | as today | unchanged | the activity colours are a system, not a style; always with icon and word |

New tokens: `--scrim: linear-gradient(180deg, rgba(17, 17, 17, 0) 40%, rgba(17, 17, 17, 0.78) 100%)` for the text
band over a hero photo, and `--on-photo: #FFFFFF` for the text in it. Text over a photo is always white on that scrim;
when a photo is light at the bottom the scrim gets stronger (a second gradient stop), the text never changes colour.
`color-scheme` stays `light`. The `prefers-contrast: more` and `forced-colors` blocks keep their mechanics and take
the new values (`--ink-3` becomes `--ink-2` there, as today).

Every text colour on every background must pass 4.5:1 (3:1 from 24 px); list the pairs you checked in the log.

### 2.3 Type

Three families, from Google Fonts, self-hosted by `tools/fonts.py` once Eric agrees (decision 4):

- `--serif: 'Instrument Serif', Georgia, serif`: roman and italic, weight 400 only. Display only: never below 22 px,
  never for body text, never for a label. It carries every page title, section heading, card and row title, the site
  statement on the home page, the lead paragraph of a write-up (decision 2), the pager's titles and the footer's name.
- `--sans: Inter, system-ui, -apple-system, 'Helvetica Neue', sans-serif`: weights 400, 500 and 600. Body text
  (write-ups, About, region introductions), the navigation, buttons, labels, captions, meta lines that are words.
- `--mono: 'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, monospace`: weights 400 and 500, `tabular-nums`.
  Everything measured: the stats strip, stat columns, dates in Mono-S caps lines, the units switch, chart and map
  labels, table cells, counts.

Google's CSS address for `core.FONTS` (`tools/sitegen/core.py:40`): `Instrument+Serif:ital@0;1`,
`Inter:wght@400;500;600`, `IBM+Plex+Mono:wght@400;500`, `display=swap`. `tools/fonts.py` `FACES` (line 27) becomes
the four Latin files: Instrument Serif roman, Instrument Serif italic, Inter (one variable file 400–600), IBM Plex Mono
(400 and 500, or the two static files if Google serves no range), with their OFL texts from the `google/fonts`
repository (`ofl/instrumentserif`, `ofl/inter`, `ofl/ibmplexmono`); `core.FONT_PRELOADS` names the serif roman and
Inter, the two faces the first screen needs. `tools/lib/mapkit.py:31` `SANS` becomes the new sans stack so that a
future render carries it; `tools/build.py:91` then replaces both the old string and the new one with `var(--sans)`.

The type classes keep their names (`assets/css/base.css:52-95`; the pages' sheets and the modules use them), with
these sizes (phone / tablet ≥ 760 / desktop ≥ 1200, in px/line-height):

| Class | Family | Phone | Tablet | Desktop | Notes |
| --- | --- | --- | --- | --- | --- |
| `t-d1` | serif 400 | 48/0.96 | 76/0.96 | 96/0.94 | page and report titles; letter-spacing −0.02em; `text-wrap: balance` |
| `t-d1--long` | serif 400 | 40/1.0 | 60/0.98 | 76/0.96 | titles over 28 characters (the existing rule) |
| `t-d2` | serif 400 | 40/1.02 | 52/1.02 | 60/1.02 | the home statement, a section page's head |
| `t-h2` | serif 400 | 32/1.0 | 40/1.0 | 44/1.0 | section headings, with a 1 px ink rule under the heading row |
| `t-h3` | serif 400 | 26/1.05 | 30/1.05 | 34/1.05 | card and list-row titles; small cards 22/1.1 |
| `t-lede` | serif 400 | 26/1.25 | 28/1.3 | 32/1.3 | the lead paragraph; ink, not ink-2 |
| `t-dek` | sans 400 | 16/1.5 | 18/1.5 | 18/1.5 | ink-2; replaces the italic serif dek |
| `t-body` | sans 400 | 17/1.65 | 18/1.7 | 19/1.7 | write-ups; `.prose` max-width 640 px |
| `t-excerpt` | sans 400 | 15/1.5 | 16/1.5 | 16/1.5 | ink-2 |
| `t-small` | sans 400 | 13/1.45 | 14/1.45 | 14/1.45 | ink-3 |
| `t-label` | sans 500 | 11/16 | 12/16 | 12/16 | uppercase, 0.12em, ink-3 |
| `t-data-xl` | mono 500 | 20/24 | 24/28 | 28/32 | the stats strip; letter-spacing −0.01em |
| `t-data-m` | mono 500 | 14/20 | 15/20 | 15/20 | stat columns, table cells |
| `t-mono-s` | mono 400 | 11/16 | 12/16 | 12/16 | uppercase, 0.1em, ink-3; the Mono-S caps rule stays (`SAT, JAN 17, 2026 · 12.8 MI`) |

Phone text stays at 12/16 px or more wherever docs/DEVELOPING.md requires it today (labels, key rows, tags, the map's
credit tag, the day ruler, table heads); `t-label` and `t-mono-s` at 11 px are for the few places the Datum rule
already allows below 12 px, and nowhere new. Headings balance their lines and prose avoids one-word last lines as
today (`base.css:93-94`).

### 2.4 Layout, rules and surfaces

- `.wrap` max-width 1360 px (was 1248), page margins 16 / 40 / 40 px (`--m`); `.bleed` stays full width; section gap
  `--sec` 56 / 72 / 96 px as today. The 12-column grid stays for the pages that use it.
- Header height `--header-h` 56 / 64 / 72 px. Breakpoints unchanged: phone < 760, tablet 760–1199, desktop ≥ 1200;
  the header nav collapses to the menu button below 1000 px as today.
- Radii 0 everywhere: photos, maps, cards, chips, buttons, inputs (Datum's 2 px on chips and buttons goes).
- No fills behind cards or rows; no shadows; no borders around photos. Rules do the separating: 1 px `--rule` between
  rows, 1 px `--rule-strong` under a section's heading row, above the footer and under the stats strip; 1 px `--rule`
  around a map render from 560 px (none on a phone, where the map runs edge to edge).
- Links: no colour change on hover; a 1 px underline 4 px down appears (`text-decoration-thickness: 1px;
  text-underline-offset: 4px`), under `@media (hover: hover)`. Cards and rows underline their title on hover. Focus
  stays the 2 px ink outline.
- Photos: `object-fit: cover` with the focal point from the content (`cover_focal_x` / `cover_focal_y`, as
  `core.cover_img` does today); 3:2 for feature cards and the home grid, 4:3 for list thumbnails and the recent cards,
  the photo's own shape in a gallery (as today's gallery rules decide).

### 2.5 Components

- **Header** (`core.header`, `core.py:2339`; `base.css:168-301`): white, 1 px `--rule` under it; the name "Eric Sichak"
  at the left in sans 600 15 px, letter-spacing 0.02em, nothing under it (no tagline); the primary links in sans 500
  13 px uppercase 0.12em with 32 px gaps; the units switch as two tabs, mono 12 px, the chosen unit with a 2 px ink
  bottom border and the other in ink-3; the search box (Phase 7's) as a bare input with a 1 px ink bottom border and
  no fill. Sticky behaviour, the no-script header, the script-failed twin rules, the short-viewport release and the
  menu stay exactly as documented. Phone: 56 px, name left, the units tabs and the menu button right.
- **Menu** (phone and below 1000 px): white, the Units row first as today, the links in serif 32 px, the five
  activities ("By activity") in sans 15 px under a `t-label`.
- **Footer** (`core.footer`, `core.py:2428`): a 1 px ink rule, then the name in serif 26 px at the left and, at the
  right, `BASED IN LAKE TAHOE · AVALANCHE TRAINING: AIARE 2 · GPS RECORDINGS VIA STRAVA` in sans 500 12 px uppercase
  ink-2 (the first two items are About's label line and the Strava item comes from `content.stats_source` as today;
  write nothing that the content does not give); under them the footer's link lists in sans 14 px ink-2 as today
  (By activity, Map, Tick list, PCT, About, the feed, the contact if `content/author.json` gives one).
- **Buttons** (`base.css:396`): `.btn` ink fill, white text, min-height 44 px, padding 0 20 px, sans 500 14–15 px;
  `.btn--ghost` 1 px ink border on white; hover darkens the fill to `#000000` or fills the ghost with ink. No radius.
  Icon buttons keep their `aria-label`.
- **Chips and tags** (`base.css:327`): square, 1 px `--rule` border, sans 500 12 px uppercase 0.08em; an activity chip
  keeps its disc and word; `.chip--title` on a report (the activity link under the crumbs) the same; the filter chips
  (`.fchip`, radios) square too, `aria-checked="true"` as ink fill with white text; `min-height`, never `height`.
- **Cards** (`core.trip_card`, `core.py:1769`; `base.css:363`): no border, no fill; a 3:2 photo (4:3 on the home's
  recent cards), the route tile on `--map-paper` when there is no photo, the activity disc slot when there is neither
  (all three as today); above the title a `t-mono-s` line `SEP 20, 2026 · HIKING`; the title in serif `t-h3`; a sans
  15 px ink-2 place line; the stats line in sans 15 px ink-2 through `core.U` (`19.9 mi · 7,546 ft · 9:55 moving`);
  the summary in `t-excerpt` where one exists. The media link stays `tabindex="-1" aria-hidden="true"` and the title
  link the tab stop, described by the meta line.
- **List rows** (`core.trip_row`, `core.py:1683`; `base.css:604`): 22 px of vertical padding, a 1 px `--rule` under
  each; a 132 × 99 px thumbnail (4:3; the 120 px tile for `.trow--brief` stays) at the left; the title in serif
  `t-h3`; under it a sans 15 px ink-2 line (place, the `Track only` or `Multi-day · N days` tag, the photo count); at
  the right the stat columns in `t-data-m`, right-aligned, units in ink-3, the column labels once per group from 760
  px as today (visual-11). On a phone the stats drop under the title as the Mono-S line `.trow-ps` as today.
- **Stats strip** (`base.css:525`): the numbers in `t-data-xl` with their `t-label` under each, the other unit's line
  (`core.U_sub`) in `t-mono-s`; four across on a phone, all six from 760 px; a 1 px ink rule under the strip; the
  stats note under it in sans 13 px ink-2 (its sentences unchanged).
- **Maps** (`core.map_block`, `core.py:741`; `base.css:405`): the renders unchanged; the frame edge to edge on a phone
  and with a 1 px `--rule` from 560 px; the key row in sans 12–13 px ink-2 with the same symbols; the caption in sans
  13 px ink-2 (`core.map_caption`'s wording, with `Not for navigation` as its last item); the credit tag as today.
  Cluster markers, pins, the linked lines, the full-screen link and `#route-start` behave exactly as documented.
- **Charts** (`core.chart_block`, `core.py:881`): the profile's area in `--profile-fill`, the line 1.5 px in ink (not
  the route colour), grid lines in `--rule`, axis labels in mono 10–11 px ink-3, `VERTICAL SCALE ×N` as today; the
  crosshair readout (profile.js) in mono.
- **Photos and the viewer** (`base.css:576`, `:831`): no border, no radius; captions in sans 13 px ink-2; the viewer's
  scrim `#111111` at 96%, its controls white, its behaviour untouched.
- **Report table, pager, tabs, copy control** (`base.css:670-830`): mono cells and uppercase sans heads with 1 px
  rules; pager titles in serif 26 px with a `t-mono-s` line; the scrollable tab rows as underline tabs (2 px ink bar
  under the current one, the 3 px route-red bars of Datum go to ink); the copy-link pop-up white with a 1 px ink
  border.
- **Bottom bar** (reports, phones; `report.bottom_bar`, `report.py:379`): white, a 1 px `--rule` above, four items with
  a 20 px stroke icon over a sans 500 10 px uppercase label (the one-row form under 500 px of height stays).
- **Crumbs** (`core.crumbs`, `core.py:2222`): sans 500 11–12 px uppercase 0.12em ink-2 with `/` between items; white
  on a hero photo; the hit areas as documented (a11y, Phase 4).
- **Day bar, month bar, filter band, section segments**: underline tabs in mono 12 px uppercase; sticky rules unchanged.

### 2.6 Page by page

**Home** (`tools/sitegen/pages/home.py`; `assets/css/pages/home.css`). From the top:

1. The hero: the cover of the first slug of `content/home.json` (`site['featured'][0]`; today the PCT journal), full
   width, min-height 720 px on desktop and 500 px on a phone, the focal point respected, `--scrim` over its lower
   part, and on it: a `t-mono-s` overline `FEATURED · <ACTIVITY> · <DATE>` (the journal: its date range; a goal is
   never featured), the trip's title in `t-d1` (the site statement moves below), a sans 18 px line with the place and
   region and, in mono 14 px, the trip's stats through `core.U` (none for a series without a facts line), and the
   destination link with its one verb (`Read the report`, `Open the journal`, `View the trip`). The home page's `<h1>`
   stays the site's own heading: keep it as a visually hidden `<h1>` ("Eric Sichak: trip reports…", the text the page
   has today) or make the statement the `<h1>` and the hero title an `<h2>`; decide by what keeps the heading order
   and the BreadcrumbList rules, and say which in the log.
2. The statement, centred, max-width 18ch: the lede the page has today ("Trip reports from the Sierra, the Alps and
   beyond.") in `t-d2`, the sentence under it in `t-dek`, and after it one computed sentence: `167 reports since
   2021.` from `len(site['published'])` and the earliest `date` (nothing typed).
3. "By the numbers" (Eric's request of 2026-10-25: the counts of the other concepts, in this concept's manner), in
   place of the by-activity tiles (`by_activity`, `home.py:217`). Under a `t-h2` head with the ink rule and a
   `t-mono-s` line (`2021 – 2026 · COUNTED FROM THE PUBLISHED REPORTS`, the years computed), a row of six figures,
   each a serif number (64 px on desktop, 44 on a phone, line-height 0.9) over a `t-label`, with a 1 px `--rule`
   under each cell: the number of published reports (a link to `trips/`), then one figure per activity in
   descending order of count (ties in `core.NAV` order), each with its disc and word and linking to its section page.
   Under the figures, "Reports by year": one thin ink bar per year from the earliest `date` to the latest, its height
   proportional to that year's count (the tallest 96 px), the count above it and the year under it in mono 12 px, the
   current year's label in ink and the others in ink-2; beside the bars a `t-label` "Reports by year" and one sentence
   only when a series is among the published trips, built from its facts (`2024 is the Pacific Crest Trail: one
   journal, Mexico to Canada, counted once.`: title, place and start year from the series' front matter). A series or
   a multi-day trip counts once, in the year of its `date`. Every number on the band is computed from
   `site['published']` at build time; the band needs no script, and the bars are plain blocks with the count as
   text, so a screen reader hears each year's count once.
4. The rest of the features (`site['featured'][1:]`): the second in a 3:2 photo taking two thirds of the row, the third
   and fourth stacked in the last third, a fifth and sixth as a row of two; each with a `t-mono-s` overline
   (`02 · HIKING · SEP 20, 2026`), the serif title (`t-h3`, 40 px for the large one on desktop), the place line and
   the `card_summary` or the computed opening as today (`core.card_summary`), nothing invented. With one featured trip
   only, the section is absent.
5. "Recent written reports": the newest six published trips for which `core.written_report(t)` is true, as list rows
   with thumbnails and right-aligned stats; the section head carries `All 167 reports →` to `trips/` (the count
   computed). Then, under it, "Recent recordings": the newest six track-only trips as `.trow--brief` rows (decision
   6), so that a visitor who finds the latest ride on today's home still finds it.
6. "Where I've been" (`where`, `home.py:279`): the one or two region maps `home.json` names (`resolve_region_maps`),
   each a plate with the render, the region's name in serif 30 px and its count in `t-mono-s` (`86 REPORTS`), linking
   to the region page; the clusters and the one-line key keep their behaviour; the `Also` line (`also_items`) under
   them in sans 14 px ink-2 with the other regions and their counts. The `Open the map →` link to `map/`.
7. The footer.

**Single-day reports** (`tools/sitegen/pages/report.py`; `assets/css/pages/report.css`), the four cases (story, written
first, photo-only, compact) in the order of sections they have today:

- The head: when `report.lead_photo` gives a photo at least 6:5 wide (the existing lead rule), a full-width hero
  (desktop: 72vh, at most 820 px; phone: 500 px) with the scrim and, on it, the crumbs, the title in `t-d1`, and the
  sans line `January 17, 2026 · Sawtooth Ridge, Eastern Sierra · with Adam` (the party from `party`, the date through
  the existing formatter); otherwise the title block on white (`title_block`, `report.py:165`) with the same parts. A
  goal page never gets a hero. The activity chip and the route-shape tag under the title; the actions (`Download GPX`
  filled, `Open the map` ghost, `Read the report` / `View route` as today) in one row.
- The stats strip, the note under it.
- The write-up (`.prose`): its first paragraph in `t-lede` (decision 2), the rest in `t-body`; headings inside it in
  serif 28 px; the text byte for byte what `markdown.to_html(t['body_md'])` gives (the lead is a class on the first
  `<p>`, never a change to the text).
- The map section (phone: edge to edge; from 560 px: in the column with the key row and the caption beneath), the
  profile, the beta `dl` (a 110 px label column in `t-label`, values in sans 16 px, 1 px rules), the gallery
  (two columns on a phone, each photo in its own shape, captions under), `More like this` as two 4:5 photo cards with
  serif 22 px titles and a `t-mono-s` line, the pager, the bottom bar. The photo-only and compact cases keep their
  shorter order; the empty-map box and the `Track only` wording stay.
- The full-screen map page (`report.fullscreen_page`): the bar in sans 12 px uppercase on white; the map untouched.

**Multi-day trips** (`multiday.py`, `multiday.css`): the overview head as a report's (a hero when the lead photo is
≥ 6:5), the day bar as underline tabs, each day's title in `t-h2` with its Mono-S line, day maps as on reports, the
chapter rail with serif numbers; the `Download all GPX` rule unchanged.

**The PCT journal** (`series.py`, `series.css`): the lead photo hero, the facts-only introduction in `t-dek`, the
highlights as the home's feature grid, the month bar as underline tabs, the day rows as list rows (serif 26 px titles,
`TRACK ONLY` and `DAYS N · NO RECORDING` in `t-mono-s`), the write-ups toggle unchanged.

**The Trips explorer** (`trips.py`, `trips.css`): "Trips" in `t-d1`, the search box bare with a bottom rule, the
filter chips square, the sort and view controls as underline tabs, year heads in `t-h2` with the ink rule, cards and
rows as in 2.5; the status row and the active-filter chips in `t-mono-s`; URL state, history and `search.json`
untouched.

**Section pages** (`section.py`, `section.css`): the head in `t-d2` with the intro the page has today, the Featured
block as a two-thirds photo card beside the one-third map panel, the filter band as underline tabs, the lists as rows
with the stat labels row.

**Region pages and map/** (`region.py`, `archive.py`, `region.css`, `archive.css`): the head in `t-d2` with the counts
line in `t-mono-s`; the sticky map column with a 1 px `--rule`; the legend discs; the table in mono; the Featured row
as 3:2 cards.

**Tick list** (`ticklist.py`, `ticklist.css`): map-led goal cards with serif titles and square status chips; the empty
wording unchanged.

**About** (`about.py`, `about.css`): `t-d1`, Eric's words in `t-body`, the photo 4:5 without a border, `At a glance`
as `.dl-leader` with mono values, the units section and its no-script rule unchanged.

**404** (`notfound.py`, `notfound.css`): serif heading, the search box, the suggestions as rows.

**Print** (`assets/css/print.css`): unchanged apart from the families; check the preview once in Phase 19.

### 2.7 What does not change

`content/`, `rendered/`, the build and its checks, every URL and anchor, the search indexes, the feed, the sitemap, the
JSON-LD, the meta tags and the share images, the scripts' behaviour, the no-JavaScript paths, the sticky-parts table,
the accessibility rules and the Lighthouse scores (100 on the report; the home's accessibility as it stands after
Phase 13C), the copy rules and every existing wording, the privacy rules, the photo sizes and `sizes` strings, the
units switch and its km default.

## 3. Decisions for Eric

Defaults stand when you say nothing. Answer in the first message of the phase that needs the decision.

1. **The home hero** (Phase 17). Default: the cover of the first slug in `content/home.json`, today the PCT journal's
   `d059-01.webp`. To put the Matterhorn couloir there as the mock-up does, move `matterhorn-peak-west-couloir` to the
   front of `featured_slugs` (a content edit you make yourself, staged with the phase or published on its own).
2. **The lead paragraph** (Phase 18). Default: the first paragraph of every write-up is set in `t-lede` (serif, 26–32
   px), the text unchanged. Alternative: no lead; the whole write-up in `t-body`.
3. **The route colour** (Phase 16). Default: keep `#D2381A`, because the maps' own label red (`ROUTE_INK #B8300F`,
   drawn into the committed renders) was chosen against it. Alternative: the mock-up's `#C8431A`.
4. **Self-hosted fonts** (Phase 16). Default: yes, `python3 tools/fonts.py` runs once in the Phase 16 session when you
   say go (the internet; about 150 KB of woff2 and three licence texts into `assets/fonts/`). Until then the pages
   load Google's stylesheet, as they do today when `fonts.css` is absent.
5. **By the numbers on home** (Phase 17). Your request of 2026-10-25: the counts from the other concepts join this
   home as one band (section 2.6, item 3), which also replaces the by-activity tiles. Default: the six figures and
   the year bars. Alternative: the six figures only.
6. **Recent recordings on home** (Phase 17). Default: keep the newest six track-only trips as brief rows under the
   written reports. Alternative: drop them (they stay on `trips/`).
7. **The name in the header**: sans 600 15 px, no tagline (your choice of 2026-10-25); the serif name appears in the
   footer only. Not a decision, a rule.

## 4. Phases

### Phase 16 - Foundations: tokens, type, fonts, header, footer and the shared components

Branch `redesign-16-foundations`. Files: `assets/css/base.css` (tokens, type, layout, header, footer, chips, cards,
buttons, maps and charts, data strip, photos, list rows, report table, pager, tabs, viewer, forced colours),
`tools/sitegen/core.py` (`FONTS`, `FONT_PRELOADS`, `header`, `footer`, `trip_card`, `trip_row`, `map_block`,
`chart_block`, `key_row`, `crumbs`: classes and markup only where the look needs a new hook), `tools/fonts.py`
(`FACES`, `LICENSES`, the docstring), `tools/lib/mapkit.py:31`, `tools/build.py:91`, `docs/DEVELOPING.md` (the Design
section rewritten as "Design: Alpine" from section 2 of this file, the type-class table, the layout line, and every
later mention of Datum's values: `.prose` 620 px, radii, the route-red hover rule), `tests/test_metadata.py`,
`tests/test_phase11.py`, `tests/test_phase14.py` (the pinned families and preloads), and whatever test the suite shows
pins a Datum value.

Prompt:

```
PHASE 16: FOUNDATIONS.

Goal: replace Datum's tokens, type and shared components with Alpine's (section 2.2 to 2.5 of docs/redesign-c/PROMPT.md)
so that every page already wears the new design before the page phases rework their layouts. Change the look, not the
mechanics (standing rule 11).

1. Build HEAD into <scratch>/before before any edit, and capture the before views of the contact sheet (home, trips/,
   the Matterhorn report, a bare ride, the Haute Route, the PCT page, map/, the Eastern Sierra region page, the tick
   list, About, the ski section page, the 404) at 1440, 1024 and 390 px.
2. Tokens (2.2) and type (2.3): rewrite base.css lines 4 to 95 against the two tables, keeping every token and class
   name. Replace core.FONTS with the three families' css2 address; rewrite tools/fonts.py FACES and LICENSES for the
   four faces and their OFL texts; set core.FONT_PRELOADS to the serif roman and Inter; change mapkit.SANS to the new
   sans stack and make tools/build.py:91 replace both the old and the new stack with var(--sans). Run python3
   tools/fonts.py --check to see that it reads the new table; run python3 tools/fonts.py itself only when Eric says go
   in this session (decision 4), and commit assets/fonts/ and assets/css/fonts.css with the phase when it has run.
3. Components (2.4, 2.5): header and footer (core.py:2339, :2428 and base.css:168-326), the units tabs, the menu, the
   buttons, chips, tags and filter chips, cards, list rows, the stats strip, the map frame, key rows and captions, the
   charts, photos and the viewer, the report table, the pager, the tab rows, the copy control, the bottom bar, the
   crumbs. Radii to 0 everywhere; fills and borders off; rules on. Keep every id, class a script reads, ARIA attribute
   and data attribute; keep the no-script header and its :where(html:not(.js)) twins, the sticky rules and their
   releases, the forced-colours and prefers-contrast blocks (with the new values).
4. Contrast: list every text colour against every background it sits on (white, --surface, --sunk, the scrim's darkest
   stop, the activity colours where text sits on them) with the ratio; every pair at or above 4.5:1 (3:1 from 24 px).
   Phone text at 12/16 px or more wherever docs/DEVELOPING.md requires it today; name each place still at 11 px.
5. docs/DEVELOPING.md: replace "Design: Datum" (line 96) with "Design: Alpine" written from section 2.2 to 2.5, with
   the same level of detail the old section had (tokens, families, the type classes, radii, targets, the hover rule),
   and update every later line that quotes a Datum value (grep for F2F1EC, 16171A, D2381A, Archivo, Source Serif,
   Geist, 620px, 2px, 1248). Update base.css's opening comment.
6. Tests: run the suite on both Pythons with -W error; a test that pins an old value is updated to the new one, a test
   that pins a rule is made to pass. Run python3 tools/build.py --out <scratch>/after --link --check, then the after
   views of the contact sheet at the three widths, paired with the before views on one HTML page under
   .cache/redesign/16/. Look at every pair before writing the report.
7. Commit on the branch: 'Phase 16: Foundations of the Alpine design'. The log entry per standing rule 12, with the
   contrast table, the text sizes still at 11 px, and the fonts' status (fetched or still Google's stylesheet).
```

Gate: both Pythons pass with `-W error`; `build.py --check` passes; every page of the before build exists in the after
build with the same URLs, ids and anchors; the contrast table has no pair under 4.5:1; the no-script header, the
sticky table and the forced-colours block are tested as before; the contact sheet shows every page in the new type and
colours with nothing clipped, overlapping or unreadable at 390 px.

### Phase 17 - Home

Branch `redesign-17-home`. Files: `tools/sitegen/pages/home.py`, `assets/css/pages/home.css`, `tools/sitegen/core.py`
(`cover_img` or `cover_preload` only if the hero needs a new size string), the home tests (`tests/test_home*.py`,
`tests/test_a11y_static.py`'s home checks, `tests/test_phase13*.py` where they read the home), `docs/CONTENT_GUIDE.md`
(how the featured list places trips now: first slug = hero, then the grid), `README.md` ("Feature a trip on the home
page").

Prompt:

```
PHASE 17: THE HOME PAGE.

Goal: rebuild the home page to section 2.6 ("Home") of docs/redesign-c/PROMPT.md, with decisions 1, 5 and 6 of section 3
as Eric answered them or by their defaults, on the foundations of Phase 16. Facts only from content; every count
computed; nothing a visitor finds on today's home disappears (the featured trips, the recent outings, the activities,
the region maps and their clusters, the Also line, the feed link).

1. Before: build HEAD into <scratch>/before and capture the home at 1440, 1024 and 390 px, and with JavaScript off.
2. The hero from site['featured'][0]: the cover through core.cover_img with a sizes string that serves the 1600 px file
   from 760 px and the 800 px copy below (core.phone_sizes decides the portrait case), its preload through
   core.cover_preload, object-position from the focal point, the scrim, the overline, the title, the place-and-stats
   line through core.U and core.caps_unit, the destination link with its one verb. Settle the heading order (the
   page's <h1>) and say which you chose in the log. A series shows its date range and no stats line; a trip without a
   cover never reaches the hero: fall back to the title block on white and warn in the validator's notes.
3. The statement, the computed sentence, the By-the-numbers band (decision 5: the six figures as links to trips/ and
   the five section pages, the year bars, the series sentence, all computed), the feature grid for site['featured'][1:], the
   written-reports list (core.written_report) with the computed 'All N reports' link, the recent recordings as brief
   rows (decision 6), Where I've been with the region plates, their counts, the Also line and the key, the footer.
   Repeated titles among the cards and rows get the short date in their link name as today (core.repeated_titles).
4. Keep: the cluster hover and pointer rules for a map without a list (aria-hidden markers, never Tab stops), the home
   region name's 44 px box, the Also links' hit areas, the feed and the contact lines.
5. Tests, both Pythons; build --check; the contact sheet (home at the three widths, with JavaScript off, and in forced
   colours) under .cache/redesign/17/; Lighthouse on the built home served under /personal-website/ (accessibility,
   best practices, SEO; the target is today's scores or better).
6. Commit 'Phase 17: Home'. Log entry; list the interface copy you added (section heads, the computed sentence's
   wording) for Eric to read.
```

Gate: the home shows the same trips and regions as today's home (list them beside each other in the log); the hero's
photo is the first featured slug's cover; every count on the page equals the build's; Lighthouse on the home is at or
above today's three scores; the no-script and forced-colours views are usable; both Pythons and `--check` pass.

### Phase 18 - Reports, goals, the full-screen map and multi-day trips

Branch `redesign-18-reports`. Files: `tools/sitegen/pages/report.py`, `assets/css/pages/report.css`,
`tools/sitegen/pages/multiday.py`, `assets/css/pages/multiday.css`, `tools/sitegen/core.py` (`map_block` and
`chart_block` only where the frame or caption needs a hook), `assets/js/pages/profile.js` (styling hooks only, if the
readout's colours live there), `tests/test_report_page.py`, `tests/test_report_phase10.py`, `tests/test_phase13c.py`,
the multi-day tests (`grep -l multiday tests/*.py` names them), `tests/test_a11y_static.py` where it reads report
fixtures.

Prompt:

```
PHASE 18: REPORT PAGES.

Goal: rebuild the single-day report (its four cases), the goal page, the full-screen map page and the multi-day pages
to section 2.6 of docs/redesign-c/PROMPT.md, with decision 2 (the lead paragraph) as answered or by default. Write-ups
byte for byte; every section, anchor, control and download the pages offer today, still offered, in the same order.

1. Before: build HEAD into <scratch>/before; capture the Matterhorn report (story case, landscape cover), a report with
   a portrait cover, a track-only report (compact case), a written-first report, a photo-only report, the Crystal Range
   goal, a full-screen map page, the Haute Route overview and one of its days, at 1440, 1024 and 390 px; and the
   print preview of the Matterhorn report.
2. The head: the hero when report.lead_photo is at least 6:5 wide, the title block otherwise; the crumbs, the title
   (t-d1 or t-d1--long by the 28-character rule), the date-place-party line, the chip and tag, the actions row. A goal
   page keeps its title block and its planned caption. The <h1> stays the title alone; page_title and the BlogPosting
   headline unchanged.
3. The stats strip and its note; the write-up with the first paragraph in t-lede (a class on the first <p> that
   markdown.to_html emits, added after conversion, never by editing the Markdown; the extracted .prose text of every
   trip page must be identical before and after); the map section edge to edge on a phone; the profile with the ink
   line and the readout; the beta list; the gallery; More like this as 4:5 cards; the pager; the bottom bar; the
   empty-map box and the no-track rules exactly as documented (no file, no control).
4. Multi-day: the overview head, the day bar as underline tabs (sticky rules unchanged), the day sections, the rail,
   the day maps and their captions, the combined GPX rule. The journal (series) waits for Phase 19.
5. Compare: extract the .prose text, the H1, the JSON-LD and the list of ids and anchors of every trip page in the
   before and after builds; they must be identical (the lead class is the only new attribute). Put the counts in the
   log.
6. Tests, both Pythons; build --check; the contact sheet under .cache/redesign/18/ with the pairs from step 1 and the
   print preview; Lighthouse on the Matterhorn report (100 / 100 / 100 expected); a VoiceOver or screen-reader pass of
   the report's stats strip and key rows per docs/CHECKING_WITH_A_SCREEN_READER.md if the session can drive one, else
   the static test of tests/test_phase13c.py as the proxy.
7. Commit 'Phase 18: Report pages'. Log entry.
```

Gate: every write-up, H1, JSON-LD block, id and anchor identical between the two builds; the four cases, the goal page
and the full-screen page render from the fixtures in the tests; Lighthouse 100 / 100 / 100 on the Matterhorn report;
the print preview shows the report, its map and chart without the chrome; both Pythons and `--check` pass.

### Phase 19 - Lists and the rest

Branch `redesign-19-lists`. Files: `tools/sitegen/pages/trips.py` and `assets/css/pages/trips.css`, `section.py` and
`section.css`, `region.py` and `region.css`, `archive.py` and `archive.css`, `ticklist.py` and `ticklist.css`,
`series.py` and `series.css`, `about.py` and `about.css`, `notfound.py` and `notfound.css`, `assets/css/print.css`,
their tests (`tests/test_section_page.py`, `tests/test_about_page.py`, `tests/test_site_map_prune.py`,
`tests/test_phase11.py`, `tests/test_phase12.py`, `tests/test_phase14.py`, the explorer and tick-list Node harnesses'
fixtures if they read class names).

Prompt:

```
PHASE 19: THE LISTS AND THE REST.

Goal: bring the Trips explorer, the section pages, the region pages, map/, the tick list, the PCT journal, About, the
404 and the print sheet to section 2.6 of docs/redesign-c/PROMPT.md. The scripts' behaviour is untouched: URL state,
history, search, the filters, the sort, the view switch, the cluster selection, the legend toggles, the month scrollspy,
the write-ups toggle and the day reveal all replay as today.

1. Before: build HEAD into <scratch>/before; capture trips/ (cards and list, with a search and a filter), the ski
   section page, the Eastern Sierra region page, map/ (with a region tab and the table), the tick list, the PCT page
   (with the month bar stuck), About and the 404 at 1440, 1024 and 390 px.
2. Each page to its paragraph in 2.6, with the shared components of Phase 16: heads in serif, underline tabs, square
   chips, rows and cards, the stat labels row, the sticky columns with their rule, the region plates, the goal cards,
   About's leader list, the 404's search box. The print sheet: the families follow; check the preview.
3. Replays in Chrome at 1440, 1024 and 390 px with real key presses, clicks and touch: the explorer (search, facets,
   sorts, the Filters button on a phone, the zero-result buttons, Back and Forward), the header search from a report,
   the 404 search, the tick list's filters, the journal (month tabs, write-ups filter, Continue reading, Back after a
   reveal), the cluster selection and legend toggles on map/, the coarse-pointer taps on a region page, the units
   switch. No console errors.
4. Tests, both Pythons; the Node harnesses; build --check; the contact sheet under .cache/redesign/19/; Lighthouse on
   trips/, map/, a region page and the PCT page (today's scores or better).
5. Commit 'Phase 19: Lists and the rest'. Log entry; the interface copy you touched, for Eric.
```

Gate: every replay in step 3 behaves as today with no console error; every list shows the same trips in the same order
as the before build; the tab stops and radio groups are unchanged (the static a11y tests pass); Lighthouse at or above
today's scores on the four pages; both Pythons and `--check` pass.

### Phase 20 - Review gate and publication

Run the prompt "Review gate before each publication" from `docs/claude-code-website-prompt-2.md` (from line 1438) as
written, on the branches of Phases 16 to 19 in order, with these additions:

- In step 1, besides the GPX files and the write-ups, compare the visible text of every page between the public build
  and the new build (the text of `<main>` with whitespace folded): the only differences allowed are the interface copy
  the four log entries list, the computed sentences, and the moved site statement. Name every other difference.
- In step 3, the inventory of what a push makes public adds: the four new font files and their three licence texts
  (if fonts.py ran), the rewritten Design section of docs/DEVELOPING.md, this folder (`docs/redesign-c/`, whose
  reference pages name only trips the site already publishes), and the new home order if Eric changed
  `content/home.json`.
- The contact sheets of the four phases are linked from the gate's review page.
- Lighthouse as the gate says: 100 on the Matterhorn report, and no page lower than today's scores.

The push happens only on Eric's word in that session, as the gate prompt says.

## 5. Reading the reference mock-ups

`reference/home-1280.html` and `reference/report-phone-390.html` are the two canvas artboards saved as plain HTML: the
fonts come from Google's stylesheet, the photos and maps from the live site, the route and the profile are the
committed render's own paths drawn inline, and the header's name is already the sans 15 px form Eric asked for. Open
them in a browser to see the intent at any width (the home is fluid; the phone page is a fixed 390 px column). What
they are not: they have no `srcset`, no `core.U` (the numbers are typed in miles and feet), no km lines, no visually
hidden text, no key-row symbols from the renders, no script, and their layouts are hand-laid for one trip; the pages
must come from the generator and its rules. Where a value is needed that section 2 does not state (a gap, a size, a
weight), read it from the mock-up's inline styles.
