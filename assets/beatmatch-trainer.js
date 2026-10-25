/* Offbeat — browser beatmatching trainer.
 *
 * Provides:
 * 1. Step-by-Step Guided Practice Mode (Untimed with real-time coaching feedback).
 * 2. 45-Second Timed Challenge Drill with scoring & personal bests.
 * 3. Genre tempo presets (House 124, Techno 132, D&B 174, Nu-Disco 115).
 * 4. Web Audio dual-drum synthesizer with stereo split cueing and distinct deck timbres.
 * 5. Interactive rotating vinyl platters, drag nudging, and tactile CUE drops.
 */

(function () {
  "use strict";

  var root = document.getElementById("trainer");
  if (!root) return;

  var el = {
    start: root.querySelector("[data-start]"),
    stop: root.querySelector("[data-stop]"),
    stage: root.querySelector("[data-stage]"),
    clock: root.querySelector("[data-clock]"),
    score: root.querySelector("[data-score]"),
    verdict: root.querySelector("[data-verdict]"),
    best: root.querySelector("[data-best]"),
    pitch: root.querySelector("[data-pitch]"),
    pitchValue: root.querySelector("[data-pitch-value]"),
    bpmA: root.querySelector("[data-bpm-a]"),
    bpmB: root.querySelector("[data-bpm-b]"),
    drift: root.querySelector("[data-drift]"),
    driftBar: root.querySelector("[data-drift-bar]"),
    driftReadout: root.querySelector(".readout--drift"),
    status: root.querySelector("[data-lock-status]"),
    nudgeBack: root.querySelector("[data-nudge-back]"),
    nudgeFwd: root.querySelector("[data-nudge-fwd]"),
    hide: root.querySelector("[data-hide]"),
    reset: root.querySelector("[data-reset]"),
    difficulty: root.querySelector("[data-difficulty]"),
    genreSelect: root.querySelector("[data-genre]"),
    modeTabs: root.querySelectorAll("[data-trainer-mode]"),
    liveA: root.querySelector("[data-live-a]"),
    liveB: root.querySelector("[data-live-b]"),
    platterA: root.querySelector("[data-platter-a]"),
    platterB: root.querySelector("[data-platter-b]"),
    cueBtn: root.querySelector("[data-cue]"),
    splitCueBtn: root.querySelector("[data-split-cue]"),
    soloABtn: root.querySelector("[data-solo-a]"),
    soloBBtn: root.querySelector("[data-solo-b]"),
    coachBanner: root.querySelector("[data-coach-banner]"),
    coachTitle: root.querySelector("[data-coach-title]"),
    coachMsg: root.querySelector("[data-coach-msg]"),
    scorecard: root.querySelector("[data-scorecard]"),
    scorecardClose: root.querySelector("[data-scorecard-close]"),
    scorecardRetry: root.querySelector("[data-scorecard-retry]"),
    scorecardCopy: root.querySelector("[data-scorecard-copy]"),
    demoLocked: document.querySelector("[data-demo='locked']"),
    demoDragging: document.querySelector("[data-demo='dragging']"),
    demoRushing: document.querySelector("[data-demo='rushing']")
  };

  var DRILL_DURATION_S = 45;
  var MASTER_BPM = 124.0;
  var LOCK_THRESHOLD_MS = 18;

  var GENRES = {
    house: { name: "House & Tech House", bpm: 124.0 },
    techno: { name: "Peak Time Techno", bpm: 132.0 },
    dnb: { name: "Drum & Bass", bpm: 174.0 },
    disco: { name: "Nu-Disco / Funk", bpm: 115.0 }
  };

  var state = {
    running: false,
    mode: "practice", // "practice" (untimed) or "drill" (45s timed)
    genre: "house",
    bpmA: MASTER_BPM,
    baseBpm: MASTER_BPM,
    bpmB: MASTER_BPM,
    pitch: 0,
    nudge: 0,
    posA: 0,
    posB: 0,
    beatA: 0,
    beatB: 0,
    scheduledA: -1,
    scheduledB: -1,
    locked: false,
    lockedMs: 0,
    totalMs: 0,
    currentStreakMs: 0,
    bestStreakMs: 0,
    offsets: [],
    endsAt: 0,
    lastAudio: 0,
    lastFrame: 0,
    raf: null,
    timer: null,
    ctx: null,
    demoTimer: null,
    splitCue: false,
    soloA: false,
    soloB: false,
    rotA: 0,
    rotB: 0,
    isDraggingPlatter: false,
    dragStartY: 0
  };

  var audio = {
    master: null,
    chanA: null,
    chanB: null,
    pannerA: null,
    pannerB: null,
    noise: null
  };

  /* ------------------------------------------------------------- Web Audio Engine */
  function noiseBuffer(ctx, seconds) {
    var rate = ctx.sampleRate;
    var len = rate * seconds;
    var buf = ctx.createBuffer(1, len, rate);
    var data = buf.getChannelData(0);
    for (var i = 0; i < len; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    return buf;
  }

  function ensureAudioCtx() {
    if (state.ctx) return state.ctx;
    var AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return null;
    var ctx = new AudioContext();
    state.ctx = ctx;
    audio.noise = noiseBuffer(ctx, 2.0);

    var master = ctx.createGain();
    master.gain.value = 0.85;
    master.connect(ctx.destination);
    audio.master = master;

    var chanA = ctx.createGain();
    var chanB = ctx.createGain();
    chanA.gain.value = 0.85;
    chanB.gain.value = 0.85;

    if (ctx.createStereoPanner) {
      audio.pannerA = ctx.createStereoPanner();
      audio.pannerB = ctx.createStereoPanner();
      audio.pannerA.pan.value = 0;
      audio.pannerB.pan.value = 0;
      chanA.connect(audio.pannerA).connect(master);
      chanB.connect(audio.pannerB).connect(master);
    } else {
      chanA.connect(master);
      chanB.connect(master);
    }

    audio.chanA = chanA;
    audio.chanB = chanB;
    return ctx;
  }

  function applyAudioRouting() {
    if (!audio.chanA || !audio.chanB) return;
    if (state.soloA) {
      audio.chanA.gain.value = 0.85;
      audio.chanB.gain.value = 0;
    } else if (state.soloB) {
      audio.chanA.gain.value = 0;
      audio.chanB.gain.value = 0.85;
    } else {
      audio.chanA.gain.value = 0.85;
      audio.chanB.gain.value = 0.85;
    }

    if (audio.pannerA && audio.pannerB) {
      if (state.splitCue) {
        audio.pannerA.pan.setValueAtTime(-0.85, state.ctx.currentTime);
        audio.pannerB.pan.setValueAtTime(0.85, state.ctx.currentTime);
      } else {
        audio.pannerA.pan.setValueAtTime(0, state.ctx.currentTime);
        audio.pannerB.pan.setValueAtTime(0, state.ctx.currentTime);
      }
    }
  }

  function kick(ctx, when, gainValue, out, isMaster) {
    var osc = ctx.createOscillator();
    var gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(isMaster ? 160 : 145, when);
    osc.frequency.exponentialRampToValueAtTime(45, when + 0.11);
    gain.gain.setValueAtTime(0.0001, when);
    gain.gain.exponentialRampToValueAtTime(gainValue, when + 0.003);
    gain.gain.exponentialRampToValueAtTime(0.0001, when + (isMaster ? 0.28 : 0.24));
    osc.connect(gain).connect(out);
    osc.start(when);
    osc.stop(when + 0.3);
  }

  function noiseHit(ctx, when, out, options) {
    if (!audio.noise) return;
    var src = ctx.createBufferSource();
    src.buffer = audio.noise;
    var filter = ctx.createBiquadFilter();
    filter.type = options.type || "highpass";
    filter.frequency.value = options.frequency || 6000;
    var gain = ctx.createGain();
    var peak = options.gain || 0.12;
    gain.gain.setValueAtTime(0.0001, when);
    gain.gain.exponentialRampToValueAtTime(peak, when + 0.002);
    gain.gain.exponentialRampToValueAtTime(0.0001, when + (options.decay || 0.06));
    src.connect(filter).connect(gain).connect(out);
    src.start(when);
    src.stop(when + (options.decay || 0.06) + 0.02);
  }

  function hat(ctx, when, out, isOpen) {
    noiseHit(ctx, when, out, {
      type: "highpass",
      frequency: 7500,
      gain: isOpen ? 0.07 : 0.045,
      decay: isOpen ? 0.12 : 0.035
    });
  }

  function snare(ctx, when, out) {
    noiseHit(ctx, when, out, { type: "bandpass", frequency: 1800, gain: 0.14, decay: 0.13 });
  }

  function bassNote(ctx, when, out, freq) {
    var osc = ctx.createOscillator();
    var gain = ctx.createGain();
    osc.type = "triangle";
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.0001, when);
    gain.gain.exponentialRampToValueAtTime(0.055, when + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, when + 0.22);
    osc.connect(gain).connect(out);
    osc.start(when);
    osc.stop(when + 0.24);
  }

  function scheduleBeat(deck, when, bpm) {
    bpm = bpm || (deck === "a" ? state.bpmA : currentBpmB());
    var beat = deck === "a" ? state.beatA : state.beatB;
    var out = deck === "a" ? audio.chanA : audio.chanB;
    var position = ((beat % 4) + 4) % 4;

    if (deck === "a") {
      kick(state.ctx, when, 0.65, out, true);
      if (position === 1 || position === 3) snare(state.ctx, when, out);
      hat(state.ctx, when + 60 / bpm / 2, out, true); // Open offbeat hihat
      bassNote(state.ctx, when + 0.02, out, position % 2 === 0 ? 55 : 65.4);
    } else {
      kick(state.ctx, when, 0.58, out, false);
      if (position === 1 || position === 3) snare(state.ctx, when, out);
      hat(state.ctx, when + 60 / bpm / 2, out, false);
      hat(state.ctx, when + (60 / bpm) * 0.75, out, false);
      bassNote(state.ctx, when + 0.02, out, position % 2 === 0 ? 61.7 : 73.4);
    }
  }

  /* ------------------------------------------------------------- scheduling */
  function advanceClock() {
    var t = state.ctx.currentTime;
    var dt = t - state.lastAudio;
    if (dt > 0 && dt < 1) {
      state.posA += (dt * state.bpmA) / 60;
      state.posB += (dt * currentBpmB()) / 60;
    }
    if (dt > 0) state.lastAudio = t;
    return t;
  }

  function pumpDeck(deck, t, horizon, bpm) {
    var pos = deck === "a" ? state.posA : state.posB;
    var last = deck === "a" ? state.scheduledA : state.scheduledB;
    var period = 60 / bpm;
    var index = Math.ceil(pos);
    if (index <= last) index = last + 1;
    var when = t + (index - pos) * period;
    var guard = 0;

    while (when < horizon && guard < 8) {
      if (deck === "a") state.beatA = index;
      else state.beatB = index;
      scheduleBeat(deck, when, bpm);
      if (deck === "a") state.scheduledA = index;
      else state.scheduledB = index;
      index += 1;
      when += period;
      guard += 1;
    }
  }

  function scheduler() {
    if (!state.running) return;
    var t = advanceClock();
    var horizon = t + 0.16;
    pumpDeck("a", t, horizon, state.bpmA);
    pumpDeck("b", t, horizon, currentBpmB());
  }

  function currentBpmB() {
    var base = state.bpmB;
    if (state.nudge === -1) base *= 0.88;
    if (state.nudge === 1) base *= 1.13;
    return base;
  }

  function phaseMs() {
    if (!state.running) return 0;
    var beats = state.posA - state.posB;
    beats -= Math.round(beats);
    return beats * (60000 / state.bpmA);
  }

  /* -------------------------------------------------------------------- UI */
  function fmt(n, digits) {
    return n.toFixed(digits === undefined ? 1 : digits);
  }

  function setPitch(percent) {
    state.pitch = Math.max(-8, Math.min(8, percent));
    state.bpmB = state.baseBpm * (1 + state.pitch / 100);
    if (el.pitch) el.pitch.value = String(state.pitch);
    if (el.pitchValue) el.pitchValue.textContent = (state.pitch > 0 ? "+" : "") + fmt(state.pitch, 2) + "%";
    if (el.bpmB) el.bpmB.textContent = fmt(state.bpmB, 1);
  }

  function setGenre(genreKey) {
    var g = GENRES[genreKey] || GENRES.house;
    state.genre = genreKey;
    state.bpmA = g.bpm;
    MASTER_BPM = g.bpm;
    if (el.bpmA) el.bpmA.textContent = fmt(state.bpmA, 1);
    if (state.running) {
      stop("manual");
      start();
    }
  }

  /* ---------------------------------------------------------------- Loop */
  function frame(timestamp) {
    if (!state.running) return;
    scheduler();

    var now = timestamp || window.performance.now();
    var delta = state.lastFrame ? now - state.lastFrame : 16;
    state.lastFrame = now;

    var diff = phaseMs();
    var absDiff = Math.abs(diff);
    var bpmDiff = state.bpmA - state.bpmB;
    var absBpmDiff = Math.abs(bpmDiff);

    state.locked = absDiff <= LOCK_THRESHOLD_MS && absBpmDiff <= 0.25;
    state.totalMs += delta;
    if (state.locked) {
      state.lockedMs += delta;
      state.currentStreakMs += delta;
      if (state.currentStreakMs > state.bestStreakMs) state.bestStreakMs = state.currentStreakMs;
    } else {
      state.currentStreakMs = 0;
    }

    if (absDiff < 200) state.offsets.push(absDiff);

    // Update drift readout
    if (el.drift) el.drift.textContent = (diff > 0 ? "+" : "") + Math.round(diff) + " ms";
    if (el.driftBar) {
      var pct = Math.max(-50, Math.min(50, (diff / 250) * 50));
      el.driftBar.style.setProperty("--drift-pct", pct + "%");
      el.driftBar.classList.toggle("is-locked", state.locked);
    }

    // Update score percentage
    if (el.score) {
      var currentScore = state.totalMs > 0 ? Math.round((state.lockedMs / state.totalMs) * 100) : 0;
      el.score.textContent = currentScore + "%";
    }

    // Update Actionable DJ Coach Banner
    updateCoachGuidance(absBpmDiff, bpmDiff, absDiff, diff, state.locked);

    if (el.bpmA) el.bpmA.textContent = fmt(MASTER_BPM, 1);
    if (el.bpmB) el.bpmB.textContent = fmt(currentBpmB(), 1);

    // Waveform beat pulses
    var beatCycleA = Math.floor(state.posA * 2) % 2 === 0;
    var beatCycleB = Math.floor(state.posB * 2) % 2 === 0;
    if (el.liveA) el.liveA.classList.toggle("is-beat", beatCycleA);
    if (el.liveB) el.liveB.classList.toggle("is-beat", beatCycleB);

    // Rotating jog platters
    state.rotA = (state.posA * 90) % 360;
    state.rotB = (state.posB * 90) % 360;
    if (el.platterA) el.platterA.style.transform = "rotate(" + state.rotA.toFixed(1) + "deg)";
    if (el.platterB) el.platterB.style.transform = "rotate(" + state.rotB.toFixed(1) + "deg)";

    // In timed drill mode, check countdown
    if (state.mode === "drill") {
      var remaining = Math.max(0, Math.ceil((state.endsAt - now) / 1000));
      if (el.clock) el.clock.textContent = remaining + "s";
      if (now >= state.endsAt) {
        stop("done");
        return;
      }
    } else {
      if (el.clock) el.clock.textContent = "Guided";
    }

    state.raf = window.requestAnimationFrame(frame);
  }

  function updateCoachGuidance(absBpmDiff, bpmDiff, absDiff, diff, isLocked) {
    if (!el.coachBanner) return;

    if (isLocked) {
      el.coachBanner.className = "coach-banner coach--locked";
      if (el.coachTitle) el.coachTitle.textContent = "🔥 LOCKED IN PERFECT SYNC";
      if (el.coachMsg) el.coachMsg.textContent = "Both kicks hitting together as one tight punch (<18ms). Hold your pitch steady!";
      if (el.status) el.status.innerHTML = '<span class="status-badge status-badge--lock">LOCKED IN</span> Perfect alignment.';
    } else if (absBpmDiff > 0.4) {
      // Step 1: Fix Tempo First
      el.coachBanner.className = "coach-banner coach--tempo";
      var faster = state.bpmB > state.bpmA;
      if (el.coachTitle) el.coachTitle.textContent = "STEP 1: MATCH TEMPO (PITCH FADER)";
      if (el.coachMsg) {
        el.coachMsg.textContent = faster
          ? "Deck B is running fast (+" + fmt(Math.abs(bpmDiff), 1) + " BPM). Drag the Pitch Slider DOWN."
          : "Deck B is running slow (-" + fmt(Math.abs(bpmDiff), 1) + " BPM). Drag the Pitch Slider UP.";
      }
      if (el.status) {
        el.status.innerHTML = '<span class="status-badge status-badge--drift">TEMPO MISMATCH</span> ' +
          (faster ? 'Deck B is too fast' : 'Deck B is too slow') + ' (' + fmt(Math.abs(bpmDiff), 1) + ' BPM).';
      }
    } else {
      // Step 2: Nudge / Cue Phase Alignment
      el.coachBanner.className = "coach-banner coach--phase";
      var dragging = diff > 0;
      if (el.coachTitle) el.coachTitle.textContent = "STEP 2: ALIGN KICK PHASE (NUDGE)";
      if (el.coachMsg) {
        el.coachMsg.textContent = dragging
          ? "Tempo matched! Deck B is trailing (" + Math.round(absDiff) + "ms behind). Tap 'push ▶' or tap CUE on beat 1."
          : "Tempo matched! Deck B is rushing (" + Math.round(absDiff) + "ms ahead). Tap '◀ slow' once.";
      }
      if (el.status) {
        el.status.innerHTML = '<span class="status-badge status-badge--close">CLOSE</span> Tap ' +
          (dragging ? 'push ▶' : '◀ slow') + ' to lock kicks.';
      }
    }
  }

  /* ------------------------------------------------------------- Controls */
  function start() {
    stop("manual");
    var ctx = ensureAudioCtx();
    if (!ctx) return;
    if (ctx.state === "suspended") ctx.resume();

    var diffSetting = el.difficulty ? el.difficulty.value : "steady";
    var maxDrift = diffSetting === "easy" ? 0.04 : diffSetting === "hard" ? 0.12 : 0.07;
    var tempoError = (Math.random() * (maxDrift * 2) - maxDrift);
    if (Math.abs(tempoError) < 0.02) tempoError = tempoError < 0 ? -0.025 : 0.025;

    state.baseBpm = state.bpmA * (1 - tempoError);
    state.pitch = 0;
    state.bpmB = state.baseBpm;
    state.posA = 0;
    state.posB = Math.random() * 0.8 + 0.1; // Random downbeat offset
    state.beatA = 0;
    state.beatB = 0;
    state.scheduledA = -1;
    state.scheduledB = -1;
    state.locked = false;
    state.lockedMs = 0;
    state.totalMs = 0;
    state.currentStreakMs = 0;
    state.bestStreakMs = 0;
    state.offsets = [];

    var nowPerf = window.performance.now();
    state.endsAt = nowPerf + DRILL_DURATION_S * 1000;
    state.lastAudio = ctx.currentTime;
    state.lastFrame = nowPerf;
    state.running = true;

    setPitch(0);
    applyAudioRouting();

    if (el.start) el.start.disabled = true;
    if (el.stop) el.stop.disabled = false;
    if (el.scorecard) el.scorecard.hidden = true;
    if (el.stage) el.stage.classList.add("is-running");

    state.raf = window.requestAnimationFrame(frame);
  }

  function stop(reason) {
    if (!state.running) return;
    state.running = false;
    if (state.raf) {
      window.cancelAnimationFrame(state.raf);
      state.raf = null;
    }

    if (el.start) el.start.disabled = false;
    if (el.stop) el.stop.disabled = true;
    if (el.stage) el.stage.classList.remove("is-running");

    if (reason === "done" && state.mode === "drill") {
      showScorecard();
    }
  }

  function showScorecard() {
    if (!el.scorecard) return;
    var finalScore = state.totalMs > 0 ? Math.round((state.lockedMs / state.totalMs) * 100) : 0;
    var avgOffset = state.offsets.length > 0 ? Math.round(state.offsets.reduce(function (a, b) { return a + b; }, 0) / state.offsets.length) : 0;
    var streakSec = (state.bestStreakMs / 1000).toFixed(1);

    var gradeBadge = root.querySelector("[data-score-grade]");
    var valElem = root.querySelector("[data-score-val]");
    var driftElem = root.querySelector("[data-score-drift]");
    var streakElem = root.querySelector("[data-score-streak]");
    var tipElem = root.querySelector("[data-score-tip]");

    if (valElem) valElem.textContent = finalScore + "%";
    if (driftElem) driftElem.textContent = "±" + avgOffset + " ms";
    if (streakElem) streakElem.textContent = streakSec + "s";

    var grade = "TRAINWRECK";
    var tip = "Focus on matching pitch first before trying to nudge phase.";
    if (finalScore >= 80) {
      grade = "CLUB READY 🔥";
      tip = "Exceptional ear! Your transitions would sound seamless on a festival sound system.";
    } else if (finalScore >= 55) {
      grade = "SOLID BLEND ✓";
      tip = "Good pitch matching. Use shorter, gentle nudges to keep kicks centered.";
    }

    if (gradeBadge) gradeBadge.textContent = grade;
    if (tipElem) tipElem.textContent = tip;

    el.scorecard.hidden = false;
  }

  /* ------------------------------------------------------------- Listeners */
  if (el.start) el.start.addEventListener("click", start);
  if (el.stop) el.stop.addEventListener("click", function () { stop("manual"); });
  if (el.reset) el.reset.addEventListener("click", function () {
    stop("manual");
    if (el.scorecard) el.scorecard.hidden = true;
    setPitch(0);
    if (el.score) el.score.textContent = "0%";
    if (el.clock) el.clock.textContent = state.mode === "drill" ? "45s" : "Guided";
  });

  if (el.pitch) {
    el.pitch.addEventListener("input", function (e) {
      setPitch(parseFloat(e.target.value));
    });
  }

  // Nudge controls
  function startNudge(direction) {
    state.nudge = direction;
  }
  function endNudge() {
    state.nudge = 0;
  }

  if (el.nudgeBack) {
    el.nudgeBack.addEventListener("mousedown", function () { startNudge(-1); });
    el.nudgeBack.addEventListener("mouseup", endNudge);
    el.nudgeBack.addEventListener("mouseleave", endNudge);
    el.nudgeBack.addEventListener("touchstart", function (e) { e.preventDefault(); startNudge(-1); }, { passive: false });
    el.nudgeBack.addEventListener("touchend", endNudge);
  }

  if (el.nudgeFwd) {
    el.nudgeFwd.addEventListener("mousedown", function () { startNudge(1); });
    el.nudgeFwd.addEventListener("mouseup", endNudge);
    el.nudgeFwd.addEventListener("mouseleave", endNudge);
    el.nudgeFwd.addEventListener("touchstart", function (e) { e.preventDefault(); startNudge(1); }, { passive: false });
    el.nudgeFwd.addEventListener("touchend", endNudge);
  }

  // CUE Drop (Drops Deck B onto current Downbeat)
  if (el.cueBtn) {
    el.cueBtn.addEventListener("click", function () {
      if (!state.running) return;
      state.posB = Math.floor(state.posA);
      state.scheduledB = state.scheduledA;
    });
  }

  // Split Cue & Solo toggles
  if (el.splitCueBtn) {
    el.splitCueBtn.addEventListener("click", function () {
      state.splitCue = !state.splitCue;
      el.splitCueBtn.classList.toggle("is-active", state.splitCue);
      applyAudioRouting();
    });
  }

  if (el.soloABtn) {
    el.soloABtn.addEventListener("click", function () {
      state.soloA = !state.soloA;
      state.soloB = false;
      el.soloABtn.classList.toggle("is-active", state.soloA);
      if (el.soloBBtn) el.soloBBtn.classList.remove("is-active");
      applyAudioRouting();
    });
  }

  if (el.soloBBtn) {
    el.soloBBtn.addEventListener("click", function () {
      state.soloB = !state.soloB;
      state.soloA = false;
      el.soloBBtn.classList.toggle("is-active", state.soloB);
      if (el.soloABtn) el.soloABtn.classList.remove("is-active");
      applyAudioRouting();
    });
  }

  // Mode switcher tabs
  if (el.modeTabs) {
    el.modeTabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        el.modeTabs.forEach(function (t) { t.classList.remove("is-active"); });
        tab.classList.add("is-active");
        state.mode = tab.getAttribute("data-trainer-mode") || "practice";
        if (el.clock) el.clock.textContent = state.mode === "drill" ? "45s" : "Guided";
        if (state.running) {
          stop("manual");
          start();
        }
      });
    });
  }

  // Genre dropdown
  if (el.genreSelect) {
    el.genreSelect.addEventListener("change", function (e) {
      setGenre(e.target.value);
    });
  }

  // Scorecard actions
  if (el.scorecardClose) {
    el.scorecardClose.addEventListener("click", function () {
      if (el.scorecard) el.scorecard.hidden = true;
    });
  }
  if (el.scorecardRetry) {
    el.scorecardRetry.addEventListener("click", function () {
      if (el.scorecard) el.scorecard.hidden = true;
      start();
    });
  }

  // Keyboard controls
  document.addEventListener("keydown", function (e) {
    if (e.target.matches("input, textarea, select, [contenteditable]")) return;

    if (e.code === "Space") {
      e.preventDefault();
      if (state.running) stop("manual");
      else start();
    } else if (e.code === "KeyC") {
      e.preventDefault();
      if (el.cueBtn) el.cueBtn.click();
    } else if (e.code === "ArrowLeft") {
      e.preventDefault();
      startNudge(-1);
    } else if (e.code === "ArrowRight") {
      e.preventDefault();
      startNudge(1);
    } else if (e.code === "ArrowUp") {
      e.preventDefault();
      setPitch(state.pitch + 0.1);
    } else if (e.code === "ArrowDown") {
      e.preventDefault();
      setPitch(state.pitch - 0.1);
    }
  });

  document.addEventListener("keyup", function (e) {
    if (e.code === "ArrowLeft" || e.code === "ArrowRight") {
      endNudge();
    }
  });

  // Platter drag interaction
  if (el.platterB) {
    el.platterB.addEventListener("mousedown", function (e) {
      state.isDraggingPlatter = true;
      state.dragStartY = e.clientY;
    });
    window.addEventListener("mousemove", function (e) {
      if (!state.isDraggingPlatter) return;
      var dy = state.dragStartY - e.clientY;
      if (Math.abs(dy) > 5) {
        state.nudge = dy > 0 ? 1 : -1;
      }
    });
    window.addEventListener("mouseup", function () {
      if (state.isDraggingPlatter) {
        state.isDraggingPlatter = false;
        endNudge();
      }
    });
  }
})();
