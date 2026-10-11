import type { ReactNode } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

/** Fades its children in over the frames before `from` and out over the frames after `to`: neighbours overlap. */
export function Blend({ from, to, over = 20, children }: { from: number; to: number; over?: number; children: ReactNode }) {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [from - over, from, to, to + over], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return opacity ? <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill> : null;
}
