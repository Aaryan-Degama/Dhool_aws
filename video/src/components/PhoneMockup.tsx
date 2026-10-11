import type { CSSProperties, ReactNode } from "react";
import { CHARCOAL } from "../theme";

const SCREEN = 390 / 844;  // the captured screen's own shape: never stretched

/** A plain phone body around real screen content. `h` is the screen's height; x and y are its centre. */
export function PhoneMockup({ x, y, h, turn = 0, opacity = 1, children }: { x: number; y: number; h: number; turn?: number; opacity?: number; children: ReactNode }) {
  const w = h * SCREEN, rim = h * 0.014, corner = h * 0.062;
  const body: CSSProperties = {
    position: "absolute", left: x - w / 2 - rim, top: y - h / 2 - rim, width: w + 2 * rim, height: h + 2 * rim, padding: rim, boxSizing: "border-box",
    borderRadius: corner + rim, background: CHARCOAL, opacity,
    boxShadow: `0 ${h * 0.05}px ${h * 0.11}px rgba(23, 24, 28, 0.22), 0 ${h * 0.008}px ${h * 0.02}px rgba(23, 24, 28, 0.18)`,
    transform: `perspective(${h * 3.2}px) rotateY(${turn}deg)`,
  };
  return (
    <div style={body}>
      <div style={{ position: "relative", width: "100%", height: "100%", borderRadius: corner, overflow: "hidden", background: "#000" }}>{children}</div>
    </div>
  );
}
