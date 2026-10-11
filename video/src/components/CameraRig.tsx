import type { ReactNode } from "react";
import { AbsoluteFill } from "remotion";

/** Everything inside moves as one shot: a scale about a point and a slide, both read from the timeline. */
export const CameraRig = ({ scale = 1, x = 0, y = 0, about = "50% 50%", children }: { scale?: number; x?: number; y?: number; about?: string; children: ReactNode }) =>
  <AbsoluteFill style={{ transform: `translate(${x}px, ${y}px) scale(${scale})`, transformOrigin: about }}>{children}</AbsoluteFill>;
