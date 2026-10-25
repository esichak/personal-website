"""How a reader reaches Eric: content/author.json, optional and strict (gap5-01, gap5-03).

    {"email": "<a public alias>", "links": [{"label": "Strava", "url": "https://www.strava.com/athletes/..."}]}

email: one address Eric is willing to keep public, written out and linked (mailto:) on About under 'Follow & contact',
in the footer, and as 'Ask about this trip' on every report. links: the profiles he names himself, on About only, each
rel="me". Both are optional, and with no file the site shows neither and builds as it did. A file that exists is
strict, like content/home.json (curation.load_manifest): an unknown key, a value that is not a string, a key or label
written twice, an address that is not one, a link that is not https or more than MAX_LINKS links stop the build with an
AuthorError naming the file. An address published here stays in the repository's history for good
(docs/PRIVACY_NOTES.md).
"""
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
AUTHOR_JSON = os.path.join(ROOT, 'content', 'author.json')
FILE = 'content/author.json'
KEYS = ('email', 'links')
LINK_KEYS = ('label', 'url')
MAX_LINKS = 6
# letters, digits and . _ + - before the @, a host name after it: nothing a mailto: address would read as its own (? # &)
_EMAIL = re.compile(r'^[A-Za-z0-9._+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$')


class AuthorError(ValueError):
    """content/author.json cannot be applied; the message names the file."""


def _err(msg):
    return AuthorError('%s: %s' % (FILE, msg))


def _once(pairs):
    """json.load's object hook: a key written twice in one object is refused (json would keep the last silently)."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise _err('"%s" is written twice; keep one' % k)
        out[k] = v
    return out


def _text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise _err('%s must be a non-empty string, got %s' % (where, json.dumps(value)))
    return value.strip()


def load(path=AUTHOR_JSON):
    """{'email': the address or None, 'links': [{'label', 'url'}, ...]}, or None when the file does not exist."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh, object_pairs_hook=_once)
    except AuthorError:
        raise
    except ValueError as ex:
        raise _err('not valid JSON (%s)' % ex)
    if not isinstance(data, dict):
        raise _err('the top-level value must be a JSON object such as {"email": "..."}')
    unknown = sorted(set(data) - set(KEYS))
    if unknown:
        raise _err('unknown key%s %s (known: %s)' % ('s' if len(unknown) > 1 else '', ', '.join('"%s"' % k for k in unknown),
                                                     ', '.join(KEYS)))
    email = None
    if 'email' in data:
        email = _text(data['email'], 'email')
        if not _EMAIL.match(email):
            raise _err('email "%s" is not an address such as name@example.com' % email)
    links = data.get('links', [])
    if not isinstance(links, list):
        raise _err('links must be a list of {"label": ..., "url": ...}')
    if len(links) > MAX_LINKS:
        raise _err('links has %d entries (at most %d)' % (len(links), MAX_LINKS))
    out = []
    for i, x in enumerate(links):
        where = 'links[%d]' % i
        if not isinstance(x, dict):
            raise _err('%s must be an object such as {"label": "Strava", "url": "https://..."}' % where)
        unknown = sorted(set(x) - set(LINK_KEYS))
        if unknown or set(LINK_KEYS) - set(x):
            raise _err('%s must have exactly the keys "label" and "url"' % where)
        label, url = _text(x['label'], where + '.label'), _text(x['url'], where + '.url')
        if not url.startswith('https://') or len(url) <= len('https://') or re.search(r'\s', url):
            raise _err('%s.url must be an https:// address, got "%s"' % (where, url))
        if label.casefold() in [y['label'].casefold() for y in out]:
            raise _err('the label "%s" is written twice; keep one' % label)
        out.append({'label': label, 'url': url})
    return {'email': email, 'links': out}
