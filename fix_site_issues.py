#!/usr/bin/env python3
"""
fix_site_issues.py — Fixes visual/content issues across offbeat-website:
1. Remove <section class="related-articles"...> blocks (redundant, bright white)
2. Remove "Making Your Final Decision" / "How to Make Your Final Pick" summary-box divs
3. Restyle remaining summary-box/tips-banner from #f8f9fa/#fff3cd to dark theme
4. Remove extra <div class="disclosure"> (keep only hero-disclosure)
5. Remove content after </footer> in beginner-dj-hub and dj-software-hub
"""
import re
from pathlib import Path

BASE = Path('/home/igpu/Desktop/AI Projects/DatBotty/offbeat-website')

def fix_page(path: Path) -> tuple[bool, list[str]]:
    txt = path.read_text()
    original = txt
    changes = []

    # 1. Remove related-articles sections entirely (bright white, redundant)
    new_txt, n = re.subn(
        r'<section[^>]*class="related-articles"[^>]*>.*?</section>\s*',
        '', txt, flags=re.DOTALL | re.IGNORECASE
    )
    if n:
        changes.append(f'removed {n} related-articles section(s)')
        txt = new_txt

    # 2. Remove "Making Your Final Decision" / "How to Make Your Final Pick" summary-box divs
    # These are <div class="summary-box"...>...<h2>Making Your Final Decision...</h2>...</div>
    # We need to match the specific div containing those headings
    def remove_summary_box_with_heading(text, heading_patterns):
        removed = 0
        for pattern in heading_patterns:
            # Match summary-box divs that contain these specific headings
            new_text, n = re.subn(
                r'<div[^>]*class="summary-box"[^>]*>(?:(?!</div>).)*?' + re.escape(pattern) + r'.*?</div>\s*',
                '', text, flags=re.DOTALL | re.IGNORECASE
            )
            if n:
                removed += n
                text = new_text
        return text, removed

    txt, n = remove_summary_box_with_heading(txt, [
        'Making Your Final Decision',
        'How to Make Your Final Pick',
    ])
    if n:
        changes.append(f'removed {n} "Making Your Final Decision" section(s)')

    # 3. Restyle remaining summary-box divs: change #f8f9fa → var(--surface)
    new_txt = txt.replace(
        'background:#f8f9fa;padding:1.5rem 2rem;border-radius:8px;margin:2rem 0;',
        'background:var(--surface);padding:1.5rem 2rem;border-radius:8px;margin:2rem 0;border:1px solid rgba(255,255,255,0.08);'
    )
    new_txt = new_txt.replace(
        'background:#f8f9fa;padding:1.5rem 2rem;border-radius:8px;margin:2rem 0',
        'background:var(--surface);padding:1.5rem 2rem;border-radius:8px;margin:2rem 0;border:1px solid rgba(255,255,255,0.08)'
    )
    # Also catch variations
    new_txt = re.sub(
        r'background:\s*#f8f9fa',
        'background:var(--surface)',
        new_txt
    )
    if new_txt != txt:
        changes.append('restyled #f8f9fa backgrounds → var(--surface)')
        txt = new_txt

    # 4. Restyle tips-banner: yellow → dark accent style
    new_txt = re.sub(
        r'background:#fff3cd;border:1px solid #ffc107;padding:([^;]+);border-radius:([^;]+);margin:([^"]+)"',
        r'background:rgba(124,58,237,0.15);border:1px solid rgba(124,58,237,0.4);padding:\1;border-radius:\2;margin:\3"',
        txt
    )
    if new_txt != txt:
        changes.append('restyled tips-banner yellow → dark accent')
        txt = new_txt

    # 5. Remove extra <div class="disclosure"> blocks (only keep hero-disclosure)
    # These are free-standing disclosure divs INSIDE main, not in the hero section
    new_txt, n = re.subn(
        r'\n?\s*<div class="disclosure"[^>]*>\s*\n\s*<strong>Disclosure:</strong>.*?</div>\s*\n',
        '\n',
        txt, flags=re.DOTALL
    )
    if n:
        changes.append(f'removed {n} extra inline disclosure div(s)')
        txt = new_txt

    # 6. Fix color:#444 in AI blocks (dark text on dark background = invisible)
    new_txt = txt.replace(
        'font-size:0.7rem;color:#444;margin-bottom:1rem;text-align:right;',
        'font-size:0.7rem;color:var(--muted);margin-bottom:1rem;text-align:right;'
    )
    if new_txt != txt:
        changes.append('fixed color:#444 in AI blocks → var(--muted)')
        txt = new_txt

    if txt != original:
        path.write_text(txt)
    return txt != original, changes


def fix_beginner_dj_hub():
    """Remove AI content + FAQ that appears AFTER </footer> in beginner-dj-hub.html"""
    path = BASE / 'beginner-dj-hub.html'
    txt = path.read_text()
    # Remove everything from after </footer> to </html>, then re-add proper closing
    # Find </footer> position
    footer_end = txt.rfind('</footer>')
    if footer_end == -1:
        return False, ['No </footer> found']
    
    after_footer = txt[footer_end + len('</footer>'):]
    # The after-footer contains Key Takeaways + FAQ + AI content calendar
    # We also need to check if there's AI artifact content before the footer
    before_footer = txt[:footer_end + len('</footer>')]
    
    # Also remove AI artifact just before the footer (the affiliate content calendar)
    # It's between <!-- DATBOTTY-AI-CONTENT-START --> and <!-- DATBOTTY-AI-CONTENT-END -->
    # inside the main before footer
    new_before = re.sub(
        r'<!-- DATBOTTY-AI-CONTENT-START -->.*?<!-- DATBOTTY-AI-CONTENT-END -->\s*',
        '', before_footer, flags=re.DOTALL
    )
    
    # Remove the "About Offbeat Inc." AI block that appears just before the AI content marker
    # (it's plain unstyled text about the company injected by AI)
    new_before = re.sub(
        r'\s*<h4>Who We Are</h4>.*?<p><strong>Welcome to the community\. Let\'s build your sound together\.</strong></p>\s*</div>\s*</section>\s*',
        '', new_before, flags=re.DOTALL
    )
    
    new_txt = new_before.rstrip() + '\n\n</body>\n</html>\n'
    path.write_text(new_txt)
    return True, ['removed misplaced AI content + FAQ after footer', 'removed AI content injected before footer']


def fix_dj_software_hub():
    """Remove FAQ that appears AFTER </footer> in dj-software-hub.html"""
    path = BASE / 'dj-software-hub.html'
    txt = path.read_text()
    footer_end = txt.rfind('</footer>')
    if footer_end == -1:
        return False, ['No </footer> found']
    
    new_txt = txt[:footer_end + len('</footer>')].rstrip() + '\n\n</body>\n</html>\n'
    path.write_text(new_txt)
    return True, ['removed misplaced FAQ section after footer']


def fix_best_dj_controllers_under_300():
    """Remove the AI-generated content block from best-dj-controllers-under-300.html"""
    path = BASE / 'best-dj-controllers-under-300.html'
    txt = path.read_text()
    new_txt = re.sub(
        r'\s*<!-- DATBOTTY-AI-CONTENT-START -->.*?<!-- DATBOTTY-AI-CONTENT-END -->\s*',
        '\n', txt, flags=re.DOTALL
    )
    if new_txt != txt:
        path.write_text(new_txt)
        return True, ['removed AI content block']
    return False, ['AI block not found']


def fix_rekordbox_review():
    """Fix Affiliate CTA #1 / #2 headings in rekordbox-review.html"""
    path = BASE / 'rekordbox-review.html'
    txt = path.read_text()
    # Remove the two fake CTA sections and replace with proper affiliate CTA
    new_txt = txt.replace(
        '<h2>Affiliate CTA #1: Best Rekordbox-Compatible Pioneer Gear</h2>\n<p>If you\'re sold on Rekordbox DJ, make the most of it with high-quality Pioneer gear. Check out <a href="##insert-affiliate-link-here##">this Pioneer DDJ controller</a> for seamless integration and incredible DJ performance.</p>\n<h2>Affiliate CTA #2: Start Your Rekordbox Journey Today</h2>\n<p>Thinking about diving into the Rekordbox universe? Sign up for the latest subscription plan <a href="##insert-affiliate-link-here##">here</a> and enjoy all the benefits offered by 2026\'s upgraded features!</p>',
        ''
    )
    # Also fix the "Two Affiliate CTAs" heading
    new_txt = new_txt.replace(
        '<h3>Two Affiliate CTAs</h3>\n<p>If you\'re ready to upgrade your DJ software and want the smoothest Pioneer integration, consider starting a Rekordbox subscription now — check the latest offers here and support our site: <span class="badge">Affiliate</span>. For DJs seeking official Pioneer hardware bundles and bundled trials, compare current deals on Pioneer products here: <span class="badge">Affiliate</span>.</p>',
        ''
    )
    if new_txt != txt:
        path.write_text(new_txt)
        return True, ['removed Affiliate CTA #1/#2 headings and "Two Affiliate CTAs" heading']
    return False, ['pattern not found']


def fix_audio_interface_guide():
    """Fix Two Affiliate CTAs heading in audio-interface-guide-djs.html"""
    path = BASE / 'audio-interface-guide-djs.html'
    txt = path.read_text()
    # Replace the "Two Affiliate CTAs (Proven Picks)" heading with a proper section heading
    new_txt = txt.replace(
        '<h2>Two Affiliate CTAs (Proven Picks)</h2>',
        '<h2>Our Top Picks on Amazon</h2>'
    )
    # Clean up the raw URL links — wrap them properly
    new_txt = new_txt.replace(
        '<li>Looking for a reliable all-rounder? Check the Focusrite Scarlett 4i4 on Amazon and get road-ready I/O and loopback for streaming: https://www.amazon.com/s?k=Focusrite+Scarlett+4i4&tag=offbeatdj-20</li>',
        '<li><strong>Best All-Rounder:</strong> <a href="https://www.amazon.com/s?k=Focusrite+Scarlett+4i4&tag=offbeatdj-20" rel="sponsored nofollow" target="_blank">Focusrite Scarlett 4i4 on Amazon</a> — road-ready I/O and loopback for streaming.</li>'
    )
    new_txt = new_txt.replace(
        '<li>Need studio-grade conversion and DSP for plugin tracking? Shop the Universal Audio Apollo Twin X here for pro-level sound and UAD plugin offload: https://www.amazon.com/s?k=UAD+Apollo+Twin+X&tag=offbeatdj-20</li>',
        '<li><strong>Best Pro Interface:</strong> <a href="https://www.amazon.com/s?k=UAD+Apollo+Twin+X&tag=offbeatdj-20" rel="sponsored nofollow" target="_blank">Universal Audio Apollo Twin X on Amazon</a> — studio-grade conversion with UAD DSP plugin offload.</li>'
    )
    if new_txt != txt:
        path.write_text(new_txt)
        return True, ['fixed Two Affiliate CTAs heading → "Our Top Picks on Amazon"', 'cleaned up raw URL links']
    return False, ['pattern not found']


def fix_pioneer_ddj_400_vs_flx4():
    """Fix Affiliate CTAs heading in pioneer-ddj-400-vs-flx4.html"""
    path = BASE / 'pioneer-ddj-400-vs-flx4.html'
    txt = path.read_text()
    new_txt = txt.replace(
        '<h2>Affiliate CTAs</h2>',
        '<h2>Where to Buy</h2>'
    )
    if new_txt != txt:
        path.write_text(new_txt)
        return True, ['fixed "Affiliate CTAs" heading → "Where to Buy"']
    return False, ['pattern not found']


def fix_best_daw_width():
    """Fix narrow max-width in best-daw-for-music-production.html"""
    path = BASE / 'best-daw-for-music-production.html'
    txt = path.read_text()
    new_txt = txt.replace(
        'main{max-width:860px;margin:0 auto;padding:2.5rem 1.5rem 4rem}',
        'main{margin:0 auto;padding:2.5rem 1.5rem 4rem}'
    )
    if new_txt != txt:
        path.write_text(new_txt)
        return True, ['removed narrow max-width:860px override — now uses global stylesheet width']
    return False, ['pattern not found']


def fix_virtual_dj_vs_serato():
    """Remove duplicate/redundant content blocks at end of virtual-dj-vs-serato.html"""
    path = BASE / 'virtual-dj-vs-serato.html'
    txt = path.read_text()
    # The page has a section of duplicate content after the verdict that repeats the pitch of the article
    # Lines 170-172 area: repeated intro paragraph + keyword-stuffed title
    new_txt = re.sub(
        r'<p>If you want, compare your current controller.*?</p>\s*<p>Virtual DJ vs Serato DJ Pro: Which Is Better\?.*?</p>\s*<p>Choosing between VirtualDJ and Serato.*?</p>',
        '', txt, flags=re.DOTALL
    )
    if new_txt != txt:
        path.write_text(new_txt)
        return True, ['removed duplicate intro paragraphs at end of page']
    return False, ['duplicate pattern not found - may already be clean']


# ── Main execution ─────────────────────────────────────────────────────────────
print('=== Fixing all offbeat-website pages ===\n')

# Phase 1: Site-wide fixes
changed_count = 0
for html_file in sorted(BASE.glob('*.html')):
    changed, changes = fix_page(html_file)
    if changed:
        changed_count += 1
        print(f'✅ {html_file.name}: {", ".join(changes)}')

print(f'\n→ Phase 1 complete: {changed_count} pages updated\n')

# Phase 2: Specific page fixes
for fn, desc in [
    (fix_beginner_dj_hub, 'beginner-dj-hub.html'),
    (fix_dj_software_hub, 'dj-software-hub.html'),
    (fix_best_dj_controllers_under_300, 'best-dj-controllers-under-300.html'),
    (fix_rekordbox_review, 'rekordbox-review.html'),
    (fix_audio_interface_guide, 'audio-interface-guide-djs.html'),
    (fix_pioneer_ddj_400_vs_flx4, 'pioneer-ddj-400-vs-flx4.html'),
    (fix_best_daw_width, 'best-daw-for-music-production.html'),
    (fix_virtual_dj_vs_serato, 'virtual-dj-vs-serato.html'),
]:
    changed, changes = fn()
    mark = '✅' if changed else '⚠️'
    print(f'{mark} {desc}: {", ".join(changes)}')

print('\n=== Done ===')
