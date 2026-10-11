import { AbsoluteFill } from "remotion";
import { Headline, Rise, SubLine } from "../components/Reveal";

/** 6–13 s. The same home on the web and on the phone. Frames are counted from the scene's start. */
export const Meet = () => (
  <AbsoluteFill>
    <div style={{ position: "absolute", left: 110, top: 44 }}>
      <Rise from={70} until={196}><Headline size={64}>On the web. On your phone.</Headline></Rise>
    </div>
    <div style={{ position: "absolute", left: 114, top: 986 }}>
      <Rise from={92} until={196}><SubLine>the same roof, the same advice</SubLine></Rise>
    </div>
  </AbsoluteFill>
);
