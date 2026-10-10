import { readFileSync } from "node:fs";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// `vite preview` serves the built app with the headers Amplify will send (../customHttp.yml), so the browser
// test (e2e/) fails on anything the Content-Security-Policy would block on the live site.
const yml = readFileSync(new URL("../customHttp.yml", import.meta.url), "utf8");
const headers = Object.fromEntries([...yml.matchAll(/key: '([^']+)'\s+value: "([^"]+)"/g)].map((m) => [m[1], m[2]]));

export default defineConfig({ plugins: [react()], preview: { headers } });
