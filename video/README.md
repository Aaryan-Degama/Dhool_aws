# Dhool product demo video

A Remotion project. Brief: `ref/brief.md`; progress and decisions: `PROGRESS.md`.

## Render
```
cd video
npm install
npx remotion render src/index.ts Draft output/draft-scenes-1-3.mp4 --codec h264 --pixel-format yuv420p   # scenes 1-3
npx remotion render src/index.ts Demo  output/dhool-product-demo.mp4 --codec h264 --pixel-format yuv420p --audio-codec aac
```
If Remotion cannot download its own browser (a blocked network), add
`--browser-executable <path to a chrome-headless-shell>`; Playwright's copy under `~/.cache/ms-playwright/` works.

## Assets
- `public/captures/`: screenshots and recordings of the live site. **Not in git** (they show a real account's home).
  Make them again from the repo root, signed in as any account with a home:
  `LIVE_EMAIL=<email> LIVE_PASSWORD=<password> node video/capture/capture.mjs`
  The login is read from the environment only. Each sky is the app's own, shown with the site's `?sky=` switch.
- `public/fonts/`: Anek Devanagari, the site's own face (SIL OFL 1.1, licence beside it).
- Sub-lines use Noto Serif Italic (SIL OFL), which must be installed on the machine that renders.

  The scrolling screen in scene 3 is 90 more stills: `LIVE_EMAIL=<email> LIVE_PASSWORD=<password> node video/capture/scroll.mjs`

- **The film is cut from `public/captures-sample/`**: the real app run locally, showing its own built-in sample
  homes (`web/src/fixtures.js`), a different advice under each sky. The interface is real; the figures are the
  app's samples, not a real roof's. Make them again with the dev server running
  (`cd web && npm run dev -- --port 5173 --strictPort`), then `node video/capture/sample.mjs`. No login.
  `public/captures/` (the owner's real account, one state throughout) is the other set; `CAPTURE_SET` in
  `src/timeline.ts` chooses.
- **Another account's captures** (say one whose roof reads "Your solar is working"): run both capture scripts
  with `CAPTURE_SET=captures-working` added, then set `CAPTURE_SET` in `src/timeline.ts` to that name and render.
- The film blurs the account's home name and picture (top right of every page) and labels the browser window
  "Dhool" in place of the site's address. Both are done in `src/Film.tsx`; the captures are left as taken.

## Audio
- Sound design: `bash video/audio/make-sound-design.sh` writes `public/audio/sound-design.wav` (made from noise
  with FFmpeg; nothing sampled, nothing to license). Run it before rendering; the file is not in git.
- Narration and music are separate files, off until they exist: put `voiceover.wav` and `music.wav` (70 s,
  starting at the film's first frame) in `public/audio/` and switch each on in `AUDIO` in `src/timeline.ts`.
  Music source and licence: none yet (no music in the film).

## Needs
Node 22, FFmpeg, a login to the live site for captures. No API keys.
