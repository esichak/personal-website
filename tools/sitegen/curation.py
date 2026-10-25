"""Homepage curation: content/home.json names the featured trips, in order.

    {"featured_slugs": ["pacific-crest-trail-2024", "matterhorn-peak-west-couloir", "peak-bagging-szn"]}

An optional "region_maps": ["Lake Tahoe", "Santa Cruz"] picks the one or two region maps "Where I've been" draws
(resolve_region_maps); without it the page draws sitegen.pages.home.HOME_REGIONS.

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


MAX_REGION_MAPS = 2


def resolve_region_maps(manifest, meta):
    """The optional "region_maps": the one or two regions whose maps the home page's "Where I've been" draws, in order.
    None when the file or the key is absent (sitegen.pages.home.HOME_REGIONS stands, so nothing changes until Eric
    writes one). Each name must have a region map in rendered/site/meta.json (meta: its contents), the test
    home.where makes before it draws one; anything else stops the build, naming the file and the value."""
    if not manifest or 'region_maps' not in manifest:
        return None
    names = manifest['region_maps']
    if not isinstance(names, list) or not 1 <= len(names) <= MAX_REGION_MAPS:
        raise _err('"region_maps" must be a list of one or two region names, such as ["Lake Tahoe", "Santa Cruz"], got %r'
                   % (names,))
    maps = (meta or {}).get('maps') or {}
    out = []
    for i, name in enumerate(names):
        if not isinstance(name, str) or not name.strip():
            raise _err('region_maps[%d] must be a region name, got %r' % (i, name))
        if name in out:
            raise _err("duplicate region '%s' in region_maps" % name)
        s = content.slugify(name)
        if ('region-%s-desktop' % s) not in maps and ('region-%s-phone' % s) not in maps:
            raise _err("region_maps: '%s' has no region map in rendered/site/meta.json (the name as the trips spell it; a "
                       "region gets a map once it has three trips with a track and python3 tools/render.py --site has run)"
                       % name)
        # the map's slug is not enough: the heading, its region page link and the ALSO line all go by the exact name
        spelt = [r for r in (meta or {}).get('regions') or [] if content.slugify(r) == s]
        if spelt and name not in spelt:
            raise _err("region_maps: '%s' is written '%s' on the trips; use that spelling" % (name, spelt[0]))
        out.append(name)
    return out


def region_maps_for(meta, path=HOME_JSON):
    return resolve_region_maps(load_manifest(path), meta)
