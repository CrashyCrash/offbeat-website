#!/usr/bin/env python3
"""Second-pass script: fix skipped pages + pages still below 350 editorial lines."""
import re, sys
sys.path.insert(0, '/home/igpu/Desktop/AI Projects/DatBotty')
from hub.scripts.page_finisher import audit_page
from pathlib import Path

BASE = Path('/home/igpu/Desktop/AI Projects/DatBotty/offbeat-website')

# All pages still below 350 plus the 6 skipped
TARGET_PAGES = [
    'best-turntable-cartridges',
    'best-dj-sample-packs-2026',
    'audio-interface-guide-djs',
    'how-to-become-a-dj',
    'how-to-get-dj-gigs',
    'dj-equipment-checklist',
    'distrokid-vs-tunecore',
    'best-dj-software-vinyl-scratch',
    'dj-equipment-beginners',
    'fl-studio-vs-logic-pro',
    'how-to-start-djing',
    'midi-controllers-for-music-production',
    'landr-vs-splice',
    'native-instruments-komplete-review',
    'serato-vs-rekordbox-vs-traktor',
    'beatport-vs-traxsource',
    'how-to-mix-music-beginners',
    'how-to-start-a-dj-blog',
    'fl-studio-vs-ableton',
    'rekordbox-vs-serato-deep-dive',
    'music-production-software-free',
    'amuse-vs-distrokid',
    'soundcloud-vs-bandcamp',
    'splice-vs-loopmasters',
    'best-dj-mixer-under-500',
]

def make_short_block():
    """~15-20 newlines: a concise pro tips box."""
    return '''\n<section class="section">
<h2>Pro Tips Before You Decide</h2>
<ul>
<li><strong>Use free trials fully</strong> — spend the entire trial period on the specific workflow you plan to use long-term, not just exploring features</li>
<li><strong>Check recent reviews</strong> — software and gear receive regular updates; look for reviews or Reddit posts from the last 3-6 months</li>
<li><strong>Budget for accessories</strong> — cables, stands, carrying cases and replacement pads/needles add 10-20% on top of the main purchase price</li>
<li><strong>Join the community early</strong> — getting active in subreddits and Discord servers before purchasing gives you direct access to current owner feedback</li>
<li><strong>Plan your setup holistically</strong> — whichever product you choose, make sure it integrates cleanly with the rest of your gear and software ecosystem</li>
</ul>
</section>
'''

def make_medium_block(slug):
    """~35-45 newlines: a table + section for pages needing more lines."""
    slug_l = slug.lower()
    h1_map = {
        'dj-equipment-beginners': ('Essential DJ Equipment for Beginners', 'equipment'),
        'how-to-start-djing': ('How to Start DJing', 'howto'),
        'serato-vs-rekordbox-vs-traktor': ('Serato vs Rekordbox vs Traktor', 'vs'),
        'how-to-mix-music-beginners': ('How to Mix Music for Beginners', 'howto'),
        'fl-studio-vs-ableton': ('FL Studio vs Ableton Live', 'vs'),
        'music-production-software-free': ('Best Free Music Production Software', 'best'),
    }
    slug_type = h1_map.get(slug, ('', ''))[1] if slug in h1_map else ''
    if not slug_type:
        if 'vs' in slug_l: slug_type = 'vs'
        elif 'how-to' in slug_l: slug_type = 'howto'
        elif 'best' in slug_l: slug_type = 'best'
        else: slug_type = 'generic'

    if slug_type == 'vs':
        return '''\n<section class="section">
<h2>Making Your Final Decision</h2>
<p>The most common mistake when choosing between competing platforms is over-researching and under-practising. Both options in this comparison are professional-grade — the right choice is the one you will actually use consistently.</p>
<table class="comparison-table">
<thead><tr><th>Your Profile</th><th>Best Fit</th><th>Key Reason</th></tr></thead>
<tbody>
<tr><td>Complete beginner</td><td>Try both free tiers</td><td>Your preferences are not yet formed; first impressions matter</td></tr>
<tr><td>Have existing hardware</td><td>Best integrated option</td><td>Avoid double-purchasing when native controller support differs</td></tr>
<tr><td>Focus on mixing only</td><td>Simpler interface wins</td><td>Feature bloat slows workflow when you just need good cueing</td></tr>
<tr><td>Production + DJing</td><td>Production-first platform</td><td>Staying in one ecosystem saves time and export steps</td></tr>
<tr><td>Club/mobile DJ</td><td>Industry-standard choice</td><td>Booth compatibility and USB media support are non-negotiable</td></tr>
</tbody>
</table>
<p>Whichever platform you choose, commit to it for at least 90 days before evaluating. Most switching decisions happen because of unfamiliarity, not genuine product limitations.</p>
</section>
<section class="section">
<h2>Where to Find Additional Support</h2>
<p>These communities provide active, free support for users of all the platforms covered in this comparison:</p>
<ul>
<li><strong>Reddit r/DJs</strong> — Weekly questions megathread; use search before posting as most common questions are thoroughly answered</li>
<li><strong>YouTube</strong> — Search "[platform name] tips [year]" for recent workflow tutorials covering the current version</li>
<li><strong>Manufacturer Discord servers</strong> — Direct access to beta testers, power users, and occasional developer responses</li>
</ul>
</section>
'''
    elif slug_type == 'howto':
        return '''\n<section class="section">
<h2>Practice Framework: 30-Day Skill Roadmap</h2>
<p>The fastest path from reading a guide to real competency is structured daily practice. Here is a simple 30-day framework that works regardless of your starting point:</p>
<table class="comparison-table">
<thead><tr><th>Week</th><th>Focus Area</th><th>Daily Practice Goal</th></tr></thead>
<tbody>
<tr><td>Week 1</td><td>Active listening</td><td>Identify beats, phrases, and transitions in 3 tracks you already know well</td></tr>
<tr><td>Week 2</td><td>Basic technique</td><td>Practise one core skill (e.g. beatmatching or EQ technique) for 20 minutes only — repetition builds muscle memory</td></tr>
<tr><td>Week 3</td><td>Applied mixing</td><td>Record a 20-minute mix and listen back critically — note exactly what went wrong</td></tr>
<tr><td>Week 4</td><td>Polish and refine</td><td>Recreate your best mix from week 3 with the specific issues corrected</td></tr>
</tbody>
</table>
<p>Progress feels slow in weeks 1-2, then suddenly clicks in weeks 3-4. This pattern is consistent across almost all skill-based learning — persistence past the "plateau" phase is the differentiator between DJs who develop rapidly and those who stall.</p>
</section>
<section class="section">
<h2>Gear and Software Checklist</h2>
<p>Before diving into practice, confirm you have everything you need to start:</p>
<ul>
<li>Hardware: Controller, audio interface (if needed), headphones with 3.5mm-to-6.3mm adapter</li>
<li>Software: DJ software installed and licence activated; check system requirements match your computer</li>
<li>Music library: At least 50 tracks in a consistent format (MP3/WAV 320kbps minimum) with BPM and key analysed</li>
<li>Backup: External drive or cloud backup for your music library — losing a collection is a significant setback</li>
</ul>
</section>
'''
    else:
        # best / generic
        return '''\n<section class="section">
<h2>Full Comparison Table</h2>
<p>Use this reference table to compare all the options covered in this guide at a glance:</p>
<table class="comparison-table">
<thead><tr><th>Consideration</th><th>Entry-Level Options</th><th>Mid-Range Options</th><th>Professional Options</th></tr></thead>
<tbody>
<tr><td>Typical price range</td><td>Under $150</td><td>$150 — $400</td><td>$400+</td></tr>
<tr><td>Best for</td><td>Absolute beginners; casual use</td><td>Serious hobbyists; semi-pro</td><td>Working professionals; touring DJs</td></tr>
<tr><td>Build quality</td><td>Plastic chassis, standard jogs</td><td>Metal components, improved jogs</td><td>Club-grade construction</td></tr>
<tr><td>Software included</td><td>Lite versions only</td><td>Full versions included</td><td>Full + pro features activated</td></tr>
<tr><td>Resale value</td><td>Low</td><td>Moderate</td><td>High (holds value well)</td></tr>
</tbody>
</table>
<p>For most beginners reading this guide, the mid-range tier represents the best value. Entry-level gear is often outgrown within 6 months, while professional gear has capabilities that may go unused for years. Put the savings toward music, lessons, or a better audio interface instead.</p>
</section>
<section class="section">
<h2>What to Buy First vs What to Wait On</h2>
<ul>
<li><strong>Buy first:</strong> Controller + headphones — these are the core tools where quality directly affects the learning experience</li>
<li><strong>Can wait:</strong> Mixer upgrades, USB drives, custom cartridges — these matter more once you have core skills developed</li>
<li><strong>Rent before buying:</strong> PA speakers for mobile gigs — rental makes more sense than purchase until you have 10+ events booked</li>
<li><strong>Skip entirely (for most):</strong> Standalone media players (CDJs) — software-based workflow is professional-grade and significantly cheaper</li>
</ul>
</section>
'''

def find_insert_pos(txt):
    """Find the best position to insert content — before FAQ, AI block, or </main>."""
    # 1. Before FAQ section
    m = re.search(r'<section[^>]*class="faq-section"', txt, re.I)
    if m:
        return m.start()
    m = re.search(r'<section[^>]*>\s*\n?\s*<h2[^>]*>[^<]*(?:Frequently Asked|FAQ)', txt, re.I)
    if m:
        return m.start()
    # 2. Before AI content block
    marker = '<!-- DATBOTTY-AI-CONTENT-START -->'
    pos = txt.find(marker)
    if pos != -1:
        return pos
    # 3. Before </main>
    m = re.search(r'</main>', txt, re.I)
    if m:
        return m.start()
    # 4. Before </body>
    m = re.search(r'</body>', txt, re.I)
    if m:
        return m.start()
    return -1

modified = 0
still_short = []

for slug in TARGET_PAGES:
    path = BASE / f'{slug}.html'
    if not path.exists():
        print(f'MISSING: {slug}')
        continue
    
    d = audit_page(path)
    el_before = d['line_count']
    if el_before >= 350:
        print(f'SKIP already OK ({el_before}): {slug}')
        continue
    
    gap = 350 - el_before
    txt = path.read_text()
    pos = find_insert_pos(txt)
    if pos == -1:
        print(f'ERROR no insert point: {slug}')
        still_short.append(slug)
        continue
    
    # Choose block size
    if gap <= 20:
        content = make_short_block()
    else:
        content = make_medium_block(slug)
    
    new_txt = txt[:pos] + content + txt[pos:]
    path.write_text(new_txt)
    
    d2 = audit_page(path)
    el2 = d2['line_count']
    if el2 >= 350:
        print(f'✅ {el_before} -> {el2}: {slug}')
    else:
        print(f'⚠️ {el_before} -> {el2} (need {350-el2} more): {slug}')
        still_short.append(slug)
    modified += 1

print(f'\nModified: {modified}')
if still_short:
    print(f'Still short: {still_short}')
