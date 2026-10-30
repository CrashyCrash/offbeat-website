# Offbeat Inc. — static publication

The public Offbeat website: independent DJ equipment, software and skills guides.
Plain HTML, one stylesheet, two small scripts. No build step, no framework, no
runtime dependencies — open a file or serve the folder and it works.

## Structure

```
*.html                     one file per guide (115 published pages)
index.html                 homepage
all-dj-guides.html         generated library page (filters + full index)
assets/style.css           the whole design system
assets/site.js             nav drawer, library filter, site search, TOC, progress
assets/offbeat-analytics.js  consent-gated GA4 loader (see privacy policy)
assets/fonts/              self-hosted Inter + Space Grotesk (OFL)
assets/img/editorial/      Offbeat editorial photography used site-wide
assets/search-index.json   generated search index
assets/og-default.jpg      social share card
tools/                     maintenance scripts (see below)
tests/                     structural tests and GA4 consent harnesses
evidence/                  dated verification notes and screenshots
```

## Local preview

```bash
python3 -m http.server 8000
# then open http://localhost:8000/
```

## Maintenance scripts

All scripts are idempotent and safe to re-run.

| Script | Purpose |
| --- | --- |
| `python3 tools/build_index.py` | Rebuilds `assets/search-index.json` and `all-dj-guides.html` from the published pages. Run after adding, renaming or retitling a page. |
| `python3 tools/redesign_pass.py` | Applies the shared shell (header, footer, breadcrumbs, hero layout, search dialog) to pages that predate it. |
| `python3 tools/dedupe_filler.py` | Collapses duplicated generic checklist/filler sections and rewrites the remaining one as the "Before you buy" component. |
| `python3 tools/pick_headings.py` | Converts `Product — Role` headings into the ranked pick heading component. |
| `python3 tools/buy_rows.py` | Rewrites repetitive "Check current prices" strips into the compact buy bar. |
| `python3 tools/hero_cta.py` | Keeps hero action rows section-specific. |

## Checks

```bash
python3 tools/check_site.py            # links, alt text, ids, shell, JSON-LD, assets
python3 tests/check_site_structure.py  # nesting, ItemList vs visible headings, internal copy
```

`tests/ga4-*.test.sh` cover the consent-gated analytics loader and need a local
Chromium; they are not required for content changes.

## Editing conventions

- Prices always carry the month they were checked and the kind of source used.
  Never present a researched figure as a live quote.
- Hands-on language is allowed when it is true. Do not invent measurements,
  test rigs, scores or benchmarks to sound authoritative.
- Images are editorial photography or credited Commons photos of the actual
  product. Illustrative photos are labelled as illustrative in the caption.
- Every buying page answers: who it is for, what it replaces, what you give up
  at the price.

## Deployment

The repository is served as static files (GitHub Pages, `CNAME` → offbeatinc.com).
Releases are handled by the site owner; do not deploy from feature branches.
