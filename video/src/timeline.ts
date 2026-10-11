// One timeline for the whole film: where each scene starts, and where the phone and the desktop window are at
// every frame. Scenes read from here, so nothing jumps at a boundary: the phone is one object moving through
// all of them.
import { Easing, interpolate } from "remotion";

const s = (seconds: number) => Math.round(seconds * 30);
export const SCENES = {
  hook: { from: s(0), length: s(6) },
  meet: { from: s(6), length: s(7) },
  sunny: { from: s(13), length: s(8) },
  clouds: { from: s(21), length: s(10) },
  dust: { from: s(31), length: s(7) },
  snow: { from: s(38), length: s(6) },
  night: { from: s(44), length: s(7) },
  desktop: { from: s(51), length: s(8) },
  payoff: { from: s(59), length: s(7) },
  close: { from: s(66), length: s(4) },
} as const;
export const TOTAL = s(70), DRAFT = SCENES.clouds.from;

// Which set of captures the film is cut from: a folder in public/. To recut from another account (say one whose
// roof reads "Your solar is working"), capture into a new folder and name it here; no scene changes.
//   "captures"         the owner's real account on the live site (capture.mjs, scroll.mjs): one state throughout
//   "captures-sample"  the app's built-in sample homes, run locally (sample.mjs): a different advice under each sky
export const CAPTURE_SET: string = "captures-sample";
export const HIDE_ACCOUNT = CAPTURE_SET === "captures";  // a real account's home name is blurred; the sample's is not
// Sound: the generated sound design is always on. The other two are separate files in public/audio/, switched on
// here once they exist (voiceover.wav, music.wav), so either can be replaced or left out without a re-edit.
export const AUDIO = { voiceover: false, music: false };

type Key = { at: number; x: number; y: number; h: number; turn: number; show: number };
/** A value eased between keyframes; held before the first and after the last. */
function along<K extends { at: number }>(keys: K[], frame: number, pick: (k: K) => number) {
  return interpolate(frame, keys.map((k) => k.at), keys.map(pick), { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
}

// The phone: centre (x, y) and height in pixels, a turn about its upright axis in degrees, and opacity.
const PHONE: Key[] = [
  { at: 0, x: 960, y: 1640, h: 820, turn: 0, show: 0 },
  { at: 96, x: 960, y: 1640, h: 820, turn: 0, show: 1 },
  { at: 150, x: 960, y: 690, h: 800, turn: 0, show: 1 },      // rises under the headline
  { at: 186, x: 960, y: 690, h: 800, turn: 0, show: 1 },
  { at: 246, x: 1580, y: 560, h: 840, turn: -12, show: 1 },   // steps aside, clear of the desktop site
  { at: 330, x: 1580, y: 560, h: 840, turn: -12, show: 1 },
  { at: 400, x: 1330, y: 560, h: 900, turn: -5, show: 1 },    // forward, as the site falls back
  { at: 470, x: 1330, y: 560, h: 900, turn: -5, show: 1 },
  { at: 610, x: 1330, y: 640, h: 1120, turn: 0, show: 1 },    // the slow push across the figures
  { at: 640, x: 1330, y: 640, h: 1120, turn: 0, show: 1 },
  { at: 710, x: 1330, y: 560, h: 900, turn: -5, show: 1 },    // back, as the cloud comes over
  { at: 920, x: 1330, y: 560, h: 900, turn: -5, show: 1 },
  { at: 990, x: 1270, y: 560, h: 980, turn: 5, show: 1 },     // closer, into the dust
  { at: 1130, x: 1270, y: 560, h: 980, turn: 5, show: 1 },
  { at: 1200, x: 620, y: 560, h: 900, turn: 6, show: 1 },     // across the frame, into the snow
  { at: 1310, x: 620, y: 560, h: 900, turn: 6, show: 1 },
  { at: 1380, x: 960, y: 560, h: 900, turn: 0, show: 1 },     // centre, and still, for the night
  { at: 1525, x: 960, y: 560, h: 900, turn: 0, show: 1 },
  { at: 1600, x: 1680, y: 740, h: 500, turn: -14, show: 1 },  // small, beside the desktop site
  { at: 1750, x: 1680, y: 740, h: 500, turn: -14, show: 1 },
  { at: 1820, x: 960, y: 560, h: 940, turn: 0, show: 1 },     // back to the middle, as the hero
  { at: 1978, x: 960, y: 560, h: 940, turn: 0, show: 1 },
  { at: 2004, x: 960, y: 540, h: 900, turn: 0, show: 0 },
];
export const phoneAt = (frame: number) => ({
  x: along(PHONE, frame, (k) => k.x), y: along(PHONE, frame, (k) => k.y), h: along(PHONE, frame, (k) => k.h),
  turn: along(PHONE, frame, (k) => k.turn), show: along(PHONE, frame, (k) => k.show),
});

// The desktop window: left edge, top, width, opacity. It appears twice: behind the phone, then on its own.
const DESK = [
  { at: 190, x: 40, y: 250, w: 1100, show: 0 },
  { at: 250, x: 90, y: 150, w: 1180, show: 1 },
  { at: 330, x: 90, y: 150, w: 1180, show: 1 },
  { at: 400, x: 20, y: 190, w: 1080, show: 0 },
  { at: 1530, x: 200, y: 200, w: 1260, show: 0 },
  { at: 1600, x: 90, y: 60, w: 1400, show: 1 },
  { at: 1750, x: 90, y: 60, w: 1400, show: 1 },
  { at: 1815, x: 160, y: 140, w: 1320, show: 0 },
];
export const deskAt = (frame: number) => ({
  x: along(DESK, frame, (k) => k.x), y: along(DESK, frame, (k) => k.y), w: along(DESK, frame, (k) => k.w), show: along(DESK, frame, (k) => k.show),
});

// What the phone shows: the real Roof page under each sky, each fading in over `fade` frames. The page is the
// same under every sky, so a fade between two of them is the light changing and nothing else.
export const SCREENS = [
  { at: 0, sky: "day", fade: 1 },
  { at: 715, sky: "cloud", fade: 50 },
  { at: 790, sky: "rain", fade: 36 },
  { at: 935, sky: "sand", fade: 40 },
  { at: 1145, sky: "snow", fade: 40 },
  { at: 1325, sky: "night", fade: 60 },
  { at: 1540, sky: "day", fade: 40 },
  { at: 1835, sky: "cloud", fade: 10 }, { at: 1860, sky: "rain", fade: 10 }, { at: 1885, sky: "sand", fade: 10 },
  { at: 1910, sky: "snow", fade: 10 }, { at: 1935, sky: "night", fade: 10 }, { at: 1960, sky: "day", fade: 12 },
];
// The Roof page scrolling (captures/scroll/000…089.jpg): down during the push, back up as the phone pulls away.
const SCROLL = [{ at: 480, i: 0 }, { at: 600, i: 89 }, { at: 645, i: 89 }, { at: 705, i: 0 }];
export const scrollAt = (frame: number) => (frame < 480 || frame > 705 ? null : Math.round(along(SCROLL, frame, (k) => k.i)));
// The desktop site's pages, in its second appearance.
export const PAGES = [{ at: 0, page: "roof", fade: 1 }, { at: 1655, page: "history", fade: 16 }, { at: 1705, page: "why", fade: 16 }];
