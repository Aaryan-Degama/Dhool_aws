// The two pictures in Dhool: the panel that shows what is wrong, and the chart that shows why.

const COLS = 6; // three strings of two columns each
const ROWS = 4;

/** A solar panel drawn so the cause is visible: dust lies on it, a dead string goes dark, haze veils it. */
export function Panel({ verdict }) {
  const { cause, loss_pct: loss = 0, evidence = {} } = verdict;
  const deadCols = cause === "fault" ? Math.max(1, Math.round(((evidence.drop_pct ?? loss) / 100) * COLS)) : 0;
  const dust = cause === "dust" ? Math.min(0.8, 0.25 + loss / 30) : 0;
  const empty = cause === "no_data" || cause === "unclear";
  const label = {
    fault: `Solar panel with ${deadCols} of ${COLS} columns dark`,
    trips: "Solar panel switching off and on",
    dust: "Solar panel covered in dust",
    haze: "Solar panel under hazy air",
    ok: "Solar panel fully lit",
  }[cause] || "Solar panel, still being measured";

  return (
    <svg className={`panel panel-${cause}`} viewBox="0 0 312 172" role="img" aria-label={label}>
      <defs>
        <pattern id="dust" width="14" height="14" patternUnits="userSpaceOnUse">
          <circle cx="3" cy="4" r="1.6" /><circle cx="10" cy="9" r="1.1" /><circle cx="7" cy="1" r="0.8" />
          <circle cx="1" cy="11" r="1" /><circle cx="12" cy="2" r="0.7" />
        </pattern>
      </defs>
      <rect className="panel-frame" width="312" height="172" rx="10" />
      {Array.from({ length: COLS * ROWS }, (_, i) => {
        const col = i % COLS, row = Math.floor(i / COLS);
        const dead = col >= COLS - deadCols;
        return (
          <g key={i} transform={`translate(${8 + col * 50} ${8 + row * 40})`}
             className={dead ? "cell dead" : empty ? "cell empty" : "cell"} style={{ "--col": col }}>
            <rect width="46" height="36" rx="3" />
            {!dead && !empty && <path className="busbar" d="M15 0v36M31 0v36" />}
          </g>
        );
      })}
      {dust > 0 && (
        <g className="dust" style={{ opacity: dust }}>
          <rect x="8" y="8" width="296" height="156" rx="3" className="dust-film" />
          <rect x="8" y="8" width="296" height="156" rx="3" fill="url(#dust)" />
        </g>
      )}
      {cause === "haze" && <rect className="haze" x="0" y="0" width="312" height="172" rx="10" />}
    </svg>
  );
}

export const day = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" });

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

const SKY = {
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M5 19l1.5-1.5M17.5 6.5 19 5" /></>,
  cloud: <path d="M7 18a4 4 0 0 1-.5-8A5.5 5.5 0 0 1 17 9.5 4.25 4.25 0 0 1 17 18z" />,
  rain: <><path d="M7 15a4 4 0 0 1-.5-8A5.5 5.5 0 0 1 17 6.5 4.25 4.25 0 0 1 17 15z" /><path className="drops" d="M8 18v3M12 18v3M16 18v3" /></>,
};
const SKY_NAME = { sun: "Sunny", cloud: "Cloudy", rain: "Rain" };

/** The coming week: weather, what the roof could make, and what it will likely make as it is running now. */
export function Forecast({ verdict }) {
  const week = verdict.forecast || [];
  if (!week.length) return null;
  const best = Math.max(...week.map((d) => d.possible_kwh));
  const sum = (key) => Math.round(week.reduce((total, d) => total + (d[key] ?? d.possible_kwh), 0));
  const likely = sum("likely_kwh"), possible = sum("possible_kwh");
  return (
    <section className="forecast">
      <h2>The next {week.length} days</h2>
      <p className="note">
        About {likely} units likely
        {possible - likely >= 2 ? `, out of ${possible} this roof could make in this weather if it were clean and healthy.` : "."}
      </p>
      <ol>
        {week.map((d) => {
          const sky = d.rain_mm >= 1 ? "rain" : d.possible_kwh < 0.7 * best ? "cloud" : "sun";
          const units = d.likely_kwh ?? d.possible_kwh;
          return (
            <li key={d.date}>
              <span>{new Date(d.date + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short" })}</span>
              <svg className={`sky sky-${sky}`} viewBox="0 0 24 24" role="img" aria-label={SKY_NAME[sky]}>{SKY[sky]}</svg>
              <span className="temp">{d.temp_max}°</span>
              <span className="meter" aria-hidden="true">
                <i style={{ width: `${(100 * d.possible_kwh) / best}%` }}><b style={{ width: `${(100 * units) / d.possible_kwh}%` }} /></i>
              </span>
              <span className="units">{units}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
