const puppeteer = require("puppeteer-core");
const assert = require("assert");

(async () => {
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME_BIN,
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--autoplay-policy=no-user-gesture-required"]
  });

  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", err => errors.push(err.message));
  page.on("console", msg => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto("http://127.0.0.1:8099/beatmatch-trainer.html", { waitUntil: "networkidle0" });

  // 1. Verify Mode Switching
  const modeTabs = await page.$$(".trainer-mode-tab");
  assert.strictEqual(modeTabs.length, 2, "Expected 2 trainer mode tabs");
  
  // 2. Select Techno Genre
  await page.select("[data-genre]", "techno");
  const bpmA = await page.$eval("[data-bpm-a]", el => el.textContent.trim());
  console.log("Techno Genre Master BPM:", bpmA);
  assert.strictEqual(bpmA, "132.0", "Expected 132.0 BPM for Techno");

  // 3. Start Training
  await page.click("[data-start]");
  await new Promise(r => setTimeout(r, 400));

  const isRunning = await page.$eval(".teacher-stage", el => el.classList.contains("is-running"));
  console.log("Trainer running status:", isRunning);
  assert.ok(isRunning, "Expected trainer stage to be running");

  // 4. Test Pitch Fader & Coach Feedback
  await page.$eval("[data-pitch]", el => {
    el.value = "2.5";
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await new Promise(r => setTimeout(r, 200));

  const pitchVal = await page.$eval("[data-pitch-value]", el => el.textContent.trim());
  console.log("Pitch value adjusted to:", pitchVal);
  assert.strictEqual(pitchVal, "+2.50%");

  // 5. Test CUE Drop Button
  await page.click("[data-cue]");
  await new Promise(r => setTimeout(r, 200));
  console.log("✓ CUE drop button clicked");

  // 6. Test Nudge Buttons
  await page.click("[data-nudge-fwd]");
  await new Promise(r => setTimeout(r, 200));
  console.log("✓ Nudge button pressed");

  // 7. Keyboard shortcuts must not hijack page navigation.
  await page.focus("a.skip-link");
  await page.keyboard.press("Space");
  assert.ok(await page.$eval("[data-stage]", el => el.classList.contains("is-running")),
    "Space on a page link must not stop the trainer");
  const pitchBefore = await page.$eval("[data-pitch]", el => el.value);
  await page.keyboard.press("ArrowUp");
  assert.strictEqual(await page.$eval("[data-pitch]", el => el.value), pitchBefore,
    "ArrowUp outside the trainer must not change its pitch");

  // Explicitly focusing the practice stage enables the advertised shortcuts.
  await page.focus("[data-stage]");
  await page.keyboard.press("ArrowUp");
  assert.notStrictEqual(await page.$eval("[data-pitch]", el => el.value), pitchBefore,
    "ArrowUp on the focused practice stage should adjust the pitch");
  await page.keyboard.press("c");
  assert.ok(await page.$eval("[data-stage]", el => el.classList.contains("is-running")),
    "CUE shortcut should preserve the running drill");

  // 8. Pause
  await page.click("[data-stop]");
  await new Promise(r => setTimeout(r, 200));

  console.log("JS Console Errors:", errors);
  assert.strictEqual(errors.length, 0, "No JS errors expected in trainer");

  await browser.close();
  console.log("ALL BEATMATCH TRAINER E2E TESTS PASSED WITH 0 ERRORS!");
})();
