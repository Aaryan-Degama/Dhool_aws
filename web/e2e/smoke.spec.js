// One look at the app in a real browser, phone-sized. Run with `npm run e2e` (servers: playwright.config.js).
//   The dev server's /#preview: every verdict state from sample data, in English and in Hindi.
//   The built app as Amplify will serve it: nothing its Content-Security-Policy blocks, nothing from another site.
import { expect, test } from "@playwright/test";
import { API_URL, REGION } from "../src/config.js";
import { HI } from "../src/hi.js";

const DEV = "http://localhost:5173", BUILT = "http://localhost:4173";
const HEADLINES = ["Your solar has stopped", "Call your vendor", "Wash the panels", "Don't wash. It's haze.", "Your solar is working"];

/** Everything the browser complains about while the page is open. A blocked file or script is one of them. */
function complaints(page) {
  const seen = [];
  page.on("console", (message) => { if (message.type() === "error") seen.push(message.text()); });
  page.on("pageerror", (error) => seen.push(String(error)));
  return seen;
}

for (const lang of ["en", "hi"]) {
  test(`every verdict state shows in ${lang}, with no sideways scroll`, async ({ page }) => {
    const seen = complaints(page);
    await page.goto(`${DEV}/?lang=${lang}#preview`);
    await expect(page.locator("html")).toHaveAttribute("lang", lang);
    for (const line of HEADLINES) {
      await expect(page.getByText(lang === "hi" ? HI[line] : line, { exact: true }).first()).toBeVisible();
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
    expect(seen).toEqual([]);
  });
}

test("the built app loads under the headers Amplify will send, from its own files alone", async ({ page }) => {
  const seen = complaints(page), elsewhere = [], fonts = [];
  page.on("request", (request) => { if (!request.url().startsWith(BUILT)) elsewhere.push(request.url()); });
  page.on("response", (response) => { if (response.url().includes("/fonts/")) fonts.push(response.status()); });
  const response = await page.goto(`${BUILT}/?lang=en`);
  expect(response.headers()["content-security-policy"]).toContain("default-src 'self'");
  expect(response.headers()["x-content-type-options"]).toBe("nosniff");
  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  expect(await page.evaluate(() => document.fonts.check('16px "Anek Devanagari"'))).toBe(true);
  await page.evaluate(() => navigator.serviceWorker.ready);  // the offline shell is in: it fetched every file it keeps
  expect(fonts.length).toBeGreaterThan(0);
  expect(fonts.every((status) => status === 200)).toBe(true);
  expect(seen).toEqual([]);
  expect(elsewhere).toEqual([]);
});

test.describe("what the page may talk to", () => {
  test.use({ serviceWorkers: "block" });  // so the stand-in answers below reach the page

  test("the backend, sign-in, uploads and the weather, and no one else", async ({ page }) => {
    // Every other site answers 200 here: what fails below is stopped by the policy, before any network.
    await page.route(/^https:\/\//, (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{}",
      headers: { "access-control-allow-origin": "*" } }));
    await page.goto(BUILT);
    const reached = (url) => page.evaluate((address) => fetch(address).then(() => true, () => false), url);
    const allowed = [`${API_URL}/me`, `https://cognito-idp.${REGION}.amazonaws.com/`, `https://a-bucket.s3.${REGION}.amazonaws.com/`,
      "https://api.open-meteo.com/v1/forecast", "https://air-quality-api.open-meteo.com/v1/air-quality"];
    for (const url of allowed) expect(await reached(url), url).toBe(true);
    for (const url of ["https://example.com/", "https://fonts.googleapis.com/css2"]) expect(await reached(url), url).toBe(false);
  });
});
