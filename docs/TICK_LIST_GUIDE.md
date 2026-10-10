# Tick list guide: goals, GPX imports, review, completion

How to save a route you want to do, attach a GPX, keep the research honest, publish the goal, and later record what
happened. Everything runs in this folder on your Mac with one local tool, `tools/ticklist.py`; the public site only
shows what you commit and push. The list lives at `tick-list/`, each goal at `trips/<slug>/`.

Adding a finished trip is in [ADDING-TRIPS.md](../ADDING-TRIPS.md); homepage features, covers and search are in
[CONTENT_GUIDE.md](CONTENT_GUIDE.md); how the generator works is in [DEVELOPING.md](DEVELOPING.md).

## 1. What the tick list is, and is not

- **A goal is a planned route, and it stays one.** It is a `kind: planned` folder under `content/trips/`, the same
  model the map's Planned group already uses. Its title, URL and planned GPX never change because you did it. When
  you do go, the outing is a separate report, added with `add_trip.py` from your own recording; the goal gets an
  `outings` entry pointing at that report, and the report gets an automatic "On the tick list" line pointing back.
  Nothing is counted twice: goals never enter report counts, completed mileage, the Trips page, search, the home
  page or the RSS feed.
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
  `goal.json`.

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
double quotes, no trailing commas); the next build validates it and stops with a message naming the field if a
value is wrong (section 9). A `goal.json` beside a report (anything that is not `kind: planned`) is an error, so a
finished trip can never be slipped into the future list.

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
| `stats` | importer only | `distance_km` always; `gain_m` / `loss_m` only when every point in the file has an elevation; `high_m` / `low_m` when any does. Written by `--publish-track`; shown everywhere as approximate ("≈ 12.3 MI · ≈ 2,100 FT GAIN", in MI or KM). "Highest point in the file" is not "summit elevation". |
| body | no | Planning notes, shown under the heading "Planning notes" (never "Trip report"). `add --notes` writes the first version. |

**In `goal.json`:**

| Field | Values | Meaning and rule |
| --- | --- | --- |
| `status` | `idea` (default), `researching`, `shortlisted`, `attempted`, `completed` | Where the goal is in your head. Any direct change is allowed. `completed` needs an outing with outcome `completed` (and vice versa); `attempted` needs an outing with outcome `attempted`. Set these with `log-outing`, not by hand. |
| `priority` | `high`, `normal` (default), `someday` | Your ordering; the default sort on the list. Shown as "High priority" or "Someday"; normal shows nothing. |
| `archived` | `true` / `false` (default) | Takes the goal out of the active list and the "+ N planned route" counts, keeps its page, GPX and outcome. Separate from status, so an attempted or completed goal can be archived without losing its history. |
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
| `outings` | list of `{"outcome", "date", "report_slug", "note"}` | What actually happened. `outcome` is `attempted` or `completed`; `date` and `report_slug` may be `null` when unknown or when there is no write-up; `report_slug` must name a published report, never a planned route. Written by `log-outing`. Earlier attempts are kept when you finally complete. |
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

### 4.2 Add a goal with a GPX

```bash
# Inspect only: the plan, the measurements and any problems. Nothing is written.
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity ski --gpx /absolute/path/route.gpx --dry-run
```

If the file holds more than one track or route, the report lists them (`trk:0`, `trk:1`, `rte:0`, each with its
name and point count) and stops the geometry step until you choose. Pick one and run again:

```bash
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity ski --gpx /absolute/path/route.gpx \
  --select trk:1 --dry-run
```

Alternatives are never joined into one line. To publish the chosen geometry as the goal's public route:

```bash
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity ski --gpx /absolute/path/route.gpx \
  --select trk:1 --publish-track --source-kind third-party-recording \
  --source-url https://example.com/route --source-label "Example source" --scope approach-only
```

**`--publish-track` means one thing:** you have looked at this file and approve copying it into the public
repository. It copies the selected geometry to `content/trips/<slug>/track.gpx`, writes the approximate `stats` into
`index.md` and the `route` block into `goal.json`, sets `route_source.public_copy_approved` to `true`, and then runs
`python3 tools/render.py <slug>` to draw the map (skip that with `--no-render`; a failed render is a warning and the
goal is still valid, section 6). It does **not** commit, push or deploy anything, does not approve any other field,
and says nothing about whether the route is safe, complete or feasible.

Without `--publish-track` the file is only read: the report prints its measurements for you, and the goal is created
metadata-only, with no `stats`, no `route` block and no copy of the file. Nothing from an unapproved file reaches the
checkout, and the local path of the file is never written anywhere.

Other `add` behaviour with a GPX:

- A file with waypoints but no track or route creates a metadata-only goal and says why: unordered points are an
  idea, not a route.
- A file whose checksum already belongs to another goal's `track.gpx` is reported as a duplicate and the import
  stops. Reference the existing goal, or pass `--allow-duplicate` if two goals really share one file. A same-named
  route in another region is legitimate; nothing is merged for you.
- `update` has no `--gpx`: a route is attached when the goal is created. If a name-only idea later gets a file,
  move the old folder aside, re-create the goal with `add --gpx … --publish-track --slug <same-slug>` so the URL
  stays, and copy your intent fields back into `goal.json`.

The report at the end lists the files created, the source checksum, the approximate values (marked approximate),
what the file did not have (elevation, times), the selection made, and the next steps: review, remove `draft: true`,
`git add` by path.

### 4.3 Update intent

```bash
python3 tools/ticklist.py update your-goal-slug --status shortlisted --priority high
python3 tools/ticklist.py update your-goal-slug --months 6,7 --year 2027 --commitment full-day
python3 tools/ticklist.py update your-goal-slug --tags scramble,ridge-traverse --why "The long ridge."
python3 tools/ticklist.py update your-goal-slug --source-kind planner-export --scope full-intended-route \
  --source-url https://example.com/plan --checked-at 2026-10-09
python3 tools/ticklist.py update your-goal-slug \
  --add-reference "access-page|Official access page|https://example.com/access"
python3 tools/ticklist.py update your-goal-slug --add-check "Does the file include the descent?"
python3 tools/ticklist.py update your-goal-slug --check c1          # id from goal.json's checklist
python3 tools/ticklist.py update your-goal-slug --uncheck c1
python3 tools/ticklist.py update your-goal-slug --archived true
```

`update` edits `goal.json` (and nothing else: not the notes, not the track, not any report), validates the whole
file with the rules in section 3, and writes only if it passes. `--add-reference` takes `ID|LABEL|URL` in one quoted
argument. `--checked-at` is the day you last read the route source's page. `--status completed` is refused with a
pointer to `log-outing`: a completion is an event you record, not a flag you flip. Reopening a goal
(`--status researching` on a completed one, say) is refused too while a completed outing exists; archive it instead,
or remove the outing by hand and accept that the history goes with it.

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

A JSON array of the public fields of every non-draft goal: slug, url, title, activity, place, region, status,
priority, archived, tags, why, target months and year, time commitment, route scope, route source (kind, label, url,
checked date), references, the approximate stats, and the outings with their report URLs. Never a local path, never
`proposed` evidence.

## 5. Review and publish

1. **Read what was written.** Open `content/trips/<slug>/index.md` and `goal.json`. Check the title, the activity,
   the region spelling, and that the notes say only what you want in public.
2. **Remove `draft: true`** from `index.md` when the goal is ready to show. A draft is validated like everything
   else but left out of the built site, so you cannot see its page until the line goes.
3. **Preview and check:**

   ```bash
   python3 tools/build.py --serve        # http://localhost:8000/tick-list/ and http://localhost:8000/trips/<slug>/
   python3 tools/build.py --check        # full build plus every link, image and anchor
   python3 -m unittest discover -s tests
   ```

   Look at the card on the list, the goal page's stats strip (every value marked approximate, no gain unless the
   file had full elevation), the "Route source" section and the map. A goal whose track has not been rendered shows
   "Map not rendered yet"; run `python3 tools/render.py <slug>` (needs internet) and commit `rendered/trips/<slug>/`
   with it.
4. **Stage by explicit path, never `git add -A`.** `rendered/` holds thousands of untracked iCloud conflict copies
   (`meta 3.json`, `map-wide 4.webp`), and `-A` would commit them all. Check `git status` for ` 2`/` 3`/` 4` names.

   ```bash
   git add "content/trips/<slug>" "rendered/trips/<slug>"
   git commit -m "Add goal: YOUR ROUTE NAME" && git push
   ```

   For an intent change or an outing, the only file is `content/trips/<slug>/goal.json`.

5. GitHub runs the same check and publishes within about a minute. A bad field fails the deploy instead of
   publishing a broken list; the site just does not update until it is fixed.

To take a goal off the site again, put `draft: true` back and push: the page and its GPX go away. That is a
publication choice, not a privacy measure; the files are still in the repository's history (section 7).

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
  otherwise: the goal gets no `date` and no moving time, and the recording's day is nobody's trip date.
- **Sparse geometry is flagged.** Under ten points in all is reported as sparse: a straight-line length between a
  few points is not a trail distance.
- **Source bytes are kept.** With one candidate, `track.gpx` is the original file byte for byte; with several, it
  is a new GPX holding only the chosen track or route, its points, elevations and times unchanged and its segments
  kept. Either way `route.source_sha256` is the checksum of the published file, and a later change to the file fails
  the build.
- **Limits and rejections.** Files over 30 MB or 500,000 points, a file that is not UTF-8, a `<!DOCTYPE`, `<!ENTITY`
  or any other `<!` declaration (comments and CDATA are fine), a processing instruction such as `<?xml-stylesheet`,
  XHTML / SVG / MathML content, a `<script>` or a `javascript:` URL anywhere in the bytes (a published GPX is served
  from the site's own address, so a browser could run such content), XML that is not well formed, a root element
  other than `gpx`, a latitude outside -90 to 90, a longitude outside -180 to 180, a non-numeric coordinate or `<ele>`,
  a `--slug` that is not a plain slug: each stops the import with a message, before anything is written. No URL inside
  a file is ever fetched.
- **The report says what else the file carries** (metadata such as an author name, device extensions, links, named
  waypoints, timestamps, comments) before you approve a copy, because `--publish-track` keeps all of it: export the
  file again without those parts if any of it is private.
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

The prompt that `review-packet` includes. Replace the bracketed fields; the text between the markers is what the
packet copies.

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

A bad `goal.json` stops the build (and `update`, which validates before writing) with one line on stderr. Every
message starts with `content/trips/<slug>/goal.json: ` and names the field.

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
| `route_source.kind` is `author-drawn` with no `approximation_note` | A drawn line needs its caveat | Write the note: how the line was made and what it is not. |
| `status: completed` without a completed outing, a completed outing without `status: completed`, or `status: attempted` without an attempted outing | Status and events disagree | Use `log-outing`, which keeps them together; do not edit `status` by hand around an outing. |
| `route.source_sha256` does not match `track.gpx` | The published file changed after import | Restore the original file, or re-import on purpose. The build never re-measures silently. |
| the outing's `report_slug` is unknown or names a planned route (message names the goal and the slug) | The report does not exist, is a draft, or is itself a goal | Add the report first, publish it, and use its folder name. |

From `tools/ticklist.py`:

| Message | Fix |
| --- | --- |
| the folder already exists (suggests `--slug`) | Another goal or trip has that slug. Pass `--slug something-else`, or `update` the existing goal. |
| several candidates: `trk:0 … trk:1 … rte:0 …` | Pass `--select` with one of the listed ids. |
| no track or route in the file (waypoint-only) | The goal is created without a route. Find a file with a track or route, or draw one and mark it `--source-kind author-drawn`. |
| duplicate checksum: already published under `<slug>` | Reference that goal instead, or pass `--allow-duplicate` knowingly. |
| file too large, too many points, `DOCTYPE`/`ENTITY`, not well-formed, root is not `gpx`, bad coordinate or elevation | Export the file again from its source as plain GPX; do not hand-edit XML into it. |
| `--status completed` refused, pointing at `log-outing` | Record the completion with `log-outing --outcome completed`. |
| `--report-slug` is not a published, non-planned trip | Add and publish the report (ADDING-TRIPS.md) first. |
| `review-packet --out` inside the repository | Choose a path outside the checkout, for example under `~/Desktop/`. |
| render failed (warning) | The goal is valid. Run `python3 tools/render.py <slug>` later with internet; until then the page shows "Map not rendered yet". |

A `content/trips/<slug>/index.md: front matter: …` message is a syntax problem in that file's front matter, as in
CONTENT_GUIDE.md section 5.

## 10. What not to do

- Do not change a goal's `kind`, replace its `track.gpx` with your recording, or log a completion because a
  recording resembles the plan. The recording becomes a report; the goal stays a goal with an outing.
- Do not put a `date` on a goal, or a recorder's moving time in `time_commitment`.
- Do not publish a grade, a season or a route description that has no approved source. Leave it blank.
- Do not call `add_trip.py` for a goal; it assumes a recording (date, times, a rewritten track).
- Do not `git add -A`. Stage `content/trips/<slug>` and `rendered/trips/<slug>` by path.
- Do not keep review packets, research notes or anyone else's files inside the checkout, even uncommitted.
