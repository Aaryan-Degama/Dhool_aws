// The browser test (e2e/): Chromium only, at phone width, against two servers started here.
//   5173  the dev server, where /#preview shows every verdict state from sample data without signing in
//   4173  the built app under `vite preview`, served with the headers Amplify will send (../customHttp.yml)
import { defineConfig } from "@playwright/test";

const fresh = Boolean(process.env.CI);  // on a laptop, a server that is already running is used as it is

export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  forbidOnly: fresh,
  reporter: "line",
  use: { viewport: { width: 390, height: 844 } },
  webServer: [
    { command: "npm run dev -- --port 5173 --strictPort", url: "http://localhost:5173", reuseExistingServer: !fresh },
    { command: "npm run build && npm run preview -- --port 4173 --strictPort", url: "http://localhost:4173", reuseExistingServer: !fresh },
  ],
});
