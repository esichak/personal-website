# Content guide: homepage features, covers, summaries, search, report pages and the PCT journal

How to choose what the homepage shows, which photo fronts a trip's card and leads its report, what the card says, what
the Trips page finds when someone searches, and which entries the PCT journal points to. All of it is done by editing
two kinds of file (`content/home.json` and a trip's `index.md`) and running two commands. No Python edit is needed to
feature, reorder or re-cover a trip, or to list PCT highlights.

Adding a trip is in [ADDING-TRIPS.md](../ADDING-TRIPS.md); how the generator works is in
[DEVELOPING.md](DEVELOPING.md).

## 1. The homepage list: `content/home.json`

```json
{"featured_slugs": ["pacific-crest-trail-2024", "matterhorn-peak-west-couloir", "peak-bagging-szn"]}
```

- A slug is the trip's folder name under `content/trips/` (also the end of its URL, `…/trips/peak-bagging-szn/`).
- Order is display order. The first slug is the lead card; the rest are supporting cards.
- Zero to six slugs. `{"featured_slugs": []}` hides the featured section; the build never swaps in another trip.
- This file alone picks the homepage. `featured: true` in a trip's front matter still drives the Featured block
  on that trip's section page (Climb, Hike, MTB, Other; the Ski page has no Featured block; single-day trips only, so
  the flag on a multi-day trip or the PCT does nothing), but it no longer has any say over the homepage.
- If the file is missing, the build prints a warning naming `content/home.json` and falls back to the old pick
  (the newest published trip flagged `featured: true`, else the newest published trip). Keep the file in place.

A wrong manifest never falls back to a different trip. A typo, a draft, a planned route or a seventh slug stops
the build with a message naming the file and the slug (table in section 5).

## 2. Feature, reorder, remove

**Feature a trip**

1. Find the slug: `ls content/trips/`.
2. Add it to `featured_slugs` where you want it. A new lead goes first.
3. Preview and check (section 5), then publish:

```bash
git add content/home.json && git commit -m "Feature Peak Bagging SZN" && git push
```

**Reorder:** move the slugs around in the array. Nothing else changes.

**Remove:** delete the slug from the array. The trip stays on its section page, on the Trips page and in Recent
outings if it is recent enough; only the homepage feature goes.

**What the homepage shows**

- One card per slug, in order. With the three slugs above: a lead card for the PCT and two supporting cards.
  The section renders cleanly with 0, 1, 2, 3 or 6 cards.
- Each card: the cover (section 3), the trip's original title as the link, an activity or "Journal" label, the
  date and place, a couple of stats, the summary (section 4), and a link: "Explore the journal" for the PCT,
  "Read the report" for a trip with a write-up, "View trip" for a track-only trip.
- The lead card's cover is also the page's share image.
- "Recent outings" below the features lists the six newest published trips that are *not* in `featured_slugs`,
  so a featured trip never shows twice. Planned routes never appear there. Adding a new trip never bumps a
  feature off the homepage; only the list does.

## 3. Covers

Three optional lines in a trip's `index.md`, among the front-matter lines above the closing `---`:

```yaml
cover_photo: photos/01.webp
cover_focal_x: 50
cover_focal_y: 45
```

`cover_photo` is a path relative to the trip folder, and it must be a photo already declared under `photos:` in
that trip's `index.md` or in one of its `days/NN.md`. The card reuses that entry's `w`, `h`, `alt` and the
`.sm.webp` copy, so nothing else is declared. A day photo works too (`cover_photo: photos/d001-03.webp` on the
PCT), but these lines always go in `index.md`, even when they name a day photo: the same keys in a `days/NN.md`
are ignored. Paths with `..`, a leading `/` or a backslash are rejected, and so is a declared photo whose file is
missing. A bare `cover_photo:` with nothing after it counts as absent. Drafts are checked like every other trip, so
a draft with a broken cover stops the build too.

`cover_focal_x` / `cover_focal_y` say where the image is anchored when the card crops it. Plain numbers from 0 to
100, no quotes, no `%`: `0` / `0` keeps the top-left corner, `50` / `50` the centre (the default), `100` / `100`
the bottom-right. Each is optional; a missing one is 50. Set them after looking at the card at phone width and
desktop width in the preview: the two crops differ, and a summit near the top of a portrait photo usually wants
`cover_focal_y` well under 50.

Without `cover_photo` the build picks, in order:

1. the first photo declared in `index.md` that is at least 6:5 wide (width ≥ 1.2 × height);
2. else the first photo declared in `index.md` that is at least as wide as tall (width ≥ height);
3. else the first photo declared in `index.md`;
4. else, for multi-day trips and series, the same three steps over the day photos (days in order): the first day photo
   at least 6:5 wide, else the first at least as wide as tall, else the first photo of the first day that has photos;
5. else the route tile;
6. else a plain card with no image.

An automatic pick is a fallback, not an editorial choice: it is simply the first file that fits. For anything on
the homepage, look at the photos and set `cover_photo`.

The same three lines also choose the lead photo of the trip's report page and of the PCT page, when the cover is at
least 6:5 wide, and the share image of the trip's page (section 7.3).

## 4. Summaries

`card_summary` is the short text on a trip's card. One or two factual sentences, written from the report or
checked against it: what the trip was, not how it felt. It never changes the report body, which is still
rendered word for word.

```yaml
card_summary: "One or two sentences that say what the trip was, taken from the report."
```

That line is a placeholder for the syntax, not copy to publish. Plain text needs no quotes (colons and apostrophes
inside it are fine). Wrap it in double quotes when it starts with a quote mark or `[`, or is nothing but digits,
`true`, `false`, `null` or `~`; escape an inner double quote as `\"`. The text is shown exactly as written and never shortened, so keep it to a sentence or two (the automatic
excerpt on a homepage card gets about 230 characters).

Without `card_summary` the card shows:

- **a trip with a write-up:** the opening of the report, as plain text, cut at about 230 characters;
- **the PCT (a series):** no sentence. The card's data lines carry the facts instead (`APR 22 – SEP 21, 2024 ·
  MEXICO TO CANADA` and `150 RECORDED DAYS · 3,167 MI RECORDED`, counted from the days that have a track). Never a
  day's prose: the first day's story is not the story of the trail;
- **a multi-day trip** with at least one written day: a labelled excerpt from that day, with the label (for
  example `DAY 2 · <day title>`) shown above it; with no written day, no sentence (the date range and the stats
  say what it was);
- **a single-day trip with no write-up:** nothing, and the link reads "View trip".

## 5. Preview and checks

```bash
python3 tools/build.py --serve              # build, then open http://localhost:8000 (Ctrl+C to stop)
python3 tools/build.py --check              # full build plus every link, image and anchor
python3 -m unittest discover -s tests       # the generator's tests
```

Run all three before pushing. A bad `home.json` or a bad front-matter field stops the build with one line on
stderr and `--check` exits 1. GitHub runs the same check on every push, so a broken file fails the deploy instead
of publishing a broken homepage; the site simply does not update until it is fixed.

| Message starts with | What it says | Fix |
| --- | --- | --- |
| `content/home.json: …` | malformed JSON, or the file is not a JSON object | Compare with the one-line example in section 1: double quotes, square brackets, commas between slugs, no trailing comma. |
| `content/home.json: …` | `featured_slugs` is missing | Add the key: `{"featured_slugs": [...]}`. |
| `content/home.json: …` | `featured_slugs` is not a list | Wrap the slugs in `[ ]`, even for one slug. |
| `content/home.json: …` | an entry is not text, or is empty | Every entry is a quoted slug; delete `""`. |
| `content/home.json: …` | a slug is listed twice (named) | Remove the repeat. |
| `content/home.json: unknown slug '…' in featured_slugs` | no such folder in `content/trips/` | Check the spelling against `ls content/trips/`. |
| `content/home.json: …` | the slug is a draft (named) | Remove `draft: true` from that trip's `index.md`, or take it out of the list. |
| `content/home.json: …` | the slug is a planned route (named) | Planned routes cannot be featured; take it out of the list. |
| `content/home.json: …` | more than six slugs | Cut the list to six or fewer. |
| `content/trips/<slug>/index.md: …` | `cover_photo` is not declared, its file is missing, or the path escapes the folder (path named) | Use the exact `file:` value of a photo under `photos:` in `index.md` or a `days/NN.md`, make sure the file exists in `photos/`, and drop any `..` or leading `/`. |
| `content/trips/<slug>/index.md: …` | `cover_focal_x` / `cover_focal_y` is out of range or not a number | Plain number from 0 to 100: `cover_focal_y: 45`, not `"45%"` or `true`. |
| `content/trips/<slug>/index.md: …` | `card_summary` is not text | Quote it: `card_summary: "…"`. A bare number, `true`, or a `[list]` parses as something other than text. |
| `content/trips/<slug>/index.md: journal_highlights must be a list …` | the value is not a list (value shown) | Square brackets, even for one id: `journal_highlights: [059]`. |
| `content/trips/<slug>/index.md: journal_highlights names day …` | an id has no `days/NNN.md` (id shown as the parser read it, so `059` appears as `59`) | Use the day file's name, not the day number: Day 5.2 is `006`. `ls content/trips/<slug>/days` lists them. |
| `content/trips/<slug>/index.md: journal_highlights lists day … twice` | the same day is listed twice (`059` and `59` are the same day) | Remove the repeat. |
| `content/trips/<slug>/index.md: journal_highlights is for a journal …` | the list is on a trip that is not `kind: series` (its kind is shown) | Remove the line; only the PCT uses it. |

A `content/trips/<slug>/index.md: front matter: …` (or `…/days/NN.md: front matter: …`) message is a syntax
problem in that file's front matter: an unclosed `---`, or a value that starts with a double quote but is not one
complete quoted string.

## 6. Search and the Trips page

`/trips/` lists every published report by year, with a search box and filters (activity, region, year, format,
has a write-up, sort, cards or list). The filters work on what is already on the page. The search box looks in:

- the title;
- the place and the region;
- the activity ("backcountry ski", "hiking", "paddleboarding");
- the summits in `map: peaks:`;
- the write-up: the report body, and every day's write-up on a multi-day trip or the PCT (the first 4,000 characters
  or so);
- `search_aliases` (below).

Every word typed has to appear somewhere in those. Case, accents and punctuation do not matter: `chamonix zermatt`
finds `Chamonix – Zermatt`. An apostrophe counts as a word break, so `lover's leap` and `lover leap` find Lover's
Leap but `lovers` does not; if people type it that way, add `Lovers Leap` as an alias. Not searched: party, beta rows,
conditions, stats, photo captions. The search data is a public file, `trips/search.json`, built from exactly those
fields: no coordinates, no GPX, never a draft.

**Aliases.** When people would type a name that is not in the title or place (an abbreviation, an older name, a
trail's nickname), add one line to the trip's `index.md`, among the front-matter lines above the closing `---`:

```yaml
search_aliases: [PCT, Pacific Crest]
```

- Square brackets, items separated by commas. Plain text needs no quotes: `[Mt. Tallac, Chamonix – Zermatt]` is fine.
- Wrap an item in double quotes when it contains an apostrophe or a comma: `["Lover's Leap", Phantom Spires]`. An
  unquoted apostrophe makes the parser read on to the next one, so `[Lover's Leap, Phantom Spires]` becomes a single
  alias.
- Quote anything that is only digits: `["2024"]`. Bare digits read as a number, and a number stops the build.
- One alias can be written without brackets: `search_aliases: PCT`. A trailing comma (`[PCT, ]`) is ignored.
- The line goes in `index.md`, not in a `days/NN.md`. Leave it out when there are none.
- Aliases are only searched, never shown on any page.
- The title, place, region and `map: peaks:` are already searched, so there is no need to repeat them.
- A value that is not text or a list of text stops the build with a `content/trips/<slug>/index.md: …` message, like the
  other fields in section 5.

When a search matches only in the write-up, the card shows the words around the first hit instead of its opening
(and a day excerpt's DAY label is hidden); clearing the search restores the card. A region appears as a link in the
browse block to its map panel once the map page has one; until then (the PCT) it links to the Trips page's own filter.

**Journal days.** A search also reads the days of the PCT journal on their own, every one of them. The days it finds
are listed under "Journal days", after the reports, and the count line above the results
gains a link to that list (`3 OF 167 REPORTS · 11 JOURNAL DAYS` for `tent` today). Each row gives the journal's name,
the day and its date (`PACIFIC CREST TRAIL 2024 · DAY 31 · MAY 22, 2024`), the day's title ("Day 31" when it has none)
and, for a written day, the words around the match (the day's opening words when the match is in its title or its
name), shown whole. The link opens that day on the journal's page; a day never becomes a page or a report of its own.

- A day is matched on its own title and write-up: every word typed has to be in one or the other. A titled day without
  a write-up is found by its title: `whitney` finds Day 48, "Mount Whitney".
- A day can also be named: `day 31` puts Day 31 first. Any other words typed with the name still have to be in that
  day's title or write-up.
- The journal's name and aliases never find a day by themselves: `pacific crest trail` finds the journal among the
  reports and no day, and `pct` only the days whose own write-up says "PCT". They may be typed along with something
  of the day's own, as whole words: `pct whitney` and `pacific crest trail 2024 day 48` both find Day 48. The place
  and the date are not searched.
- Order: a day the query names comes first (`day 5.2` lists Day 5.2 above Day 5); after that a word found in the title
  counts for more than one found in the write-up, and equal days keep the journal's order.
- The first five days are shown, with "Show all N journal days" for the rest and "Show fewer journal days" to fold
  them again. A new search starts from five.
- The filters apply to a day exactly as they apply to its journal (Hiking, 2024, Series). "Has a write-up" also asks
  it of the day itself, so a track-only day is not listed while it is on.
- A day with neither a write-up nor a title is found only by its name: `day 100` finds Day 100.

Multi-day trips are different: they are searched as one report, and a match in a day's write-up shows that day's words
on the trip's card. The day data is a second public file, `trips/journal.json`: for each day of the journal, the
journal's name, aliases and folder name, the day's label, anchor, date and title, and its write-up as plain text. No
coordinates, no GPX, no photo names.

**Planned routes** are tick-list goals: they live on `/tick-list/` (and on the map and their activity page), never on the
Trips page or in its search. Adding, importing and updating them is a separate workflow: [TICK_LIST_GUIDE.md](TICK_LIST_GUIDE.md).

Preview with `python3 tools/build.py --serve` and open http://localhost:8000/trips/; type the alias into the search
box. The index is rebuilt on every build, so an alias needs no `render.py` run. Run the checks from section 5 and
commit the trip's `index.md` by path.

## 7. Report pages and the PCT journal

Report pages are built from the trip folder. Nothing in this section needs a new field except the PCT's optional
`journal_highlights` (7.8). What is new: a report with a write-up and a photo opens with the write-up, under its cover
photo when that photo is at least 6:5 wide; the cover lines from section 3 choose that photo; the map caption says
when the track was recorded; reports end with up to three related reports; and pages have a Copy link control.

### 7.1 Which layout a single-day report gets

| `index.md` has | Layout | The page leads with | Photos section |
| --- | --- | --- | --- |
| a write-up and photos, the cover at least 6:5 wide | story | the cover photo (7.3) | the other photos, in their order; left out when the cover is the only photo |
| a write-up and photos, the cover narrower than 6:5 (a portrait, a square or a near-square) | story, without a lead photo | the stats strip and the write-up | every photo, the cover among them |
| a write-up and one photo, a portrait | story, without a lead photo | the stats strip and the write-up; the portrait sits beside the write-up, as before | none |
| a write-up and no photos | compact | the map | none |
| photos and no write-up | compact | the map | every photo; a single portrait is shown on its own instead, as before |
| a track only | compact | the map | none |

The build decides from the trip folder. No field switches the layout: a trip gets the story layout when it has both a
write-up (text under the closing `---` of `index.md`) and at least one photo declared under `photos:`. Whether a story
opens with a lead photo depends only on the shape of its cover (7.3). Track-only, photo-only and no-photo reports keep
the compact page, and nothing is written or added to fill them out. Multi-day trips, the PCT and tick-list goals have
their own pages and do not use these two layouts.

Multi-day trips keep their map-first page in Phase 3. That is a decision: a multi-day page has no lead photo and no
row of section links, whatever its cover. It did gain Copy link (7.6), More like this (7.5), the "As recorded" caption
(7.4) and the cover as its share image (7.3).

### 7.2 The order of a story page

1. The title block. Its buttons are "View route" (jumps to the map), "Download GPX" and "Copy link" (7.6).
2. The lead photo, with its caption when the photo has one. A cover narrower than 6:5 does not lead (7.3), and the
   page then goes from the title block straight to the stats strip.
3. The stats strip.
4. A row of section links: Report, Photos, Route, Trip details. The row is always in that order, which is not the
   order of the page (the photos come after the route). Photos is listed only when the page has a Photos section. Trip
   details jumps to the Beta block when the trip has beta rows and to the stats strip when it has none. No link in the
   row is marked as the current section. The row is hidden on phones, where the bottom bar does the same job.
5. The write-up under "Trip report", word for word, with the Beta block beside it.
6. The map with its key and caption (7.4), then the elevation profile (the speed chart for flat water).
7. Photos: every photo except the lead.
8. On phones only, "Copy link to this page" (7.6).
9. More like this (7.5), then Newer / Older.

A compact page keeps its earlier order: the title block ("Read the report" when there is a write-up, "Download GPX",
"Copy link"), stats, map, profile, the write-up and Beta, photos, and then items 8 and 9 above.

On a phone a story page's bottom bar reads Report, Map, Photos, GPX. When the page has no Photos section it reads
Beta, Report, Map, GPX for a trip with beta rows, and Report, Map, Profile, GPX otherwise (Speed in place of Profile
for flat water, Stats when the trip has no chart). A compact page's bottom bar is unchanged. On both layouts the bar
marks the section being read, and an item the reader presses stays marked until the page scrolls on from there.

Nothing on either layout is written by the build. The write-up is rendered word for word and the lead photo is a
photo declared in the trip's `index.md`.

### 7.3 The lead photo

`cover_photo`, `cover_focal_x` and `cover_focal_y` (section 3) now choose three things: the photo on the trip's cards,
the lead photo of a story report page, and the lead photo of the PCT page. A cover leads a page only when it is at
least 6:5 wide (its width at least 1.2 times its height); see "Portraits and squares" below. Whether or not it leads,
the cover is the share image of the trip's own page: a single-day report on either layout, a multi-day trip and the
PCT.

- **Without `cover_photo` the automatic pick is the cover.** For a single-day report that is the first photo declared
  in `index.md` that is at least 6:5 wide, else the first that is at least as wide as tall, else the first photo. A
  square first photo therefore does not keep a later landscape from leading the page. It is the first file that fits,
  not a choice. On reports that matter, look at the photos and set `cover_photo`.
- **One focal point, several crops.** The lead photo's frame is 4:3 on screens under 560 px wide, 3:2 from 560 to
  1199 px and 2:1 from 1200 px, and the card crops differ again. All of them are anchored on `cover_focal_x` /
  `cover_focal_y`. Look at the report at phone width and at desktop width in the preview before settling on the numbers.
- **The lead photo is left out of the Photos grid.** The grid shows the other photos in their original order, and its
  heading counts only those: "6 PHOTOS" for a trip with seven. The lead photo and the grid open in the same viewer,
  which steps through all of the trip's photos, lead first, and counts them all: "PHOTO 1 / 7" on the lead.
- **A cover that is the only photo.** When that one photo is at least 6:5 wide, the page has a lead photo and no
  Photos section, and an older link to the page's `#photos` lands on the lead photo. A single portrait stays beside
  the write-up and the page has no lead photo (7.1). A single square or near-square photo does not lead either (one
  report today has a single 1600 × 1577 photo): it stays in the Photos section, which then holds that one photo.
- **Portraits and squares.** The lead frame is wide (4:3 to 2:1), and a portrait, a square or a near-square photo
  would lose much of itself to it. So a cover narrower than 6:5 does not lead the page: the report keeps the story
  order (stats, write-up, map) and every photo stays in the Photos section. That covers a trip with no photo at least
  6:5 wide, and a `cover_photo` that names a portrait or a near-square photo. The cover still fronts the trip's cards,
  so its focal point still matters there, and it is still the page's share image. To give such a report a lead photo,
  name a photo that is at least 6:5 wide in `cover_photo`, adding one to the trip if it has none.
- **Caption and alt text** come from the cover photo's own entry under `photos:`. A `caption:` is shown under the lead
  photo and in the viewer; without one the lead photo has no caption. The `alt:` text describes the photo to screen
  readers, as it does in the grid.
- **The PCT.** Its lead photo is whatever `cover_photo` names in `content/trips/pacific-crest-trail-2024/index.md`, as
  long as that photo is at least 6:5 wide. A portrait or a square named there would still front the PCT's cards and be
  its share image, and the page would open without a lead photo. Today the line names `photos/d059-01.webp` (1600 ×
  1200) with `cover_focal_x: 45` and `cover_focal_y: 55`. Those lines were added in Phase 1 so the homepage card had a
  picture, and the implementation log still lists them for confirmation: change them after looking at the day photos.
  On the PCT page the lead photo opens in the viewer on its own, and the same picture still appears in its day's
  entry.

A cover change needs a build, not a `render.py` run.

### 7.4 "As recorded on"

The caption under a report's map now starts with the date of the track:

- a single-day report: `As recorded on Jan 17, 2026 · full track, not trimmed · North up`
- a multi-day trip: `As recorded <date range> · full track, not trimmed · North up` (`As recorded on <date>` when
  every day shares one date)
- the PCT: `As recorded Apr 22 – Sep 21, 2024 · full tracks, not trimmed · North up`
- the featured map on an activity page (Climb, Hike, MTB, Other; the Ski page has no Featured block): it opens `As
  recorded on <date>` too, like the report it features

The date is the trip's `date:`. For a multi-day trip and the PCT it is `date:` to `end_date:`, or the first and last
day when those lines are absent. Nothing is set by hand. A trip with no date gets no such item, and its caption starts
with `full track, not trimmed`: a single-day trip with no `date:`, and a multi-day trip or a journal with no dates in
`index.md` or in its day files. The line is there so an old report reads as a record of that day and does not suggest
current conditions. A goal page keeps "Planned route, not a recorded track".

### 7.5 More like this

Single-day reports (both layouts) and multi-day trips end with "More like this": up to three cards above Newer /
Older. The rule, in one sentence: other published reports that share this trip's region and its activity come first,
then those that share only its region, then those that share only its activity, and within each of those groups the
report closest in date to this one comes first, the newer one on a tie.

There is nothing to configure.

- Never the report itself, a planned route or a draft, and no report twice. The two reports the page already links as
  Newer / Older are left out as well, so the block never repeats the links right under it. A multi-day trip or the PCT
  can be one of the cards.
- The line beside the heading states the rule: `SAME REGION, THEN ACTIVITY · NEAREST IN DATE`, or `SAME ACTIVITY ·
  NEAREST IN DATE` on a trip with no `region:`. When the page has a Newer or an Older report it ends `· NEWER / OLDER
  NOT REPEATED`, because the nearest reports in date are usually those two.
- The region match is on the exact text of `region:`, so spell a region the same way on every trip that belongs to it.
- A report without a date comes last in its group. When the trip itself has no date, each group is newest first.
- When nothing is left to show, the block is left out: no other report shares the region or the activity, or the only
  ones that do are the Newer / Older pair.
- The PCT page and goal pages have no such block.

### 7.6 Copy link

| Page | 760 px and wider | Phones (under 760 px) |
| --- | --- | --- |
| single-day report, both layouts | "Copy link", the last button in the title block | "Copy link to this page" near the end of the page, after the photos and above More like this (the title buttons are hidden on phones) |
| multi-day trip | "Copy link", the last button in the title block | "Copy link to this page" after the last day, above More like this (the title buttons are hidden on phones) |
| goal page | "Copy link", the last button in the title block | "Copy link to this page", above "Back to the tick list" |
| the PCT | "Copy link", the last button in the title block | the same button (the PCT keeps its title buttons on phones) |

On the PCT every written entry also ends with "Copy link to this entry", at every width (7.7).

- It copies the page's public address, `https://esichak.github.io/personal-website/trips/<slug>/`. The local preview
  copies that public address too, not the `localhost` one.
- When the copy works, "Link copied" appears just under the button for about four seconds. It hangs over the page, so
  no button, title or row moves. In the phone row ("Copy link to this page") it appears beside the button instead.
- When the browser has no clipboard access or refuses it, the address appears under the button in a small read-only
  field, already selected, to copy by hand. Escape, a second press of the button or a press anywhere else closes it.
- With scripting off the control is not shown, and neither is the phone row that holds only it: the button could do
  nothing there. The address bar holds the same address.
- On the PCT each entry's button reads "Copy link to this entry", and screen readers also hear the day ("Copy link to
  this entry, Day 3"), so every copy button on the page has its own name.
- There is no account, no share menu and no third-party script.

### 7.7 The PCT page

**Page order.** The title block, with its buttons under the title at every width, the lead photo when the cover can
lead (7.3), the stats strip, the Overview (map, introduction, month list), Highlights when any are listed (7.8), then
the day log under "Day by day".

**The two actions.**

- "Read the first written entry" jumps to the first day, in day-file order, that has a write-up (Day 1 today). It is
  left out when no day has a write-up.
- "Browse all recordings" jumps to the day log and switches the write-ups filter off, so every recorded day shows.

"Copy link" follows them (7.6). The earlier "Day by day" button is gone; the day log keeps that heading. There is no
"Download all GPX" button: each day has its own download, as before.

**The introduction.** Until the PCT's `index.md` has text under its front matter, the Overview shows one paragraph
built from fields and counts only. Today it reads:

> Pacific Crest Trail 2024: 150 recorded days, Apr 22 – Sep 21, 2024, Mexico to Canada. One entry per recorded day,
> grouped by month. The 32 days with a write-up carry the notes from that day and any photos; the other 118 show the
> track, 3 of them with photos. Every track is the full recording, not trimmed, with its own GPX download.

The first sentence is the `title:`, the number of day files, the date range and the `place:`. A journal with no dates
or no `place:` leaves that part out of the sentence, and the page's meta description leaves out a missing date range
the same way. The other numbers are counted from the day files on every build. To replace the paragraph, write the
introduction as ordinary text under the closing `---` of `content/trips/pacific-crest-trail-2024/index.md`. It is then
shown word for word, like a report write-up, in place of the whole generated paragraph, including the notes on how the
log is organised. Two things follow from having that text: the Trips page search finds its words, and its opening
becomes the PCT card's summary unless `card_summary` is set (section 4).

**Written entries first.** With JavaScript the day log opens on the days that have a write-up. The "Show days with
write-ups only" toggle ("Write-ups only" on phones) starts switched on, so 32 of the 150 days show, months without a
write-up are hidden, and the month bar greys those months out (July and August 2024 today). Switching the toggle off,
or "Browse all recordings", shows every day. Once a reader has used the toggle or that button, the page keeps their
choice for the rest of the browser session in that tab, so a reload or Back returns to the list as they left it. The
button counts as a choice even when a link had already switched the filter off. A fresh tab starts on write-ups again.
Without JavaScript there is no toggle and every day shows.

**A direct link still lands.** A link to something the filter would hide is not left hidden.

- Opening the page at `…/trips/pacific-crest-trail-2024/#day-5-2` (Day 5.2, a track-only day) or at
  `…/trips/pacific-crest-trail-2024/#month-2024-07` (July 2024, no write-ups): the filter starts switched off and the
  browser goes to the target.
- When the address changes while the page is open (a Highlights link to a track-only day, a month in the Overview's
  month list, Back or Forward): the filter is switched off, screen readers hear "Showing all 150 days", and the page
  scrolls to the target. The same happens when a link to a hidden day or month is followed while the address already
  ends with that fragment.
- A link to a written entry or to a month with write-ups leaves the filter as it is. When such a link opens the page
  with the filter on, the page scrolls to the target again after the filter has hidden the other days. It does not do
  that on a reload or on Back / Forward: the browser returns the reader to where they were, and the page leaves them
  there.
- Being shown a hidden day by a link does not count as the reader's choice: the next visit in that tab starts on
  write-ups again.

**Moving between written entries.** Each written entry ends with "Previous write-up: Day N" and "Next write-up: Day
N". They go to the nearest written day before and after, skipping track-only days: from Day 35 the next write-up is
Day 50. The first written entry has only Next and the last has only Previous. After them, "Copy link to this entry"
copies the page address with the entry's anchor, for example
`https://esichak.github.io/personal-website/trips/pacific-crest-trail-2024/#day-50`. Track-only days have none of
these. The day number is the day file's `day:` value (`day: 0` is Day 0; without the line a day takes its position
among the day files), and a decimal point becomes a hyphen in the anchor: Day 5.2 is `#day-5-2`. Any other character
that is not a plain letter (A to Z) or a digit becomes a hyphen as well, so the anchor is safe to link to whatever the
label holds. Two days of one journal may not end up with the same anchor, and a label needs at least one letter or
digit; the build stops and names the day file:

  | In a day file | The build says (after `content/trips/<slug>/days/<file>.md: `) |
  | --- | --- |
  | `day: 5-2` when another day is `5.2` | `day: '5-2' gives the same page anchor (#day-5-2) as days/004.md; give each day its own label` |
  | no `day:` line, in a file whose position another day uses as its label | `no day: line, so this day takes its position, 151, and that gives the same page anchor (#day-151) as days/148.md; add a day: line with a label no other day has` |
  | `day: "5 n"` when another day is `5` | `day: '5 n' needs the page id #day-5-n, which days/005.md already uses; give each day its own label` |
  | `day: "?"` | `day: '?' has no letter or digit to make its page anchor from` |

The second row is the one to expect on the PCT. Its labels do not follow the file order (`days/148.md` is Day 151), and
`add_trip.py --day-of` writes a day file without a `day:` line, so a day added there needs the line typed in, with a
label no other day has (for example `day: "154"`).

Unchanged: the month bar, the Overview's month list, every `#day-…` and `#month-…` anchor, each day's GPX link and
file name. There is still one PCT page and no page per day.

**Finding an entry from the Trips page.** A search on `/trips/` also lists the PCT days that match, written or
track-only, under "Journal days" after the reports, and each one links to its day on this page (section 6, "Journal
days"). A link to a track-only day switches the write-ups filter off, as above.

### 7.8 Highlights: `journal_highlights`

An optional list of entries the PCT page points to, shown above the day log. The list is empty today: the line is not
in the PCT's `index.md`, the page has no Highlights section, and nothing else depends on it. Add it after reading the
entries.

```yaml
journal_highlights: [001, 059]
```

- The line goes in `content/trips/pacific-crest-trail-2024/index.md`, among the front-matter lines above the closing
  `---`. Square brackets, ids separated by commas.
- **Ids are day-file names, not day numbers.** `days/001.md` is `001` and `days/059.md` is `059`. The day number
  written inside the file (`day: "5.2"`) is something else: Day 5.2 is `days/006.md`, so to list it write `006`.
  `ls content/trips/pacific-crest-trail-2024/days` shows the ids.
- **Zero-padding.** Write the ids as the files are named. The parser reads a bare `059` as the number 59, and the build
  pads it back to the width of the file names, so `[1, 59]` means the same as `[001, 059]`. Quoted ids
  (`["001", "059"]`) work too.
- **Order is kept.** The listed order is the display order. Reorder the list, not the files.
- **What shows.** A "Highlights" section between the Overview and the day log, with an `N ENTRIES` count and one item
  per listed day: "Day" and the day number, the day's title with its date on a line under it, and, for a written day,
  the opening of its write-up as plain text, cut at about 160 characters. A day with no title shows its date in the
  title's place, once, with no date line under it. Each item links to the day's entry. A track-only day can be listed;
  it shows no excerpt, and following its link switches the write-ups filter off (7.7).
- **What stops the build.** Each message starts with the file name, `content/trips/pacific-crest-trail-2024/index.md: `,
  and the build prints it after `ERROR`. The id is printed the way the parser read it, so a bare `059` appears as `59`.

  | Mistake | Message after the file name |
  | --- | --- |
  | not a list (`journal_highlights: 059`, no brackets) | `journal_highlights must be a list of day ids such as [001, 059], got 59` |
  | an id with no day file (`[999]`) | `journal_highlights names day 999, which is not a days/NNN.md of this trip` |
  | the same day twice (`[059, 59]`) | `journal_highlights lists day 59 twice` |
  | a list with ids on a trip that is not a journal | `journal_highlights is for a journal (kind: series); this trip is kind: trip` |

- **Absent or empty is fine.** No line, a bare `journal_highlights:`, or `journal_highlights: []` all mean no
  Highlights section. A list with ids on any trip but the PCT stops the build (the last row above), so the line
  belongs in the PCT's `index.md` only.
- Highlights are a choice: list entries that have been read and are worth pointing to. The build never picks one, and a
  long day is not a highlight because it is long.

A build is enough; no `render.py` run.

### 7.9 Preview

```bash
python3 tools/build.py --serve              # build, then open http://localhost:8000 (Ctrl+C to stop)
```

- A story report: http://localhost:8000/trips/matterhorn-peak-west-couloir/ (or any trip with a write-up and photos).
- A story without a lead photo: http://localhost:8000/trips/thankful-for-the-demo-forest/ (its one photo is nearly
  square).
- The PCT: http://localhost:8000/trips/pacific-crest-trail-2024/
- A direct link to a track-only day: http://localhost:8000/trips/pacific-crest-trail-2024/#day-5-2
- A direct link to a month without write-ups: http://localhost:8000/trips/pacific-crest-trail-2024/#month-2024-07

Look at a report at phone width and at desktop width when a cover or focal point changed. The PCT page remembers the
write-ups toggle for the tab, so open a fresh tab to see the page as a first visit does. Then run the checks from
section 5 and commit the edited `index.md` by path.

## 8. What not to do

- Do not invent summary copy, captions or stats. If a sentence cannot be checked against the report, leave
  `card_summary` out; the fallbacks in section 4 are built from the data and are truthful.
- Do not present the PCT as one day's story. The series card shows no sentence: its DATE · PLACE line and its
  RECORDED DAYS · MI RECORDED line carry the facts; a day's prose belongs on that day's page.
- Do not invent highlights or captions. `journal_highlights` lists entries that have been read and chosen; leave the
  line out rather than listing the longest days or guessing from titles. A lead photo's caption is that photo's own
  `caption:`; when there is none the photo has no caption, and the build never writes one.
- Do not name a portrait, a square or a near-square photo in `cover_photo` to get a lead photo. Only a cover at least
  6:5 wide leads a page (7.3); a narrower one changes the cards and the share image and leaves the page without a lead
  photo.
- Do not rename day files or change day labels to change an anchor. `days/006.md` and its `day: "5.2"` are what
  `#day-5-2`, the day's GPX link and file name, the Previous / Next write-up links, the copied entry links, the
  journal-day search results and `journal_highlights` refer to, and a link someone already saved would open the page
  at the top instead of the entry. To change what a row says, edit `title:` in the day file; to reorder highlights,
  reorder the list.
- Do not paste a day's prose into the journal introduction. Text under the front matter of the PCT's `index.md` is
  for words written about the whole trail; a day's write-up stays in its `days/NNN.md`. Until such text exists the
  facts-only paragraph is the introduction (section 7.7).
- Keep original titles. `PEAK BAGGING SZN` is one loop, titled the way Eric titled it; do not rename a trip or
  trim a route name to fit a card.
- Do not edit `_site/` by hand. It is rebuilt from `content/`, `rendered/` and `assets/` on every build and on
  every push.
- Stage content changes by explicit path. `rendered/` holds thousands of untracked iCloud conflict copies with
  names like `meta 3.json` and `map-wide 4.webp`, and `git add -A` would commit them all. Check `git status`
  for ` 2`/` 3`/` 4` names before committing.

```bash
git add content/home.json "content/trips/matterhorn-peak-west-couloir/index.md"
git commit -m "Feature Matterhorn and set its cover" && git push
```

When highlights or the PCT cover change, the PCT's `index.md` joins the explicit paths:

```bash
git add "content/trips/pacific-crest-trail-2024/index.md"
git commit -m "List the PCT highlights" && git push
```
