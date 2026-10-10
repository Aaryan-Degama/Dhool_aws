// The headers Amplify serves the app with (customHttp.yml, at the repo root) must let the app reach the
// backend it is configured for, and nothing it does not need. Run with `npm test`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { API_URL, REGION } from "./config.js";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const csp = read("../../customHttp.yml").match(/key: 'Content-Security-Policy'\s+value: "([^"]+)"/)[1];

test("the Content-Security-Policy allows this deployment's API, sign-in and uploads", () => {
  const connect = csp.match(/connect-src ([^;]+)/)[1].split(" ");
  for (const host of [API_URL, `https://cognito-idp.${REGION}.amazonaws.com`, `https://*.s3.${REGION}.amazonaws.com`]) {
    assert.ok(connect.includes(host), host);
  }
});

test("the page loads its own files only, and cannot be framed", () => {
  assert.match(csp, /^default-src 'self';/);
  assert.match(csp, /frame-ancestors 'none'/);
  assert.doesNotMatch(csp, /unsafe-inline|unsafe-eval/);
  assert.doesNotMatch(read("../index.html"), /https?:\/\//);  // no font, script or style from another site
});
