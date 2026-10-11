// Scenes 4 to 7: one word for the sky, one small line under it, set beside the phone. Each is counted from its
// own start (the Sequence in Film.tsx), and leaves before the next arrives.
import { AbsoluteFill } from "remotion";
import { Rise, SubLine, Typed } from "../components/Reveal";
import { CHARCOAL } from "../theme";

function Sky({ word, line, from, until, left = 150, color = CHARCOAL, soft }: { word: string; line: string; from: number; until: number; left?: number; color?: string; soft?: string }) {
  return (
    <AbsoluteFill>
      <Rise from={from} until={until} style={{ position: "absolute", left, top: 400 }}>
        <Typed text={word} from={from} size={124} color={color} />
        <Rise from={from + word.length * 2 + 24} style={{ marginTop: 26 }}><SubLine size={36} color={soft}>{line}</SubLine></Rise>
      </Rise>
    </AbsoluteFill>
  );
}

/** 21–31 s: cloud, then rain. */
export const Clouds = () => (
  <>
    <Sky word="Under cloud." line="dust has built up: wash the panels" from={80} until={158} />
    <Sky word="In rain." line="rain is coming: let it wash them" from={176} until={296} />
  </>
);
/** 31–38 s. Dhool is the Hindi word for dust. */
export const DustStorm = () => <Sky word="In dust." line="wait out the storm, then wash" from={36} until={204} />;
/** 38–44 s. The phone has crossed to the left, so the words sit on the right. */
export const SnowFall = () => <Sky word="In snow." line="a fault, not dust: call the vendor" from={66} until={174} left={1010} />;
/** 44–51 s. Light type on the dark. */
export const Night = () => <Sky word="After dark." line="washed, checked, back to normal" from={70} until={204} left={120} color="#f3f5f8" soft="#aab2c5" />;
