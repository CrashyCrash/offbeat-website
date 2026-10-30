#!/usr/bin/env python3
"""Remove machine-appended "buying checkpoint" blocks and duplicate related-lists.

Older automation appended a section to the end of many guides, after the author
box, with headings such as "Best Standalone Dj Systems buying checkpoint",
a re-list of the same picks, and a "Related next reads" list of lower-cased link
labels. It repeats content, breaks the page's closing structure and is the most
visible sign that a page was assembled rather than written. This removes those
blocks (r27-/r28-buying-checkpoint) and the duplicate "Related guides" mini-lists
that repeat the primary related-links block on the same page.
"""
import glob
import re

CHECKPOINT = re.compile(
    r'<section[^>]*class="[^"]*r2[78]-buying-checkpoint[^"]*"[^>]*>.*?</section>\s*',
    re.S,
)
RELATED_MINOR = re.compile(
    r'<section[^>]*class="[^"]*datbotty-related-guides[^"]*"[^>]*>.*?</section>\s*',
    re.S,
)
REVENUE_NOTE = re.compile(
    r'<section[^>]*class="[^"]*r26-revenue-note[^"]*"[^>]*>.*?</section>\s*',
    re.S,
)
REVENUE_HEADINGS = re.compile(
    r'<section[^>]*>(?:(?!</section>).)*?<h2>[^<]*(?:cost and hardware lock-in check|lock-in check)</h2>.*?</section>\s*',
    re.S,
)


def strip_block(pattern, src):
    """Remove matched sections; returns (src, count)."""
    count = 0
    while True:
        match = pattern.search(src)
        if not match:
            break
        src = src[: match.start()] + src[match.end():]
        count += 1
    return src, count


def main():
    pages = 0
    removed = {"checkpoint": 0, "related_minor": 0, "revenue": 0}
    for path in sorted(glob.glob("*.html")):
        src = open(path, encoding="utf-8").read()
        before = src
        src, n1 = strip_block(CHECKPOINT, src)
        src, n3 = strip_block(REVENUE_NOTE, src)
        src, n4 = strip_block(REVENUE_HEADINGS, src)
        # The minor related list only adds noise when the page already has a
        # primary related-links block.
        if 'funnel-related' in src:
            src, n2 = strip_block(RELATED_MINOR, src)
        else:
            n2 = 0
        if src != before:
            open(path, "w", encoding="utf-8").write(src)
            pages += 1
            removed["checkpoint"] += n1
            removed["related_minor"] += n2
            removed["revenue"] += n3 + n4
    print("pages cleaned:", pages, removed)


if __name__ == "__main__":
    main()
