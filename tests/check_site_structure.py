#!/usr/bin/env python3
"""Deterministic structural checks for the static site (stdlib only).

    python3 tests/check_site_structure.py            # all root *.html
    python3 tests/check_site_structure.py page.html  # specific pages

Catches the defects that browser rendering and "JSON-LD parses" do not:
  * document nesting: exactly one <html>/<body>/<main>, the tags close in
    order, nothing but whitespace after </html>, no malformed "</html<..."
  * editorial sections that land outside <main> (e.g. after </body>)
  * JSON-LD ItemList entries that are not visible product headings, or that
    name discontinued models
  * internal-only copy ("Verify current price", "verify the current price")
  * local <img src>/<a href> targets that do not exist

Exit 0 when all checked pages pass, 1 otherwise. Output lists each failure.
"""
import glob
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Models that are no longer sold new. They may appear in a clearly labelled
# discontinued note, but never as ItemList/Product structured data.
DISCONTINUED = ["DDJ-800", "MC7000"]
INTERNAL_COPY = re.compile(r"verify (the )?current price|verify current price|verify actual retailer", re.I)

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Walker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.counts = {"html": 0, "body": 0, "main": 0}
        self.h2 = []
        self.h3 = []
        self.imgs = []
        self.hrefs = []
        self.ld = []
        self._in_ld = False
        self._ld_buf = []
        self.main_depth = 0
        self.chrome_depth = 0  # header/nav/footer: legitimately outside <main>
        self.h2_depth = 0
        self._h2_buf = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.counts:
            self.counts[tag] += 1
        if tag == "main":
            self.main_depth += 1
        if tag in ("header", "nav", "footer"):
            self.chrome_depth += 1
        if tag == "img":
            self.imgs.append((a.get("src", ""), a.get("alt")))
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True
            self._ld_buf = []
        if tag == "h3":
            self.h3_depth = getattr(self, "h3_depth", 0) + 1
            self._h3_buf = []
        if tag == "h2":
            self.h2_depth += 1
            self._h2_buf = []
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag == "main":
            self.main_depth -= 1
        if tag in ("header", "nav", "footer") and self.chrome_depth:
            self.chrome_depth -= 1
        if tag == "h3" and getattr(self, "h3_depth", 0):
            self.h3_depth -= 1
            text = "".join(self._h3_buf).strip()
            if text:
                self.h3.append(text)
        if tag == "h2" and self.h2_depth:
            self.h2_depth -= 1
            text = "".join(self._h2_buf).strip()
            if text:
                self.h2.append((text, self.main_depth > 0 or self.chrome_depth > 0))
        if tag == "script" and self._in_ld:
            self._in_ld = False
            self.ld.append("".join(self._ld_buf))
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"line {self.getpos()[0]}: mis-nested </{tag}> (open: {self.stack[-3:]})")
            if tag in self.stack:
                while self.stack and self.stack[-1] != tag:
                    self.stack.pop()
                if self.stack:
                    self.stack.pop()
        else:
            self.stack.pop()
        if tag == "html":
            self.saw_end_html_at = self.getpos()

    def handle_data(self, data):
        if self._in_ld:
            self._ld_buf.append(data)
        if self.h2_depth:
            self._h2_buf.append(data)
        if getattr(self, "h3_depth", 0):
            self._h3_buf.append(data)


def check_page(path):
    errors = []
    text = open(path, encoding="utf-8").read()
    rel = os.path.relpath(path, ROOT)

    # Raw-text guards that catch the exact regression class seen in 8fe0904.
    if re.search(r"</html(?![\s>])", text):
        errors.append("malformed </html (missing '>' or followed by content)")
    tail = text.split("</html>")[-1] if "</html>" in text else None
    if tail is None:
        errors.append("no closing </html> tag")
    elif tail.strip():
        errors.append(f"content after </html>: {tail.strip()[:60]!r}")

    w = Walker()
    w.feed(text)
    errors += [f"nesting: {e}" for e in w.errors[:5]]
    if w.counts["html"] != 1:
        errors.append(f"expected 1 <html>, found {w.counts['html']}")
    if w.counts["body"] != 1:
        errors.append(f"expected 1 <body>, found {w.counts['body']}")
    if w.counts["main"] != 1:
        errors.append(f"expected 1 <main>, found {w.counts['main']}")
    if w.stack:
        errors.append(f"unclosed tags at EOF: {w.stack[-5:]}")

    # Every <h2> must be inside <main>: a section emitted after </body> would
    # be rendered by browsers but would sit outside the document's content.
    h2_outside = [h for h, inside in w.h2 if not inside]
    if h2_outside:
        errors.append(f"{len(h2_outside)} <h2> outside <main>/header/nav/footer: {h2_outside[:2]}")

    # JSON-LD ItemList: entries must be real visible product headings.
    # Compare against every visible heading level, normalised for punctuation, so
    # structured data is checked against what a reader can actually see.
    def norm(value):
        value = value.replace("\u2019", "'").replace("\u2018", "'")
        value = re.sub(r"[\u2013\u2014:\-\u00b7|]+", " ", value)
        return re.sub(r"\s+", " ", value).strip().lower()

    h2_text = norm(" | ".join([h for h, _ in w.h2] + list(w.h3)))
    for block in w.ld:
        try:
            d = json.loads(block)
        except ValueError as e:
            errors.append(f"JSON-LD does not parse: {e}")
            continue
        items = [d] if isinstance(d, dict) else d
        for obj in items:
            if not isinstance(obj, dict) or obj.get("@type") != "ItemList":
                continue
            names = [i.get("name", "") for i in obj.get("itemListElement", [])]
            if obj.get("numberOfItems") != len(names):
                errors.append(f"ItemList numberOfItems={obj.get('numberOfItems')} but {len(names)} entries")
            for n in names:
                if norm(n) not in h2_text:
                    errors.append(f"ItemList entry not a visible heading: {n!r}")
                for dc in DISCONTINUED:
                    if dc in n:
                        errors.append(f"discontinued model in ItemList: {n!r}")

    # Visible internal-only copy must not ship.
    visible = re.sub(r"<script.*?</script>", "", text, flags=re.S)
    for m in INTERNAL_COPY.finditer(visible):
        errors.append(f"internal copy: {m.group(0)!r}")

    # Local assets and links must resolve.
    for src, alt in w.imgs:
        if src.startswith(("http://", "https://", "data:", "//")):
            if alt is None:
                errors.append(f"remote image without alt: {src[:60]}")
            continue
        target = os.path.normpath(os.path.join(os.path.dirname(path), src.split("?")[0].split("#")[0]))
        if src and not os.path.exists(target):
            errors.append(f"missing local image: {src}")
        if alt is None:
            errors.append(f"image without alt: {src[:60]}")
    for href in w.hrefs:
        if href.startswith(("http://", "https://", "mailto:", "tel:", "#", "javascript:")):
            continue
        clean = href.split("#")[0].split("?")[0]
        if not clean:
            continue
        target = os.path.normpath(os.path.join(os.path.dirname(path), clean))
        if not os.path.exists(target):
            errors.append(f"broken local link: {href}")

    return rel, errors


def main(argv):
    pages = argv[1:] or sorted(glob.glob(os.path.join(ROOT, "*.html")))
    failed = 0
    for p in pages:
        rel, errs = check_page(p)
        if errs:
            failed += 1
            print(f"FAIL {rel}")
            for e in errs:
                print(f"     - {e}")
    print(f"{len(pages) - failed}/{len(pages)} pages passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
