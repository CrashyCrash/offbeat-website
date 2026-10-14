#!/usr/bin/env python3
"""Read-only static triage for one TDQ draft on the protected base.

NOT a semantic model review, source citation, approval or merge grant.
Never check out / import / execute files from the untrusted PR head.
"""
import argparse
import difflib
import hashlib
import html
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys

HEX = re.compile(r"[0-9a-f]{40,64}\Z")
PAGE = re.compile(r"[a-z0-9][a-z0-9-]{0,100}\.html\Z")
RISK = re.compile(
    r"(?i)\$\s?\d|(?:\d+[\s-]?(?:years|hours|products|guides|%))\b|"
    r"\b(?:guarantee|tested|ranked|compared|best|all.in|free|compatible|"
    r"unlimited|always|never|only|fastest|exclusive|verified)\b"
)


def git(*args):
    p = subprocess.run(
        ["git", "--no-pager", "-c", "core.hooksPath=/dev/null",
         "-c", "core.fsmonitor=false", *args],
        capture_output=True, timeout=45, check=False,
    )
    if p.returncode:
        raise ValueError("trusted git operation failed: " + args[0])
    return p.stdout


class Markup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.media = []
        self.handlers = []
        self.forms = []
        self.stylesheets = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a":
            self.links.append(a.get("href"))
        if tag in ("img", "audio", "video", "source", "iframe"):
            self.media.append((tag, a.get("src")))
        if tag == "form":
            self.forms.append(a.get("action"))
        if tag == "link" and "stylesheet" in str(a.get("rel", "")).lower():
            self.stylesheets.append(a.get("href"))
        self.handlers.extend((tag, k, v) for k, v in attrs
                             if k and k.lower().startswith("on"))


def script_surfaces(doc):
    """Separate inert JSON-LD from potentially executable JS."""
    js, structured = [], []
    for match in re.finditer(r"(?is)<script\b([^>]*)>(.*?)</script\s*>", doc):
        raw = match.group(0)
        if re.search(r"""(?i)type\s*=\s*['"]application/ld\+json['"]""", match.group(1)):
            structured.append(raw)
        else:
            js.append(raw)
    return js, structured


def analyze(base, head, path):
    if path is None or not PAGE.fullmatch(path):
        raise ValueError("outside authorized root HTML scope")
    old = base.decode("utf-8", "strict")
    new = head.decode("utf-8", "strict")
    if old == new:
        raise ValueError("no changed source bytes")

    o, n = Markup(), Markup()
    o.feed(old)
    n.feed(new)
    critical = ("links", "media", "forms", "stylesheets", "handlers")
    failures = [name for name in critical if getattr(o, name) != getattr(n, name)]
    old_js, old_jsonld = script_surfaces(old)
    new_js, new_jsonld = script_surfaces(new)
    if old_js != new_js:
        failures.append("executable script content")
    if failures:
        raise ValueError("unauthorized source surface changed: " + ", ".join(failures))

    added = [s[1:] for s in difflib.unified_diff(
        old.splitlines(), new.splitlines(), n=0)
        if s.startswith("+") and not s.startswith("+++")]
    risk_lines = sum(bool(RISK.search(s)) for s in added)
    return {
        "base_hash": hashlib.sha256(base).hexdigest(),
        "head_hash": hashlib.sha256(head).hexdigest(),
        "added_lines": len(added),
        "risk_lines": risk_lines,
        "structured_data_changed": old_jsonld != new_jsonld,
    }


def bounded_paths(entries):
    """Independent protected-base scope validation; 1–4 existing root HTML pages."""
    if not 1 <= len(entries) <= 4:
        raise ValueError("expected one to four source files")
    paths = []
    for entry in entries:
        fields = entry.split("\t", 1)
        if len(fields) != 2:
            raise ValueError("malformed source status")
        status, path = fields
        if status != "M" or not PAGE.fullmatch(path):
            raise ValueError("draft may modify only existing root-level HTML pages")
        paths.append(path)
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate changed page")
    return paths


def selftest():
    old = b'<html><a href="contact.html">Home</a><p>Guaranteed.</p></html>'
    new = b'<html><a href="contact.html">Home</a><p>Usually.</p></html>'
    assert analyze(old, new, "index.html")["added_lines"] == 1
    try:
        analyze(old, new.replace(b"contact.html", b"evil.html"), "index.html")
    except ValueError:
        pass
    else:
        raise AssertionError("link change must fail")
    for bad in ("../index.html", ".github/page.html", "a.js"):
        try:
            analyze(old, new, bad)
        except ValueError:
            continue
        raise AssertionError("path must fail")
    try:
        analyze(old, old, "index.html")
    except ValueError:
        pass
    else:
        raise AssertionError("unchanged source must not pass")
    try:
        analyze(old, new.replace(b"<p>", b'<p onclick="alert(1)">'),
                "index.html")
    except ValueError:
        pass
    else:
        raise AssertionError("new event handlers must not pass")
    # Inert JSON-LD edits are flagged for review, not mistaken for proof.
    a = (b'<script type="application/ld+json">{"name":"Old"}</script>'
         b'<a href="x.html">same</a>')
    b = (b'<script type="application/ld+json">{"name":"New"}</script>'
         b'<a href="x.html">same</a>')
    assert analyze(a, b, "index.html")["structured_data_changed"] is True
    assert bounded_paths(["M\tindex.html"]) == ["index.html"]
    assert bounded_paths(["M\tguide-a.html", "M\tguide-b.html"]) == [
        "guide-a.html", "guide-b.html"]
    for rejected in ([], ["M\ta.html"] * 5,
                     ["M\tindex.html", "M\tindex.html"],
                     ["M\ta.html", "M\t../x.html"],
                     ["M\ta.html", "A\tnew.html"],
                     ["M\ta.html", "M\tassets/x.html"],
                     ["M\ta.html", "M\tfile.js"]):
        try:
            bounded_paths(rejected)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe or excessive changed source paths")



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--summary")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    selftest()
    if args.self_test:
        print("TDQ source triage selftest OK")
        return 0
    if not args.base or not args.head or not args.summary:
        parser.error("base, head and summary are required")
    if not HEX.fullmatch(args.base) or not HEX.fullmatch(args.head):
        raise ValueError("invalid immutable SHA")
    names = git("diff", "--no-renames", "--name-status", args.base, args.head, "--")
    entries = names.decode("utf-8", "strict").strip().splitlines()
    paths = bounded_paths(entries)
    metrics_by_path = []
    for path in paths:
        before = git("show", args.base + ":" + path)
        after = git("show", args.head + ":" + path)
        metrics_by_path.append((path, analyze(before, after, path)))
    risk_count = sum(metrics["risk_lines"] for _, metrics in metrics_by_path)
    notes = [
        "### TDQ draft source integrity / claim-risk triage",
        "",
        "**NOT an approval.** No model or human fact-check took place. The "
        "protected-base checker did not execute candidate code.",
        "",
        "- Bounded existing root-level editorial HTML pages changed: " + str(len(paths)),
        "- Links, executable scripts, handlers, media, forms and stylesheets "
        "preserved independently for every changed page",
        "- Potential product/price/credibility risk lines: " + str(risk_count),
    ]
    for path, metrics in metrics_by_path:
        notes.extend([
            "- " + html.escape(path) + ": head HTML SHA-256 " + metrics["head_hash"]
            + "; structured data changed=" + str(metrics["structured_data_changed"])
            + "; risk lines=" + str(metrics["risk_lines"])
        ])
    notes.extend([
        "",
        "**Next gate:** Independent semantic and cross-page consistency review "
        "of all changed claims, followed by separately authorized release checks. "
        "Zero risk-pattern lines is NOT evidence of factual accuracy."
    ])
    Path(args.summary).write_text("\n".join(notes) + "\n", encoding="utf-8")
    print("TDQ_STATIC_SCOPE_PASS; SEMANTIC_REVIEW_REQUIRED; pages=",
          len(paths), "fact-risk lines=", risk_count)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, UnicodeError, subprocess.TimeoutExpired) as e:
        print("TDQ_STATIC_SCOPE_BLOCKED:", type(e).__name__, str(e)[:200],
              file=sys.stderr)
        sys.exit(2)
