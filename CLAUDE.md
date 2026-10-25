# CLAUDE.md

Guidance for Claude Code in this repository: a static trip-report site, Python 3 standard library only, published to
GitHub Pages from `main`. Read first: [README.md](README.md), [ADDING-TRIPS.md](ADDING-TRIPS.md) (the author's
workflow), [docs/DEVELOPING.md](docs/DEVELOPING.md) (design system, hard rules, how the generator works) and
[docs/CONTENT_GUIDE.md](docs/CONTENT_GUIDE.md) (content fields, every message the checks print).

## Checks

```bash
python3 tools/validate.py                                    # content checks, no build
python3 -m unittest discover -s tests                        # unit tests (one module: -p test_report_page.py)
python3 tools/build.py --out <scratch folder> --link --check # build and check the built site, in a few seconds
python3 tools/check.py                                       # all three, the suite on both Pythons, before a push of code
```

Run the suite on both Pythons with `-W error` before a change to `tools/`, `tests/` or `assets/` goes in: the Mac's
`/usr/bin/python3` is 3.9, CI runs 3.12. Keep the tools 3.9-compatible. `python3 tools/doctor.py` is a read-only look
at the checkout and the Mac.

## Publishing

- A push to `main` publishes the site (about a minute for content, three when code changed). Push only when the
  author says so.
- Publish trips with `python3 tools/publish.py <slug> [--push]`; otherwise stage by explicit path. Never `git add -A`
  or `git add .`, and read `git status --short` before a commit (iCloud conflict copies: `tools/tidy.py` lists them).
- `tools/render.py` draws the maps on the author's Mac and needs the internet; `rendered/` is committed. Never render
  in CI, and run it only when the author agrees.
- Never force-push or rewrite pushed history; a bad push is undone with `git revert` (ADDING-TRIPS.md, "When something
  goes wrong").

## Rules that are easy to break

- Facts only from the content files; write-ups verbatim; every distance and height through `core.U`; relative links
  through `core.link` (docs/DEVELOPING.md, "Rules").
- The repository is public: nothing in code, tests or docs may name a home location, start coordinates or anything
  else `docs/PRIVACY_NOTES.md` keeps out. Test fixtures are synthetic.
