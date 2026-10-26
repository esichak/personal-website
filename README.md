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
# from a Garmin (or any) FIT/GPX file, or Garmin's "Export Original" .zip as it is, with photos
python3 tools/add_trip.py ~/Downloads/Morning_Ski.fit --title "Rose Knob Peak" --activity ski \
    --place "Mount Rose" --region "Lake Tahoe" --party "Adam" --photos ~/Desktop/rose/

# or straight from a Strava bulk export (title, stats, description and photos come along)
python3 tools/add_trip.py --strava-export "/path/to/Strava export folder" --strava-id "<activity id>"

# the next day of a trip whose index.md says kind: multi-day (starting one: ADDING-TRIPS.md); an end_date: line
# earlier than the new day is moved to it
python3 tools/add_trip.py day3.fit --day-of chamonix-zermatt-haute-route --title "Le Châble → Cabane de Prafleuri"

# a trip that is on the site: a better recording (keeps the write-up and photos), more photos
python3 tools/add_trip.py ~/Downloads/Better.fit --update rose-knob-peak --dry-run
python3 tools/trip_photos.py rose-knob-peak ~/Desktop/more/
```

`--activity` is one of `ski`, `climb`, `hike`, `mtb`, `other` (use `--subtype SUP|Rafting|Kayaking|Mountaineering`
with `other`). The script creates `content/trips/<slug>/` and renders its maps, which needs the internet
(`--no-render` skips that; run `python3 tools/render.py <slug>` later), and ends with a numbered list of what is left.
It refuses a second spelling of an existing region, and `--force` over a trip someone has worked on. For a trip
that is already on the site, [ADDING-TRIPS.md](ADDING-TRIPS.md), "Changing a trip that is on the site", has one table:
each kind of change, what to run, whether it needs the internet and what to stage. Then:

1. Edit `content/trips/<slug>/index.md`: write the report under the front matter (Markdown), check `place`,
   `region`, `party`, add `beta:` rows, and give every photo an `alt:` description.
2. Preview: `python3 tools/build.py --serve --open <slug> --watch` builds in a few seconds, opens the new report in the
   browser (http://localhost:8000/trips/<slug>/) and builds again whenever you save a file; Ctrl+C stops it. The build
   checks the content first and stops with `ERROR` lines that name the file.
3. Publish with one command, from `main`:

   ```bash
   python3 tools/publish.py <slug> --dry-run   # check the site and list what would be staged; writes nothing
   python3 tools/publish.py <slug> --push      # check, stage the trip's files, commit, push and watch the deploy
   ```

   It stops at the first thing that is wrong and says what to do: not on `main`, something unrelated already staged,
   maps not drawn yet (`python3 tools/render.py <slug>`), a failed site check, an iCloud conflict copy among the files.
   It stages `content/trips/<slug>`, `rendered/trips/<slug>`, `rendered/site` when the region maps changed and
   `content/home.json` when it changed, never the whole tree, and commits `Add <title>` (or `Update <title>`). With
   `--push` it waits for GitHub's run and prints the trip's live address, or the failed step and that the old site is
   still up. Without `--push` it prints the `git push` line instead. The commands it runs are in
   [ADDING-TRIPS.md](ADDING-TRIPS.md), step 5, to type by hand if it ever fails. Only a push to `main` is published.

Useful front-matter fields (see any existing trip for the format; what a change to each one needs once the trip is
published: [ADDING-TRIPS.md](ADDING-TRIPS.md), "Changing a trip that is on the site"):

| Field | Meaning |
| --- | --- |
| `title`, `activity`, `subtype`, `date`, `start_time`, `timezone` | Basics (filled in by `add_trip.py`; for a multi-day trip you write `title` and `activity` yourself, see ADDING-TRIPS.md) |
| `place`, `region`, `party` | "Sawtooth Ridge", "Eastern Sierra", "Adam". `region` groups trips on the map page and is a filter on the Trips page. A region that has a region map and at least one published report also has a page of its own, `regions/<slug>/`. The slug is the name in lower case, with accents folded to plain letters, apostrophes and characters that have no plain-letter form dropped, and every run of what is then neither a letter nor a digit turned into one hyphen (none at the ends): `Eastern Sierra` gives `regions/eastern-sierra/`, and `Val d'Isère` would give `regions/val-disere/`. Nothing is written for the page, and it lists every report and active tick-list goal whose `region` is exactly that name, from the next build on; its map shows a new trip once the region maps have been drawn again (`docs/CONTENT_GUIDE.md`, section 11) |
| `route_shape` | `loop`, `out-and-back` or `point-to-point` (detected from the track) |
| `stats` | `distance_km`, `moving`, `elapsed`, `gain_m`, `loss_m`, `high_m`, `low_m` (Strava's numbers, or computed) |
| `source` | Optional: `Strava`, `Garmin` or `CalTopo`, the service the recording came through, named in the stats note under the strip ("Stats from the GPS recording via Garmin."). Without it the note says "via Strava" when the trip, or every day of it, has a `strava_id` line, and names no service otherwise. `add_trip.py` writes `source: Strava` for a Strava-export import (`docs/CONTENT_GUIDE.md`, 7.11) |
| `featured: true` | Eligible for the section pages' "Featured" block (single-day trips with a track only; the home page is picked in `content/home.json`, see below). On its region's page the same line counts for a report of any kind, with or without a track: the Featured row there holds three cards, and flagged reports come before unflagged ones, the newest flagged first, so a fourth flagged report is not shown (`docs/CONTENT_GUIDE.md`, 11.3) |
| `cover_photo`, `cover_focal_x`, `cover_focal_y` | The photo the trip's cards and its page's share image use (a path declared under `photos`), and where to keep in the crop, 0–100 (default 50/50). It is also the lead photo of a single-day report with photos, of a multi-day trip and of the PCT page, when it is at least 6:5 wide; a portrait or a square does not lead. After changing `cover_photo`, run `python3 tools/thumbs.py <slug>` and commit the `.th` file it writes: the small copy the cards load |
| `card_summary` | Optional one- or two-sentence factual summary for the trip's cards: the home page's feature card and its card on the Trips page (the report's opening is used when it is absent) |
| `search_aliases` | Other names people might search for, as an inline list (`[PCT, Pacific Crest]`); searched on the Trips page, never shown |
| `region_days` | PCT only: which days of the journal lie in which region, by the day numbers the page shows, so that region's map draws them and its list names them. A region's days can be named parts (`Lake Tahoe:` with `Pacific Crest Trail: 67-76` and `Tahoe Rim Trail: 147-153` under it): each part is one line on the map and one row in the list. `146/2` takes only the second stretch of day 146, for a day recorded before and after a drive; needs `render.py --site`. See `docs/CONTENT_GUIDE.md`, 11.7 |
| `journal_highlights` | PCT only: the entries the journal points to, as an inline list of day-file ids (`[001, 059]`), in display order; absent means no Highlights section |
| `published_at`, `updated_at` | Optional publication dates; see `docs/CONTENT_GUIDE.md` |
| `draft: true` | Keep it off the site (once pushed, its files are still in the public repository). `render.py` leaves drafts out, so run `python3 tools/render.py <slug>` after removing the line. For a trip that is already published the line is enough too, from anywhere (even a web edit on github.com): the build leaves the trip's own pin and line out of the region maps; a numbered cluster keeps counting it until `render.py --site` is run when online (ADDING-TRIPS.md, "Taking a trip off the site") |
| `kind: multi-day`, `end_date` | A trip of several days, each a `days/NN.md` with its `NN.gpx` (see ADDING-TRIPS.md). `date` and `end_date` are its first and last day; when absent they come from the day files. `kind: series` is the PCT journal |
| `kind: planned` | A tick-list goal, not a report: planned route, approximate stats, `goal.json` beside it (see `docs/TICK_LIST_GUIDE.md`) |
| `beta` | List of `label` / `value` rows shown beside the report; conditions go here too (`Snow`, `Weather`, `Water level`). The old `conditions:` key is not read |
| `map` | `peaks: [Mount Tallac]` to label summits (also searchable on the Trips page), `places: [...]`, `water_labels: [{text, x, y}]` |
| `photos` | `file`, `w`, `h`, `alt`, optional `caption` |
| `summits` | Optional: the summits of the trip, one entry each: `- name: Mount Tallac`, with `outcome: summit`, `turned-around` or `traverse` and `route:` if you like. Shown as a Summits row beside the report and found by the search; never worked out from anything else (`docs/CONTENT_GUIDE.md`, 7.13) |

## Feature a trip on the home page

`content/home.json` lists the featured trips, in order, up to six: the first is the hero across the top of the home
page (its cover, with the title over it), the others the grid under it:

```json
{"featured_slugs": ["pacific-crest-trail-2024", "matterhorn-peak-west-couloir", "peak-bagging-szn"]}
```

Edit the list to feature, reorder or remove trips; nothing else decides it. Covers and summaries are front-matter
fields on the trip (`cover_photo`, `cover_focal_x`/`cover_focal_y`, `card_summary`). The build stops with a clear
message when a slug is unknown, a draft, a planned route or listed twice. An optional
`"region_maps": ["Lake Tahoe", "Santa Cruz"]` in the same file picks the one or two region maps "Where I've been"
draws (Lake Tahoe and Eastern Sierra without it); a name without a region map stops the build. Details:
**[docs/CONTENT_GUIDE.md](docs/CONTENT_GUIDE.md)**.

## Let readers reach you

An optional `content/author.json` puts a contact on the site: an address shown on About ('Follow & contact') and in
the footer, with 'Ask about this trip' on every report, and the profiles you name, on About only:

```json
{"email": "<an alias you are willing to keep public>", "links": [{"label": "Strava", "url": "https://..."}]}
```

Leave the file out and the site shows no contact. Use an alias, not your own address: once committed it stays in the
repository's history for good (docs/PRIVACY_NOTES.md). The build stops on a misspelt key or a link that is not https.

## Keep a tick list of future goals

Future routes live beside the reports as `kind: planned` trips with an optional `goal.json`, shown at
https://esichak.github.io/personal-website/tick-list/. Save one locally (a name and an activity are enough; a GPX is
optional and is copied into the public checkout only with `--publish-track`), review it, then publish through git:

```bash
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity hike --gpx ~/Downloads/route.gpx --dry-run
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity hike --gpx ~/Downloads/route.gpx --publish-track
python3 tools/ticklist.py update your-route-name --status shortlisted --priority high
python3 tools/ticklist.py suggest-peaks your-route-name      # the named summits the line goes over (writes nothing)
python3 tools/ticklist.py update your-route-name --objective "The whole ridge" --peaks "North Top, South Top"
python3 tools/ticklist.py log-outing your-route-name --outcome completed --report-slug an-existing-report
```

New goals are drafts until you remove `draft: true`. With `--publish-track` the command also starts `render.py`
(`--no-render` skips that), but `render.py` leaves drafts out, so it draws no map for the new goal. After you remove
`draft: true`, run `python3 tools/render.py your-route-name` (needs the internet) to draw it. The full workflow, every
field and the research prompt are in **[docs/TICK_LIST_GUIDE.md](docs/TICK_LIST_GUIDE.md)**.

## Check, build and re-render

```bash
python3 tools/doctor.py              # one read-only look at this Mac and checkout: disk, git, conflict copies, tools
python3 tools/validate.py            # check content/ without building: ERROR and WARNING lines, then a summary
python3 tools/build.py --out ~/Library/Caches/personal-website/site --link --check   # build and check, outside iCloud
python3 tools/build.py --out ~/Library/Caches/personal-website/site --serve          # ... and serve it on localhost:8000
python3 tools/check.py               # before pushing a change to tools/, tests/ or assets/: validate, both Pythons, build check
python3 tools/tidy.py                # list iCloud conflict copies (--delete removes those of rendered/ and _site/)
python3 tools/thumbs.py              # make the card-size (.th) copies of cover photos that are missing (needs cwebp)
python3 tools/content_report.py      # what each report has and lacks (--missing place, --alt, --taxonomy, --markdown)
python3 tools/trip_photos.py SLUG FILES   # add photos to a trip that is on the site (--day NN, --cover, --dry-run)
python3 tools/about_photo.py FILE    # put a photo on the About page (content/about.md; it shows once its alt is written)
python3 tools/render.py --status     # what a render would draw and why (offline; exit 1 when something is to draw)
python3 tools/render.py              # render anything whose track or map settings changed (needs internet)
python3 tools/render.py --charts     # only elevation profiles (fast, offline)
python3 tools/share_preview.py       # what each page's share card is made of, with flags (reads _site/; --site DIR)
python3 tools/fonts.py --check       # are the site's own fonts complete? (tools/fonts.py without --check downloads them)
python3 tools/render_sheet.py --all  # after a render: every changed map beside its old self (.cache/render-sheet/)
python3 tools/size_report.py         # what the repository and the site weigh, and how fast they grow
python3 -m unittest discover -s tests   # the generator's unit tests (see docs/DEVELOPING.md)
python3 tools/smoke.py ~/Library/Caches/personal-website/site   # a few pages in headless Chrome (CI runs it too)
python3 tools/reflow.py ~/Library/Caches/personal-website/site  # does any page scroll sideways at 320 or 375 px? (Chrome, by hand)
```

A plain `python3 tools/build.py --check` writes the published build into `_site/` (about 240 MB of copies; CI uses
it); the `--out ... --link` form above links the photos, maps and GPX instead and takes a few seconds.

What the repository and the site weigh, and the rules that keep them well inside GitHub's limits, are in
`docs/DEVELOPING.md`, "Storage budget"; "Yearly upkeep" there is the once-a-year list (sizes, the workflow's actions,
GitHub's limits, the map and font sources).

`render.py` keeps the terrain tiles and OpenStreetMap answers it downloads in `~/Library/Caches/personal-website/`
(outside iCloud Drive; `docs/DEVELOPING.md`, "Render caches", has the one-time move of the old `.cache/` folders). An
answer is used for ever: to pick up newer OpenStreetMap data (a new trail, a renamed lake), delete the cache's `osm/`
folder (or one answer in it) and run `python3 tools/render.py --site --force`. That downloads every answer again and
can change roads and labels on every map, which the change check does not notice; the best time is just before the
year's render round (`docs/DEVELOPING.md`, "Yearly upkeep"), which redraws every map anyway. A render that fails keeps the last
good maps and ends with exit status 1.

Every `build.py` run validates the content first and builds nothing when `validate.py` would report an error.
`--check` then goes over the built site: links, images, anchors, each page's metadata, the sitemap, the feed, the
search indexes, the GPX copies, ARIA references and heading order. On each push to `main` GitHub runs
`build.py --check`, and the unit tests too when the push changes `tools/`, `tests/`, `assets/`, `.github/` or
`docs/PRIVACY_NOTES.md`: a push of content alone is live in about a minute, one with code in about three. A push of
only Markdown the build never reads (this file, the log, the plans) starts no run.
`docs/CONTENT_GUIDE.md`, section 5, lists the lines both commands print and what to do about each; among the warnings
are maps drawn from older inputs than the trip has now (`maps were drawn from other inputs ...`).

Before a push that changes titles, descriptions or covers, run `python3 tools/share_preview.py` on the build and read
its flags. After the push, once the site is live:

- `curl -I "https://esichak.github.io/personal-website/assets/site.css?v=<the hash a page names>"` answers 200 with
  `cache-control: max-age=600`;
- paste a report and the home page into Google's Rich Results Test (the BreadcrumbList and, on a written report, the
  BlogPosting);
- check `https://esichak.github.io/personal-website/feed.xml` once in the W3C feed validator;
- paste the Matterhorn report, a report with a portrait cover and the home page into a share debugger (Facebook's
  Sharing Debugger or opengraph.xyz) and an iMessage thread, and note what each drew.

## Search Console

Search engines find the site through its sitemap, which has to be submitted: `robots.txt` sits at
`/personal-website/robots.txt`, and crawlers only read one at the host's root (`esichak.github.io/robots.txt`, which
does not exist), so they never see its `Sitemap:` line.

1. In Google Search Console add a URL-prefix property for `https://esichak.github.io/personal-website/`.
2. Choose the HTML tag method and put its token in `tools/sitegen/core.py`:
   `VERIFY_TAGS = (('google-site-verification', '<token>'),)`. The token is public; commit it, push, then press Verify.
3. Submit `sitemap.xml`, and inspect one report's address to see it as Google does.
4. Import the property into Bing Webmaster Tools, adding its `('msvalidate.01', '<token>')` pair the same way if it
   asks for a tag.

Optional, outside this repository: a public `esichak/esichak.github.io` repository with a `robots.txt` (`User-agent:
*`, `Allow: /`, `Sitemap: https://esichak.github.io/personal-website/sitemap.xml`) and an `index.html` that links to
`/personal-website/`, so the bare host stops answering 404. No Disallow lines: the explorer's search indexes must stay
readable.

## Setting up a new Mac

1. `xcode-select --install` (git and `/usr/bin/python3`), then install [Homebrew](https://brew.sh).
2. `brew install webp gh node python@3.12`: `cwebp` for photos; `gh` to watch deploys (`publish.py --push`); `node`
   runs the JavaScript tests (they are skipped without it); `python@3.12` is what CI tests with.
3. `gh auth login`, and `git config --global user.name "..."` and `user.email "..."`.
4. `git clone https://github.com/esichak/personal-website.git ~/Code/personal-website` (any folder outside iCloud
   Drive; never a Finder copy of an old checkout, which carries its conflict copies).
5. In it: `python3 tools/doctor.py`, `python3 -m unittest discover -s tests`, `python3 tools/build.py --check`.

The first `render.py` downloads about 360 MB of terrain tiles and OpenStreetMap answers into
`~/Library/Caches/personal-website/`; until a track, a title or a map setting changes nothing is redrawn, and
`render.py --site --force` redraws every region map from current OpenStreetMap data. What a clone does not bring is
listed below.

## Moving the checkout out of iCloud Drive

The checkout used to live in `~/Documents`, which iCloud Drive syncs: it leaves conflict copies (`meta 3.json`,
`.git/index 2`), offloads files a build then waits for, and once removed `.git/index`. First commit (or set aside)
everything in the old folder: `git status --short` there must list nothing but untracked files you mean to leave, since
only commits move. Then, with the old folder still in place:

```bash
OLD="$HOME/Documents/Claude Code/personal-website"        # the old folder
git clone https://github.com/esichak/personal-website.git ~/Code/personal-website && cd ~/Code/personal-website
git remote add old "$OLD" && git fetch old           # the branches of the old folder, as old/<name>
git log --oneline origin/main..old/main              # commits on the old main that GitHub does not have yet
git merge --ff-only old/main                         # ... brought onto this main (nothing to do when the list was empty)
git branch --no-track phase-8-publishing-loop old/phase-8-publishing-loop   # once for each other branch not on GitHub
git remote remove old
mkdir -p .cache/p4 && cp "$OLD/.cache/p4/PRIVACY_AUTHOR_ONLY.md" .cache/p4/
mkdir -p ~/Library/Caches/personal-website && mv "$OLD/.cache/tiles" "$OLD/.cache/osm" ~/Library/Caches/personal-website/
python3 tools/doctor.py
```

`git branch -r` lists the old folder's branches between the fetch and the `remote remove`; only commits come along,
no working files. Copy any untracked file you want to keep by hand (`git status --short` in the old folder lists
them). The two cache folders are the render caches (skip that line if they are already there). Once the new folder
works, delete the old one. Until then, in the old folder, `python3 tools/tidy.py --delete` removes the conflict copies
of generated files (`rendered/`, `_site/`); copies under `content/` and `assets/` and the stray index copies are listed
for you to compare and delete by hand (`python3 tools/doctor.py` prints the `rm` line for the index copies).

## What is and is not in the repository

Everything published is on GitHub: `content/` (every trip, track and web photo copy) and `rendered/` (every map). A
clone has the site whole. Not in it: the original photos and track files you hand to `add_trip.py` (it writes the
1600 px, 800 px and card-size WebP copies without EXIF and a simplified `track.gpx`, never the originals), so keep
those wherever you keep them; the render caches, which are fetched again; and `.cache/p4/PRIVACY_AUTHOR_ONLY.md`, the
one file in the checkout that is neither on GitHub nor fetched again: back it up yourself.

## Privacy

Tracks are published in full (not trimmed), with timestamps; use `add_trip.py --strip-times` to publish a GPX
without times. Photos are re-encoded as WebP with all EXIF/GPS metadata removed. Maps are for illustration, not
navigation. `docs/PRIVACY_NOTES.md` says what the tracks add up to and which decisions are yours;
`python3 tools/privacy_audit.py` reproduces its counts.

See `docs/DEVELOPING.md` for how the site generator works.
