// Captures of the app showing its own built-in sample homes (web/src/fixtures.js), one advice per sky, so the film
// can show what Dhool says in different situations. The app is the real one, run locally; the figures are the
// app's samples, not a real roof's, and the README says so. No login.
//   (cd web && npm run dev -- --port 5173 --strictPort) &   then, from the repo root:   node video/capture/sample.mjs
import { chromium } from "../../web/node_modules/@playwright/test/index.mjs";
import { mkdirSync, writeFileSync } from "node:fs";
import { API_URL } from "../../web/src/config.js";
import { FIXTURES } from "../../web/src/fixtures.js";

const OUT = new URL("../public/captures-sample/", import.meta.url).pathname;
mkdirSync(`${OUT}scroll`, { recursive: true });
// Which sample verdict is shown under which sky (the index into FIXTURES, and its headline).
const STORY = { day: [7, "Your solar is working"], cloud: [2, "Wash the panels"], rain: [4, "Wait for the rain"], storm: [4, "Wait for the rain"],
                sand: [5, "Wash after the dust storm"], snow: [1, "Call your vendor"], night: [8, "Your solar is working, after a wash that worked"] };
const house = { house_id: "sample", name: "Sharma house", role: "owner", kw: 3.3, wash_cost_rs: 50, tariff_rs: 7, linked: false, members: [] };
const history = { log: [{ date: "2026-09-25", kind: "said", verdict: "OK", cause: "ok", loss_pct: 1 }, { date: "2026-09-16", kind: "did", type: "wash", status: "verified" },
                        { date: "2026-09-12", kind: "said", verdict: "CLEAN", cause: "dust", loss_pct: 13 }], actions: [{ date: "2026-09-16", type: "wash", status: "verified" }] };
const VIEWS = { phone: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true }, desktop: { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 } };
const browser = await chromium.launch(), inventory = [];

async function open(view, sky, tab, scale) {
  const context = await browser.newContext({ ...VIEWS[view], ...(scale ? { deviceScaleFactor: scale } : {}) });
  const page = await context.newPage();
  await page.clock.setFixedTime(new Date("2026-09-26T10:00:00"));  // the day after the samples' last reading
  await page.addInitScript(() => localStorage.setItem("dhool.tokens", JSON.stringify({ access: "a.e30.c", refresh: "r" })));
  await page.route(`${API_URL}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    route.fulfill({ json: path.endsWith("/me") ? { houses: [house] } : path.endsWith("/verdict") ? FIXTURES[STORY[sky][0]] : path.endsWith("/history") ? history : house });
  });
  await page.goto(`http://localhost:5173/?lang=en&sky=${sky}#/${tab}`);
  await page.locator(".nav").waitFor();
  await page.waitForTimeout(3200);
  return page;
}
for (const sky of Object.keys(STORY)) {
  for (const view of ["phone", "desktop"]) {
    const page = await open(view, sky, "roof");
    await page.screenshot({ path: `${OUT}${view}-roof-${sky}.png` });
    inventory.push({ file: `${view}-roof-${sky}.png`, view, sky, shows: `Roof: ${STORY[sky][1]} (sample data)` });
    await page.context().close();
  }
}
for (const tab of ["history", "why"]) {
  const page = await open("desktop", "day", tab);
  await page.screenshot({ path: `${OUT}desktop-${tab}-day.png` });
  inventory.push({ file: `desktop-${tab}-day.png`, view: "desktop", sky: "day", shows: `${tab} page (sample data)` });
  await page.context().close();
}
{
  const page = await open("phone", "day", "roof", 2), far = await page.evaluate(() => document.documentElement.scrollHeight - innerHeight);
  for (let i = 0; i < 90; i++) {
    await page.evaluate((y) => window.scrollTo(0, y), Math.round((Math.min(430, far) * i) / 89));
    await page.waitForTimeout(70);
    await page.screenshot({ path: `${OUT}scroll/${String(i).padStart(3, "0")}.jpg`, type: "jpeg", quality: 88 });
  }
  inventory.push({ file: "scroll/000.jpg … 089.jpg", view: "phone", sky: "day", shows: "Roof scrolling (sample data)" });
}
await browser.close();
writeFileSync(`${OUT}inventory.json`, JSON.stringify(inventory, null, 2));
console.log(`${inventory.length} entries`);
