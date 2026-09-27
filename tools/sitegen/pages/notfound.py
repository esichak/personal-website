"""404 page — /404.html. GitHub Pages serves it for any missing path at any depth, so the page carries
<base href="/personal-website/"> (the path of core.SITE_URL) and every link is built as if from the site root.
"""
from urllib.parse import urlparse

from sitegen import core
from sitegen.core import esc, link, icon
from sitegen.pages.about import act_rows

URL = '404.html'
HERE = ''  # links are resolved against <base>, i.e. the site root


def base_tag():
    """<base href='/personal-website/'>. Single-quoted on purpose: build.py --check scans href="…" as a file path and
    would report this site-absolute URL as broken (and fail the deploy)."""
    path = urlparse(core.SITE_URL).path or '/'
    return "<base href='%s'>" % esc(path if path.endswith('/') else path + '/')


def page(site):
    here = HERE
    body = ('<div class="nf wrap"><div class="nf-grid">'
            '<div class="nf-intro">'
            '<p class="t-mono-s nf-code">404 · PAGE NOT FOUND</p>'
            '<h1 class="t-d1 nf-h">Off route</h1>'
            '<p class="nf-line">There is no page at this address. The link may be old or mistyped.</p>'
            '<a class="btn btn--ink nf-home" href="%s">Go to the home page%s</a>'
            '</div>'
            '<nav class="nf-nav" aria-label="Ways back"><h2 class="t-label nf-l">Reports</h2>%s'
            '<h2 class="t-label nf-l nf-l2">Site</h2><ul class="abo-act"><li><a class="abo-act-a" href="%s"><span class="nf-ic" aria-hidden="true">%s</span>'
            '<span class="abo-act-w"><span class="abo-act-n">Map &amp; archive</span>'
            '<span class="t-mono-s abo-act-m">ALL %d REPORTS</span></span>%s</a></li></ul></nav>'
            '</div></div>'
            % (link(here, ''), icon('arrow-right', 18), act_rows(site, here, dist=False),
               link(here, 'map/'), icon('map', 20), len(site['published']), icon('chevron-right', 20, 'abo-act-c')))
    extra = base_tag() + '<meta name="robots" content="noindex">'
    html_ = core.document(here, 'Page not found', body, 'This page is not on the map.', body_cls='p-404', extra_head=extra)
    # <base> only applies to URLs that come after it, and core.document places extra_head after the stylesheet links,
    # so move it to the top of <head>. (Requested in core: emit extra_head / a base tag before any URL.)
    html_ = html_.replace(extra, '', 1).replace('<meta charset="utf-8">', '<meta charset="utf-8">' + extra, 1)
    # document() derives canonical / og:url from `here` (''), which would name the home page; a 404 has neither.
    home = core.SITE_URL
    html_ = (html_.replace('<link rel="canonical" href="%s">' % home, '', 1)
             .replace('<meta property="og:url" content="%s">' % home, '', 1))
    # Fragment-only links resolve against <base> too (the skip link would load the home page): notfound.js keeps them in-page.
    return core.Page(URL, html_, 'Page not found')


def build(site):
    return [page(site)]
