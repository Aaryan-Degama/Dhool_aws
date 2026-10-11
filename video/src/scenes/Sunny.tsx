import { AbsoluteFill } from "remotion";
import { Rise, SubLine, Typed } from "../components/Reveal";

/** 13–21 s. A clear day: the phone comes forward and the shot moves slowly in on the real figures. */
export const Sunny = () => (
  <AbsoluteFill>
    <Rise until={236} style={{ position: "absolute", left: 150, top: 400 }}>
      <Typed text="A clear day." from={30} size={124} />
      <Rise from={78} style={{ marginTop: 26 }}><SubLine size={36}>what the roof made,<br />against what it should have</SubLine></Rise>
    </Rise>
  </AbsoluteFill>
);
