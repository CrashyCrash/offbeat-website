#!/usr/bin/env python3
"""Whole-site integrity check (stdlib only).

Covers the things that actually break a static site:
  * every internal link and image target resolves on disk
  * exactly one <h1> per page, and a meta description per page
  * every <img> has a non-empty alt attribute
  * no duplicate element ids on a page
  * the shared shell is present (header, footer, search dialog, stylesheet)
  * no remote image is used as a page hero (placeholder-art guard)
  * no leftover "page-visuals" placeholder illustrations are referenced
  * no machine-generated metadata strings reach <meta> or JSON-LD

Usage: python3 tools/check_site.py
Exit code 0 when clean, 1 when problems are found.
"""
import glob
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

problems = []

# Strings that only ever came from the automated page generator. They read as
# keyword lists rather than sentences and should never ship.
MACHINE_COPY = (
    "practical recommendations and current buying notes",
    "Comprehensive guide to",
)


def check_page(path):
    src = open(path, encoding="utf-8").read()

    for href in set(re.findall(r'(?:href|src)="([^"#?:]+\.(?:html|css|js|json|svg|woff2|jpg|jpeg|png))', src)):
        if href.startswith(("http", "//")):
            continue
        if not os.path.exists(href):
            problems.append(f"{path}: missing target {href}")

    for match in re.finditer(r'<a [^>]*href="([^"]+)"', src):
        href = match.group(1)
        if href.startswith(("http", "mailto:", "tel:", "#", "/")):
            continue
        target = href.split("#")[0].split("?")[0]
        if target and not os.path.exists(target):
            problems.append(f"{path}: broken link {href}")

    h1 = len(re.findall(r"<h1\b", src))
    if h1 != 1:
        problems.append(f"{path}: {h1} <h1> elements")

    if 'name="description"' not in src:
        problems.append(f"{path}: no meta description")

    for img in re.finditer(r"<img\b[^>]*>", src):
        tag = img.group(0)
        alt = re.search(r'alt="([^"]*)"', tag)
        if not alt or not alt.group(1).strip():
            problems.append(f"{path}: image without alt text: {tag[:70]}")

    ids = re.findall(r'\sid="([^"]+)"', src)
    for value, count in Counter(ids).items():
        if count > 1:
            problems.append(f"{path}: duplicate id {value!r} ({count}x)")

    for required, label in (
        ('class="nav-inner"', "shared header"),
        ('class="footer-nav-grid', "shared footer"),
        ('id="site-search"', "search dialog"),
        ('assets/style.css', "stylesheet"),
        ('assets/site.js', "site script"),
    ):
        if required not in src:
            problems.append(f"{path}: missing {label}")

    if "images.unsplash.com" in src or "page-visuals" in src:
        problems.append(f"{path}: references a removed placeholder image")

    for script in re.findall(r'<script type="application/ld\+json">(.*?)</script>', src, re.S):
        if script.count("{") != script.count("}"):
            problems.append(f"{path}: unbalanced JSON-LD braces")

    # A link inside a card link is invalid HTML and breaks the card layout
    # in browsers that reparent anchors. Cheap to detect, easy to miss by eye.
    for card in re.finditer(r'<a\b[^>]*class="[^"]*ofb-card[^"]*"[^>]*>', src):
        window = src[card.end():card.end() + 900]
        close = window.find("</a>")
        if "<a " in window[: close if close != -1 else len(window)]:
            problems.append(f"{path}: nested <a> inside a card link")
            break


def check_machine_copy(path, src):
    meta = " ".join(re.findall(r'<meta [^>]*content="([^"]*)"[^>]*>', src))
    schema = " ".join(re.findall(r'<script type="application/ld\+json">(.*?)</script>', src, re.S))
    for phrase in MACHINE_COPY:
        if phrase in meta:
            problems.append(f"{path}: machine-written phrase in <meta>: {phrase!r}")
        if phrase in schema:
            problems.append(f"{path}: machine-written phrase in JSON-LD: {phrase!r}")


def main():
    pages = sorted(glob.glob("*.html"))
    for page in pages:
        check_page(page)
        check_machine_copy(page, open(page, encoding="utf-8").read())
    for asset in glob.glob("assets/**/*", recursive=True):
        if os.path.isdir(asset):
            continue
        if os.path.getsize(asset) == 0:
            problems.append(f"{asset}: empty file")

    print(f"pages checked: {len(pages)}")
    if problems:
        print(f"problems: {len(problems)}")
        for problem in problems[:60]:
            print(" -", problem)
        return 1
    print("no problems found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
