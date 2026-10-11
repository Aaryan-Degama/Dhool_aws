import { AbsoluteFill } from "remotion";
import { CHARCOAL, PAPER } from "../theme";
import { Rise, SubLine } from "./Reveal";

/** The site's own wordmark (the same strokes as web/src/visuals.jsx), and the question under it. */
export const Wordmark = ({ height = 120, color = CHARCOAL }: { height?: number; color?: string }) => (
  <svg viewBox="0 0 92 40" height={height} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 7V33Q25 30 24 19Q22 8 6 7M35 5V33M35 25Q41 16 47 33M86 5V33" />
    <circle cx="59" cy="27" r="6.5" fill={color} stroke="none" /><circle cx="73" cy="27" r="6.5" fill={color} stroke="none" />
  </svg>
);

export const ClosingBrand = () => (
  <AbsoluteFill style={{ background: PAPER, alignItems: "center", justifyContent: "center", gap: 28 }}>
    <Rise><Wordmark /></Rise>
    <Rise from={14}><SubLine>Is your solar actually working?</SubLine></Rise>
  </AbsoluteFill>
);
