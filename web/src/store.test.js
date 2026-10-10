import assert from "node:assert/strict";
import { test } from "node:test";
import { FIXTURES } from "./fixtures.js";
import { daysSince, kept, localDay, POLL_MS, toNumber, weeksOf } from "./store.js";

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

test("a month splits into weeks by date, each with its total and its days", () => {
  const daily = { "2026-10-01": 10, "2026-10-02": 11.25, "2026-10-04": 9.5, "2026-10-08": 12, "2026-10-31": 7.04 };
  const weeks = weeksOf("2026-10", daily, "2026-11-03");
  assert.deepEqual(weeks.map((w) => [w.from, w.to, w.kwh, w.read]),
    [[1, 7, 30.8, 3], [8, 14, 12, 1], [15, 21, 0, 0], [22, 28, 0, 0], [29, 31, 7, 1]]);
  assert.deepEqual(weeks[0].days.slice(0, 3),
    [{ date: "2026-10-01", kwh: 10 }, { date: "2026-10-02", kwh: 11.25 }, { date: "2026-10-03", kwh: null }]);  // no reading is not 0
  assert.deepEqual(weeks.map((w) => w.days.length), [7, 7, 7, 7, 3]);
});

test("the month still running stops at the last reading, and February has four weeks or five", () => {
  const running = weeksOf("2026-10", { "2026-10-09": 5 }, "2026-10-09");
  assert.deepEqual(running.map((w) => [w.from, w.to]), [[1, 7], [8, 9]]);
  assert.equal(running[1].days.at(-1).date, "2026-10-09");
  assert.deepEqual(weeksOf("2026-10", {}, "2026-10-29").at(-1).days, [{ date: "2026-10-29", kwh: null }]);
  assert.deepEqual(weeksOf("2026-02", {}, "2026-03-01").map((w) => w.to), [7, 14, 21, 28]);
  assert.deepEqual(weeksOf("2028-02", {}, "2028-03-01").map((w) => w.to), [7, 14, 21, 28, 29]);
});

test("the sample days add up to the sample months", () => {
  const { months, daily_kwh: daily, as_of: asOf } = FIXTURES[0];
  assert.deepEqual(new Set(Object.keys(daily).map((d) => d.slice(0, 7))), new Set(months.filter((m) => m.days).map((m) => m.month)));
  for (const m of months) {
    const weeks = weeksOf(m.month, daily, asOf);
    assert.equal(weeks.reduce((n, w) => n + w.read, 0), m.days, m.month);
    assert.equal(+weeks.flatMap((w) => w.days).reduce((sum, d) => sum + (d.kwh ?? 0), 0).toFixed(2), m.kwh, m.month);
  }
});
