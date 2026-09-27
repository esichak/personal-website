"""Inline stroke icons, 24px viewBox, 1.5 stroke, square caps, miter joins, currentColor."""

PATHS = {
    # activities
    'SKI': '<path d="M3 20.5h18"/><path d="M4 16.5L15.5 5a2.5 2.5 0 0 1 3.5 0"/><path d="M8 18.5L19.5 7a2.5 2.5 0 0 1 1.5 2.2"/><path d="M8.5 11.5l2 2"/><path d="M12.5 13l2 2"/>',
    'CLM': '<path d="M8.5 8.5V16a4 4 0 0 0 4 4h.5a5 5 0 0 0 5-5V9a5 5 0 0 0-5-5h-1a3.5 3.5 0 0 0-3.5 3.5"/><path d="M8.5 11.5l3-2"/>',
    'HIK': '<path d="M12 3v18"/><path d="M12 5h6l2 2-2 2h-6"/><path d="M12 11H6l-2 2 2 2h6"/><path d="M9 21h6"/>',
    'MTB': '<circle cx="6" cy="16" r="4"/><circle cx="18" cy="16" r="4"/><path d="M6 16l4-7h6l2 7"/><path d="M10 9l3 7h-7"/><path d="M14.5 6.5H17"/><path d="M1.5 16h1M21.5 16h1M6 11.5v-1M18 11.5v-1"/>',
    'OTH': '<circle cx="12" cy="12" r="9"/><path d="M12 5.5l2.5 6.5L12 18.5 9.5 12z"/><path d="M12 5.5l2.5 6.5h-5z" fill="currentColor"/>',
    'SUP': '<rect x="2.5" y="16" width="19" height="3.5" rx="1.75"/><path d="M15 3v11"/><path d="M13.5 3h3"/><path d="M13.8 14h2.4l-.6 3h-1.2z"/>',
    'RFT': '<rect x="3" y="10" width="18" height="7" rx="3.5"/><rect x="5.5" y="12" width="13" height="3" rx="1.5"/><path d="M2 21c2.5-1.6 4.5-1.6 7 0s4.5 1.6 7 0 3.5-1.2 6-.3"/>',
    'KYK': '<path d="M2 14c5-3.5 15-3.5 20 0-5 3.5-15 3.5-20 0z"/><path d="M5 4.5l14 17"/><path d="M3.8 3l2.4 3M17.8 20l2.4 3"/>',
    'MTN': '<path d="M12 6v15"/><path d="M5 6h12.5v3.5H20"/><path d="M5 6c-1.2.5-2 1.6-2 3"/><path d="M12 21l-1-2.2h2z"/>',
    # ui
    'download': '<path d="M12 3v12"/><path d="M7 10.5l5 5 5-5"/><path d="M4 17v3h16v-3"/>',
    'expand': '<path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/>',
    'arrow-right': '<path d="M4 12h15"/><path d="M13.5 6.5L19 12l-5.5 5.5"/>',
    'arrow-left': '<path d="M20 12H5"/><path d="M10.5 6.5L5 12l5.5 5.5"/>',
    'chevron-down': '<path d="M6 9.5l6 6 6-6"/>',
    'chevron-right': '<path d="M9.5 6l6 6-6 6"/>',
    'menu': '<path d="M3.5 6.5h17M3.5 12h17M3.5 17.5h17"/>',
    'close': '<path d="M5.5 5.5l13 13M18.5 5.5l-13 13"/>',
    'caution': '<path d="M12 3.5L21.5 20h-19z"/><path d="M12 9.5v5"/><path d="M12 16.5v1.5"/>',
    'checkbox': '<rect x="4" y="4" width="16" height="16"/>',
    'list': '<path d="M8.5 6.5h12M8.5 12h12M8.5 17.5h12M3.5 6.5h1.5M3.5 12h1.5M3.5 17.5h1.5"/>',
    'map': '<path d="M3 6l6-2.5 6 2.5 6-2.5v14.5l-6 2.5-6-2.5-6 2.5z"/><path d="M9 3.5V18M15 6v14.5"/>',
    'info': '<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><path d="M12 7.5V9"/>',
    'report': '<path d="M5 3.5h10l4 4v13H5z"/><path d="M8.5 11h7M8.5 14.5h7M8.5 18h4.5"/>',
    'beta': '<path d="M4 6.5h16M4 12h16M4 17.5h10"/><circle cx="18" cy="17.5" r="1"/>',
    'photo': '<rect x="3" y="5" width="18" height="14"/><path d="M3 16l5-5 4 4 3-3 6 6"/><circle cx="16" cy="9" r="1.5"/>',
    'search': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5l5 5"/>',
    'rss': '<path d="M5 4.5a14.5 14.5 0 0 1 14.5 14.5"/><path d="M5 10.5a8.5 8.5 0 0 1 8.5 8.5"/><circle cx="6" cy="18" r="1.2"/>',
    'north': '<path d="M12 3l5 18-5-4-5 4z"/>',
}


def icon(name, size=24, color='currentColor', stroke=1.5, extra_style=''):
    return ('<svg width="%d" height="%d" viewBox="0 0 24 24" aria-hidden="true" '
            'style="flex-shrink: 0; fill: none; stroke: %s; stroke-width: %s; stroke-linecap: square; '
            'stroke-linejoin: miter; color: %s%s">%s</svg>') % (size, size, color, stroke, color,
                                                                  ('; ' + extra_style) if extra_style else '',
                                                                  PATHS[name])


def icon_inner(name):
    return PATHS[name]
