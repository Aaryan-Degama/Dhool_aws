import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { Typed } from "../components/Reveal";
import { SunSweep } from "../components/WeatherBackground";

/** 0–6 s. The question, typed on a bright page as a band of sunlight passes; then it lifts to make room for the phone. */
export function Hook() {
  const frame = useCurrentFrame();
  const lift = interpolate(frame, [96, 150], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  return (
    <AbsoluteFill>
      <SunSweep from={10} to={120} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", transform: `translateY(${-400 * lift}px) scale(${1 - 0.42 * lift})` }}>
        <Typed text="Is your solar actually working?" from={12} size={112} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
