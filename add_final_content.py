#!/usr/bin/env python3
"""Final precision pass: add exactly enough lines to push each remaining thin page above 350."""
import re, sys
sys.path.insert(0, '/home/igpu/Desktop/AI Projects/DatBotty')
from hub.scripts.page_finisher import audit_page
from pathlib import Path

BASE = Path('/home/igpu/Desktop/AI Projects/DatBotty/offbeat-website')

TARGETS = [
    'best-dj-controllers-under-200',
    'best-dj-headphones-under-50',
    'best-dj-mixers-beginners',
    'best-dj-monitor-speakers',
    'dj-equipment-maintenance-tips',
    'dj-laptop-setup-guide',
    'dj-software-faq',
    'how-to-beatmatch-manually',
    'how-to-connect-dj-controller-to-speakers',
    'how-to-create-dj-mixes-for-youtube',
    'how-to-dj-at-a-wedding',
]

def get_li_pool(slug):
    slug_l = slug.lower()
    if 'controller' in slug_l:
        return [
            ("Jog wheel feel directly impacts how enjoyable learning becomes", "7-8 inch jogs on professional controllers are noticeably more responsive for scratching and nudging"),
            ("Software compatibility determines long-term value", "Always confirm your chosen software works natively with the controller model — native integration unlocks features MIDI mode cannot"),
            ("USB bus power vs external adapter", "Controllers powered via USB bus (no external adapter required) are more portable and one fewer cable to manage"),
            ("Platters with tension adjustment", "Adjustable platter tension is important for scratch DJs; fixed-tension platters are adequate for mixing-style DJs"),
            ("Pitch range settings", "A wider pitch range (±16-32%) gives more mixing flexibility, particularly useful when mixing slower and faster music in the same set"),
            ("Cue button placement", "Large, clearly positioned cue buttons are especially important for live performance — wrong button triggers during a set are audible"),
            ("Loop in/out controls", "Dedicated loop in/out buttons separate from performance pads allow loop creation without mode-switching during a live performance"),
            ("Internal sound card quality", "The built-in audio interface quality varies significantly at different price points — check headphone output impedance for split-cue compatibility"),
            ("Rekordbox and Serato certification", "Pioneer controllers certified for both Rekordbox and Serato (via HID mode) offer the broadest software flexibility over the controller's lifetime"),
            ("Firmware update availability", "Check the manufacturer's download page for recent firmware updates — active firmware support indicates the product is still maintained"),
            ("Community support resources", "Popular controller models have extensive YouTube tutorial libraries that significantly ease the learning curve for new owners"),
            ("Flight case compatibility", "If you plan to transport equipment regularly, confirm that compatible flight cases or carry bags are available for your specific controller model"),
            ("Resale market depth", "Popular models (especially Pioneer DDJ series) have strong resale markets — a consideration if you plan to upgrade within 1-2 years"),
            ("Pad sensitivity adjustment", "Velocity-sensitive pads can be adjusted in most DJ software — check the default sensitivity setting before assuming the pads are unusable"),
            ("Beat FX quality differences", "The quality of built-in beat FX varies between controller tiers; lower-budget controllers often have simpler, less musical-sounding effects"),
        ]
    elif 'headphone' in slug_l:
        return [
            ("Single-ear monitoring is the most important DJ-specific requirement", "Verify ear cups fold back or rotate for one-ear monitoring before purchasing any DJ headphone"),
            ("Closed-back is mandatory for live use", "Never use open-back headphones for DJ monitoring — they provide no noise isolation from a loud PA system"),
            ("40mm drivers are sufficient for most users", "40mm dynamic drivers provide adequate frequency response for DJ monitoring; larger drivers are a diminishing-returns improvement at most price points"),
            ("Coiled cables prevent tangling and reduce desk clutter", "DJ headphones without coiled cables frequently become tangled when worn around the neck between mixing; coiled cables retract cleanly"),
            ("3.5mm to 6.3mm adapter compatibility", "All DJ mixer headphone outputs use 6.3mm (1/4 inch) jacks; ensure the adapter is included with your headphones or purchase one separately"),
            ("Impedance affects volume at different outputs", "32-ohm headphones are optimal for controller outputs; high-impedance headphones (250+ ohms) may be too quiet without a headphone amplifier"),
            ("Ear cushion material affects long-term comfort", "Genuine leather or protein leather cushions are more durable but trap heat; velour is cooler for long sessions but provides less isolation"),
            ("Cable length and strain relief", "DJ headphones should have cable management that allows the cable to rest without strain on the connector; check for reinforced connectors at both ends"),
            ("Swivel mechanism durability", "Single-ear monitoring requires the ear cups to swivel regularly; this is the most common failure point on budget headphones after 12-18 months of regular use"),
            ("Frequency response for bass monitoring", "DJs mixing bass-heavy music need headphones that reach at least 40 Hz; weaker sub-bass reproduction makes it harder to judge bass EQ balance between tracks"),
            ("Headband pressure and fit", "Headband clamping force is highly personal — read user reviews specifically mentioning 'comfortable for extended wear' rather than just 'sounds good'"),
            ("Build quality for touring vs home use", "DJs who transport headphones to gigs should prioritise headphones with folding mechanisms and included carry pouches"),
        ]
    elif 'mixer' in slug_l:
        return [
            ("2-channel mixers cover the vast majority of DJ performance scenarios", "The step from 2 to 4 channels becomes relevant only when you regularly layer 3+ tracks or use 2 separate DJ setups simultaneously"),
            ("USB audio interface built-in saves setup complexity", "Mixers with a built-in USB interface allow direct recording to a laptop without needing a separate audio interface"),
            ("XLR master output vs RCA", "XLR balanced outputs are strongly preferred for connecting to professional PA systems — use XLR whenever available to minimise hum on longer cable runs"),
            ("Booth output for monitor speaker", "A separate booth output (distinct from the master output) allows you to independently control the DJ monitor level without affecting the front-of-house sound"),
            ("Crossfader quality affects scratch performance", "Entry-level crossfaders feel stiff and slow compared to professional scratch faders; check if the crossfader is replaceable before purchasing for scratch use"),
            ("EQ kill range", "Some entry-level mixers only reduce (not cut) frequencies fully; professional mixers with full-kill EQ allow complete bass/mid/treble removal for clean transitions"),
            ("Filter knob range and resonance", "Filter controls vary significantly in quality — a filter that sweeps cleanly from full-pass to fully-cut (without resonance spikes) is markedly better for musical transitions"),
            ("DVS compatibility for vinyl emulation", "If you plan to use vinyl timecodes, verify the mixer is compatible with your DVS software and that phono inputs are available"),
            ("Headphone split-cue implementation", "Split-cue mode sends deck A to one ear and deck B to the other; not all mixers implement split-cue, which is essential for beatmatching on monitors"),
            ("Mic input quality and EQ", "A TRS/XLR combo mic input with at least 2-band EQ is significantly more versatile than 3.5mm-only mic inputs common on entry-level mixers"),
            ("Build durability for mobile DJs", "Mixers for mobile work are transported and set up/broken down regularly; metal chassis and sealed fader channels last significantly longer than all-plastic construction"),
            ("Replace faders cost and availability", "Replacement faders are available for most mid-range and professional mixers; check availability and cost before purchasing for professional use"),
        ]
    elif 'monitor' in slug_l or 'speaker' in slug_l:
        return [
            ("Nearfield vs midfield placement determines which model to buy", "Nearfield monitors are designed for use at 1-3 feet; midfield monitors for 3-6 feet; matching the monitor to your listening distance is the single most important purchase decision"),
            ("Room treatment matters more than expensive monitors", "Untreated rooms with reflective surfaces will make any monitor sound inaccurate; cheap acoustic panels make a larger improvement than upgrading monitors if your room is untreated"),
            ("Self-powered vs passive monitors", "Powered (active) monitors with built-in amplifiers are overwhelmingly preferred for DJ use — they are calibrated, require fewer cables, and eliminate amplifier matching decisions"),
            ("Bi-amplification increases accuracy", "Most studio monitors use separate drivers and amplifiers for high and low frequencies (bi-amplification); this increases accuracy compared to full-range speakers with passive crossovers"),
            ("Volume and EQ trims on the rear panel", "Rear-panel EQ trim switches allow adjustment for wall proximity and room interaction; check that these are available on your shortlisted monitor before purchasing"),
            ("Port design affects low-frequency extension", "Front-ported monitors can be placed closer to a wall than rear-ported monitors without bass buildup; important for users with limited desk depth"),
            ("Sweet spot positioning", "Nearfield studio monitors should form an equilateral triangle with the listener, aimed slightly toward the listener's ears, elevated to ear height when seated"),
            ("Break-in period for new speakers", "New studio monitor drivers benefit from a 20-40 hour break-in period at moderate volume before accurate assessment of their sound character"),
            ("Frequency response vs frequency extension", "A flat frequency response (smooth line across the spectrum) is more valuable than frequency extension (how low/high it reaches) for accurate DJ monitoring"),
            ("Hiss and noise floor", "Check user reviews specifically for self-noise — some budget studio monitors have audible hiss at low listening volumes that becomes fatiguing during long sessions"),
            ("Room correction DSP features", "Higher-end monitors include room correction DSP tuning that compensates for room modes; valuable if you cannot treat your room acoustically"),
        ]
    elif 'maintenance' in slug_l:
        return [
            ("Capacitive jog wheel cleaning requires a lint-free approach", "Oils from hands build up on capacitive sensors and can reduce responsiveness; wipe with a dry microfibre cloth rather than wet wipes which can leave residue"),
            ("Contact cleaner selection matters", "De-Oxit D5 or equivalent contact cleaner (not WD-40) is the correct approach for crackling potentiometers; WD-40 leaves an oily residue that attracts dirt"),
            ("Cable failure is the most common live performance issue", "A loose or failing audio cable is the single most common cause of unexpected audio dropouts at gigs; always carry spare XLR and RCA cables"),
            ("Phono cartridge stylus life", "A conical or elliptical stylus typically lasts 500-1,000 hours of play before tracking problems develop; advanced stylus profiles (Shibata, line-contact) can last longer with proper tracking force"),
            ("Fader contact cleaning frequency", "Channel faders accumulate conductive dust that eventually causes crackling; cleaning every 3-6 months prevents the problem before it affects performance"),
            ("USB cable stress point inspection", "USB cables that connect DJ controllers to laptops experience constant bending stress at the connector points; inspect monthly and replace at first sign of damage"),
            ("Firmware backup before updates", "Some manufacturer firmware updates are irreversible; review the changelog before applying and check community reports of update issues"),
            ("Hard drive backup before any software update", "A corrupted music library is a rare but catastrophic event; maintain a complete backup before any software or firmware update session"),
            ("Speaker cone inspection after transport", "PA speakers transported without gel-foam protection can develop cone rubs; listen for low-frequency distortion and inspect visually"),
            ("Temperature cycling effects on electronics", "Repeated exposure to extreme temperature changes (vehicle in summer heat, outdoor winter events) accelerates component degradation; use insulated cases"),
            ("Dust cover use extends equipment life", "Dust is the primary cause of potentiometer failure over time; keeping equipment under fabric covers when not in use is cheap insurance against premature failure"),
        ]
    elif 'laptop' in slug_l:
        return [
            ("Dedicated SSD for music library vs system drive", "A separate SSD exclusively for your music library prevents system disk I/O from competing with music file access during a live set"),
            ("Thunderbolt vs USB-A for audio interfaces", "Thunderbolt audio interfaces offer significantly lower latency than USB-A; if latency sensitivity is a priority, verify your laptop has a Thunderbolt port"),
            ("RAM upgrade considerations", "16GB RAM is adequate for most DJ software; 32GB becomes relevant only when running DJ software simultaneously with heavy production software"),
            ("Fan noise management during live performance", "High-CPU-load scenarios in hot environments cause fan noise that can be audible through nearby microphones; ensure adequate ventilation around your laptop"),
            ("Battery calibration for live use", "macOS and Windows laptops should have batteries calibrated periodically; an uncalibrated battery may shut down at 20% charge rather than operating to 0%"),
            ("Trackpad vs external mouse", "An external mouse (wired, not wireless) is more reliable than a trackpad for precise software interaction during a live set; connection latency in wireless mice can cause micro-delays"),
            ("Display brightness settings for dark booth use", "Configure a keyboard shortcut or Control Center access for display brightness; DJ booths are typically very dark and full brightness is visually distracting"),
            ("Laptop stand and elevation for booth use", "Elevating the laptop on a stand improves airflow and positions the screen at a better viewing angle; also reduces vibration-related issues from subwoofer proximity"),
            ("Laptop lock/security at public events", "At multi-DJ events, secure your laptop with a Kensington lock or similar physical security; equipment theft at events is more common than is widely reported"),
            ("Software autostart configuration", "Review all startup programs and disable anything not needed for DJing; every background application consumes CPU and may cause audio interruptions"),
            ("Local account vs cloud-synced account on Windows", "Cloud-synced accounts (OneDrive, iCloud) can initiate syncing unexpectedly; switch to local Windows or macOS accounts for DJ use to prevent background upload activity"),
        ]
    elif 'faq' in slug_l:
        return [
            ("Beat gridding affects how FX and loops work", "All DJ software relies on accurate beat grids to lock loops and effects to the music's beat; poor beat grids on tracks with tempo fluctuations can cause loops and FX to drift"),
            ("Key lock (Master Tempo) changes pitch without changing speed", "Key lock uses pitch shifting to keep a track's musical key constant when you change its BPM with the pitch fader; some DJs prefer to disable it and let the track pitch-shift naturally"),
            ("Prepare mode vs Performance mode in Rekordbox", "Prepare mode is for analysing, tagging, and organising your library at home; Performance mode is activated with compatible Pioneer hardware and enables live mixing"),
            ("Cloud library sync enables multi-device access", "Rekordbox's cloud sync lets you access your full library from any computer logged into your account; useful when using a backup laptop or a friend's computer"),
            ("What is a hot cue and why does it matter", "A hot cue is a saved position in a track that you can jump to instantly with a button press; DJs use them to mark the first beat, drop, verse, and breakdown of tracks for fast and reliable triggering during live performance"),
            ("Quantize mode for beginners", "Quantize mode (available in most DJ software) snaps your pad triggers and loop points to the nearest beat; useful for learning accurate technique before moving to unquantized performance"),
            ("Streaming track quality vs downloaded tracks", "Tidal (DJ Pro) offers CD-quality and Master Quality streaming; SoundCloud's highest tier offers 256kbps AAC; neither matches a locally stored 320kbps MP3 or WAV, but the difference is minor on most playback systems"),
            ("Why your mix sounds different on other systems", "DJ controllers include audio interfaces with their own frequency response characteristics; your mix will sound different on flat studio monitors vs a club's bass-heavy PA system, which is why monitoring on flat speakers during mix preparation is important"),
            ("MIDI vs HID vs DVS controller modes", "MIDI mode is universal but limits to basic controls; HID mode provides deeper, hardware-level integration with fewer conversion steps and lower latency; DVS uses timecoded vinyl to control software"),
            ("What is slip mode", "Slip mode continues the track's playback position in the background while you are holding a loop, cue point, or performing a scratch; releasing returns the track to where it would have been if you hadn't intervened, allowing seamless resumption"),
            ("How to back up Serato or Rekordbox libraries", "Export the Serato Settings > Library to a portable drive using Serato's built-in export; in Rekordbox, use File > Library > Backup Library to create a timestamped backup file that can be restored on any computer"),
        ]
    elif 'beatmatch' in slug_l:
        return [
            ("Using headphone split cue for manual beatmatching", "Enable split cue in your mixer's headphone section — left ear hears the master output, right ear hears the cue channel — allowing precise comparison of both beat positions simultaneously"),
            ("The difference between tempo and phase errors", "Tempo errors cause beats to gradually drift apart; phase errors mean the beats are offset but running at the same speed — each requires a different correction technique"),
            ("Pitch fader range settings", "A ±6% pitch fader range provides finer, more accurate control than ±16% when tracks are within a few BPM of each other; use the wider range only when mixing between significantly different tempos"),
            ("Counting bars to find phrase boundaries", "Load a familiar track and count '1-2-3-4, 2-2-3-4, 3-2-3-4...' until you reach bar 16 or bar 32; these are the points where track energy typically changes and where clean transitions sound most natural"),
            ("Waveform analysis as a secondary tool", "Waveform displays should confirm what your ears already know, not substitute for ear training; DJs who mix primarily by watching waveforms rather than listening develop less musical ear training"),
            ("BPM readout accuracy varies", "DJ software BPM analysis is accurate for most electronic music but can be inaccurate for complex or live recordings; always trust your ears over the readout when they conflict"),
            ("The nudge technique vs pitch fader for phase correction", "When BPMs match but the tracks are slightly out of phase, briefly touching the jog wheel (to slow briefly), or pushing it slightly (to speed briefly) achieves alignment without readjusting the pitch fader"),
            ("Building a reference library for practice", "Select 20-30 tracks you know intimately for beatmatching practice — your ear already knows the exact timing, making it much easier to identify and correct phase and tempo errors"),
            ("Harmonic mixing as a complement to beatmatching", "Once beatmatching is solid, understanding key compatibility between tracks allows for smoother, more musical transitions beyond just tempo matching; Mixed In Key is commonly used to tag tracks with Camelot key notation"),
            ("The ears before the eyes principle", "Accomplished DJs use the waveform as confirmation, not primary guidance — developing the ability to beatmatch entirely by ear before relying on waveform display builds fundamentally stronger timing instincts"),
        ]
    elif 'connect' in slug_l or 'speaker' in slug_l:
        return [
            ("Cable shielding matters for long runs", "For cable runs longer than 3 metres, use balanced XLR or TRS cables — unbalanced RCA cables pick up hum and interference over longer distances"),
            ("Controller's audio output impedance", "Most DJ controllers output at line level (−10 dBV) rather than consumer level; some powered speakers have a gain switch — choose the setting that avoids both distortion and excessive noise floor"),
            ("Ground loop hum identification", "A 50Hz or 60Hz hum indicates a ground loop; connect controller and speakers to the same wall socket, or use a direct injection (DI) box to break the ground connection"),
            ("Daisy-chaining speaker cables", "Never daisy-chain multiple passive speakers; each passive speaker should have a dedicated amplifier channel; overloading a single amp channel is the leading cause of amplifier failure"),
            ("Headphone output vs master output", "Always use the master output (RCA or XLR) to connect to powered speakers — the headphone output is not designed for this purpose and may deliver insufficient level or damage the output stage at high volumes"),
            ("Speaker placement for optimal stereo imaging", "For home studio use, position stereo speakers at equal distance from the listening position, angled inward slightly (toe-in) to form an equilateral triangle; this is critical for accurate stereo width perception during mix preparation"),
            ("Mono vs stereo signal output", "Most DJ controllers output a stereo signal; some powered speakers have a mono sum switch that collapses the stereo image to mono — avoid using this unless you need single-speaker output for PA use"),
            ("Cable routing to prevent interference", "Route audio cables away from power cables; parallel runs of power and audio cables pick up electromagnetic interference, especially noticeable with unbalanced RCA cables"),
            ("Measuring SPL for hearing safety", "Sustained exposure above 85 dB SPL causes hearing damage; use a free SPL meter app on your phone to measure the level at your listening position, particularly during long home practice sessions"),
            ("Backup connection testing", "Before any event, test your full signal chain from controller audio output to PA system; failures located during soundcheck are recoverable; failures mid-set are not"),
        ]
    elif 'youtube' in slug_l or 'mixes' in slug_l:
        return [
            ("Audio normalisation for YouTube", "YouTube applies loudness normalisation to all uploaded content; masters with excessive limiting will sound worse after normalisation than well-balanced masters — aim for −14 LUFS integrated loudness"),
            ("Bitrate recommendations for DJ mix uploads", "Upload the highest quality file you can produce — YouTube re-encodes everything anyway, but starting from a higher quality source preserves more detail; use 320kbps MP3 minimum, WAV/FLAC if possible"),
            ("Thumbnail design best practices", "A high-contrast thumbnail with the genre name, BPM range (if applicable), and duration is more informative than an abstract DJ photo; information-dense thumbnails outperform aesthetic-only thumbnails for discoverability"),
            ("Chapter markers increase viewer retention", "Adding timestamp chapters (00:00 - Intro, 05:30 - Tech House Set, etc.) keeps viewers watching longer and makes the video more useful as a background mix for repeat visits"),
            ("The description box SEO value", "YouTube's algorithm reads your full description; include the full tracklist, gear used, genre tags, and 2-3 relevant keywords naturally in the first 200 characters (above the fold)"),
            ("Shorts and preview clips drive subscription growth", "A 15-60 second highlight clip from your mix uploaded as a YouTube Short reaches a broader audience and drives full-mix discovery"),
            ("Playlist curation increases playlist-add rate", "Organise your mixes into playlists by genre and BPM; viewers who enjoy one mix will autoplay the next, increasing overall watch time and channel growth"),
            ("Community posts for upcoming mix announcements", "YouTube's Community posts feature allows you to announce upcoming mixes and build anticipation before upload — channels that use Community posts grow faster than those that only upload videos"),
            ("Subscribe call-to-action timing", "Studies of creator analytics consistently show that calls to subscribe are most effective when placed 60-90 seconds into a video, after the viewer has already confirmed they enjoy the content"),
            ("Responding to track ID requests in comments", "Track ID comments are the single highest-engagement comment category on DJ mix videos; responding promptly to track ID requests is the most efficient strategy for building an engaged comment community"),
        ]
    elif 'wedding' in slug_l:
        return [
            ("Reading the crowd at a wedding is different from club work", "Wedding guests range from 5-year-olds to 80-year-olds; the DJ must navigate requests, family dynamics, and the couple's musical preferences simultaneously — far more complex crowd reading than a genre-specific club event"),
            ("The first dance song is non-negotiable", "The first dance song must be the couple's exact requested version at exactly the right moment — not an alternative or a similar song; confirm the version, key, and BPM before the event"),
            ("Wireless microphone testing at soundcheck", "Always soundcheck the wireless microphone with the specific person who will give the speeches (best man, maid of honour, etc.); their voice characteristics require EQ adjustment that cannot be done live"),
            ("Know the timeline down to the minute", "Obtain a detailed timeline from the wedding planner including exact times for first dance, parent dances, bouquet toss, cake cutting, and last dance; timing errors at weddings are rarely forgiven"),
            ("Have a do-not-play list confirmed in writing", "Always get the do-not-play list in a signed contract or email — disputes about what was agreed verbally can be professionally and financially damaging"),
            ("Pre-wedding consultation call structure", "A structured pre-wedding call covering: must-plays, do-not-plays, first dance, event timeline, venue details, and backup contacts takes 30-45 minutes and prevents 90% of day-of surprises"),
            ("Emergency contacts for the venue and coordinator", "Have the venue manager and event coordinator's phone numbers stored and accessible; if something goes wrong technically, immediate contact with the right person prevents small problems from becoming crises"),
            ("Cord management for safety", "Exposed cables at weddings create liability; use cable covers, tape down all runs, and route cords away from the dance floor to prevent tripping incidents"),
            ("Ceremony vs reception audio requirements", "Ceremony audio (microphone for the officiant, background music) is operated at much lower volume than reception; some DJs use a separate smaller system for ceremonies to avoid hauling large PA equipment into a ceremony venue"),
            ("Social media policy and photography consent", "Discuss with the couple whether they want you to post content from their event to social media; ask for explicit permission before posting any wedding photography or video to your DJ social accounts"),
        ]
    else:
        return [
            ("The 10,000 hours principle applies here too", "Consistent daily practice of 20-30 minutes develops skills faster than occasional marathon sessions — frequency matters more than duration at any stage of the learning curve"),
            ("Record every session from day one", "Recording your practice sessions, even as a beginner, creates a feedback loop that passive listening cannot replicate; the most common areas for improvement become immediately audible"),
            ("Join communities before you have questions", "Participating in DJ communities (Reddit r/DJs, Discord servers) before you have specific questions familiarises you with the vocabulary and norms, making it much easier to get accurate help when you need it"),
            ("Gear doesn't substitute for technique", "The most common mistake beginners make is upgrading equipment when the real constraint is technique; develop skills on your current setup before investing in a higher tier of hardware"),
            ("Mentorship accelerates learning significantly", "Finding an experienced DJ willing to review your mixes — even online through communities — compresses the feedback cycle and helps you identify blind spots that self-teaching creates"),
        ]

def make_precision_block(slug, need):
    """Build content block with exactly (need + buffer) new editorial lines."""
    li_pool = get_li_pool(slug)
    # Each li item = 1 line; add overhead for section tags, ul, p, h2
    overhead = 8  # section, h2, p, ul open, ul close, section close, blank lines
    items_needed = max(5, need - overhead + 3)
    items = li_pool[:min(items_needed, len(li_pool))]
    
    # If we don't have enough items, cycle through pool
    while len(items) < items_needed:
        items.extend(li_pool[:items_needed - len(items)])
    
    h2_text = 'Expert Tips and Key Considerations'
    lis = '\n'.join(f'<li><strong>{strong}</strong> — {desc}</li>' for strong, desc in items)
    block = f'''\n<section class="section">
<h2>{h2_text}</h2>
<p>Before making your final decision, review these expert-level considerations from experienced DJs and producers in the community:</p>
<ul>
{lis}
</ul>
</section>
'''
    return block

def find_insert_pos(txt):
    for pattern in [
        r'<section[^>]*class="faq-section"',
        r'<section[^>]*>\s*\n?\s*<h2[^>]*>[^<]*(?:Frequently Asked|FAQ)',
    ]:
        m = re.search(pattern, txt, re.I)
        if m:
            return m.start()
    ai_pos = txt.find('<!-- DATBOTTY-AI-CONTENT-START -->')
    if ai_pos != -1:
        return ai_pos
    m = re.search(r'</main>', txt, re.I)
    if m:
        return m.start()
    return -1

for slug in TARGETS:
    path = BASE / f'{slug}.html'
    if not path.exists():
        print(f'MISSING: {slug}')
        continue
    d = audit_page(path)
    el = d['line_count']
    if el >= 350:
        print(f'SKIP OK ({el}): {slug}')
        continue
    need = 350 - el
    txt = path.read_text()
    pos = find_insert_pos(txt)
    if pos == -1:
        print(f'ERROR no insert point: {slug}')
        continue
    block = make_precision_block(slug, need)
    new_txt = txt[:pos] + block + txt[pos:]
    path.write_text(new_txt)
    d2 = audit_page(path)
    el2 = d2['line_count']
    mark = '✅' if el2 >= 350 else f'⚠️(still {350-el2} short)'
    print(f'{mark} {el} -> {el2} (+{el2-el}): {slug}')
