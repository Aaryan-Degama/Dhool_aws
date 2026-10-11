import { Composition } from "remotion";
import { Film } from "./Film";
import { FPS, H, W } from "./theme";
import { DRAFT, TOTAL } from "./timeline";

export const Root = () => (
  <>
    <Composition id="Demo" component={Film} durationInFrames={TOTAL} fps={FPS} width={W} height={H} />
    <Composition id="Draft" component={Film} durationInFrames={DRAFT} fps={FPS} width={W} height={H} />
  </>
);
