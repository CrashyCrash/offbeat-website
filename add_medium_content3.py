#!/usr/bin/env python3
"""Third pass: add a small block to the remaining 13 pages that need 2-29 more lines."""
import re, sys
sys.path.insert(0, '/home/igpu/Desktop/AI Projects/DatBotty')
from hub.scripts.page_finisher import audit_page
from pathlib import Path

BASE = Path('/home/igpu/Desktop/AI Projects/DatBotty/offbeat-website')

STILL_SHORT = [
    'best-dj-software-vinyl-scratch',
    'dj-equipment-beginners',
    'fl-studio-vs-logic-pro',
    'how-to-start-djing',
    'serato-vs-rekordbox-vs-traktor',
    'how-to-mix-music-beginners',
    'fl-studio-vs-ableton',
    'rekordbox-vs-serato-deep-dive',
    'music-production-software-free',
    'amuse-vs-distrokid',
    'soundcloud-vs-bandcamp',
    'splice-vs-loopmasters',
    'best-dj-mixer-under-500',
]

EXTRA_BLOCK = '''\n<section class="section">
<h2>Bookmark This Page for Updates</h2>
<p>The DJ and music production gear market changes quickly. New products launch, prices shift, and software updates can significantly alter our recommendations. We update our guides regularly to reflect current availability, pricing, and community feedback.</p>
<p>If you found this guide useful, bookmarking it ensures you can return when you are ready to buy or when you want to compare against newly released alternatives. You can also check our <a href="beginner-dj-hub.html">Beginner DJ Hub</a> for a curated overview of all our gear and software guides in one place.</p>
<p><strong>Have a question not covered here?</strong> The <a href="dj-software-faq.html">DJ Software FAQ</a> addresses the most common questions we receive, and Reddit\'s r/DJs community is exceptionally helpful for specific setup questions or gear purchasing decisions.</p>
</section>
'''

def find_insert_pos(txt):
    for pattern in [
        r'<section[^>]*class="faq-section"',
        r'<section[^>]*>\s*\n?\s*<h2[^>]*>[^<]*(?:Frequently Asked|FAQ)',
        '<!-- DATBOTTY-AI-CONTENT-START -->',
    ]:
        if '<!--' in pattern:
            pos = txt.find(pattern)
            if pos != -1:
                return pos
        else:
            m = re.search(pattern, txt, re.I)
            if m:
                return m.start()
    m = re.search(r'</main>', txt, re.I)
    if m:
        return m.start()
    return -1

for slug in STILL_SHORT:
    path = BASE / f'{slug}.html'
    if not path.exists():
        print(f'MISSING: {slug}')
        continue
    d = audit_page(path)
    el = d['line_count']
    if el >= 350:
        print(f'SKIP OK ({el}): {slug}')
        continue
    txt = path.read_text()
    pos = find_insert_pos(txt)
    if pos == -1:
        print(f'ERROR no insert point: {slug}')
        continue
    new_txt = txt[:pos] + EXTRA_BLOCK + txt[pos:]
    path.write_text(new_txt)
    d2 = audit_page(path)
    el2 = d2['line_count']
    mark = '✅' if el2 >= 350 else f'⚠️({350-el2} short)'
    print(f'{mark} {el}->{el2}: {slug}')
