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
cd ~/Documents/"Claude Code"/personal-website
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
| `--timezone` | The trip's time zone as an IANA name, e.g. `America/Chicago` (optional). Without it the tool guesses from where the track starts and prints the zone it used (`timezone America/Denver, guessed; --timezone to change`); the date and the start time are worked out in that zone |
| `--party` | Who you went with, e.g. "Adam" (optional) |
| `--photos` | A folder of photos, or individual photo files (optional) |
| `--draft` | Keep the trip off the site until you remove `draft: true` from its file. A draft you push is still in the public repository. Its maps are not drawn while it is a draft: after you remove the line, run `python3 tools/render.py <trip-name>`. To push a draft, stage `"content/trips/<trip-name>"` alone in step 5. For a trip that is already on the site, see "Taking a trip off the site" below |
| `--strip-times` | Write the GPX without timestamps. The page still shows the date and the start time (see `docs/PRIVACY_NOTES.md`) |
| `--no-render` | Skip drawing the maps, so no internet is needed. Draw them later with `python3 tools/render.py <trip-name>` |
| `--force` | Import again over a folder that is still an untouched import: the placeholder report, empty `alt:` lines and nothing you added. It is refused, and nothing is written, once the folder has a write-up, a photo description, a line such as `beta:`, `map:` or `cover_photo:`, day files or a `goal.json` ("If something goes wrong", below) |

Two more commands share the script; neither adds a trip:

| Command | What it does |
| --- | --- |
| `python3 tools/add_trip.py --retime <trip-name> --timezone America/Chicago` | Sets the trip's time zone and works its `date:` and `start_time:` out again from its own `track.gpx`, which keeps the time of every point; it prints each line old and new. Without `--timezone` it uses the zone the file already names. Offline; no map is drawn again. A trip with day files, or whose track has no times, is refused |
| `python3 tools/add_trip.py --strava-export "/path/to/Strava export folder" --list` | Lists the activities of a Strava export that no `strava_id:` line of a trip or a day names, newest first: date, activity ID, type, distance, whether it has photos, name. `--type Hike,Ride` and `--since 2026-01-01` narrow the list. It only prints. The `strava_id:` lines are the first bulk import's; `add_trip.py` writes none, so an activity added with `--strava-id` stays on the list (add the line to its `index.md` by hand to drop it: `strava_id: "<activity id>"`) |

Regions already on the site: Lake Tahoe, Santa Cruz, Eastern Sierra, Boise, Bay Area, Tetons, Alps, Oregon, Utah,
Yosemite, Washington, Idaho, Minnesota, Arizona (the PCT journal has a region of its own, Pacific Crest Trail). A new
region name is fine too; it gets its own region map once it has three trips with a track. An active tick-list goal
with a route counts as one of the three; a report without a track does not. Until the region maps are drawn again
the Map page does not list the new region, and the check prints a `WARNING` for the trip that ends
`run python3 tools/render.py --site --force`: run that (internet needed) and stage `rendered/site` with the trip. A
name that differs from an existing region only in capitals, accents, apostrophes or other punctuation is not a new
region but a second spelling of that one. `add_trip.py` refuses such a spelling and names the one to use
(`region "eastern sierra" is written "Eastern Sierra" on N trips; use that spelling`); for a `region:` line typed by
hand the content check warns instead: correct it rather than running the command (`docs/CONTENT_GUIDE.md`, 11.4). A
name no trip uses yet is a new region, and the command says so (`new region: ...`) and lists the existing ones.

A region that has a region map and at least one published report also has a page of its own, `regions/<region>/`. The
address is made from the name: lower case, accents folded to plain letters, apostrophes and characters with no
plain-letter form dropped, and every run of what is then neither a letter nor a digit turned into one hyphen (none
at the ends). `Lake Tahoe` gives `regions/lake-tahoe/`, and
`Val d'Isère` would give `regions/val-disere/`. The first eight regions in the list above have one today. A region
whose map draws planned routes only has none. Nothing is written for the page: its head is counts, years and places
taken from its trips, and under that come the region's map, up to three Featured reports and every report of the
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
- The other optional lines (the cover photo and its crop, the card summary, search names, and the `published_at` and
  `updated_at` dates) are described in `docs/CONTENT_GUIDE.md`.

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

Run the build check, stage this trip's files by path, and list what is staged:

```bash
python3 tools/build.py --check
git add "content/trips/rose-knob-peak" "rendered/trips/rose-knob-peak" rendered/site
git status --short
```

Put your trip's folder name in place of `rose-knob-peak`. Then read what the three commands printed before you go
on. They run one after the other whatever each one answers, so a failed check does not stop the `git add`. Go on only
when both of these are true:

- The check ended with `link check: OK`. When it stops with `ERROR` lines, or ends with `link check: N problems`, fix
  what the lines name and run the three commands again.
- Every staged name in the list is a file of this trip or a map under `rendered/site/`. How to read the list, and
  what to do with a name that does not belong, comes after the table below.

If the check prints a `WARNING` line for your trip that says `no rendered map`, its maps were not drawn (no internet
at the time, or `--no-render`): run `python3 tools/render.py <trip-name>`, then the three commands again. `git add`
does not always catch this.

Then commit and push:

```bash
git commit -m "Add Rose Knob Peak"
git push
```

Which paths to give `git add`:

| What you did | Paths |
| --- | --- |
| Added a trip, or a day of one | `"content/trips/<trip-name>"`, `"rendered/trips/<trip-name>"` and `rendered/site` |
| Added a trip with `--draft`, to push it as a draft | `"content/trips/<trip-name>"` alone: a draft has no maps yet |
| Edited a trip's text, photo descriptions or other lines, with no render | `"content/trips/<trip-name>"` |
| Ran `render.py <trip-name>` after changing a track, a title or a `map:` setting | all three, as for a new trip |
| Ran `render.py` with no trip name | `rendered` (the whole folder), plus the `content/trips/<trip-name>` folders you edited |
| Changed the home page's features | `content/home.json` |

A folder path stages what is new, changed or deleted inside it. `rendered/site` holds the region maps, which a render
redraws along with the trip's own; naming it when nothing changed there does no harm. The trip is in the lists of its
region's page (`regions/<region>/`) without it; `rendered/site` is what puts the trip's line and pin on the map there,
as on the Map page.

Never use `git add -A` or `git add .`. This folder syncs through iCloud Drive, which sometimes leaves a conflict copy
of a file: the same name with a space and a number added, such as `meta 3.json` or `index 2.md`. `.gitignore` hides
the copies under `rendered/` and `assets/`, but one can appear in any folder, and `git add` on a folder takes
everything in it. The content check names a copy that sits in a trip's folder or in its `days/`. For most that is a
`WARNING`. A copy of a day file stops the build, because it would go out as one more day of the trip:

```
ERROR content/trips/rose-knob-peak/days/02 2.md: looks like an iCloud conflict copy (the name ends in a space and a number): it would be published as one more day; delete it
```

A warning stops nothing, so still read the `git status --short` list before you commit. A letter in its first column
marks a staged file (`A` new, `M` changed, `D` deleted, `R` moved), and each of those should be a file of this trip
or a map under `rendered/site/`. If a staged path has a name with a space and a number added, as in `index 2.md` (git
shows such a path in double quotes), unstage it with `git restore --staged "<path>"`. For a copy of a file you write
yourself (`index.md`, a `days/NN.md`), compare it with the original first, because the copy may be the one with your
newer text. Then delete the copy.

Only the `main` branch is published. On every push to `main` GitHub runs the unit tests and `build.py --check`, and
deploys when both pass; the trip is live a few minutes later. A push to any other branch runs nothing and the site
stays as it was. `git branch --show-current` says which branch you are on. If it is not `main`, the push publishes
nothing, and on a branch that was never pushed `git push` stops with
`fatal: The current branch <name> has no upstream branch`. The trip goes live only when its commit is on `main` and
`main` is pushed.

## Quick fixes from anywhere

For small text changes (a typo, a better title, a photo description), you can edit the trip's `index.md` directly on
github.com: open the file on the `main` branch, click the pencil, and commit. The site redeploys on its own. Run
`git pull` in this folder before your next local change so the two stay in step. That brings the edit only when this
folder is on `main`: on another branch `git pull` leaves it out, and on a branch that was never pushed it answers
`There is no tracking information for the current branch`.

## Taking a trip off the site

Put `draft: true` among the lines above the closing `---` of the trip's `index.md`, or remove its folder from
`content/trips/`. A build then leaves out the trip's page, its photos, its GPX download and its own map. The trip
also leaves the lists and the counts on its region's page at that build, and a region left without a report loses its
page. A region left with no report and no tick-list goal also leaves the Map page's region maps and the home page's
`ALSO` row at that build; with a goal still filed under it, see `docs/CONTENT_GUIDE.md`, 11.4. Two things stand
between that build and the site:

- **The region maps still draw the trip.** The maps on the home page, the Map page, the region pages and the Ski
  page are drawn by `render.py` and committed under `rendered/site/`; a build only places them. They keep the trip's
  line and title until you run `python3 tools/render.py` (internet needed). Where the trip has a pin of its own on a
  map, the pin links to the page that is gone, and `build.py --check` fails on it with lines such as
  `BROKEN map/index.html -> ../trips/<trip-name>/` and, for its region's page,
  `BROKEN regions/<region>/index.html -> ../../trips/<trip-name>/`. Where its pin is merged with others, the check
  passes and the line stays on the map. So run `render.py` before the check of step 5, and stage `rendered` with the
  trip's folder, as the table there gives for a run with no trip name. Until the maps are drawn again the content
  check prints a `WARNING` for the trip that begins `the site maps under rendered/site/ still draw this trip`. That
  run can take more than the trip's line away: a region left with fewer than three trips with a track gets no region
  map from it, and without the map the region has no page. Its remaining reports are then listed on the Map page
  under "Not on a region map", and their links to the region lead there.
- **The build stops while something else names the trip:** `content/home.json`, a tick-list goal's outing
  (`report_slug` in its `goal.json`), or a link in another trip's write-up. Each `ERROR` line names the file to
  change.

GitHub publishes nothing when the build stops or the check fails, so the page and its download stay on the site until
both pass.

Deleting only `track.gpx` from a single-day report keeps its page, with the write-up, the photos and the stats. The
page loses its map, its elevation profile or speed chart, its links to the route and its GPX download, other pages
no longer draw the small route beside its name, and the check prints a `WARNING`:
`no track.gpx: the page has no map, no profile and no GPX download`. The region maps keep the trip's line until
`render.py` has been run; its pin still leads to a page, so `--check` passes meanwhile. That run also deletes the
report's `rendered/trips/<trip-name>/` folder, which the site no longer uses, so stage `rendered` after it. A report
without a track is drawn on no region map, so after that run the Map page no longer names it in its region's list. It
stays on the Trips page, in the Map page's table of all reports and, as long as the region still has a region map, in
the lists and the counts of its region's page (`docs/CONTENT_GUIDE.md`, section 11.4). A report without a track does
not count towards the three trips a region map takes, so the same run draws no map for a region that is left with
fewer than three trips with a track. The region's page goes with the map, and the Map page then lists the region's
reports, this one included, under "Not on a region map".

None of this takes a file out of the repository's history (`docs/PRIVACY_NOTES.md`, section 6).

## Or let Claude do it

Open Claude Code in this folder and say something like: *"Add this trip: ~/Downloads/Morning_Ski.fit, photos in
~/Desktop/rose, ski tour on Rose Knob Peak with Adam."* Claude runs the steps above, writes the photo descriptions,
previews the page and publishes it as in step 5.

## If something goes wrong

- **`cwebp` not found:** run `brew install webp` (photos fall back to larger JPEGs without it).
- **A map is missing its roads or lake names:** OpenStreetMap was busy. The check says so (`maps were drawn without
  OpenStreetMap data ...`). Run `python3 tools/render.py` again later; it retries anything that didn't finish. Then
  stage what the table in step 5 gives for a run with no trip name.
- **A render stops with `! <trip-name>: ...`:** that trip's drawing failed (a terrain tile that would not download, a
  file it could not read). Its last good maps stay where they were, the run goes on with the other trips, and it ends
  with `1 failed, their last good maps kept: <trip-name>`. Run the same command again later. A render you stop with
  Ctrl+C also leaves the maps as they were.
- **Changed a trip's title or map settings:** run `python3 tools/render.py <trip-name>` to redraw its maps, then
  stage `rendered/trips/<trip-name>` and `rendered/site` with the trip's folder (step 5). The check reminds you
  (`maps were drawn from other inputs ...`). `python3 tools/render.py --status` lists, without the internet, every
  trip a render would draw and why, and whether the region maps are up to date.
- **Newer OpenStreetMap data (a new trail, a renamed lake):** a downloaded answer is kept and used for ever. Delete the
  cache's `osm/` folder (`~/Library/Caches/personal-website/osm/`, or `.cache/osm/` in this folder until the caches
  have been moved: `docs/DEVELOPING.md`, "Render caches"), or one answer in it, then run
  `python3 tools/render.py --site --force`. That downloads every answer again (one is about 200 MB) and can change
  roads and labels on every map, which the change check does not notice; stage `rendered` after it.
- **`add_trip.py --force` stops with `... --force would erase them`:** the folder is not an untouched import any more
  (a write-up, photo descriptions, lines you added, day files or a `goal.json`), and nothing was written. To import the
  recording again, move the folder out of `content/trips/` first; git keeps the committed version, and
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
- More detail on how the site works: `README.md`, `docs/CONTENT_GUIDE.md` and `docs/DEVELOPING.md`.
