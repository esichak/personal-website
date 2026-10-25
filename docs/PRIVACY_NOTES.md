# Privacy notes

What this site and its public repository tell a stranger about where and when these trips happened, and which
decisions about that are yours. Counted on 2026-10-10, during Phase 4 of the redesign. Phase 4 wrote this down and
changed none of it.

Nothing here names a trip or a place. The repository is public, and a list of the spots that repeat would be the
exposure this note is about. For the same reason nothing here is a figure about one track, or about one or two
places: no earliest or latest start, clock times only to the quarter hour, no count of places below three.
Section 7 says how to see the specifics on your own machine.

The counts below come from one command, which only reads and prints. This note repeats what its default report
prints and nothing that report withholds. The few statements that need a flag, or come from git or from reading
the code, say so.

    python3 tools/privacy_audit.py

## 1. What the site publishes

- **340 recorded tracks, in full.** 156 single-day reports, 34 days of the 10 multi-day trips and the 150 days of
  the journal. Each is a GPX download; a multi-day trip also offers one combined file. A build copies each file
  unchanged (from the code of `tools/build.py`). Given a full build, `--site` (section 7) compares every copy with
  its source byte for byte. The build made for this note used `--link`, which puts a link to the source in place
  of each of the 341 copies (the 340 tracks and the one planned route), so there was nothing to compare.
- **Starts and finishes are not trimmed.** Nothing in the import or the build cuts a track short: `add_trip.py`
  keeps the first and the last point of what it reads (from the code), the maps mark both ends, and the map
  captions and the About page say "not trimmed".
- **Every point has its time.** All 340 tracks carry a timestamp on every one of their 314,316 points. No track
  was imported with `--strip-times`.
- **Points may be thinned, never moved.** `add_trip.py` drops points that add less than 2 m of detail (from the
  code). Measured over the 340 files, the median file has a point every 20 seconds and every 19 m; one file in
  ten is at 3 s or less, one in ten at 28 s or more.
- **Elevation** is on every point of 332 tracks. The other 8 have it on some points or on none.
- **Nothing else is in the files.** No extensions (heart rate and the like), links, waypoints, named points, GPS
  quality fields or comments. Each holds a name, a time, a type (the activity) and the creator text "Eric Sichak
  trip reports".
- **The planned route** (one, on the tick list) is a line with no times and no elevation. It is a single file, so
  the report gives no point total and no spacing for it.
- **Dates and start times.** Every report shows its date. A single-day report and each day of a multi-day trip also
  show a start time to the minute, and in all 340 cases the `start_time` in the front matter is the track's first
  timestamp. The journal page shows dates only; its GPX files carry the times all the same.
- **Photos carry no metadata.** None of the 1,004 files in the trips' `photos/` folders has EXIF, XMP or a colour
  profile. Every file in those folders is counted, whatever its name, because the build publishes every one. (The
  number grows with every photo and every size; the claim is the zero.)
- **Companions.** 13 of the 352 trip and day files have a `party:` line, shown on the page as "WITH ...". Titles
  and write-ups name people too. Those are your words, published as written, and nothing counts them.
- **Not written out on the site, as far as the check sees.** In the same build `--site` read 1,452 text files: the
  pages, the drawings, the two search indexes, the feed, the sitemap, robots.txt, the script and the style sheet.
  - None held the latitude and the longitude of the first or the last point of any of the 341 GPX files. The check
    looks for each of those 682 points with both of its numbers in one file, written with three or more decimals,
    rounded or cut short, in either order and whatever stands between them (a comma, a key, an attribute name).
  - None held a Strava id or a time zone name from the front matter.
  - A second, cruder count takes any two numbers with four or more decimals, within 40 characters of each other,
    that could be a latitude and a longitude. That count is 0. A further 78 files have such pairs only between CSS
    custom properties: `tools/sitegen/core.py` writes the proportions of the photos in a row that way, for the
    layout. They are counted apart so that a position on one of those pages would still show in the first count.
  - The check does not look for a position in another notation (degrees and minutes, whole numbers, an encoded
    line) or one written with fewer than three decimals, and it cannot see what an image shows. The maps draw every
    track over the terrain with its two ends marked, so where a track starts can be read off a map by eye. That is
    the first point of this section, not something this check rules out.

  The feed dates each item at noon UTC on the trip's date, not at its start time (from the code).

## 2. What the repository adds

The repository is public (checked with `gh repo view` on 2026-10-10), so a file in it is published whether or not a
page links to it:

- the same 341 GPX files, as `track.gpx` and `days/NN.gpx`;
- `strava_id` in the front matter of 340 of the 352 trip and day files. No page shows it (it is in none of the
  site's text files) and nothing but the audit and `add_trip.py --strava-export --list` (which leaves out the
  activities it names) reads it. `add_trip.py` itself writes no `strava_id` line;
- `start_time` in 340 of them and `timezone` in 167;
- `rendered/trips/<slug>/meta.json` for 168 trips, each with the start point and the end point written out as
  numbers. The build does not copy these files to the site;
- `rendered/site/`, the region maps as `tools/render.py` last drew them, with the line and the title of every trip
  they showed then (decision 3);
- any trip marked `draft: true`: no page and no download, its files in the repository all the same (there is none
  today);
- every earlier version of every file. Today the history holds 341 GPX files, the same 341, and 1,682 images, none
  with metadata (counted with `git rev-list --objects --all`, not by the tool).

`draft: true`, a removed button or a file deleted in a new commit takes a page or a download off the site at the
next build. It does not take a trip's line off the region maps until they are drawn again (decision 3), and it
takes nothing out of the history, or out of a copy somebody already has.

## 3. What the tracks add up to

One track shows a route. 340 of them, with times, show habits. Taking "the same place" as within 150 m:

- 165 tracks finish within 150 m of their own start.
- 129 tracks start or finish where three or more tracks do (the track itself counted) and 68 where five or more
  do. Counting a multi-day trip or the journal once, because last night's camp is the next morning's start, the
  two numbers are 105 and 61. For ten or more the report gives no count: it would be a count at fewer than three
  places.
- Chained together, the starts and finishes make 274 places. 29 of them are shared by two or more separate
  outings, 16 by three or more and 5 by five or more; by ten or more, fewer than three. 105 tracks start or finish
  at one of the 16.
- At all of the 16, or all but one or two (the report does not say which), every track starts on a different
  date. At 8 the starts fall in more than one calendar year, and 3 are used for more than one activity. At 3 the
  start times stay within 90 minutes of each other; at 7 they are spread over four hours or more.
- A different radius moves the numbers, not the picture: with `--radius`, 105 tracks start or finish where three or
  more do at 50 m, 129 at 150 m, 140 at 300 m and 154 at 1,000 m.
- To the quarter hour, half of all tracks start before 08:00 local time, one in twenty before 05:30 and one in
  twenty after 16:30. 44% start on a Saturday or Sunday (62% of single-day reports). Times are read in each trip's
  `timezone:` field, so where that field is wrong the time is too.

What the counts cannot say is what any place is. A shared start may be a trailhead, a car park, a hut or a front
door. The files do not tell these apart and this note does not try. The counts also cannot see a private place
visited once, because one track is not a group; `--near` (section 7) is for that.

## 4. What Phase 4 did not change

- No track was trimmed, thinned again, re-timed, replaced or removed. `git diff --name-only a9baab9 HEAD -- '*.gpx'`
  prints nothing, and so does `git status --short -- '*.gpx'`: the 341 GPX files are what they were before the
  redesign began.
- No timestamp, start time, date, companion's name or Strava id was removed or hidden.
- No history was rewritten. The branch only adds commits on top of what is already public.
- No switch was added that hides a label while the data stays public. A switch in the page would not make past data
  private: the GPX download keeps its times and its two ends whatever the page shows, the repository holds the
  source file, the history holds every earlier version, and nothing recalls a copy that was already downloaded,
  cloned, cached or archived.
- The README's privacy paragraph stands as written, with one sentence added that points to this note.
- The site can now build the page of a report whose `track.gpx` has been removed (decision 3). No report is in
  that state: the count of trips without a GPX file is 0.
- `tools/privacy_audit.py` is new. It reads and prints. It writes no file and adds nothing to the site, and neither
  the build nor CI runs it.

## 5. What `add_trip.py --strip-times` does and does not do

Read from the code. No existing track uses the flag, so none of this has been seen on a published trip.

- It leaves the time off every point of the GPX it writes, and off the file's own header.
- It still writes `start_time` (local, to the minute) and `date` into the front matter, and the page shows both.
- It still records the moving and elapsed time in `stats`.
- It changes no position. The start and the finish are where they were.
- It works at import only. Nothing in the repository strips the times from a track that is already there.

So a trip imported with the flag has a GPX without times and a page that still says on what day and at what time
it started.

## 6. Decisions that are yours

Each of these changes what is published. None was made for you, and nothing here says which way to decide.

1. **Trim the starts and finishes of future tracks.** There is no option for it. Trimming the file before
   `add_trip.py` reads it keeps the download, the maps, the profile, `start_time` and `meta.json` in step, because
   all of them come from that file; stats taken from a Strava export would still be for the whole activity. The map
   captions, the About page and the README say "not trimmed" about every track and would have to change.

   A track that is already published takes more. For a single-day trip (since Phase 9), trim a copy of the original
   file and run `python3 tools/add_trip.py TRIMMED.gpx --update <slug> --source Strava` (the service the file came
   from; every published trip credits its stats to one, so `--update` asks): it replaces `track.gpx` and works `date:`,
   `start_time:`, `route_shape:` and `stats:` out again from the trimmed file, keeps every other line and the write-up,
   and draws the maps again (`--dry-run` shows the changes first). It keeps the file's timestamps: `--strip-times` is
   refused on an update while decision 2 is open. For a day of a multi-day trip or of the journal it is still by hand:
   - edit its GPX;
   - by hand, in the day's file, set `start_time:` to the new first point's local time and `stats:` to the shortened
     track's figures, and `date:` too if the cut crosses midnight. Left alone, the page keeps the old start time and
     the whole activity's distance and times beside a download that begins later, and the difference says how long and
     how far the removed part was;
   - then run `python3 tools/render.py` and commit `rendered/`: the maps, the profile and the two points in
     `meta.json` are drawn from the file, and the mile markers are scaled to the distance in `stats:`;
   - check it with the audit's line "start_time in the front matter ... equal to the track's first timestamp, to the
     minute", which should count every track again (340 of 340 today). Nothing checks `stats:` or `date:`.

   The old file stays in the history (decision 6).
2. **Drop timestamps.** New imports: `--strip-times`, with the limits in section 5. Existing tracks: rewrite each
   GPX without its times and decide what happens to `start_time`. A flat-water trip's speed chart is drawn from the
   times. The old files stay in the history.
3. **Remove a trip, or only its track.** There are three ways, and a push alone finishes none of them.
   - `draft: true` in its `index.md`: the next build leaves out its page, its photos and its downloads. Every file
     stays in the repository.
   - Deleting its folder: the same, the files leave the current tree, and the page's address stops working.
     `render.py` removes `rendered/trips/<slug>/` the next time it runs.
   - Deleting only `track.gpx` from a single-day report: the page keeps its write-up, photos and stats. At the next
     build it loses its map and the full-screen map page, its links to the route, its elevation profile or speed
     chart, its GPX download, and the small route drawings other pages show beside its name; the build no longer
     publishes anything from `rendered/trips/<slug>/`, though that folder stays in the repository until it is
     removed. (Read from the code for a single-day report; a day of a multi-day trip or of the journal was not
     looked at for this note.)

   In all three cases the region maps are a separate matter. The maps on the home page, on the Map page, the region
   pages and the Ski page are drawn by `tools/render.py` on your Mac and committed under `rendered/site/`; a build only
   places them. Since Phase 8 the build leaves the trip's own pin and line out of them, so the check passes and the
   trip leaves those maps at the same build as its page. A numbered cluster the trip was merged into keeps counting
   it, with its title in the cluster's tooltip, and the committed map files under `rendered/site/` still hold the
   line, until `python3 tools/render.py --site` has been run and `rendered/site/` committed. `python3 tools/validate.py`
   prints a warning for each such trip ("the site maps under rendered/site/ still draw this trip ..."), and a build
   prints the first few of its warnings as it starts.

   Three things stop the build when a report is made a draft or deleted: a place among the featured trips in
   `content/home.json`, a tick-list goal whose outing names it, and a link to it from another report's write-up.
   A build that stops deploys nothing, so the old site stays up, the page and its download included, until the
   other file is changed as well.

   `render.py` covers a report without a track as well (read from the code on 2026-10-10; the renderer was not run
   for this note): it draws nothing for it, deletes the report's `rendered/trips/<slug>/` folder and leaves the
   report out of the region maps the next time it draws them. So each of the three ways can be followed by the
   render that takes the line off those maps.

   Whichever way, the files stay in the history.
4. **The Strava ids, and the start and end points in `meta.json`.** The `strava_id` lines can be deleted from the
   340 files with no effect on the site. Whether an id leads anywhere depends on what is public on Strava itself.
   `meta.json` gets its start, end and bounding box from `tools/render.py`. A search of `tools/sitegen/` finds
   nothing that reads them, so dropping them means changing the renderer and rewriting the 168 files. The same two
   points are the first and last lines of each GPX in any case.
5. **Companions' names.** Whether each person is content to be named beside a dated, timed track. `party:` is one
   line in each of 13 files. A name in a title is in the page's address too; a name in a write-up is your text.
6. **Rewrite history.** The only way to take a file out of the repository's past. It needs a history-rewriting
   tool, a force push and a fresh clone everywhere. It breaks links to old commits and recalls nothing already
   cloned, forked, cached or archived. The plan keeps it out of a design release.

## 7. Looking at the specifics yourself

    python3 tools/privacy_audit.py                  # the counts in this note, from today's files
    python3 tools/privacy_audit.py --radius 300     # a wider idea of "the same place"
    python3 tools/privacy_audit.py --min-cluster 5  # only places that five or more outings share
    python3 tools/privacy_audit.py --site _site     # also a built site: GPX copies, text files, images
    python3 tools/privacy_audit.py --list           # exact figures, each shared place's trips and rounded position
    python3 tools/privacy_audit.py --near           # asks for a point and counts the tracks around it

It works offline and looks nothing up. The default report is the one this note is written from: counts, with
nothing about one track or about one or two places. `--list` has what that report withholds (the earliest and the
latest start, every hour, every count of places) and names the trips; it prints to a terminal only, and its first
line says it is for you. Keep its output out of the repository, commit messages, issues, pull requests and CI logs:
all of those are public. `--near` does not show, store or print the point you type.

The listing made on the day of this note, with the observations that name trips, is in
`.cache/p4/PRIVACY_AUTHOR_ONLY.md` on your machine. Git ignores that folder; keep the file there.
