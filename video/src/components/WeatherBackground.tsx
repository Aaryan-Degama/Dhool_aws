// The room the phone sits in. Quiet on purpose: the weather itself is on the phone's real screen; this carries
// its light and what falls through the air. It is drawn behind the phone, so nothing ever crosses the interface.
import { AbsoluteFill, interpolate, random, useCurrentFrame } from "remotion";
import { H, PAPER, W } from "../theme";

export type Weather = "plain" | "sunny" | "cloudy" | "rain" | "dust" | "snow" | "night";
const BASE: Record<Weather, string> = {
  plain: PAPER, sunny: "#faf5ea", cloudy: "#e4e6e9", rain: "#c9d1d6", dust: "#d6b684", snow: "#edf1f5", night: "#11132a",
};
const many = (n: number) => Array.from({ length: n }, (_, i) => i);
const wrap = (v: number, span: number) => ((v % span) + span) % span;

function Rain({ frame }: { frame: number }) {
  return <>{many(170).map((i) => {
    const depth = 0.5 + random(`r${i}`) * 0.5, x = random(`rx${i}`) * (W + 300), y = wrap(random(`ry${i}`) * H + frame * 34 * depth, H + 120) - 60;
    return <i key={i} style={{ position: "absolute", left: x - (y / H) * 110, top: y, width: 1.6 * depth, height: 46 * depth, background: "rgba(60, 78, 92, 0.34)", transform: "rotate(9deg)", opacity: depth }} />;
  })}</>;
}
function Dust({ frame }: { frame: number }) {
  return (
    <>
      {/* The sun, dimmed to a pale disc by what is in the air. */}
      <div style={{ position: "absolute", left: 250, top: 120, width: 190, height: 190, borderRadius: "50%", background: "rgba(255, 240, 205, 0.55)", filter: "blur(10px)" }} />
      {many(3).map((layer) => many(46).map((i) => {
        const key = `${layer}-${i}`, size = (2 + random(`ds${key}`) * 5) * (1 + layer * 1.6), speed = (2.2 + layer * 2.6) * (0.7 + random(`dv${key}`) * 0.6);
        const x = W + 80 - wrap(random(`dx${key}`) * (W + 160) + frame * speed, W + 160), y = random(`dy${key}`) * H + Math.sin((frame + i * 9) / 34) * 14;
        return <i key={key} style={{ position: "absolute", left: x, top: y, width: size * 2.4, height: size, borderRadius: "50%", background: "rgba(122, 86, 38, 0.3)", filter: `blur(${1 + layer * 2.5}px)` }} />;
      }))}
      <AbsoluteFill style={{ background: "linear-gradient(90deg, rgba(150, 104, 44, 0.22), rgba(150, 104, 44, 0) 45%, rgba(150, 104, 44, 0.14))" }} />
    </>
  );
}
function Snow({ frame }: { frame: number }) {
  return <>{many(3).map((layer) => many(60).map((i) => {
    const key = `${layer}-${i}`, size = 3 + layer * 3.5 + random(`ss${key}`) * 2, speed = 1.1 + layer * 1.3;
    const y = wrap(random(`sy${key}`) * H + frame * speed, H + 40) - 20, x = random(`sx${key}`) * W + Math.sin((frame + i * 13) / (40 + layer * 12)) * (10 + layer * 8);
    return <i key={key} style={{ position: "absolute", left: x, top: y, width: size, height: size, borderRadius: "50%", background: "#fff", boxShadow: "0 0 0 1px rgba(150, 166, 184, 0.25)", filter: `blur(${layer === 2 ? 2 : 0}px)`, opacity: 0.55 + layer * 0.2 }} />;
  }))}</>;
}
const Stars = () => <>{many(70).map((i) => {
  const size = 1.5 + random(`ts${i}`) * 2;
  return <i key={i} style={{ position: "absolute", left: random(`tx${i}`) * W, top: random(`ty${i}`) * H * 0.8, width: size, height: size, borderRadius: "50%", background: "#fff", opacity: 0.25 + random(`to${i}`) * 0.5 }} />;
})}</>;

export function WeatherBackground({ kind }: { kind: Weather }) {
  const frame = useCurrentFrame();
  const drift = interpolate(frame % 600, [0, 600], [0, 1]);
  return (
    <AbsoluteFill style={{ background: BASE[kind], overflow: "hidden" }}>
      {kind === "sunny" && (
        // One soft pool of warm light, moving a little: the sun is off-frame, up and to the left.
        <div style={{ position: "absolute", left: -260 + drift * 90, top: -420, width: 1500, height: 1500, borderRadius: "50%",
                      background: "radial-gradient(closest-side, rgba(255, 205, 110, 0.3), rgba(255, 205, 110, 0))" }} />
      )}
      {kind === "cloudy" && <div style={{ position: "absolute", left: -300 + drift * 260, top: -260, width: 2100, height: 700, borderRadius: "50%", background: "rgba(120, 128, 138, 0.16)", filter: "blur(90px)" }} />}
      {kind === "rain" && <Rain frame={frame} />}
      {kind === "dust" && <Dust frame={frame} />}
      {kind === "snow" && <Snow frame={frame} />}
      {kind === "night" && <Stars />}
    </AbsoluteFill>
  );
}

/** A band of sunlight crossing the frame once, between `from` and `to`. */
export function SunSweep({ from, to }: { from: number; to: number }) {
  const frame = useCurrentFrame();
  const at = interpolate(frame, [from, to], [-0.5, 1.4], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <div style={{ position: "absolute", top: -200, bottom: -200, left: `${at * 100}%`, width: 620, transform: "skewX(-18deg)",
                       background: "linear-gradient(90deg, rgba(255, 214, 140, 0), rgba(255, 214, 140, 0.34), rgba(255, 214, 140, 0))" }} />;
}
