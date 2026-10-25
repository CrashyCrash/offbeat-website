#!/usr/bin/env python3
"""Remove duplicated generic filler sections from guide pages.

Across the site, several generated sections repeat near-identical advice
("Practical checklist before you decide", "Buying checklist before you choose",
"How to use this guide in a real DJ setup"). On many pages two or three of them
appear in a row, which is what makes a long guide feel machine-written.

This pass:
  * keeps at most ONE buying-checklist block per page and rewrites it as a short,
    consistent component;
  * removes the "How to use this guide in a real DJ setup" filler entirely;
  * removes the duplicated "Related guides" mini-list that repeats the page-level
    related links block.

Idempotent: rewritten blocks carry data-filler="checked" and are left alone.
"""
import glob
import os
import re

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHECKLIST_HEADINGS = (
    "practical checklist before you decide",
    "buying checklist before you choose",
    "practical checklist before moving on",
    "buyer checklist before you purchase",
    "buying advice and compatibility checks",
    "how to make the comparison useful",
    "before you buy",
)
DROP_HEADINGS = (
    "how to use this guide in a real dj setup",
    "expert tips and key considerations",
)

CLEAN_CHECKLIST = """<section class="article-section buy-check" data-filler="checked">
<h2>Before you buy: five quick checks</h2>
<p>Price is the easy part. These are the checks that decide whether a purchase still looks sensible six months later.</p>
<div class="format-action-table">
<div class="format-action-row"><strong>Software fit</strong><span>Confirm the exact model unlocks or works with the software and version you use — not just the brand family. Licence tiers and bundled unlocks change between hardware generations.</span></div>
<div class="format-action-row"><strong>Your computer</strong><span>Check the operating-system support list and the minimum specs for your platform before you assume your machine is fine.</span></div>
<div class="format-action-row"><strong>Connections</strong><span>Match the outputs to what you plug into: RCA, TRS, XLR, booth out, headphone jacks. Adapters cost money and add failure points.</span></div>
<div class="format-action-row"><strong>Upgrade path</strong><span>If you plan to add a second deck, a DVS setup or a PA, check that this purchase does not need replacing to get there.</span></div>
<div class="format-action-row"><strong>Total cost</strong><span>Add the case, cables, stands, replacement pads or licence upgrade. The shelf price is rarely the whole number.</span></div>
</div>
</section>"""


def find_sections(src):
    """Yield (start, end, class_attr, inner) for top-level <section> blocks."""
    out = []
    depth = 0
    start = None
    for match in re.finditer(r"<section\b([^>]*)>|</section>", src):
        token = match.group(0)
        if token.startswith("<section"):
            if depth == 0:
                start = (match.start(), match.group(1))
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start:
                out.append((start[0], match.end(), start[1], src[start[0]:match.end()]))
                start = None
    return out


def heading_of(inner):
    match = re.search(r"<h2[^>]*>(.*?)</h2>", inner, re.S)
    if not match:
        return ""
    return re.sub(r"<[^>]+>", "", match.group(1)).strip().lower()


def clean(src):
    changed = False
    sections = find_sections(src)
    drop = []
    seen_check = False
    for start, end, attrs, inner in sections:
        if 'article-section buy-check' in attrs or 'data-filler="checked"' in attrs:
            seen_check = True
            continue
        heading = heading_of(inner)
        if not heading:
            continue
        if heading in DROP_HEADINGS:
            drop.append((start, end, None))
            continue
        if heading in CHECKLIST_HEADINGS:
            # A page that already has a real "before you buy" section keeps it;
            # the generic block would only repeat it.
            has_real_check = any(
                key in heading_of(other)
                for start2, end2, attrs2, other in sections
                if (start2, end2) != (start, end) and ('buy-check' not in attrs2)
                for key in ("before you buy", "before you purchase", "buyer checklist", "buying checklist")
            )
            if has_real_check:
                drop.append((start, end, None))
            elif seen_check:
                drop.append((start, end, None))
            else:
                drop.append((start, end, CLEAN_CHECKLIST))
                seen_check = True
    for start, end, replacement in sorted(drop, reverse=True):
        src = src[:start] + (replacement or "") + src[end:]
        changed = True
    return src, changed


def main():
    pages = 0
    removed = 0
    for path in sorted(glob.glob("*.html")):
        src = open(path, encoding="utf-8").read()
        before = len(src)
        new, changed = clean(src)
        if changed:
            open(path, "w", encoding="utf-8").write(new)
            pages += 1
            removed += before - len(new)
    print("pages cleaned:", pages, "bytes removed:", removed)


if __name__ == "__main__":
    main()
