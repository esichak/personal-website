# Content guide: homepage features, covers and summaries

How to choose what the homepage shows, which photo fronts a trip's card, and what the card says. All of it is
done by editing two kinds of file (`content/home.json` and a trip's `index.md`) and running two commands. No
Python edit is needed to feature, reorder or re-cover a trip.

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
  on that trip's section page (Ski, Climb, …; single-day trips only, so the flag on a multi-day trip or the PCT does
  nothing), but it no longer has any say over the homepage.
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

**Remove:** delete the slug from the array. The trip stays on its section page and in Recent outings if it is
recent enough; only the homepage feature goes.

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

1. the first landscape photo (width ≥ height) declared in `index.md`;
2. else the first photo declared in `index.md`;
3. else, for multi-day trips and series, the first landscape day photo (days in order), else the first photo of
   the first day that has photos;
4. else the route tile;
5. else a plain card with no image.

An automatic pick is a fallback, not an editorial choice: it is simply the first file that fits. For anything on
the homepage, look at the photos and set `cover_photo`.

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

A `content/trips/<slug>/index.md: front matter: …` (or `…/days/NN.md: front matter: …`) message is a syntax
problem in that file's front matter: an unclosed `---`, or a value that starts with a double quote but is not one
complete quoted string.

## 6. What not to do

- Do not invent summary copy, captions or stats. If a sentence cannot be checked against the report, leave
  `card_summary` out; the fallbacks in section 4 are built from the data and are truthful.
- Do not present the PCT as one day's story. The series card shows no sentence: its DATE · PLACE line and its
  RECORDED DAYS · MI RECORDED line carry the facts; a day's prose belongs on that day's page.
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
