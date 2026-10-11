// Type that arrives: a headline typed out behind a cursor, a line that rises into place, a small serif line.
import type { CSSProperties, ReactNode } from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { CHARCOAL, SANS, SERIF, SOFT } from "../theme";

const HEAD: CSSProperties = { margin: 0, font: `700 96px/1.02 ${SANS}`, letterSpacing: "-0.035em", color: CHARCOAL, whiteSpace: "pre" };

/** Typed one letter at a time from `from`, about `perLetter` frames each; the cursor blinks, then goes. */
export function Typed({ text, from = 0, perLetter = 1.6, size = 96, color = CHARCOAL, style }: { text: string; from?: number; perLetter?: number; size?: number; color?: string; style?: CSSProperties }) {
  const frame = useCurrentFrame() - from;
  const shown = Math.max(0, Math.min(text.length, Math.floor(frame / perLetter)));
  const done = frame > text.length * perLetter + 30;
  const cursor = !done && frame >= 0 && (shown < text.length || Math.floor(frame / 14) % 2 === 0);
  return (
    <p style={{ ...HEAD, fontSize: size, color, ...style }}>
      {text.slice(0, shown)}
      <span style={{ display: "inline-block", width: size * 0.045, height: size * 0.82, marginLeft: size * 0.04, verticalAlign: "-0.08em", background: color, opacity: cursor ? 1 : 0 }} />
      <span style={{ opacity: 0 }}>{text.slice(shown)}</span>
    </p>
  );
}

/** Rises a little and fades in from `from`; fades out before `until` when that is given. */
export function Rise({ from = 0, until, children, style }: { from?: number; until?: number; children: ReactNode; style?: CSSProperties }) {
  const frame = useCurrentFrame();
  const arrive = interpolate(frame, [from, from + 18], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const leave = until == null ? 1 : interpolate(frame, [until - 12, until], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <div style={{ opacity: arrive * leave, transform: `translateY(${(1 - arrive) * 22}px)`, ...style }}>{children}</div>;
}

export const Headline = ({ children, size = 96, color = CHARCOAL }: { children: ReactNode; size?: number; color?: string }) =>
  <p style={{ ...HEAD, fontSize: size, color, whiteSpace: "normal" }}>{children}</p>;

export const SubLine = ({ children, color = SOFT, size = 34 }: { children: ReactNode; color?: string; size?: number }) =>
  <p style={{ margin: 0, font: `italic 400 ${size}px/1.35 ${SERIF}`, color }}>{children}</p>;
