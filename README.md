# Eric Sichak — Trip Reports

Trip reports with GPX maps: backcountry skiing, climbing, hiking, mountain biking and other trips (paddleboarding,
rafting, kayaking, mountaineering). Live at **https://esichak.github.io/personal-website/**.

Every report is a folder in `content/trips/` with a Markdown write-up and the recorded track. Maps, elevation
profiles and track glyphs are rendered on your Mac from real terrain (AWS Terrain Tiles) and OpenStreetMap data, then
committed; GitHub Actions only assembles the pages. Everything is Python 3 standard library — nothing to install
except the tools macOS already has (plus `cwebp` from Homebrew for photos: `brew install webp`).

## Add a trip

Step-by-step guide: **[ADDING-TRIPS.md](ADDING-TRIPS.md)**. The short version:

```bash
# from a Garmin (or any) FIT/GPX file, with photos
python3 tools/add_trip.py ~/Downloads/Morning_Ski.fit --title "Rose Knob Peak" --activity ski \
    --place "Mount Rose" --region "Lake Tahoe" --party "Adam" --photos ~/Desktop/rose/

# or straight from a Strava bulk export (title, stats, description and photos come along)
python3 tools/add_trip.py --strava-export "~/Documents/Outdoors/Strava Export 4:14:26" --strava-id 17094418552

# another day of a multi-day trip
python3 tools/add_trip.py day3.fit --day-of chamonix-zermatt-haute-route --title "Le Châble → Cabane de Prafleuri"
```

`--activity` is one of `ski`, `climb`, `hike`, `mtb`, `other` (use `--subtype SUP|Rafting|Kayaking|Mountaineering`
with `other`). The script creates `content/trips/<slug>/` and renders its maps. Then:

1. Edit `content/trips/<slug>/index.md`: write the report under the front matter (Markdown), check `place`,
   `region`, `party`, add `beta:` rows, and give every photo an `alt:` description.
2. Preview: `python3 tools/build.py --serve` and open http://localhost:8000 (the new report is also on http://localhost:8000/trips/).
3. Publish: `git add "content/trips/<slug>" "rendered/trips/<slug>" && git commit -m "Add <trip>" && git push`. The site
   updates in about a minute. (Stage by path: `rendered/` holds untracked iCloud conflict copies such as `meta 3.json`,
   and `git add -A` would commit them all.)

Useful front-matter fields (see any existing trip for the format):

| Field | Meaning |
| --- | --- |
| `title`, `activity`, `subtype`, `date`, `start_time`, `timezone` | Basics (filled in by `add_trip.py`) |
| `place`, `region`, `party` | "Sawtooth Ridge", "Eastern Sierra", "Adam" — `region` groups trips on the map page and is a filter on the Trips page |
| `route_shape` | `loop`, `out-and-back` or `point-to-point` (detected from the track) |
| `stats` | `distance_km`, `moving`, `elapsed`, `gain_m`, `loss_m`, `high_m`, `low_m` (Strava's numbers, or computed) |
| `featured: true` | Eligible for the section pages' "Featured" block (single-day trips only; the home page is picked in `content/home.json`, see below) |
| `cover_photo`, `cover_focal_x`, `cover_focal_y` | The photo the home page's cards use for this trip (a path declared under `photos`) and where to keep in the crop, 0–100 (default 50/50) |
| `card_summary` | Optional one- or two-sentence factual summary for the home page's featured card (the report's opening is used when it is absent) |
| `search_aliases` | Other names people might search for, as an inline list (`[PCT, Pacific Crest]`); searched on the Trips page, never shown |
| `draft: true` | Keep it off the site |
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

## Re-render or rebuild

```bash
python3 tools/render.py              # render anything whose track or map settings changed (needs internet)
python3 tools/render.py --charts     # only elevation profiles (fast, offline)
python3 tools/build.py --check       # build _site/ and check every link and image
python3 -m unittest discover -s tests   # the generator's unit tests (curation, covers, summaries, search index, Trips page, header)
```

## Privacy

Tracks are published in full (not trimmed), with timestamps; use `add_trip.py --strip-times` to publish a GPX
without times. Photos are re-encoded as WebP with all EXIF/GPS metadata removed. Maps are for illustration, not
navigation.

See `docs/DEVELOPING.md` for how the site generator works.
