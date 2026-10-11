// The film: backgrounds, then the desktop window, then the one phone that travels through every scene, then
// each scene's own type. Where things are, and what they show, comes from timeline.ts.
import { AbsoluteFill, Audio, Img, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { ClosingBrand } from "./components/ClosingBrand";
import { DesktopBrowser } from "./components/DesktopBrowser";
import { PhoneMockup } from "./components/PhoneMockup";
import { Blend } from "./components/Transition";
import { WeatherBackground, type Weather } from "./components/WeatherBackground";
import { Desktop } from "./scenes/Desktop";
import { Hook } from "./scenes/Hook";
import { Meet } from "./scenes/Meet";
import { Clouds, DustStorm, Night, SnowFall } from "./scenes/Skies";
import { Sunny } from "./scenes/Sunny";
import { AUDIO, CAPTURE_SET, HIDE_ACCOUNT, PAGES, SCENES, SCREENS, deskAt, phoneAt, scrollAt } from "./timeline";

const FILL = { position: "absolute", inset: 0, width: "100%", height: "100%" } as const;
const capture = (file: string) => staticFile(`${CAPTURE_SET}/${file}`);

/** Blurs one patch of a capture: the account's home name and picture, top right of every page. Given in percent of
    the capture, so it holds at any size. Done here, in the film; the captures themselves are left as taken. */
const Hide = ({ left, top, width, height }: { left: number; top: number; width: number; height: number }) =>
  <div style={{ position: "absolute", left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%`, borderRadius: 999, backdropFilter: "blur(14px)", background: "rgba(255, 255, 255, 0.06)" }} />;

/** The newest of `items` that has started, fading in over the one before it. */
function Latest<T extends { at: number; fade: number }>({ items, src }: { items: T[]; src: (item: T) => string }) {
  const frame = useCurrentFrame();
  const now = Math.max(0, items.findLastIndex((item) => frame >= item.at));
  const opacity = interpolate(frame, [items[now].at, items[now].at + items[now].fade], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <>
      {now > 0 && opacity < 1 && <Img src={src(items[now - 1])} style={FILL} />}
      <Img src={src(items[now])} style={{ ...FILL, opacity }} />
    </>
  );
}

/** The phone's screen: the real Roof page under the sky of the moment, or the page scrolling. */
function Screen() {
  const scroll = scrollAt(useCurrentFrame());
  return (
    <>
      <Latest items={SCREENS} src={(s) => capture(`phone-roof-${s.sky}.png`)} />
      {scroll != null && <Img src={capture(`scroll/${String(scroll).padStart(3, "0")}.jpg`)} style={FILL} />}
      {HIDE_ACCOUNT && <Hide left={68} top={0.7} width={31} height={4.4} />}
    </>
  );
}

// The light in the room: when each kind is fully on. Neighbours overlap as they fade.
const ROOMS: [Weather, number, number][] = [["sunny", 410, 650], ["cloudy", 720, 780], ["rain", 800, 925], ["dust", 950, 1135], ["snow", 1160, 1315], ["night", 1345, 1520]];

export function Film() {
  const frame = useCurrentFrame();
  const phone = phoneAt(frame), desk = deskAt(frame);
  const scenes = SCENES;
  const type = (scene: keyof typeof SCENES, what: React.ReactNode) => <Sequence from={scenes[scene].from} durationInFrames={scenes[scene].length}>{what}</Sequence>;
  return (
    <AbsoluteFill>
      <WeatherBackground kind="plain" />
      {ROOMS.map(([kind, from, to]) => <Blend key={kind} from={from} to={to} over={30}><WeatherBackground kind={kind} /></Blend>)}
      {desk.show > 0 && (
        <div style={{ opacity: desk.show }}>
          <DesktopBrowser x={desk.x} y={desk.y} w={desk.w} address="Dhool">
            <Latest items={PAGES} src={(p) => capture(`desktop-${p.page}-day.png`)} />
            {HIDE_ACCOUNT && <Hide left={89.5} top={1.4} width={9.8} height={5.6} />}
          </DesktopBrowser>
        </div>
      )}
      <PhoneMockup x={phone.x} y={phone.y} h={phone.h} turn={phone.turn} opacity={phone.show}><Screen /></PhoneMockup>
      <Sequence from={scenes.hook.from} durationInFrames={scenes.hook.length + 20}><Blend from={0} to={scenes.hook.length - 6} over={14}><Hook /></Blend></Sequence>
      {type("meet", <Meet />)}
      {type("sunny", <Sunny />)}
      {type("clouds", <Clouds />)}
      {type("dust", <DustStorm />)}
      {type("snow", <SnowFall />)}
      {type("night", <Night />)}
      {type("desktop", <Desktop />)}
      <Blend from={scenes.close.from + 14} to={scenes.close.from + scenes.close.length} over={18}><Sequence from={scenes.close.from + 6}><ClosingBrand /></Sequence></Blend>
      <Audio src={staticFile("audio/sound-design.wav")} />
      {AUDIO.voiceover && <Audio src={staticFile("audio/voiceover.wav")} />}
      {AUDIO.music && <Audio src={staticFile("audio/music.wav")} volume={0.5} />}
    </AbsoluteFill>
  );
}
