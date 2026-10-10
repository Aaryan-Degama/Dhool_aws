// One look at the app in a real browser, phone-sized. Run with `npm run e2e` (servers: playwright.config.js).
//   The dev server's /#preview: every verdict state from sample data, in English and in Hindi.
//   The built app as Amplify will serve it: nothing its Content-Security-Policy blocks, nothing from another site.
import { expect, test } from "@playwright/test";
import { API_URL, REGION } from "../src/config.js";
import { FIXTURES } from "../src/fixtures.js";
import { HI } from "../src/hi.js";

const DEV = "http://localhost:5173", BUILT = "http://localhost:4173";
const HEADLINES = ["Your solar has stopped", "Call your vendor", "Wash the panels", "Don't wash. It's haze.", "Your solar is working",
  "Generation History", "Washes and vendor visits", "System size"];

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

  test(`a month opens to its weeks and a week to its days in ${lang}`, async ({ page }) => {
    await page.goto(`${DEV}/?lang=${lang}#preview`);
    const months = page.locator(".months").first();
    const figure = months.getByText(String(FIXTURES[0].daily_kwh["2026-09-23"]), { exact: true });
    await expect(figure).toBeHidden();
    await months.locator("> li > details > summary").last().click();  // September, the month still running
    await expect(figure).toBeHidden();
    const week = months.locator("summary").filter({ hasText: /^22–25 / });
    await expect(week.getByText(lang === "hi" ? HI["Readings on {n} of {total} days"] : "Readings on")).toHaveCount(0);  // all four days read
    await week.click();
    await expect(figure).toBeVisible();
    await expect(months.locator("> li").last().locator(".weeks summary")).toHaveCount(4);  // nothing after the last reading
    await week.click();
    await expect(figure).toBeHidden();
    // A verdict stored before the days were sent: its months are there and do not open.
    await expect(page.locator(".months").nth(1)).toBeVisible();
    await expect(page.locator(".months").nth(1).locator("summary")).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
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

  test("a screen that breaks says so and offers to open the app again, in place of a blank page", async ({ page }) => {
    // Signed in, and the API answers with a list the app cannot draw.
    await page.addInitScript(() => localStorage.setItem("dhool.tokens", JSON.stringify({ access: "a.e30.c", refresh: "r" })));
    await page.route(/^https:\/\//, (route) => route.fulfill({ status: 200, contentType: "application/json", body: '{"houses":[null]}',
      headers: { "access-control-allow-origin": "*" } }));
    await page.goto(`${BUILT}/?lang=hi`);
    await expect(page.getByRole("heading", { name: HI["Something went wrong"] })).toBeVisible();
    await expect(page.getByRole("button", { name: HI["Open again"] })).toBeVisible();
  });

  test("a typed reading whose verdict never arrives ends in 'taking longer than usual', not in silence", async ({ page }) => {
    const sent = [];
    const house = { house_id: "h1", name: "Sharma house", role: "owner" };
    const answers = {
      "GET /me": { houses: [house] },
      "GET /houses/h1": { ...house, kw: 3, lat: 28.61, lon: 77.21, tilt: 20, azimuth: 180, wash_cost_rs: 50, tariff_rs: 7, linked: false, members: [] },
      "GET /houses/h1/verdict": { ...FIXTURES.find((v) => v.verdict === "OK"), computed_at: 111 },  // every time: the new run never lands
      "GET /houses/h1/history": { log: [] },
      "POST /houses/h1/readings": { saved: 1 },
    };
    await page.addInitScript(() => localStorage.setItem("dhool.tokens", JSON.stringify({ access: "a.e30.c", refresh: "r" })));
    await page.route(/^https:\/\//, (route) => {
      const request = route.request();
      if (request.method() === "POST") sent.push(request.postDataJSON());
      return route.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify(answers[`${request.method()} ${new URL(request.url()).pathname}`] ?? {}) });
    });
    await page.clock.install();
    await page.goto(`${BUILT}/?lang=en#/setup`);
    await page.getByLabel("Units made (kWh)").fill("5,5");
    await page.getByRole("button", { name: "Save reading" }).click();
    await expect(page.getByRole("heading", { name: "Working it out" })).toBeVisible();
    expect(sent[0].kwh).toBe(5.5);  // the comma was taken as the decimal point
    for (let look = 0; look < 12; look++) {  // three minutes of looking, in a second: each jump lets one look happen
      await page.clock.fastForward(31_000);
      await page.waitForTimeout(40);
    }
    await expect(page.getByText("This is taking longer than usual.", { exact: false })).toBeVisible();
    await expect(page.getByText("Your solar is working", { exact: true }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Check again" })).toBeVisible();
  });

  test("'was this advice useful' sends the answer for that day's verdict, survives a failed try, and is not asked twice", async ({ page }) => {
    const sent = [];
    const house = { house_id: "h1", name: "Sharma house", role: "owner" };
    const verdict = { ...FIXTURES.find((v) => v.verdict === "OK"), computed_at: 111 };
    const answers = {
      "GET /me": { houses: [house] },
      "GET /houses/h1": { ...house, kw: 3, lat: 28.61, lon: 77.21, tilt: 20, azimuth: 180, wash_cost_rs: 50, tariff_rs: 7, linked: false, members: [] },
      "GET /houses/h1/verdict": verdict,
    };
    await page.addInitScript(() => localStorage.setItem("dhool.tokens", JSON.stringify({ access: "a.e30.c", refresh: "r" })));
    await page.route(/^https:\/\//, (route) => {
      const request = route.request(), path = new URL(request.url()).pathname;
      if (request.method() === "POST") sent.push([path, request.postDataJSON()]);
      const broken = request.method() === "POST" && sent.length === 1;  // the first answer does not get through
      return route.fulfill({ status: broken ? 500 : 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify(broken ? { error: "Something went wrong" } : answers[`${request.method()} ${path}`] ?? {}) });
    });
    await page.goto(`${BUILT}/?lang=en`);
    const question = page.getByRole("group", { name: "Was this advice useful?" });
    await question.getByRole("button", { name: "No" }).click();
    await expect(page.getByRole("alert")).toHaveText("Something went wrong");
    await question.getByRole("button", { name: "Yes" }).click();  // still there to press
    await expect(page.getByText("Thanks for telling Dhool.")).toBeVisible();
    await expect(question).toHaveCount(0);
    expect(sent).toEqual([["/houses/h1/feedback", { date: verdict.as_of, helpful: false }],
      ["/houses/h1/feedback", { date: verdict.as_of, helpful: true }]]);
    await page.reload();  // the phone remembers the day it answered for
    await expect(page.getByText("Your solar is working", { exact: true }).first()).toBeVisible();
    await expect(question).toHaveCount(0);
    await expect(page.getByText("Thanks for telling Dhool.")).toHaveCount(0);
  });
});
