# Six Battle Mode follow-ups — verified asset paths and corrected buyer defects

**Owner inputs:** `1A(1).md`, `1B(1).md`, `2A(1).md`, `2B(1).md`, `3A(1).md`, `3B(1).md`. Full independent assessment and source provenance: [Forgotten-Value: follow-up verification](https://github.com/CrashyCrash/Forgotten-Value/blob/main/projects/offbeat-website/evidence/external-research-20261027/FOLLOWUP-6-REPORTS-VERIFIED-20261027.md). This is **documentation-only** (review PR #1045); no images published or buying pages edited.

## Verified manufacturer-photo boundaries (#1042)

- [Official RANE ONE MKII launch](https://www.inmusicbrands.com/press/one-mk2/) and [Numark Party Mix III/MixTrack Go launch](https://www.inmusicbrands.com/press/party-mix-mixtrack-go/) link public high-resolution media folders. **Download access != permission** to republish next to monetized affiliate links. Model identity must match the particular product launch; e.g., RANE ONE MKII is not original ONE.
- [inMusic web terms](https://www.inmusicbrands.com/terms-of-use/) require express prior written consent for unlicensed commercial display/distribution of their website content; [AlphaTheta terms](https://alphatheta.com/en/company/terms-of-use/) ask for consent for reproducing their site content, subject to legal exceptions. Neither source defeats the rights of a separate independent CC/Pexels photographer.
- [inMusic press contact](https://www.inmusicbrands.com/press/): `inmusic@jessuppr.com` — **not** a grant or the confirmed authority to license every third-party photographer's work. Written clearance for independent commercial editorial use, image transformations and affiliate adjacency remains **OPEN**.
- External report `1A(1)` overstates that all product images adjacent to affiliate links are intrinsically prohibited/resale; apply only actual covered terms and distinct independent licenses.

## Six Pexels source URLs genuinely recovered (#1042)

All six source pages independently opened and showed the same reported photographer, license and pixel dimensions. [Pexels' current published license](https://www.pexels.com/license/) permits website use, modification, resizing and cropping without mandatory attribution, but no implication of endorsement and no blanket rights to third-party trademarks/identifiable subjects.

| ID | Exact source URL | Photographer | Original px | Suitable editorial purpose |
|---|---|---|---|---|
| `17976974` | https://www.pexels.com/photo/black-laptop-and-mixer-17976974/ | Prajwal | 2984×4032 | Portrait/mobile DJ controller+laptop, poor wide hero |
| `17858169` | https://www.pexels.com/photo/dj-using-sound-mixer-and-laptop-17858169/ | Oliver Morgan Media | 5785×3857 | Generic controller+laptop techniques, no model-specific caption |
| `4062561` | https://www.pexels.com/photo/dj-with-mixer-controller-in-night-club-4062561/ | Erik Mclean | 5472×3648 | General DJ software/club workflow; check stock saturation |
| `27495246` | https://www.pexels.com/photo/a-laptop-and-a-mixer-on-a-table-27495246/ | Giuseppe Di Maria | 6000×4000 | Production workstation; bright, mobile crop review needed |
| `5949083` | https://www.pexels.com/photo/a-dj-using-an-audio-mixer-inside-a-dark-room-5949083/ | Elviss Railijs Bitāns | 5184×3456 | Cueing/headphone technique; warm/red palette |
| `7523439` | https://www.pexels.com/photo/person-playing-dj-mixer-7523439/ | Gigxels com | 4330×2887 | General turntable/vinyl explanation, verify composition |

These are **EDITORIAL** photo leads, not verified photos of XDJ-AZ, PRIME GO+, CDJ-3000, etc. Download URLs from `2B(1).md` remain source-file leads; only Pexels per-photo page + license provides rights evidence. No change to current website until crop, duplicate and context QA.

## Reproduce/correct actual production buyer defects (#1043)

Independently compared source of `CrashyCrash/offbeat-website` `main` at **`bad6e15f95041912d4590cbae2301c8ab664ac86`**, not the cumulative Arena fork PR #10/#12. The source contains:

1. `beginner-dj-setup-guide-2026.html`: FLX4+HD25 starter card CTA points to `https://www.amazon.com/s?k=powered+DJ+monitor+speakers&tag=offbeatdj-20` — wrong *search category*, not a known retailer stock/redirect failure.
2. `best-dj-monitor-speakers.html`: KRK ROKIT 5 G4 CTA points correctly to `https://www.amazon.com/s?k=KRK+Rokit+5+G4&tag=offbeatdj-20`. **RETRACT previous KRK→Yamaha mismatch assertion**; Yamaha buttons independently exist on the page but do not make the KRK CTA wrong.
3. `pioneer-ddj-flx4-vs-flx6.html`: falsely says FLX4 has no mic, FLX6-GT has aux/external inputs and allows two laptops/CDJs routed as external sources. Official controller I/O disproves this.
4. `pioneer-ddj-flx4-review.html`: misleading `2.8kg` vs manufacturer weight, unverified `1/4 turn` recessed jog-screw adjustment, and Serato DJ Lite Stems incorrectly presented as a Pro purchase benefit. Remove hardware-adjustment claim pending actual manual evidence.
5. `best-dj-headphones-2026.html`: labels ATH-M50x **99 dB/mW sensitivity** as **maximum SPL**, including visible FAQ.
6. `best-budget-dj-equipment.html`: structured top pick FLX4 but bottom line recommends older archived DDJ-400 and sends to DDJ-400 search; must align intended buyer recommendation, not automatically call the link technically broken.

Verify against manufacturer references from [issue #1043](https://github.com/CrashyCrash/offbeat-website/issues/1043), then create exact-file minimal review fix with FAQ/JSON-LD alignment and real browser confirmation. **Do not edit the already-correct KRK link; do not claim live production source equals newer Arena dev branches.**

### Next real deliverables

- **[#1042](https://github.com/CrashyCrash/offbeat-website/issues/1042):** deduplicate and visually review the six Pexels heroes; select 2–3 genuine improvements with source/credits and 390/1440px QA on review branch.
- **[#1043](https://github.com/CrashyCrash/offbeat-website/issues/1043):** independently fix/accept confirmed live buyer misinformation; prioritize wrong starter CTA, controller input specifications and unsafe jog-screw suggestions.
- **Do not** continue overlapping broad external image/web research; the interrupted local OpenCode task remains deliberately deferred until owner asks to resume. No production merge/deploy without owner visual acceptance.
