# Content guide: homepage features, covers, summaries, search, report pages and the PCT journal

How to choose what the homepage shows, which photo fronts a trip's card and leads its report, what the card says, what
the Trips page finds when someone searches, and which entries the PCT journal points to. It also covers checking the
content before it is built (section 5), the optional publication dates (section 8), what a shared link shows
(section 9) and the page that a region with a region map and a published report gets (section 11). All of it is done
by editing two kinds of file (`content/home.json` and a trip's `index.md`) and running the commands in section 5. No
Python edit is needed to feature, reorder or re-cover a trip, or to list PCT highlights.

Adding a trip is in [ADDING-TRIPS.md](../ADDING-TRIPS.md); how the generator works is in
[DEVELOPING.md](DEVELOPING.md).

## 1. The homepage list: `content/home.json`

```json
{"featured_slugs": ["pacific-crest-trail-2024", "matterhorn-peak-west-couloir", "peak-bagging-szn"]}
```

- A slug is the trip's folder name under `content/trips/` (also the end of its URL, `…/trips/peak-bagging-szn/`).
- Order is display order. The first slug is the lead card; the rest are supporting cards.
- Zero to six slugs. `{"featured_slugs": []}` hides the featured section; the build never swaps in another trip. With
  no features the home page has no share image, and neither do About, Map, Trips and Tick list (section 9).
- This file alone picks the homepage. `featured: true` in a trip's front matter still drives the Featured block
  on that trip's section page (Climb, Hike, MTB, Other; the Ski page has no Featured block; single-day trips with a
  track only, so the flag on a multi-day trip, the PCT or a report without `track.gpx` does nothing there). On its
  region's page it counts for a report of any kind, with or without a track: flagged reports come before unflagged
  ones in the Featured row there, which holds three cards (11.3). It no longer has any say over the homepage.
- If the file is missing, the build prints a warning naming `content/home.json` and falls back to the old pick
  (the newest published trip flagged `featured: true`, else the newest published trip). The build still succeeds, so
  GitHub would publish that fallback: keep the file in place.

A wrong manifest never falls back to a different trip. A typo, a draft, a planned route or a seventh slug stops
the build with a message naming the file and the slug or the count (first table in section 5.2).

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
outings if it is recent enough; only the homepage feature goes. Taking the trip itself off the site is in 7.10.

**What the homepage shows**

- One card per slug, in order. With the three slugs above: a lead card for the PCT and two supporting cards.
  The section renders cleanly with 0, 1, 2, 3 or 6 cards.
- Each card: the cover (section 3), the trip's original title as the link, an activity or "Journal" label, the
  date and place, a couple of stats, the summary (section 4), and a link: "Explore the journal" for the PCT,
  "Read the report" for a trip with a write-up, "View trip" for a track-only trip.
- The lead card's cover is also the page's share image (section 9).
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
that trip's `index.md` or in one of its `days/NN.md`. The card reuses that entry's `w`, `h`, `alt` and the photo's
smaller copies (below), so nothing else is declared. A day photo works too (`cover_photo: photos/d001-03.webp` on the
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
least 6:5 wide (section 7.3), and the share image of the trip's page (section 9).

**Card-size copies.** A photo comes as up to three files in `photos/`: the full one (`01.webp`), an 800 px copy
(`01.sm.webp`) and a card-size copy (`01.th.webp`, 320 px on its short edge). `add_trip.py` writes all three for every
photo it imports. On a phone the small cards (the Trips page, Recent outings, More like this, the Featured row of a
region page) load the cover's card-size copy when the file is there and the 800 px copy when it is not, so a missing
copy never breaks a page; those cards just load a larger file than they need. A card's photo is 112 px wide on a
phone, and the page tells the phone 106 px: three times 106 is 318, so a phone with three pixels to the point still
takes the card-size copy of a portrait or square cover, which is 320 px wide. On wider screens the cards are not
offered the card-size copy. They load what they loaded before it existed: the 800 px copy on a standard screen, and
the full file where a screen with two or three pixels to the point asks for more than the 800 px copy holds.
`validate.py` and every build name the covers that have none:

```
WARNING content/trips/<slug>/index.md: cover photos/01.webp has no card-size copy (.th); run python3 tools/thumbs.py <slug>
```

Expect it after pointing `cover_photo` at another photo of an older trip: apart from the PCT's day photos, only the
covers were given a card-size copy when these were introduced. Make the file and commit it with the change:

```bash
python3 tools/thumbs.py <slug> --dry-run    # say what would be written, write nothing
python3 tools/thumbs.py <slug>              # write the missing copy for that trip's cover
python3 tools/thumbs.py                     # the same for every trip
```

`thumbs.py` only adds `<name>.th.webp` files beside the photos; it changes no photo and no `index.md`. It needs
`cwebp` (`brew install webp`). It skips a cover whose entry has no `w` and `h`, without saying so: add those two lines
first. A photo that `cwebp` cannot read is skipped with a line of its own, and the closing line counts it:

```
skipped content/trips/<slug>/photos/01.th.webp: the photo could not be converted
wrote 0 card-size copies; 0 already there; 1 skipped (photo missing or unreadable)
```

Replace that photo file with a sound copy and run the command again. Which copy a phone or a desktop then loads is
settled by the build and the browser; nothing needs setting for it.

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
excerpt on a homepage feature card gets about 230 characters, on the Recent outings and Trips page cards about 180).

Without `card_summary` the card shows:

- **a trip with a write-up:** the opening of the report, as plain text. It ends at the end of a sentence when one ends
  after the first third of the room the card has (about 230 characters on a homepage feature card, 180 on the Recent
  outings and the Trips page), with no ellipsis; otherwise it is cut at a word and ends in `…`. A full stop after `Mt`,
  `St`, `vs`, `approx` and the like, after a single letter (an initial) or inside `e.g.` is not a sentence end. The
  words are always the report's own, from its start;
- **the PCT (a series):** no sentence. The card's data lines carry the facts instead (`APR 22 – SEP 21, 2024 ·
  MEXICO TO CANADA` and `150 RECORDED DAYS · 3,167 MI RECORDED`, counted from the days that have a track). Never a
  day's prose: the first day's story is not the story of the trail;
- **a multi-day trip** with at least one written day: a labelled excerpt from that day, with the label (for
  example `DAY 2 · <day title>`) shown above it; with no written day, no sentence (the date range and the stats
  say what it was);
- **a single-day trip with no write-up:** nothing, and the link reads "View trip".

## 5. Preview and checks

```bash
python3 tools/validate.py                   # read content/ and list every problem; nothing is built
python3 tools/build.py --serve              # build, then open http://localhost:8000 (Ctrl+C to stop)
python3 tools/build.py --check              # full build, then the checks of the built site (5.4)
python3 -m unittest discover -s tests       # the generator's tests
```

Run all four before pushing. `validate.py` is the quick one: it reads the content and prints one line per problem
without building anything. Every build runs the same rules before it writes a file, so a broken value stops `--serve`
and `--check` too. Ctrl+C stops the preview; the Python traceback it leaves, ending in `KeyboardInterrupt`, is normal.

GitHub runs the tests and `build.py --check` on every push to the `main` branch, and publishes only when both pass. A
push to any other branch runs nothing and publishes nothing. So an error fails the deploy instead of publishing a
broken page, and the site does not update until it is fixed. A warning does not hold a deploy back.

### 5.1 `validate.py`

It reads every trip folder under `content/trips/` (drafts too: a broken draft stops a build like any other trip),
`content/home.json`, and four things in `rendered/`: whether a trip's map has been drawn, whether it was drawn from the
trip as it is now (the track, title, activity, kind, `map:` and stats) and with OpenStreetMap data, which regions the
site maps know, and which trips those maps draw. It writes nothing, draws nothing and fetches nothing.

Each finding is one line: the level, the file to open, then the message. The lines are sorted by file and a summary
follows. On today's content the summary reads:

```
content: 0 errors, 1 warnings, 468 notes (168 trips, 398 photos, 341 GPX files)
```

The one warning is about a planned route saved before the tick list ([TICK_LIST_GUIDE.md](TICK_LIST_GUIDE.md),
section 9).

| Level | What it is | What happens |
| --- | --- | --- |
| `ERROR` | a value the generator cannot use, or a file that a page needs and is not there | the build stops; exit status 1 |
| `WARNING` | optional metadata left incomplete; the pages cope | the build goes on; exit status 0 |
| `NOTE` | an optional field that is simply absent: no place, no write-up, no photos, a day without a title, photos without a caption; and a trip whose `timezone:` is `UTC` (`timezone is UTC, so start_time is a UTC clock; set the zone with python3 tools/add_trip.py --retime <slug> --timezone <zone>`: the tool's guess falls back to UTC where it knows no zone, and the page's Start time is then a UTC clock) | counted in the summary; listed only with `-v` |

| Flag | Effect |
| --- | --- |
| `-v` | also list the notes, one by one |
| `-q` | print the errors and the summary line only |
| `--strict` | a warning fails the run as well (exit status 1) |
| `--json` | print every finding, notes included, as a JSON list of `{"level", "file", "text"}` |
| `--site DIR` | also check a built site folder such as `_site`: the lines of 5.4, each after `ERROR`, then `site: N problems` |
| `--content DIR` | check another folder laid out like `content/` (`trips/` and `home.json` inside). The lines still name the files `content/trips/<slug>/…`. Renders are looked for in a `rendered/` folder beside DIR; without one, the `no rendered map`, `region … is not in rendered/site/meta.json` and `the site maps under rendered/site/ still draw this trip` warnings are not given |
| `--today YYYY-MM-DD` | the day that dates are judged against (default: today) |

Exit status: 0 when there is no error, 1 for an error (or a warning under `--strict`, or a problem in the `--site`
folder), 2 for a mistake on the command line.

**What a build does with the same rules.** `build.py`, with or without `--serve` or `--check`, checks the content
first. With an error it prints every `ERROR` line and stops with exit status 1 before the output folder is touched.
With warnings only it prints the first ten, then `... N more; python3 tools/validate.py lists them`, and builds.

### 5.2 Errors

An error line reads `ERROR <file>: <message>`. In the second table below and in 5.3 the messages are quoted exactly
as printed after the file name, with `<slug>` standing for a trip's folder name. Where a message ends in `got …`, that
is the value found in the file. `photos[1]` and `beta[0]` count entries from 0: `photos[1]` is the second photo listed.

`content/home.json` and the fields of sections 3, 4 and 7.8:

| Message (after `ERROR`) starts with | What it says | Fix |
| --- | --- | --- |
| `content/home.json: …` | malformed JSON, or the file is not a JSON object | Compare with the one-line example in section 1: double quotes, square brackets, commas between slugs, no trailing comma. |
| `content/home.json: …` | `featured_slugs` is missing | Add the key: `{"featured_slugs": [...]}`. |
| `content/home.json: …` | `featured_slugs` is not a list | Wrap the slugs in `[ ]`, even for one slug. |
| `content/home.json: …` | an entry is not text, or is empty | Every entry is a quoted slug; delete `""`. |
| `content/home.json: …` | a slug is listed twice (named) | Remove the repeat. |
| `content/home.json: "featured_slugs" is written twice; keep one` | the key stands twice inside the one pair of braces, for example a second `"featured_slugs": [...]` added after the first (a whole second `{...}` line pasted under the first is reported as malformed JSON, first row) | Delete one of the two lists. |
| `content/home.json: unknown slug '…' in featured_slugs` | no such folder in `content/trips/` | Check the spelling against `ls content/trips/`. |
| `content/home.json: …` | the slug is a draft (named) | Remove `draft: true` from that trip's `index.md`, or take it out of the list. |
| `content/home.json: …` | the slug is a planned route (named) | Planned routes cannot be featured; take it out of the list. |
| `content/home.json: …` | more than six slugs (the count is given) | Cut the list to six or fewer. |
| `content/trips/<slug>/index.md: …` | `cover_photo` is not a photo declared under `photos:`, or the path escapes the folder (path named). A declared photo whose file is gone is reported as `photos[N].file … is missing` (next table) | Use the exact `file:` value of a photo under `photos:` in `index.md` or a `days/NN.md`, and drop any `..` or leading `/`. |
| `content/trips/<slug>/index.md: …` | `cover_focal_x` / `cover_focal_y` is out of range or not a number | Plain number from 0 to 100: `cover_focal_y: 45`, not `"45%"` or `true`. |
| `content/trips/<slug>/index.md: …` | `card_summary` is not text | Quote it: `card_summary: "…"`. A bare number, `true`, or a `[list]` parses as something other than text. |
| `content/trips/<slug>/index.md: journal_highlights must be a list …` | the value is not a list (value shown) | Square brackets, even for one id: `journal_highlights: [059]`. |
| `content/trips/<slug>/index.md: journal_highlights names day …` | an id has no `days/NNN.md` (id shown as the parser read it, so `059` appears as `59`) | Use the day file's name, not the day number: Day 5.2 is `006`. `ls content/trips/<slug>/days` lists them. |
| `content/trips/<slug>/index.md: journal_highlights lists day … twice` | the same day is listed twice (`059` and `59` are the same day) | Remove the repeat. |
| `content/trips/<slug>/index.md: journal_highlights is for a journal …` | the list is on a trip that is not `kind: series` (its kind is shown) | Remove the line; only the PCT uses it. |
| `content/trips/<slug>/index.md: region_days …` | the journal's `region_days` block is not readable: it is not a list of regions with their days, a day or a range matches no day of the journal, a range runs backwards, a region or a part has no days, a region is listed twice, a part is named twice or has no name, a stretch is written of a range or without a number from 1 (`146/0`), a day is listed both whole and as a stretch, or the block is on a trip that is not a journal (the message says which, and names the part as `Lake Tahoe: Tahoe Rim Trail`) | Write it as in 11.7: a region with its days (`Eastern Sierra: 58-65`) or with named parts under it, with the day numbers the journal page shows. |
| `content/trips/<slug>/index.md: region_days takes stretch 3 of day 146, whose track has 2 (a stretch ends where two fixes lie more than 20 km apart)` | the block takes a stretch the day's recording does not have (`146/3`), or a stretch of a day without a track (`… whose track holds no fixes`) | Count the stretches from 1 in the order they were recorded (11.7), or list the day whole. |
| `content/trips/<slug>/index.md: region_days names the region 'Lake Taho', which no report is filed under (did you mean 'Lake Tahoe'?)` | the region in the block is not the `region:` of any report, letter for letter | Spell it as the reports do. |

Any trip's files. The file named is `content/trips/<slug>/index.md`, or the `days/NN.md` that holds the line, unless
the row says otherwise:

| Message | Cause | Fix |
| --- | --- | --- |
| `title is missing or empty (write the trip's name after title:)` | no `title:` line, or nothing after it | Add the trip's name. |
| `activity must be one of ski, climb, hike, mtb, other, got 'skiing'` | an activity the site does not have | Use one of the five words. |
| `kind must be one of multi-day, series, planned (leave the line out for a single-day report), got 'multiday'` | a misspelt `kind:` | `multi-day`, `series` (the PCT) or `planned` (a tick-list goal). A single-day report has no `kind:` line. |
| `days/ holds 1 day file but there is no kind: line; add kind: multi-day (or kind: series for a journal)` | a day was added with `add_trip.py --day-of` to a trip whose `index.md` does not say it has days | Add `kind: multi-day` to `index.md`. An `end_date:` line is optional: without one the page ends on the last day file's date. Not when the folder also holds a `track.gpx`: the trip is then a single-day report, and a multi-day page draws and offers only the day files, so that track would drop off the page with only the `is not used: …` warning (5.3) to say so. In that case delete the `days/` folder when the day was added by mistake, or rebuild the trip as a multi-day folder ([ADDING-TRIPS.md](../ADDING-TRIPS.md), "Multi-day trips": "If the trip is already on the site as a single-day report"). |
| `kind is 'multi-day' but the folder has no day files (days/01.md, days/02.md, ...)` | `kind: multi-day` on a trip without a `days/` folder | Add the days with `add_trip.py --day-of <slug>`, or remove the line. |
| `date must be a date written YYYY-MM-DD, got 'Jan 17 2026'` | a date in another form, or one that does not exist (`2026-13-45`). `end_date:` and the `date:` of a `days/NN.md` are held to the same rule | `date: 2026-01-17` |
| `end_date 2026-08-30 is before date 2026-09-01` | one of the two is wrong | Fix it. |
| `draft must be true or false, got 'yes'` | `draft: yes` reads as text, not as true. `featured:` is held to the same rule | `draft: true`, or delete the line. |
| `place must be text, got ['Nowhere Flat', 'Elsewhere']` | a value that starts with `[` is read as a list. `region:` and `party:` are held to the same rule | Drop the brackets, or wrap the whole value in double quotes. |
| `stats.distance_km must be a number, got 'about 2'` | words in a stats number | Digits only: `distance_km: 12.4`. |
| `stats.moving must be a time written H:MM such as "6:10", got '39 min'` | a time in another form | `moving: "0:39"` |
| `photos[1].file 'photos/20.webp' is missing from the trip folder` | a photo listed under `photos:` whose file is not in `photos/`: a typo in `file:`, or the file was moved or deleted | Fix the `file:` value, or put the file back. |
| `photos[1] (photos/02.webp) has w but no h; record both (the pixel size) or neither` | one of the two size lines is missing | Add it, or delete the other. |
| `beta[0] has no value` | a `- label:` row without its `value:` line | Add the line, or delete the row. |
| `beta[0].value must be text, got 5.1 (quote a number to keep it as written)` | a bare number: `value: 5.10` is read as 5.1 | `value: "5.10"` |
| `write-up link '/trips/peak-bagging-szn/' starts with /, which leaves the site (it is served under https://esichak.github.io/personal-website/); write a relative link such as ../other-trip/ or the full address` | a Markdown link in the write-up that starts with `/` | From one report to another: `[text](../peak-bagging-szn/)`. |
| `write-up link '../no-such-trip/' points at trips/no-such-trip/, which is not a page of the site (no content/trips/no-such-trip/index.md)` | a link to a report that does not exist. For a draft the message ends `a draft, which has no page` | Check the slug against `ls content/trips/`. |
| `the file is empty; a report's track must be a GPX file with at least one point (without the file there is no map and no download for it)` | the file named is `content/trips/<slug>/track.gpx`, or a day's `days/NN.gpx`: an empty track file | Export the track again, or delete the file. |
| `looks like an iCloud conflict copy (the name ends in a space and a number): it would be published as one more day; delete it` | the file named is the copy itself, such as `content/trips/<slug>/days/02 2.md` or `days/02 2.gpx`: iCloud Drive left a second copy of a day file, and the build would read `02 2.md` as one more day. The PCT's day files are held to the same rule | Delete the copy, and the copy of its GPX when there is one. |
| `none of the day GPX files holds a recorded track (<trk>): "Download all GPX" would be an empty file; a day's file is that day's recording` | the file named is the `index.md` of a multi-day trip whose `days/NN.gpx` files all hold a route (`<rte>`) and no recorded track. `add_trip.py --day-of` writes a track, so this takes GPX files put into `days/` by hand. One such day among recorded ones is a warning (5.3) | Put each day's recording in its `days/NN.gpx`. |
| `the folder name 'My_New Trip' cannot be a page address: use lower-case letters, digits and single dashes (such as my-new-trip)` | a trip folder made or renamed by hand | Rename the folder. |
| `front matter: front matter is not closed with ---` | the `---` line that ends the block at the top of the file is gone. A `days/NN.md` is named the same way | Put it back. |
| `front matter: line 7 is indented with a tab; use spaces` | a line of the front matter (line 7 of the file here) starts with a tab, as an editor's Tab key writes one. A tab would move the key under it to another level without a word, so it is refused | Replace the tab with spaces: two for each level, as in the lines around it. |
| `front matter: Extra data: line 1 column 14 (char 13)` | a value that starts with a double quote but is not one complete quoted string, such as `card_summary: "No chance." The rest` | Quote the whole value and write an inner quote as `\"`. |

A `#` after a space starts a note that is not part of the value, as in YAML: `title: Rose Knob  # first lap` is the
title `Rose Knob`. A `#` inside quotes or inside `[...]`, or with no space before it (`C#`), stays in the value; to
write ` #` into a value, quote it (`title: "Peak #2"`). A `#` that looks like part of a value (`Lap #2`: a letter or a
digit right after it) gets a warning (5.3), because the note cuts the value short.

The two tables do not quote every error. One that is not listed is written the same way: the line names the file and
the field and says what is accepted there, as in `start_time must be a time written HH:MM (00:00 to 23:59), got '8am'`.

Dates, clock times, durations and numbers are read in the digits 0 to 9 only. The same value typed in other digits,
such as full-width ones, is refused with its field's message, as in
`date must be a date written YYYY-MM-DD, got '２０２６-０９-０１'`.

The messages for `published_at` and `updated_at` are in section 8, those for a PCT day's `day:` label in 7.7, and
those for a tick-list goal in [TICK_LIST_GUIDE.md](TICK_LIST_GUIDE.md), section 9.

### 5.3 Warnings

A warning line reads `WARNING <file>: <message>`. A warning never stops a build. The file named is
`content/trips/<slug>/index.md`, or the `days/NN.md` that holds the line, unless the row says otherwise.

| Message | Cause | Fix |
| --- | --- | --- |
| `no date (add date: YYYY-MM-DD): the page, its card and the feed show none and the trip sorts last` | a report without a `date:` line | Add it when the day is known. |
| `date 2027-09-01 is in the future (today is 2026-10-10)` | usually a typo in the year. A date one day ahead is accepted | Fix the date. |
| `no track.gpx: the page has no map, no profile and no GPX download` | a single-day report without a track | Nothing, when the trip has no recording: the page is built without those parts (7.2). Otherwise add the track. |
| `none of the 2 days has a GPX (days/NN.gpx): the page shows an empty map and offers no downloads` | a multi-day trip or a journal with no `NN.gpx` beside any of its `days/NN.md` | The page is built either way, with an empty map. `add_trip.py --day-of <slug>` writes a day's `NN.md` and `NN.gpx` together ([ADDING-TRIPS.md](../ADDING-TRIPS.md)). |
| `region_days: the region map of Lake Tahoe was last drawn without these days; run python3 tools/render.py --site and commit rendered/site/` | the journal's `region_days` block lists days for a region whose map was drawn before, or with other days (`… with other days of this journal`) or another stretch of a day (`… with another stretch of one of these days`), or the block no longer lists days the map still draws (`the region map of … still draws days of this journal …`) | Run the command (internet needed) and commit `rendered/site/` with the change (11.7). The message names the part when the region has named parts (`the region map of Lake Tahoe (Tahoe Rim Trail) …`). Until then the list has the rows and the map shows what it was last drawn with. |
| `region_days: 'Yosemite' has no region map (one is drawn from three reports with a track), so these days are shown on no map` | the block names a region that has reports but no region map | Nothing, or take the line out: the days appear once the region has its map. |
| `no rendered map (rendered/trips/<slug>/meta.json is missing); run python3 tools/render.py <slug> (until then the page shows "Map not rendered yet")` | the trip was added with `--no-render`, or its render did not finish. Until then the page's map section is a box that says so (7.2). On the PCT journal the line ends after the command, and its map area is empty | Run the command it gives (needs the internet), then stage `rendered/trips/<slug>` and `rendered/site` with the trip (step 5 of [ADDING-TRIPS.md](../ADDING-TRIPS.md)). |
| `maps were drawn from other inputs (the track, the title, activity, kind, map: or stats changed since): run python3 tools/render.py <slug>` | the trip's track, `title:`, `activity:`, `kind:`, `map:`, `stats:` or `route_shape:` (or a day's file of a multi-day trip) changed after its maps were drawn: `render.py` stores what it drew from, and it no longer matches. The page still shows the old maps | Run the command (needs the internet) and stage as in step 5 of [ADDING-TRIPS.md](../ADDING-TRIPS.md). `python3 tools/render.py --status` says which of them changed. |
| `maps were drawn without OpenStreetMap data (no roads, trails or lake names); run python3 tools/render.py <slug> again` | OpenStreetMap did not answer when the maps were drawn, so they show terrain only | Run the command again later. |
| `the region and ski maps were drawn from other inputs (a trip on one of them changed, was added or was taken out since); run python3 tools/render.py --site and commit rendered/site/` | the file named is `rendered/site/meta.json`: a trip of a region with a region map (or a ski map) changed, was added or was taken out after those maps were drawn. The line is left out when another line of the same run already asks for a render, because `render.py <slug>` draws these maps again too | Run the command and stage `rendered/site`. |
| `the region and ski maps were drawn without OpenStreetMap data; run python3 tools/render.py --site again and commit rendered/site/` | the file named is `rendered/site/meta.json`; as the line above for a trip's maps | Run the command again later. |
| `photos[1] (photos/02.webp) has no alt text; describe the photo in a sentence` | `alt: ""`, which is what `add_trip.py` writes | Write the description. On the cover it is also the share image's description (section 9). |
| `photos[1] (photos/02.webp) has no w and h, so the page cannot hold its place while it loads; record the pixel size` | a photo entry typed by hand | Add `w:` and `h:`, the file's size in pixels. |
| `photos[1] (photos/02.webp) has no 800 px copy (02.sm.webp), so phones load the full file` | a photo copied into `photos/` by hand. `add_trip.py` writes this copy for the photos it imports; no tool adds one afterwards | Save a copy 800 px on its long edge under the name in the message. |
| `photos[2] declares photos/01.webp again (first in index.md, photos[0]); the page shows it twice` | one photo file is listed in two entries of the trip: in `index.md`, in a day file, or one in each. The line names the file that holds the second entry and says where the first one is | Delete one of the two entries. |
| `cover photos/01.webp has no card-size copy (.th); run python3 tools/thumbs.py <slug>` | section 3, "Card-size copies" | Run the command it gives. |
| `not declared under photos: in index.md or a days/NN.md, and not the .sm or .th copy of a declared photo; the build publishes it all the same` | the file named is one in `content/trips/<slug>/photos/` that no entry lists. An iCloud conflict copy such as `01 2.webp` shows up this way | Delete the file, or add an entry for it. |
| `looks like an iCloud conflict copy (the name ends in a space and a number): nothing reads it, but git add of the folder would stage it; delete it` | the file named is the copy: a file in a trip folder or its `days/` whose name ends in a space and a number, such as `index 2.md` or `track 2.gpx`. A copy of a day's `.md` or `.gpx` is an error instead (5.2), and a copy in `photos/` gets the line above | Delete the file. |
| `unknown key 'plase' (did you mean 'place'?); nothing reads it` | a misspelt field name: the line is ignored. Inside a photo entry or `stats:` the message says where (`in photos[1]`, `in stats`). A misspelt key in `content/home.json` gets the same line, with that file named | Correct the name. |
| `line 2: '#2' after a space starts a note, so the line is read as 'title: Lap'; quote the value if the # belongs to it` | a `#` after a space with a letter or a digit right after it (`title: Lap #2`): the front matter reads everything from ` #` as a note (5.2), so the value is cut short. A note written `# like this`, with a space after the `#`, is taken for a comment and says nothing | Quote the value (`title: "Lap #2"`), or write the note with a space after the `#`. |
| `key 'place' is written twice in the front matter; only the last one is read` | a field name stands twice at the left margin of the front matter, in `index.md` or in a `days/NN.md` | Delete one of the two lines. |
| `route_shape 'lollipop' is not one of loop, out-and-back, point-to-point; it is shown as written` | a `route_shape:` the site has no word for. `subtype:` is held to its own list in the same words: `subtype 'Scrambling' is not one of SUP, Rafting, Kayaking, Mountaineering; it is shown as written` | Use one of the listed words. |
| `region 'Lake Taho' is not in rendered/site/meta.json, so the map page does not list it yet; run python3 tools/render.py --site --force` | a region the site maps do not know: a misspelling, a new region, or a region that was renamed. When several trips are filed under it, the line names one of them and counts the others: `region 'Lake Taho' (and 2 more trips) is not in …` | Correct the spelling. When the warning of the next row is printed as well, the name is a second spelling of a region that is on the site: bring the trips to one spelling and do not run the command while two are in use, because after that render `build.py --check` fails (next row). For a new region run the command as printed (needs the internet) and commit `rendered/site/`. Without `--force` the run can end before it rewrites the list of regions. For a renamed region the same command draws the region map under the new name, which takes three trips with a track; until it has, the region's reports are on no region page (11.4). |
| `region 'nowhere range' is written 'Nowhere Range' on 1 other trip; the two are listed as different regions but share one filter value and one map anchor (nowhere-range)` | two spellings of one region that give one address (the slug rule is in section 11: capitals, accents, apostrophes and other punctuation do not count). Once the region maps have been drawn with both spellings, the Map page has two blocks with one address, and the check fails with a `DUPLICATE IDS map/index.html: …` line that lists ids of the region, `region-nowhere-range` among them. Where the region has a map on the Ski page and ski reports are filed under both spellings, that page fails in the same way (`DUPLICATE IDS ski/index.html: …`), even before a render (11.4) | Use one spelling on every trip. A build is then enough for the check to pass, except where each spelling had a region map: there the maps have to be drawn again as well (`python3 tools/render.py`, needs the internet). |
| `the site maps under rendered/site/ still draw this trip, which is a draft: its line and title stay on the pages that show those maps (the home page, the Map page, an activity page) until python3 tools/render.py has been run and rendered/site/ committed` | a trip the region maps were drawn with has since become a draft. Those maps are on the home page, the Map page, the region pages (section 11) and the Ski page, and a build cannot redraw them (7.10); the message does not name the region pages. The same line reads `which has no track any more` after its `track.gpx` was deleted, and `which has no folder under content/trips any more` after its folder was removed; the file named is that trip's `index.md` even then. The build passes meanwhile. `--check` passes too for a report that only lost its `track.gpx`. For a draft or a removed trip that has a pin of its own on one of those maps it fails, with lines such as `BROKEN map/index.html -> ../trips/<slug>/` and `BROKEN regions/<region>/index.html -> ../../trips/<slug>/` (7.10) | Run `python3 tools/render.py` (needs the internet), then stage `rendered` as step 5 of [ADDING-TRIPS.md](../ADDING-TRIPS.md) gives for a run with no trip name. |
| `date 2026-09-04 is before the day ahead of it (days/01.md, 2026-09-05); days are shown in file order` | the file named is a `days/NN.md` whose date is earlier than the day before it | Fix the date. |
| `date 2026-09-20 is after the last day's date 2026-09-13 (days/02.md), so the page would end the trip before it starts` | `date:` in the `index.md` of a multi-day trip or a journal is later than the date of its last day file, and there is no `end_date:` line | Correct `date:`, or delete the line: the page then starts on the first day's date. |
| `date 2026-09-03 is after the trip's end_date 2026-09-02 (index.md), so the page's dates end before this day` | the file named is a `days/NN.md` dated later than the `end_date:` in the trip's `index.md` | Correct `end_date:`, or the day's date. |
| `holds a route and no recorded track (<trk>): "Download all GPX" leaves this day out` | the file named is a `days/NN.gpx` of a multi-day trip that holds a route (`<rte>`) and no recorded track, while another day's file has one. When no day has a track it is an error (5.2) | Replace the file with the day's recording. |
| `is not used: this trip has day files, and its page, maps and downloads come from days/NN.gpx; remove the file` | the file named is the `track.gpx` of a multi-day trip or a journal that has day files. No page shows it or links to it, but on a journal, and on a multi-day trip without any day track, the build still copies it to the site as `trips/<slug>/<slug>.gpx` | Remove the file. A recording that belongs to one of the days goes in `days/` as that day's `NN.gpx`. |
| `day label '1' is also the label of days/01.md; give each day its own day: line` | the file named is a `days/NN.md` of a multi-day trip whose day label an earlier day file already has. The label is the `day:` value, or the day's position when it has no such line. On the PCT a repeated label is an error (7.7) | Give the day its own `day:` value. |
| `same title and date as content/trips/<other-slug>/index.md ('Nowhere Loop', 2026-09-05): the two pages get the same <title>` | two published reports have the same `title:` and the same `date:`, for example one recording imported twice. The message names the other report | Delete the duplicate folder when the trip was imported twice. When the two are different outings the warning can stay: do not rename a trip to silence it (section 10). |
| `the file is missing, so the home page falls back to the newest featured report; create it to choose the featured trips (see docs/CONTENT_GUIDE.md)` | the file named is `content/home.json` | Restore it (section 1). |

A warning that is not in this table is written the same way: the line names the file and says what was found in it.
Those about a tick-list goal are in [TICK_LIST_GUIDE.md](TICK_LIST_GUIDE.md), section 9.

### 5.4 What `build.py --check` prints

After the content rules and the build, `--check` reads the built folder and prints one line per problem (the first 40,
then `... N more`). It ends with `link check: OK`, or with `link check: N problems` and exit status 1.

| Line starts with | What it means | What to do |
| --- | --- | --- |
| `BROKEN <page> -> <link>` | the page links to a file or a page that is not in the build | Fix the link in the write-up. `[the photo](photos/nope.webp)` in a trip's `index.md` gives `BROKEN trips/<slug>/index.html -> photos/nope.webp`. |
| `BROKEN ANCHOR <page> -> <link>` | the link reaches its page, but nothing there has the id after the `#` | Fix the part after the `#`. A PCT day is `#day-…` (7.7). |
| `DUPLICATE IDS <page>: …` | the page uses one id twice (the ids are listed) | See below. |
| `META <page>: …` | the page's head is wrong: its title, description, own address, share image or structured data | See below. |
| `SITEMAP sitemap.xml: …` | the sitemap leaves out a page, or lists something that is not one | See below. |
| `FEED feed.xml: …` | an RSS item points at a page that is not in the build | See below. |
| `INDEX trips/search.json: …` (or `trips/journal.json`) | the search data names a trip without a page, or a PCT day without its anchor | See below. |
| `GPX <file>: …` | a published GPX file is not, byte for byte, its source file in `content/`, or a multi-day trip's "Download all GPX" file does not hold its days' tracks as they are, holds no track at all, or is not well-formed XML | See below. |

The two `BROKEN` lines are the ones a write-up usually causes. A `BROKEN` line on `index.html`, `map/index.html`,
`regions/<region>/index.html` or `ski/index.html` that points at `trips/<slug>/` has another cause: the trip was made
a draft or deleted, and a region map still has a pin that links to its page. Run `python3 tools/render.py` (7.10). A
photo missing from `photos/`, a misspelt `kind:`, an iCloud conflict copy of a day file (`days/02 2.md` beside
`days/02.md`) and a multi-day trip whose day files all hold a route and no recorded track used to end here as well;
all four are now errors (5.2).

A write-up can cause `DUPLICATE IDS` too: raw HTML in it with an `id=` that the page already uses, such as `map`,
`stats`, `report`, `photos` or `title`. `<span id="map">` in a report's `index.md` gives
`DUPLICATE IDS trips/<slug>/index.html: map`, and `validate.py` does not catch it. Remove the `id`, or give it another
name.

So can a region written two ways. A `DUPLICATE IDS map/index.html: …` line that lists `region-<slug>`, or a
`DUPLICATE IDS ski/index.html: …` line whose ids carry a region's slug, means that two spellings of one region share
that slug, such as `Lake Tahoe` and `lake tahoe`. `validate.py` names the pair in a warning (5.3:
`region '…' is written '…' on N other trips; …`). Use one spelling on every trip and build again: the check then
passes without a render, except where each spelling had a region map of its own, which takes a render as well
(11.4).

One `GPX` line can still come from the content: a day's GPX of a multi-day trip whose track is not well-formed XML,
for example a track that uses a prefix such as `gpxtpx:` which the file's `<gpx>` tag does not declare. `validate.py`
does not read that far. The trip's "Download all GPX" file is made of the days' tracks, so it is broken in the same
way, and `--check` prints a line such as
`GPX trips/<slug>/<slug>.gpx: not well-formed XML (unbound prefix: line 4, column 90)`. Export that day's track again.

A second line about that file, `GPX trips/<slug>/<slug>.gpx: holds no track (no day file has a <trk>)`, is the check's
word for day files that hold routes only. A build stops at the error in 5.2 before it writes such a file; the line is
there for `validate.py --site DIR`, which checks a folder however it was built.

Apart from the track that is not well-formed, no content edit tried for this guide led to one of the last five lines
(`META`, `SITEMAP`, `FEED`, `INDEX`, `GPX`) in a fresh `build.py --check`. There they point at the generator
(`tools/sitegen/`, see [DEVELOPING.md](DEVELOPING.md)), not at a content file, and so does a `DUPLICATE IDS` line
whose ids are neither in a write-up nor those of a region written two ways: do not push. `validate.py --site _site`
prints them too when `_site` is older than the content, for example `GPX …: not the bytes of …` after a track changed
since the build; build again.

## 6. Search and the Trips page

`/trips/` lists every published report by year, with a search box and filters (activity, region, year, month, format,
has a write-up, has photos, sort, cards or list). The Month filter keeps a trip under every month it spans (the PCT
is under April to September); a journal day found by a search is listed under Month only for its own date's month,
and under Has photos only when that day has photos. The sorts are Newest first, Oldest first, Best match, Longest first
and Most gain; the last two list multi-day trips and the PCT by their totals, and a report without a distance (or a
gain) after the rest, as the line beside the heading says. The filters work on what is already on the page. On a phone
the region, year, month and format menus, the two boxes and the sort sit behind a **Filters** button, which shows how
many of them are on; the search box and the activity chips stay in view.

Every page's header has a search box too (in the menu on a phone) that opens the Trips page with the words, best match
first; on the Trips page itself the header keeps a Search link to the page's own box. The 404 page has one as well:
an old or mistyped report address (`/trips/half-dome-cables/`) fills it with the address's words and asks
`Looking for "half dome cables"?`. One- and two-digit numbers are left out (`/trips/tallac-2026-09-25/` asks for
`tallac 2026`), because the search knows a trip's year and month names but never the day of the month.

The search box looks in:

- the title;
- the place and the region;
- the activity, with its other forms: "backcountry ski", "skiing", "skied", "skimo", "touring"; "hiking", "hikes";
  "climbing", "climbed"; "mountain biking", "bikes", "rides", "cycling"; for Other, its type ("paddleboarding",
  "paddling", "SUP", "rafting", "kayaking", "mountaineering");
- the summits in `map: peaks:`;
- the dates: the year (both years when a trip ends in the next one) and the name of every month it spans, so
  `june 2024` finds the trips of June 2024. Never the day of the month: search by month and year. The words are not
  paired, so a trip from December 2023 to January 2024 is also found by `december 2024`;
- the route shape (`loop`, `out-and-back`, `point-to-point`) where the trip has one;
- the write-up: the report body, and every day's write-up on a multi-day trip or the PCT (the first 4,000 characters
  or so);
- `search_aliases` (below).

Every word typed has to be the start of a word somewhere in those: `tall` finds Tallac, and `skiing` finds every ski
report. A word is not found inside another one, so `horn` no longer finds the Matterhorn (type `matterhorn`, or add an
alias when people really type the short form). Case, accents and punctuation do not matter: `chamonix zermatt` finds
`Chamonix – Zermatt`. An apostrophe is not a word break: `lovers leap`, `lover's leap` and `lovers` all find Lover's
Leap, typed with a straight or a curly apostrophe. After a single letter it is one (`d'Argentière` reads as
`d argentiere`), so `argentiere` finds it. Not searched: party, beta rows, conditions, stats, photo captions. The
search data is a public file, `trips/search.json`, built from exactly those fields: no coordinates, no GPX, never a
draft.

When a search and the filters together find nothing, the empty state offers the nearest views that do, each with its
count: the search without the filters (`N reports match ‘<words>’ in all activities`, or `… without Region: <name>`,
or `… without the filters`, with the journal days it finds counted too: `1 journal day matches ‘whitney’ …`) and the filters without the search (`N climbing reports without the search`), beside Clear
filters. Each count is of the cards on the page, so a button never leads to an empty list; a count of nothing is not
offered.

**Aliases.** When people would type a name that is not in the title or place (an abbreviation, an older name, a
trail's nickname, a short form that is not the start of the name), add one line to the trip's `index.md`, among the front-matter lines above the closing `---`:

```yaml
search_aliases: [PCT, Pacific Crest]
```

- Square brackets, items separated by commas. Plain text needs no quotes: `[Mt. Tallac, Chamonix – Zermatt]` is fine.
- Wrap an item in double quotes when it contains a comma: `["Name, with a comma", Other Name]`. An apostrophe needs
  no quotes: `[Lover's Leap, Phantom Spires]` finds the same searches as `["Lover's Leap", Phantom Spires]`.
- Quote anything that is only digits: `["2024"]`. Bare digits read as a number, and a number stops the build.
- One alias can be written without brackets: `search_aliases: PCT`. A trailing comma (`[PCT, ]`) is ignored.
- The line goes in `index.md`, not in a `days/NN.md`. Leave it out when there are none.
- Aliases are only searched, never shown on any page.
- The title, place, region and `map: peaks:` are already searched, so there is no need to repeat them.
- A value that is not text or a list of text stops the build with a `content/trips/<slug>/index.md: …` message, like the
  other fields in section 5.2.

When a search matches only in the write-up, the card shows the words around the first hit instead of its opening
(and a day excerpt's DAY label is hidden); clearing the search restores the card. A region appears as a link in the
browse block (shown without JavaScript; with it the form's menus do the same): to its own page when it has one
(section 11), else to its list on the Map page. A region whose only reports are journals (the PCT's) is in neither the
browse block nor the Region menu, as the Map page leaves it out: the journal is found with Format: Series.

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
  is not searched.
- A day's date is searched as its month and day of the month: `may 22` finds the day of May 22, and `june 2024` every
  day of that June (the year is the journal's own word, so `2024` alone finds no day).
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

Three things on either layout follow from what the trip folder holds:

- A report whose `index.md` states `published_at` shows a `PUBLISHED …` line after the photos (section 8).
- A report without a `track.gpx` is a page of its words, its photos and whatever `stats:` its `index.md` states. It
  has no map section, no full-screen map page, no elevation profile or speed chart and no GPX download: no "View
  route" or "Download GPX" button, no Route link in the row of section links, no Map or GPX item in the bottom bar, and
  no bottom bar when fewer than two items would be left. Nothing is drawn in their place, and no card, list row or
  Newer / Older link shows a route drawing beside its name. The facts line that describes it in the RSS feed, and in a
  search result or a shared link when it has no write-up, does not end `with map and GPX`, and the note under its
  stats strip says nothing about a GPS recording. With no `stats:` block either, the page has no stats strip, Trip
  details is listed only when the trip has beta rows, and a beta row labelled Track stays in the Beta block (with a
  strip, the note under it prints that row instead). Such a report is never its section page's Featured trip, whatever
  its `featured:` line says (section 1). What deleting the `track.gpx` of a published report takes off the site, and
  what it leaves, is in 7.10.
- A report whose track `render.py` has not drawn yet keeps its map section, where a box says `Map not rendered yet. The
  GPX file is published: use the Download GPX button.` There is no key, no `As recorded on …` caption, no profile and
  no full-screen map page; "Download GPX" and, on a story page, "View route" (which leads to the box) still work. A
  multi-day trip in the same state shows the same box over its days (`... The GPX files of the days are published: use
  the Download all GPX button.`). `validate.py` and every build warn `no rendered map …` (5.3) until
  `python3 tools/render.py <slug>` has run (needs the internet).

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
PCT (section 9).

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
Older. The rule, in one sentence: other published reports of the same activity at the same place or of the same name
come first, then those that share this trip's region and its activity, then those that share only its region, then
those that share only its activity, and within each of those groups the report closest in date to this one comes
first, the newer one on a tie.

"The same place or name" is the same `place:` (spelled alike but for capitals), a summit both have in `map: peaks:`,
or a word both titles share that is the proper part of some place or summit name on the site: `tallac` (from
`place: Mount Tallac`) pairs two Tallac tours whatever else their titles say. The generic part of a name (`mount`,
`peak`, `ridge`, `lake`, `north` and the like), a word under five letters, and a word found in three or more different
place names never pair two titles.

There is nothing to configure.

- Never the report itself, a planned route or a draft, and no report twice. The two reports the page already links as
  Newer / Older are left out as well, so the block never repeats the links right under it. A multi-day trip or the PCT
  can be one of the cards.
- The line beside the heading states the rule: `SAME PLACE OR NAME AND ACTIVITY, THEN REGION AND ACTIVITY, THEN
  REGION, THEN ACTIVITY · NEAREST IN DATE`, or `SAME PLACE OR NAME AND ACTIVITY, THEN ACTIVITY · NEAREST IN DATE` on a
  trip with no `region:`. When the page has a Newer or an Older report it ends `· NEWER / OLDER
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
  field, already selected, to copy by hand. Escape, a second press of the button, a press anywhere else or moving on with the Tab key closes it.
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
- An address that names a hidden day's title or number, or a hidden month's heading (`#day-5-2-t`, `#day-5-2-n`,
  `#month-2024-07-h`), opens that day or month in the same way. No page links to these, but the public site has
  always had these ids, and there the day log opens on every day (the filter is off until a reader switches it on),
  so a saved link may name one.
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
  | `day: 5-2` when another day is `5.2` | `day: '5-2' gives the same page anchor (#day-5-2) as days/006.md; give each day its own label` |
  | no `day:` line, in a file whose position another day uses as its label | `no day: line, so this day takes its position, 151, and that gives the same page anchor (#day-151) as days/148.md; add a day: line with a label no other day has` |
  | `day: "5 n"` when another day is `5` | `day: '5 n' needs the page id #day-5-n, which days/005.md already uses; give each day its own label` |
  | `day: "?"` | `day: '?' has no letter or digit to make its page anchor from` |

The second row is the one to expect on the PCT. Its labels do not follow the file order (`days/148.md` is Day 151), and
`add_trip.py --day-of` writes a day file without a `day:` line. To add a day to the PCT:

1. `python3 tools/add_trip.py day.fit --day-of pacific-crest-trail-2024 --title "…"`. It ends by drawing the maps,
   which needs the internet; with `--no-render` it skips that, and `python3 tools/render.py pacific-crest-trail-2024`
   draws them later. It names the file it wrote (`days/151.md` for the next day) and notes that the other days carry
   a `day:` label.
2. Open that day file, not `index.md`. Add a `day:` line with a label no other day has, for example `day: "154"`, and
   write the entry under the closing `---`.
3. When the day is later than `end_date:` in the PCT's `index.md`, change `end_date:`. The date range on the page
   comes from that line, not from the day files, and `validate.py` warns while a day is dated after it (5.3).
4. Run the checks (section 5) and publish as in step 5 of [ADDING-TRIPS.md](../ADDING-TRIPS.md).

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

### 7.10 Taking a trip, or only its track, off the site

Three edits take a published report off the site, or part of it, at the next build:

- `draft: true` in its `index.md`: the build leaves out its page, its photos and its GPX downloads.
- Deleting its folder: the same. A run of `python3 tools/render.py` then removes its `rendered/trips/<slug>/` folder.
- Deleting only the `track.gpx` of a single-day report: the page stays, as a report without a track (7.2). Its map, its
  full-screen map page, its profile or speed chart, its GPX download and the route drawings other pages show beside
  its name all go. What `render.py` drew for it earlier is still in `rendered/trips/<slug>/`; the build neither shows
  nor copies any of it, and a run of `python3 tools/render.py` with no trip name, or with that trip's, removes the
  folder.

A draft or a deleted trip also leaves the lists and the counts of its region's page at that build, and the last
report out of a region takes the page with it (section 11). A report that only lost its `track.gpx` stays on that
page.

A build cannot take the trip off the region maps. The maps on the home page, the Map page, the region pages and the
Ski page are drawn by `render.py` and committed under `rendered/site/`, so they keep the trip's line and its title
until `python3 tools/render.py` has been run (needs the internet) and `rendered/site/` committed. Until then
`validate.py` and every build warn `the site maps under rendered/site/ still draw this trip, …` (5.3, which also says
what to stage). The build passes all the same. `--check` does not always. Where a draft or a deleted trip has a pin
of its own on one of those maps, the pin links to a page that is no longer built, and the check ends with lines such
as `BROKEN map/index.html -> ../trips/<slug>/`, the same for its region's page
(`BROKEN regions/<region>/index.html -> ../../trips/<slug>/`), and exit status 1. GitHub then publishes nothing, so
the page and its downloads stay online. Where the pin is merged with others, and for a report that only lost its
`track.gpx`, the check passes. It also passes when the trip was the last report of its region and no tick-list goal
is filed under the region: no page shows that region's map any more, unless it is one of the two on the home page
(11.4 has the other cases). So run `render.py` before the check, and stage `rendered` with the change.

That run can take more than the trip's line off the maps. It draws a region map only for a region with three trips
with a track, so a region that the change leaves with fewer gets no map, and without the map it has no page: its
remaining reports are listed on the Map page under "Not on a region map", and their links to the region lead there
(11.4). That holds for a report that only lost its `track.gpx` as well, because it no longer counts as one of the
three.

A report that something else names cannot be made a draft or deleted on its own. The build stops, so the site stays as
it was, until the other file is changed as well:

| The report is | The build stops with | Change |
| --- | --- | --- |
| in `featured_slugs` | `content/home.json: '<slug>' is a draft (draft: true in its index.md); drafts cannot be featured`, or after a deletion `content/home.json: unknown slug '<slug>' in featured_slugs (no content/trips/<slug>/index.md)` | Take the slug out of `content/home.json` (section 2). |
| linked from another report's write-up | `write-up link '../<slug>/' points at trips/<slug>/, a draft, which has no page`, or after a deletion `write-up link '../<slug>/' points at trips/<slug>/, which is not a page of the site (no content/trips/<slug>/index.md)`. The file named is the one that holds the link | Remove the link, or point it elsewhere. |
| named by an outing of a tick-list goal | `outing report_slug '<slug>' is not a published report`, with the goal's `goal.json` named | Change that outing ([TICK_LIST_GUIDE.md](TICK_LIST_GUIDE.md)). |

A multi-day trip or a journal keeps its map section even when none of its days has a GPX: the page then shows an empty
map and offers no downloads, and the warning `none of the N days has a GPX …` (5.3) says so.

None of this takes a file out of the repository or its history: [PRIVACY_NOTES.md](PRIVACY_NOTES.md), decision 3.

## 8. Publication dates: `published_at` and `updated_at`

Two optional lines in a report's `index.md`, among the front-matter lines above the closing `---`:

```yaml
published_at: 2026-10-03
updated_at: 2026-10-05
```

- `published_at` is the day the report first went online on this site. `updated_at` is the day its content last
  changed in a way a reader should know about. Both are yours to state: the build never fills them in, and no trip has
  them today.
- **Accepted forms.** A date, `2026-10-03`, or a date and time with an explicit offset: `2026-10-03T18:30:00-07:00` or
  `2026-10-03T18:30Z` (seconds are optional; the offset is `Z`, `+HH:MM` or `-HH:MM`, and no more than 14:00 either
  way). Only the digits 0 to 9 count as digits. Quotes around the value are optional. A line with nothing after the
  colon counts as absent.
- **Where.** The `index.md` of a single-day report, a multi-day trip or the PCT. In a `days/NN.md` the lines are not
  read, and the validator warns `unknown key 'published_at'; nothing reads it`. On a planned route they are an error.

**What they drive**

- One line near the end of the report: `PUBLISHED OCT 3, 2026`, or `PUBLISHED OCT 3, 2026 · UPDATED OCT 5, 2026` with
  both lines. It sits after the photos (after the last day on a multi-day trip) and above More like this, and on the
  PCT after the day log. It shows the calendar date as written, never a time.
- `article:published_time` and `article:modified_time` in the page's head, holding the value exactly as written.
- `datePublished` and `dateModified` in the page's structured data, when the page has any (section 9).

**What they are not**

- Not the trip date. `date:` and `end_date:` stay the days of the trip and drive what they always did: the order of
  every list, the dates on cards and pages, "As recorded on" (7.4) and the dates in the RSS feed. Neither new line
  reorders anything or changes the feed, the sitemap or the home page.
- Never guessed. Without the lines a page has no "Published" line and no `article:` tags, and its structured data
  carries no date. Leave them out when the day is not known; do not copy the trip date in.

**Rules.** Each of these stops the build. The message follows `content/trips/<slug>/index.md: `.

| In `index.md` | Message |
| --- | --- |
| `published_at: Oct 3, 2026`, or any other form, such as a time without an offset or a date typed in full-width digits | `published_at must be a date written YYYY-MM-DD, or a date and time with an offset such as 2026-10-03T18:30:00-07:00, got 'Oct 3, 2026'` |
| `published_at: 2026-02-30`, or an offset above 14:00 such as `+14:30` | `published_at '2026-02-30' is not a real date or time` |
| `published_at: 2026-12-01`, built on 2026-10-10 | `published_at 2026-12-01 is in the future` |
| `published_at: 2026-08-15` on a trip dated 2026-09-01 | `published_at 2026-08-15 is before the trip itself (2026-09-01); it is the day the report went online, not the trip date` |
| `updated_at:` with no `published_at:` | `updated_at needs published_at (the day the report first went online)` |
| `updated_at: 2026-09-05` with `published_at: 2026-09-10` | `updated_at 2026-09-05 is before published_at 2026-09-10` |
| either line on a planned route | `published_at is for a report; this is a planned route (kind: planned)` |

"In the future" means more than one day after the day of the build; a draft is not held to that rule until its
`draft: true` line goes, and every other rule applies to a draft as well. The trip's day is its first day: its `date:`,
or without that line the date of its first day file, and its `end_date:` only when it has no other date. So a
multi-day trip or the journal may state a day that falls during the trip, and stays valid when days are added later. A
trip with no date is not compared. `updated_at` is held to the same form and the same future rule, and its messages
start with `updated_at`.

A build is enough; no `render.py` run.

## 9. Share previews and structured data

What a link shows when it is pasted into a message or a post is read from the page's head: its title, its description
and one image. Nothing in this section needs a new field.

| Page | Share image |
| --- | --- |
| a trip's own page: a single-day report on either layout, a multi-day trip, the PCT, a goal page | the trip's cover (section 3), whether or not it leads the page; none when the trip has no photo |
| home | the lead card's cover: the first slug in `content/home.json` |
| an activity page (Ski, Climb, Hike, MTB, Other) | the cover of its Featured trip when that trip has a photo, else of the first trip on the page that has one |
| a region page (section 11) | the cover of the first report in its Featured row that has a photo, else of the newest report on the page that has one; when no report of the region has a photo, the image of the next row |
| About, Map, Trips, Tick list | they have no photo of their own, so: the cover of the first featured trip, the first slug in `content/home.json` |
| the 404 page and the full-screen map pages | none |

- The image is the cover's full file. Its size in pixels is published with it when the cover's entry has both `w` and
  `h`, and its `alt` text is published as the image's description when it is not empty. So complete the cover's entry
  under `photos:`: `w`, `h` and an `alt` that describes the picture.
- A page without a share image is shared as title and description only. The route tile is never a share image.
- With `{"featured_slugs": []}` the home page, About, Map, Trips and Tick list have none.
- A cover change needs a build, not a `render.py` run. To see what a page will share, build and read its head:

```bash
python3 tools/build.py --check
grep -o '<meta property="og:image[^>]*>' "_site/trips/<slug>/index.html"
```

**Structured data.** A report's page also carries one `BlogPosting` block, which search engines read, when both of
these hold:

- it is a published report: a single-day report, a multi-day trip or the PCT, never a planned route;
- its own write-ups come to at least 100 characters of plain text, counting the text under the front matter of
  `index.md` and of every `days/NN.md` together.

A track-only report, or one with a caption-length note, gets none. The block holds the title as written, the page's
address and description, the language (`en`), the author (Eric Sichak, linked to the About page), the cover with its
size in pixels (left out when the cover's entry has no `w` and `h`), and `datePublished` / `dateModified` only when
the lines of section 8 are set. It holds no rating, and never the trip date as a publication date. There is nothing to
set, and `build.py --check` verifies the block on every page that has one (the `META` lines in 5.4).

## 10. What not to do

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
- Do not set `published_at` or `updated_at` from the trip date, a file's date or a guess. When the day a report went
  online is not known, leave both lines out (section 8).
- Do not edit `_site/` by hand. It is rebuilt from `content/`, `rendered/` and `assets/` on every build and on
  every push to `main`.
- Do not `git add -A` or `git add .`. Stage only what you changed, by path, and read `git status --short` before
  committing: every line with a letter in its first column is in the commit. `.gitignore` hides the iCloud conflict
  copies under `rendered/` and `assets/` (names that end in a space and a number, such as `meta 3.json` and
  `map-wide 4.webp`), but a copy anywhere else, such as `content/trips/<slug>/index 2.md`, is not hidden, and a folder
  path or a blanket add takes it along; `validate.py` names a copy that sits in a trip folder (5.2, 5.3). When one is
  staged, `git restore --staged "<path>"` and delete the file. The whole publishing step, with the paths for a new
  trip and for a render, is step 5 of [ADDING-TRIPS.md](../ADDING-TRIPS.md).

```bash
git add content/home.json "content/trips/matterhorn-peak-west-couloir/index.md"
git status --short
git commit -m "Feature Matterhorn and set its cover"
git push                                    # GitHub publishes pushes to main only (section 5)
```

When highlights or the PCT cover change, the PCT's `index.md` is the path:

```bash
git add "content/trips/pacific-crest-trail-2024/index.md"
git commit -m "List the PCT highlights" && git push
```

A new card-size copy (section 3) is a new file, so it is added by path as well, with the `index.md` that names the
cover:

```bash
git add "content/trips/<slug>/index.md" "content/trips/<slug>/photos/03.th.webp"
git status --short
git commit -m "Change the cover of <trip>" && git push
```

## 11. Region pages

A region that has a region map and at least one published report has a page of its own at `regions/<slug>/`. The
slug is made from the region's name, and it is the same one as in `map/#region-<slug>`: the name in lower case, with
accents folded to plain letters and apostrophes dropped; a character with no plain-letter form (an en dash, `ø`, a
letter of another script) is dropped as well; every run of what is then neither a letter nor a digit becomes one
hyphen, and hyphens at the two ends are removed. Lake Tahoe is `regions/lake-tahoe/`, and a region named
`Val d'Isère` would be `regions/val-disere/`. Two names that come out the same share one slug (11.4): `Lake Tahoe` and
`lake tahoe`, or `St. Moritz` and `St Moritz`. Eight regions have a page today: Lake Tahoe, Santa Cruz, Eastern Sierra, Bay Area, Boise, Alps,
Tetons and Oregon. There is no `regions/` page that lists them: the Map page is their parent, and every region page
links to the others.

Nothing is written for a region. The page has no file in `content/` and no text of its own. Everything on it is
counted or copied from its trips (`region:`, `place:`, `date:` and `end_date:`, `featured:`, the titles, write-ups and
covers), and its map is the region map `render.py` drew.

### 11.1 Which regions get a page, and which trips are on it

Two things make a page, and they come from different places.

- **Whether a region has a page** comes from the region maps. `tools/render.py` draws a region map once a region has
  three trips with a track (an active tick-list goal with a route counts as one; a journal and a report without a
  track do not) and records the region in `rendered/site/meta.json`. While that file lists the region with a map,
  every build makes the page, as long as at least one report is filed under the region: planned routes alone do not
  make one. The published site has it once `rendered/site/` is committed and pushed.
- **Which trips are on the page** comes from `content/` alone, at every build: every report and every active
  tick-list goal whose `region:` is the region's name, letter for letter. A multi-day trip, a journal filed under the
  region, a report without a track and a report added since the maps were last drawn are all on it. So, for a region
  that is written one way on every trip, the page counts the reports the Trips page counts for it under "By region".
  A region written two ways is the exception: the Trips page counts both spellings in one link, and the page lists
  only the trips that spell the region as it does (11.4).

The map on the page is not made from that list. It is the picture `render.py` last drew, so a new report's line and
pin appear on it after the next render, exactly as on the Map page. The Map page's own list for a region still names
the trips its map was drawn with. So that list has no report without a track and no journal filed under the region,
and between an edit and the next render it can differ from the region's page in other trips as well. (A journal's
days that lie in the region are another matter: 11.7.)

- A region without a region map has no page. It is where it has always been: in the Map page's "Not on a region map"
  list, at `map/#region-<slug>`. Utah, Arizona, Idaho, Minnesota, Washington and Yosemite are there today. A new
  region is listed there once the command of the `region '…' is not in rendered/site/meta.json …` warning has been
  run (5.3).
- The PCT's region, Pacific Crest Trail, has no region map, because a journal as a whole is drawn on none. So it has
  no page. The days of the journal that lie in another region can be drawn on that region's map (11.7).

### 11.2 What the page shows

In this order:

1. **The head.** `Reports / Map / <Region>`, the region's name, and one line of counts and years:
   `86 REPORTS · INCL. 8 MULTI-DAY · + 1 PLANNED ROUTE · 2022–2026` on Lake Tahoe's page today. The years run from the
   earliest to the latest `date:` or `end_date:` of the reports, and one year is written once. A second line names
   the places in capitals: each `place:` the reports state, the one on the most reports first and equal ones A to Z.
   Two spellings that read the same in capitals (`Mount Rose` and `Mount rose`) are one place, and their reports are
   counted together. Up to four are all named; with more, the first three and `N MORE`:
   `TAHOMA · EMERALD BAY · KINGSBURY · 7 MORE` on Lake Tahoe's page today. A place too long for the line wraps at
   its spaces, and a single word too long for a line is broken across lines. A region whose reports state no place
   has no second line. That is all the introduction the page has.
2. **The map**, with its caption and legend as on the Map page, and beside it the list the Map page has for a region:
   "In this region", the counts again, and one row for every report and planned route of the page, newest first, the
   planned routes last. The legend is the key to the map, not to the list: it names the activities of the reports the
   map draws, and shows the planned-route line only when the map draws one. A report without a track, or a trip added
   since the maps were last drawn, is in the list and adds nothing to the legend. (Only when none of the trips the
   map draws is on the site any more is the legend made from the list.) Pointing at the row of a trip that is not on the map
   leaves the map as it is; the row of a trip on the map picks out that trip's line and pin. A list of more than nine
   rows shows its first eight with "Show all N" under them, N being the number of reports; pressed, the button shows
   the rest and reads "Show fewer", and pressed again it folds the list back to eight rows.
3. **Featured**: up to three cards (11.3).
4. **All reports**: every report of the region by year, as in the Map page's table, with the activity filter when
   the reports are of more than one activity, and the region's planned routes under "Planned". Under the table,
   "Search and filter these in Trips" opens the Trips page with the region chosen.
5. **Other regions**: a link to each other region page with its number of reports, then "Map & archive". The block is
   left out when no other region has a page.

With JavaScript off, the two links into the Trips page ("Search and filter these in Trips" and the one under the
Featured cards) are not shown, because the Trips page applies its filters with a script. The activity filter and the
"Show all N" button are not shown either: the table lists every report, and the list beside the map every row.

### 11.3 The Featured row

No list picks it. The row takes up to three of the region's reports, in this order:

1. reports with `featured: true` in their `index.md`. It is the line that makes a single-day trip with a track
   eligible for the Featured block of its activity page (section 1); here it counts on every kind of report: a
   multi-day trip, a journal and a report without a track as well;
2. reports whose write-ups come to at least 100 characters (the measure section 9 gives for structured data) and that
   have a photo;
3. reports with such a write-up and no photo.

Within each step the newest comes first, and the row stops at three cards. So:

- A flagged report is ahead of every unflagged one. The flag does not put it first in the row: flagged reports are in
  date order among themselves, and of more than three only the three newest are shown. A fourth flagged report is
  not in the row.
- Among unflagged reports, one with a photo is ahead of one without, whatever their dates. A region without a flag
  shows its newest written reports that have a photo, and one without a photo only when fewer than three have one.

A report with neither the flag nor such a write-up is never in the row, a planned route never is, and a region with no
candidate has no Featured section (Tetons and Oregon today). Each card carries the trip's summary (section 4).

To put a report ahead of the unflagged ones, add `featured: true` to its `index.md`; to take it out of the first step,
remove the line. A build is enough.

"All N write-ups in Trips" under the cards opens the Trips page with the region and "Has a write-up" chosen. N is the
number of the region's reports with a write-up of any length, and the link is there when N is two or more. It is part
of the Featured section, so a region without a Featured row has no such link, however many short write-ups it has.

### 11.4 When a page changes

The lists and the counts of a region page follow `content/` at every build. Its map, and whether the region has a
page at all, follow `rendered/site/meta.json`, which only `render.py` rewrites (11.1). So:

- **A new report** is on its region's page at the next build: in the counts, in the list beside the map, in the
  table and, when it qualifies, in the Featured row. That holds for a trip added with `--no-render` too. Its line and
  pin are on the page's map once the region maps have been drawn again and `rendered/site/` is pushed with the trip
  (step 5 of [ADDING-TRIPS.md](../ADDING-TRIPS.md)). Until then the Map page's list for the region does not name it.
- **A draft or a deleted trip** leaves the page's lists and counts at the next build, with no render. Its line stays
  on the map until `python3 tools/render.py` has run, exactly as on the Map page, and `--check` fails meanwhile when
  the trip has a pin of its own there (7.10).
- **The last report out of a region** takes the page with it at the next build, whatever its map still draws. The
  Map page keeps or drops its panel for the region by its own rule: it lists the trips the map was last drawn with
  that are still on the site. So until the maps have been drawn again the two can differ:
  - Reports that were *moved* to another region are still in the Map page's panel for the old one, the home page's
    `ALSO` row still names it, and `build.py --check` passes.
  - When the reports were *drafted or deleted* and nothing the map draws is left on the site, the panel goes as
    well, and with it the region's item in the `ALSO` row. The check then passes unless a page still links to the
    panel's address: a tick-list goal that is filed under the region and is not on its map, or the home page when
    the region is one of the two whose maps it shows (Lake Tahoe and Eastern Sierra). The check names the page:
    `BROKEN ANCHOR <page> -> …map/#region-<slug>`. `validate.py` goes on warning
    `the site maps under rendered/site/ still draw this trip, …` (5.3) either way.
  - A tick-list goal that the map draws keeps the panel, which then lists the goal alone. A drafted or deleted
    trip's own pin on that map fails the check there as it does anywhere else (7.10).

  `python3 tools/render.py` (needs the internet), with `rendered` staged afterwards, brings the maps and the lists
  back in step in each case.
- **A region that falls under three trips with a track** keeps its page until the maps are drawn again. That run
  draws no map for it, so the page goes, a saved link to it no longer finds it, and the region is back in the Map
  page's "Not on a region map" list.
- **A report without a track** is on its region's page like any other: in the counts, the list and the table. It has
  no line on the map, and the page's description no longer promises a GPX track for every report (11.6). After the
  `track.gpx` of a report is deleted, the map keeps its line until the next render (7.10).
- **A report moved to another region** leaves the old region's page at the next build and is on the new region's
  page at once, when that region has one. The two maps, and the Map page's two lists, follow with the next render.
- **Another spelling is another region.** A report filed under `Lake Taho` leaves Lake Tahoe's page at the next build
  and is on no region page. Its breadcrumb has no region link, the Trips page lists `Lake Taho` as a region of its
  own, and `validate.py` gives the `region 'Lake Taho' is not in rendered/site/meta.json …` warning (5.3). Correct the
  spelling: left as it is, a spelling gets a map and a page of its own only with three trips with a track. A spelling
  that comes out as the same slug (`lake tahoe`; the rule is at the top of this section) is still another region.
  That report is not on the page either, and its breadcrumb leads to `map/#region-lake-tahoe`. The Trips page counts
  both spellings in one "By region" link, which takes the spelling of the newest report and leads to the region's page
  only when that spelling is the page's. `validate.py` gives two warnings for such a report (5.3): the one above,
  which asks for a render, and `region 'lake tahoe' is written 'Lake Tahoe' on N other trips; …`. Do not run that
  render for a second spelling. Once the maps know both spellings, the Map page has two blocks with one address and
  `build.py --check` fails with a `DUPLICATE IDS map/index.html: …` line that lists ids of the region,
  `region-lake-tahoe` among them. When ski reports are filed under both spellings and the region has a map on the Ski
  page, that page fails in the same way, with a `DUPLICATE IDS ski/index.html: …` line, even before a render. GitHub
  publishes nothing while the check fails. These lines do not point at the generator (5.4): the fix is one spelling
  on every trip. The check then passes at the next build, with no render, and the report is on the region's page.
  Only where each spelling had a region map of its own when the maps were drawn does it take a render as well.
- **A renamed region.** The page's address is made from the name (the rule is at the top of this section), and
  nothing redirects an old address. Change `region:` on every trip of the region. At the next build the old name's
  page is gone, because the page lists by the exact name and no report is filed under that name any more, and the
  reports are on no region page. `validate.py` gives the warning of 5.3, which names one trip and counts the rest:
  `region '<new name>' (and 4 more trips) is not in rendered/site/meta.json, …`. The build and `build.py --check`
  pass on this site (the home page's "N more regions" link needs the Map page's "Not on a region map" block, which
  the PCT journal and the regions without a map keep there). What the site shows meanwhile, and what the render brings back, depend on whether the address changes:
  - *The new name gives a new slug* (`Bay Area` to `East Bay`). The new name has no region map yet. Meanwhile the Map
    page still shows the region under its old name, with the trips its map was drawn with, and the home page's `ALSO`
    row still names it so; the renamed reports have no region link in their breadcrumb; and the Trips page links
    the new name to its own filter. Run the command the warning gives and commit `rendered/site/`. A new name with
    three trips with a track then has a region map, and with it a page at the address made from the new name.
    Nothing is left at the old address, neither a page nor a redirect, so a saved link to `regions/<old-slug>/` or to
    `map/#region-<old-slug>` no longer finds the region.
  - *The new name gives the same slug*: only capitals, an apostrophe, a hyphen or an accent change (`Bay Area` to
    `Bay area`). Meanwhile the breadcrumbs of the renamed reports and the Trips page's "By region" link lead to
    `map/#region-<slug>`, where the Map page still shows the region under its old spelling, as the home page's `ALSO`
    row does. Run the command the warning gives and commit `rendered/site/`. The page is then back at the address it
    had, under the new spelling, so a saved link to `regions/<slug>/` finds the region again; `map/#region-<slug>`
    never stopped working.

  The home page's two region maps are named in the generator (`HOME_REGIONS` in `tools/sitegen/pages/home.py`: Lake
  Tahoe and Eastern Sierra), so renaming one of those takes an edit there too. Without it, after a rename that
  changes the slug, the home page keeps the map under the old name, which is no longer a link, until the maps are
  drawn again, and shows no map for the region from then on. After a rename that keeps the slug, the home page goes
  on showing the map, before and after the render, under the old spelling and without a link on the name, and once
  the maps are drawn again the `ALSO` row names the region a second time, in the new spelling.

### 11.5 Links to a region page

Where a region has a page, these lead to it and no longer to the Map page:

- the region at the end of a breadcrumb, on a single-day report, a multi-day trip, a journal and a tick-list goal;
- the "By region" links on the Trips page;
- the regions in the home page's `ALSO` row (the row names a region that has a region map only while it has a page
  or the Map page has a panel for it, 11.4);
- the names over the home page's two region maps ("Open the map" beside each still opens the Map page).

Two links read "All <Region> reports": a new one under each region's list on the Map page, and the link at the foot
of a tick-list goal's page, which read "Open the map" before. A region page carries no such link to itself. A region
without a page keeps the links it had, to `map/#region-<slug>`, and every `map/#region-<slug>` address still lands on
the Map page as before. Each link goes by the region as the trip spells it, so a trip filed under another spelling
keeps the link it had (11.4).

### 11.6 Description, share image and preview

The page's description, for search results and shared links, is one sentence made of the same counts. Today the
Tetons page has
`Tetons: 4 trip reports, 2026 (backcountry ski), with a map of the region and the full GPX track of each.` The end
depends on the tracks. When every report of the region has one, it is as above, or
`, with a map of the region and its full GPX track.` for a region with a single report. As soon as one report has no
track, the sentence ends `, with a map of the region.` and promises no file. It never says that every report is on
the map. The page's share image is in the table of section 9. The page is in the sitemap; it is not in the RSS feed
or in the Trips page's search.

Preview with `python3 tools/build.py --serve` and open http://localhost:8000/regions/lake-tahoe/. A build is enough
for everything the page lists: a new report, a draft, a changed `region:`, `featured:`, `place:`, date or write-up.
`render.py` (internet needed) and a commit of `rendered/site/` are needed for what the map draws, for a new region to
get its map and with it its page, and for a renamed region to get them back. A region page has no files of its own,
so there is nothing else to stage for it.

### 11.7 A journal's days on a region map: `region_days`

The PCT journal is one trip filed under a region of its own, so no region map drew any of it, although it walks
through Lake Tahoe and the Sierra. The `region_days` block in the journal's `index.md` says which of its days lie in
which region:

```yaml
region_days:
  Lake Tahoe:
    Pacific Crest Trail: 67-69, 72-74, 76
    Tahoe Rim Trail: 146/2, 147-153
  Eastern Sierra:
    Pacific Crest Trail: 58-65
```

- **A region holds its days, or named parts.** The short form is the region and its days on one line
  (`Eastern Sierra: 58-65`); the days are then one part, called by the journal's title. The form above gives each
  part a name of its own. A part is one thing on the page: its days are one line on the map (one link, one
  highlight) and one row in the region's list, and the two are tied together. Name a part when the days are a hike
  a reader would look for by name (the Tahoe Rim Trail), or when one region holds two different walks.
- **A day is named by the number the journal page shows** (Day 148), not by its file name. `147-153` is every day
  from 147 to 153 that the journal has; single days and ranges are separated by commas. A day may be listed under
  two regions.
- **One stretch of a day: `146/2`.** A day that was recorded in two places, with a drive in between, falls into
  stretches: one ends and the next begins wherever two recorded points lie more than 20 km apart. `146/2` is the
  second stretch of day 146 (Day 146 finishes a section of the PCT in the morning and starts the Tahoe Rim Trail in
  the afternoon; the Tahoe Rim Trail takes the afternoon). Stretches are counted from 1 in the order recorded. The
  part then takes that stretch alone: on the map, for its pin, in its small drawing and in its distance, which for
  that day is the length of the stretch measured along its track (the day's own figure is for the whole day). The day
  still counts as one of the part's journal days, with its date. A lost signal of a few kilometres is not a split,
  and the site never draws a line across a gap in a recording, so a day needs this only when one of its stretches
  does not belong to the part. A stretch the recording does not have stops the build (5.2).
- **List the days of the route, not every day in between.** Every listed day is drawn in the route's line, picked out
  with it and counted in its row, whatever was recorded that day. A day off the trail (a walk on a rest day, a ride
  in town) is a day of the journal and not of the route: leave it out, as days 70, 71 and 75 are above, and the
  line is the trail alone. The route is still one walk: the days after such a gap go on from where the days before
  it stopped.
- **The region is spelled as the reports spell it**, letter for letter. A name no report is filed under stops the
  build with a message that suggests the nearest one (5.2).
- **On the map**, each listed day that has a GPX is drawn in the journal's activity colour, where it crosses the map.
  The map keeps its frame: it is fitted to the region's own reports, and a day that runs past its edge is cut off
  there. So list every day that crosses the map, the first and the last included, and the line runs from edge to
  edge (Lake Tahoe above: days 67 and 76 are the ones that come in at the bottom and leave at the top). A pin marks a
  start: an unbroken run of days that starts inside the region gets one, at its start, and it opens the journal at
  that day (the Tahoe Rim Trail, at the start of its stretch of Day 146). A run that walks in from outside, as the
  PCT does, has a line and no pin. Days left out in between do not make a new start: a day that begins within 5 km
  of where the part's last listed day ended goes on with the same run (Day 72 after Day 69), and gets no pin.
- **The line itself is a link.** A part's line answers the pointer as a report's pin does: pointing at it (or
  reaching it with Tab) picks out all of the part's days, dims the rest, marks the part's row in the list and shows
  its name ("Tahoe Rim Trail: Pacific Crest Trail 2024, Day 146 to Day 153"); a click or tap opens the journal at the
  part's first day. Where a pin or a numbered marker lies on the line, that marker answers first, and where two
  parts share a trail the one written later in the block does.
- **In the region's list**, on the Map page and on the region's page, each part has one row: its name, the dates of
  its first and last day, the number of journal days and the distance they add up to (whole days, also where a day
  leaves the map), with a small drawing of the part's own days. The rows stand after the region's reports and are
  always shown, also while the list is folded behind "Show all". A row opens the journal at the part's first day,
  and pointing at it picks out the part's line on the map. It is not a report of the region: no count includes it,
  and it is not in the table of reports.
- **It needs a render.** After changing the block (days, a part's name, or the order), run
  `python3 tools/render.py --site` (internet needed) and commit `rendered/site/` with `index.md`, the new
  `*-g64.svg.html` drawings included. Until then the rows are there and the map shows what it was last drawn with;
  `validate.py` says so (5.3). A region without a region map shows the days on no map.
