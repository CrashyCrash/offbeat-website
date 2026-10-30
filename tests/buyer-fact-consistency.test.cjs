"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

function page(name) {
  return fs.readFileSync(path.join(__dirname, "..", name), "utf8");
}

function faqPairs(html) {
  const blocks = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
    .map(match => JSON.parse(match[1]));
  const faq = blocks.find(block => block["@type"] === "FAQPage");
  assert.ok(faq, "FAQPage structured data must exist");
  const visible = [...html.matchAll(/<details><summary>([\s\S]*?)<\/summary><p>([\s\S]*?)<\/p><\/details>/g)]
    .map(match => ({ question: match[1], answer: match[2] }));
  assert.equal(faq.mainEntity.length, 5, "five FAQ questions");
  assert.equal(visible.length, 5, "five visible answers");
  for (const item of faq.mainEntity) {
    assert.ok(visible.some(pair => pair.question === item.name && pair.answer === item.acceptedAnswer.text),
      "visible FAQ and JSON-LD disagree: " + item.name);
  }
}

test("FLX4 software and predecessor claims match primary vendor facts", () => {
  const html = page("pioneer-ddj-flx4-review.html");
  faqPairs(html);
  assert.match(html, /Serato DJ Lite already includes basic Stems/);
  assert.match(html, /DDJ-400 also had/);
  assert.match(html, /DDJ-400 already had Beat FX controls/);
  assert.match(html, /Traktor Play is officially supported/);
  assert.match(html, /compatible computer or supported mobile device/);
  assert.match(html, /separately supplied 9V\/3A power source/);
  assert.doesNotMatch(html, /DDJ-400 needed external|Serato DJ Pro adds four decks, Stems|laptop is required for every set|\$9\.99\/month|absent on the DDJ-400|a built-in audio interface, a Beat FX section, and a licence/);
  assert.match(html, /https:\/\/serato\.com\/dj\/lite/);
  assert.match(html, /https:\/\/www\.pioneerdj\.com\/en\/product\/dj-controllers\/ddj-flx4\//);
});

test("headphone comparison never equates sensitivity to max SPL", () => {
  const html = page("best-dj-headphones-2026.html");
  faqPairs(html);
  assert.match(html, /99 dB\/mW sensitivity is not max SPL/);
  assert.match(html, /Audio-Technica ATH-M50x specification/);
  assert.doesNotMatch(html, /Club-Ready Picks Tested/);
  assert.doesNotMatch(html, /SPL Max|low max SPL \(99 dB|106 dB max SPL|100\+ dB SPL for loud club/);
  const table = html.match(/<table class="comparison-table">([\s\S]*?)<\/table>/);
  assert.ok(table, "comparison table exists");
  const rows = [...table[1].matchAll(/<tr>([\s\S]*?)<\/tr>/g)].map(match => match[1]);
  assert.equal(rows.length, 7, "header plus six product rows");
  rows.forEach((row, index) => {
    const cells = [...row.matchAll(/<(?:th|td)>[\s\S]*?<\/(?:th|td)>/g)];
    assert.equal(cells.length, 5, "consistent five-column row " + index);
  });
});
