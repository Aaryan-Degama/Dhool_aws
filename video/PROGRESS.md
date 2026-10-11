# Dhool demo video: progress notes

Brief: `ref/brief.md` (in the main checkout, `/home/naukarji/Github/Dhool_aws/ref/`). Plan approved 11 Oct 2026.

## Decisions that differ from the brief
- Narration is recorded by the owner (no Fish Audio key here). I supply script and cue sheet; the recording goes in `ref/voiceover-raw.wav`.
- The Snatch promo's audio is NOT used as music (the brief forbids it; it is someone else's track). Music waits for a track the owner has the right to use.
- The six weather scenes are real app states: the site has seven skies and a `?sky=` switch.
- The login is passed as `LIVE_EMAIL` / `LIVE_PASSWORD` at run time, never written down.

## Phase 1: done (11 Oct 2026), waiting for approval
- `video/capture/capture.mjs`: signs in on the live site, saves 29 captures to `video/public/captures/` with `inventory.json`. Run from the repo root: `LIVE_EMAIL=… LIVE_PASSWORD=… node video/capture/capture.mjs`. No page errors.
  - Phone 390×844 @3x (1170×2532): Roof first screen and scrolled, under day, cloud, rain, storm, sand, snow, night; History, Why, Setup under day.
  - Desktop 1440×900 @2x (2880×1800): Roof under the same seven skies; History, Why, Setup under day.
  - Recordings (WebM, CSS-pixel size): `phone-interactions.webm`, `desktop-interactions.webm`: turning the array, scrolling (phone) or the chart's 7/30/90 switch (desktop), then each tab.
- The account's home ("Degama") currently reads "Checking the repair", 85% of normal, about ₹658 a week lost. Every capture shows that state.
- Captures are not committed (owner's decision): they show a real account's home and figures, and the repo is public.
- Reference video (57.3 s, 1920×1080, 30 fps): contact sheet in `video/ref-frames/sheet-2s.png` (git-ignored). Cuts at 9.1, 12.7, 16.9 s, a burst of ~0.75 s cuts from 17.6 to 22.9 s, then one long section to 44.8 s. Tempo not measured (no audio-analysis library installed).
- Pronunciation clip (13.2 s): four bursts of sound, not five: 1.0–3.5 s (long), 5.1–5.9, 8.3–8.9, 10.8–11.4 s. Not transcribed (no speech-to-text here).

## Phase 2: full cut built and shown to the owner (11 Oct 2026)
- Owner's decisions: keep the Degama captures ("Checking the repair"); no music for now; captures stay out of git;
  keep my on-screen lines; no rooftop silhouette; the phone must not cover the desktop chart; use a real scroll.
- Remotion 4 + React 19 + TypeScript in `video/`. Remotion's browser download is blocked on this network: render with
  `--browser-executable ~/.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell`.
- `src/timeline.ts` holds everything that moves: scene starts, the phone's and the desktop window's keyframes,
  which sky is on the phone's screen when (`SCREENS`), the scroll (`scrollAt`), the desktop pages (`PAGES`).
  `src/Film.tsx` layers background rooms, the desktop window, the one phone, each scene's type, and the audio.
- Scroll: `capture/scroll.mjs` takes 90 stills of the live Roof page scrolling (780x1688), played down and back in
  scene 3. Sharper than the 390-pixel recording, so the recording is not used.
- Weather: on the phone it is the app's real screen under each sky; around the phone a quiet room of the same
  light, with rain, dust and snow drawn behind the phone only.
- Sound: `audio/make-sound-design.sh` makes `public/audio/sound-design.wav` from noise with FFmpeg (whoosh at
  each scene change, rain, wind). No narration and no music yet.
- `output/dhool-product-demo.mp4`: 70.0 s, 1920x1080, 30 fps, H.264 yuv420p, AAC 48 kHz. `output/montage.png`: 24 frames.
- Fixed after the first full render: the desktop window was blank in scene 2 (its page list started at frame
  1530); the line under the window in scene 8 overlapped it.
- Not done: narration (owner records `ref/voiceover-raw.wav`), music (owner supplies), `voiceover.wav`,
  the music-only render, a second QC pass with audio.

- Owner's review, 11 Oct: the browser window is labelled "Dhool" (no address); the home name and picture are
  blurred in the film (`Hide` in `Film.tsx`); `CAPTURE_SET` and `AUDIO` switches added to `timeline.ts`.
  Audio is sound design only, -25.8 LUFS integrated.

- Owner, 11 Oct: every scene read 85% "Checking the repair"; show different situations, from localhost. Done:
  `capture/sample.mjs` captures the local app on its built-in samples into `public/captures-sample/` (clock held
  at 26 Sept 2026, the day after the samples' last reading). Day: working 99%. Cloud: wash the panels 85%. Rain:
  wait for the rain 91%. Dust: wash after the dust storm 91%. Snow: call your vendor 67%, dead panels. Night:
  working 99%. `CAPTURE_SET` now points there; the blur applies only to the real-account set. Sub-lines in
  scenes 3-7 rewritten to say what each screen advises.

- Owner, 11 Oct (asked twice): use the reference promo's audio as music. Done as a separate, switchable file
  (`public/audio/music.wav`, `AUDIO.music`). It is NOT licensed: README says so. To be replaced before publishing.

## Next
Place the narration when it arrives, mix, re-render, QC, write the final README sections.
