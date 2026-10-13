# Eric Sichak — Trip Reports

Trip reports with GPX maps: backcountry skiing, climbing, hiking, mountain biking and other trips (paddleboarding,
rafting, kayaking, mountaineering). Live at **https://esichak.github.io/personal-website/**.

Every report is a folder in `content/trips/` with a Markdown write-up and the recorded track. Maps, elevation
profiles and track glyphs are rendered on your Mac from real terrain (AWS Terrain Tiles) and OpenStreetMap data, then
committed; GitHub Actions never renders: on every push to `main` it runs the tests, assembles the pages and publishes
them. Everything is Python 3 standard library, with nothing to install except the tools macOS already has (plus
`cwebp` from Homebrew for photos: `brew install webp`).

## Add a trip

Step-by-step guide: **[ADDING-TRIPS.md](ADDING-TRIPS.md)**. The short version:

```bash
# from a Garmin (or any) FIT/GPX file, with photos
python3 tools/add_trip.py ~/Downloads/Morning_Ski.fit --title "Rose Knob Peak" --activity ski \
    --place "Mount Rose" --region "Lake Tahoe" --party "Adam" --photos ~/Desktop/rose/

# or straight from a Strava bulk export (title, stats, description and photos come along)
python3 tools/add_trip.py --strava-export "/path/to/Strava export folder" --strava-id "<activity id>"

# the next day of a trip whose index.md says kind: multi-day (starting one, and the end_date: line to change
# afterwards: ADDING-TRIPS.md)
python3 tools/add_trip.py day3.fit --day-of chamonix-zermatt-haute-route --title "Le Châble → Cabane de Prafleuri"
```

`--activity` is one of `ski`, `climb`, `hike`, `mtb`, `other` (use `--subtype SUP|Rafting|Kayaking|Mountaineering`
with `other`). The script creates `content/trips/<slug>/` and renders its maps, which needs the internet
(`--no-render` skips that; run `python3 tools/render.py <slug>` later). Then:

1. Edit `content/trips/<slug>/index.md`: write the report under the front matter (Markdown), check `place`,
   `region`, `party`, add `beta:` rows, and give every photo an `alt:` description.
2. Preview: `python3 tools/build.py --serve` and open http://localhost:8000 (the new report is also on http://localhost:8000/trips/).
   The build checks the content first and stops with `ERROR` lines that name the file.
3. Publish, staging by path. First check, stage and list:

   ```bash
   python3 tools/build.py --check
   git add "content/trips/<slug>" "rendered/trips/<slug>" rendered/site
   git status --short
   ```

   Read what these printed: the commands run one after the other whatever each one answers. Go on only when the
   check ended with `link check: OK` and every staged name is a file of this trip or a map under `rendered/site/`.
   A `WARNING` line that says `no rendered map` for the trip means its maps were not drawn: run
   `python3 tools/render.py <slug>` first. Then:

   ```bash
   git commit -m "Add <trip>" && git push
   ```

   `rendered/site` holds the region maps, which a render redraws too. Never `git add -A` or `git add .`: iCloud Drive
   leaves conflict copies in this folder (`meta 3.json`, `index 2.md`). `.gitignore` hides the ones under `rendered/`
   and `assets/`, and the content check names one inside a trip's folder, but a copy can appear anywhere, which is
   why the list is read before the commit (ADDING-TRIPS.md, step 5, says what to do with one). Only a push to `main`
   is published: GitHub runs the unit tests and `build.py --check`, and the site updates a few minutes later. A push to
   any other branch runs nothing, and on a branch that was never pushed `git push` stops with
   `fatal: The current branch <name> has no upstream branch`. `git branch --show-current` names the branch you are on.

Useful front-matter fields (see any existing trip for the format):

| Field | Meaning |
| --- | --- |
| `title`, `activity`, `subtype`, `date`, `start_time`, `timezone` | Basics (filled in by `add_trip.py`; for a multi-day trip you write `title` and `activity` yourself, see ADDING-TRIPS.md) |
| `place`, `region`, `party` | "Sawtooth Ridge", "Eastern Sierra", "Adam". `region` groups trips on the map page and is a filter on the Trips page. A region that has a region map and at least one published report also has a page of its own, `regions/<slug>/`. The slug is the name in lower case, with accents folded to plain letters, apostrophes and characters that have no plain-letter form dropped, and every run of what is then neither a letter nor a digit turned into one hyphen (none at the ends): `Eastern Sierra` gives `regions/eastern-sierra/`, and `Val d'Isère` would give `regions/val-disere/`. Nothing is written for the page, and it lists every report and active tick-list goal whose `region` is exactly that name, from the next build on; its map shows a new trip once the region maps have been drawn again (`docs/CONTENT_GUIDE.md`, section 11) |
| `route_shape` | `loop`, `out-and-back` or `point-to-point` (detected from the track) |
| `stats` | `distance_km`, `moving`, `elapsed`, `gain_m`, `loss_m`, `high_m`, `low_m` (Strava's numbers, or computed) |
| `featured: true` | Eligible for the section pages' "Featured" block (single-day trips with a track only; the home page is picked in `content/home.json`, see below). On its region's page the same line counts for a report of any kind, with or without a track: the Featured row there holds three cards, and flagged reports come before unflagged ones, the newest flagged first, so a fourth flagged report is not shown (`docs/CONTENT_GUIDE.md`, 11.3) |
| `cover_photo`, `cover_focal_x`, `cover_focal_y` | The photo the trip's cards and its page's share image use (a path declared under `photos`), and where to keep in the crop, 0–100 (default 50/50). It is also the lead photo of a single-day report with a write-up, or of the PCT page, when it is at least 6:5 wide; a portrait or a square does not lead, and multi-day trips have no lead photo. After changing `cover_photo`, run `python3 tools/thumbs.py <slug>` and commit the `.th` file it writes: the small copy the cards load |
| `card_summary` | Optional one- or two-sentence factual summary for the trip's cards: the home page's feature card and its card on the Trips page (the report's opening is used when it is absent) |
| `search_aliases` | Other names people might search for, as an inline list (`[PCT, Pacific Crest]`); searched on the Trips page, never shown |
| `region_days` | PCT only: which days of the journal lie in which region, by the day numbers the page shows, so that region's map draws them and its list names them. A region's days can be named parts (`Lake Tahoe:` with `Pacific Crest Trail: 67-76` and `Tahoe Rim Trail: 147-153` under it): each part is one line on the map and one row in the list; needs `render.py --site`. See `docs/CONTENT_GUIDE.md`, 11.7 |
| `journal_highlights` | PCT only: the entries the journal points to, as an inline list of day-file ids (`[001, 059]`), in display order; absent means no Highlights section |
| `published_at`, `updated_at` | Optional publication dates; see `docs/CONTENT_GUIDE.md` |
| `draft: true` | Keep it off the site (once pushed, its files are still in the public repository). `render.py` leaves drafts out, so run `python3 tools/render.py <slug>` after removing the line. For a trip that is already published the line is not enough: the region maps still draw the trip, and `build.py --check` can fail on them, until `render.py` is run again (ADDING-TRIPS.md, "Taking a trip off the site") |
| `kind: multi-day`, `end_date` | A trip of several days, each a `days/NN.md` with its `NN.gpx` (see ADDING-TRIPS.md). `date` and `end_date` are its first and last day; when absent they come from the day files. `kind: series` is the PCT journal |
| `kind: planned` | A tick-list goal, not a report: planned route, approximate stats, `goal.json` beside it (see `docs/TICK_LIST_GUIDE.md`) |
| `beta` | List of `label` / `value` rows shown beside the report |
| `map` | `peaks: [Mount Tallac]` to label summits (also searchable on the Trips page), `places: [...]`, `water_labels: [{text, x, y}]` |
| `photos` | `file`, `w`, `h`, `alt`, optional `caption` |

## Feature a trip on the home page

`content/home.json` lists the featured trips, in order (the first is the lead card; up to six):

```json
{"featured_slugs": ["pacific-crest-trail-2024", "matterhorn-peak-west-couloir", "peak-bagging-szn"]}
```

Edit the list to feature, reorder or remove trips; nothing else decides it. Covers and summaries are front-matter
fields on the trip (`cover_photo`, `cover_focal_x`/`cover_focal_y`, `card_summary`). The build stops with a clear
message when a slug is unknown, a draft, a planned route or listed twice. Details: **[docs/CONTENT_GUIDE.md](docs/CONTENT_GUIDE.md)**.

## Keep a tick list of future goals

Future routes live beside the reports as `kind: planned` trips with an optional `goal.json`, shown at
https://esichak.github.io/personal-website/tick-list/. Save one locally (a name and an activity are enough; a GPX is
optional and is copied into the public checkout only with `--publish-track`), review it, then publish through git:

```bash
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity hike --gpx ~/Downloads/route.gpx --dry-run
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity hike --gpx ~/Downloads/route.gpx --publish-track
python3 tools/ticklist.py update your-route-name --status shortlisted --priority high
python3 tools/ticklist.py log-outing your-route-name --outcome completed --report-slug an-existing-report
```

New goals are drafts until you remove `draft: true`. With `--publish-track` the command also starts `render.py`
(`--no-render` skips that), but `render.py` leaves drafts out, so it draws no map for the new goal. After you remove
`draft: true`, run `python3 tools/render.py your-route-name` (needs the internet) to draw it. The full workflow, every
field and the research prompt are in **[docs/TICK_LIST_GUIDE.md](docs/TICK_LIST_GUIDE.md)**.

## Check, build and re-render

```bash
python3 tools/validate.py            # check content/ without building: ERROR and WARNING lines, then a summary
python3 tools/build.py --check       # validate the content, build _site/, then check the built site
python3 tools/thumbs.py              # make the card-size (.th) copies of cover photos that are missing (needs cwebp)
python3 tools/render.py              # render anything whose track or map settings changed (needs internet)
python3 tools/render.py --charts     # only elevation profiles (fast, offline)
python3 -m unittest discover -s tests   # the generator's unit tests (see docs/DEVELOPING.md)
```

Every `build.py` run validates the content first and builds nothing when `validate.py` would report an error.
`--check` then goes over the built site: links, images, anchors, each page's metadata, the sitemap, the feed, the
search indexes and the GPX copies. GitHub runs the unit tests and `build.py --check` on each push to `main`.
`docs/CONTENT_GUIDE.md`, section 5, lists the lines both commands print and what to do about each.

## Privacy

Tracks are published in full (not trimmed), with timestamps; use `add_trip.py --strip-times` to publish a GPX
without times. Photos are re-encoded as WebP with all EXIF/GPS metadata removed. Maps are for illustration, not
navigation. `docs/PRIVACY_NOTES.md` says what the tracks add up to and which decisions are yours;
`python3 tools/privacy_audit.py` reproduces its counts.

See `docs/DEVELOPING.md` for how the site generator works.
