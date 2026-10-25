# Adding a trip report

How to put a new trip on https://esichak.github.io/personal-website/. Everything runs in this folder on your Mac. GitHub
rebuilds and publishes the site on its own every time you push to the `main` branch; a push to any other branch
publishes nothing.

## 1. Get the track file

- **Garmin Connect:** open the activity, then ⚙, then **Export Original**. You get a `.zip` holding the `.fit` file; give
  the `.zip` to `add_trip.py` as it is (it reads the one track file inside without unpacking anything), or unzip it and
  give the `.fit`.
- **Strava:** open the activity, then ⋯, then **Export GPX**.

Put the photos you want in one folder, for example `~/Desktop/rose/`.

## 2. Add the trip

In Terminal:

```bash
cd ~/Code/personal-website        # the folder you cloned the site into (README.md, "Setting up a new Mac")
```

```bash
python3 tools/add_trip.py ~/Downloads/Morning_Ski.fit --title "Rose Knob Peak" --activity ski --place "Mount Rose" --region "Lake Tahoe" --party "Adam" --photos ~/Desktop/rose/
```

| Option | What to put |
| --- | --- |
| `--title` | The trip's name as it should appear on the site |
| `--activity` | `ski`, `climb`, `hike`, `mtb` or `other` |
| `--subtype` | Only with `other`: `SUP`, `Rafting`, `Kayaking` or `Mountaineering` (any other word is refused) |
| `--place` | The specific spot, e.g. "Mount Rose" (optional) |
| `--region` | Reuse an existing region, spelt exactly as it is, so the trip joins its region map and its region page (list below). A second spelling of an existing region is refused |
| `--source` | Where the recording came from, `Strava`, `Garmin` or `CalTopo` (optional): the stats note under the strip names it ("Stats from the GPS recording via Garmin."). An import from a Strava export is `Strava` by itself; a FIT or GPX file names no service unless you give one |
| `--timezone` | The trip's time zone as an IANA name, e.g. `America/Chicago` (optional). Without it the tool guesses from where the track starts and prints the zone it used (`timezone America/Denver, guessed; --timezone to change`); the date and the start time are worked out in that zone |
| `--party` | Who you went with, e.g. "Adam" (optional) |
| `--photos` | A folder of photos, or individual photo files (optional) |
| `--draft` | Keep the trip off the site until you remove `draft: true` from its file. A draft you push is still in the public repository. Its maps are not drawn while it is a draft: after you remove the line, run `python3 tools/render.py <trip-name>`. To push a draft, stage `"content/trips/<trip-name>"` alone in step 5. For a trip that is already on the site, see "Taking a trip off the site" below |
| `--strip-times` | Write the GPX without timestamps. The page still shows the date and the start time (see `docs/PRIVACY_NOTES.md`) |
| `--no-render` | Skip drawing the maps, so no internet is needed. Draw them later with `python3 tools/render.py <trip-name>` |
| `--force` | Import again over a folder that is still an untouched import: the placeholder report, empty `alt:` lines and nothing you added; it rewrites `index.md`. It is refused, and nothing is written, once the folder has a write-up, a photo description, a line such as `beta:`, `map:` or `cover_photo:`, day files or a `goal.json` ("When something goes wrong", below). For a better recording of a trip that is on the site, use `--update` (below and "Changing a trip that is on the site") |

If the title comes from a Strava export or the file name and looks like a name Strava gives an activity by itself
(`Morning Hike`, `Ride near <a town>`), the command says so: `note: the title "Morning Ride" looks like one
Strava gives an activity by itself; pass --title ...`. It never changes the title for you. The folder name is the
trip's address, so the title can also be changed later in `index.md` ("Changing a trip that is on the site").

Three more commands share the script; none adds a trip:

| Command | What it does |
| --- | --- |
| `python3 tools/add_trip.py ~/Downloads/Better.fit --update <trip-name>` | A better recording of a single-day trip that is on the site. It replaces `track.gpx` and the lines worked out from the track (`date:`, `start_time:`, `route_shape:`, and `stats:` unless you add `--keep-stats`, for a figure you corrected by hand); the write-up, the photos and every other line stay as they were, and the trip's own `timezone:` line wins unless you give `--timezone`. `--dry-run` prints the changes to `index.md` and writes nothing. It then checks the trip and draws its maps (internet; `--no-render` to leave that for later). A trip whose stats are credited to a service (a `strava_id:` or `source:` line, as on every trip today) needs `--source Garmin` (or `Strava`, `CalTopo`) for where the new recording came from, or `--keep-stats`, so the new figures are not shown as Strava's. Refused: a trip with day files, a planned route, a track published without timestamps, `--strip-times`, and the options of a new import (`--title`, `--photos`, ...): change those lines in `index.md` |
| `python3 tools/add_trip.py --retime <trip-name> --timezone America/Chicago` | Sets the trip's time zone and works its `date:` and `start_time:` out again from its own `track.gpx`, which keeps the time of every point; it prints each line old and new. Without `--timezone` it uses the zone the file already names. Offline; no map is drawn again. A trip with day files, or whose track has no times, is refused |
| `python3 tools/add_trip.py --strava-export "/path/to/Strava export folder" --list` | Lists the activities of a Strava export that no `strava_id:` line of a trip or a day names, newest first: date, activity ID, type, distance, whether it has photos, name. `--type Hike,Ride` and `--since 2026-01-01` narrow the list. It only prints. The `strava_id:` lines are the first bulk import's; `add_trip.py` writes none, so an activity added with `--strava-id` stays on the list (add the line to its `index.md` by hand to drop it: `strava_id: "<activity id>"`) |

`--region` is the map grouping: the trip joins that region's map, its page and its filter on the Trips page. `--place`
is the named area inside it (a peak, a trailhead, a crag), which the cards and the lists print; without one they print
the region. `python3 tools/content_report.py --taxonomy` lists the regions already on the site with their counts and the
places inside each, and names spellings that look like one place written two ways. Today the eight with a region map are
Lake Tahoe, Santa Cruz, Eastern Sierra, Boise, Bay Area, Tetons, Alps and Oregon (the PCT journal has a region of its
own, Pacific Crest Trail). A new region name is fine too; it gets its own region map once it has three trips with a
track. An active tick-list goal with a route counts as one of the three; a report without a track does not. Until the
region maps are drawn again the Map page does not list the new region, and the check prints a `WARNING` for the trip
that ends `run python3 tools/render.py --site --force`: run that (internet needed) and stage `rendered/site` with the
trip. A name that differs from an existing region only in capitals, accents, apostrophes or other punctuation is not a
new region but a second spelling of that one. `add_trip.py` refuses such a spelling and names the one to use (`region
"eastern sierra" is written "Eastern Sierra" on N trips; use that spelling`); for a `region:` line typed by hand the
content check warns instead: correct it rather than running the command (`docs/CONTENT_GUIDE.md`, 11.4). A name no trip
uses yet is a new region, and the command says so (`new region: ...`) and lists the existing ones.

A region that has a region map and at least one published report also has a page of its own, `regions/<region>/`. The
address is made from the name: lower case, accents folded to plain letters, apostrophes and characters with no
plain-letter form dropped, and every run of what is then neither a letter nor a digit turned into one hyphen (none
at the ends). `Lake Tahoe` gives `regions/lake-tahoe/`, and
`Val d'Isère` would give `regions/val-disere/`. The eight named above have one today. A region whose map draws planned
routes only has none. Nothing has to be written for the page: its head is counts, years and places taken from its
trips (and, when you write one, your introduction from `content/regions/<region>.md`, `docs/CONTENT_GUIDE.md` 11.8),
and under that come the region's map, up to three Featured reports and every report of the
region. The page lists every report and active tick-list goal whose `region:` is exactly the region's name, so a new
trip is on it at the next build, also one added with `--no-render` and one without a track. The map on the page is the
region map as it was last drawn: the new trip's line and pin appear there, as on the Map page, once the render that
draws the trip's own maps has redrawn it and `rendered/site` is pushed with the trip (step 5). A region without a
region map has no page and stays in the Map page's list, under "Not on a region map". `docs/CONTENT_GUIDE.md`, section
11, has the rest.

The command creates `content/trips/<trip-name>/` with the GPX track, web copies of each photo in three sizes (GPS and
camera data removed) and the stats, then draws the maps and elevation profile. That takes about a minute and needs the
internet; the terrain tiles and OpenStreetMap answers it downloads are kept in `~/Library/Caches/personal-website/`
for the next render. `<trip-name>` is the title in lower case with hyphens: `rose-knob-peak` here. It then says what a render
would still draw (`render.py --status`, below; when the render failed or something is left to draw, the list below
keeps the step that draws the maps) and ends with a numbered list of what is left to do: the file to edit,
how many `alt:` lines are empty, the optional lines, the preview command and the publishing step. With `--no-render`
it prints `maps not drawn: python3 tools/render.py <trip-name>` instead of drawing.

**Multi-day trips.** A multi-day trip is one folder: an `index.md` that says `kind: multi-day`, and two files for each
day in `days/` (`01.md` and `01.gpx`, `02.md` and `02.gpx`, and so on). `add_trip.py` writes the day files; you write
the `index.md` first. Do not start from the single-day command above: it puts the first day in `track.gpx`, outside
`days/`, and the build stops once a day file sits beside it.

If the trip is already on the site as a single-day report, do not add a day to it either. Once `kind: multi-day` is
in its `index.md` the build passes, but the `track.gpx` left beside `days/` is on no page. Only a `WARNING` on that
file says so:
`is not used: this trip has day files, and its page, maps and downloads come from days/NN.gpx; remove the file`.
Move the old folder out of `content/trips/` instead, start the multi-day folder under the same name as below, and add
the first day again with `--day-of`, from the same recording and the same photos as before. Then copy your write-up
across. The old folder's `track.gpx` can stand in for a recording you no longer have, but the day's stats are then
worked out again from that file and can differ from the ones the report showed.

1. Pick the folder name (lower-case letters, digits and single hyphens; it becomes the page's address) and create
   `content/trips/<trip-name>/index.md` in a text editor. For a two-day version of the example above that is
   `content/trips/rose-knob-peak/index.md`:

   ```yaml
   ---
   title: Rose Knob Peak
   activity: ski
   kind: multi-day
   place: Mount Rose
   region: Lake Tahoe
   party: Adam
   ---
   ```

   Every line starts at the left margin: no spaces before `---` or before a field name. `activity` takes the same
   words as `--activity` (with `other`, add a `subtype:` line). `place`, `region` and `party` are optional. Leave
   `date:` and `end_date:` out: the page takes the first and the last day's dates from the day files.
2. Add every day in order, the first one included, then draw the maps once:

   ```bash
   python3 tools/add_trip.py ~/Downloads/day1.fit --day-of rose-knob-peak --title "Trailhead to hut" --photos ~/Desktop/rose/day1/ --no-render
   python3 tools/add_trip.py ~/Downloads/day2.fit --day-of rose-knob-peak --title "Hut to summit" --photos ~/Desktop/rose/day2/ --no-render
   python3 tools/render.py rose-knob-peak
   ```

   Each `add_trip.py` run writes the next `days/NN.md` and `days/NN.gpx` and names the file to edit. `render.py`
   needs the internet; without `--no-render` it runs after every day instead of once.
3. Write the trip's overall report under the closing `---` of `index.md`, and each day's under the closing `---` of
   its `days/NN.md`. The day file also lists that day's photos, each with an `alt:` to fill in.

To add a day to a multi-day trip that is already on the site, run the same `--day-of` command. If its `index.md` has
an `end_date:` line (the older trips do) earlier than the new day, the command moves it to the new day's date and says
so (`end_date 2026-09-12 -> 2026-09-13 (index.md)`): the page's date range follows that line. A trip without the line
gets none. An `index.md` with a comment inside its front matter is left alone, and the command prints a `note:` that
asks you to change the line by hand; until then the day's file gets a `WARNING` such as
`date 2026-09-13 is after the trip's end_date 2026-09-12 (index.md), so the page's dates end before this day`.
If the command prints a `note:`, do what it says before you build, with one exception: a note that asks for
`kind: multi-day` in a folder that holds a `track.gpx` means the folder is a single-day report, and "If the trip is
already on the site as a single-day report" above applies.

**A day on the PCT journal** (`pacific-crest-trail-2024`) is added the same way, with two more edits:

```bash
python3 tools/add_trip.py ~/Downloads/day.fit --day-of pacific-crest-trail-2024 --title "The day's title" --no-render
```

1. Open the new `days/NNN.md` the command names (not `index.md`) and add a `day:` line with a label no other day has,
   for example `day: "154"`. The journal's day labels do not follow the file numbers, so the build stops until the
   new day has one.
2. If the day is later than `end_date:` in the journal's `index.md`, the command has moved `end_date:` to it (it
   prints `end_date ... -> ...`); check that it did.
3. Write the entry under the `---` of the day file, then run `python3 tools/render.py pacific-crest-trail-2024`
   (internet needed) and go on with steps 4 and 5.

**From a Strava bulk export** (Strava settings, then Download your data): unzip the download and give
`--strava-export` the folder that holds `activities.csv`. The title, stats, description and photos come along
automatically. `--strava-id` is the activity's number in the `Activity ID` column of that file; `--list` instead of
`--strava-id` prints the activities that are on no trip yet, with their numbers, and stops.

```bash
python3 tools/add_trip.py --strava-export "/path/to/Strava export folder" --list
python3 tools/add_trip.py --strava-export "/path/to/Strava export folder" --strava-id "<activity id>"
```

## 3. Write the report

Open `content/trips/<trip-name>/index.md` in any text editor:

- Write the report under the block that ends with `---`. Plain text works; blank lines start new paragraphs.
- Give every photo a short `alt:` description, e.g. `alt: "Two skiers skin up a ridge above Lake Tahoe."`
- Optional extras, added among the lines above the closing `---`:

  ```yaml
  featured: true
  beta:
    - label: Trailhead
      value: Mount Rose Summit
  map:
    peaks: [Mount Rose]
  ```

  `featured: true` makes a single-day trip with a track eligible for the Featured block of its activity page (Climb,
  Hike, MTB, Other; the Ski page has none); the home page's features are listed in `content/home.json` (see
  `docs/CONTENT_GUIDE.md`). On its region's page, when the region has one, the same line counts for a report of any
  kind, with or without a track: the Featured row there holds three cards, and flagged reports come before unflagged
  ones, the newest flagged first, so a fourth flagged report is not shown (`docs/CONTENT_GUIDE.md`, 11.3). `beta:`
  rows show beside the report. `map: peaks:` labels those summits on the map (run `python3 tools/render.py
  <trip-name>` after changing it). Indent with spaces: a line indented with a tab stops the build with a line that
  names it. Any existing trip's `index.md` shows the format.
- The other optional lines (the cover photo and its crop, the card summary, search names, the summits you reached,
  the service the recording came through, and the `published_at` and `updated_at` dates) are described in
  `docs/CONTENT_GUIDE.md`.

## 4. Preview it

```bash
python3 tools/build.py --serve --open rose-knob-peak --watch
```

It builds the site in a few seconds, opens the trip's page in your browser (`--open` alone opens the home page), and
serves it on http://localhost:8000 until you press Ctrl+C. The preview links the photos, maps and GPX files instead of
copying them (add `--copy` to copy, as the published build does). With `--watch`, every time you save a file under
`content/`, `assets/`, `tools/sitegen/`, `tools/lib/` or `rendered/site/` the site is built again (`rebuilt in 2.4s:
content/trips/rose-knob-peak/index.md changed`); reload the page to see it. A rebuild empties the folder first, so a
reload during those two seconds can show "File not found": reload again. When the content check stops a rebuild, its
`ERROR` lines print and the preview keeps the last good build until you fix the file and save it again.

Every build checks the content first. A mistake stops it with one line for each problem, starting with `ERROR` and
the name of the file; fix the file and run the command again. Lines starting with `WARNING` do not stop the build.
`docs/CONTENT_GUIDE.md`, section 5, says what each line means and what to do about it. To see the whole list without
building:

```bash
python3 tools/validate.py
```

## 5. Publish

From `main`, one command checks the site, stages exactly this trip's files, commits and (with `--push`) publishes:

```bash
python3 tools/publish.py rose-knob-peak --dry-run    # the check, and the list of what would be staged; writes nothing
python3 tools/publish.py rose-knob-peak --push       # check, stage, commit, push, and watch GitHub publish it
```

Before that, fill the `published_at:` line `add_trip.py` left empty in `index.md` with the day you publish
(`published_at: 2026-10-24`): the RSS feed then lists the report on that day rather than on the trip date, and the
sitemap tells search engines when it went online. For a draft, fill it the day the `draft: true` line comes off.
Leave it empty only if you would rather the feed used the trip date (`docs/CONTENT_GUIDE.md`, section 8).

Put your trip's folder name in place of `rose-knob-peak` (several names publish several trips in one commit). It stops
at the first thing that is wrong, with one line that says what to do:

- not on `main` (`git switch main`), or something unrelated already staged (`git restore --staged <path>`);
- with `--push`, `main` already holds commits that are not on GitHub: it lists them, so you push them yourself once
  you have read them (`git push origin main`), or publish without `--push`;
- the trip's maps not drawn yet (no internet at the time, or `--no-render`): `python3 tools/render.py <trip-name>`,
  or `--allow-unrendered` to publish without them;
- the site check fails: the `ERROR` or `BROKEN` lines above it name the file; fix it and run the command again;
- an iCloud conflict copy among the trip's files (`index 2.md`): compare it with the original, delete it, run again;
- what it would commit names a trip that is in this folder but not committed (`content/home.json` features it, the
  region maps were drawn with it, or the write-up links to it): GitHub's check would not have that trip, so publish
  the two together (`publish.py one-trip other-trip`), or the other first.

It then stages `content/trips/<trip-name>`, `rendered/trips/<trip-name>` (when it exists, or existed), `rendered/site`
when the region maps changed and `content/home.json` when it changed, prints the list, and commits `Add <title>`
(`Update <title>` for a trip already published, `Remove <trip-name>` for a folder you deleted; `--message` gives your
own). With `--push` it pushes and waits for GitHub's run: about a minute for a push of content alone, about three
when it changes code. Then it prints `live: https://esichak.github.io/personal-website/trips/<trip-name>/`, or that the
deploy failed, the old site is still up, and the end of the failed step's log (When something goes wrong, below).
Without `gh` it prints the Actions page to watch instead. `gh run list -L 3` shows the last three runs any time.

`add_trip.py` never copies your original photos or track file into the site (it writes resized WebP copies without
EXIF and a simplified `track.gpx`), so keep the originals wherever you keep them; the one file in this folder that is
neither on GitHub nor fetched again is `.cache/p4/PRIVACY_AUTHOR_ONLY.md`, which you back up yourself.

**What it does, by hand.** If `publish.py` itself ever fails, these are its steps (read each answer before the next):

```bash
git branch --show-current            # must say main
python3 tools/build.py --out ~/Library/Caches/personal-website/site --link --check    # must end with link check: OK
git add "content/trips/rose-knob-peak" "rendered/trips/rose-knob-peak" rendered/site
git status --short                   # every staged name a file of this trip or a map under rendered/site/
git commit -m "Add Rose Knob Peak"
git push
```

Which paths to give `git add`:

| What you did | Paths |
| --- | --- |
| Added a trip, or a day of one | `"content/trips/<trip-name>"`, `"rendered/trips/<trip-name>"` and `rendered/site` |
| Added a trip with `--draft`, to push it as a draft | `"content/trips/<trip-name>"` alone: a draft has no maps yet |
| Changed a trip that is on the site | the last column of "Changing a trip that is on the site", below |
| Ran `render.py` with no trip name | `rendered` (the whole folder), plus the `content/trips/<trip-name>` folders you edited |
| Changed the home page's features or region maps | `content/home.json` |

A folder path stages what is new, changed or deleted inside it. `rendered/site` holds the region maps, which a render
redraws along with the trip's own; naming it when nothing changed there does no harm. Never use `git add -A` or
`git add .`: a checkout in an iCloud Drive folder collects conflict copies (`meta 3.json`, `index 2.md`) that would go
out with them (`python3 tools/tidy.py` lists them). Only the `main` branch is published; a push to any other branch
runs nothing.

## Changing a trip that is on the site

Edit the trip's files, run what the table says, then publish as in step 5: `python3 tools/publish.py <trip-name>
--push` stages the paths in the last column itself (`rendered/site` only when the region maps changed). A render needs
the internet; the other commands do not. Whether a change needs a render follows what the maps are drawn from: the
track, `title:`, `activity:`, `kind:`, `map:`, `stats:` and `route_shape:` (`render.py --status` lists every trip a
render would draw, and why).

| Change | What to run | Internet | Paths to stage |
| --- | --- | --- | --- |
| The write-up, a photo's `alt:` or `caption:` | nothing | no | `"content/trips/<trip-name>"` |
| `place:`, `party:`, `beta:`, `card_summary:`, `search_aliases:`, `featured:`, `summits:`, `source:`, `published_at:` or `updated_at:` | nothing | no | `"content/trips/<trip-name>"` |
| `title:` | `python3 tools/render.py <trip-name>`: the trip's own maps carry the title. The region maps take the new title when the site is built, so they are not drawn again | yes | `"content/trips/<trip-name>"` and `"rendered/trips/<trip-name>"` |
| `activity:`, `route_shape:`, a `stats:` value, or `map:` (`peaks`, `places`, `water_labels`) | `python3 tools/render.py <trip-name>`, which draws the region maps again after the trip's own | yes | `"content/trips/<trip-name>"`, `"rendered/trips/<trip-name>"` and `rendered/site` |
| `region:` | `python3 tools/render.py --site --force`, after checking the spelling (one region is one spelling: `docs/CONTENT_GUIDE.md`, 11.4) | yes | `"content/trips/<trip-name>"` and `rendered/site` |
| `cover_photo:` | `python3 tools/thumbs.py <trip-name>`: the card-size copy of the new cover | no | `"content/trips/<trip-name>"` |
| A better recording | `python3 tools/add_trip.py NEW_TRACK --update <trip-name>` (step 2's table), which draws the maps as well | yes | `"content/trips/<trip-name>"`, `"rendered/trips/<trip-name>"` and `rendered/site` |
| More photos | `python3 tools/trip_photos.py <trip-name> FILES_OR_FOLDER` (below) | no | `"content/trips/<trip-name>"` |
| A wrong time zone | `python3 tools/add_trip.py --retime <trip-name> --timezone America/Chicago` (step 2's table). If the date moves past another trip's, the order of the region maps' trips changes and the check asks for `render.py --site` | no (yes for that render) | `"content/trips/<trip-name>"` (and `rendered/site` after a render) |
| A day of a multi-day trip recorded again | by hand, for now: replace `days/NN.gpx`, correct that day's `date:`, `start_time:` and `stats:`, then `python3 tools/render.py <trip-name>` | yes | `"content/trips/<trip-name>"`, `"rendered/trips/<trip-name>"` and `rendered/site` |
| Off the site, or back on | "Taking a trip off the site", below | | |

**Adding photos to a trip that is on the site.** `python3 tools/trip_photos.py rose-knob-peak ~/Desktop/more/` makes
the copies an import makes (1600 px, 800 px and card-size WebP, upright, no EXIF or GPS) of each photo in the folder
(or of the files you name), numbered after the photos the trip already has, and adds an entry for each under
`photos:` in `index.md` with an empty `alt:` line to fill. `--day 03` adds them to `days/03.md` of a multi-day trip
instead; `--cover` makes the first one the cover; `--dry-run` lists what it would write. It ends by naming the empty
`alt:` lines. No render is needed. Taking a photo out is still done by hand: delete its three files and its entry.

## Quick fixes from anywhere

For small text changes (a typo, a better title, a photo description), you can edit the trip's `index.md` directly on
github.com: open the file on the `main` branch, click the pencil, and commit. The site redeploys on its own, in about
a minute. Run `git pull` in this folder before your next local change so the two stay in step (on `main`; another
branch leaves the edit out).

A web edit gets no check before it is published: one that breaks a line of the front matter, or links to a report
that does not exist, fails GitHub's check, and the site stays as it was. Look at the Actions page (or
`gh run list --limit 1`) after a web edit; a red X is explained under When something goes wrong.

## Taking a trip off the site

Put `draft: true` among the lines above the closing `---` of the trip's `index.md` (or remove its folder from
`content/trips/`), then publish: `python3 tools/publish.py <trip-name> --push`, or the same edit on github.com from a
phone. The next build leaves out the trip's page, its photos, its GPX download and its own map, takes it out of the
lists and counts of its region's page and the Map page, and leaves its own pin and route line out of the region maps
on the home page, the Map page, the region pages and the Ski page. No render is needed for that.

- **A numbered cluster still counts the trip.** Where its pin was merged with others, the cluster keeps its number
  and the trip's title in its tooltip until the region maps are drawn again: `python3 tools/render.py --site` when
  online, then publish `rendered/site`. Until then the content check prints a `WARNING` for the trip that begins
  `the site maps under rendered/site/ still draw this trip`. That render can change more than the cluster: a region
  left with fewer than three trips with a track gets no region map from it, and without the map the region has no
  page; its remaining reports are then listed on the Map page under "Not on a region map".
- **The build stops while something else names the trip:** `content/home.json`, a tick-list goal's outing
  (`report_slug` in its `goal.json`), or a link in another trip's write-up. Each `ERROR` line names the file to
  change. GitHub publishes nothing when the build stops or the check fails, so the page stays on the site until both
  pass.

Deleting only `track.gpx` from a single-day report keeps its page, with the write-up, the photos and the stats. The
page loses its map, its elevation profile or speed chart, its links to the route and its GPX download, other pages
no longer draw the small route beside its name, the region maps leave out its pin and line, and the check prints a
`WARNING`: `no track.gpx: the page has no map, no profile and no GPX download`. The next `render.py` run deletes the
report's `rendered/trips/<trip-name>/` folder, which the site no longer uses, so stage `rendered` after it. A report
without a track is drawn on no region map and does not count towards the three trips a region map takes; it stays on
the Trips page, in the Map page's table of all reports and in its region page's lists (`docs/CONTENT_GUIDE.md`, 11.4).

None of this takes a file out of the repository's history (`docs/PRIVACY_NOTES.md`, section 6).

## Or let Claude do it

Open Claude Code in this folder and say something like: *"Add this trip: ~/Downloads/Morning_Ski.fit, photos in
~/Desktop/rose, ski tour on Rose Knob Peak with Adam."* Claude runs the steps above, writes the photo descriptions,
previews the page and publishes it as in step 5.

## When something goes wrong

### Before the push

- **`cwebp` not found:** run `brew install webp` (photos fall back to larger JPEGs without it).
- **A render stops with `! <trip-name>: ...`:** that trip's drawing failed (a terrain tile that would not download, a
  file it could not read). Its last good maps stay where they were, the run goes on with the other trips, and it ends
  with `1 failed, their last good maps kept: <trip-name>`. Run the same command again later. A render you stop with
  Ctrl+C also leaves the maps as they were.
- **Changed a trip's title or map settings:** run `python3 tools/render.py <trip-name>` to redraw its maps, then
  publish the trip ("Changing a trip that is on the site" says what is staged: for a title the trip's own maps alone,
  since the region maps take titles at build time). The check reminds you (`maps were drawn from other inputs ...`).
  `python3 tools/render.py --status` lists, without the internet, every trip a render would draw and why, and whether
  the region maps are up to date.
- **`add_trip.py --force` stops with `... --force would erase them`:** the folder is not an untouched import any more
  (a write-up, photo descriptions, lines you added, day files or a `goal.json`), and nothing was written. For a better
  recording of the same trip, `--update <trip-name>` replaces the track and keeps everything else. To import from
  scratch, move the folder out of `content/trips/` first; git keeps the committed version, and
  `git checkout -- content/trips/<trip-name>` puts it back.
- **A warning says a cover has no card-size copy (.th):** run `python3 tools/thumbs.py <trip-name>` and stage the new
  file with the trip's folder. It happens when `cover_photo` names a photo that was imported before those copies
  existed. If the command prints a `skipped` line that ends `the photo could not be converted`, the photo file itself
  could not be read (a damaged or incomplete file): no copy was written, and the last line counts it as
  `1 skipped (photo missing or unreadable)`. Replace the photo file with a good copy and run the command again.
- **`add_trip.py` stops with `no activities.csv in that folder` or `no such activity`:** `--strava-export` must name
  the unzipped export folder, the one that holds `activities.csv`, and `--strava-id` a number from that file's
  `Activity ID` column. Nothing was written; run the command again.
- **`git add` answers `fatal: pathspec 'rendered/trips/<trip-name>' did not match any files`:** the trip has no maps
  folder, because it was added with `--no-render` or with `--draft`. Nothing was staged. Run
  `python3 tools/render.py <trip-name>`, then `git add` again. For a draft, remove `draft: true` before the render, or
  stage `"content/trips/<trip-name>"` alone to push it as a draft.

### After the push

- **The Actions run shows a red X:** the old site stays up; nothing was published. Open the run (the link
  `publish.py` printed, or `gh run view --web`) and see which step of the build job stopped. *Unit tests:* the log's
  first `FAIL:` or `ERROR:` line names the test; fix it here, run `python3 tools/check.py`, push again. *Build:* the
  first `ERROR` or `BROKEN` line, or `link check: N problems`, names the file; fix it, run `python3 tools/build.py
  --out ~/Library/Caches/personal-website/site --link --check`, push again. *actions/configure-pages* with
  `Get Pages site failed`: the repository's Pages setting on GitHub is off (Settings > Pages > Source: GitHub Actions);
  nothing to fix here. The *smoke* job never holds a deploy back: a red mark there means a page script misbehaved in
  Chrome (its log names the page), and the site went out all the same.
- **The site is wrong after a push:** undo the commit with a new one, which is published like any push:
  `git revert --no-edit <sha>` and then `git push` (for several commits, revert each, newest first, then push once).
  The deploy takes about three minutes, and a push cancels a run still in progress, so do not wait for a bad deploy to
  finish. Never force-push and never rewrite history: the old commits stay public either way
  (`docs/PRIVACY_NOTES.md`, section 6). Watch it with `gh run watch` or the Actions page. (Not rehearsed yet: the first
  rehearsal, on a commit that changes only a document, is due at the next publication and its minutes go here.)
- **I need an old version back for a moment:** `gh run list` shows the last runs; `gh run rerun <id>` with the id of
  the last good one deploys that commit again with no commit of yours, is offered for 30 days after the run, and is
  undone by the next push. `gh workflow run pages.yml -f ref=$(git rev-parse <sha>)` builds and deploys any commit on
  `main` (give it the full 40-character id, which `git rev-parse` prints for a short one; it runs
  that commit's tests and check first; only someone with write access can start it); it too lasts until the next push,
  so follow it with a revert. (The `ref` input exists once this phase's `pages.yml` is on `main`; it has not been
  tried yet.)
- **A trip I drafted is still on the site:** look at the run (`gh run list --limit 1`). A red X means the build or the
  check stopped, often on something that still names the trip (Taking a trip off the site, above). A green run with
  the trip's number still in a cluster is expected until `render.py --site` (same section).

### The Mac

- **The build takes minutes instead of seconds:** iCloud Drive has offloaded files under `rendered/` and each one
  downloads as the build reads it. In Finder choose Keep Downloaded on the folder, or move the checkout out of iCloud
  Drive (README.md); `python3 tools/doctor.py` counts the offloaded files.
- **git says the index is missing or unreadable:** run `git read-tree HEAD`, then `git status --short`. Nothing is lost
  but the list of what was staged, so `git add` again what you had staged. Then free disk space: iCloud removed
  `.git/index` once when the disk was nearly full. `python3 tools/doctor.py` checks for this, and lists stray
  `.git/index 2`, `index 3`, ... copies with the line to delete them once `git status` works.
- **A map has no roads or lake names after a render:** OpenStreetMap was busy. The check says so (`maps were drawn
  without OpenStreetMap data ...`); run `python3 tools/render.py` again later, it retries anything that did not finish.
  For newer OpenStreetMap data (a new trail, a renamed lake), delete the cache's `osm/` folder
  (`~/Library/Caches/personal-website/osm/`, or `.cache/osm/` in this folder until the caches have been moved:
  `docs/DEVELOPING.md`, "Render caches"), or one answer in it, then run `python3 tools/render.py --site --force`. That
  downloads every answer again (one is about 200 MB) and can change roads and labels on every map; stage `rendered`
  after it.

More detail on how the site works: `README.md`, `docs/CONTENT_GUIDE.md` and `docs/DEVELOPING.md`.
