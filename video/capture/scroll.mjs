// The Roof page scrolling on a phone, as a sequence of sharp stills (a screen recording is only 390 pixels wide).
//   LIVE_EMAIL=... LIVE_PASSWORD=... node video/capture/scroll.mjs      (run from the repo root, after capture.mjs)
import { chromium } from "../../web/node_modules/@playwright/test/index.mjs";
import { mkdirSync } from "node:fs";

const URL_ = process.env.LIVE_URL || "https://main.d18fp2anb76xgh.amplifyapp.com";
const OUT = new URL(`../public/${process.env.CAPTURE_SET || "captures"}/scroll/`, import.meta.url).pathname, FRAMES = 90, TO = 430;
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
const page = await context.newPage();
await page.goto(`${URL_}/?lang=en&sky=day`);
await page.locator('input[type="email"]').fill(process.env.LIVE_EMAIL);
await page.locator('input[type="password"]').fill(process.env.LIVE_PASSWORD);
await page.getByRole("button", { name: "Sign in", exact: true }).click();
await page.locator(".nav").waitFor({ timeout: 30000 });
await page.waitForTimeout(3500);
for (let i = 0; i < FRAMES; i++) {
  await page.evaluate((y) => window.scrollTo(0, y), Math.round((TO * i) / (FRAMES - 1)));
  await page.waitForTimeout(70);  // the page's own scroll effects settle
  await page.screenshot({ path: `${OUT}${String(i).padStart(3, "0")}.jpg`, type: "jpeg", quality: 88 });
}
await browser.close();
console.log(`${FRAMES} frames`);
