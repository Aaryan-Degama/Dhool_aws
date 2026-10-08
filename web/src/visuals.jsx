// Dhool's pictures: the rooftop array that shows what is wrong, the chart that shows why, and the icons.
import { useEffect, useId, useRef, useState } from "react";

// ── The rooftop array, drawn in perspective ────────────────────────────────────────────────────────────
// Six columns by two rows of modules on a tilted frame: three strings of two columns each.
// Everything is in metres-ish world units and projected to the screen here, so the model can be turned.
const COLS = 6, ROWS = 2;
const MW = 1, ML = 1.75, GAP = 0.05;      // module width, length up the slope, gap between modules
const TH = 0.07, H0 = 0.6;                // frame thickness, height of the lower edge off the roof
const RIM = 0.035;                        // the aluminium rim around each module's glass
const CELL_COLS = 6, CELL_ROWS = 12;      // half-cut cells on one module
const TILT = (24 * Math.PI) / 180;        // slope of the array
const PITCH = (26 * Math.PI) / 180;       // how far down the camera looks
const DIST = 12;                          // camera distance: smaller is more dramatic perspective
const WIDE = COLS * MW + (COLS - 1) * GAP;
const LONG = ROWS * ML + (ROWS - 1) * GAP;
const ZF = (LONG * Math.cos(TILT)) / 2;   // the lower edge sits this far toward the viewer
const VIEW_W = 360;
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
  const k = DIST / (DIST - z2);
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
  const [rx0, rx1, ry0, ry1] = box([YAW_REST]);
  return { k, ox: VIEW_W / 2 - (k * (rx0 + rx1)) / 2, oy: 12 - k * ry0, height: Math.ceil(12 + k * (ry1 - ry0) + 26) };
})();
const VIEW_H = FIT.height;

const DUST = (() => {  // the same speckles every time: a tiny seeded generator, not Math.random
  let seed = 7;
  const next = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  return Array.from({ length: 300 }, () => [-WIDE / 2 + next() * WIDE, next() * LONG, 0.3 + next() * 0.65]);
})();

const LABEL = {
  fault: (n) => `Rooftop solar array with ${n} of ${COLS} columns dark`,
  trips: () => "Rooftop solar array switching off and on",
  dust: () => "Rooftop solar array covered in dust",
  haze: () => "Rooftop solar array under hazy air",
  ok: () => "Rooftop solar array, fully lit",
};

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
  }, []);

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

  const deadCols = cause === "fault" ? Math.max(1, Math.min(COLS - 1, Math.round(((evidence.drop_pct ?? loss) / 100) * COLS))) : 0;
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
  const [gx, gy] = at([0, 0, 0]);
  const [topX, topY] = at(surf(0, LONG)), [lowX, lowY] = at(surf(0, 0));
  const sweep = -WIDE / 2 + WIDE * (0.2 + (yaw - YAW_REST) / 70);  // the reflection slides as the model turns
  const band = (a, w) => poly([surf(a, 0), surf(a + w, 0), surf(a + w + 1.5, LONG), surf(a + 1.5, LONG)]);

  return (
    <svg className={`pm pm-${cause}${ghost ? " pm-ghost" : ""}`} viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} role="img"
         aria-label={(LABEL[cause] || (() => "Rooftop solar array, still being measured"))(deadCols)}
         onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}>
      <defs>
        <radialGradient id={`${id}fog`}><stop offset="0.3" stopColor="#cdd4dd" stopOpacity="0.52" /><stop offset="1" stopColor="#cdd4dd" stopOpacity="0" /></radialGradient>
        <radialGradient id={`${id}floor`}><stop offset="0" className="pm-glow" stopOpacity="0.3" /><stop offset="1" className="pm-glow" stopOpacity="0" /></radialGradient>
        <linearGradient id={`${id}glass`} gradientUnits="userSpaceOnUse" x1={topX} y1={topY} x2={lowX} y2={lowY}>
          <stop offset="0" stopColor="#27405f" /><stop offset="0.45" stopColor="#101d30" /><stop offset="1" stopColor="#080f1a" />
        </linearGradient>
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

      <ellipse cx={gx} cy={gy + 6} rx={VIEW_W * 0.52} ry="46" fill={`url(#${id}floor)`} />
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
const SKY_NAME = { sun: "Sunny", cloud: "Cloudy", rain: "Rain" };
const ICONS = {
  ...SKY,
  bolt: <path d="M13 2 4.5 13.5H11L10 22l8.5-11.5H12z" />,
  roof: <><path d="M6 6h12l3.5 12h-19z" /><path d="M10 6 8.5 18M14 6l1.5 12M4.2 12h15.6" /></>,
  week: <><path d="M4 6h16v14H4zM4 10.5h16M8 3.5v4M16 3.5v4" /></>,
  why: <path d="M3 20h18M6 20v-6M12 20V5M18 20v-9" />,
  setup: <><path d="M4 7h9M19 7h1M4 17h1M11 17h9" /><circle cx="16" cy="7" r="2.5" /><circle cx="8" cy="17" r="2.5" /></>,
  gauge: <path d="M4 17a8 8 0 1 1 16 0M12 17l4.5-6" />,
};
export const Icon = ({ name, label }) => (
  <svg className={`icon icon-${name}`} viewBox="0 0 24 24" role={label ? "img" : undefined} aria-label={label} aria-hidden={label ? undefined : true}>
    {ICONS[name]}
  </svg>
);

export const day = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" });
export const weekday = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short" });
/** sun, cloud or rain for one forecast day, judged against the best day of that week. */
export const skyOf = (d, week) => (d.rain_mm >= 1 ? "rain" : d.possible_kwh < 0.7 * Math.max(...week.map((w) => w.possible_kwh)) ? "cloud" : "sun");

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
           aria-label={`Daily output from ${day(first.date)} to ${day(last.date)}. On the last day the roof should have made ${last.expected} units and made ${last.actual ?? "no reading"}.`}>
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
        <span className="key key-expected">Should have made</span>
        <span className="key key-actual">Made</span>
        <span className="key key-rain">Rain that washes panels</span>
      </figcaption>
    </figure>
  );
}

/** The coming week: weather, what the roof could make, and what it will likely make as it is running now. */
export function Forecast({ verdict }) {
  const week = verdict.forecast || [];
  if (!week.length) return <p className="lede">No forecast yet. It appears with the next reading.</p>;
  const best = Math.max(...week.map((d) => d.possible_kwh));
  const [likely, possible] = weekTotals(verdict);
  return (
    <section className="forecast">
      <p className="lede">
        About {likely} units likely
        {possible - likely >= 2 ? `, out of ${possible} this roof could make in this weather if it were clean and healthy.` : "."}
      </p>
      <ol className="card">
        {week.map((d) => {
          const sky = skyOf(d, week);
          const units = d.likely_kwh ?? d.possible_kwh;
          return (
            <li key={d.date}>
              <span>{weekday(d.date)}</span>
              <svg className={`icon sky-${sky}`} viewBox="0 0 24 24" role="img" aria-label={SKY_NAME[sky]}>{SKY[sky]}</svg>
              <span className="temp">{d.temp_max}°</span>
              <span className="meter" aria-hidden="true">
                <i style={{ width: `${(100 * d.possible_kwh) / best}%` }}><b style={{ width: `${(100 * units) / d.possible_kwh}%` }} /></i>
              </span>
              <span className="units">{units}</span>
            </li>
          );
        })}
      </ol>
      <p className="key-row"><span className="key key-likely">Likely</span><span className="key key-possible">Possible if clean and healthy</span></p>
    </section>
  );
}

/** Sums the week for the home tile: [likely, possible] units, or null when there is no forecast. */
export function weekTotals(verdict) {
  const week = verdict.forecast || [];
  if (!week.length) return null;
  const sum = (key) => Math.round(week.reduce((total, d) => total + (d[key] ?? d.possible_kwh), 0));
  return [sum("likely_kwh"), sum("possible_kwh")];
}
