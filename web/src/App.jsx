import { useEffect, useRef, useState } from "react";
import { api, confirmSignUp, plants, signedIn, signIn, signOut, signUp } from "./api.js";
import { TARIFF_NOTE } from "./config.js";
import { FIXTURES } from "./fixtures.js";
import { day, Forecast, Panel, WhyChart } from "./visuals.jsx";

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
      <Panel verdict={{ cause: "dust", loss_pct: 12 }} />
      <h1>Is your solar actually working?</h1>
      <p className="lede">
        Your inverter app shows a number. Dhool tells you what your roof should have made, and what to do
        when it falls short.
      </p>
      <form onSubmit={submit}>
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
      </form>
      {mode !== "code" && (
        <button className="link" onClick={() => setMode(mode === "in" ? "up" : "in")}>
          {mode === "in" ? "New here? Create an account" : "Already have an account? Sign in"}
        </button>
      )}
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
      <h1>Add your home</h1>
      <p className="lede">Dhool needs to know where your roof is and how big the system is. That is all.</p>
      <form onSubmit={create}>
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

      <h2>Someone at home already uses Dhool?</h2>
      <form onSubmit={join}>
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

export function VerdictView({ house, verdict: v }) {
  const acting = v.verdict !== "OK" && v.cause !== "no_data";
  return (
    <article className={`verdict v-${v.verdict.toLowerCase()} c-${v.cause}`}>
      <Panel verdict={v} />
      <h1>{HEADLINE[`${v.verdict}:${v.cause}`] || v.verdict}</h1>
      <p className="reason">{v.reason}</p>

      <dl className="figures">
        <div><dt>Should have made</dt><dd>{v.expected_kwh}<span> units</span></dd></div>
        <div><dt>Made</dt><dd>{v.actual_kwh}<span> units</span></dd></div>
      </dl>
      {acting && v.loss_rs_per_week > 0 && (
        <p className="loss">
          About <strong>₹{v.loss_rs_per_week} a week</strong> is being lost ({v.loss_kwh_per_day} units a day, {TARIFF_NOTE}).
        </p>
      )}
      <p className="sure">{SURE[v.confidence]} Reading from {day(v.as_of)}.</p>

      {v.verdict === "INSPECT" && (
        <a className="primary" href={`https://wa.me/?text=${encodeURIComponent(vendorMessage(house, v))}`}
           target="_blank" rel="noreferrer">Message your vendor on WhatsApp</a>
      )}
      {v.verdict === "CLEAN" && (
        <p className="note">Wash early in the morning or after sunset, with plain water and a soft cloth. Never on hot panels.</p>
      )}

      <Forecast verdict={v} />

      <details open={acting}>
        <summary>Why Dhool says this</summary>
        <WhyChart verdict={v} />
      </details>
    </article>
  );
}

function AddData({ house, onSent }) {
  const [list, setList] = useState(null);
  const [plant, setPlant] = useState("");
  const today = new Date().toLocaleDateString("en-CA");
  const [reading, setReading] = useState({ date: today, kwh: "" });
  const [state, run] = useAction();

  useEffect(() => {
    plants().then((p) => { setList(p); setPlant(p[0]?.id || ""); }).catch(() => setList([]));
  }, []);

  return (
    <section className="add-data">
      <h1>How should Dhool get your readings?</h1>
      <form onSubmit={(e) => { e.preventDefault(); run(async () => { await api(`/houses/${house.house_id}/inverter`, { plant_id: plant }); onSent(); }); }}>
        <h2>Connect your inverter</h2>
        <p className="note">Dhool reads every day on its own. This demo connects to simulated homes, not a real inverter brand.</p>
        <label className="field">
          <span>Inverter account</span>
          <select value={plant} onChange={(e) => setPlant(e.target.value)} disabled={!list?.length}>
            {(list || []).map((p) => <option key={p.id} value={p.id}>{p.id} ({p.kw} kW)</option>)}
          </select>
        </label>
        <button className="primary" disabled={state.busy || !plant}>Connect</button>
      </form>
      <form onSubmit={(e) => { e.preventDefault(); run(async () => { await api(`/houses/${house.house_id}/readings`, { date: reading.date, kwh: Number(reading.kwh) }); onSent(); }); }}>
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
    <section className="invite">
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

function Home({ house, onSignOut }) {
  const [verdict, setVerdict] = useState(undefined); // undefined = loading, null-verdict = none yet
  const [waiting, setWaiting] = useState(false);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const timer = useRef();

  const load = () => api(`/houses/${house.house_id}/verdict`).then(setVerdict).catch((e) => setError(e.message));
  useEffect(() => { load(); return () => clearInterval(timer.current); }, [house.house_id]);

  // New data was sent: the analysis runs in the background, so check until a fresh verdict lands.
  const awaitVerdict = () => {
    const before = verdict?.computed_at;
    let tries = 0;
    setAdding(false);
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
  return (
    <main className="page">
      <header className="bar">
        <span className="wordmark">Dhool</span>
        <span className="house">{house.name}</span>
        <button className="link" onClick={onSignOut}>Sign out</button>
      </header>
      <ErrorLine error={error} />
      {waiting ? (
        <section className="working" aria-live="polite">
          <Panel verdict={{ cause: "no_data" }} />
          <h1>Working it out</h1>
          <p className="lede">Checking the sun, clouds and rain over your roof for each day. This takes about 20 seconds.</p>
        </section>
      ) : verdict === undefined ? (
        <p className="lede" aria-live="polite">Loading your home…</p>
      ) : has && !adding ? (
        <>
          <VerdictView house={house} verdict={verdict} />
          <button className="link" onClick={() => setAdding(true)}>Add a reading or change the inverter</button>
        </>
      ) : (
        <AddData house={house} onSent={awaitVerdict} />
      )}
      <Invite house={house} />
    </main>
  );
}

function Preview() {
  const house = { name: "Sharma house" };
  return (
    <main className="page preview">
      {FIXTURES.map((v) => <VerdictView key={v.cause + v.verdict} house={house} verdict={v} />)}
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
