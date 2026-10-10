import assert from "node:assert/strict";
import { test } from "node:test";
import { daysSince, kept, localDay, POLL_MS, toNumber } from "./store.js";

test("days since the last reading", () => {
  assert.equal(daysSince("2026-10-07", "2026-10-07"), 0);
  assert.equal(daysSince("2026-10-04", "2026-10-07"), 3);
  assert.equal(daysSince("2026-09-25", "2026-10-07"), 12);
  assert.equal(daysSince("2026-02-27", "2026-03-02"), 3);     // across a month end
  assert.equal(daysSince("2025-12-30", "2026-01-02"), 3);     // across a year end
  assert.equal(daysSince("2026-10-08", "2026-10-07"), -1);    // a reading dated tomorrow is not stale
});

test("today is the phone's date, not UTC's", () => {
  assert.equal(localDay(new Date(2026, 9, 7, 0, 30)), "2026-10-07");
  assert.equal(localDay(new Date(2026, 9, 7, 23, 30)), "2026-10-07");
});

test("a read gives null where there is no storage", () => {
  assert.equal(kept("me"), null);
});

test("the wait for a fresh verdict looks every 4 seconds for 20, then backs off, and gives up in about three minutes", () => {
  assert.deepEqual(POLL_MS.slice(0, 5), [4000, 4000, 4000, 4000, 4000]);
  const later = POLL_MS.slice(5);
  assert.ok(later.every((wait, i) => wait > 4000 && wait <= 30000 && wait >= (later[i - 1] ?? 0)), "longer each time, 30 s at most");
  const total = POLL_MS.reduce((sum, wait) => sum + wait, 0);
  assert.ok(total >= 120_000 && total <= 240_000, `${total} ms`);  // an analysis run may take 120 s
});

test("a figure typed with a decimal comma is the same number", () => {
  assert.equal(toNumber("5,5"), 5.5);
  assert.equal(toNumber(" 12.4 "), 12.4);
  assert.equal(toNumber("7"), 7);
  assert.ok(Number.isNaN(toNumber("1,234.5")));  // not guessed at: the API then says it must be a number
  assert.ok(Number.isNaN(toNumber("five")));
});
