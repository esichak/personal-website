# Checking the site with a screen reader

A twenty-minute pass with VoiceOver, on the Mac in Safari and on an iPhone, written for the review gate before each
publication. Every check of the site so far is static (tests/test_a11y_static.py reads the markup and the stylesheets)
or done in Chrome's emulation; this is the part only a person with the real tools can do. Do it on the published site
or on a local build served with `python3 tools/build.py --serve` (the address it prints).

Record what you heard in the table at the end, with the date, and copy the table into the log entry of the phase.

## Before you start

- **Mac:** System Settings > Accessibility > VoiceOver, or Command-F5. In Safari, turn on Safari > Settings >
  Advanced > "Press Tab to highlight each item on a webpage". VO means Control-Option. The rotor is VO-U; Left and Right
  Arrow change its list (headings, landmarks, links, form controls), Up and Down move in it, Return goes there.
- **iPhone:** Settings > Accessibility > VoiceOver. Swipe right and left to move, double-tap to activate, turn two
  fingers like a dial for the rotor, then swipe up and down to move by the chosen kind.

## On the Mac, in Safari (about 12 minutes)

1. **Home.** Open the rotor's headings list. Expect one heading level 1, then the sections at level 2 ("Featured
   trips", "Where I've been" and the rest), the region names at level 3. Open the landmarks list: banner, navigation
   "Main", main, contentinfo, and the footer's two lists. The first Tab stop is "Skip to content".
2. **Trips.** Tab into the search box; type a word. The count line is read out when the list changes ("12
   REPORTS"). Tab to an activity chip, press the arrow keys: each chip is read as a radio button, "checked" when chosen.
   Tab to Region and Year; they are pop-up buttons. Nothing should be read twice.
3. **A report** (the Matterhorn report). Headings: the title at level 1, then the sections at level 2 (Beta, Report,
   Elevation, Photos, More like this), the related reports at level 3. In the stats strip a distance should be read
   with its word, "12.8 miles", not "12.8 M I", and the line under it in the other system as "20.6 kilometers"; the
   Moving time as "hours and minutes". Activate a photo: the viewer opens and says which photo it is ("Photo 1 of 7" and its description); Escape closes it and the
   focus is back on the photo you opened. Tab to "Copy link": pressing it says "Link copied".
4. **The Haute Route.** The day bar's days are links; the one you are on is read as "current". Each day is one
   heading at level 3 under "Day by day", its number and then its title: "Day 3: Le Châble → Cabane de Prafleuri".
5. **The PCT page.** The month tabs: with "Show days with write-ups only" on (the default), an empty month says "no
   write-ups" after its name. The rows of a month are read as links with the day and its title.
6. **Map** (map/). The region tabs are a tab list ("tab, 1 of 8, selected"). Tab into a map: a pin is read as a link
   with its report's title. A numbered circle is read as a button, "3 reports start here, not pressed". Press it with
   Space: the list beside the map now holds those reports, and the count line says so. Press Escape: the list comes
   back. The live line reads "37 of 86 reports" when you press an activity in the legend.
7. **The units switch.** In the header (from 1000 px wide) or the menu: "MI: miles and feet, radio button, checked".
   Choose KM: "Showing kilometers and meters" is read out once.

## On the iPhone, in Safari (about 8 minutes)

1. **The menu.** Double-tap "Menu": the first thing read is the menu's first link ("Backcountry Skiing"). The Units
   buttons are above it: swipe left past the "By activity" label to reach KM, then MI. Swiping right goes through the menu only; the page behind is not reachable until
   the menu is closed. "Menu" again closes it.
2. **A report.** Swipe through the title and the stats: units are read as words. The bottom bar's links (Report, Map,
   Photos, GPX) jump to their sections.
3. **The photo viewer.** Double-tap a photo; swipe right inside the viewer to the Next button and double-tap: the next
   photo's number is read. A three-finger swipe should not move the page behind.
4. **A region page** (Lake Tahoe). Swipe to a numbered circle on the map: it is a button with its count; double-tap
   narrows the list, as on the Mac.

## What was heard

| Date | Device and browser | Page | Step | Heard | As expected? |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

Anything read twice, a control without a name, a step where the focus was lost, or a page that moved by itself goes in
the table with what you did just before it.
