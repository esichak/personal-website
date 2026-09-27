# Eric Sichak — Trip Reports

Trip reports with GPX maps: backcountry skiing, climbing, hiking, mountain biking and other trips (paddleboarding,
rafting, kayaking, mountaineering). Live at **https://esichak.github.io/personal-website/**.

Every report is a folder in `content/trips/` with a Markdown write-up and the recorded track. Maps, elevation
profiles and track glyphs are rendered on your Mac from real terrain (AWS Terrain Tiles) and OpenStreetMap data, then
committed; GitHub Actions only assembles the pages. Everything is Python 3 standard library — nothing to install
except the tools macOS already has (plus `cwebp` from Homebrew for photos: `brew install webp`).

## Add a trip

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
2. Preview: `python3 tools/build.py --serve` and open http://localhost:8000.
3. Publish: `git add -A && git commit -m "Add <trip>" && git push`. The site updates in about a minute.

Useful front-matter fields (see any existing trip for the format):

| Field | Meaning |
| --- | --- |
| `title`, `activity`, `subtype`, `date`, `start_time`, `timezone` | Basics (filled in by `add_trip.py`) |
| `place`, `region`, `party` | "Sawtooth Ridge", "Eastern Sierra", "Adam" — `region` groups trips on the map page |
| `route_shape` | `loop`, `out-and-back` or `point-to-point` (detected from the track) |
| `stats` | `distance_km`, `moving`, `elapsed`, `gain_m`, `loss_m`, `high_m`, `low_m` (Strava's numbers, or computed) |
| `featured: true` | Eligible for the home page and section "Featured" blocks |
| `draft: true` | Keep it off the site |
| `beta` | List of `label` / `value` rows shown beside the report |
| `map` | `peaks: [Mount Tallac]` to label summits, `places: [...]`, `water_labels: [{text, x, y}]` |
| `photos` | `file`, `w`, `h`, `alt`, optional `caption` |

## Re-render or rebuild

```bash
python3 tools/render.py              # render anything whose track or map settings changed (needs internet)
python3 tools/render.py --charts     # only elevation profiles (fast, offline)
python3 tools/build.py --check       # build _site/ and check every link and image
```

## Privacy

Tracks are published in full (not trimmed), with timestamps; use `add_trip.py --strip-times` to publish a GPX
without times. Photos are re-encoded as WebP with all EXIF/GPS metadata removed. Maps are for illustration, not
navigation.

See `docs/DEVELOPING.md` for how the site generator works.
