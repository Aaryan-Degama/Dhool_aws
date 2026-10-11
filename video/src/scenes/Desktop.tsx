import { AbsoluteFill } from "remotion";
import { Rise, SubLine } from "../components/Reveal";

/** 51–59 s. The site on a wide screen: Roof, then History, then Why. One small line under the window. */
export const Desktop = () => (
  <AbsoluteFill>
    <Rise from={76} until={228} style={{ position: "absolute", left: 96, top: 1006 }}><SubLine size={30}>the same home, with room to spread out</SubLine></Rise>
  </AbsoluteFill>
);
