import { useEffect, useRef, useState } from "react";
import { api, confirmSignUp, signedIn, signIn, signOut, signUp } from "./api.js";
import { API_URL, TARIFF_NOTE } from "./config.js";
import { FIXTURES } from "./fixtures.js";
import { setSky, skyOver } from "./sky.js";
import { day, Forecast, Icon, PanelModel, skyOf, weekday, weekTotals, WhyChart } from "./visuals.jsx";

// What the homeowner should do, in their words. The API's verdict and cause pick the line.
const HEADLINE = {
  "INSPECT:fault": "Call your vendor",
  "INSPECT:trips": "Call your vendor",
  "CLEAN:dust": "Wash the panels",
  "WAIT:dust": "Wait for the rain",
  "WAIT:haze": "Don't wash. It's haze.",
  "WAIT:unclear": "Wait and watch",
  "WAIT:no_data": "Still learning your roof",
  "OK:ok": "Your solar is working",
};
const SURE = { high: "Dhool is sure about this.", medium: "Dhool is fairly sure about this.", low: "Dhool is not sure yet." };
const SURE_SHORT = { high: "Dhool is sure", medium: "Fairly sure", low: "Not sure yet" };

function useAction() {
  const [state, setState] = useState({ busy: false, error: "" });
  const run = async (fn) => {
    setState({ busy: true, error: "" });
    try {
      await fn();
      setState({ busy: false, error: "" });
    } catch (e) {
      setState({ busy: false, error: e.message });
    }
  };
  return [state, run];
}

const ErrorLine = ({ error }) => (error ? <p className="error" role="alert">{error}</p> : null);

function Field({ label, hint, ...input }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input {...input} />
      {hint && <small>{hint}</small>}
    </label>
  );
}

function Auth({ onDone }) {
  const [mode, setMode] = useState("in"); // in | up | code
  const [form, setForm] = useState({ email: "", password: "", code: "" });
  const [state, run] = useAction();
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = (e) => {
    e.preventDefault();
    run(async () => {
      if (mode === "up") {
        await signUp(form.email, form.password);
        return setMode("code");
      }
      if (mode === "code") await confirmSignUp(form.email, form.code);
      await signIn(form.email, form.password);
      onDone();
    });
  };

  return (
    <main className="page auth">
      <p className="brand">Dhool</p>
      <div className="hero"><PanelModel verdict={{ cause: "ok" }} /></div>
      <h1>Is your solar actually working?</h1>
      <p className="lede">
        Your inverter app shows a number. Dhool tells you what your roof should have made, and what to do
        when it falls short.
      </p>
      <form onSubmit={submit} className="card">
        {mode === "code" ? (
          <Field label="Code from your email" inputMode="numeric" autoComplete="one-time-code" required
                 value={form.code} onChange={set("code")} hint={`Sent to ${form.email}`} />
        ) : (
          <>
            <Field label="Email" type="email" autoComplete="email" required value={form.email} onChange={set("email")} />
            <Field label="Password" type="password" required minLength={8} value={form.password} onChange={set("password")}
                   autoComplete={mode === "up" ? "new-password" : "current-password"}
                   hint={mode === "up" ? "At least 8 characters, with a capital letter, a number and a symbol" : undefined} />
          </>
        )}
        <ErrorLine error={state.error} />
        <button className="primary" disabled={state.busy}>
          {state.busy ? "One moment…" : mode === "in" ? "Sign in" : mode === "up" ? "Create account" : "Confirm and sign in"}
        </button>
        {mode !== "code" && (
          <button type="button" className="link" onClick={() => setMode(mode === "in" ? "up" : "in")}>
            {mode === "in" ? "New here? Create an account" : "Already have an account? Sign in"}
          </button>
        )}
      </form>
    </main>
  );
}

function Setup({ onDone }) {
  const [form, setForm] = useState({ name: "", kw: "3", lat: "", lon: "", code: "" });
  const [state, run] = useAction();
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const [locationHelp, setLocationHelp] = useState(false);
  const locate = () =>
    navigator.geolocation.getCurrentPosition(
      (p) => setForm((f) => ({ ...f, lat: p.coords.latitude.toFixed(4), lon: p.coords.longitude.toFixed(4) })),
      () => setLocationHelp(true),
    );

  const create = (e) => {
    e.preventDefault();
    run(async () => {
      await api("/houses", { name: form.name, kw: Number(form.kw), lat: Number(form.lat), lon: Number(form.lon) });
      onDone();
    });
  };
  const join = (e) => {
    e.preventDefault();
    run(async () => {
      await api("/join", { code: form.code });
      onDone();
    });
  };

  return (
    <main className="page">
      <p className="brand">Dhool</p>
      <h1>Add your home</h1>
      <p className="lede">Dhool needs to know where your roof is and how big the system is. That is all.</p>
      <form onSubmit={create} className="card">
        <Field label="Name for this home" required maxLength={60} placeholder="Sharma house" value={form.name} onChange={set("name")} />
        <label className="field">
          <span>System size</span>
          <select value={form.kw} onChange={set("kw")}>
            {[1, 2, 3, 4, 5, 6, 8, 10].map((kw) => <option key={kw} value={kw}>{kw} kW</option>)}
          </select>
          <small>It is on your installation papers and in your inverter app.</small>
        </label>
        <div className="row">
          <Field label="Latitude" inputMode="decimal" required value={form.lat} onChange={set("lat")} />
          <Field label="Longitude" inputMode="decimal" required value={form.lon} onChange={set("lon")} />
        </div>
        <button type="button" className="secondary" onClick={locate}>Use my location</button>
        {locationHelp && <p className="note">Location is off for this site. Type the two numbers in, or allow location and try again.</p>}
        <ErrorLine error={state.error} />
        <button className="primary" disabled={state.busy}>{state.busy ? "Saving…" : "Add home"}</button>
      </form>

      <form onSubmit={join} className="card">
        <h2>Someone at home already uses Dhool?</h2>
        <Field label="Family code" required maxLength={6} autoCapitalize="characters" className="code-input"
               value={form.code} onChange={set("code")} hint="Ask them for the six-letter code from their Dhool app." />
        <button className="secondary" disabled={state.busy}>Join their home</button>
      </form>
    </main>
  );
}

function vendorMessage(house, v) {
  return [
    "Namaste,",
    `Our rooftop solar system (${house.name}) is producing much less than it should.`,
    v.reason,
    `On ${day(v.as_of)} it should have made about ${v.expected_kwh} units and made ${v.actual_kwh}.`,
    "Please send someone to inspect it under the maintenance that comes with the installation.",
    "Thank you.",
  ].join("\n");
}

const acting = (v) => v.verdict !== "OK" && v.cause !== "no_data";
const tone = (v) => `v-${v.verdict.toLowerCase()} c-${v.cause}`;

/** One line of evidence for the "Why" tile, taken from what the analysis found. */
function whyLine(v) {
  const e = v.evidence || {};
  if (e.step_date) return `Fell ${Math.round(e.drop_pct)}% on ${day(e.step_date)}`;
  if (e.dip_days) return `${e.dip_days.length} sharp dips this month`;
  if (e.pm25) return `Air at PM2.5 ${e.pm25}`;
  if (e.rate_pct_per_day) return `${e.rate_pct_per_day}% a day for ${e.days_since_clean} days`;
  return v.cause === "no_data" ? "Not enough days yet" : "The last 90 days";
}

/** The first screen: the roof as a model, the weather around it, and what to do. */
export function RoofTab({ house, verdict: v, go }) {
  const known = v.cause !== "no_data";
  const running = Math.max(0, Math.round(100 - v.loss_pct));
  const week = v.forecast || [];
  const today = week[0];
  const rain = week.find((d) => d.rain_mm >= 5);
  const totals = weekTotals(v);
  const lost = !known ? "Needs two weeks of readings"
    : acting(v) && v.loss_rs_per_week > 0 ? `About ₹${v.loss_rs_per_week} a week lost`
    : "Nothing to fix";

  return (
    <article className={`roof ${tone(v)}`}>
      <header className="top">
        <div>
          <p className="brand">Dhool</p>
          <p className="home-name">{house.name}</p>
        </div>
        {known && (
          <p className="running" aria-label={`Running at ${running}% of this roof's normal`}>
            <Icon name="bolt" /> {running}%
          </p>
        )}
      </header>

      <div className="hero"><PanelModel verdict={v} /></div>

      <dl className="strip card">
        <div>
          <Icon name={today ? skyOf(today, week) : "sun"} />
          <dt>Today</dt><dd>{today ? `${today.temp_max}°` : "–"}</dd>
        </div>
        <div>
          <Icon name="rain" />
          <dt>Next rain</dt><dd>{!week.length ? "–" : rain ? weekday(rain.date) : "None"}</dd>
        </div>
        <div>
          <Icon name="gauge" />
          <dt>Units possible</dt><dd>{today ? today.possible_kwh : "–"}</dd>
        </div>
        <div>
          <Icon name="week" />
          <dt>Last reading</dt><dd>{day(v.as_of)}</dd>
        </div>
      </dl>

      <section className="card verdict-card">
        <div className="vc-top">
          <Icon name="bolt" />
          <h1>{HEADLINE[`${v.verdict}:${v.cause}`] || v.verdict}</h1>
          {known && <span className="pct">{running}%</span>}
        </div>
        <div className="glow-meter" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow={known ? running : 0}
             aria-label="Output compared with this roof's normal">
          <i style={{ width: `${known ? Math.min(100, running) : 0}%` }} />
        </div>
        <div className="vc-sub"><strong>{lost}</strong><span>{SURE_SHORT[v.confidence]}</span></div>
        <p className="reason">{v.reason}</p>
        {v.verdict === "INSPECT" && (
          <a className="primary" href={`https://wa.me/?text=${encodeURIComponent(vendorMessage(house, v))}`}
             target="_blank" rel="noreferrer">Message your vendor on WhatsApp</a>
        )}
        {v.verdict === "CLEAN" && (
          <p className="note">Wash early in the morning or after sunset, with plain water and a soft cloth. Never on hot panels.</p>
        )}
      </section>

      <div className="tiles">
        <button className="card tile" onClick={() => go("week")}>
          <span className="badge"><Icon name="week" /></span>
          <strong>Next 7 days</strong>
          <span>{totals ? `${totals[0]} of ${totals[1]} units likely` : "No forecast yet"}</span>
        </button>
        <button className="card tile" onClick={() => go("why")}>
          <span className="badge"><Icon name="why" /></span>
          <strong>Why</strong>
          <span>{whyLine(v)}</span>
        </button>
      </div>
    </article>
  );
}

export function WeekTab({ verdict: v }) {
  return (
    <article className={`tab ${tone(v)}`}>
      <h1>The next 7 days</h1>
      <Forecast verdict={v} />
    </article>
  );
}

export function WhyTab({ verdict: v }) {
  return (
    <article className={`tab ${tone(v)}`}>
      <h1>Why Dhool says this</h1>
      <p className="lede">{v.reason}</p>
      <div className="card stack">
        <dl className="figures">
          <div><dt>Should have made</dt><dd>{v.expected_kwh}<span> units</span></dd></div>
          <div><dt>Made</dt><dd>{v.actual_kwh}<span> units</span></dd></div>
        </dl>
        {acting(v) && v.loss_rs_per_week > 0 && (
          <p className="loss">
            About <strong>₹{v.loss_rs_per_week} a week</strong> is being lost ({v.loss_kwh_per_day} units a day, {TARIFF_NOTE}).
          </p>
        )}
      </div>
      <div className="card stack">
        <WhyChart verdict={v} />
        <p className="sure">{SURE[v.confidence]} Reading from {day(v.as_of)}.</p>
      </div>
    </article>
  );
}

function AddData({ house, onSent }) {
  const today = new Date().toLocaleDateString("en-CA");
  const base = `/houses/${house.house_id}`;
  const [key, setKey] = useState("");
  const [reading, setReading] = useState({ date: today, kwh: "" });
  const [shot, setShot] = useState(null); // null, { readings, app } once read, or { failed: true }
  const [state, run] = useAction();
  const send = (path, body) => (e) => { e?.preventDefault(); run(async () => { await api(base + path, body()); onSent(); }); };

  const upload = (file) => run(async () => {
    setShot(null);
    const slot = await api(`${base}/screenshots`, { content_type: file.type });
    const form = new FormData();
    Object.entries(slot.fields).forEach(([name, value]) => form.append(name, value));
    form.append("file", file);
    const sent = await fetch(slot.url, { method: "POST", body: form });
    if (!sent.ok) throw new Error("The upload did not go through. Check the image is under 5 MB, then try again.");
    const result = await api(`${base}/screenshots/read`, { key: slot.key });
    setShot(result.ok ? result : { failed: true });
  });
  const demoApp = <a href={`${API_URL}/mock/app`} target="_blank" rel="noreferrer">demo inverter app</a>;

  return (
    <section className="add-data">
      <h1>How should Dhool get your readings?</h1>

      <div className="card stack">
        <h2>Upload a screenshot</h2>
        <p className="note">
          A screenshot of your inverter app's daily generation screen. This demo can read images saved from
          the {demoApp}; for any other screenshot, type the number in below.
        </p>
        {shot?.readings ? (
          <>
            <p>Dhool read {shot.readings.length} days from {shot.app || "your screenshot"}. Check them before saving.</p>
            <ul className="read-list" aria-label="Readings found in the screenshot">
              {[...shot.readings].reverse().map((r) => <li key={r.date}><span>{day(r.date)}</span><strong>{r.kwh} units</strong></li>)}
            </ul>
            <button className="primary" disabled={state.busy}
                    onClick={send("/readings", () => ({ readings: shot.readings, source: "screenshot" }))}>
              These are right. Save them
            </button>
            <button className="link" onClick={() => setShot(null)}>Not right? Choose another image</button>
          </>
        ) : (
          <label className="secondary file">
            {state.busy ? "Reading…" : "Choose a screenshot"}
            <input type="file" accept="image/png,image/jpeg,image/webp" disabled={state.busy}
                   onChange={(e) => { const file = e.target.files[0]; e.target.value = ""; if (file) upload(file); }} />
          </label>
        )}
        {shot?.failed && <p className="error" role="alert">Dhool could not read that image. Type the number in below.</p>}
      </div>

      <form className="card" onSubmit={send("/inverter", () => ({ api_key: key.trim() }))}>
        <h2>Connect your inverter</h2>
        <p className="note">
          Dhool then reads every day on its own. Copy your API key from the {demoApp}. It holds simulated
          homes, not a real inverter brand.
        </p>
        <Field label="API key from your inverter app" required autoComplete="off" autoCapitalize="none" spellCheck={false}
               value={key} onChange={(e) => setKey(e.target.value)} />
        <button className="primary" disabled={state.busy}>Connect</button>
      </form>

      <form className="card" onSubmit={send("/readings", () => ({ date: reading.date, kwh: Number(reading.kwh) }))}>
        <h2>Or type today's number</h2>
        <div className="row">
          <Field label="Date" type="date" max={today} required value={reading.date} onChange={(e) => setReading({ ...reading, date: e.target.value })} />
          <Field label="Units made (kWh)" inputMode="decimal" required value={reading.kwh} onChange={(e) => setReading({ ...reading, kwh: e.target.value })} />
        </div>
        <button className="secondary" disabled={state.busy}>Save reading</button>
      </form>
      <ErrorLine error={state.error} />
    </section>
  );
}

function Invite({ house }) {
  const [code, setCode] = useState("");
  const [state, run] = useAction();
  if (house.role !== "owner") return null;
  return (
    <section className="card invite">
      <h2>Share with your family</h2>
      {code ? (
        <>
          <p className="code" aria-label={`Family code ${code.split("").join(" ")}`}>{code}</p>
          <p className="note">Works for 7 days. Anyone who joins sees this home's readings and verdicts.</p>
          <a className="secondary" target="_blank" rel="noreferrer"
             href={`https://wa.me/?text=${encodeURIComponent(`Join our home on Dhool with this code: ${code}`)}`}>Send on WhatsApp</a>
        </>
      ) : (
        <button className="secondary" disabled={state.busy}
                onClick={() => run(async () => setCode((await api(`/houses/${house.house_id}/invites`, {})).code))}>
          Get a family code
        </button>
      )}
      <ErrorLine error={state.error} />
    </section>
  );
}

const TABS = [["roof", "Roof"], ["week", "Forecast"], ["why", "Why"], ["setup", "Setup"]];

function Nav({ tab, go }) {
  return (
    <nav className="nav" aria-label="Sections">
      <div>
        {TABS.map(([id, label]) => (
          <button key={id} aria-current={tab === id ? "page" : undefined} onClick={() => go(id)}>
            <Icon name={id} />{label}
          </button>
        ))}
      </div>
    </nav>
  );
}

function Home({ house, onSignOut }) {
  const [verdict, setVerdict] = useState(undefined); // undefined = loading, null-verdict = none yet
  const [waiting, setWaiting] = useState(false);
  const [tab, setTab] = useState("roof");
  const [error, setError] = useState("");
  const timer = useRef();

  const load = () => api(`/houses/${house.house_id}/verdict`).then(setVerdict).catch((e) => setError(e.message));
  useEffect(() => { load(); return () => clearInterval(timer.current); }, [house.house_id]);
  // The sky behind the app is the weather over this roof. If it cannot be fetched, the clock's sky stays.
  useEffect(() => {
    api(`/houses/${house.house_id}`).then((h) => skyOver(h.lat, h.lon)).then(setSky).catch(() => {});
  }, [house.house_id]);
  const go = (id) => { setTab(id); window.scrollTo(0, 0); };

  // New data was sent: the analysis runs in the background, so check until a fresh verdict lands.
  const awaitVerdict = () => {
    const before = verdict?.computed_at;
    let tries = 0;
    go("roof");
    setWaiting(true);
    clearInterval(timer.current);
    timer.current = setInterval(async () => {
      const next = await api(`/houses/${house.house_id}/verdict`).catch(() => null);
      if ((next?.verdict && next.computed_at !== before) || ++tries > 20) {
        clearInterval(timer.current);
        setWaiting(false);
        if (next) setVerdict(next);
      }
    }, 4000);
  };

  const has = verdict?.verdict;
  const setup = (
    <>
      <AddData house={house} onSent={awaitVerdict} />
      <Invite house={house} />
      <button className="secondary" onClick={onSignOut}>Sign out</button>
    </>
  );
  return (
    <main className={`page ${has && !waiting ? "has-nav" : ""}`}>
      <ErrorLine error={error} />
      {waiting ? (
        <section className="working" aria-live="polite">
          <p className="brand">Dhool</p>
          <div className="hero"><PanelModel verdict={{ cause: "no_data" }} /></div>
          <h1>Working it out</h1>
          <p className="lede">Checking the sun, clouds and rain over your roof for each day. This takes about 20 seconds.</p>
        </section>
      ) : verdict === undefined ? (
        <p className="lede" aria-live="polite">Loading your home…</p>
      ) : !has ? (
        <>
          <header className="top"><div><p className="brand">Dhool</p><p className="home-name">{house.name}</p></div></header>
          {setup}
        </>
      ) : tab === "roof" ? <RoofTab house={house} verdict={verdict} go={go} />
        : tab === "week" ? <WeekTab verdict={verdict} />
        : tab === "why" ? <WhyTab verdict={verdict} />
        : <article className="tab">{setup}</article>}
      {has && !waiting && <Nav tab={tab} go={go} />}
    </main>
  );
}

function Preview() {
  const house = { name: "Sharma house" };
  return (
    <main className="page preview">
      {FIXTURES.map((v) => <RoofTab key={v.cause + v.verdict} house={house} verdict={v} go={() => {}} />)}
      <WeekTab verdict={FIXTURES[0]} />
      <WhyTab verdict={FIXTURES[0]} />
      <Nav tab="roof" go={() => {}} />
    </main>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(signedIn());
  const [houses, setHouses] = useState(null);
  const [error, setError] = useState("");

  const loadHouses = () =>
    api("/me").then((me) => setHouses(me.houses)).catch((e) => (e.signedOut ? setAuthed(false) : setError(e.message)));
  useEffect(() => { if (authed) loadHouses(); }, [authed]);

  if (import.meta.env.DEV && location.hash === "#preview") return <Preview />;
  if (!authed) return <Auth onDone={() => setAuthed(true)} />;
  if (error) return <main className="page"><ErrorLine error={error} /><button className="secondary" onClick={() => { setError(""); loadHouses(); }}>Try again</button></main>;
  if (!houses) return <main className="page"><p className="lede" aria-live="polite">Loading…</p></main>;
  if (!houses.length) return <Setup onDone={loadHouses} />;
  // ponytail: shows the first home only. Add a switcher when someone belongs to two.
  return <Home house={houses[0]} onSignOut={() => { signOut(); setHouses(null); setAuthed(false); }} />;
}
