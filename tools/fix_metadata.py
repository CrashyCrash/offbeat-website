#!/usr/bin/env python3
"""Replace machine-generated metadata strings with the page's human description.

Older automation wrote keyword-stuffed strings such as
"Comprehensive guide to X 2026 features price with practical recommendations and
current buying notes — updated 2026" into meta descriptions, hero subtitles and
JSON-LD "description" fields. The hero and <meta> copy has been rewritten by
hand; this script brings the structured data into line by reusing the page's
own <meta name="description"> wherever a schema description still carries the old
pattern, then verifies every JSON-LD block still parses.
"""
import glob
import json
import re

BAD = ("practical recommendations", "Comprehensive guide to", "current buying notes")


def meta_description(src):
    """Read the page description whichever attribute order the page uses."""
    for pattern in (
        r'<meta content="([^"]*)" name="description">',
        r'<meta name="description" content="([^"]*)">',
    ):
        match = re.search(pattern, src)
        if match:
            return match.group(1).replace("&quot;", '"')
    return None


def main():
    fixed = 0
    pages = 0
    errors = []
    for path in sorted(glob.glob("*.html")):
        src = open(path, encoding="utf-8").read()
        desc = meta_description(src)
        if not desc:
            continue
        original = src

        def patch_block(block):
            try:
                data = json.loads(block)
            except Exception:
                errors.append(path)
                return block

            changed = False

            def walk(node):
                nonlocal changed
                if isinstance(node, dict):
                    for key, value in list(node.items()):
                        if key in ("description", "abstract") and isinstance(value, str) and any(b in value for b in BAD):
                            node[key] = desc
                            changed = True
                        elif key == "name" and isinstance(value, str) and any(b in value for b in BAD):
                            node[key] = re.sub(r"\s*[—-]\s*Offbeat$", "", value)
                            changed = True
                        else:
                            walk(value)
                elif isinstance(node, list):
                    for item in node:
                        walk(item)

            walk(data)
            if not changed:
                return block
            return "\n" + json.dumps(data, indent=2, ensure_ascii=False) + "\n"

        src = re.sub(
            r'(<script type="application/ld\+json">)(.*?)(</script>)',
            lambda m: m.group(1) + patch_block(m.group(2)) + m.group(3),
            src,
            flags=re.S,
        )
        if src != original:
            open(path, "w", encoding="utf-8").write(src)
            pages += 1
            fixed += sum(src.count(b) for b in BAD)
    print("pages updated:", pages, "| leftover bad strings:", fixed, "| json errors:", sorted(set(errors)))


if __name__ == "__main__":
    main()
