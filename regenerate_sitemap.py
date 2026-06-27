#!/usr/bin/env python3
"""Regenerate sitemap.xml from current root-level public .html files."""

import os
import xml.etree.ElementTree as ET
from datetime import datetime

# Root directory
root_dir = os.path.dirname(os.path.abspath(__file__))

# Target files: root-level .html files (excluding private/dev)
public_files = []
for fname in os.listdir(root_dir):
    if fname.endswith('.html') and os.path.isfile(os.path.join(root_dir, fname)):
        # Skip known private/dev files
        if fname not in ['404.html', 'CNAME', '.nojekyll']:
            public_files.append(fname)

# Sort for stable output
public_files.sort()

# Build XML
urlset = ET.Element('urlset', {
    'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9',
    'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'xsi:schemaLocation': 'http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd'
})

now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+00:00')

for fname in public_files:
    url = ET.SubElement(urlset, 'url')
    loc = ET.SubElement(url, 'loc')
    loc.text = f'https://offbeatinc.com/{fname}'
    lastmod = ET.SubElement(url, 'lastmod')
    lastmod.text = now
    changefreq = ET.SubElement(url, 'changefreq')
    changefreq.text = 'weekly'
    priority = ET.SubElement(url, 'priority')
    priority.text = '0.8'

# Write
sitemap_path = os.path.join(root_dir, 'sitemap.xml')
ET.ElementTree(urlset).write(sitemap_path, encoding='utf-8', xml_declaration=True)

print(f"Regenerated sitemap.xml with {len(public_files)} URLs")
for f in public_files:
    print(f"  - https://offbeatinc.com/{f}")
