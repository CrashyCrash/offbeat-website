#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/igpu/Desktop/AI Projects/DatBotty')
from hub.scripts.page_finisher import audit_page
from pathlib import Path
from collections import defaultdict

BASE = Path('/home/igpu/Desktop/AI Projects/DatBotty/offbeat-website')
buckets = defaultdict(list)

for p in sorted(BASE.glob('*.html')):
    try:
        d = audit_page(p)
        s = round(d['completion_score'], 2)
        buckets[s].append((d['line_count'], p.stem))
    except Exception:
        pass

total = sum(len(v) for v in buckets.values())
for score in sorted(buckets.keys()):
    pages = buckets[score]
    print(f'Score {score:.2f}: {len(pages)} pages')
    for lc, slug in sorted(pages)[:3]:
        missing = next((audit_page(BASE / f'{slug}.html')['missing_sections'] for _ in [0]), '')
        print(f'  {lc}L: {slug} | {missing}')
    if len(pages) > 3:
        print(f'  ...and {len(pages)-3} more')
print(f'\nTotal pages: {total}')
print(f'At 0.87+: {sum(len(v) for s, v in buckets.items() if s >= 0.87)}')
print(f'At 0.75+: {sum(len(v) for s, v in buckets.items() if s >= 0.75)}')
