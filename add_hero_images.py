#!/usr/bin/env python3
"""Add hero images to pages scoring below max due to no_hero_image."""
import re, sys
sys.path.insert(0, '/home/igpu/Desktop/AI Projects/DatBotty')
from hub.scripts.page_finisher import audit_page
from pathlib import Path

BASE = Path('/home/igpu/Desktop/AI Projects/DatBotty/offbeat-website')

PAGES = [
    ('affiliate-tools', 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?ixlib=rb-4.1.0&w=900&h=380&fit=crop&q=80', 'Affiliate marketing tools and programs guide for content creators'),
    ('best-dj-controllers-under-500-2026', 'https://images.unsplash.com/photo-1571266028243-d220c6a3d7c4?ixlib=rb-4.1.0&w=900&h=380&fit=crop&q=80', 'Best DJ controllers under $500 in 2026'),
    ('festival-dj-gear-checklist', 'https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?ixlib=rb-4.1.0&w=900&h=380&fit=crop&q=80', 'Festival DJ gear checklist and equipment guide'),
    ('music-distribution-affiliates', 'https://images.unsplash.com/photo-1511379938547-c1f69419868d?ixlib=rb-4.1.0&w=900&h=380&fit=crop&q=80', 'Music distribution affiliate programs review'),
]

def add_hero(path, img_url, alt_txt):
    txt = path.read_text()
    if 'page-hero-img' in txt:
        return 'already_has_hero'
    
    HERO = f'''<figure class="hero-figure">
<img class="page-hero-img" src="{img_url}"
     alt="{alt_txt}"
     width="900" height="380" loading="eager" decoding="async"
     style="width:100%;height:auto;border-radius:8px;display:block;margin-top:1.5rem;">
</figure>
'''
    # Find insertion point: after h1 + sub paragraph
    m = re.search(r'<h1[^>]*>.*?</h1>', txt, re.DOTALL)
    if not m:
        return 'no_h1'
    
    # Search for a short paragraph after h1
    rest = txt[m.end():]
    p_match = re.search(r'<p[^>]*>[^<]{20,}</p>', rest[:1500])
    if p_match:
        insert_at = m.end() + p_match.end()
    else:
        insert_at = m.end()
    
    new_txt = txt[:insert_at] + '\n' + HERO + txt[insert_at:]
    path.write_text(new_txt)
    return 'added'

for slug, img_url, alt in PAGES:
    path = BASE / f'{slug}.html'
    if not path.exists():
        print(f'MISSING: {slug}')
        continue
    d_before = audit_page(path)
    result = add_hero(path, img_url, alt)
    if result == 'added':
        d_after = audit_page(path)
        print(f'{slug}: {d_before["completion_score"]:.2f} -> {d_after["completion_score"]:.2f} ({result})')
    else:
        print(f'{slug}: {result}')
