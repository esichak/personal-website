"""Homepage curation: content/home.json names the featured trips, in order.

    {"featured_slugs": ["pacific-crest-trail-2024", "matterhorn-peak-west-couloir", "peak-bagging-szn"]}

The list alone decides what the home page features and in what order (the first slug is the lead card); the old
`featured: true` front-matter flag keeps driving the section pages' Featured block and nothing else. A manifest that
exists is strict: duplicates, unknown slugs, drafts, planned routes, non-strings or more than MAX_FEATURED entries
stop the build with a CurationError that names the file and the slug, and an explicit empty list means no features
(never a substitute). Only a missing file falls back to the legacy pick, with a warning, so an old checkout still builds.
"""
import json
import os
import sys
import warnings

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import content  # noqa: E402
import frontmatter  # noqa: E402

HOME_JSON = os.path.join(ROOT, 'content', 'home.json')
MAX_FEATURED = 6
FILE = 'content/home.json'


class CurationError(ValueError):
    """content/home.json cannot be applied; the message names the file and, when there is one, the slug."""


def _err(msg):
    return CurationError('%s: %s' % (FILE, msg))


def _once(pairs):
    """json.load's object hook: a key written twice in one object is refused (json itself keeps the last and says
    nothing, so a list pasted under the old one would silently win or lose)."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise _err('"%s" is written twice; keep one' % k)
        out[k] = v
    return out


def load_manifest(path=HOME_JSON):
    """The parsed manifest, or None when the file does not exist."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh, object_pairs_hook=_once)
    except CurationError:
        raise
    except ValueError as ex:
        raise _err('not valid JSON (%s)' % ex)
    if not isinstance(data, dict):
        raise _err('the top-level value must be a JSON object such as {"featured_slugs": [...]}')
    return data


def _is_draft(trips_dir, slug):
    p = os.path.join(trips_dir, slug, 'index.md')
    if not os.path.exists(p):
        return False
    try:
        with open(p, encoding='utf-8') as fh:
            meta, _body = frontmatter.split(fh.read())
    except ValueError:
        return False
    return bool(meta.get('draft'))


def legacy_featured(site):
    """The pre-manifest pick: the newest published trip flagged featured, else the newest published trip."""
    pool = site.get('published') or []
    t = next((x for x in pool if x.get('featured')), None) or (pool[0] if pool else None)
    return [t] if t else []


def resolve_featured(site, manifest, trips_dir=content.TRIPS_DIR):
    """The featured trips, in manifest order. manifest None (no file) -> legacy pick plus a warning."""
    if manifest is None:
        warnings.warn('%s is missing: the home page falls back to the newest featured report. Create the file to choose '
                      'the featured trips (see docs/CONTENT_GUIDE.md).' % FILE, UserWarning, stacklevel=2)
        return legacy_featured(site)
    if 'featured_slugs' not in manifest:
        raise _err('missing "featured_slugs" (a list of trip slugs)')
    slugs = manifest['featured_slugs']
    if not isinstance(slugs, list):
        raise _err('"featured_slugs" must be a list of trip slugs, got %s' % type(slugs).__name__)
    if len(slugs) > MAX_FEATURED:
        raise _err('"featured_slugs" lists %d trips; at most %d can be featured' % (len(slugs), MAX_FEATURED))
    by_slug = site.get('by_slug') or {}
    out, seen = [], set()
    for i, slug in enumerate(slugs):
        if not isinstance(slug, str) or not slug.strip():
            raise _err('featured_slugs[%d] must be a trip slug (a non-empty string), got %r' % (i, slug))
        if slug in seen:
            raise _err("duplicate slug '%s' in featured_slugs" % slug)
        seen.add(slug)
        t = by_slug.get(slug)
        if t is None:
            if _is_draft(trips_dir, slug):
                raise _err("'%s' is a draft (draft: true in its index.md); drafts cannot be featured" % slug)
            raise _err("unknown slug '%s' in featured_slugs (no content/trips/%s/index.md)" % (slug, slug))
        if t.get('kind') == 'planned':
            raise _err("'%s' is a planned route; only published reports can be featured" % slug)
        out.append(t)
    return out


def featured_for(site, path=HOME_JSON):
    return resolve_featured(site, load_manifest(path))
