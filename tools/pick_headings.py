#!/usr/bin/env python3
"""Give buying-guide product sections a real editorial hierarchy.

Turns headings like

    <h2>Sennheiser HD 25 — Best DJ Headphones Overall</h2>

into

    <h2 class="pick-title"><span class="pick-name">Sennheiser HD 25</span>
        <span class="pick-role">Best DJ Headphones Overall</span></h2>

so every product pick in a guide reads as a ranked editorial entry rather than
another flat paragraph break. Idempotent; leaves FAQ and question headings alone.
"""
import glob
import html
import os
import re

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PATTERN = re.compile(r"<h2(\s[^>]*)?>([^<]{3,120}?)\s+[—–]\s+([^<]{3,90}?)</h2>", re.S)
SKIP_ROLE = re.compile(r"^(review|comparison|verdict|pros|cons|faq|summary|specs?|who)\b", re.I)


def repl(match):
    attrs = match.group(1) or ""
    name = html.unescape(match.group(2)).strip()
    role = html.unescape(match.group(3)).strip()
    if "?" in name or "?" in role or SKIP_ROLE.match(role):
        return match.group(0)
    if "pick-title" in attrs:
        return match.group(0)
    return (
        '<h2 class="pick-title"%s><span class="pick-name">%s</span>'
        '<span class="pick-role">%s</span></h2>' % (attrs, name, role)
    )


def main():
    changed = []
    for path in sorted(glob.glob("*.html")):
        src = open(path, encoding="utf-8").read()
        new, count = PATTERN.subn(repl, src)
        if count and new != src:
            open(path, "w", encoding="utf-8").write(new)
            changed.append((path, count))
    print("pages:", len(changed), "headings:", sum(c for _, c in changed))
    for path, count in changed[:12]:
        print(" ", path, count)


if __name__ == "__main__":
    main()
