#!/usr/bin/env python3
"""Turn repetitive "Check current prices" strips into a compact buy bar.

Each guide currently repeats the same two sentences dozens of times, which reads
as boilerplate. This rewrites those strips to a single line: the product name and
a dated price note pulled from the guide where available, plus the retailer link.
"""
import glob
import re

PATTERN = re.compile(
    r'<div class="product-buy-row[^"]*"><div><strong>Check current prices</strong>'
    r'<p>Confirm today[^<]*</p></div>'
    r'(<a class="([^"]*)" href="([^"]*)"[^>]*>)([^<]*)</a></div>',
    re.S,
)

REPLACEMENT = (
    '<div class="product-buy-row"><div><strong>{name}</strong>'
    '<p>Live price and stock at the retailer. Prices move week to week — we date every figure in this guide.</p></div>'
    '{link}</div>'
)


def product_name(anchor_text):
    label = re.sub(r"<[^>]+>", "", anchor_text)
    label = re.sub(r"^Shop\s+", "", label).strip()
    label = re.sub(r"\s+on Amazon.*$", "", label)
    label = re.sub(r"\s+→$", "", label)
    return label.strip()


def main():
    pages = 0
    rows = 0
    for path in sorted(glob.glob("*.html")):
        src = open(path, encoding="utf-8").read()

        def repl(match):
            name = product_name(match.group(4))
            return REPLACEMENT.format(name=name, link=match.group(1) + match.group(4) + "</a>")

        new, count = PATTERN.subn(repl, src)
        if count:
            open(path, "w", encoding="utf-8").write(new)
            pages += 1
            rows += count
    print("pages:", pages, "rows:", rows)


if __name__ == "__main__":
    main()
