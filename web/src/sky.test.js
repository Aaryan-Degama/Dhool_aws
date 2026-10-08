// node --test   (no test framework: Node's own runner)
import assert from "node:assert/strict";
import { test } from "node:test";
import { skyByClock, skyFor } from "./sky.js";

const sky = (weather) => { const { sky, dark } = skyFor(weather); return dark ? `${sky} dark` : sky; };

test("the sky follows the weather and the time", () => {
  const cases = [
    [{ code: 0, isDay: true }, "day"], [{ code: 2, isDay: true }, "day"], [{ code: 0, isDay: false }, "night dark"],
    [{ code: 3, isDay: true }, "cloud"], [{ code: 3, isDay: false }, "cloud dark"],
    [{ code: 61, isDay: true }, "rain"], [{ code: 80, isDay: true }, "rain"],
    [{ code: 65, isDay: true }, "storm"], [{ code: 61, isDay: false }, "storm dark"], [{ code: 95, isDay: true }, "storm"],
    [{ code: 73, isDay: true }, "snow"], [{ code: 86, isDay: false }, "snow dark"],
  ];
  for (const [weather, expected] of cases) assert.equal(sky(weather), expected, JSON.stringify(weather));
});

test("dust in the air alone is not a sandstorm", () => {
  // Delhi on a calm clear night, as measured on 3 Oct 2026: dust 302, gusts 7.9 km/h, visibility 9.4 km.
  assert.equal(sky({ code: 0, isDay: false, dust: 302, gusts: 7.9, visibility: 9360 }), "night dark");
  assert.equal(sky({ code: 0, isDay: true, dust: 384, gusts: 4.7, visibility: 9560 }), "day");
  assert.equal(sky({ code: 0, isDay: true, dust: 600, gusts: 55, visibility: 9000 }), "day");   // windy but clear
  assert.equal(sky({ code: 0, isDay: true, dust: 600, gusts: 55, visibility: 1500 }), "sand");
  assert.equal(sky({ code: 0, isDay: false, dust: 600, gusts: 55, visibility: 1500 }), "sand dark");
});

test("before the weather is known, the clock decides", () => {
  assert.deepEqual([5, 6, 12, 18, 19, 23].map((h) => skyByClock(h).sky), ["night", "day", "day", "day", "night", "night"]);
});
