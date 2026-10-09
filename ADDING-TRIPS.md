# Adding a trip report

How to put a new trip on https://esichak.github.io/personal-website/. Everything runs in this folder on your Mac. GitHub
rebuilds and publishes the site on its own every time you push.

## 1. Get the track file

- **Garmin Connect:** open the activity → ⚙ → **Export Original**. You get a `.zip`; unzip it to get the `.fit` file.
- **Strava:** open the activity → ⋯ → **Export GPX**.

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
| `--subtype` | Only with `other`: `SUP`, `Rafting`, `Kayaking` or `Mountaineering` |
| `--place` | The specific spot, e.g. "Mount Rose" (optional) |
| `--region` | Reuse an existing region so the trip joins its region map (list below) |
| `--party` | Who you went with, e.g. "Adam" (optional) |
| `--photos` | A folder of photos, or individual photo files (optional) |
| `--draft` | Keep the trip off the site until you remove `draft: true` from its file |

Regions already on the site: Lake Tahoe, Santa Cruz, Eastern Sierra, Boise, Bay Area, Tetons, Alps, Oregon, Utah,
Yosemite, Washington, Idaho, Minnesota, Arizona. A new region name is fine too; it gets its own region map once it has
three trips.

The command creates `content/trips/<trip-name>/` with the GPX track, web copies of the photos (GPS and camera data
removed) and the stats, then draws the maps and elevation profile. That takes about a minute and needs the internet.

**Multi-day trips:** add the first day as above, then add each later day with `--day-of <trip-name>`:

```bash
python3 tools/add_trip.py day2.fit --day-of rose-knob-peak --title "Hut → Summit"
```

**From a Strava bulk export** (Strava settings → Download your data): the title, stats, description and photos come
along automatically.

```bash
python3 tools/add_trip.py --strava-export "~/Downloads/strava_export" --strava-id 17094418552
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

  `featured: true` makes the trip eligible for its section's Featured block; the home page's features are listed in
  `content/home.json` (see `docs/CONTENT_GUIDE.md`). `beta:` rows show
  beside the report. `map: peaks:` labels those summits on the map (run `python3 tools/render.py` after changing it).
  Keep comments out of this block: a `#` note at the end of a line breaks it. Any existing trip's `index.md` shows the
  format.

## 4. Preview it

```bash
python3 tools/build.py --serve
```

Open http://localhost:8000 to check the page, then press Ctrl+C to stop.

## 5. Publish

```bash
git add -A && git commit -m "Add Rose Knob Peak" && git push
```

The trip is live about a minute later.

## Quick fixes from anywhere

For small text changes (a typo, a better title, a photo description), you can edit the trip's `index.md` directly on
github.com: open the file, click the pencil, and commit. The site redeploys on its own. Run `git pull` in this folder
before your next local change so the two stay in step.

## Or let Claude do it

Open Claude Code in this folder and say something like: *"Add this trip: ~/Downloads/Morning_Ski.fit, photos in
~/Desktop/rose, ski tour on Rose Knob Peak with Adam."* Claude runs the steps above, writes the photo descriptions,
previews the page and pushes it.

## If something goes wrong

- **`cwebp` not found:** run `brew install webp` (photos fall back to larger JPEGs without it).
- **A map is missing its roads or lake names:** OpenStreetMap was busy. Run `python3 tools/render.py` again later; it
  retries anything that didn't finish.
- **Changed a trip's title or map settings:** run `python3 tools/render.py` to redraw its maps before pushing.
- More detail on how the site works: `README.md` and `docs/DEVELOPING.md`.
