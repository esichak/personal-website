# Personal Trip-Report Website: Improvement and Implementation Plan

Prepared for Eric Sichak | October 8, 2026

**Revision:** Added the requested Tick list feature, Phase 2T, source-aware GPX intake, goal lifecycle, and AI-assisted enrichment workflow. This updates the implementation specification; it does not modify or deploy the website.

**Recommendation:** Keep the existing static Python site and Datum visual identity. Turn the homepage into a curated introduction to your best trips; keep the complete activity archive as a separate discovery tool. Lead with photography and stories, then make route data easy to reach.

## 1. Scope, evidence, and implementation boundaries

This is a source-level audit and implementation specification, not an implemented redesign. The public repository was inspected, along with the page structures of Stav is Lost. The live GitHub Pages URL could not be retrieved in the audit environment. No local site build, rendered browser comparison, Lighthouse audit, or live interaction test was completed. Responsive observations below come from the actual CSS and generator code, not inferred screenshots.

Repository inspected: `https://github.com/esichak/personal-website`

Live destination: `https://esichak.github.io/personal-website/`

The repository tree returned commit `a9baab989f9afd74f8142b127ec8f04d8995bad4` during the audit. Re-read the current checkout before implementing; do not overwrite subsequent work to force agreement with this snapshot.

Source references such as [R3] and [W2] refer to the evidence register at the end. Proposed files, fields, and behaviors are explicitly identified as new.

### Non-negotiable constraints

- Retain Python 3 standard-library production builds, the existing Markdown content workflow, GitHub Pages deployment, and committed map assets. No React/Next.js migration, database, hosted CMS, or mandatory npm/pip production build.
- Preserve Eric's existing narrative text, titles, dates, stats, photo metadata, and original recorded tracks. Front-matter additions for presentation are permitted; silently rewriting reports is not.
- Preserve report URLs, GPX URLs, existing map URLs, and PCT day/month anchors. Adding `trips/` as an index must not rename `trips/<slug>/`.
- Keep maps, elevation profiles, unit switching, activity-specific stats, accessible galleries, and no-JavaScript reading/navigation.
- Do not invent route grades, slope angles, summit elevations, conditions, personal recollections, captions, or completion claims. Missing facts remain missing.
- Work locally on a dedicated branch after inspecting the working tree. Do not reset unrelated changes, rewrite Git history, push, or deploy without separate authorization.

## 2. What the current site already does well

The project already has responsive terrain maps, GPX downloads, multi-day reports, a PCT series, an accessible photo dialog, unit switching, category pages, region browsing, an archive, and RSS. The build also generates canonical URLs, Open Graph metadata, a sitemap, robots.txt, and internal link/image/anchor checks. These are foundations to retain, not features to rebuild. [R1, R2, R6, R7, R8]

The existing Datum design is coherent: warm paper, dark ink, strong typography, small activity-color accents, and red route lines. Keep its distinctive map-and-journal character rather than replacing it with a generic travel template. [R2]

### Verified opportunities

| Finding | Evidence | Recommended response |
| --- | --- | --- |
| Homepage features only one report: the first flagged item in the newest-first published list, otherwise the newest item. | `home.featured()` and `content.load_all()` [R3, R5] | Introduce an ordered homepage manifest, independent of date and category features. |
| Featured photos are hidden below 1,000px; homepage action buttons are hidden below 760px. | `.hom-fphoto` and `.hom-cta` [R4] | Display photographs and meaningful navigation on phones as first-class content. |
| Cover selection uses the first parent photo, then the first available day photo. | `home.first_photo()` [R3] | Add explicit cover selection and focal-point controls. |
| Homepage latest reports are a ten-item table. | `home.latest()` [R3] | Use six visual entries on the homepage; retain the dense table in the archive. |
| The general archive is bundled into `map/`; its JavaScript has activity filters but no free-text search. | `home.latest()`, `archive.js` [R3, R9] | Add a dedicated Trips explorer with text search and combined filters. |
| Single reports put stats, maps, and profiles before the narrative and gallery. | `report.page()` [R7] | Provide a more inviting narrative-first presentation without obscuring route tools. |
| PCT is already a series with month navigation and a write-ups-only filter. Its parent index has no narrative or photos. | `series.py`, PCT front matter [R8, R10] | Improve that landing page; do not create a redundant series system. |
| A series excerpt can lose its day label when the caller uses `core.excerpt()` instead of `excerpt_parts()`. | Homepage and core helpers [R3, R6] | Never present an individual day's experience as the summary of the entire PCT. |
| All page CSS and JavaScript are bundled globally. | `css_bundle()` and `js_bundle()` [R6] | Measure the result, then split assets only when the measured benefit justifies it. |

## 3. Direction: editorial homepage, practical archive

The website should answer four different visitor questions without forcing one layout to do everything:

**"What should I read first?"** The homepage answers with three curated highlights.

**"Have you done something near this place?"** The Trips explorer and map answer with search, filters, and geographic links.

**"What happened, and what was the route?"** The report page answers with photography, Eric's writing, and accessible route information.

**"What do I want to do next?"** The Tick list answers with future objectives, planned routes, research notes, priority, and links to eventual attempts/completions. See Section 20.

Stav is Lost is useful inspiration for explicit discovery paths, clearly separated report sections, route-order peak information, and photographs that help explain a trip. Its homepage, map, search, and report pages expose these functions directly. Borrow those organizing principles, not its writing, photography, commercial features, or complete appearance. [W1-W4]

Do not turn this personal journal into an exhaustive route-guide business. Useful trip information and a complete personal archive are enough.

## 4. Priority roadmap

Complexity is relative implementation scope, not a time estimate.

| Priority | Work package | Value | Complexity | Dependency |
| --- | --- | --- | --- | --- |
| P0 | Baseline checks, route inventory, screenshots | Protect existing work and reveal actual layout issues | Small | None |
| P0 | Three manually curated homepage features | Directly fulfills the requested change | Medium | Baseline |
| P0 | Shared cover and summary resolution | Consistent photos, correct PCT presentation | Medium | Content loader review |
| P0 | Mobile photography and visible home navigation | Fixes a concrete responsive shortcoming | Small | Homepage redesign |
| P1 | Trips explorer with search and combined filters | Makes the growing archive usable | Medium | Shared cards and metadata |
| P1 | Tick list with GPX intake, planning notes, and completion links | Makes future goals easy to save, research, and revisit | Medium | Existing planned-route model; reuse explorer where available |
| P1 | Report layout and section navigation | Improves reading while retaining route utility | Medium | Shared covers |
| P1 | PCT landing and written-entry navigation | Makes a flagship trip approachable | Medium | Shared cards; existing series model |
| P1 | Content validation and regression coverage | Keeps future publishing reliable | Medium | Starts in first release; expands throughout |
| P1 | Related reports, share metadata, performance fixes | Better continuation and presentation | Medium | Core pages |
| P2 | Curated collections and region landing pages | More ways to browse substantial existing content | Medium | Explorer |
| P2 | Verified summit index | Valuable for peak-oriented reports | Medium/Large | Explicit summit metadata |
| P2 | On-demand interactive geographic explorer | Useful only beyond the current static maps | Large | Data model, provider decision, performance budget |

**Release recommendation:** Implement the homepage first, then the Trips explorer, Tick list (Phase 2T), reading improvements, and hardening as separate reviewable changes. Phase 2T can also be run independently against the existing site when it is the immediate priority. Do not let an interactive-map rebuild delay either requested feature.

## 5. Homepage specification

### 5.1 Final hierarchy

1. Compact header and short introduction.
2. Featured trips: PCT lead, Matterhorn Peak, PEAK BAGGING SZN.
3. Recent outings: six entries, with appropriate photos or route-thumbnail fallbacks.
4. Compact exploration links by activity and region.
5. Optional lightweight map preview leading to the full map.
6. Brief factual author introduction and footer.

Avoid stacking a full-screen hero, a second full-screen feature, ten archive rows, multiple map panels, and every possible collection. The featured block should be the visual center of the page.

Retain the existing headline initially unless the rendered design benefits from changing it. A suitable proposed supporting line is: "Stories, photos, and routes from days outside." This is positioning copy, not a fabricated trip description.

### 5.2 Desktop wireframe

```text
Eric Sichak          Trips   Tick list   Map   PCT   About   Search

Trip reports from the Sierra, the Alps, and beyond.
Short introduction.  [Browse trips]  [Explore the map]

FEATURED TRIPS
+-------------------------------------+------------------------------+
|                                     | Matterhorn image | title     |
|       PCT lead photograph           |                  | metadata  |
|                                     |                  | summary   |
|                                     +------------------------------+
| Pacific Crest Trail 2024            | Peak Bagging image | title   |
| Journal / date range                |                    | metadata|
| Explore the journal                 |                    | summary |
+-------------------------------------+------------------------------+

RECENT OUTINGS                         View all trips
[ photo / route ] [ photo / route ] [ photo / route ]
[ photo / route ] [ photo / route ] [ photo / route ]

EXPLORE BY ACTIVITY / REGION
Compact text links or small cards, not another large dashboard.

Small map teaser or author introduction, then footer.
```

The wireframe specifies hierarchy, not fixed pixel heights. Use a lead card plus two compact supporting cards. Supporting cards may place an image beside the copy on wide screens. Avoid brittle height matching or relying on unusually short titles.

### 5.3 Responsive rules

On desktop, the PCT is visually larger, with Matterhorn and Peak Bagging alongside. On tablet, the PCT spans the row and the two supporting cards sit beneath it. On mobile, all three become a vertical sequence in the same order, each with a visible photograph and readable title.

No carousel, automatic rotation, hidden swipe-only content, or map-first substitute for the phone photograph. Feature cards must remain discoverable through ordinary scrolling and links.

Keep both homepage navigation actions visible on mobile. Let them wrap or stack. The first viewport should show the introduction and the start of real featured content, not an oversized heading alone.

### 5.4 Featured card content

Use a selected cover, original report title, activity or journal label, location/date where useful, no more than two primary data points, a short truthful summary, and a clear destination.

For ordinary trips, distance and gain are useful. For the PCT, the date range and "Journal" label may communicate more than enormous aggregate numbers. Any aggregate shown must say "recorded" where appropriate; it is not automatically total trail length or days spent on trail.

Text should usually sit on the paper surface beside or below photographs, not on top of a busy image. Do not truncate identifying parts of route names to fit a rigid card. Make the title the clear accessible link name and avoid nested links inside a whole-card anchor.

### 5.5 Recent outings

Replace the homepage's ten-row table with six compact visual cards or image-led rows. Exclude the three featured parents from this shelf to avoid immediate repetition; do not exclude them from the actual archive.

Keep brief outings and track-only entries available. A report without narrative should not be forced to display an empty summary or a misleading "Read the story" button. Use "View trip" instead.

Initially order by the existing trip date and call the section "Recent outings." Do not call a backfilled old outing a newly published report unless real publication metadata exists.

## 6. Manual curation: exact implementation contract

### 6.1 One authority for homepage selection

Create **new** `content/home.json`:

```json
{
  "featured_slugs": [
    "pacific-crest-trail-2024",
    "matterhorn-peak-west-couloir",
    "peak-bagging-szn"
  ]
}
```

Array order determines display order; the first entry is the lead. This file controls homepage curation only. Existing `featured: true` values retain their current category/section behavior. Do not make authors coordinate two conflicting homepage selection systems.

The content paths above are confirmed existing trips. The PCT and Matterhorn already have `featured: true`; Peak Bagging currently does not. The manifest must nevertheless display exactly the three requested items. [R10-R12]

### 6.2 Validation and fallback rules

Resolve the manifest after loading content, before rendering pages. The strict build must reject malformed JSON, a non-list value, duplicate slugs, unknown slugs, drafts, and planned routes in an explicit featured selection.

Allow zero through six selections. An explicit empty list hides the section; it must not silently show a different trip. An absent configuration file may temporarily preserve the legacy selection for backward compatibility, with a migration warning. Once the file exists, never silently replace an invalid explicit selection with the newest report.

Zero, one, two, three, and six cards must all render cleanly. Adding a newer trip must not displace any configured feature.

Errors should name the configuration file and problematic slug. Do not rely on an empty `next()` result or a generic stack trace to explain a publishing mistake.

### 6.3 Optional presentation metadata

Introduce these optional trip-level front-matter fields, using syntax supported by the existing custom parser:

```yaml
cover_photo: photos/01.webp
cover_focal_x: 50
cover_focal_y: 45
card_summary: A short, factual editorial summary.
```

The sample summary is illustrative schema text, not publishable copy. The exact `photos/01.webp` example is valid for Matterhorn, not an assumed path for every trip.

`cover_photo` is a path relative to the trip directory and must resolve to a photo already declared in that trip or its days. Reuse the matched photo's width, height, alternate text, and smaller version. Focal coordinates are numeric percentages from 0 through 100, defaulting to 50/50 when omitted. Reject invalid explicit values.

Normalize these fields in `tools/lib/content.py`. It currently preserves raw metadata but does not expose these new fields in the shared trip dictionary. Also verify the local front-matter parser rather than assuming full YAML support. [R5]

Cover resolution order: explicit valid selection; suitable parent photograph; suitable day photograph; existing route thumbnail; neutral non-photographic card. Explicit broken paths are errors, not invitations to hide mistakes with a fallback. Prevent paths escaping the trip directory.

Prefer an available landscape photo for automatic card fallbacks, based on recorded dimensions. Never pretend this automatic choice is editorial approval.

### 6.4 Summary resolution and provenance

Use a shared presentation helper, not a separate ad hoc implementation on every page:

1. Explicit `card_summary`, written or verified from the actual report.
2. An excerpt of the parent report.
3. For a series, a clearly labeled excerpt from a specific written day.
4. A neutral factual description from existing fields, such as a dated journal organized by recorded day.
5. No summary when none is appropriate.

Return both text and provenance, for example `text`, `source_kind`, and `source_label`. Do not return only the first day's prose for callers to mistake for a whole-journey description. Fix the existing homepage use of `core.excerpt()` as part of this change. [R3, R6]

For the PCT feature, prefer a neutral series description over the first daily anecdote. The parent index currently contains no narrative. Do not generate first-person reflections to fill the gap. [R10]

### 6.5 Initial selections and image direction

| Feature | Treatment | Initial image direction | Content safeguard |
| --- | --- | --- | --- |
| Pacific Crest Trail 2024 | Lead journal card linking to the existing series URL | Inspect real day photos and choose a landscape that represents the journal. Resolve its actual filename and existing metadata. | No fabricated parent story, mileage, or number of days. |
| Matterhorn Peak - West Couloir | Supporting ski report | `photos/01.webp` is a candidate; its existing alternate text describes Sawtooth granite spires and snow couloirs. Inspect the image before finalizing the crop. | The report disputes a guidebook's 35-degree description. Do not present 35 degrees as verified difficulty. |
| PEAK BAGGING SZN | Supporting single-day hiking/scrambling report | Inspect `photos/03.webp` or `photos/04.webp` as alternatives to the first selfie. Existing descriptions indicate scenic basin views. | This is one loop report, not a season-long collection. Preserve the original title. |

These are source-informed photo candidates, not the result of a visual image review during this audit. [R11, R12]

## 7. Visual design system

### Keep the identity

Retain paper `#F2F1EC`, ink `#16171A`, route red `#D2381A`, and the existing activity colors. Keep Archivo for interface/headings, Source Serif 4 for prose, and Geist Mono for genuinely measured values. Preserve square-edged photography and restrained controls. These are existing design tokens, not a new palette. [R2]

### Change the emphasis

Make photographs substantially more prominent on home and report headers. Reduce the quantity of small all-caps metadata and repeated statistic strips above the fold. Give narrative text room to breathe without making every page tall and sparse.

Use a consistent card component with variants for featured, recent, related, and search results. Keep compact table rows for dense archive use rather than forcing every listing into a photo grid.

Suggested project targets: body text around 18-20px for report prose, line height around 1.6, roughly 60-70 characters per line, and restrained fluid headings. Work within the existing approximately 620px prose width and 1,248px content container unless rendered testing reveals a reason to change them. [R2]

Cover crops may use `object-fit: cover` plus a validated focal point. Galleries should preserve image proportions. Do not crop all portrait images into landscape thumbnails outside contexts that specifically require a cover crop.

Limit animation to short, nonessential hover/focus transitions. No parallax, animated route drawing on every visit, background video, moving carousels, or scroll-jacking. Honor reduced-motion preferences.

## 8. Navigation and Trips explorer

### 8.1 Simplify the primary navigation

Target: **Trips | Tick list | Map | PCT | About**, plus a clearly named Search action. Add Tick list only when its real destination ships in Phase 2T. Keep the five existing activity pages as secondary exploration routes. Retain their URLs.

During the homepage-only release, link "Trips" to the functioning existing archive until the new index is ready. Do not ship a Search button or a new-route link that goes nowhere. Once the explorer exists, Search should lead to its real search input rather than creating a second competing search interface.

Keep units accessible on report pages and in the mobile menu. Avoid giving the global unit switch more visual emphasis than the site's main destinations.

### 8.2 Add a dedicated index

Create **new** `tools/sitegen/pages/trips.py`, producing `trips/index.html`. Register it in `tools/build.py`. Add matching page CSS and JavaScript only as required.

This coexists with all existing `trips/<slug>/` pages. Keep `map/` as the map destination and retain `map/#all-reports`, `map/#region-*`, and existing year anchors during the transition. The simplest first release keeps the old archive working rather than replacing it with a fragment-losing redirect.

Do not duplicate data-loading or filtering models between the old and new index. Reuse shared trip metadata and row/card helpers, even while both routes remain available.

### 8.3 First-release search and filters

Provide text search over title, place, region, activity label, and available report text. Add explicit aliases such as "PCT" for Pacific Crest Trail without changing the actual title. Add fields for explicit peak names only when those names are present in source content.

Combine search with activity, region, year, format, and "Has a write-up" filters. Default to all published trips; use Tick list as the primary destination for planned goals. Any optional inclusion of goals in report search must be explicit, separately labeled, and separately counted. Show a result count, active filter chips, a clear-all action, and an honest no-results state.

Start with newest/oldest and relevance sorting. Add distance or elevation sorting only when missing values are handled as unknown, not zero. Do not add difficulty filters until a useful body of consistent, verified difficulty metadata exists.

Cards can be the default browsing view, with the existing compact list/table style as an alternate view. Avoid implementing several barely different listing components.

### 8.4 URL and state behavior

Represent filter state in query parameters, for example:

```text
trips/?q=matterhorn&activity=ski&region=eastern-sierra&sort=newest
```

Define canonical allowed values and ignore unsupported parameters safely. Reload, shared URLs, browser Back/Forward, and returning from a report must preserve a understandable filter state. Use replace-state for ongoing typing and deliberate history entries for meaningful submitted/filter changes so Back does not traverse every keystroke.

Keep geographic/measurement filtering in canonical metric values; switching visible units must not change which records qualify.

### 8.5 Static implementation

Generate a lean search index at build time from the same content model. Use vanilla JavaScript; no search service, database, API token, or mandatory frontend framework.

Include identifiers, site-relative destination URLs, titles, filter metadata, normalized searchable text, and short snippets. Do not embed GPX coordinates or entire rendered SVGs. If daily PCT search is enabled in the later series phase, label those results as entries within a parent journal and keep parent-report counts separate.

Keep all parent report links in server-rendered HTML. Without JavaScript, the full list and category navigation still work; interactive search may be unavailable and should say so. A failed index fetch must not leave an endless loading state or erase the static archive.

Use safe DOM APIs for query text and snippets. Do not put untrusted query strings into `innerHTML`. If JSON is embedded in HTML, escape script-termination sequences. Validate paths and avoid root-relative links that escape the GitHub project prefix.

## 9. Trip-report reading experience

### 9.1 Give narrative reports a clear beginning

For reports with writing and photos, use a compact title/location/date header, a meaningful lead photo, a small stats row, and a section navigation before the reader reaches the narrative. Keep a direct "View route" link and GPX action visible.

Recommended reading order: title and context; lead photograph; compact trip facts; section navigation; report and supporting photos; route map/profile; remaining gallery; related reports.

This is a presentation default, not a demand to duplicate images or to bury route data. A reader who wants the map must reach it immediately through a link. For track-only entries or reports without photos, retain a compact map/data-first layout instead of manufacturing editorial content.

Preserve `#title`, `#stats`, `#map`, `#profile`, `#beta`, `#report`, and `#photos` wherever those sections exist. Do not leave navigation links pointing to omitted sections.

### 9.2 Section navigation

Use a consistent set of available sections: Report, Photos, Route, Trip details. Keep the existing phone bottom navigation and adapt it rather than adding a second competing sticky bar. Its labels and targets must match the actual content.

The report already supports GPX actions, a photo viewer, an elevation table disclosure, and full-size map pages. Improve their placement and test them; do not build redundant replacements. [R7]

### 9.3 Trip facts and route context

Keep activity-specific statistics. A climbing approach's GPX gain is not the climbing route's technical length; flat-water reports need different emphasis than ski tours. The existing components already account for several such differences. [R6]

Promote useful existing beta fields such as trailhead, objective, route shape, party, and documented logistics. Hide missing fields. Add an explicit "As recorded on [trip date]" context near route information so historical reports do not imply current conditions.

Keep surveyed summit elevations distinct from the highest GPS point. Preserve attribution when a grade or slope angle comes from an external guidebook, especially when Eric's text disputes it.

### 9.4 Photos and captions

Retain the existing lightbox and native full-image links. Test keyboard navigation, Escape, focus return, touch controls, portrait handling, caption display, and image-load errors.

Support route-relevant captions where Eric supplies them: identifying a key turn, describing a route-finding decision, or explaining a terrain section. Do not automatically turn visual guesses into route advice. Keep original photo ordering unless a deliberate editorial change is documented.

Avoid displaying the same image as both a hero and the first gallery item unless the repetition serves a purpose. If the cover is removed from the visible gallery sequence, ensure the viewer's photo counts and navigation remain consistent.

For informative images, alternate text should convey useful image content; decorative images should not create repetitive announcements. This distinction follows W3C's image guidance. [W5]

### 9.5 Continuation and sharing

Add up to three related reports using a transparent rule: same explicit collection or region first, then activity, with date as a tie-breaker. Exclude the current report, drafts, planned routes, and duplicates. Keep the existing newer/older links where useful.

Provide a copy-link action with a normal selectable URL fallback. Share a particular PCT entry using its existing anchor. Do not require an account, install prompt, or third-party social script to share a report.

## 10. PCT as the flagship journal

The PCT is already `kind: series`, with recorded days grouped by month and a written-days filter. Build on that model. The parent source currently supplies the title, date range, place, and region but no introductory story. [R8, R10]

Add a real selected cover and a reader-facing introduction assembled only from those facts until Eric writes his own. Make "Read the first written entry" and "Browse all recordings" distinct actions.

Add a small selection of journal highlights, chosen through explicit day IDs rather than automatically equating longest distance with most interesting story. Initially use an optional `journal_highlights` list in the PCT's metadata, normalized and validated by the loader. Keep the list empty until actual entries are inspected; the absence of highlights must not block the rest of the redesign.

Keep month browsing and the all-recordings view. Written entries may be the initial reader mode, but a direct day/month hash must reveal its destination even when that destination would otherwise be hidden. Handle hash changes after load, not only the first page request.

Provide previous/next written-entry navigation with precise labels. Recorded day labels may contain decimals; reuse the existing `day_anchor()` helper rather than inventing a conflicting conversion. Keep the GPX filename and displayed day label distinction intact.

Daily search results should identify their parent journal, day/date, and source snippet. They should link into the existing canonical series page during this release. Do not create hundreds of new day routes merely to add search.

If geographic chapters such as Sierra or Oregon are added later, require explicit author-reviewed chapter assignments. Do not infer every boundary from a title or invent a complete geographic chronology.

Optional later enhancement: a local-only "Continue reading" bookmark based on the last deliberately opened entry. No server account or tracking service is required. Treat this as a convenience, not a first-release requirement.

## 11. Additional discovery ideas worth adding later

### Curated collections

Examples include Sierra scrambles, backcountry ski tours, and multi-day Alpine trips. A collection is an ordered list of existing parent reports, not a new copy of their content. Publish only collections supported by enough real reports to be useful.

Keep collections separate from the PCT's existing series semantics and from the original single-day PEAK BAGGING SZN report.

### Region pages

A region page can combine a short factual introduction, selected reports, a compact map, and links into the filtered archive. Start with populated regions such as those already used on the homepage rather than generating thin pages for every incidental location.

### Verified summit index

Introduce optional structured summit names and outcomes when explicitly supported by a report. PEAK BAGGING SZN already names eight peaks in its narrative, making it a useful candidate for author-reviewed structured metadata. [R12]

Store name, optional stable identifier, and outcome/route order if known. Do not infer that a named map label was summited, equate GPS maximum with summit elevation, or assume similarly named peaks are the same. Do not publish an all-time peak count until deduplication and completion semantics are established.

### Interactive map, on demand

The existing map should remain the default reliable fallback. A later enhancement could synchronize visible reports with the map viewport, let visitors filter activity, and show a selected report card. This is inspired by the reference site's map/list organization, not a requirement to reproduce its full implementation. [W3]

Before adding a map library, choose and document the tile provider, usage conditions, attribution, costs, key restrictions, accessibility fallback, and loading budget. Load the interactive layer only on the map page or after explicit activation. Do not expose secret credentials or assume unlimited free tile hosting.

Do not add 3D terrain or GPX playback before ordinary geographic discovery works well.

## 12. Performance, metadata, and reliability

### 12.1 Measure before optimizing

Baseline the homepage, Trips index, Matterhorn report, Peak Bagging report, PCT series, and map page. Record transferred bytes, initial image requests, rendered layout, console errors, and representative performance measurements. Do not label estimates as benchmark results.

Recommended performance goals are LCP at or below 2.5 seconds, CLS at or below 0.1, and INP at or below 200 milliseconds at the 75th percentile when sufficient real-user data exists. These are targets, not measured scores for this website. Lab Lighthouse does not establish a field INP result. [W6]

Proposed first-release budgets: keep initial mobile homepage transfer around 1-1.5 MB or less, lead-photo variants around 250-300 KB or less when image quality permits, and avoid loading an interactive map or all trip photos on the homepage. Record exceptions instead of ruining photographs solely to hit an arbitrary byte threshold.

### 12.2 Images and map loading

Use the existing WebP workflow and 800/1,600px variants. Add a smaller card derivative only when measurements justify it. Provide dimensions, correct `srcset`/`sizes`, and an intentional priority for the actual largest above-the-fold image.

The chosen lead image should not be lazily delayed. Offscreen galleries and map previews should not compete with it. When moving a report map below the fold, revisit its existing high-priority preloads; do not keep preloading both the new photo hero and every map variant as equally critical. [R6, R7]

Keep full map detail on report/map pages. Homepage cards usually need photographs or small cached route thumbnails, not multiple large inline terrain fragments.

### 12.3 CSS, JavaScript, and fonts

Measure the current global bundles before splitting them. If worthwhile, keep shared CSS/JavaScript plus page-specific additions and test dependency/order assumptions. Do not perform a broad bundler migration to save a modest amount of CSS. [R6]

Self-hosting the existing fonts is optional, subject to their licenses. It is not a reason to add more typefaces. If font assets are placed in a new nested directory, extend the build's copy logic: its present top-level assets glob does not automatically publish arbitrary nested font folders. [R6]

On the long PCT page, distinguish transfer weight from rendering cost. Merely hiding existing day markup does not reduce downloaded HTML. Measure before adding pagination or aggressive rendering tricks, and preserve discoverability and anchors.

### 12.4 Search and share metadata

Keep the existing canonical, title, description, Open Graph, Twitter-card, RSS, sitemap, and robots output. Improve it by reusing selected covers, adding image descriptions/dimensions where appropriate, and providing a valid site-wide fallback when no photo exists. [R6]

Add accurate `BlogPosting` JSON-LD to genuine written reports only after validating it against the current schema guidance. Include applicable author, headline, image, and actual publication/update information. Google describes these properties as useful, but structured data is not a guarantee of a particular search appearance. [W7]

Trip date is not automatically publication date. Add optional `published_at` and `updated_at` only with honest semantics and supported values. Do not initialize them to the current build time or relabel trip dates to simulate freshness. Preserve existing ordering until a deliberate migration is documented.

Do not add aggregate ratings, invented review scores, FAQ content, or fake availability/conditions merely to produce richer metadata.

### 12.5 Validation

Add a standard-library content validator and focused unit tests. Validate explicit featured selections, cover references, focal points, date syntax, new metadata types, internal destinations, required files for advertised capabilities, and duplicate identifiers.

Use strict failures for broken explicit new configuration. Existing incomplete optional metadata should initially produce actionable warnings rather than suddenly making the entire legacy archive unpublishable. Missing optional fields should stay hidden in the UI.

Capability-driven rendering is important: no GPX file means no download button; no narrative means no Report tab; no gallery means no Photos link. Add fixtures for these cases even if current content happens to avoid them.

The existing `python3 tools/build.py --check` remains mandatory but is not a substitute for browser testing. [R6]

## 13. Privacy and historical conditions

The README explicitly states that recorded tracks are published in full with timestamps, and that photo EXIF/GPS is removed by re-encoding. Preserve those existing statements accurately. [R1]

The new Tick list contains future intentions, which need a separate publication review: keep private schedules, contacts, and unapproved GPX/research sources outside the public checkout. Draft flags do not provide privacy. See Section 20.8 for source-approval and upload rules.

Audit whether starts, finishes, timestamps, or sensitive locations reveal more than Eric intends. Any new privacy behavior must apply consistently to published GPX, visible maps, derived assets, and search metadata, not just hide a label.

A public repository is also a source of the underlying files. Sanitizing future site downloads alone does not remove raw tracks already committed publicly. Do not promise retroactive privacy from a UI switch, and do not rewrite repository history as part of a design release.

Changes that trim or remove data require a separate explicit decision. For this implementation, document exposure and preserve existing recordings. Keep historical-condition and not-for-navigation notices near relevant route information without repeating giant warnings across every card.

## 14. File-level change map

All entries marked New are proposed, not files discovered during the audit.

| File | Change |
| --- | --- |
| `content/home.json` - New | Ordered homepage feature selection. |
| `tools/lib/content.py` | Normalize optional cover, focal, summary, and later journal metadata; preserve old content behavior. |
| `tools/sitegen/curation.py` - New | Validate and resolve homepage selections with explicit fallback semantics. |
| `tools/sitegen/core.py` | Shared cover/summary/card helpers; navigation and metadata reuse; retain existing units, links, galleries. |
| `tools/sitegen/pages/home.py` | Replace the one-item feature algorithm and cross-coupled hero layout; render curated features and recent outings. |
| `assets/css/pages/home.css` | New responsive feature layout; visible mobile photos and actions. |
| `assets/css/base.css` | Reusable card styling and only necessary shared token adjustments. |
| `content/trips/pacific-crest-trail-2024/index.md` | Add verified cover selection and optional journal metadata without inventing a parent narrative. |
| `content/trips/matterhorn-peak-west-couloir/index.md` | Add cover/focal metadata if needed; preserve disputed slope-angle context. |
| `content/trips/peak-bagging-szn/index.md` | Add cover/focal metadata; preserve original single-day report. |
| `tools/sitegen/pages/trips.py` - New | Dedicated parent-report explorer at `trips/`. |
| `assets/css/pages/trips.css` - New | Explorer layout and responsive controls. |
| `assets/js/pages/trips.js` - New | Search, combined filters, view switching, URL restoration, safe failure behavior. |
| `tools/build.py` | Register the explorer, emit search data, invoke validation/checks, adjust assets only when justified. |
| `tools/sitegen/pages/report.py` | Conditional editorial layout, section actions, related reports, cover-based metadata, and a distinct planned-goal variant with completion links. |
| `assets/css/pages/report.css` | Photo-led report variant and mobile-safe section layout. |
| `tools/sitegen/pages/series.py` | PCT introduction, written-entry links, optional highlights, stable anchor handling. |
| `assets/css/pages/series.css` and `assets/js/pages/series.js` | Journal presentation, filter/hash interaction, existing navigation retained. |
| `assets/js/base.js` | Only targeted changes to shared menu, viewer, or share behaviors after reading existing code. |
| `tools/validate_content.py` - New | Clear content/configuration errors and legacy metadata warnings. |
| `content/trips/<goal-slug>/goal.json` - New, per planned goal | Status, priority, source provenance, references, checklist, and confirmed outings; no duplicated report identity/stats. |
| `tools/lib/goals.py` - New | Normalize/validate goal sidecars, active subsets, provenance, and completion relationships. |
| `tools/ticklist.py` - New | Local GPX/name-only intake, dry-run, updates, confirmed outings, review packets, and export. |
| `tools/sitegen/pages/ticklist.py` - New | Dedicated Tick list index; reuse the existing planned-report URL for detail pages. |
| `assets/css/pages/ticklist.css` and `assets/js/pages/ticklist.js` - New | Map-led cards, filtering, responsive controls, and shareable state; no public write credentials. |
| Existing GPX parser/rendering modules | Inspect and adapt goal paths for route elements, segment gaps, and missing elevation; preserve completed-report behavior. |
| `docs/TICK_LIST_GUIDE.md` - New | Import/review/publish workflow, goal statuses, privacy boundaries, AI enrichment prompt. |
| `tests/` - New or extend existing | Standard-library curation, metadata, route-compatibility, and search-index tests. |
| `docs/CONTENT_GUIDE.md` - New | How to feature/reorder trips, choose covers, write summaries, preview, and validate. |
| `docs/DEVELOPING.md` and `README.md` | Update documented contracts to match actual implementation. |
| Existing deployment workflow under `.github/workflows/` | Resolve its actual filename first; extend checks without moving terrain rendering into deployment. |

The generator and source content are authoritative. Do not hand-edit `_site/` and call the change complete. Do not casually regenerate `rendered/` for a layout-only change.

## 15. Implementation phases and acceptance gates

### Phase 0 - Baseline and safe working setup

Read the repo instructions and working tree. Record the current commit, existing routes/anchors, report counts, representative GPX checksums, and any existing validation failures. Inspect the existing front-matter parser and browser JavaScript before extending them.

Run the existing full build/check. Capture desktop/mobile screenshots of the six representative page types where browser tooling is available. Record the environment and any unavailable tests honestly.

**Gate:** Baseline is documented, unrelated changes are protected, and pre-existing problems are distinguished from new regressions. Do not claim a screenshot or performance check was performed when it was not.

### Phase 1 - Curated homepage and presentation foundation

Implement the exact three-item manifest, validation, shared cover/summary resolution, responsive featured layout, six recent outings, and working mobile actions. Choose real photographs after inspecting available images. Retain functional old archive links until the new route exists.

Add focused tests and author documentation. Do not rewrite report layouts or add an interactive map in this phase.

**Gate:** The homepage shows PCT, Matterhorn, and Peak Bagging in that order at phone/tablet/desktop widths. Reordering the manifest changes the order. A newer report cannot displace them. Photos remain visible below 1,000px. Invalid explicit curation fails clearly. Existing report/GPX URLs and the build check still pass.

### Phase 2 - Trips explorer and discovery

Add the parent index, build-time search data, combined filters, URL state, and card/list views. Connect the final navigation. Keep legacy map/archive links operational.

**Gate:** A visitor can find Matterhorn by name, combine skiing with Eastern Sierra, clear filters, share a filtered URL, and use Back/Forward without losing state. Zero matches and failed search loading are handled. No-JavaScript visitors retain all report links. Existing counts exclude drafts and do not double-count series days.

### Phase 2T - Tick list and future-goal workflow

Implement Section 20: a dedicated Tick list, minimal name/category/optional-GPX intake, source-aware route handling, optional planning metadata, local author updates, and explicit attempt/completion links. Reuse the existing `kind: planned` model without converting goals into reports. Prefer running after Phase 2; a dedicated standalone run may reuse the currently available components instead.

**Gate:** Import a GPX-backed goal and a name-only idea, locate both using filters, shortlist an objective, record an explicitly confirmed outcome, and connect a real report without overwriting planned or recorded tracks. Validate segmentation, unknown elevation, provenance, count/feed isolation, legacy planned pages, and public read-only behavior. Document privacy and the local publish workflow. No fabricated production goals, hosted admin backend, or automatic completion.

### Phase 3 - Reports and PCT reading

Improve report headers and available section links, preserve gallery/map functionality, add related reports, and improve the existing PCT landing and written-entry navigation. Add daily search only with clear parent attribution and without new duplicate canonical day pages.

**Gate:** Single-day, no-photo, track-only, multi-day, series, and planned examples still render appropriately. All legacy day/month anchors work, including decimal day labels and destinations hidden by an initial filter. A reader can reach route information in one deliberate action and read without an obstructive sticky UI.

### Phase 4 - Hardening, performance, metadata, and handoff

Finish validation coverage, including Phase 2T when implemented; measure performance before/after; implement only justified asset changes; improve cover-based social metadata; and add accurate structured data where appropriate. Document privacy observations without changing existing track publication policy.

**Gate:** The test matrix below is completed or explicitly marked blocked; no unexplained route/anchor/GPX regressions remain; author instructions reproduce the curation workflow; actual measured improvements are distinguished from unmeasured goals.

### Phase 5 - Optional expansion, not part of the core launch

Collections, region pages, a verified summit index, local reading bookmarks, or an interactive map require a fresh scope decision. They must not silently become prerequisites for completing Phases 1-4.

## 16. Test matrix

### Automated checks

| Area | Required cases |
| --- | --- |
| Featured configuration | Exact initial three; order changes; 0/1/2/3/6 entries; duplicate/unknown/draft/planned rejection; missing configuration compatibility; newer trip does not displace selection. |
| Cover resolution | Explicit parent image; declared day image; parent/day fallbacks; no photo; bad path; path traversal; missing dimensions; invalid focal percentage. |
| Summary provenance | Parent narrative; explicit summary; labeled day excerpt; neutral series description; no invented first-person PCT overview. |
| Source preservation | Existing narrative bodies and GPX checksums unchanged unless an intentional change is explicitly documented. |
| URLs and anchors | Root and `/personal-website/` prefix; all previous report/GPX/map routes; `map/#all-reports`; region/year anchors; PCT decimal day labels and months. |
| Search | Case/punctuation handling; aliases; combined filters; missing values; accurate counts; no drafts; parent/day distinction; safe escaping. |
| Conditional UI | No dead report/photos/profile/download links when the corresponding content is absent. |
| Tick list / intake | Name-only; route-only GPX; disjoint segments; alternative tracks; missing/partial elevation; sparse data; missing timestamps; duplicate import; safe parser/paths; dry-run; source checksum; unavailable map. |
| Goal lifecycle | Valid/invalid transitions; attempts and completion; no report/date; archive without losing outcome; backlinks; no auto-completion; no pollution of report totals/RSS/features. |
| Tick-list publication | Draft exclusion; public source approval; no raw private packets/paths/credentials in output; static read-only status; exact existing goal URLs/downloads retained. |
| Metadata | One title/canonical; valid absolute social-image URLs; truthful publication fields; no duplicate schema blocks; helper map pages remain excluded appropriately. |

Use standard-library unit tests for pure logic. Use available browser tooling for interaction checks; document any optional development-only dependencies separately from the production build.

Existing mandatory command:

```bash
python3 tools/build.py --check
```

After adding tests, the proposed standard-library command is:

```bash
python3 -m unittest discover -s tests
```

Use the full build for final checking rather than a partial build that intentionally lacks referenced pages.

### Browser and visual checks

Test widths 320, 390, 768, 1,024, and 1,440px; portrait and landscape where useful; 200% zoom; keyboard-only operation; JavaScript disabled; reduced motion; blocked image/index requests; long titles and empty optional metadata.

Check visible focus, skip link, heading structure, actual button/link semantics, image descriptions, menu focus behavior, lightbox focus return, and 44px project touch-target goals. Verify the bottom report bar respects safe areas and does not cover content or collide with other sticky elements.

Take before/after screenshots of home, explorer, Matterhorn, Peak Bagging, PCT, and map. Include a no-photo/track-only case and an existing multi-day page. Check the real browser network panel for image selection and priority rather than assuming `srcset` is working.

### Compatibility checks

Save an initial manifest of output paths and important anchors, then compare after changes. Existing paths should be a subset of the new output unless a deliberate, compatible migration is approved. Compare downloadable GPX content as well as link existence.

Because this is a project-site deployment, test a preview served under `/personal-website/`, not only a root-served preview. Keep link generation through `core.link()` and the existing canonical-site configuration.

## 17. Author workflow after implementation

To change homepage features, edit only `content/home.json`. Reorder slugs to change priority; add or remove slugs to change selection. No Python edit should be necessary.

To change a cover, choose an existing declared image and set `cover_photo`; adjust focal percentages after reviewing phone and desktop crops. To change card copy, add an accurate `card_summary` without changing the original report narrative.

Preview with the existing command:

```bash
python3 tools/build.py --serve
```

Run the full build check and tests before publishing through the existing Git workflow. Document how to resolve a missing slug, bad cover, absent photo, or invalid metadata value. Do not expose a browser-based admin panel or GitHub credential in the static site.

A small local curation helper script can be added later if hand-editing the JSON becomes inconvenient. It should edit the same manifest, not create another source of truth.

For future goals, use the new Phase 2T importer or ask Claude Code to run it with a GPX path, route name, and category. Review derived values and any proposed enrichment, explicitly approve public source material, and change a reviewed draft to public through the existing Git workflow. See Section 20 and `docs/TICK_LIST_GUIDE.md`. The companion prompt pack includes both implementation and ongoing intake/enrichment prompts.

## 18. Deliberately excluded from the core implementation

No framework rewrite, database, account system, comments backend, public admin UI, automatic AI-generated trip reports, synthetic personal photos, subjective score system, weather/avalanche-feed integration, full-screen video, rotating hero carousel, 3D map, GPX animation, or all-site visual rebrand.

Dark mode, an email newsletter, analytics, and a custom domain are separate decisions. None is a prerequisite for making this website substantially more attractive and useful.

Tick-list planning notes and reviewed factual enrichment are explicitly included in Phase 2T; they are not automatic AI-generated trip reports. A local-only upload desk is an optional enhancement to the importer, not a public admin UI or an exception permitting credentials in the static site.

## 19. Claude Code handoff contract

Use the companion `claude-code-website-prompt.md`. Normal sequence: Phases 0-1, Phase 2, Phase 2T, Phase 3, then Phase 4. Review each result before the next run. The dedicated Tick list prompt also works independently against existing components. This prevents a long specification from turning into one unreviewable rewrite.

For each phase, Claude Code should report changed files, implemented behaviors, tests actually run with results, screenshots actually captured, existing problems, any missing author inputs, and the next smallest implementation step. Keep a local implementation log in the repository's documentation.

Missing optional editorial content is not a reason to invent facts or stop all progress. Use the defined truthful fallback, complete unaffected work, and record the exact author input that would improve the result.

Completion means working generated pages with tested links and documented author controls, not simply new CSS or a prose summary of intended changes.

## 20. Tick list: future goals, route imports, and completion tracking

**Added at Eric's request on October 8, 2026.** This is a core requested feature, not one of the optional Phase 5 ideas. Implement it as **Phase 2T**, preferably after the Trips explorer so it can reuse search and card components. It may be implemented earlier against the existing components when it is the immediate priority; do not require a completed redesign to add a useful tick list.

### 20.1 Product goal and release boundary

Create a dedicated **Tick list** destination at `tick-list/`: an organized collection of routes Eric wants to do, with an easy way to add a GPX, categorize the objective, collect useful research, shortlist it, and later connect it to actual outings.

Minimum manual entry: **route name and primary activity**. A GPX is strongly useful but optional: Eric must be able to save an idea before finding a track. Region may initially be unknown. Everything else should be optional, derived from supplied data, or proposed for review. Do not turn saving a route into a lengthy questionnaire.

The initial delivery includes public browsing, individual goal pages, a local importer, author-controlled updates, planning notes, and links to attempts/completions. It does not include a public write API, logged-in social features, automatic safety recommendations, or continuous weather monitoring. No future objectives were supplied in this request: do not populate production with invented goals or assume earlier trip reports are future intentions.

### 20.2 Navigation, layout, and discovery

Final primary navigation becomes **Trips | Tick list | Map | PCT | About**, plus the working Search action. Add Tick list to the mobile menu as well. Keep activity pages as secondary navigation. Do not add a nonfunctional Upload button to the public header.

Use a restrained introduction: "Routes and objectives I'd like to get to." This is section-positioning copy, not a claim that any objective has been completed. A small summary can show active goals, shortlisted goals, and completed goals; no invented or hardcoded counts.

```text
TICK LIST
Routes and objectives I'd like to get to.

[Search goals........................................]
[Activity] [Region] [Status] [Priority] [Preferred month]
[More filters: tags / time commitment / GPX available]

Active goals | Shortlisted | Completed | Archived
Sort: Priority                 View: Cards | List

+----------------------+----------------------+----------------------+
| Route-map thumbnail  | Route-map thumbnail  | Neutral no-GPX tile  |
| Route name           | Route name           | Route name           |
| Region / activity    | Region / activity    | Region / activity    |
| Priority / status    | Priority / status    | Priority / status    |
| Approx. route stats  | Approx. route stats  | Route not added yet  |
| View goal            | View goal            | View goal            |
+----------------------+----------------------+----------------------+
```

Default to active, non-archived goals. Sort by Eric's priority, then newest-added, with slug as a deterministic final tie-breaker. Missing dates sort last. Combined filters, active chips, result counts, clear-all, no-results, query sharing, and Back/Forward should follow the Trips explorer's behavior. Search title, region/place, tags, and approved public notes, not unpublished research packets.

Use URLs such as `tick-list/?activity=hike&region=eastern-sierra&status=shortlisted&priority=high`. Values should be normalized through the same taxonomy as the report explorer. A query must not reinterpret unknown elevation or duration as zero. Show unknown values explicitly when a comparison depends on them.

Cards should be route/map-led, distinguishing future goals from the photo-led completed reports. Use existing route colors plus a text label and dashed planned-line treatment where supported; never rely on color alone. Do not borrow somebody else's summit photo to imply Eric has been there. A user-owned, appropriate photograph can be an optional cover using the existing cover helper.

Provide a static regional grouping/list in the first release. Interactive map/list synchronization can reuse the later geographic explorer, but must not block the tick list. Optional later: compare up to three goals side by side using approved facts and visible unknowns, not an AI-generated safety or overall difficulty score.

The public site displays status as a badge, not an editable checkbox that appears to persist. Any future browser-only favorites must be labeled "saved on this device" and must not modify Eric's authoritative tick list.

### 20.3 Fields: capture little, make the saved route useful

| Field | Entry source | Purpose / rule |
| --- | --- | --- |
| Route name and primary activity | Required from Eric | Reuse `title` and existing `activity` values. |
| GPX | Optional from Eric | Route visualization, downloadable approved source, approximate geometry-derived measurements. |
| Region and place | Eric, or researched suggestion | Searchable geography; coordinates alone must not be silently assigned to a guessed place name. |
| Tags | Eric, or suggestions | Examples: scramble, ridge-traverse, couloir, backpacking. Tags do not create incompatible new primary activities. |
| Status and priority | Eric | Organize intent, not algorithmic readiness. Default Idea / Normal. |
| Why this route | Eric | One sentence about its appeal; no invented personal motivation. |
| Preferred months / target year | Eric | Personal planning window, not a claim about best or safe conditions. |
| Typical season notes | Cited research, reviewed by Eric | Keep separate from preferred months and from current conditions. |
| Time commitment | Eric or attributed estimate | Half-day, full-day, overnight, multi-day; optional. No duration prediction from distance alone. |
| Technical difficulty | Attributed source plus review | Store grading system and value together, with uncertainty/context. Do not equate climbing grades, scrambling classes, and ski descriptions. |
| Route scope and origin | Eric, GPX metadata, source evidence | Full intended route vs approach-only/ascent-only/partial/unknown; drawn plan vs somebody else's recording. |
| References and access notes | Eric or cited research | Relevant report/guide/official access/permit sources, specific claims, and check date. |
| Preparation questions | Eric or AI draft | Route-specific gaps worth checking, not a percentage-based safety certificate. |
| Attempts and completion | Explicit confirmation from Eric | Optional date and linked report; preserve unsuccessful attempts and the original plan. |

Distance, elevation gain/loss, and highest point should be labeled as approximate values from the supplied geometry. "Highest point in GPX" is not "summit elevation." Do not present estimated gain from an approach-only track as the entire climbing objective's gain. GPX includes separate routes, tracks, and segments, and elevation/time fields are optional; the importer must preserve these distinctions. [W9]

Do not add a required star rating, beauty score, skill-readiness score, gear inventory, expected departure date, or collaborator account system. Optional personal notes should improve decisions rather than become data entry for its own sake.

### 20.4 Status, archive, and linking a goal to real outings

Use five statuses: `idea`, `researching`, `shortlisted`, `attempted`, `completed`. Display human-readable labels. Allow direct transitions: not every objective needs every stage. **Shortlisted is editorial intent, never "safe" or "ready to climb."**

Store archival separately as `archived: true|false`, so archiving a completed or attempted goal does not erase its outcome. Draft publication state remains the existing `draft` field; it is not a goal status and is not a privacy control.

Log attempts/completions as `outings` on the goal. Each event has an explicit `outcome` (`attempted` or `completed`), optional author-supplied `date`, optional existing `report_slug`, and optional short public `note`. A linked report must be a real non-planned report. Do not manufacture an exact date when Eric only confirms the outcome. Hide unknown dates.

A `completed` goal must have an author-confirmed completed event. An `attempted` status must have an attempted event. The update helper must reject inconsistent requests instead of filling in a fictional outing. Reopening a goal must preserve prior events and make the change explicit; archival never destroys them.

The goal stays a goal, at its original URL and with its original planned GPX. A new completed report gets its own recorded track and report URL. **Do not change the goal's `kind` to an ordinary trip, overwrite its planned track with an actual recording, or mark it completed from spatial similarity alone.**

Generate backlinks on reports from the goals' outing references; do not maintain a second hand-edited reciprocal list. One report may satisfy several explicitly confirmed goals, and one goal may have several attempts. Count goals and reports separately, never counting a linked report twice in report totals or a goal's planned distance as completed mileage. Completion without a write-up is allowed; use a completion event and omit the nonexistent report link.

### 20.5 Architecture: extend the existing planned-route model

The current loader already accepts `kind: planned`, stores routes under `content/trips/<slug>/`, and gives them `trips/<slug>/` URLs. The build separates them from published reports and excludes them from the report RSS feed. Reuse this model rather than creating a duplicate route database. [R5, R6]

For a new goal, keep ordinary identity/geography/body content in `index.md`, approved route geometry in the existing `track.gpx` location, and introduce a **new optional `goal.json` sidecar** for richer planning metadata:

```text
content/trips/<goal-slug>/
  index.md             # kind: planned; existing title/activity/place/body fields
  goal.json            # new: intent, source provenance, research, outings
  track.gpx            # optional; original approved public GPX
rendered/trips/<goal-slug>/
  ...                  # generated maps/profiles/derived geometry, as supported
```

Minimal front matter, using placeholder text only in documentation:

```yaml
---
title: YOUR ROUTE NAME
activity: hike
kind: planned
draft: true
---
```

Do not set `date` to the GPX's recording date, import date, or an invented future attempt date. Use a distinct optional `added_at` for the actual import date and `target_year` for personal planning. A GPX recorded by someone else does not establish an outing by Eric.

Illustrative `goal.json` defaults (no real route or trip claims):

```json
{
  "schema_version": 1,
  "status": "idea",
  "priority": "normal",
  "archived": false,
  "tags": [],
  "why": "",
  "added_at": null,
  "target_months": [],
  "target_year": null,
  "time_commitment": null,
  "season_notes": "",
  "difficulty": null,
  "route_scope": "unknown",
  "route_source": {
    "kind": "unknown",
    "url": null,
    "label": null,
    "checked_at": null,
    "public_copy_approved": false
  },
  "references": [],
  "field_evidence": {},
  "checklist": [],
  "outings": []
}
```

`goal.json` must not duplicate title, activity, region, GPX stats, or the main planning body. JSON uses the standard library and avoids pretending the existing limited front-matter parser supports arbitrary nested YAML. Normalize it into `t['goal']` using a dedicated helper. A sidecar on a non-planned report is an error, not a way to quietly put completed reports into the future list.

Allowed priority values: `high`, `normal`, `someday`. `target_months` contains unique integers 1-12. `time_commitment` is null or one of `half-day`, `full-day`, `overnight`, `multi-day`. `route_scope` is `full-intended-route`, `approach-only`, `ascent-only`, `partial`, or `unknown`. These are explicit author/source statements, not confident geometric inferences.

`route_source.kind` is `author-drawn`, `planner-export`, `third-party-recording`, `own-prior-recording`, or `unknown`. A sketch/AI-assisted trace must additionally carry a visible approximation note; a GPX `<trk>` element does not prove that the planned route was physically traveled. `public_copy_approved` controls whether a NEW source may be copied into the public repository at import, not an ineffective UI hiding switch after the fact.

Each reference has `id`, `label`, `url`, `checked_at`, and optional `note`. Each researched `field_evidence` entry identifies its field, `source_ids`, and review state; published factual enrichment requires author review. `difficulty`, when present, contains `system`, `value`, and an optional contextual note, with a reference through `field_evidence`. A checklist entry has a stable `id`, `text`, and `done` boolean. Display checklists as read-only on the public site.

Introduce `site['goals']` for all non-draft goal records and an `active_goals` helper for non-archived, non-completed ones. Do not casually change the meaning of `site['planned']`, since existing builders depend on it to emit goal pages. Audit each consumer: page/asset generation still needs every non-draft goal; future-route counters and map filters should use the appropriate active subset. Report lists, homepage featured trips, RSS, completed mileage, and verified summit counts must never start counting all goals as trips.

Legacy planned routes with no sidecar should continue rendering with safe default goal metadata. List them in a migration report for Eric to review; do not invent priority, preferred months, or completion. Preserve their titles, URLs, and GPX bytes. New import/privacy defaults must not silently remove previously published downloads.

### 20.6 Import workflow and derived data

Add a **new** local `tools/ticklist.py` CLI with `add`, `update`, `log-outing`, `review-packet`, and `export` subcommands. Reuse helpers when their behavior fits; do not call `add_trip.py` unchanged for goals. The current trip importer simplifies/re-writes geometry, derives dates from recordings, and has no planned-goal mode. Those defaults are not the goal import contract. [R13, R14]

Proposed commands below become runnable only AFTER Phase 2T implements and documents them:

```bash
# Preview without changing the repository. GPX is optional.
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity hike \
  --gpx /absolute/path/route.gpx --dry-run

# Import reviewed, public-appropriate geometry as a draft goal.
python3 tools/ticklist.py add --title "YOUR ROUTE NAME" --activity hike \
  --gpx /absolute/path/route.gpx --publish-track --no-render

# Change intent without changing report content.
python3 tools/ticklist.py update YOUR_GOAL_SLUG --status shortlisted --priority high

# Explicitly confirm an outcome and optionally connect an existing report.
python3 tools/ticklist.py log-outing YOUR_GOAL_SLUG --outcome completed \
  --report-slug YOUR_EXISTING_REPORT_SLUG

# Export a review packet outside the public checkout.
python3 tools/ticklist.py review-packet YOUR_GOAL_SLUG \
  --out /absolute/path/outside-repo/goal-review.md
```

`--publish-track` approves copying this new GPX to the public checkout; it does NOT commit, push, deploy, approve other fields, or certify route safety. Without it, inspect the supplied source and create a metadata-only goal if desired, but do not copy the raw source or publish derived location assets from that unapproved GPX. Do not persist private local file paths in public metadata. No automatic Git actions.

Importer acceptance contract:

- Support ordinary GPX routes (`rte/rtept`) and tracks (`trk/trkseg/trkpt`), preserving independent segments and named waypoints. Accept no-elevation/no-time inputs. Do not infer a usable route from unordered waypoint-only data; save the idea and explain the limitation. Multi-route or alternative-route files require explicit selection, never a silent concatenation. [W9]
- Keep an approved source file byte-for-byte. Store its checksum and parser/method version in derived metadata. Compute measurements on the selected full-resolution geometry; simplify only display derivatives, within each segment. Do not stitch a gap into a fictional traversable line or include a transfer between unrelated tracks in route length. For an ambiguous selection, stop only the geometry operation with an actionable choice.
- Treat sparse route measurements as approximate polyline lengths, not routed trail distances. Missing or incomplete elevation must produce unknown/partial coverage, not zero gain or a deceptively complete elevation profile. Do not borrow the original recorder's moving time as Eric's expected duration. Do not silently query an elevation service or fabricate missing points.
- Reuse existing terrain rendering locally where compatible, and adapt the goal rendering path to respect segments/unknown elevation. If map generation cannot run, allow a valid metadata-only goal with a clear map-unavailable fallback. Do not break the static production build or require network map rendering in GitHub Actions.
- Validate file size, point counts, XML structure, supported encodings, finite coordinate ranges, paths, slugs, JSON types, and source references. Use bounded parsing; disallow DTD/entity declarations. Escape imported names/notes in HTML, and accept only safe external-link protocols. Never fetch a URL embedded in an imported file merely because it is present.
- Use safe file operations with no shell interpolation, path traversal, or overwrite-by-default. Duplicate slug or checksum produces a clear warning and a choice to reference/rename, not `--force` data loss. A same-name route in a different region may be legitimate; do not auto-merge it.
- New entries default to `draft: true`. A dry-run must write nothing. Import reports should separate created files, unchanged sources, approximate computed values, missing data, and optional research suggestions. Document the review and explicit draft-to-public step.

Do not widen this feature into a rewrite of every existing track helper. The current helpers expose a flat point sequence and write a single segment; the goal ingestion/rendering adapter must not silently inherit segment-loss behavior. Existing completed-report geometry and statistics stay unchanged unless separately authorized. [R14]

### 20.7 What ChatGPT/Claude should add

Separate three kinds of work:

| Work | Automatic or review-gated? | Required behavior |
| --- | --- | --- |
| Read GPX, calculate approximate geometry stats, create map/profile assets | Deterministic code | Identify file/method, preserve gaps, expose missing data. |
| Normalize provided names, propose region/tags, draft a short third-person route summary | Review-gated | Use supplied/source-backed facts; do not invent Eric's motivation or experience. |
| Research route descriptions, published grades, access/permits, seasonal considerations | Review-gated | Record claim-level sources and checked date; prefer the relevant managing authority for access/permits and credible original route documentation for technical details. |
| Assemble questions Eric still needs to answer | Draft suggestions | Examples: is the file the entire route, does it include the descent, is a shuttle required, what does the current official access page say? |
| Find related existing personal reports | Suggestions only | Explicit geography/route relationships; similarity never proves equal difficulty or completion. |
| Set priority, confirm feasibility, certify safety, tick completion | Author-only decisions | Never auto-write these based on AI judgment. |

The enrichment workflow is **inspect -> research when requested -> propose a field-by-field patch -> Eric reviews -> apply approved edits**. GPX derivation does not require an AI API. The static site should not call an LLM or hold provider credentials. A ChatGPT/Claude session can create the structured proposal or edits through the normal local Git workflow.

`review-packet` should export a compact Markdown/JSON-friendly packet with the goal's public data, source summary, known geometry limitations, missing fields, and source references. Keep unreviewed research and private notes outside the public checkout. Unavailable or conflicting sources remain unresolved with an explanation; do not fill every blank just to make a polished card.

No invented technical grades, exposure ratings, avalanche conclusions, water availability, road-open status, legal access, expected completion time, or precise route-finding directions from a GPX alone. "Typical season" is not a current-condition report. Check dates describe when a source was read, not when it was guaranteed true.

For each factual proposal, provide `field`, `proposed_value`, `source_ids`, `checked_at`, and a short qualification. Pure suggestions such as a tag must be labeled suggestions. Preserve an existing author-approved value unless Eric specifically accepts its replacement. Do not copy entire third-party trip reports or unlicensed photographs/GPX files.

### 20.8 Uploading, editing, and privacy

**First-release recommendation: public read-only tick list, local authoring through Claude Code and the importer.** Eric supplies a file path/GPX plus name and category; the helper produces the entry; Eric reviews and publishes through the existing Git process. This is a file-backed workflow, not a hosted admin application.

GitHub Pages serves static files. A form can read a selected file in a browser, but that alone does not persist changes to the repository or publish a new page. Persistent live-site uploads require an authenticated external write mechanism. Do not imply that a static file picker provides publishing, and never put a GitHub write token or model API key in shipped JavaScript. [W8, W10]

An optional **local upload desk** is a separate Phase 2T enhancement: a local-only browser form with GPX drag/drop, route title, activity, inline validation, preview, and author status/research editing. It must call the same importer/validator rather than create a second source of truth. Bind to loopback only; validate Host/Origin, use a per-session write token, restrict file access to intended goal data, bound uploads, and exclude the management assets/endpoints from deployed output. Do not replace public authentication with a hidden URL or a client-side password. Build this only after the importer works, and document that it runs on Eric's computer, not the public domain.

Direct phone editing from the live site requires a later authenticated Git-backed CMS or separate administration service. That is a distinct infrastructure decision, not a dependency of Phase 2T.

Everything committed to this public repository must be treated as public, including sidecars, drafts, GPX metadata, and source notes. Do not create a misleading `private: true` field and leave the underlying material in the repository. Keep private dates, contact details, reservations, home coordinates, and unlicensed sources outside the checkout. `robots.txt`, hidden pages, and `noindex` are not access controls. Existing published data is not made private by a new UI filter.

### 20.9 Goal detail page and small useful enhancements

At the existing `trips/<goal-slug>/` URL, render a goal-specific variant: title, goal status/priority, location/activity, approximate route stats, map/profile when available, brief motivation, approved planning notes, source links, unresolved research questions, and attempts/completion links.

Use **Planning notes**, not **Trip report**, for the goal body. Use **Planned route**, not **Eric's recording**, for its map context. Provide a download only for the approved file actually present, with its origin/scope and approximation note. Completed goals say "Completed" and point to the real outing, while keeping the original planned route clearly identified.

Phase 2T conveniences: stable copy-link action; named source links; preserved MI/KM display; read-only preparation checklist; JSON export of approved tick-list data. Exports must include the agreed public fields only, not absolute local paths or raw draft AI packets. CSV can be an optional later export, not a required second database.

After core browsing works, add author-selected goal collections or a three-goal comparison. An optional small homepage "On my list" shelf may show at most three explicitly selected active goals, using a separate `tick_list_slugs` key in `content/home.json`. Do not enable it by default, mix it into `featured_slugs`, or let it displace the required PCT/Matterhorn/Peak Bagging features. No performance dashboard, popularity ranking, or season-based "safe today" recommendation.

### 20.10 Implementation and acceptance

Extend `tools/lib/content.py`, `tools/build.py`, the existing planned report variant, and shared cards/links/units. Add `tools/lib/goals.py`, `tools/ticklist.py`, `tools/sitegen/pages/ticklist.py`, corresponding CSS/JS, focused tests, and `docs/TICK_LIST_GUIDE.md`. Add a source-backed enrichment prompt to that guide. Resolve actual rendering/parser modules from the checkout; proposed filenames are not claims that the modules exist now.

Required tests include: metadata-only idea; route-only GPX; multi-segment track; multiple alternatives requiring selection; no elevation; partial elevation; no timestamps; waypoint-only file; sparse geometry; duplicate import; rejected XML/path inputs; failed map render; legacy planned route without sidecar; valid/invalid status and reference fields; attempts before completion; completion without a report/date; completed/archived goal counts; safe source-preserving import; draft exclusion; exact existing GPX checksums; read-only public UI; and unchanged homepage/report/RSS totals.

Verify all relevant page/asset/index paths under `/personal-website/`, static no-JavaScript goal browsing, keyboard controls, 320/390/768/1024/1440px layouts, long names, missing map fallbacks, filter-state restoration, export contents, and an actual round-trip author workflow. Use synthetic fixtures in tests only. Do not add imaginary live goals to make screenshots look populated.

**Done means:** Eric can save a real GPX or a name-only idea, review the goal, find it by category/region/status, shortlist it, record an explicit attempt or completion, and follow a link to the associated actual report without overwriting either route. The full build/check and targeted tests pass, or blocked checks are reported honestly. The public site has no fake upload/status persistence and no private write credentials. No push or deployment occurs without separate authorization.


## Evidence register

### Repository sources

Repository base: `https://github.com/esichak/personal-website`

The following paths were read during the audit. Source references identify inspected functions or content rather than claiming current deployed behavior was visually tested.

| ID | Source path | Relevant evidence |
| --- | --- | --- |
| R1 | `README.md` | Build/authoring workflow, featured flag, photo handling, GPX privacy. |
| R2 | `docs/DEVELOPING.md` | Datum design, architecture, accessibility conventions, content and URL rules. |
| R3 | `tools/sitegen/pages/home.py` | Single featured selection, first-photo fallback, ten latest rows, map/archive links. |
| R4 | `assets/css/pages/home.css` | Featured photograph and action visibility breakpoints; desktop layout. |
| R5 | `tools/lib/content.py` | Normalized metadata, custom front matter, series/day model, date ordering. |
| R6 | `tools/sitegen/core.py` and `tools/build.py` | Shared formatting, summary provenance, metadata, lightbox, bundles, copying, RSS and checks. |
| R7 | `tools/sitegen/pages/report.py` | Report sequence, conditional content, GPX actions, mobile sections, gallery, map helper. |
| R8 | `tools/sitegen/pages/series.py` | Recorded-day log, month groups, written-entry presentation, anchor helper. |
| R9 | `assets/js/pages/archive.js` | Activity filters, region tabs, existing fragment handling. |
| R10 | `content/trips/pacific-crest-trail-2024/index.md` | Existing series identity and empty parent narrative/photo list. |
| R11 | `content/trips/matterhorn-peak-west-couloir/index.md` | Existing ski report, photos, beta, and narrative qualifications. |
| R12 | `content/trips/peak-bagging-szn/index.md` | Existing single-day loop, four photos, explicit eight-peak narrative. |
| R13 | `tools/add_trip.py` (follow-up read October 8, 2026) | Existing importer has no goal flag; derives recording dates and simplifies/rewrites tracks. Blob `7552362111b2e5da048f87b98ade1cab900af6da`. |
| R14 | `tools/lib/tracks.py` (follow-up read October 8, 2026) | Flat-point helper interface, GPX writer, approximate statistics, and route-shape heuristics. Blob `455f843f8a84b3d066e5bd278df1e1e4d958a4ee`. |

The Tick list follow-up also re-read `tools/lib/content.py` (blob `c778de85d55da82515b69315ff06a015cd467f26`) and the first 150 lines of `tools/build.py` (blob `59638f4500d107317a405bca4ed07f3a5037997c`), confirming the planned-route loader/build/feed separation. No local website build or live UI test was performed during this plan revision.

For the initial audit sources R1-R12, a reproducible historical source URL uses the path above after this prefix:

```text
https://github.com/esichak/personal-website/blob/a9baab989f9afd74f8142b127ec8f04d8995bad4/
```

### External primary sources

W1. Stav is Lost homepage: `https://stavislost.com/`

W2. Representative report structure: `https://stavislost.com/hikes/trail/old-man-mountain-and-black-buttes-loop/`

W3. Map organization: `https://stavislost.com/map/`

W4. Search organization: `https://stavislost.com/search/`

W5. W3C image accessibility tutorial: `https://www.w3.org/WAI/tutorials/images/`

W6. Google web.dev Web Vitals definitions and measurement guidance: `https://web.dev/articles/vitals`

W7. Google Search Central Article/BlogPosting structured-data guidance: `https://developers.google.com/search/docs/appearance/structured-data/article`

W8. GitHub Pages static hosting model: `https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages`

W9. Topografix GPX 1.1 schema (route/track/segment distinctions and optional elevation/time): `https://www.topografix.com/GPX/1/1/index.htm`

W10. GitHub credential security: `https://docs.github.com/en/rest/authentication/keeping-your-api-credentials-secure`

All design prescriptions, sequencing choices, implementation budgets, and proposed metadata contracts in this plan are recommendations. They are not claims that the changes already exist or have been measured on the live website.
