// Every line the app shows has its Hindi, with the same {names} to fill in. Run with `npm test`.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { ARRIVES, HI } from "./hi.js";

const here = new URL(".", import.meta.url);
const source = readdirSync(here).filter((f) => /\.jsx?$/.test(f) && !/test|^hi\.js$/.test(f))
  .map((f) => readFileSync(new URL(f, here), "utf8")).join("\n");
const used = new Set([...source.matchAll(/\bt\(\s*"((?:[^"\\]|\\.)*)"/g)].map((m) => JSON.parse(`"${m[1]}"`)));
const names = (text) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

test("every line passed to t() has its Hindi", () => {
  assert.ok(used.size > 100, "found the app's lines");
  assert.deepEqual([...used].filter((en) => !HI[en]), []);
});

test("the Hindi fills in the same {names} as the English, and is Hindi", () => {
  for (const [en, hi] of Object.entries(HI)) {
    assert.deepEqual(names(hi), names(en), en);
    assert.match(hi, /[ऀ-ॿ]/, en);
  }
});

test("no Hindi is left behind for a line the app no longer uses", () => {
  assert.deepEqual(Object.keys(HI).filter((en) => !used.has(en) && !ARRIVES.includes(en)), []);
});

// The Hindi is found by the English line itself, so "Try again" and "try  again" are two keys: one can miss
// its Hindi, or carry a different one, for what a reader sees as the same line.
test("no two lines differ only by capital letters or spacing", () => {
  const alike = Map.groupBy(new Set([...used, ...Object.keys(HI), ...ARRIVES]), (en) => en.toLowerCase().replace(/\s+/g, " ").trim());
  assert.deepEqual([...alike.values()].filter((lines) => lines.length > 1), []);
});

test("no text is left bare between tags", () => {
  // Words sitting directly in the JSX, outside t(): what a missed line looks like. Brand and language names are meant to be.
  const bare = [...source.matchAll(/>\s*([A-Z][a-z]+(?: [A-Za-z']+)+[^<>{}]*?)\s*</g)].map((m) => m[1]).filter((s) => !/^Language/.test(s));
  assert.deepEqual(bare, []);
});
