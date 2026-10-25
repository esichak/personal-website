# Tick list guide: goals, GPX imports, review, completion

How to save a route you want to do, attach a GPX, keep the research honest, publish the goal, and later record what
happened. Everything runs in this folder on your Mac with one local tool, `tools/ticklist.py`; the public site only
shows what you commit and push to the `main` branch. The list lives at `tick-list/`, each goal at `trips/<slug>/`.

Adding a finished trip is in [ADDING-TRIPS.md](../ADDING-TRIPS.md); homepage features, covers and search are in
[CONTENT_GUIDE.md](CONTENT_GUIDE.md); how the generator works is in [DEVELOPING.md](DEVELOPING.md).

## 1. What the tick list is, and is not

- **A goal is a planned route, and it stays one.** It is a `kind: planned` folder under `content/trips/`, the same
  model the map's Planned group already uses. Its title, URL and planned GPX never change because you did it. When
  you do go, the outing is a separate report, added with `add_trip.py` from your own recording; the goal gets an
  `outings` entry pointing at that report, and the report (single-day, multi-day or a journal) gets an automatic "On the tick list" line pointing back.
  Nothing is counted twice: goals never enter report counts, completed mileage, the Trips page, search, the home
  page's featured and recent cards or the RSS feed. Where a page mentions them it says so: "+ 1 PLANNED ROUTE" beside
  a count of reports, a row under "Planned", or a row marked PLANNED at the end of a region's list.
- **The minimum entry is a name and an activity.** A GPX, a region, notes and research are all optional. Saving an
  idea must take one command, not a questionnaire.
- **Status is intent, not readiness.** `shortlisted` means you want to do it soon; it never means safe, in condition
  or within your ability. The site shows status as a read-only badge. There is no public checkbox, upload form or
  login, and nothing a visitor does changes your list.
- **Unknown stays unknown.** A route with no elevation in its file has no gain, not zero gain. A goal without a
  track shows "Route not added yet". The site never invents a date, a duration, a grade or a summit.
- **Everything committed is public**, including `draft: true` goals, sidecars and GPX files. Section 7.
- The planned routes that were on the site before the tick list (for example a folder with only `index.md` and
  `track.gpx`) keep working with default goal metadata (`idea`, `normal`, nothing else) until you give them a
  `goal.json`. The first `update` on such a route writes one: the defaults plus your change, with `added_at` left
  `null` (set it by hand if you know the day). `export` lists the routes that still have none (section 4.6). Their
  goal page says the GPX's source was not recorded, because no checksum or source exists for them.

## 2. The files

```
content/trips/<slug>/
  index.md      kind: planned; title, activity, place, region, approximate stats; body = planning notes
  goal.json     intent, provenance, references, checklist, outings (optional; defaults apply without it)
  track.gpx     the approved public copy of the route (optional)
rendered/trips/<slug>/   maps, tile and glyph, drawn on your Mac by render.py
```

Nothing is written twice: `index.md` holds what every trip has (title, activity, place, region, stats, the body);
`goal.json` holds what only a goal has. A new goal's `index.md` is as small as this, and the importer writes it:

```yaml
---
title: YOUR ROUTE NAME
activity: hike
kind: planned
draft: true
---
```

`draft: true` keeps the goal off the built site until you remove the line (section 5). A goal never gets a `date`:
a recording's date, an import date or a hoped-for date would all read as a trip date. The import date is
`added_at` in `goal.json`; your planning window is `target_months` and `target_year`.

A `goal.json` with every default, which is what `add` writes before applying your options:

```json
{
  "schema_version": 1,
  "status": "idea",
  "priority": "normal",
  "archived": false,
  "tags": [],
  "why": "",
  "added_at": "2026-10-09",
  "target_months": [],
  "target_year": null,
  "time_commitment": null,
  "season_notes": "",
  "difficulty": null,
  "route_scope": "unknown",
  "route_source": {"kind": "unknown", "url": null, "label": null, "checked_at": null,
                   "public_copy_approved": false, "approximation_note": null},
  "references": [],
  "field_evidence": {},
  "checklist": [],
  "outings": [],
  "route": null
}
```

Every key is optional in the file; a missing one takes its default. You can edit `goal.json` by hand (plain JSON,
double quotes, no trailing commas); `python3 tools/validate.py` and every build check it, and a build stops with a
message naming the field if a value is wrong (section 9). A `goal.json` beside a report (anything that is not
`kind: planned`) is an error, so a finished trip can never be slipped into the future list.

## 3. Fields

**In `index.md`** (the usual trip fields; `ticklist.py add` fills them from its options):

| Field | Required | Meaning |
| --- | --- | --- |
| `title` | yes | The route's name as it should appear. Keep the name the route is known by. |
| `activity` | yes | `ski`, `climb`, `hike`, `mtb` or `other` (`subtype` with `other`: `SUP`, `Rafting`, `Kayaking`, `Mountaineering`). Tags never create a new activity. |
| `kind: planned` | yes | What makes it a goal. Never change it to turn a goal into a trip. |
| `draft: true` | on creation | Off the site until removed. Not a goal status and not a privacy control. |
| `place`, `region` | no | "Desolation Wilderness", "Lake Tahoe". Reuse an existing region name so the goal joins that group; without one it sits under "No region yet". Coordinates alone never become a place name. |
| `route_shape` | no | `loop`, `out-and-back`, `point-to-point`, when you know it. |
| `stats` | importer only | `distance_km` always; `gain_m` / `loss_m` only when every point in the file has an elevation; `high_m` / `low_m` when any does. Written by `--publish-track`; shown everywhere as approximate ("≈ 12.3 MI · ≈ 2,100 FT GAIN", in MI or KM): on the tick list, the goal page, the Hiking page's Planned rows (the other activity pages count a planned route and do not list it) and the rows and table of the map page and of the goal's region page, where the top of the line is labelled "High point", not "GPS max". "Highest point in the file" is not "summit elevation". |
| body | no | Planning notes, shown under the heading "Planning notes" (never "Trip report"). `add --notes` writes the first version. |

**In `goal.json`:**

| Field | Values | Meaning and rule |
| --- | --- | --- |
| `status` | `idea` (default), `researching`, `shortlisted`, `attempted`, `completed` | Where the goal is in your head. Any direct change is allowed. `completed` needs an outing with outcome `completed` (and vice versa, until the goal is reopened); `attempted` needs an outing with outcome `attempted`. Set these with `log-outing`, not by hand; open a completed goal again with `update --reopen` (section 4.3). |
| `priority` | `high`, `normal` (default), `someday` | Your ordering; the default sort on the list. Shown as "High priority" or "Someday"; normal shows nothing. |
| `archived` | `true` / `false` (default) | Takes the goal out of the active list, the "+ N planned route" counts (Home, the activity pages, the About page, the map page and its region's page) and the Planned rows (the Hiking page, the map page's region lists and table, its region's page); keeps its page, GPX and outcome. Separate from status, so an attempted or completed goal can be archived without losing its history. The region maps are drawings: its dashed line leaves them the next time `python3 tools/render.py --site` runs (needs internet). The same goes for a completed goal. |
| `tags` | list of short text | `scramble`, `ridge-traverse`, `couloir`, `backpacking`, and so on. Searchable on the list. |
| `why` | one sentence | Your reason, in your words. Nobody else writes this. |
| `added_at` | `YYYY-MM-DD` or `null` | The day the goal was saved; `add` sets it to today. Not a trip date. |
| `target_months` | unique integers 1-12 | When you would like to go. A planning window, not a statement about conditions. |
| `target_year` | 2000-2100 or `null` | Same, by year. |
| `time_commitment` | `null`, `half-day`, `full-day`, `overnight`, `multi-day` | Your or a source's estimate. Never derived from distance; a recorder's moving time is never used. |
| `season_notes` | text | What published sources say about the usual season. Kept apart from your months and from current conditions. **Needs an approved `field_evidence` entry** (below) when non-empty. |
| `difficulty` | `null` or `{"system": …, "value": …, "note": …}` | A grade with the system it belongs to (`"system": "YDS", "value": "Class 3"`), optional note for context. Systems are never converted into each other. **Needs an approved `field_evidence` entry.** |
| `route_scope` | `full-intended-route`, `approach-only`, `ascent-only`, `partial`, `unknown` (default) | What the file covers. Your statement or the source's, never a guess from the geometry. Shown beside the stats so an approach-only gain is not read as the whole objective. |
| `route_source` | object | Where the line came from. `kind`: `author-drawn`, `planner-export`, `third-party-recording`, `own-prior-recording`, `unknown` (default). `url` (http/https), `label`, `checked_at` (when you last read that page). `public_copy_approved`: set to `true` by `--publish-track`; it records that you approved copying the file into the repo. `approximation_note`: required text when `kind` is `author-drawn` (a sketch or traced line is not a travelled route). |
| `references` | list of `{"id", "label", "url", "checked_at", "note"}` | Sources: reports, guidebooks, the managing agency's access and permit pages. `id` is unique, lowercase letters, digits and hyphens; `url` is http or https; `checked_at` is the day you read it, not a guarantee it is still true. |
| `field_evidence` | `{"<field>": {"source_ids": […], "status": "proposed" or "approved"}}` | Which references back a researched field. Every id must exist in `references`; `source_ids` is never empty. `proposed` is research you have not reviewed and it does not publish the field; `approved` is your sign-off. |
| `checklist` | list of `{"id", "text", "done"}` | Questions still to answer before going. Public pages show them read-only ("Done" / "To check"). |
| `outings` | list of `{"outcome", "date", "report_slug", "note"}` | What actually happened, in order. `outcome` is `attempted` or `completed`; `date` and `report_slug` may be `null` when unknown or when there is no write-up; `report_slug` must name a published report (single-day, multi-day or a journal), never a planned route. Written by `log-outing`. Earlier attempts are kept when you finally complete. One more kind of entry, `"outcome": "reopened"` (a date, an optional note, never a report), is written by `update --reopen` after a completed outing: from there on the goal is open again and the history above it stays. |
| `route` | `null` or the derived block | Written by `--publish-track`, never by hand: `source_sha256` of `track.gpx`, `method` (`ticklist-gpx-1`), `selected` (`trk`/`rte`, index, name), `alternatives`, `segments`, `points`, `elevation` (`full`, `partial`, `none`), `times`, `waypoints`. If `track.gpx` changes after import, the checksum no longer matches and the build stops rather than quietly re-measuring. |

The evidence rule in one line: a difficulty or a season note appears on the site only when `field_evidence` for that
field is `approved` and every id in it is a real reference. Unreviewed research is never published, however
plausible.

## 4. Commands

Run everything from the site folder. Every subcommand takes `--dry-run`: it prints what would happen and writes
nothing. Use it first, every time.

```bash
cd ~/Documents/"Claude Code"/personal-website
```

### 4.1 Save an idea

```bash
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity hike --dry-run
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity hike
```

Creates `content/trips/your-route-name/` with `index.md` (`kind: planned`, `draft: true`) and `goal.json`
(defaults, `added_at` today). The slug is made from the title (lowercase, hyphens); pass `--slug` to choose it. An
existing folder is a hard error, never an overwrite: the message suggests `--slug`.

Optional flags. The `goal.json` ones work on `add` and again later on `update`; the `index.md` ones are `add`
only (edit the file by hand afterwards):

| Flag | Example | Writes |
| --- | --- | --- |
| `--place`, `--region`, `--subtype` (`add` only) | `--region "Lake Tahoe"` | `index.md` |
| `--notes TEXT` (`add` only) | `--notes "Start from the north trailhead."` | the body (planning notes) |
| `--priority`, `--status` | `--priority high --status researching` | `goal.json` |
| `--tags a,b` | `--tags scramble,ridge-traverse` | `tags` |
| `--why TEXT` | `--why "The long ridge."` | `why` |
| `--months 6,7`, `--year YYYY` | `--months 6,7 --year 2027` | `target_months`, `target_year` |
| `--commitment` | `--commitment full-day` | `time_commitment` |
| `--scope` | `--scope approach-only` | `route_scope` |
| `--source-kind`, `--source-url`, `--source-label` | `--source-kind third-party-recording --source-url https://example.com/route --source-label "Example source"` | `route_source` |
| `--checked-at YYYY-MM-DD` | `--checked-at 2026-10-09` | `route_source.checked_at`: the day you read the route source's page |
| `--approximation-note TEXT` | `--source-kind author-drawn --approximation-note "Traced on a planner map, not a travelled line."` | `route_source.approximation_note`; required whenever the kind is `author-drawn` |

### 4.2 Add a goal with a GPX

```bash
# Inspect only: the plan, the measurements and any problems. Nothing is written.
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity ski --gpx /absolute/path/route.gpx --dry-run
```

If the file holds more than one track or route, the report lists them (`trk:0`, `trk:1`, `rte:0`, each with its
name and point count) and the command stops there (exit code 2): nothing is created, not even the idea, in a dry run
or a real one. Pick one and run again:

```bash
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity ski --gpx /absolute/path/route.gpx \
  --select trk:1 --dry-run
```

Alternatives are never joined into one line. When you publish one of several, the public copy leaves out the file's
other tracks and routes, its waypoints and its `<metadata>` block. It still holds everything inside the track or
route you chose (its name, description, links, device extensions, timestamps, comments) and the file's opening `<gpx>`
tag with whatever stands before it (the `creator` text, a leading comment). A file with a single track or route is
copied whole, waypoints and metadata included. Either way the report ends with **"the published copy carries: …"**,
read from the exact bytes that will be written: that line, not an assumption about what was dropped, is the list to
check before you commit. To publish the chosen geometry as the goal's public route:

```bash
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity ski --gpx /absolute/path/route.gpx \
  --select trk:1 --publish-track --source-kind third-party-recording \
  --source-url https://example.com/route --source-label "Example source" --scope approach-only
```

**`--publish-track` means one thing:** you have looked at this file and approve copying it into the public
repository. It copies the selected geometry to `content/trips/<slug>/track.gpx`, writes the approximate `stats` into
`index.md` and the `route` block into `goal.json`, sets `route_source.public_copy_approved` to `true`, and then starts
`python3 tools/render.py <slug>` (skip that with `--no-render`; a failed render is a warning and the goal is still
valid, section 6). That run draws no map for the goal: a new goal is a draft, and `render.py` leaves drafts out. The
command says so in its last lines, quoted at the end of this section. It does **not** commit, push or deploy
anything, does not approve any other field, and says nothing about whether the route is safe, complete or feasible.

Without `--publish-track` the file is only read: the report prints its measurements for you, and the goal is created
metadata-only, with no `stats`, no `route` block and no copy of the file. Nothing from an unapproved file reaches the
checkout, and the local path of the file is never written anywhere.

Other `add` behaviour with a GPX:

- A file with waypoints but no track or route creates a metadata-only goal and says why: unordered points are an
  idea, not a route.
- A file whose checksum already belongs to another goal's `track.gpx` is reported as a duplicate and the import
  stops. Reference the existing goal, or pass `--allow-duplicate` if two goals really share one file. A same-named
  route in another region is legitimate; nothing is merged for you. The check runs with `--publish-track` only
  (without it nothing is copied, so there is nothing to duplicate), and it compares the bytes that would be published
  with every goal's published route, including the planned routes saved before the tick list. It does not look at
  report recordings, and the same line exported twice with different bytes is two different files to it.
- `update` has no `--gpx`: a route is attached when the goal is created. If a name-only idea later gets a file,
  move the old folder out of `content/trips/` (to the Desktop, for example), re-create the goal with
  `add --gpx … --publish-track --slug <same-slug>` so the URL stays, and copy your intent fields back into
  `goal.json`. `add` writes a fresh `index.md`: a draft again, holding only what the command was given and the
  distance measured anew. Compare it with the old one and carry over what it lacks, such as `route_shape` and the
  notes. When `rendered/trips/<slug>/` still holds a `meta.json`, the map there was drawn for the folder you moved
  out: `add` then prints no `no map was drawn` line and its `Next:` line names that folder, so run
  `python3 tools/render.py <slug>` yourself once `draft: true` is removed. The same steps give a planned route from
  before the tick list its `route` block (section 9); the file to give `--gpx` is then the `track.gpx` of the folder
  you moved out. A folder that is only renamed inside `content/trips/` is still a goal there, and with that
  `track.gpx` in it the import stops with
  `ERROR this file is already published under content/trips/<folder>/ (same checksum); …`.

The report lists the source checksum, the selection made, the approximate values (marked approximate), what the file
did not have (elevation, times) and the files written. A real run ends with a `Next:` line. With `--publish-track`,
for the goal `your-route-name`, the last two lines are:

```
  no map was drawn (render.py leaves drafts out): once "draft: true" is removed, run python3 tools/render.py your-route-name and add "rendered/trips/your-route-name" as well
Next: review content/trips/your-route-name/ (index.md, goal.json, track.gpx); remove "draft: true" to publish; python3 tools/build.py --check; git add "content/trips/your-route-name"
```

A goal saved without a published track gets only the `Next:` line, with `(index.md, goal.json)` in its brackets. The
first of the two lines is not printed with `--no-render` either, or when `rendered/trips/<slug>/` already holds a
`meta.json` (the last bullet above); in that last case the `git add` of the `Next:` line names
`"rendered/trips/<slug>"` as well. A dry run prints the plan and no `Next:` line.

### 4.3 Update intent

```bash
python3 tools/ticklist.py update your-goal-slug --status shortlisted --priority high
python3 tools/ticklist.py update your-goal-slug --months 6,7 --year 2027 --commitment full-day
python3 tools/ticklist.py update your-goal-slug --tags scramble,ridge-traverse --why "The long ridge."
python3 tools/ticklist.py update your-goal-slug --source-kind planner-export --scope full-intended-route \
  --source-url https://example.com/plan --checked-at 2026-10-09
python3 tools/ticklist.py update your-goal-slug \
  --add-reference "access-page|Official access page|https://example.com/access" --reference-checked-at 2026-10-09
python3 tools/ticklist.py update your-goal-slug --add-check "Does the file include the descent?"
python3 tools/ticklist.py update your-goal-slug --check c1          # id from goal.json's checklist
python3 tools/ticklist.py update your-goal-slug --uncheck c1
python3 tools/ticklist.py update your-goal-slug --archived true
python3 tools/ticklist.py update your-goal-slug --reopen --status shortlisted --reopen-note "Back for the north side."
```

`update` edits `goal.json` (and nothing else: not the notes, not the track, not any report), validates the whole
file with the rules in section 3, and writes only if it passes.

- `--add-reference` takes `ID|LABEL|URL` in one quoted argument and can be given several times in one command, as
  can `--add-check`. A new reference is dated today unless you pass `--reference-checked-at YYYY-MM-DD` (one date
  for every reference added by that command).
- `--checked-at` is the day you last read the route source's page. It only ever sets `route_source.checked_at`; it
  does not date a reference, and adding a reference does not change it.
- `--source-kind author-drawn` needs `--approximation-note "..."` in the same command (or a note already in the
  file): how the line was made and what it is not.
- `--status completed` is refused with a pointer to `log-outing`: a completion is an event you record, not a flag
  you flip.
- A completed goal is opened again with `--reopen --status <the status it goes back to>`. That appends a dated
  "Reopened" entry after its outings and keeps every earlier attempt and completion; the goal page lists it with
  them. `--reopen-note` is optional. A plain `--status researching` on a completed goal is still refused (the
  message names `--reopen`), so a goal never leaves Completed by accident. Logging a new completion later closes it
  again, and the whole history stays.

### 4.4 Log an attempt or a completion

```bash
# Turned around; no report written. The date is optional.
python3 tools/ticklist.py log-outing your-goal-slug --outcome attempted --date 2026-06-14 \
  --note "Turned around below the notch."

# Done, with the report you added with add_trip.py.
python3 tools/ticklist.py log-outing your-goal-slug --outcome completed --report-slug your-report-slug

# Done, no write-up and no exact date. Both are allowed to stay unknown.
python3 tools/ticklist.py log-outing your-goal-slug --outcome completed
```

`log-outing` appends one event and sets the status: `completed` makes the goal `completed`; `attempted` makes it
`attempted` unless it is already completed. The report slug must be a published, non-planned trip that already exists
in `content/trips/`; the planned track and the report are left exactly as they were. A goal can have several
attempts, and one report can complete several goals, each confirmed by you. Never log a completion because a
recording looks like the planned line.

A completed goal keeps its page and its planned GPX, shows "Completed" in its chips, lists its outings first, and the
linked report shows "On the tick list: <goal title>" under its title. It leaves the active list and the active
counts and sits under the list's Completed scope; archive it as well when you want it out of the way.

### 4.5 Review packet

```bash
python3 tools/ticklist.py review-packet your-goal-slug --out ~/Desktop/tick-list-review/your-goal-slug.md
```

Writes a Markdown packet with the goal's public fields, a summary of the source and its limits, the fields still
empty, the references, the enrichment prompt from section 8 and the patch shape a researcher should return. `--out`
must be outside the repository; a path inside it is refused, because the packet and anything written against it are
not for the public checkout.

### 4.6 Export

```bash
python3 tools/ticklist.py export --out ~/Desktop/tick-list.json
python3 tools/ticklist.py export                     # prints the JSON
```

A JSON array of the public fields of every non-draft goal: `slug`, `url`, `title`, `activity`, `subtype`, `place`,
`region`, `draft` (always `false`: drafts are left out), `status`, `priority`, `archived`, `tags`, `why`, `added_at`,
`target_months`, `target_year`, `time_commitment`, `route_scope`, `route_source` (kind, label, url, checked date),
`references` (id, label, url, checked date), `approx_stats`, `route` (segments, points, elevation; `null` without a
published route), `has_gpx`, `outings` (outcome, date, report URL, note) and `legacy` (`true` for a planned route
that has no `goal.json` yet). Not exported: `difficulty`, `season_notes`, `field_evidence`, `checklist`, reference
notes. Never a local path, never `proposed` evidence.

When some planned routes still have no `goal.json`, `export` also prints one line naming them (to the error stream,
so `export > file.json` stays clean JSON): that is the list to review and `update`.

## 5. Review and publish

1. **Read what was written.** Open `content/trips/<slug>/index.md` and `goal.json`. Check the title, the activity,
   the region spelling, and that the notes say only what you want in public.
2. **Remove `draft: true`** from `index.md` when the goal is ready to show. A draft is validated like everything
   else but left out of the built site, so you cannot see its page until the line goes.
3. **Preview and check:**

   ```bash
   python3 tools/validate.py             # every content problem, one line each; nothing is built
   python3 tools/build.py --serve        # http://localhost:8000/tick-list/ and http://localhost:8000/trips/<slug>/
   python3 tools/build.py --check        # full build, then the checks of the built site
   python3 -m unittest discover -s tests
   ```

   `validate.py` and every build check each goal, drafts included. What they say about a goal is in section 9; the
   flags, the other messages and the lines `--check` prints are in CONTENT_GUIDE.md, section 5. Look at the card on
   the list, the goal page's stats strip (every value marked approximate, no gain unless the file had full
   elevation), the "Route source" section and the map. A goal with a track shows "Map not rendered yet" until its map
   is drawn, and none was drawn while it was a draft: run `python3 tools/render.py <slug>` (needs internet) and stage
   what it drew with the goal (step 4).
4. **Stage by explicit path, and read `git status --short` before committing. Never `git add -A` or `git add .`.**
   It is the rule of step 5 in ADDING-TRIPS.md, which gives the reasons. For a goal:

   ```bash
   git add "content/trips/<slug>" "rendered/trips/<slug>" rendered/site
   git status --short
   git commit -m "Add goal: YOUR ROUTE NAME"
   git push
   ```

   - Every line of `git status --short` with a letter in its first column is in the commit. A name that ends in a
     space and a number, such as `goal 2.json`, is an iCloud conflict copy: `git restore --staged "<path>"`, then
     delete the file. `.gitignore` hides those copies under `rendered/` and `assets/`, not under `content/`, where
     the content validator prints a warning that names the copy (section 9).
   - `rendered/site` holds the region maps, which `render.py <slug>` refreshes too (its usage text says so). Naming
     it when nothing changed there does no harm.
   - A goal without a rendered map has no `rendered/trips/<slug>/` folder. `git add` then stops with
     `fatal: pathspec 'rendered/trips/<slug>' did not match any files` and stages nothing: give
     `content/trips/<slug>` alone.
   - For an intent change or an outing, the only file is `content/trips/<slug>/goal.json`.

5. GitHub runs the tests and the same check on every push to the `main` branch, and publishes a few minutes later.
   A push to any other branch runs nothing. A bad field fails the deploy instead of publishing a broken list; the
   site just does not update until it is fixed. A warning does not hold a deploy back.

To take a goal off the site again, put `draft: true` back: a build then leaves out the page and its GPX. A region
map that was drawn with the goal (on the home page, the Map page and the Ski page) keeps its dashed line and its
title until `python3 tools/render.py` has been run again (needs internet). Where the goal has a pin of its own on
such a map, the pin links to the page that is gone, and `build.py --check` fails on it with lines such as
`BROKEN map/index.html -> ../trips/<slug>/`. So run the render before the checks of step 3, and stage `rendered`
with the goal's folder. Until the maps are drawn again the content validator prints the `site maps` warning of
section 9. The build also stops while another trip's write-up links to the goal's page. All of this is a publication
choice, not a privacy measure; the files are still in the repository's history (section 7).

## 6. What the importer does with a GPX

- **Routes and tracks both work.** `<rte>` routes (one segment each) and `<trk>` tracks (one or more `<trkseg>`)
  are read; tracks are listed first, then routes, in file order. Waypoints are counted (and stay in the file when it
  is copied whole) but never turned into a route.
- **Segments stay separate.** Distance is the sum of each segment's own polyline; the gap between two segments is
  never bridged, on the map or in the number. Two unrelated tracks in one file are two candidates, not one traverse.
- **Several candidates need a choice.** With more than one track or route you pass `--select trk:N` or
  `--select rte:N`; nothing is concatenated silently. With exactly one candidate, no choice is needed.
- **No elevation means no gain.** `gain_m` and `loss_m` are written only when every point has an `<ele>`;
  `elevation: "partial"` or `"none"` in the `route` block says why not, and the stats strip says "No elevation in the
  file" or "Partial elevation". High and low points appear when any point has one. No elevation service is queried
  and no points are made up.
- **Times are not a date.** A recorder's timestamps are kept in the file if they were there, and ignored
  otherwise: the goal gets no `date` and no moving time, and the recording's day is nobody's trip date. The report
  says whether the file has them, whatever time zone they are written in.
- **Sparse geometry is flagged.** Under ten points in all is reported as sparse: a straight-line length between a
  few points is not a trail distance.
- **Source bytes are kept.** With one candidate, `track.gpx` is the original file byte for byte; with several, it
  is a new GPX holding only the chosen track or route, its points, elevations and times unchanged and its segments
  kept. Either way `route.source_sha256` is the checksum of the published file, and a later change to the file fails
  the build. `build.py --check` also compares the copy on the built site with `track.gpx`, byte for byte, and prints
  a `GPX …` line when they differ.
- **Limits and rejections.** Files over 30 MB or 500,000 points, a file that is not UTF-8, a `<!DOCTYPE`, `<!ENTITY`
  or any other `<!` declaration (comments and CDATA are fine), a processing instruction such as `<?xml-stylesheet`,
  XHTML / SVG / MathML content, a `<script>` or a `javascript:` URL anywhere in the bytes (a published GPX is served
  from the site's own address, so a browser could run such content), XML that is not well formed, a root element
  other than `gpx`, a latitude outside -90 to 90, a longitude outside -180 to 180, a non-numeric coordinate or `<ele>`,
  a `--slug` that is not a plain slug: each stops the import with a message, before anything is written. The same
  checks run again on the parsed document, so spelling a marker with character references, a namespace prefix or an
  encoding declaration does not get past them (the declaration must say UTF-8 or nothing). When one element of a
  multi-route file is published, the new document is checked again as a whole and must hold exactly the chosen
  route. No URL inside a file is ever fetched.
- **The report says what the public copy carries.** Before anything is chosen it lists what the file holds besides
  the line: the `creator` text, track and route names, descriptions and comments, file information (an author name,
  say), waypoints (places that are not on the line, named or not), device extensions, links, timestamps, named points,
  GPS fields, XML comments. With `--publish-track` it lists the same for the bytes about to be published, which is
  the list that matters: everything on it becomes public. If any of it is private, export the route again without it
  and import that file; nothing is stripped for you, because the published file is kept byte for byte.
  - The list is complete by construction: every element and attribute in the file is either the line itself
    (GPX points with latitude, longitude and elevation, in their proper place) or an item on the list. Something no
    GPX schema knows shows up under "other elements" or "attributes"; it is never skipped. So do the places a field
    list would miss: namespace declarations (a prefix and a URI are free text), a `version` that is not plainly 1.0
    or 1.1, loose text between elements, and anything in another namespace that merely looks like a track (it is
    never read as one). The report says "the scan found nothing besides the line" only when all of that is empty.
  - Two things no scan can tell you. The coordinates are the point of publishing and are public: a line that starts
    at a front door says where the door is. And a file could carry information in its spacing or in how its numbers
    are written; if a file comes from someone you do not trust, export the line again from your own planner.
  - Text taken from the file (a track name, the creator, a waypoint name, a namespace) is printed in quotes, on one
    line, cut at 60 to 100 characters. Control and invisible characters, stacked accents and right-to-left letters
    are written as `\uXXXX`, because they can forge, hide or reorder what the report shows. If you see `\u…` in a
    name, the file contains characters you would not otherwise notice.
- **Rendering is local.** Maps, tiles and glyphs come from `tools/render.py` on your Mac, which downloads terrain
  and OpenStreetMap data; GitHub never renders. Planned routes are drawn segment by segment in the planned style, with
  no elevation profile. Until a render exists (or if it fails), the goal is still valid and its card and page show
  "Map not rendered yet"; with no track at all they show "Route not added yet" / "No route added yet".

## 7. Privacy

- **Everything committed is public:** `index.md`, `goal.json`, `track.gpx`, drafts, and every past version in git
  history. `draft: true` hides a page; it does not hide a file. There is no `private: true`, on purpose, because it
  would be a lie; `robots.txt`, `noindex` and unlinked pages are not access controls.
- **Keep these outside the checkout:** private dates and plans, contact details, reservations and permit numbers,
  home or car coordinates, anybody else's unlicensed GPX, photographs or trip-report text, and research you have not
  reviewed. Review packets go to a folder outside the repo (`review-packet` insists), and so do the notes you make
  against them.
- **Approve before copying.** `--publish-track` is the one place a new file enters the repository, and it is your
  decision each time. A GPX recorded by someone else is published only when you are allowed to publish it; say so
  in `route_source` (`third-party-recording`, with the source's label and URL).
- **The importer writes no local paths**, and `export` and the search data carry only the public fields. Nothing
  `proposed` leaves `goal.json` until you approve it, and then it is public too.
- A goal's `why` is yours. A short factual description can be drafted for you; a motivation cannot.

## 8. AI enrichment

Research is welcome; publishing it is your decision, field by field. The workflow is:

1. `review-packet` for the goal (section 4.5), written outside the checkout.
2. Research with the prompt below, in Claude Code or any chat. The session reads the packet, derives nothing from
   the GPX that the importer has not already computed, and consults only sources it can actually open.
3. The session returns three groups: facts you supplied or the importer computed; sourced suggestions; unresolved
   questions. Each factual suggestion is a patch entry:

   ```json
   {"field": "season_notes",
    "proposed_value": "Usually travelled from early summer once the access road opens.",
    "source_ids": ["agency-page"],
    "checked_at": "2026-10-09",
    "qualification": "Agency page describes a typical season, not this year's conditions."}
   ```

   with the matching `references` entries (`id`, `label`, `url`, `checked_at`). A tag or a region is a suggestion,
   labelled as one, with no source required. Conflicting or missing evidence stays an unresolved question; a blank
   is better than a confident guess.
4. You read each proposal against its source and decide. Nothing is applied until you say so, and an approved value
   already in the file is never replaced unless you accept the replacement.
5. Apply what you approved: `update` for the fields it has flags for (`--tags`, `--scope`, `--source-*`,
   `--add-reference`, `--add-check`); a region or place goes into `index.md` by hand; for `season_notes` and
   `difficulty`, edit `goal.json`, add the references, and write the `field_evidence` entry yourself with
   `"status": "approved"`. Run the checks (section 5) and commit by
   path. A `proposed` entry can stay in the file as a reminder; the field it backs stays off the site.

**Never auto-filled**, whatever a session is sure of: `status`, `priority`, `archived`, `why`, `target_months`,
`target_year`, any outing or completion, feasibility, a safety or avalanche verdict, legal access or a road's
status, water, an expected duration, a grade without a cited system and source, turn-by-turn directions from the line,
or a place name from coordinates alone. "Typical season" is never a current-conditions report, and a `checked_at`
says when a page was read, not that it is still true.

The prompt that `review-packet` includes. Replace the bracketed fields. The packet copies the `text` block below whose
first line is "Add or enrich this future goal": keep that first line and keep the block fenced, or the packet says
the prompt is missing.

<!-- enrichment-prompt:start -->
```text
Add or enrich this future goal using the existing Tick list workflow:

Route name: [name]
Primary activity: [ski / climb / hike / mtb / other]
Region/place: [known location, or unknown]
GPX: [attached file or local path, or none yet]
Route source/reference links: [links or unknown]
Priority: [high / normal / someday; default normal]
Why I want to do it: [my own note, or leave blank]
GPX approved for public copying: [yes / no; default no]

Inspect the supplied material first. In Claude Code, read docs/TICK_LIST_GUIDE.md and use the importer dry-run before creating/updating files. In a chat without write access, return the proposed entry and exact unresolved fields without claiming to have imported anything.

Use deterministic code for approximate distance/elevation and preserve route/track segment boundaries. Identify whether the source appears incomplete or approximate; do not infer technical difficulty, successful summits, total route completeness, or expected duration from the line alone. No GPX is acceptable. Never use the source recording's date as my completion or future-trip date.

Research missing context only from sources you can actually access. Propose region/tags, a short factual third-person description, published difficulty with its grading system, typical-season notes, relevant official access/permit links, and questions I should resolve. Keep my preferred months separate from published seasonal guidance. Each factual proposal needs the supporting URL, checked date, and qualification; conflicting or missing evidence stays unresolved. Do not invent personal motivation, route conditions, a safety verdict, or a completion claim.

Return three clearly separated groups: facts supplied by me or computed from the GPX; sourced suggestions for review; unresolved questions. Keep unreviewed research/private details outside the public checkout. Preserve approved existing fields. Create only the draft fields I explicitly supplied and approved derived public data; do not apply researched changes until I approve them. Do not tick the goal, overwrite an existing source/report, push, or deploy.
```
<!-- enrichment-prompt:end -->

## 9. Troubleshooting

A bad `goal.json` stops the build, and `update`, which validates before writing. Each line reads
`ERROR content/trips/<slug>/goal.json: …` and names the field. `python3 tools/validate.py` prints the same lines
without building; it and the build report every broken goal in one run.

| Message says | What it means | Fix |
| --- | --- | --- |
| malformed JSON, or not an object | A comma, quote or bracket is wrong, or the file is a list or a string | Compare with the example in section 2: double quotes, commas between entries, no trailing comma, one `{ … }` object. |
| `only a kind: planned trip can carry a goal sidecar` | A `goal.json` sits beside a report | Delete the sidecar. A finished trip is a report; the goal keeps its own folder. |
| `status` / `priority` / `time_commitment` / `route_scope` / `route_source.kind` not one of the allowed values | A typo, or a value from a different field | Use the exact lowercase values in section 3 (`full-day`, not `Full day`). |
| `target_months` not unique or outside 1-12; `target_year` outside 2000-2100 | | Integers only: `[6, 7]`, `2027`. |
| `archived` not a boolean, `tags` not a list of text, `why` / `season_notes` not text | A wrong type | `true`/`false` without quotes; `["a", "b"]`; `"…"`. |
| `references`: duplicate `id`, `id` not `a-z0-9-`, `url` not http/https | | Rename the id (lowercase, digits, hyphens); give every reference an `https://` or `http://` URL. |
| `field_evidence`: unknown source id, empty `source_ids`, or `status` not `proposed`/`approved` | The evidence names a reference that is not in `references` | Add the reference first, or fix the id. |
| `difficulty` or a non-empty `season_notes` without approved evidence | Research not yet reviewed | Add `field_evidence` for that field with `"status": "approved"` once you have checked the source, or empty the field. |
| `route_source.kind` is `author-drawn` with no `approximation_note` | A drawn line needs its caveat | Pass `--approximation-note "..."` together with `--source-kind author-drawn` (on `add` or `update`), or write `approximation_note` in `goal.json`: how the line was made and what it is not. A refused `add` has written nothing, even though the message names the `goal.json` it would have created. |
| `status: completed` without a completed outing, a completed outing without `status: completed`, or `status: attempted` without an attempted outing | Status and events disagree | Use `log-outing`, which keeps them together; do not edit `status` by hand around an outing. To open a completed goal again, `update <slug> --reopen --status <status>`. |
| `status is 'completed' but the goal was reopened after its last completed outing` | A "reopened" entry follows the last completion | Log the new completion with `log-outing --outcome completed`, or set the status the goal is really in. |
| `outings[n] reopens the goal, but no completed outing comes before it` | A hand-written "reopened" entry in the wrong place | Remove it, or put it after the completed outing it follows. |
| `checklist[n].text must not be empty`, `schema_version must be 1`, `unknown field …` | A hand edit left an empty question, a wrong version or a misspelled key | Fix the key or the value; nothing is published from a file that does not validate. |
| `route.source_sha256` does not match `track.gpx` | The published file changed after import | Restore the original file, or re-import on purpose. The build never re-measures silently. |
| the outing's `report_slug` is unknown or names a planned route (message names the goal and the slug) | The report does not exist, is a draft, or is itself a goal | Add the report first, publish it, and use its folder name. |

From the content validator (`python3 tools/validate.py`, and the start of every build). These concern the goal's
folder as a whole, which `goal.json`'s own rules do not look at. A line is `ERROR` or `WARNING`, the file, then the
message; an error stops the build and a warning does not. The messages are quoted exactly, with `<slug>` standing for
the goal's folder name; the dates and `your-report-slug` are examples.

| Level, file | Message | What it means | Fix |
| --- | --- | --- | --- |
| `WARNING`, `index.md` | `planned route without goal.json: it is listed with the default status and priority; review it and run python3 tools/ticklist.py update <slug> to give it one` | A planned route saved before the tick list (section 1). One route has it today | Nothing has to be done: the route works with the defaults. Any `update` writes a `goal.json` and ends this warning. When the folder holds a `track.gpx`, the next two warnings then take its place, because that file was never imported. To end all three, re-create the goal from the file (section 4.2, last bullet). |
| `WARNING`, `goal.json` | `track.gpx is published but there is no route block, so nothing records where the file came from or how it was measured` | A `track.gpx` beside a `goal.json` whose `route` is `null`: the file was copied in by hand, or a route from before the tick list got its `goal.json` from `update` | Re-create the goal with `add --gpx … --publish-track --slug <slug>` (section 4.2, last bullet); the importer writes the block. |
| `WARNING`, `goal.json` | `track.gpx is published but route_source.public_copy_approved is false; set it to true once you approve publishing the file, or remove track.gpx` | The same two cases: nothing records that you approved publishing the file | The re-import sets it. Or set `"public_copy_approved": true` in `goal.json` by hand, once you do approve. |
| `ERROR`, `goal.json` | `the route block is there but track.gpx is missing from the folder: the page would describe a route it can neither draw nor offer; put the file back` | `track.gpx` was deleted or moved after the import | Put the same file back. |
| `WARNING`, `index.md` | `a planned route has a date: line (2026-09-01); a goal has no date, and an outing's date goes in goal.json` | A `date:` line in a goal's `index.md` | Delete the line. The day you went is `log-outing --date`. |
| `ERROR`, `index.md` | `published_at is for a report; this is a planned route (kind: planned)` | `published_at:` in a goal's `index.md` (`updated_at:` is refused the same way) | Delete the line; it belongs to reports (CONTENT_GUIDE.md, section 8). |
| `WARNING`, `goal.json` | `outings[0].date 2027-06-14 is in the future (today is 2026-10-10); an outing is something that happened` | An outing dated after today; `log-outing --date` does not refuse one. `outings[0]` is the first entry | Correct the date in `goal.json`. |
| `WARNING`, `goal.json` | `outings[1].report_slug 'your-report-slug' is already named by outings[0]` | Two outings of one goal name the same report, for example an attempt and a completion logged with one `--report-slug` | If that is not what happened, set `report_slug` to `null` on one of them. |
| `WARNING`, `index.md` | `no rendered map (rendered/trips/<slug>/meta.json is missing); run python3 tools/render.py <slug> (until then the page shows "Map not rendered yet")` | A published goal has a `track.gpx` whose map has not been drawn; its page shows "Map not rendered yet". A new goal with a track is in this state once `draft: true` is removed, because no map is drawn for a draft | Run the command it gives (needs internet), then stage `rendered/trips/<slug>` and `rendered/site` with the goal (section 5, step 4). |
| `WARNING`, the copy itself | `looks like an iCloud conflict copy (the name ends in a space and a number): nothing reads it, but git add of the folder would stage it; delete it` | The file named, such as `content/trips/<slug>/goal 2.json`, is an iCloud conflict copy of a file in the goal's folder | Delete it (section 5, step 4). For a copy of `index.md` or `goal.json`, compare it with the original first: the copy may hold your newer text. |
| `WARNING`, `index.md` | `the site maps under rendered/site/ still draw this trip, which is a draft: its line and title stay on the pages that show those maps (the home page, the Map page, an activity page) until python3 tools/render.py has been run and rendered/site/ committed` | A goal that a region map was drawn with is a draft again (section 5). After the goal's folder was removed the line reads `which has no folder under content/trips any more` and still names its `index.md`; after its `track.gpx` was removed, `which has no track any more`. While the goal has no page, `build.py --check` can fail as well (section 5, last paragraph) | Run `python3 tools/render.py` (needs internet), then stage `rendered` with the goal's folder, as step 5 of ADDING-TRIPS.md gives for a run with no trip name. |

From `tools/ticklist.py`:

| Message | Fix |
| --- | --- |
| the folder already exists (suggests `--slug`) | Another goal or trip has that slug. Pass `--slug something-else`, or `update` the existing goal. |
| several candidates: `trk:0 … trk:1 … rte:0 …` | Pass `--select` with one of the listed ids. |
| no track or route in the file (waypoint-only) | The goal is created without a route. Find a file with a track or route, or draw one and mark it `--source-kind author-drawn --approximation-note "how the line was made"`. |
| the title gives no usable folder name | The title has no letters or digits the slug can keep. Pass `--slug a-name-you-choose`. |
| `--reopen` refused | The goal is not completed, or no `--status` (other than `completed`) says what it goes back to. |
| `--reference-checked-at goes with --add-reference` | That date belongs to a reference being added; the route source's date is `--checked-at`. |
| `route_source must be an object` | A hand edit set `route_source` to something else. Restore the object (section 2) and run the command again. |
| duplicate checksum: already published under `<slug>` | Reference that goal instead, or pass `--allow-duplicate` knowingly. |
| file too large, too many points, `DOCTYPE`/`ENTITY`, not well-formed, root is not `gpx`, bad coordinate or elevation | Export the file again from its source as plain GPX; do not hand-edit XML into it. |
| `--status completed` refused, pointing at `log-outing` | Record the completion with `log-outing --outcome completed`. |
| `--report-slug` is not a published, non-planned trip | Add and publish the report (ADDING-TRIPS.md) first. |
| `review-packet --out` inside the repository (directly, or through a symbolic link that leads into it) | Choose a path outside the checkout, for example under `~/Desktop/`. |
| render failed (warning) | The goal is valid. Run `python3 tools/render.py <slug>` later with internet; until then the page shows "Map not rendered yet". |

A `content/trips/<slug>/index.md: front matter: …` message is a syntax problem in that file's front matter, and an
`unknown key …` warning is a misspelt field name in `index.md`; both are in CONTENT_GUIDE.md, section 5.

## 10. What not to do

- Do not change a goal's `kind`, replace its `track.gpx` with your recording, or log a completion because a
  recording resembles the plan. The recording becomes a report; the goal stays a goal with an outing.
- Do not put a `date` on a goal, or a recorder's moving time in `time_commitment`.
- Do not publish a grade, a season or a route description that has no approved source. Leave it blank.
- Do not call `add_trip.py` for a goal; it assumes a recording (date, times, a rewritten track).
- Do not `git add -A` or `git add .`. Stage `content/trips/<slug>`, `rendered/trips/<slug>` and `rendered/site` by
  path, and read `git status --short` before committing (section 5).
- Do not keep review packets, research notes or anyone else's files inside the checkout, even uncommitted.
