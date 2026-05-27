#!/usr/bin/env python3
"""
inject_affiliatematic.py — Issue #922
Injects the affiliatematic Amazon associate widget into all content pages.
Idempotent: skips pages that already have the widget.
"""
import os
import glob

SKIP_PAGES = {"404.html", "about.html", "contact.html", "disclosure.html",
              "datbotty-status.html", "inject_affiliatematic.py"}

WIDGET_TAG = "offbeatdj-20"
WIDGET_DIV = f'  <div class="amazon-widget-container" data-tag="{WIDGET_TAG}" style="margin:2rem 0;"></div>\n'
WIDGET_SCRIPT = ('  <script src="https://affiliatematic.com/amazon-widget.iife.js"'
                 ' async defer></script>\n')

SENTINEL = 'amazon-widget-container'

injected = 0
skipped_already = 0
skipped_excluded = 0

pages = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "*.html")))

for path in pages:
    fname = os.path.basename(path)
    if fname in SKIP_PAGES:
        skipped_excluded += 1
        continue

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if SENTINEL in content:
        skipped_already += 1
        continue

    # Inject div before </footer> (or before </body> as fallback)
    if "</footer>" in content:
        content = content.replace("</footer>", f"{WIDGET_DIV}</footer>", 1)
    elif "</body>" in content:
        content = content.replace("</body>", f"{WIDGET_DIV}</body>", 1)
    else:
        print(f"  [SKIP] {fname}: no </footer> or </body> found")
        skipped_excluded += 1
        continue

    # Inject script before </body>
    if "</body>" in content:
        content = content.replace("</body>", f"{WIDGET_SCRIPT}</body>", 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    injected += 1
    print(f"  [OK] {fname}")

print(f"\nDone — injected: {injected}, already had widget: {skipped_already}, excluded: {skipped_excluded}")
