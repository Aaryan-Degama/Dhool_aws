// node --test src/   (no test framework: Node's own runner)
import assert from "node:assert/strict";
import { test } from "node:test";
import { skyByClock, skyFor } from "./sky.js";

test("the sky follows the weather", () => {
  const cases = [
    [{ code: 0, isDay: true }, "day"], [{ code: 2, isDay: true }, "day"], [{ code: 3, isDay: true }, "cloud"],
    [{ code: 0, isDay: false }, "night"], [{ code: 3, isDay: false }, "night"],
    [{ code: 61, isDay: true }, "rain"], [{ code: 80, isDay: true }, "rain"],
    [{ code: 65, isDay: true }, "storm"], [{ code: 61, isDay: false }, "storm"], [{ code: 95, isDay: true }, "storm"],
    [{ code: 73, isDay: true }, "snow"], [{ code: 86, isDay: false }, "snow"],
    [{ code: 0, isDay: true, dust: 450 }, "sand"], [{ code: 0, isDay: true, dust: 120 }, "day"],
  ];
  for (const [weather, sky] of cases) assert.equal(skyFor(weather), sky, JSON.stringify(weather));
});

test("before the weather is known, the clock decides", () => {
  assert.deepEqual([5, 6, 12, 18, 19, 23].map(skyByClock), ["night", "day", "day", "day", "night", "night"]);
});
