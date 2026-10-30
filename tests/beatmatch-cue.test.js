"use strict";

// Deterministic source-level acceptance of CUE timing and audible downbeat.
// No production test hooks, browser audio devices or network required.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function makeTrainer(options = {}) {
  const source = fs.readFileSync(path.join(__dirname, "../assets/beatmatch-trainer.js"), "utf8");
  assert.match(source, /\}\)\(\);\s*$/, "Expected trainer IIFE");
  const instrumented = source.replace(/\}\)\(\);\s*$/,
    "globalThis.__trainerProbe = { state: state, phaseMs: phaseMs, audio: audio, start: start, stop: stop, frame: frame, currentBpmB: currentBpmB, showScorecard: showScorecard };})();");
  const cueListeners = {};
  const documentListeners = {};
  const windowListeners = {};
  const cue = {
    addEventListener(type, handler) { cueListeners[type] = handler; },
    click() { cueListeners.click(); }
  };
  const scoreDrift = { textContent: "" };
  const scorecard = { hidden: true };
  const platterListeners = {};
  const platter = {
    style: {},
    captured: null,
    addEventListener(type, handler) { platterListeners[type] = handler; },
    setPointerCapture(id) { this.captured = id; }
  };
  const stage = {
    focusCalls: 0,
    classList: { add() {}, remove() {} },
    focus() { this.focusCalls++; }
  };
  const root = {
    contains(target) { return target && target.insideTrainer !== false; },
    querySelector(selector) {
      if (selector === "[data-stage]") return stage;
      if (selector === "[data-cue]") return cue;
      if (selector === "[data-platter-b]") return platter;
      if (selector === "[data-difficulty]") return { value: options.difficulty || "steady" };
      if (selector === "[data-pitch]") return { min: "-8", max: "8", value: "0", addEventListener() {} };
      if (selector === "[data-score-drift]") return scoreDrift;
      if (selector === "[data-scorecard]") return scorecard;
      return null;
    },
    querySelectorAll() { return []; }
  };
  const document = {
    getElementById(id) { return id === "trainer" ? root : null; },
    querySelector() { return null; },
    addEventListener(type, handler) { documentListeners[type] = handler; }
  };
  const context = {
    document,
    window: {
      performance: { now() { return 1000; } },
      requestAnimationFrame() { return 1; },
      cancelAnimationFrame() {},
      addEventListener(type, handler) { windowListeners[type] = handler; }
    },
    console,
    Math: options.randomValues ? Object.assign(Object.create(Math), {
      random() { return options.randomValues.shift() ?? 0.5; }
    }) : Math
  };
  vm.runInNewContext(instrumented, context, { filename: "beatmatch-trainer.js" });
  assert.equal(typeof cueListeners.click, "function", "CUE handler registered");
  return { ...context.__trainerProbe, cue, documentListeners, windowListeners, document, scoreDrift, scorecard, platter, platterListeners, stage };
}

function setRunningState(probe, elapsed) {
  const starts = [];
  function gainNode() {
    return {
      gain: { value: 0, setValueAtTime() {}, exponentialRampToValueAtTime() {} },
      connect() { return this; },
      disconnect() { this.disconnected = true; }
    };
  }
  const oldB = gainNode();
  const ctx = {
    currentTime: elapsed,
    createGain: gainNode,
    createOscillator() {
      return {
        frequency: { value: 0, setValueAtTime() {}, exponentialRampToValueAtTime() {} },
        connect() { return this; },
        start(when) { starts.push(when); },
        stop() {}
      };
    }
  };
  Object.assign(probe.audio, {
    chanA: gainNode(), chanB: oldB, master: gainNode(),
    pannerA: null, pannerB: null, noise: null
  });
  Object.assign(probe.state, {
    running: true, ctx, lastAudio: 0,
    bpmA: 120, bpmB: 120,
    posA: 8, posB: 7.2, beatB: 7,
    scheduledA: 8, scheduledB: 10
  });
  return { starts, oldB };
}

test("mistimed CUE sounds B beat 1 immediately without snapping to A", () => {
  const probe = makeTrainer();
  const audio = setRunningState(probe, 0.25); // Half a beat late at 120 BPM.
  probe.cue.click();
  assert.equal(probe.state.posA, 8.5, "A advances to the actual press time");
  assert.equal(probe.state.posB, 0, "B starts from its own beat 1");
  assert.equal(probe.state.beatB, 0);
  assert.equal(probe.state.scheduledB, 0, "beat 1 scheduled, not deferred a beat");
  assert.equal(audio.oldB.disconnected, true, "stale queued B audio silenced");
  assert.notEqual(probe.audio.chanB, audio.oldB, "fresh B channel connected");
  assert.ok(audio.starts.includes(0.25), "immediate B downbeat actually scheduled");
  assert.ok(Math.abs(probe.phaseMs()) >= 240,
    "a half-beat-late press remains visibly out of phase");
});

test("well-timed CUE aligns phase without altering either tempo", () => {
  const probe = makeTrainer();
  const audio = setRunningState(probe, 0.003);
  probe.cue.click();
  assert.ok(audio.starts.includes(0.003), "near-downbeat CUE sounds immediately");
  assert.ok(Math.abs(probe.phaseMs()) < 18, "near-downbeat press is aligned");
  assert.equal(probe.state.bpmA, 120);
  assert.equal(probe.state.bpmB, 120);
  assert.equal(probe.state.posB, 0);
});

test("keyboard C uses the same timed CUE and channel reset", () => {
  const probe = makeTrainer();
  const audio = setRunningState(probe, 0.25);
  let prevented = false;
  probe.documentListeners.keydown({
    code: "KeyC",
    target: { matches() { return false; } },
    preventDefault() { prevented = true; }
  });
  assert.equal(prevented, true);
  assert.equal(probe.state.posB, 0);
  assert.equal(probe.state.scheduledB, 0);
  assert.equal(audio.oldB.disconnected, true);
  assert.ok(audio.starts.includes(0.25));
  assert.ok(Math.abs(probe.phaseMs()) >= 240);
});

test("STOP disconnects both queued audio paths; immediate restart cannot replay stale beats", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.12);
  const oldA = probe.audio.chanA;
  const oldB = probe.audio.chanB;
  probe.stop("manual");
  assert.equal(probe.state.running, false);
  assert.equal(oldA.disconnected, true, "scheduled A notes have no output path");
  assert.equal(oldB.disconnected, true, "scheduled B notes have no output path");
  assert.notEqual(probe.audio.chanA, oldA, "fresh A output reserved for next run");
  assert.notEqual(probe.audio.chanB, oldB, "fresh B output reserved for next run");

  probe.start();
  assert.equal(probe.state.running, true, "new session can start immediately");
  assert.equal(oldA.disconnected, true, "old A cannot reappear after restart");
  assert.equal(oldB.disconnected, true, "old B cannot reappear after restart");
});

test("held nudge cannot earn a false locked score while audible Deck B tempo differs", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.001);
  Object.assign(probe.state, {
    posA: 8, posB: 8, scheduledA: 8, scheduledB: 10,
    nudge: 1, lastAudio: 0, lastFrame: 1000, totalMs: 0, lockedMs: 0
  });
  assert.equal(probe.currentBpmB(), 135.6, "held push makes Deck B audibly faster");
  probe.frame(1016);
  assert.ok(Math.abs(probe.phaseMs()) < 18, "instantaneous phase is nearly aligned");
  assert.equal(probe.state.locked, false, "tempo mismatch must prevent lock");
  assert.equal(probe.state.lockedMs, 0, "no false locked time credited");
  assert.equal(probe.state.totalMs, 16);
});

test("release outside controls, focus loss and backgrounding clear held nudge", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.01);
  const arrow = code => ({
    code, target: { matches() { return false; } }, preventDefault() {}
  });
  probe.documentListeners.keydown(arrow("ArrowRight"));
  assert.equal(probe.state.nudge, 1);
  probe.windowListeners.mouseup();
  assert.equal(probe.state.nudge, 0, "global mouseup releases button held outside");

  probe.documentListeners.keydown(arrow("ArrowLeft"));
  assert.equal(probe.state.nudge, -1);
  probe.windowListeners.blur();
  assert.equal(probe.state.nudge, 0, "lost focus releases held keyboard nudge");

  probe.documentListeners.keydown(arrow("ArrowRight"));
  probe.document.hidden = true;
  probe.documentListeners.visibilitychange();
  assert.equal(probe.state.nudge, 0, "backgrounding releases held nudge");

  probe.documentListeners.keydown(arrow("ArrowRight"));
  probe.windowListeners.touchcancel();
  assert.equal(probe.state.nudge, 0, "touch cancellation releases held nudge");
});

test("STOP resets held nudge before immediate restart", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.12);
  probe.state.nudge = -1;
  probe.state.isDraggingPlatter = true;
  probe.stop("manual");
  assert.equal(probe.state.nudge, 0);
  assert.equal(probe.state.isDraggingPlatter, false);
  probe.start();
  assert.equal(probe.state.nudge, 0);
});

test("starting while an idle nudge control was held begins at neutral tempo", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.12);
  probe.stop("manual");
  probe.state.nudge = 1; // A button may still be pressed while stopped.
  probe.state.isDraggingPlatter = true;
  probe.start();
  assert.equal(probe.state.nudge, 0);
  assert.equal(probe.state.isDraggingPlatter, false);
  assert.equal(probe.currentBpmB(), probe.state.bpmB);
});

test("suspended or frozen Web Audio cannot earn a perfect silent drill", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.001);
  Object.assign(probe.state, {
    mode: "drill", endsAt: 46000,
    posA: 8, posB: 8, scheduledA: 8, scheduledB: 10,
    nudge: 0, lastAudio: 0, lastFrame: 1000,
    totalMs: 0, lockedMs: 0, currentStreakMs: 100, offsets: []
  });
  probe.state.ctx.state = "suspended";
  probe.frame(1016);
  assert.equal(probe.state.totalMs, 0, "a suspended audio device is not audible practice");
  assert.equal(probe.state.lockedMs, 0);
  assert.equal(probe.state.currentStreakMs, 0);
  assert.equal(probe.state.offsets.length, 0, "no silent drift samples");

  probe.state.ctx.state = "running";
  probe.state.lastAudio = probe.state.ctx.currentTime;
  probe.frame(1032);
  assert.equal(probe.state.totalMs, 0, "an unmoving audio clock is not audible practice");
  assert.equal(probe.state.lockedMs, 0);

  probe.state.ctx.currentTime += 0.016;
  probe.frame(1048);
  assert.equal(probe.state.totalMs, 16, "observed frames count after the audio clock resumes");
});

test("a stalled animation frame never credits unseen seconds as locked practice", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.001);
  Object.assign(probe.state, {
    posA: 8, posB: 8, scheduledA: 8, scheduledB: 10,
    nudge: 0, lastAudio: 0, lastFrame: 1000,
    totalMs: 0, lockedMs: 0, currentStreakMs: 100
  });
  probe.frame(4000); // Simulate a three-second stalled/backgrounded frame.
  assert.equal(probe.state.locked, true, "near-phase/tempo alignment can still display");
  assert.equal(probe.state.totalMs, 0, "unobserved time must not inflate denominator");
  assert.equal(probe.state.lockedMs, 0, "unobserved time must not earn a score");
  assert.equal(probe.state.currentStreakMs, 0, "streak is broken across a long stall");
});

test("backgrounding a running drill stops it and silences queued deck audio", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.12);
  const oldA = probe.audio.chanA;
  const oldB = probe.audio.chanB;
  probe.state.nudge = 1;
  probe.document.hidden = true;
  probe.documentListeners.visibilitychange();
  assert.equal(probe.state.running, false);
  assert.equal(probe.state.nudge, 0);
  assert.equal(oldA.disconnected, true);
  assert.equal(oldB.disconnected, true);
});


test("timed drill includes severe 250ms phase misses in reported average drift", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.001);
  Object.assign(probe.state, {
    mode: "drill", endsAt: 46000, posA: 8, posB: 8.5,
    scheduledA: 8, scheduledB: 10, lastFrame: 1000, offsets: []
  });
  probe.frame(1016);
  assert.equal(probe.state.locked, false);
  assert.equal(probe.state.offsets.length, 1, "severe miss must not be silently excluded");
  assert.ok(probe.state.offsets[0] >= 240, "half-beat phase error is about 250ms");
  probe.showScorecard();
  assert.equal(probe.scoreDrift.textContent, "±250 ms",
    "the final scorecard must not present a severe miss as zero drift");
});

test("practice and unobserved frames cannot inflate the drill drift sample", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.001);
  Object.assign(probe.state, {
    mode: "practice", posA: 8, posB: 8.5,
    scheduledA: 8, scheduledB: 10, lastFrame: 1000, offsets: []
  });
  probe.frame(1016);
  assert.equal(probe.state.offsets.length, 0,
    "untimed practice must not accumulate an unbounded scorecard sample");
  probe.state.mode = "drill";
  probe.state.endsAt = 46000;
  probe.frame(4000);
  assert.equal(probe.state.offsets.length, 0,
    "a stalled/unobserved frame must not contaminate measured drift");
  probe.showScorecard();
  assert.equal(probe.scoreDrift.textContent, "Not measured",
    "a drill with no observed samples must not claim ±0 ms");
});

test("hard-mode tempo mismatch is challenging but always reachable with the visible 8% pitch fader", () => {
  for (const magnitude of [0, 0.999999]) {
    for (const sign of [0, 0.999999]) {
      const probe = makeTrainer({ difficulty: "hard", randomValues: [magnitude, sign, 0.5] });
      setRunningState(probe, 0.12);
      probe.start();
      const correction = (probe.state.bpmA / probe.state.baseBpm - 1) * 100;
      assert.ok(Math.abs(correction) >= 6.5 - 1e-8,
        "hard mode must present a meaningful tempo challenge");
      assert.ok(Math.abs(correction) <= 8 + 1e-8,
        "hard mode must never demand a correction beyond the physical fader");
      assert.ok(Math.abs(probe.state.baseBpm * (1 + correction / 100) - probe.state.bpmA) < 1e-8,
        "a legal pitch adjustment must bring Deck B exactly to Deck A tempo");
    }
  }
});

test("easy and steady initial offsets also stay within their intended playable ranges", () => {
  for (const [difficulty, lower, upper] of [["easy", 2, 4], ["steady", 2, 7]]) {
    for (const magnitude of [0, 0.999999]) {
      for (const sign of [0, 0.999999]) {
        const probe = makeTrainer({ difficulty, randomValues: [magnitude, sign, 0.5] });
        setRunningState(probe, 0.12);
        probe.start();
        const correction = Math.abs((probe.state.bpmA / probe.state.baseBpm - 1) * 100);
        assert.ok(correction >= lower - 1e-8 && correction <= upper + 1e-8,
          difficulty + " mode correction must be reachable and appropriately scaled");
      }
    }
  }
});


test("START plays Deck A beat zero immediately and reserves it against duplicate scheduling", () => {
  const probe = makeTrainer();
  const audio = setRunningState(probe, 0.12);
  probe.stop("manual");
  probe.start();

  assert.equal(probe.state.beatA, 0, "master begins on beat zero");
  assert.equal(probe.state.scheduledA, 0, "first beat is reserved in lookahead state");
  const initialStarts = audio.starts.filter(when => when === 0.12).length;
  assert.ok(initialStarts >= 1, "the first kick oscillator starts at the actual START time");
  assert.ok(audio.starts.some(when => Math.abs(when - 0.14) < 1e-9),
    "the first bass note follows 20 ms after the downbeat");

  probe.frame(1016); // First animation frame, with no audio-time progression.
  assert.equal(audio.starts.filter(when => when === 0.12).length, initialStarts,
    "first animation frame must not schedule a second beat zero");
  assert.equal(probe.state.scheduledA, 0);
});

test("mobile finger swipe nudges Deck B and release outside the platter restores tempo", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.01);
  assert.equal(probe.platter.style.touchAction, "none", "touch scroll must not cancel jog drag");
  probe.platterListeners.pointerdown({ pointerId: 7, pointerType: "touch", clientY: 160 });
  assert.equal(probe.platter.captured, 7, "capture keeps finger release observable");
  probe.platterListeners.pointermove({ pointerId: 7, pointerType: "touch", clientY: 120 });
  assert.equal(probe.state.nudge, 1, "upward swipe pushes Deck B forward");
  assert.equal(probe.currentBpmB(), 135.6, "swipe changes the actual audio tempo");
  probe.platterListeners.pointermove({ pointerId: 8, pointerType: "touch", clientY: 200 });
  assert.equal(probe.state.nudge, 1, "second finger cannot hijack active jog");
  probe.windowListeners.pointerup({ pointerId: 7, pointerType: "touch" });
  assert.equal(probe.state.isDraggingPlatter, false);
  assert.equal(probe.state.nudge, 0, "release outside the platter stops nudging");
  assert.equal(probe.currentBpmB(), 120, "deck returns to pitch-fader tempo");
});

test("downward finger swipe, cancellation and lost capture cannot leave Deck B nudging", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.01);
  probe.platterListeners.pointerdown({ pointerId: 11, pointerType: "touch", clientY: 80 });
  probe.platterListeners.pointermove({ pointerId: 11, pointerType: "touch", clientY: 120 });
  assert.equal(probe.state.nudge, -1, "downward swipe slows Deck B");
  probe.platterListeners.pointercancel({ pointerId: 11 });
  assert.equal(probe.state.nudge, 0, "touch cancellation releases jog");
  probe.platterListeners.pointerdown({ pointerId: 12, pointerType: "touch", clientY: 80 });
  probe.platterListeners.pointermove({ pointerId: 12, pointerType: "touch", clientY: 120 });
  probe.platterListeners.lostpointercapture({ pointerId: 12 });
  assert.equal(probe.state.nudge, 0, "lost capture releases jog");
  assert.equal(probe.state.dragPointerId, null);
});

test("mouse jog drag still works, rejects right-click and ignores idle swipes", () => {
  const probe = makeTrainer();
  const down = { pointerId: 3, pointerType: "mouse", button: 0, clientY: 160 };
  probe.platterListeners.pointerdown(down);
  assert.equal(probe.state.isDraggingPlatter, false, "idle jog should not latch");
  setRunningState(probe, 0.01);
  probe.platterListeners.pointerdown({ ...down, button: 2 });
  assert.equal(probe.state.isDraggingPlatter, false, "right click is not a jog gesture");
  probe.platterListeners.pointerdown(down);
  probe.platterListeners.pointermove({ pointerId: 3, pointerType: "mouse", clientY: 120 });
  assert.equal(probe.state.nudge, 1, "mouse drag still pushes the platter");
  probe.platterListeners.pointerup({ pointerId: 3 });
  assert.equal(probe.state.nudge, 0);
});

test("keyboard shortcuts never hijack page navigation or native trainer controls", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.12);
  const originalPosB = probe.state.posB;
  const outside = { insideTrainer: false, matches() { return false; }, closest() { return null; } };
  const button = { insideTrainer: true, matches(selector) { return selector.includes("button"); }, closest() { return null; } };
  const shortcut = code => ({ code, target: outside, preventDefault() { throw Error("page shortcut intercepted"); } });
  probe.documentListeners.keydown(shortcut("Space"));
  probe.documentListeners.keydown(shortcut("ArrowDown"));
  probe.documentListeners.keydown(shortcut("KeyC"));
  assert.equal(probe.state.running, true, "outside Space must not stop the drill");
  assert.equal(probe.state.pitch, 0, "outside arrows must retain native page behavior");
  assert.equal(probe.state.posB, originalPosB, "outside C must not trigger CUE");

  probe.documentListeners.keydown({
    code: "Space", target: button,
    preventDefault() { throw Error("native button Space intercepted"); }
  });
  assert.equal(probe.state.running, true, "native button Space must remain native");
});

test("focused practice stage accepts shortcuts and respects modifier keys", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.12);
  let prevented = 0;
  const target = { insideTrainer: true, matches() { return false; }, closest() { return null; } };
  const key = (code, extra = {}) => ({
    code, target, preventDefault() { prevented++; }, ...extra
  });
  probe.documentListeners.keydown(key("ArrowRight"));
  assert.equal(probe.state.nudge, 1, "focused stage should nudge B");
  probe.documentListeners.keyup({ code: "ArrowRight" });
  assert.equal(probe.state.nudge, 0);
  probe.documentListeners.keydown(key("ArrowUp"));
  assert.equal(probe.state.pitch, 0.1, "focused stage should adjust pitch");
  probe.documentListeners.keydown(key("ArrowDown", { ctrlKey: true }));
  assert.equal(probe.state.pitch, 0.1, "modified shortcuts must not alter the trainer");
  assert.equal(prevented, 2, "only active trainer shortcuts prevent browser defaults");
});

test("START focuses the accessible practice stage; R retries only a visible scorecard", () => {
  const probe = makeTrainer();
  setRunningState(probe, 0.12);
  probe.stop("manual");
  probe.start();
  assert.equal(probe.stage.focusCalls, 1, "START should enable focused stage shortcuts");
  const target = { insideTrainer: true, matches() { return false; }, closest() { return null; } };
  const retry = () => probe.documentListeners.keydown({ code: "KeyR", target, preventDefault() {} });
  retry();
  assert.equal(probe.stage.focusCalls, 1, "R must not reset an active drill");
  probe.scorecard.hidden = false;
  retry();
  assert.equal(probe.stage.focusCalls, 2, "R should retry when scorecard is visible");
  assert.equal(probe.scorecard.hidden, true, "retry hides the old scorecard");
});
