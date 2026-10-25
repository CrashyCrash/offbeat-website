/* Offbeat — Interactive Camelot Harmonic Mixing Wheel & Skills Progress Tracker
 *
 * Provides:
 * 1. Interactive Camelot Key Finder: click any key to see smooth blends, energy shifts (+1/-1 step), and dramatic lifts (+2).
 * 2. Web Audio chord harmonic preview: hear compatible vs clashing keys.
 * 3. Six-Week Learning Milestone Tracker: check off weekly goals with localStorage state and progress percentage.
 */
(function () {
  "use strict";

  /* -------------------------------------------------- 1. Milestone Tracker */
  var trackerRoot = document.getElementById("milestone-tracker");
  if (trackerRoot) {
    var STORAGE_KEY = "offbeat.skills.progress";

    var getSaved = function () {
      try {
        var raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
      } catch (e) {
        return {};
      }
    };

    var saveProgress = function (data) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      } catch (e) {}
    };

    var updateProgressUI = function () {
      var saved = getSaved();
      var checkboxes = trackerRoot.querySelectorAll("[data-week-check]");
      var total = checkboxes.length;
      var checkedCount = 0;

      checkboxes.forEach(function (cb) {
        var week = cb.getAttribute("data-week-check");
        var isChecked = !!saved[week];
        cb.checked = isChecked;
        var row = cb.closest(".week-tracker-card");
        if (row) row.classList.toggle("is-completed", isChecked);
        if (isChecked) checkedCount++;
      });

      var pct = total > 0 ? Math.round((checkedCount / total) * 100) : 0;
      var fillEl = trackerRoot.querySelector("[data-progress-fill]");
      var labelEl = trackerRoot.querySelector("[data-progress-label]");
      if (fillEl) fillEl.style.width = pct + "%";
      if (labelEl) labelEl.textContent = checkedCount + " of " + total + " Weeks Completed (" + pct + "%)";
    };

    trackerRoot.addEventListener("change", function (e) {
      if (e.target && e.target.hasAttribute("data-week-check")) {
        var week = e.target.getAttribute("data-week-check");
        var saved = getSaved();
        saved[week] = e.target.checked;
        saveProgress(saved);
        updateProgressUI();
      }
    });

    updateProgressUI();
  }

  /* -------------------------------------------------- 2. Harmonic Mixing Wheel */
  var wheelRoot = document.getElementById("camelot-tool");
  if (!wheelRoot) return;

  var CAMELOT_DATA = {
    "1A": { standard: "A♭ minor (G♯m)", relative: "1B", standardRel: "B Major", boost: "2A", drop: "12A", lift: "3A", rootFreq: 207.65, relFreq: 246.94 },
    "2A": { standard: "E♭ minor (D♯m)", relative: "2B", standardRel: "F♯ Major (G♭)", boost: "3A", drop: "1A", lift: "4A", rootFreq: 155.56, relFreq: 185.00 },
    "3A": { standard: "B♭ minor", relative: "3B", standardRel: "D♭ Major (C♯)", boost: "4A", drop: "2A", lift: "5A", rootFreq: 233.08, relFreq: 277.18 },
    "4A": { standard: "F minor", relative: "4B", standardRel: "A♭ Major", boost: "5A", drop: "3A", lift: "6A", rootFreq: 174.61, relFreq: 207.65 },
    "5A": { standard: "C minor", relative: "5B", standardRel: "E♭ Major", boost: "6A", drop: "4A", lift: "7A", rootFreq: 130.81, relFreq: 155.56 },
    "6A": { standard: "G minor", relative: "6B", standardRel: "B♭ Major", boost: "7A", drop: "5A", lift: "8A", rootFreq: 196.00, relFreq: 233.08 },
    "7A": { standard: "D minor", relative: "7B", standardRel: "F Major", boost: "8A", drop: "6A", lift: "9A", rootFreq: 146.83, relFreq: 174.61 },
    "8A": { standard: "A minor", relative: "8B", standardRel: "C Major", boost: "9A", drop: "7A", lift: "10A", rootFreq: 220.00, relFreq: 261.63 },
    "9A": { standard: "E minor", relative: "9B", standardRel: "G Major", boost: "10A", drop: "8A", lift: "11A", rootFreq: 164.81, relFreq: 196.00 },
    "10A": { standard: "B minor", relative: "10B", standardRel: "D Major", boost: "11A", drop: "9A", lift: "12A", rootFreq: 246.94, relFreq: 293.66 },
    "11A": { standard: "F♯ minor", relative: "11B", standardRel: "A Major", boost: "12A", drop: "10A", lift: "1A", rootFreq: 185.00, relFreq: 220.00 },
    "12A": { standard: "D♭ minor (C♯m)", relative: "12B", standardRel: "E Major", boost: "1A", drop: "11A", lift: "2A", rootFreq: 138.59, relFreq: 164.81 },

    "1B": { standard: "B Major", relative: "1A", standardRel: "A♭ minor", boost: "2B", drop: "12B", lift: "3B", rootFreq: 246.94, relFreq: 207.65 },
    "2B": { standard: "F♯ Major (G♭)", relative: "2A", standardRel: "E♭ minor", boost: "3B", drop: "1B", lift: "4B", rootFreq: 185.00, relFreq: 155.56 },
    "3B": { standard: "D♭ Major (C♯)", relative: "3A", standardRel: "B♭ minor", boost: "4B", drop: "2B", lift: "5B", rootFreq: 277.18, relFreq: 233.08 },
    "4B": { standard: "A♭ Major", relative: "4A", standardRel: "F minor", boost: "5B", drop: "3B", lift: "6B", rootFreq: 207.65, relFreq: 174.61 },
    "5B": { standard: "E♭ Major", relative: "5A", standardRel: "C minor", boost: "6B", drop: "4B", lift: "7B", rootFreq: 155.56, relFreq: 130.81 },
    "6B": { standard: "B♭ Major", relative: "6A", standardRel: "G minor", boost: "7B", drop: "5B", lift: "8B", rootFreq: 233.08, relFreq: 196.00 },
    "7B": { standard: "F Major", relative: "7A", standardRel: "D minor", boost: "8B", drop: "6B", lift: "9B", rootFreq: 174.61, relFreq: 146.83 },
    "8B": { standard: "C Major", relative: "8A", standardRel: "A minor", boost: "9B", drop: "7B", lift: "10B", rootFreq: 261.63, relFreq: 220.00 },
    "9B": { standard: "G Major", relative: "9A", standardRel: "E minor", boost: "10B", drop: "8B", lift: "11B", rootFreq: 196.00, relFreq: 164.81 },
    "10B": { standard: "D Major", relative: "10A", standardRel: "B minor", boost: "11B", drop: "9B", lift: "12B", rootFreq: 293.66, relFreq: 246.94 },
    "11B": { standard: "A Major", relative: "11A", standardRel: "F♯ minor", boost: "12B", drop: "10B", lift: "1B", rootFreq: 220.00, relFreq: 185.00 },
    "12B": { standard: "E Major", relative: "12A", standardRel: "D♭ minor", boost: "1B", drop: "11B", lift: "2B", rootFreq: 164.81, relFreq: 138.59 }
  };

  var selectedKey = "8A"; // Default A minor (club popular)
  var audioCtx = null;

  function playKeyChord(freq, isMinor) {
    var Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    if (!audioCtx) audioCtx = new Ctx();
    if (audioCtx.state === "suspended") audioCtx.resume();

    var now = audioCtx.currentTime;
    var master = audioCtx.createGain();
    master.gain.setValueAtTime(0.001, now);
    master.gain.exponentialRampToValueAtTime(0.12, now + 0.04);
    master.gain.exponentialRampToValueAtTime(0.0001, now + 1.2);
    master.connect(audioCtx.destination);

    // Root, Third (minor or major), Fifth
    var thirdMult = isMinor ? Math.pow(2, 3 / 12) : Math.pow(2, 4 / 12);
    var fifthMult = Math.pow(2, 7 / 12);

    [freq, freq * thirdMult, freq * fifthMult].forEach(function (f) {
      var osc = audioCtx.createOscillator();
      osc.type = "sine";
      osc.frequency.setValueAtTime(f, now);
      osc.connect(master);
      osc.start(now);
      osc.stop(now + 1.3);
    });
  }

  function renderWheel() {
    var data = CAMELOT_DATA[selectedKey] || CAMELOT_DATA["8A"];
    var isMinor = selectedKey.indexOf("A") !== -1;

    var keysA = ["1A","2A","3A","4A","5A","6A","7A","8A","9A","10A","11A","12A"];
    var keysB = ["1B","2B","3B","4B","5B","6B","7B","8B","9B","10B","11B","12B"];

    var html = "";
    html += '<div class="camelot-head">';
    html += '<h3>Harmonic Mixing Key Navigator</h3>';
    html += '<p>Click any key on the wheel to see perfectly compatible mixes, energy boosts, and mood changes.</p>';
    html += '</div>';

    // Key selection grid
    html += '<div class="camelot-grid-wrap">';
    html += '<div class="camelot-row"><span class="camelot-row-label">Minor (A)</span><div class="camelot-btn-group">';
    keysA.forEach(function (k) {
      html += '<button type="button" class="btn-cam' + (k === selectedKey ? " is-selected" : "") + '" data-cam-key="' + k + '"><b>' + k + '</b><span>' + CAMELOT_DATA[k].standard.split(" ")[0] + '</span></button>';
    });
    html += '</div></div>';

    html += '<div class="camelot-row"><span class="camelot-row-label">Major (B)</span><div class="camelot-btn-group">';
    keysB.forEach(function (k) {
      html += '<button type="button" class="btn-cam' + (k === selectedKey ? " is-selected" : "") + '" data-cam-key="' + k + '"><b>' + k + '</b><span>' + CAMELOT_DATA[k].standard.split(" ")[0] + '</span></button>';
    });
    html += '</div></div>';
    html += '</div>';

    // Results card
    html += '<div class="camelot-results">';
    html += '<div class="camelot-current">';
    html += '<div class="cam-now-badge">Current Track Key</div>';
    html += '<h4 class="cam-now-title">' + selectedKey + ' · ' + data.standard + '</h4>';
    html += '<button type="button" class="btn btn-secondary btn-cam-audio" data-play-current>▶ Hear Chord</button>';
    html += '</div>';

    html += '<div class="cam-matches-grid">';

    // 1. Same Key
    html += '<div class="cam-match-card cam-match--same">';
    html += '<span class="cam-match-tag">Perfect Blend</span>';
    html += '<h5>' + selectedKey + ' (' + data.standard.split(" ")[0] + ')</h5>';
    html += '<p>Identical key. Basslines, vocals and melodies lock without musical dissonance.</p>';
    html += '</div>';

    // 2. Relative Key (A <-> B)
    html += '<div class="cam-match-card cam-match--rel">';
    html += '<span class="cam-match-tag">Mood Shift (' + (isMinor ? 'Minor → Major' : 'Major → Minor') + ')</span>';
    html += '<h5>' + data.relative + ' (' + data.standardRel.split(" ")[0] + ')</h5>';
    html += '<p>' + (isMinor ? 'Shifts from dark/moody to bright and uplifting.' : 'Shifts from uplifting to dark/moody.') + '</p>';
    html += '</div>';

    // 3. Energy Boost (+1 Step)
    html += '<div class="cam-match-card cam-match--boost">';
    html += '<span class="cam-match-tag">Energy Boost (+1 Step)</span>';
    html += '<h5>' + data.boost + ' (' + CAMELOT_DATA[data.boost].standard.split(" ")[0] + ')</h5>';
    html += '<p>Steps up energy and raises dancefloor excitement smoothly.</p>';
    html += '</div>';

    // 4. Energy Drop (-1 Step)
    html += '<div class="cam-match-card cam-match--drop">';
    html += '<span class="cam-match-tag">Energy Drop (-1 Step)</span>';
    html += '<h5>' + data.drop + ' (' + CAMELOT_DATA[data.drop].standard.split(" ")[0] + ')</h5>';
    html += '<p>Cool-down transition. Ideal for taking room tension down after a peak.</p>';
    html += '</div>';

    // 5. Energy Lift (+2 Steps)
    html += '<div class="cam-match-card cam-match--lift">';
    html += '<span class="cam-match-tag">Dramatic Energy Lift (+2 Steps)</span>';
    html += '<h5>' + data.lift + ' (' + CAMELOT_DATA[data.lift].standard.split(" ")[0] + ')</h5>';
    html += '<p>Noticeable jump in tension and perceived energy for peak-time moments.</p>';
    html += '</div>';

    html += '</div>'; // cam-matches-grid
    html += '</div>'; // camelot-results

    wheelRoot.innerHTML = html;

    // Attach listeners
    wheelRoot.querySelectorAll("[data-cam-key]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        selectedKey = btn.getAttribute("data-cam-key");
        renderWheel();
        var d = CAMELOT_DATA[selectedKey];
        if (d) playKeyChord(d.rootFreq, selectedKey.indexOf("A") !== -1);
      });
    });

    var playBtn = wheelRoot.querySelector("[data-play-current]");
    if (playBtn) {
      playBtn.addEventListener("click", function () {
        var d = CAMELOT_DATA[selectedKey];
        if (d) playKeyChord(d.rootFreq, selectedKey.indexOf("A") !== -1);
      });
    }
  }

  renderWheel();
})();
