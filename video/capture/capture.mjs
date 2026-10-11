// Captures of the live Dhool site for the demo video: real pages, signed in as a real account.
//   LIVE_EMAIL=... LIVE_PASSWORD=... node video/capture/capture.mjs      (run from the repo root)
// The login is read from the environment and never written anywhere; the saved session (.auth.json) is git-ignored.
// Every sky is the app's own: `?sky=` is the site's documented switch for showing one (CLAUDE.md, Commands).
import { chromium } from "../../web/node_modules/@playwright/test/index.mjs";
import { mkdirSync, renameSync, writeFileSync } from "node:fs";

const URL_ = process.env.LIVE_URL || "https://main.d18fp2anb76xgh.amplifyapp.com";
const { LIVE_EMAIL, LIVE_PASSWORD } = process.env;
if (!LIVE_EMAIL || !LIVE_PASSWORD) throw new Error("Set LIVE_EMAIL and LIVE_PASSWORD");
const OUT = new URL(`../public/${process.env.CAPTURE_SET || "captures"}/`, import.meta.url).pathname, AUTH = new URL(".auth.json", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const SKIES = ["day", "cloud", "rain", "storm", "sand", "snow", "night"];
const VIEWS = { phone: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true }, desktop: { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 } };
const inventory = [], complaints = [];
const browser = await chromium.launch();

const open = async (context, sky, tab) => {
  const page = context.pages()[0] || await context.newPage();
  page.on("pageerror", (e) => complaints.push(String(e)));
  await page.goto(`${URL_}/?lang=en&sky=${sky}#/${tab}`);
  await page.reload();  // a change of ?sky alone does not reload a hash-routed page
  await page.locator(".nav").waitFor({ timeout: 30000 });
  await page.waitForTimeout(3200);  // the verdict, then the arrival sequence
  return page;
};
const shot = async (page, name, view, sky, shows, options = {}) => {
  await page.screenshot({ path: `${OUT}${name}.png`, ...options });
  inventory.push({ file: `${name}.png`, view, sky, shows });
};

// Sign in once, keep the session for the rest.
{
  const context = await browser.newContext(VIEWS.phone), page = await context.newPage();
  await page.goto(`${URL_}/?lang=en`);
  await page.locator('input[type="email"]').fill(LIVE_EMAIL);
  await page.locator('input[type="password"]').fill(LIVE_PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.locator(".home-name").first().waitFor({ timeout: 30000 });
  console.log("signed in; home:", await page.locator(".home-name").first().innerText(), "| headline:", await page.locator("h1").first().innerText());
  await context.storageState({ path: AUTH });
  await context.close();
}

for (const [view, device] of Object.entries(VIEWS)) {
  const context = await browser.newContext({ ...device, storageState: AUTH });
  for (const sky of SKIES) {
    const page = await open(context, sky, "roof");
    await shot(page, `${view}-roof-${sky}`, view, sky, "Roof, first screen");
    if (view === "phone") {
      await page.evaluate(() => window.scrollTo(0, 420)); await page.waitForTimeout(500);
      await shot(page, `${view}-roof-${sky}-scrolled`, view, sky, "Roof, scrolled to the advice");
    }
  }
  for (const tab of ["history", "why", "setup"]) {
    const page = await open(context, "day", tab);
    await shot(page, `${view}-${tab}-day`, view, "day", `${tab} page`);
  }
  await context.close();
}

// Recordings of real interactions (WebM, at CSS-pixel size: stills above are the sharp ones).
for (const [view, device] of Object.entries(VIEWS)) {
  const context = await browser.newContext({ ...device, storageState: AUTH, recordVideo: { dir: OUT, size: device.viewport } });
  const page = await open(context, "day", "roof");
  const { width, height } = device.viewport;
  const box = await page.locator(".pm").first().boundingBox();
  const x = Math.min(width - 40, box.x + box.width * 0.6), y = Math.min(height - 80, box.y + box.height * 0.55);
  await page.mouse.move(x, y); await page.mouse.down();
  for (const dx of [-140, 140, 0]) { await page.mouse.move(x + dx, y, { steps: 45 }); await page.waitForTimeout(250); }
  await page.mouse.up(); await page.waitForTimeout(600);
  if (view === "desktop") {
    for (const n of [1, 2, 0]) { await page.locator(".trend .switch button").nth(n).click(); await page.waitForTimeout(900); }
  } else {
    for (const to of [300, 700, 0]) { await page.evaluate((top) => window.scrollTo({ top, behavior: "smooth" }), to); await page.waitForTimeout(1300); }
  }
  for (const name of ["History", "Why", "Setup", "Roof"]) { await page.locator(".nav").getByRole("button", { name, exact: true }).click(); await page.waitForTimeout(1300); }
  const video = page.video();
  await context.close();
  renameSync(await video.path(), `${OUT}${view}-interactions.webm`);
  inventory.push({ file: `${view}-interactions.webm`, view, sky: "day", shows: "turning the array, " + (view === "desktop" ? "the chart's 7/30/90 switch" : "scrolling Roof") + ", then each tab" });
}
await browser.close();
writeFileSync(`${OUT}inventory.json`, JSON.stringify(inventory, null, 2));
console.log(`${inventory.length} captures; page errors: ${JSON.stringify(complaints)}`);
