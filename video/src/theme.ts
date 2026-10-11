// Colours and type for the film. The sans is the site's own face (Anek Devanagari, public/fonts/, SIL OFL);
// the italic serif for sub-lines is Noto Serif, which must be installed on the machine that renders.
import { continueRender, delayRender, staticFile } from "remotion";

export const PAPER = "#f7f6f3";      // the bright base
export const CHARCOAL = "#17181c";   // headlines, the phone's body
export const SOFT = "#6d6f76";       // sub-lines
export const SOLAR = "#ffc21a";      // the site's own yellow, used sparingly
export const SANS = '"Anek Devanagari", system-ui, sans-serif';
export const SERIF = '"Noto Serif", "Liberation Serif", Georgia, serif';
export const W = 1920, H = 1080, FPS = 30;

const wait = delayRender("the site's font");
new FontFace("Anek Devanagari", `url(${staticFile("fonts/anek-devanagari-latin.woff2")})`, { weight: "100 800", stretch: "75% 125%" })
  .load().then((face) => { document.fonts.add(face); continueRender(wait); }).catch(() => continueRender(wait));
