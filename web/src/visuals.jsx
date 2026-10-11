// Dhool's pictures: the rooftop array that shows what is wrong, the chart that shows why, and the icons.
import { useEffect, useId, useRef, useState } from "react";
import { LOCALE, t } from "./i18n.js";
import { weeksOf } from "./store.js";

// ── The rooftop array, drawn in perspective ────────────────────────────────────────────────────────────
// Six columns by two rows of modules on a tilted frame: three strings of two columns each.
// Everything is in metres-ish world units and projected to the screen here, so the model can be turned.
const COLS = 6, ROWS = 2;
const MW = 1, ML = 1.75, GAP = 0.05;      // module width, length up the slope, gap between modules
const TH = 0.07, H0 = 0.6;                // frame thickness, height of the lower edge off the roof
const RIM = 0.035;                        // the aluminium rim around each module's glass
const CELL_COLS = 6, CELL_ROWS = 12;      // half-cut cells on one module
const TILT = (24 * Math.PI) / 180;        // slope of the array
const PITCH = (13 * Math.PI) / 180;       // how far down the camera looks: about eye height on the terrace
const WALL_Z = -4, WALL_H = 0.85;         // the parapet at the far edge of the terrace
const DIST = 12;                          // camera distance: smaller is more dramatic perspective
const WIDE = COLS * MW + (COLS - 1) * GAP;
const LONG = ROWS * ML + (ROWS - 1) * GAP;
const ZF = (LONG * Math.cos(TILT)) / 2;   // the lower edge sits this far toward the viewer
const VIEW_W = 360;
const WING = 1000;                        // the terrace and the city are drawn this far to the left of the picture, for a wide screen where the scene runs behind the headline
const SKYLINE_ROOM = 92;                  // sky kept above the horizon: the city's tallest building, then the sun or moon
const YAW_REST = -24, YAW_MIN = -44, YAW_MAX = -6;

/** A point on the glass: u across the array, v up the slope, lift along the surface normal. */
const surf = (u, v, lift = 0) => [
  u,
  H0 + v * Math.sin(TILT) + lift * Math.cos(TILT),
  ZF - v * Math.cos(TILT) + lift * Math.sin(TILT),
];

function raw([x, y, z], yaw) {
  const c = Math.cos(yaw), s = Math.sin(yaw);
  const x1 = x * c + z * s, z1 = -x * s + z * c;
  const y2 = y * Math.cos(PITCH) - z1 * Math.sin(PITCH), z2 = y * Math.sin(PITCH) + z1 * Math.cos(PITCH);
  const k = DIST / Math.max(0.6, DIST - z2);  // never divide by a point behind the camera
  return [x1 * k, -y2 * k];
}

// One scale for every angle, so turning the model never resizes it.
const FIT = (() => {
  const corners = [-WIDE / 2, WIDE / 2].flatMap((u) => [surf(u, 0), surf(u, LONG), [u, 0, ZF], [u, 0, -ZF]]);
  const box = (yaws) => {
    const pts = yaws.flatMap((deg) => corners.map((p) => raw(p, (deg * Math.PI) / 180)));
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    return [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  };
  const [x0, x1] = box([YAW_MIN, YAW_REST, YAW_MAX]);
  const k = (VIEW_W - 28) / (x1 - x0);
  // Framed on the resting angle; at other angles a corner may dip past the frame, which is left visible.
  const [rx0, rx1, , ry1] = box([YAW_REST]);
  // The horizon sits where level ground vanishes; leave room above it for the city.
  const oy = SKYLINE_ROOM + k * DIST * Math.tan(PITCH);
  return { k, ox: VIEW_W / 2 - (k * (rx0 + rx1)) / 2, oy, horizon: SKYLINE_ROOM, height: Math.ceil(oy + k * ry1 + 46) };
})();
const VIEW_H = FIT.height;

// The city beyond the parapet: two rows of flat silhouettes, some with a water tank on the roof.
const SKYLINE = (() => {
  let seed = 11;
  const next = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const row = (wMin, wMax, hMin, hMax) => {
    const out = [];
    for (let x = -WING; x < VIEW_W + 160;) {
      const w = wMin + next() * (wMax - wMin);
      out.push({ x, w, h: hMin + next() * (hMax - hMin), tank: next() < 0.35, crown: next() < 0.3, mast: next() < 0.14 });
      x += w + 2 + next() * 9;  // room between blocks for a side wall to show
    }
    return out;
  };
  const back = row(10, 26, 4, 15), far = row(12, 30, 9, 27), near = row(18, 42, 14, 44);
  for (const b of far) if (next() < 0.16) b.h *= 1.7;  // a few towers stand over the rest
  // A glass front: thin lines for the floors and the mullions between panes (one path), and a few panes lit
  // after dark (another).
  // The glass runs the whole height of a tower: down past the horizon to where the parapet hides its foot.
  let panes = "", lit = "", warm = "";
  const FOOT = SKYLINE_ROOM + 60;
  const floors = (b, gapX, gapY, share) => {
    const top = SKYLINE_ROOM - b.h, cols = Math.max(1, Math.round(b.w / gapX)), w = b.w / cols;
    for (let y = top + gapY; y < FOOT; y += gapY) panes += `M${b.x.toFixed(1)} ${y.toFixed(1)}h${b.w.toFixed(1)}`;
    for (let c = 1; c < cols; c++) panes += `M${(b.x + c * w).toFixed(1)} ${top.toFixed(1)}V${FOOT}`;
    for (let y = top; y < FOOT; y += gapY) for (let c = 0; c < cols; c++) {
      if (next() >= share) continue;
      const pane = `M${(b.x + c * w + 0.3).toFixed(1)} ${(y + 0.3).toFixed(1)}h${(w - 0.6).toFixed(1)}v${(gapY - 0.6).toFixed(1)}h-${(w - 0.6).toFixed(1)}z`;
      if (next() < 0.45) warm += pane; else lit += pane;  // some rooms under a yellow lamp, the rest office white
    }
  };
  far.forEach((b) => floors(b, 3.2, 2.6, 0.08));
  near.forEach((b) => floors(b, 4.6, 3.4, 0.12));
  return { back, far, near, panes, lit, warm };
})();

const DUST = (() => {  // the same speckles every time: a tiny seeded generator, not Math.random
  let seed = 7;
  const next = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  return Array.from({ length: 300 }, () => [-WIDE / 2 + next() * WIDE, next() * LONG, 0.3 + next() * 0.65]);
})();

const LABEL = {
  fault: (n) => t("Rooftop solar array with {n} of {cols} columns dark", { n, cols: COLS }),
  trips: () => t("Rooftop solar array switching off and on"),
  dust: () => t("Rooftop solar array covered in dust"),
  haze: () => t("Rooftop solar array under hazy air"),
  ok: () => t("Rooftop solar array, fully lit"),
};
LABEL.outage = LABEL.fault;

/** The app's name, drawn by hand with a round marker: the two o's are filled, as dots of dust. */
export const Wordmark = () => (
  <p className="brand" aria-label="Dhool">
    <svg viewBox="0 0 92 40" aria-hidden="true">
      <path d="M6 7V33Q25 30 24 19Q22 8 6 7M35 5V33M35 25Q41 16 47 33M86 5V33" />
      <circle cx="59" cy="27" r="6.5" /><circle cx="73" cy="27" r="6.5" />
    </svg>
  </p>
);

/** The roof as a model: a dead string goes dark, dust lies on the glass, haze veils it. Drag to turn it. */
export function PanelModel({ verdict }) {
  const { cause, loss_pct: loss = 0, evidence = {} } = verdict;
  const id = useId().replace(/:/g, "");
  const still = typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [yaw, setYaw] = useState(still ? YAW_REST : YAW_REST - 18);
  const frame = useRef(0);
  const drag = useRef(null);

  // The camera settles onto the roof once, when the model first appears.
  useEffect(() => {
    if (still) return;
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - start) / 1400);
      setYaw(YAW_REST - 18 * (1 - t) ** 3);
      if (t < 1) frame.current = requestAnimationFrame(tick);
    };
    frame.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame.current);
  }, [still]);

  const down = (e) => {
    cancelAnimationFrame(frame.current);
    drag.current = { x: e.clientX, yaw };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const move = (e) => {
    if (drag.current) setYaw(Math.max(YAW_MIN, Math.min(YAW_MAX, drag.current.yaw + (e.clientX - drag.current.x) * 0.3)));
  };
  const up = () => { drag.current = null; };

  const rad = (yaw * Math.PI) / 180;
  const at = (p) => { const [x, y] = raw(p, rad); return [FIT.ox + x * FIT.k, FIT.oy + y * FIT.k]; };
  const xy = (p) => at(p).map((n) => n.toFixed(1)).join(",");
  const poly = (list) => list.map(xy).join(" ");

  const deadCols = cause === "outage" ? COLS  // nothing is being made: the whole array is dark
    : cause === "fault" ?Math.max(1, Math.min(COLS - 1, Math.round(((evidence.drop_pct ?? loss) / 100) * COLS))) : 0;
  const ghost = cause === "no_data" || cause === "unclear";
  const dust = cause === "dust" ? Math.min(0.85, 0.3 + loss / 28) : 0;
  const modules = Array.from({ length: COLS * ROWS }, (_, i) => {
    const col = i % COLS, row = Math.floor(i / COLS);
    const u0 = -WIDE / 2 + col * (MW + GAP), v0 = row * (ML + GAP);
    return { i, col, row, u0, u1: u0 + MW, v0, v1: v0 + ML, dead: col >= COLS - deadCols };
  });
  const quad = (m, inset = 0) => poly([surf(m.u0 + inset, m.v0 + inset), surf(m.u1 - inset, m.v0 + inset),
                                       surf(m.u1 - inset, m.v1 - inset), surf(m.u0 + inset, m.v1 - inset)]);
  const line = (u0, v0, u1, v1) => `M${xy(surf(u0, v0))}L${xy(surf(u1, v1))}`;
  // The pale backsheet showing between cells, with the wider seam across the middle of a half-cut module.
  const gaps = (m) => {
    const a = m.u0 + RIM, b = m.u1 - RIM, lo = m.v0 + RIM, hi = m.v1 - RIM, mid = (lo + hi) / 2;
    let d = line(a, mid - 0.012, b, mid - 0.012) + line(a, mid + 0.012, b, mid + 0.012);
    for (let k = 1; k < CELL_COLS; k++) { const u = a + (k * (b - a)) / CELL_COLS; d += line(u, lo, u, hi); }
    for (let k = 1; k < CELL_ROWS; k++) if (k !== CELL_ROWS / 2) { const v = lo + (k * (hi - lo)) / CELL_ROWS; d += line(a, v, b, v); }
    return d;
  };
  // Busbars: the fine silver wires running up every cell.
  const bars = (m) => {
    const a = m.u0 + RIM, w = (m.u1 - m.u0 - 2 * RIM) / CELL_COLS;
    let d = "";
    for (let c = 0; c < CELL_COLS; c++) for (let k = 1; k <= 3; k++) { const u = a + (c + k / 4) * w; d += line(u, m.v0 + RIM, u, m.v1 - RIM); }
    return d;
  };
  const live = modules.filter((m) => !m.dead);
  const side = yaw < 0 ? WIDE / 2 : -WIDE / 2;  // the end of the array that faces the camera
  const legs = [-WIDE / 2 + 0.5, -WIDE / 6, WIDE / 6, WIDE / 2 - 0.5].map((x) => {
    const front = surf(x, 0.15, -TH), rear = surf(x, LONG - 0.15, -TH);
    return { x, front, rear, frontFoot: [x, 0, front[2]], rearFoot: [x, 0, rear[2]] };
  });
  // A level line on the terrace or its parapet, carried out past both edges of the picture.
  const across = (y, z) => {
    const [ax, ay] = at([-6, y, z]), [bx, by] = at([6, y, z]);
    const yAt = (x) => ay + ((by - ay) * (x - ax)) / (bx - ax);
    return [[-WING, yAt(-WING)], [VIEW_W + 160, yAt(VIEW_W + 160)]];
  };
  const flat = (points) => points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const wallBase = across(0, WALL_Z), wallTop = across(WALL_H, WALL_Z);
  const floor = flat([...wallBase, [VIEW_W + 160, VIEW_H], [-WING, VIEW_H]]);
  let tiles = "";
  for (let z = WALL_Z + 1; z < 4; z += 1) { const [a, b] = across(0, z); tiles += `M${flat([a])}L${flat([b])}`; }
  for (let x = -72; x <= 15; x += 1.5) tiles += `M${xy([x, 0, WALL_Z])}L${xy([x, 0, 3.4])}`;
  const drift = (yaw - YAW_REST) * 2.2;  // the far city slides a little as the model turns
  const [topX, topY] = at(surf(0, LONG)), [lowX, lowY] = at(surf(0, 0));
  const sweep = -WIDE / 2 + WIDE * (0.2 + (yaw - YAW_REST) / 70);  // the reflection slides as the model turns
  const [glintX, glintY] = at(surf(WIDE / 2, LONG));
  const band = (a, w) => poly([surf(a, 0), surf(a + w, 0), surf(a + w + 1.5, LONG), surf(a + 1.5, LONG)]);

  return (
    <svg className={`pm pm-${cause}${ghost ? " pm-ghost" : ""}`} viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} preserveAspectRatio="xMaxYMid meet" role="img"
         aria-label={(LABEL[cause] || (() => t("Rooftop solar array, still being measured")))(deadCols)}
         onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}>
      <defs>
        <radialGradient id={`${id}fog`}><stop offset="0.3" stopColor="#cdd4dd" stopOpacity="0.52" /><stop offset="1" stopColor="#cdd4dd" stopOpacity="0" /></radialGradient>
        <linearGradient id={`${id}ground`} gradientUnits="userSpaceOnUse" x1="0" y1={wallBase[0][1]} x2="0" y2={VIEW_H}>
          <stop offset="0" className="pm-ground-far" /><stop offset="0.72" className="pm-ground-near" /><stop offset="1" className="pm-ground-near" stopOpacity="0" />
        </linearGradient>
        {/* A tower's glass front mirrors the sky: paler toward the top. And one slanting streak of light across it. */}
        <linearGradient id={`${id}tower`} gradientUnits="userSpaceOnUse" x1="0" y1={FIT.horizon - 46} x2="0" y2={FIT.horizon + 60}>
          <stop offset="0" className="pm-tower-hi" /><stop offset="1" className="pm-tower-lo" />
        </linearGradient>
        <linearGradient id={`${id}shine`} x1="0" y1="0" x2="1" y2="0.7">
          <stop offset="0.15" stopColor="#fff" stopOpacity="0" /><stop offset="0.3" stopColor="#fff" stopOpacity="0.22" />
          <stop offset="0.42" stopColor="#fff" stopOpacity="0.05" /><stop offset="0.6" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <clipPath id={`${id}floor`}><polygon points={floor} /></clipPath>
        <linearGradient id={`${id}haze`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" className="pm-haze" stopOpacity="0" /><stop offset="0.3" className="pm-haze" stopOpacity="0.5" /><stop offset="0.6" className="pm-haze" stopOpacity="0.82" /><stop offset="1" className="pm-haze" stopOpacity="0.9" />
        </linearGradient>
        <linearGradient id={`${id}wall`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" className="pm-wall-hi" /><stop offset="1" className="pm-wall-lo" /></linearGradient>
        <linearGradient id={`${id}glass`} gradientUnits="userSpaceOnUse" x1={topX} y1={topY} x2={lowX} y2={lowY}>
          <stop offset="0" className="pm-reflect" /><stop offset="0.45" className="pm-cell" /><stop offset="1" className="pm-cell-low" />
        </linearGradient>
        {/* The sun, caught in the far corner of the glass: a warm flare that falls off across the array. */}
        <radialGradient id={`${id}glint`} gradientUnits="userSpaceOnUse" cx={glintX} cy={glintY} r={VIEW_W * 0.42}>
          <stop offset="0" stopColor="#fff6e0" stopOpacity="0.95" /><stop offset="0.12" stopColor="#ffd9a0" stopOpacity="0.55" />
          <stop offset="0.45" stopColor="#ffc27a" stopOpacity="0.12" /><stop offset="1" stopColor="#ffc27a" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`${id}sheen`} gradientUnits="userSpaceOnUse" x1={topX} y1={topY} x2={lowX} y2={lowY}>
          <stop offset="0" stopColor="#fff" stopOpacity="0.3" /><stop offset="1" stopColor="#fff" stopOpacity="0.03" />
        </linearGradient>
        <linearGradient id={`${id}edge`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#4a525e" /><stop offset="0.6" stopColor="#aab3c0" /><stop offset="1" stopColor="#6d7682" />
        </linearGradient>
        <filter id={`${id}blur`} x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="7" /></filter>
        <filter id={`${id}soft`} x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3.5" /></filter>
        <clipPath id={`${id}live`}>{live.map((m) => <polygon key={m.i} points={quad(m, RIM)} />)}</clipPath>
      </defs>

      <g className="pm-city" transform={`translate(${drift.toFixed(1)} 0)`}>
        {["back", "far", "near"].map((depth) => (
          <g key={depth} className={depth}>
            {SKYLINE[depth].map((b, i) => {
              const top = FIT.horizon - b.h;
              // Seen a little from the left and from above: each block shows its shaded right wall and its roof.
              const d = depth === "near" ? 6 : depth === "far" ? 3.5 : 0, r = b.x + b.w, up = top - d * 0.45;
              const n = (v) => v.toFixed(1);
              return (
                <g key={i}>
                  {d > 0 && <polygon className="side" points={`${n(r)},${n(top)} ${n(r + d)},${n(up)} ${n(r + d)},${n(top + b.h + 120)} ${n(r)},${n(top + b.h + 120)}`} />}
                  {d > 0 && <polygon className="roof" points={`${n(b.x)},${n(top)} ${n(b.x + d)},${n(up)} ${n(r + d)},${n(up)} ${n(r)},${n(top)}`} />}
                  <rect x={b.x.toFixed(1)} y={top.toFixed(1)} width={b.w.toFixed(1)} height={b.h + 120} fill={d > 0 ? `url(#${id}tower)` : undefined} />
                  {depth === "near" && <rect x={b.x.toFixed(1)} y={top.toFixed(1)} width={b.w.toFixed(1)} height={(b.h + 60).toFixed(1)} fill={`url(#${id}shine)`} />}
                  {b.crown && <rect x={(b.x + b.w * 0.2).toFixed(1)} y={(top - 4).toFixed(1)} width={(b.w * 0.6).toFixed(1)} height="4" />}
                  {depth === "near" && b.tank && !b.crown && <rect x={(b.x + b.w * 0.22).toFixed(1)} y={(top - 4.5).toFixed(1)} width="6.5" height="4.5" rx="1.6" />}
                  {depth !== "back" && b.mast && <rect x={(b.x + b.w * 0.7).toFixed(1)} y={(top - 13).toFixed(1)} width="0.9" height="13" />}
                </g>
              );
            })}
          </g>
        ))}
        <path className="pm-panes" d={SKYLINE.panes} />
        <path className="pm-tint" d={SKYLINE.lit + SKYLINE.warm} />
        <path className="pm-windows" d={SKYLINE.lit} />
        <path className="pm-windows warm" d={SKYLINE.warm} />
        {/* The air thickens toward the horizon, so the feet of the buildings fade into it. */}
        <rect x={-WING - 10} y={FIT.horizon - 46} width={VIEW_W + WING + 180} height="170" fill={`url(#${id}haze)`} />
      </g>
      <polygon points={flat([...wallTop, wallBase[1], wallBase[0]])} fill={`url(#${id}wall)`} />
      <path className="pm-wall-top" d={`M${flat([wallTop[0]])}L${flat([wallTop[1]])}`} />
      <polygon points={floor} fill={`url(#${id}ground)`} />
      <path className="pm-wall-foot" d={`M${flat([wallBase[0]])}L${flat([wallBase[1]])}`} />
      <path className="pm-tiles" d={tiles} clipPath={`url(#${id}floor)`} />
      <polygon className="pm-shadow" filter={`url(#${id}blur)`}
               points={poly([[-WIDE / 2, 0, ZF], [WIDE / 2, 0, ZF], [WIDE / 2, 0, -ZF], [-WIDE / 2, 0, -ZF]])} />

      <g className="pm-frame">
        {legs.map((l) => (
          <g key={l.x}>
            <path d={`M${xy(l.rearFoot)}L${xy(l.rear)}M${xy(l.frontFoot)}L${xy(l.rearFoot)}M${xy(l.frontFoot)}L${xy(l.front)}`} />
            <path className="pm-foot" d={`M${xy([l.x - 0.16, 0, l.frontFoot[2]])}L${xy([l.x + 0.16, 0, l.frontFoot[2]])}M${xy([l.x - 0.16, 0, l.rearFoot[2]])}L${xy([l.x + 0.16, 0, l.rearFoot[2]])}`} />
          </g>
        ))}
      </g>

      <g className="pm-body">
        <polygon fill={`url(#${id}edge)`} opacity="0.55" points={poly([surf(side, 0), surf(side, LONG), surf(side, LONG, -TH), surf(side, 0, -TH)])} />
        {modules.map((m) => (
          <g key={m.i} className={m.dead ? "pm-module dead" : "pm-module"}>
            <polygon className="pm-rim" points={quad(m)} fill={ghost ? undefined : `url(#${id}edge)`} />
            {!ghost && <polygon className="pm-glass" points={quad(m, RIM)} fill={m.dead ? undefined : `url(#${id}glass)`} />}
            {!ghost && <path className="pm-gaps" d={gaps(m)} />}
            {!ghost && !m.dead && <path className="pm-bars" d={bars(m)} />}
          </g>
        ))}
        {!ghost && (
          <g clipPath={`url(#${id}live)`} fill={`url(#${id}sheen)`}>
            <g filter={`url(#${id}soft)`}>
              <polygon points={band(sweep, 1.1)} />
              <polygon points={band(sweep + 1.7, 0.3)} />
            </g>
            <polygon className="pm-glint" fill={`url(#${id}glint)`} points={poly([surf(-WIDE / 2, 0), surf(WIDE / 2, 0), surf(WIDE / 2, LONG), surf(-WIDE / 2, LONG)])} />
            {dust > 0 && (
              <g className="pm-dust" style={{ opacity: dust }}>
                <polygon className="pm-film" points={poly([surf(-WIDE / 2, 0), surf(WIDE / 2, 0), surf(WIDE / 2, LONG), surf(-WIDE / 2, LONG)])} />
                {DUST.map(([u, v, r], i) => { const [x, y] = at(surf(u, v)); return <circle key={i} cx={x.toFixed(1)} cy={y.toFixed(1)} r={r} />; })}
              </g>
            )}
          </g>
        )}
        <polygon fill={`url(#${id}edge)`} points={poly([surf(-WIDE / 2, 0), surf(WIDE / 2, 0), surf(WIDE / 2, 0, -TH), surf(-WIDE / 2, 0, -TH)])} />
        {/* Current: a strip of light along the lower rail of every column that is producing. */}
        {!ghost && modules.filter((m) => m.row === 0 && !m.dead).map((m) => {
          const d = `M${xy(surf(m.u0 + 0.06, 0, -TH / 2))}L${xy(surf(m.u1 - 0.06, 0, -TH / 2))}`;
          return <g key={m.i} className="pm-current" style={{ "--col": m.col }}><path className="halo" d={d} /><path d={d} /></g>;
        })}
      </g>
      {cause === "haze" && <ellipse className="pm-fog" cx={VIEW_W / 2} cy={VIEW_H * 0.45} rx={VIEW_W * 0.5} ry={VIEW_H * 0.46} fill={`url(#${id}fog)`} />}
    </svg>
  );
}

// ── Icons: one stroke weight, drawn on a 24 grid ───────────────────────────────────────────────────────
const SKY = {
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M5 19l1.5-1.5M17.5 6.5 19 5" /></>,
  cloud: <path d="M7 18a4 4 0 0 1-.5-8A5.5 5.5 0 0 1 17 9.5 4.25 4.25 0 0 1 17 18z" />,
  rain: <><path d="M7 15a4 4 0 0 1-.5-8A5.5 5.5 0 0 1 17 6.5 4.25 4.25 0 0 1 17 15z" /><path className="drops" d="M8 18v3M12 18v3M16 18v3" /></>,
};
const ICONS = {
  ...SKY,
  bolt: <path d="M13 2 4.5 13.5H11L10 22l8.5-11.5H12z" />,
  roof: <><path d="M6 6h12l3.5 12h-19z" /><path d="M10 6 8.5 18M14 6l1.5 12M4.2 12h15.6" /></>,
  history: <><path d="M4 6h16v14H4zM4 10.5h16M8 3.5v4M16 3.5v4" /></>,
  why: <path d="M3 20h18M6 20v-6M12 20V5M18 20v-9" />,
  setup: <><path d="M4 7h9M19 7h1M4 17h1M11 17h9" /><circle cx="16" cy="7" r="2.5" /><circle cx="8" cy="17" r="2.5" /></>,
  gauge: <path d="M4 17a8 8 0 1 1 16 0M12 17l4.5-6" />,
  thumb: <path d="M7 10.5v9.5H4v-9.5zM7 10.5 11 3a2.2 2.2 0 0 1 2.3 2.6L12.6 9H18a2 2 0 0 1 2 2.4l-1.2 6.2A3 3 0 0 1 15.9 20H7" />,
};
export const Icon = ({ name, label }) => (
  <svg className={`icon icon-${name}`} viewBox="0 0 24 24" role={label ? "img" : undefined} aria-label={label} aria-hidden={label ? undefined : true}>
    {ICONS[name]}
  </svg>
);

export const day = (iso) => new Date(iso + "T00:00:00").toLocaleDateString(LOCALE, { day: "numeric", month: "short" });
export const when = (ms) => new Date(ms).toLocaleString(LOCALE, { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
/** "2026-10" as the month's name: short beside a bar, in full with its year in a sentence. */
export const monthName = (iso, full) =>
  new Date(iso + "-01T00:00:00").toLocaleDateString(LOCALE, full ? { month: "long", year: "numeric" } : { month: "short" });
export const weekday = (iso) => new Date(iso + "T00:00:00").toLocaleDateString(LOCALE, { weekday: "short" });
/** sun, cloud or rain for one forecast day, judged against the best day of that week. */
export const skyOf = (d, week) => (d.rain_mm >= 1 ? "rain" : d.possible_kwh < 0.7 * Math.max(...week.map((w) => w.possible_kwh)) ? "cloud" : "sun");

/**
 * Units made on each of the last 7, 30 or 90 days with a reading: one bar a day, on the wide-screen dashboard.
 * From the days the verdict carries (`daily_kwh`); nothing is shown for a verdict from before it carried them.
 * A day under a quarter of what this roof normally makes is drawn in the fault colour: a way to see the days
 * that went wrong, not a verdict of its own.
 */
export function Trend({ verdict }) {
  const [span, setSpan] = useState(7);
  const all = Object.entries(verdict.daily_kwh || {}).sort(([a], [b]) => (a < b ? -1 : 1));
  if (!all.length) return null;
  const days = all.slice(-span), most = Math.max(...days.map(([, kwh]) => kwh), 1);
  // The scale ends on a round number at or above the best day: 1, 2, 2.5 or 5 times a power of ten.
  const unit = 10 ** Math.floor(Math.log10(most)), top = [1, 2, 2.5, 5, 10].map((k) => k * unit).find((n) => n >= most);
  const every = Math.max(1, Math.ceil(days.length / 4));  // about four dates along the bottom
  return (
    <section className="card trend wide-only">
      <header>
        <h2><Icon name="why" />{t("Generation trend")}</h2>
        <div className="switch" role="group" aria-label={t("Generation trend")}>
          {[7, 30, 90].map((n) => (
            <button type="button" key={n} aria-pressed={span === n} aria-label={t("{n} days", { n })} onClick={() => setSpan(n)}>{t("{n}D", { n })}</button>
          ))}
        </div>
      </header>
      <div className="chart">
        <p className="chart-unit">kWh</p>
        <ol className="chart-ticks" aria-hidden="true"><li>{top}</li><li>{top / 2}</li><li>0</li></ol>
        <ol className="bars" style={{ "--top": top, "--n": days.length }}>
          {days.map(([date, kwh], i) => (
            <li key={date} className={kwh < 0.25 * verdict.expected_kwh ? "low" : undefined} style={{ "--kwh": kwh }} title={`${day(date)}: ${kwh}`}>
              <span>{day(date)}: {kwh} {t("units")}</span>
              {i % every === 0 && <time aria-hidden="true">{day(date)}</time>}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/** Actual against expected output, day by day, with rain marked along the bottom. */
export function WhyChart({ verdict }) {
  const series = verdict.series || [];
  if (series.length < 2) return null;
  const W = 340, H = 170, top = 8, bottom = 26;
  const max = Math.max(...series.map((d) => Math.max(d.expected, d.actual ?? 0))) * 1.05;
  const x = (i) => (i / (series.length - 1)) * W;
  const y = (v) => top + (1 - v / max) * (H - top - bottom);
  const expected = series.map((d, i) => `${x(i).toFixed(1)},${y(d.expected).toFixed(1)}`).join(" ");
  // Days with no reading break the line instead of being drawn as zero.
  const actual = series
    .map((d, i) => (d.actual == null ? null : `${x(i).toFixed(1)},${y(d.actual).toFixed(1)}`))
    .reduce((runs, p) => (p ? (runs[runs.length - 1].push(p), runs) : [...runs, []]), [[]])
    .filter((run) => run.length);
  const stepAt = series.findIndex((d) => d.date === verdict.evidence?.step_date);
  const first = series[0], last = series[series.length - 1];

  return (
    <figure className="why">
      <svg viewBox={`0 0 ${W} ${H}`} role="img"
           aria-label={t("Daily output from {from} to {to}. On the last day the roof should have made {expected} units and made {made}.",
                         { from: day(first.date), to: day(last.date), expected: last.expected, made: last.actual ?? t("no reading") })}>
        <polygon className="expected-area" points={`0,${H - bottom} ${expected} ${W},${H - bottom}`} />
        <polyline className="expected-line" points={expected} />
        {actual.map((run, i) =>
          run.length > 1 ? <polyline key={i} className="actual-line" points={run.join(" ")} />
                         : <circle key={i} className="actual-dot" cx={run[0].split(",")[0]} cy={run[0].split(",")[1]} r="2.5" />)}
        {series.map((d, i) => d.rain_mm >= 5 && (
          <rect key={d.date} className="rain" x={x(i) - 1.5} y={H - bottom + 3} width="3" height="7" rx="1.5" />))}
        {stepAt > 0 && (
          <g className="step">
            <line x1={x(stepAt)} x2={x(stepAt)} y1={top} y2={H - bottom} />
            <text x={Math.min(x(stepAt) + 5, W - 44)} y={top + 10}>{day(series[stepAt].date)}</text>
          </g>
        )}
        <text className="axis" x="0" y={H - 2}>{day(first.date)}</text>
        <text className="axis" x={W} y={H - 2} textAnchor="end">{day(last.date)}</text>
      </svg>
      <figcaption>
        <span className="key key-expected">{t("Should have made")}</span>
        <span className="key key-actual">{t("Made")}</span>
        <span className="key key-rain">{t("Rain that washes panels")}</span>
      </figcaption>
    </figure>
  );
}

/** One month's weeks, each opening to its days. A day with no reading says so: it is not a day that made 0. */
function Weeks({ month, daily, asOf }) {
  return (
    <ol className="weeks">
      {weeksOf(month, daily, asOf).map((w) => (
        <li key={w.from}>
          <details>
            <summary>
              <span className="line">
                <span>{w.from === w.to ? w.from : `${w.from}–${w.to}`} {monthName(month)}</span>
                <span className="units">{w.read > 0 && w.kwh}</span>
                {w.read < w.days.length && (
                  <small>{w.read ? t("Readings on {n} of {total} days", { n: w.read, total: w.days.length }) : t("No readings")}</small>)}
              </span>
            </summary>
            <ol className="days">
              {w.days.map((d) => (
                <li key={d.date} className="line">
                  <span>{weekday(d.date)} {day(d.date)}</span>
                  {d.kwh == null ? <small>{t("no reading")}</small> : <span className="units">{d.kwh}</span>}
                </li>
              ))}
            </ol>
          </details>
        </li>
      ))}
    </ol>
  );
}

/**
 * What the roof made in each of the last months (six at most), with the total. A month opens to its weeks and
 * a week to its days when the verdict carries the days (`daily_kwh`); one worked out before it did shows the
 * months alone. A verdict from before the analysis counted months has none: say when they will appear.
 */
export function Months({ verdict }) {
  const { months, daily_kwh: daily } = verdict;
  if (!months?.length) return <p className="lede">{t("The monthly totals appear with the next reading, or after tonight's check.")}</p>;
  const best = Math.max(...months.map((m) => m.kwh)) || 1;
  const note = (m) => {
    const [year, month] = m.month.split("-");
    const total = new Date(year, month, 0).getDate();  // day 0 of the next month: the last day of this one
    if (!m.days) return t("No readings");
    if (m.month === verdict.as_of.slice(0, 7)) return t("{n} days so far", { n: m.days });
    return m.days < total ? t("Readings on {n} of {total} days", { n: m.days, total }) : "";
  };
  return (
    <>
      <p className="lede">
        {t("{units} units made since {month}.", { units: Math.round(months.reduce((sum, m) => sum + m.kwh, 0)), month: monthName(months[0].month, true) })}
      </p>
      <div className="card stack">
        <ol className="months">
          {months.map((m) => {
            const line = (
              <span className="line">
                <span>{monthName(m.month)}</span>
                <span className="meter" aria-hidden="true"><b style={{ width: `${(100 * m.kwh) / best}%` }} /></span>
                <span className="units">{m.kwh}</span>
                {note(m) && <small>{note(m)}</small>}
              </span>
            );
            return (
              <li key={m.month}>
                {daily && m.days ? <details><summary>{line}</summary><Weeks month={m.month} daily={daily} asOf={verdict.as_of} /></details> : line}
              </li>
            );
          })}
        </ol>
        <p className="note">
          {t("Units made each month, from the readings Dhool has.")}
          {daily && t(" Tap a month for its weeks, and a week for its days.")}
        </p>
      </div>
    </>
  );
}
