// A look at the hosted app as a signed-in homeowner sees it. Not part of `npm run e2e` (it needs the live
// site and a real login):  LIVE_URL=https://... LIVE_EMAIL=... LIVE_PASSWORD=... node e2e/live-check.js
import { chromium } from "@playwright/test";

const { LIVE_URL, LIVE_EMAIL, LIVE_PASSWORD } = process.env;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
const complaints = [];
page.on("console", (message) => { if (message.type() === "error") complaints.push(message.text()); });
page.on("pageerror", (error) => complaints.push(String(error)));

await page.goto(`${LIVE_URL}/?lang=en`);
await page.locator('input[type="email"]').fill(LIVE_EMAIL);
await page.locator('input[type="password"]').fill(LIVE_PASSWORD);
await page.getByRole("button", { name: "Sign in", exact: true }).click();
await page.locator(".home-name").waitFor({ timeout: 30000 });
await page.waitForTimeout(4000);  // the weather sky and the member list arrive after the verdict
console.log("home:", await page.locator(".home-name").innerText());
console.log("headline:", await page.locator("h1").first().innerText());
console.log("stale card:", await page.getByText("No new reading", { exact: false }).count());
console.log("useful question:", await page.getByText("Was this advice useful?").count());
console.log("sideways scroll:", await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth));
console.log("console errors:", JSON.stringify(complaints));
await page.screenshot({ path: process.env.SHOT || "live.png" });
await browser.close();
