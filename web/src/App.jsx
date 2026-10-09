import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { api, confirmSignUp, signedIn, signIn, signOut, signUp } from "./api.js";
import { CheckCard, ReportAction, VendorReply } from "./check.jsx";
import { API_URL, TARIFF_NOTE } from "./config.js";
import { FIXTURES } from "./fixtures.js";
import { lang, setLang, t } from "./i18n.js";
import { Log, WashCost } from "./plan.jsx";
import { setSky, skyOver } from "./sky.js";
import { headline } from "./words.js";
import { day, Forecast, Icon, PanelModel, skyOf, weekday, weekTotals, WhyChart } from "./visuals.jsx";

const SURE = { high: t("Dhool is sure about this."), medium: t("Dhool is fairly sure about this."), low: t("Dhool is not sure yet.") };
const SURE_SHORT = { high: t("Dhool is sure"), medium: t("Fairly sure"), low: t("Not sure yet") };

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

const ErrorLine = ({ error }) => (error ? <p className="error" role="alert">{t(error)}</p> : null);
/** The reason that goes with a verdict. The server sends both languages; verdicts stored before it did have English only. */
const reasonOf = (v) => (lang === "hi" && v.reason_hi) || v.reason;

/** English or हिंदी. Each is named in its own language, so it can be found by someone who reads only that one. */
function Language() {
  return (
    <div className="reply-kinds" role="group" aria-label={t("Language")}>
      <button type="button" lang="en" aria-pressed={lang === "en"} onClick={() => setLang("en")}>English</button>
      <button type="button" lang="hi" aria-pressed={lang === "hi"} onClick={() => setLang("hi")}>हिंदी</button>
    </div>
  );
}

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
      <h1>{t("Is your solar actually working?")}</h1>
      <p className="lede">
        {t("Your inverter app shows a number. Dhool tells you what your roof should have made, and what to do when it falls short.")}
      </p>
      <form onSubmit={submit} className="card">
        {mode === "code" ? (
          <Field label={t("Code from your email")} inputMode="numeric" autoComplete="one-time-code" required
                 value={form.code} onChange={set("code")} hint={t("Sent to {email}", { email: form.email })} />
        ) : (
          <>
            <Field label={t("Email")} type="email" autoComplete="email" required value={form.email} onChange={set("email")} />
            <Field label={t("Password")} type="password" required minLength={8} value={form.password} onChange={set("password")}
                   autoComplete={mode === "up" ? "new-password" : "current-password"}
                   hint={mode === "up" ? t("At least 8 characters, with a capital letter, a number and a symbol") : undefined} />
          </>
        )}
        <ErrorLine error={state.error} />
        <button className="primary" disabled={state.busy}>
          {state.busy ? t("One moment…") : mode === "in" ? t("Sign in") : mode === "up" ? t("Create account") : t("Confirm and sign in")}
        </button>
        {mode !== "code" && (
          <button type="button" className="link" onClick={() => setMode(mode === "in" ? "up" : "in")}>
            {mode === "in" ? t("New here? Create an account") : t("Already have an account? Sign in")}
          </button>
        )}
      </form>
      <Language />
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
      <h1>{t("Add your home")}</h1>
      <p className="lede">{t("Dhool needs to know where your roof is and how big the system is. That is all.")}</p>
      <form onSubmit={create} className="card">
        <Field label={t("Name for this home")} required maxLength={60} placeholder={t("Sharma house")} value={form.name} onChange={set("name")} />
        <label className="field">
          <span>{t("System size")}</span>
          <select value={form.kw} onChange={set("kw")}>
            {[1, 2, 3, 4, 5, 6, 8, 10].map((kw) => <option key={kw} value={kw}>{kw} kW</option>)}
          </select>
          <small>{t("It is on your installation papers and in your inverter app.")}</small>
        </label>
        <div className="row">
          <Field label={t("Latitude")} inputMode="decimal" required value={form.lat} onChange={set("lat")} />
          <Field label={t("Longitude")} inputMode="decimal" required value={form.lon} onChange={set("lon")} />
        </div>
        <button type="button" className="secondary" onClick={locate}>{t("Use my location")}</button>
        {locationHelp && <p className="note">{t("Location is off for this site. Type the two numbers in, or allow location and try again.")}</p>}
        <ErrorLine error={state.error} />
        <button className="primary" disabled={state.busy}>{state.busy ? t("Saving…") : t("Add home")}</button>
      </form>

      <form onSubmit={join} className="card">
        <h2>{t("Someone at home already uses Dhool?")}</h2>
        <Field label={t("Family code")} required maxLength={6} autoCapitalize="characters" className="code-input"
               value={form.code} onChange={set("code")} hint={t("Ask them for the six-letter code from their Dhool app.")} />
        <button className="secondary" disabled={state.busy}>{t("Join their home")}</button>
      </form>
    </main>
  );
}

function vendorMessage(house, v) {
  return [
    t("Namaste,"),
    t("Our rooftop solar system ({name}) is producing much less than it should.", { name: house.name }),
    reasonOf(v),
    t("In the week to {date} it made about {made} units a day, where it normally makes {normal} in that weather.",
      { date: day(v.as_of), made: v.actual_kwh, normal: v.expected_kwh }),
    t("Please send someone to inspect it under the maintenance that comes with the installation."),
    t("Thank you."),
  ].join("\n");
}

const acting = (v) => v.verdict !== "OK" && v.cause !== "no_data";
const tone = (v) => `v-${v.verdict.toLowerCase()} c-${v.cause}`;

/** One line of evidence for the "Why" tile, taken from what the analysis found. */
function whyLine(v) {
  const e = v.evidence || {};
  if (e.step_date) return t("Fell {pct}% on {date}", { pct: Math.round(e.drop_pct), date: day(e.step_date) });
  if (e.dip_days) return t("{n} sharp dips this month", { n: e.dip_days.length });
  if (e.pm25) return t("Air at PM2.5 {pm}", { pm: e.pm25 });
  if (e.rate_pct_per_day) return t("{rate}% a day for {days} days", { rate: e.rate_pct_per_day, days: e.days_since_clean });
  return v.cause === "no_data" ? t("Not enough days yet") : t("The last 90 days");
}

/** The first screen: the roof as a model, the weather around it, and what to do. */
export function RoofTab({ house, verdict: v, go, onAction }) {
  const scene = useRef(null);
  // The scene stays where it first appears while everything after it slides over, like a weather app's
  // backdrop. Sticky needs a "top": measure where the scene sits in the page when it is not stuck.
  useLayoutEffect(() => {
    const el = scene.current;
    const pin = () => {
      el.style.position = "static";
      const top = el.getBoundingClientRect().top + window.scrollY;
      el.style.position = "";
      el.style.top = `${top}px`;
    };
    pin();
    window.addEventListener("resize", pin);
    return () => window.removeEventListener("resize", pin);
  }, []);
  // Once the page moves, the background below the top 30% of the screen blurs in (see .veil).
  useEffect(() => {
    let frame = 0;
    const root = document.documentElement.style;
    const update = () => { frame = 0; root.setProperty("--scrolled", Math.min(1, window.scrollY / 160).toFixed(3)); };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => { window.removeEventListener("scroll", onScroll); cancelAnimationFrame(frame); root.removeProperty("--scrolled"); };
  }, []);
  const known = v.cause !== "no_data";
  const running = Math.max(0, Math.round(100 - v.loss_pct));
  const week = v.forecast || [];
  const today = week[0];
  const rain = week.find((d) => d.rain_mm >= 5);
  const totals = weekTotals(v);
  const lost = !known ? t("Needs two weeks of readings")
    : acting(v) && v.loss_rs_per_week > 0 ? t("About ₹{rs} a week lost", { rs: v.loss_rs_per_week })
    : t("Nothing to fix");

  return (
    <article className={`roof ${tone(v)}`}>
      <header className="top">
        <div>
          <p className="brand">Dhool</p>
          <p className="home-name">{house.name}</p>
        </div>
        {known && (
          <p className="running" aria-label={t("Running at {pct}% of this roof's normal", { pct: running })}>
            <Icon name="bolt" /> {running}%
          </p>
        )}
      </header>

      <div className="hero" ref={scene}><PanelModel verdict={v} /></div>

      <dl className="strip card">
        <div>
          <Icon name={today ? skyOf(today, week) : "sun"} />
          <dt>{t("Today")}</dt><dd>{today ? `${today.temp_max}°` : "–"}</dd>
        </div>
        <div>
          <Icon name="rain" />
          <dt>{t("Next rain")}</dt><dd>{!week.length ? "–" : rain ? weekday(rain.date) : t("None")}</dd>
        </div>
        <div>
          <Icon name="gauge" />
          <dt>{t("Units possible")}</dt><dd>{today ? today.possible_kwh : "–"}</dd>
        </div>
        <div>
          <Icon name="week" />
          <dt>{t("Last reading")}</dt><dd>{day(v.as_of)}</dd>
        </div>
      </dl>

      <section className="card verdict-card">
        <div className="vc-top">
          <Icon name="bolt" />
          <h1>{headline(v)}</h1>
          {known && <span className="pct">{running}%</span>}
        </div>
        <div className="glow-meter" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow={known ? running : 0}
             aria-label={t("Output compared with this roof's normal")}>
          <i style={{ width: `${known ? Math.min(100, running) : 0}%` }} />
        </div>
        <div className="vc-sub"><strong>{lost}</strong><span>{SURE_SHORT[v.confidence]}</span></div>
        <p className="reason">{reasonOf(v)}</p>
        {v.verdict === "INSPECT" && (
          <a className="primary" href={`https://wa.me/?text=${encodeURIComponent(vendorMessage(house, v))}`}
             target="_blank" rel="noreferrer">{t("Message your vendor on WhatsApp")}</a>
        )}
        {v.verdict === "CLEAN" && (
          <p className="note">{t("Wash early in the morning or after sunset, with plain water and a soft cloth. Never on hot panels.")}</p>
        )}
        {onAction && v.verdict === "INSPECT" && <VendorReply house={house} />}
        {onAction && (v.verdict === "CLEAN" || v.verdict === "INSPECT") && (
          <ReportAction key={v.verdict} house={house} type={v.verdict === "CLEAN" ? "wash" : "visit"} onSent={onAction} />
        )}
      </section>
      {v.check && <CheckCard check={v.check} house={house} onSent={onAction} />}

      <div className="tiles">
        <button className="card tile" onClick={() => go("week")}>
          <span className="badge"><Icon name="week" /></span>
          <strong>{t("Next 7 days")}</strong>
          <span>{totals ? t("{likely} of {possible} units likely", { likely: totals[0], possible: totals[1] }) : t("No forecast yet")}</span>
        </button>
        <button className="card tile" onClick={() => go("why")}>
          <span className="badge"><Icon name="why" /></span>
          <strong>{t("Why")}</strong>
          <span>{whyLine(v)}</span>
        </button>
      </div>
      <div className="veil" aria-hidden="true" />
    </article>
  );
}

export function WeekTab({ verdict: v }) {
  return (
    <article className={`tab ${tone(v)}`}>
      <h1>{t("The next 7 days")}</h1>
      <Forecast verdict={v} />
    </article>
  );
}

export function WhyTab({ verdict: v, house, log }) {
  return (
    <article className={`tab ${tone(v)}`}>
      <h1>{t("Why Dhool says this")}</h1>
      <p className="lede">{reasonOf(v)}</p>
      <div className="card stack">
        <dl className="figures">
          <div><dt>{t("Should have made")}</dt><dd>{v.expected_kwh}<span> {t("units")}</span></dd></div>
          <div><dt>{t("Made")}</dt><dd>{v.actual_kwh}<span> {t("units")}</span></dd></div>
        </dl>
        <p className="note">
          {t("A day, on average, in the week to {date}.", { date: day(v.as_of) })}
          {v.cause !== "no_data" && t(" “Should have made” is what this roof normally makes in that weather.")}
        </p>
        {acting(v) && v.loss_rs_per_week > 0 && (
          <p className="loss">
            {t("About {amount} is being lost ({units} units a day, {tariff}).", {
              amount: <strong key="amount">{t("₹{rs} a week", { rs: v.loss_rs_per_week })}</strong>,
              units: v.loss_kwh_per_day, tariff: t(TARIFF_NOTE) })}
          </p>
        )}
      </div>
      <div className="card stack">
        <WhyChart verdict={v} />
        <p className="sure">{t("{sure} Reading from {date}.", { sure: SURE[v.confidence], date: day(v.as_of) })}</p>
      </div>
      {(house || log) && <Log house={house} entries={log} />}
    </article>
  );
}

/** While the model reads a screenshot: how long it has been, and the way to type the number instead. */
function Reading({ since, onType }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(tick);
  }, []);
  const s = Math.max(0, Math.round((now - since) / 1000));
  return (
    <div className="reading">
      <span className="spinner" aria-hidden="true" />
      <p role="status">
        {t("Reading your screenshot: about a minute. Stay on this page.")}
        {s > 120 && <small>{t("Still reading. After a quiet spell the reader starts up first, which can take up to five minutes.")}</small>}
      </p>
      <span className="elapsed" aria-hidden="true">{Math.floor(s / 60)}:{String(s % 60).padStart(2, "0")}</span>
      <button className="link" onClick={onType}>{t("Type the number instead")}</button>
    </div>
  );
}

function AddData({ house, onSent }) {
  const today = new Date().toLocaleDateString("en-CA");
  const base = `/houses/${house.house_id}`;
  const [key, setKey] = useState("");
  const [reading, setReading] = useState({ date: today, kwh: "" });
  const [shot, setShot] = useState(null); // null, { reading: true }, { rows } once read, or { failed: true }
  const [state, run] = useAction();
  const here = useRef(true);
  useEffect(() => () => { here.current = false; }, []);
  const send = (path, body) => (e) => { e?.preventDefault(); run(async () => { await api(base + path, body()); onSent(); }); };

  const upload = (file) => run(async () => {
    setShot({ reading: true, since: Date.now() });
    try {
      const slot = await api(`${base}/screenshots`, { content_type: file.type });
      const form = new FormData();
      Object.entries(slot.fields).forEach(([name, value]) => form.append(name, value));
      form.append("file", file);
      const sent = await fetch(slot.url, { method: "POST", body: form });
      if (!sent.ok) throw new Error(t("The upload did not go through. Check the image is under 5 MB, then try again."));
      const { shot_id } = await api(`${base}/screenshots/read`, { key: slot.key });
      waitFor(shot_id); // not awaited: the other ways in stay usable while the model reads
    } catch (e) {
      setShot(null);
      throw e;
    }
  });
  // A model reads the picture in the background, which takes about a minute: ask until it has finished.
  const waitFor = async (shotId) => {
    for (let asked = 0; asked < 150 && here.current; asked++) {
      await new Promise((done) => setTimeout(done, 4000));
      const result = await api(`${base}/screenshots/${shotId}`).catch(() => null); // a dropped connection: ask again
      if (result?.status === "read") return setShot({ rows: result.readings.map((r) => ({ date: r.date, kwh: String(r.kwh) })) });
      if (result?.status === "unreadable") break;
    }
    setShot({ failed: true });
  };
  const typeInstead = () => {
    const box = document.getElementById("typed-kwh");
    box.scrollIntoView({ block: "center", behavior: "smooth" });
    box.focus({ preventScroll: true });
  };
  const setRow = (date, kwh) => setShot({ rows: shot.rows.map((r) => (r.date === date ? { ...r, kwh } : r)) });
  const kept = () => shot.rows.filter((r) => r.kwh.trim() !== "").map((r) => ({ date: r.date, kwh: Number(r.kwh) }));
  const demoApp = <a href={`${API_URL}/mock/app`} target="_blank" rel="noreferrer" key="app">{t("demo inverter app")}</a>;

  return (
    <section className="add-data">
      <h1>{t("How should Dhool get your readings?")}</h1>

      <div className="card stack">
        <h2>{t("Upload a screenshot")}</h2>
        <p className="note">
          {t("A screenshot of your inverter app showing the units made each day: today's figure, or a list of days. Dhool reads the numbers printed on it; it does not guess from charts. Try it with a screen saved from the {app}.", { app: demoApp })}
        </p>
        {shot?.rows ? (
          <>
            <p>
              {t("Dhool read {days} from your screenshot. Check them against it. Correct any number that is wrong, or clear a box to leave that day out.",
                 { days: shot.rows.length === 1 ? t("1 day") : t("{n} days", { n: shot.rows.length }) })}
            </p>
            <ul className="read-list" aria-label={t("Readings found in the screenshot")}>
              {[...shot.rows].reverse().map((r) => (
                <li key={r.date}>
                  <label htmlFor={`read-${r.date}`}>{day(r.date)}</label>
                  <input id={`read-${r.date}`} inputMode="decimal" value={r.kwh} onChange={(e) => setRow(r.date, e.target.value)} />
                  <span>{t("units")}</span>
                </li>
              ))}
            </ul>
            <button className="primary" disabled={state.busy || !kept().length}
                    onClick={send("/readings", () => ({ readings: kept(), source: "screenshot" }))}>
              {t("These are right. Save them")}
            </button>
            <button className="link" onClick={() => setShot(null)}>{t("Not right? Choose another image")}</button>
          </>
        ) : shot?.reading ? (
          <Reading since={shot.since} onType={typeInstead} />
        ) : (
          <label className="secondary file">
            {t("Choose a screenshot")}
            <input type="file" accept="image/png,image/jpeg" disabled={state.busy}
                   onChange={(e) => { const file = e.target.files[0]; e.target.value = ""; if (file) upload(file); }} />
          </label>
        )}
        {shot?.failed && (
          <>
            <p className="error" role="alert">
              {t("Dhool could not read daily units from that image. Try a screen where the number is printed, or type it in.")}
            </p>
            <button className="link" onClick={typeInstead}>{t("Type the number instead")}</button>
          </>
        )}
      </div>

      <form className="card" onSubmit={send("/inverter", () => ({ api_key: key.trim() }))}>
        <h2>{t("Connect your inverter")}</h2>
        <p className="note">
          {t("Dhool then reads every day on its own. Copy your API key from the {app}. It holds simulated homes, not a real inverter brand.", { app: demoApp })}
        </p>
        <Field label={t("API key from your inverter app")} required autoComplete="off" autoCapitalize="none" spellCheck={false}
               value={key} onChange={(e) => setKey(e.target.value)} />
        <button className="primary" disabled={state.busy}>{t("Connect")}</button>
      </form>

      <form className="card" onSubmit={send("/readings", () => ({ date: reading.date, kwh: Number(reading.kwh) }))}>
        <h2>{t("Or type today's number")}</h2>
        <div className="row">
          <Field label={t("Date")} type="date" max={today} required value={reading.date} onChange={(e) => setReading({ ...reading, date: e.target.value })} />
          <Field label={t("Units made (kWh)")} id="typed-kwh" inputMode="decimal" required value={reading.kwh} onChange={(e) => setReading({ ...reading, kwh: e.target.value })} />
        </div>
        <button className="secondary" disabled={state.busy}>{t("Save reading")}</button>
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
      <h2>{t("Share with your family")}</h2>
      {code ? (
        <>
          <p className="code" aria-label={t("Family code {code}", { code: code.split("").join(" ") })}>{code}</p>
          <p className="note">{t("Works for 7 days. Anyone who joins sees this home's readings and verdicts.")}</p>
          <a className="secondary" target="_blank" rel="noreferrer"
             href={`https://wa.me/?text=${encodeURIComponent(t("Join our home on Dhool with this code: {code}", { code }))}`}>{t("Send on WhatsApp")}</a>
        </>
      ) : (
        <button className="secondary" disabled={state.busy}
                onClick={() => run(async () => setCode((await api(`/houses/${house.house_id}/invites`, {})).code))}>
          {t("Get a family code")}
        </button>
      )}
      <ErrorLine error={state.error} />
    </section>
  );
}

const TABS = [["roof", t("Roof")], ["week", t("Forecast")], ["why", t("Why")], ["setup", t("Setup")]];

function Nav({ tab, go }) {
  return (
    <nav className="nav" aria-label={t("Sections")}>
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
    let every, gone = false;
    api(`/houses/${house.house_id}`).then((h) => {
      if (gone) return;
      const look = () => skyOver(h.lat, h.lon).then(setSky).catch(() => {});
      look();
      every = setInterval(look, 10 * 60 * 1000);  // the weather moves on while the app stays open
    }).catch(() => {});
    return () => { gone = true; clearInterval(every); };
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
      <WashCost house={house} onSent={awaitVerdict} />
      <Invite house={house} />
      <section className="card"><h2 lang="en">Language · <span lang="hi">भाषा</span></h2><Language /></section>
      <button className="secondary" onClick={onSignOut}>{t("Sign out")}</button>
    </>
  );
  return (
    <main className={`page ${has && !waiting ? "has-nav" : ""}`}>
      <ErrorLine error={error} />
      {waiting ? (
        <section className="working" aria-live="polite">
          <p className="brand">Dhool</p>
          <div className="hero"><PanelModel verdict={{ cause: "no_data" }} /></div>
          <h1>{t("Working it out")}</h1>
          <p className="lede">{t("Checking the sun, clouds and rain over your roof for each day. This takes about 20 seconds.")}</p>
        </section>
      ) : verdict === undefined ? (
        <p className="lede" aria-live="polite">{t("Loading your home…")}</p>
      ) : !has ? (
        <>
          <header className="top"><div><p className="brand">Dhool</p><p className="home-name">{house.name}</p></div></header>
          {setup}
        </>
      ) : tab === "roof" ? <RoofTab house={house} verdict={verdict} go={go} onAction={awaitVerdict} />
        : tab === "week" ? <WeekTab verdict={verdict} />
        : tab === "why" ? <WhyTab verdict={verdict} house={house} />
        : <article className="tab">{setup}</article>}
      {has && !waiting && <Nav tab={tab} go={go} />}
    </main>
  );
}

function Preview() {
  const house = { name: t("Sharma house") };
  return (
    <main className="page preview">
      {FIXTURES.map((v, i) => <RoofTab key={i} house={house} verdict={v} go={() => {}} onAction={() => {}} />)}
      <WeekTab verdict={FIXTURES[0]} />
      <WhyTab verdict={FIXTURES[0]} log={[
        { date: "2026-09-25", kind: "said", verdict: "OK", cause: "ok", loss_pct: 1 },
        { date: "2026-09-16", kind: "did", type: "wash", status: "verified" },
        { date: "2026-09-12", kind: "said", verdict: "CLEAN", cause: "dust", loss_pct: 13 },
        { date: "2026-09-05", kind: "said", verdict: "WAIT", cause: "dust", wait_for: "dust_storm", loss_pct: 9 },
        { date: "2026-08-20", kind: "said", verdict: "OK", cause: "ok", loss_pct: 2 },
      ]} />
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
  if (error) return <main className="page"><ErrorLine error={error} /><button className="secondary" onClick={() => { setError(""); loadHouses(); }}>{t("Try again")}</button></main>;
  if (!houses) return <main className="page"><p className="lede" aria-live="polite">{t("Loading…")}</p></main>;
  if (!houses.length) return <Setup onDone={loadHouses} />;
  // ponytail: shows the first home only. Add a switcher when someone belongs to two.
  return <Home house={houses[0]} onSignOut={() => { signOut(); setHouses(null); setAuthed(false); }} />;
}
