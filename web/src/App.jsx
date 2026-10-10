import { useEffect, useId, useRef, useState, useSyncExternalStore } from "react";
import { Alerts, Auth, DeleteAccount, Family, Homes, Setup, stopPush } from "./account.jsx";
import { api, signedIn, signOut } from "./api.js";
import { CheckCard, ReportAction, VendorReply } from "./check.jsx";
import { TARIFF_RS } from "./config.js";
import { FIXTURES } from "./fixtures.js";
import { ErrorLine, useAction } from "./form.jsx";
import { lang, setLang, t } from "./i18n.js";
import { Actions, Costs, Log, Size } from "./plan.jsx";
import { AddData } from "./readings.jsx";
import { setSky, skyOver } from "./sky.js";
import { daysSince, keep, kept, POLL_MS, STALE_DAYS } from "./store.js";
import { headline } from "./words.js";
import { day, Icon, monthName, Months, PanelModel, skyOf, weekday, when, WhyChart, Wordmark } from "./visuals.jsx";

const SURE = { high: t("Dhool is sure about this."), medium: t("Dhool is fairly sure about this."), low: t("Dhool is not sure yet.") };
const SURE_SHORT = { high: t("Dhool is sure"), medium: t("Fairly sure"), low: t("Not sure yet") };

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
  if (e.outage_days) {
    return e.outage_days === 1 ? t("Nothing made on {date}", { date: day(e.since) })
      : t("Nothing made for {n} days, since {date}", { n: e.outage_days, date: day(e.since) });
  }
  if (e.step_date) return t("Fell {pct}% on {date}", { pct: Math.round(e.drop_pct), date: day(e.step_date) });
  if (e.dip_days) return t("{n} sharp dips this month", { n: e.dip_days.length });
  if (e.pm25) return t("Air at PM2.5 {pm}", { pm: e.pm25 });
  if (e.rate_pct_per_day) return t("{rate}% a day for {days} days", { rate: e.rate_pct_per_day, days: e.days_since_clean });
  return v.cause === "no_data" ? t("Not enough days yet") : t("The last 90 days");
}

/**
 * Readings have stopped: the verdict under this card is as old as the last one. Worked out here from the
 * date, not by the nightly run, so it is right at any hour.
 */
function StaleCard({ house, asOf, today, go }) {
  const n = daysSince(asOf, today);
  if (!(n >= STALE_DAYS)) return null;
  return (
    <section className="card check stack">
      <h2>{t("No reading for {n} days", { n })}</h2>
      <p className="note">
        {t("The last reading Dhool has is from {date}. What you see below is from that day.", { date: day(asOf) })}{" "}
        {house.linked ? t("Your inverter may be offline. Check that it is switched on and that its Wi-Fi stick is connected.")
          : t("Add a new reading to bring this up to date.")}
      </p>
      {!house.linked && <button className="secondary" onClick={() => go("setup")}>{t("Add a reading")}</button>}
    </section>
  );
}

/**
 * Was the advice any use? One quiet line at the foot of the verdict card, asked once on this phone for each
 * day's verdict. The answer belongs to the home (one for a day): the last phone in the family to answer stands.
 */
function Useful({ house, date }) {
  const key = `useful.${house.house_id}`;
  // ponytail: the phone remembers only the last day it answered for a home. A verdict that moves back to an
  // earlier day is asked about again, and the server keeps the newer answer. Keep a list if that ever matters.
  const [stage, setStage] = useState(() => (kept(key) === date ? "answered" : "ask"));
  const [state, run] = useAction();
  const label = useId();
  const send = (helpful) => run(async () => {
    await api(`/houses/${house.house_id}/feedback`, { date, helpful });
    keep(key, date);
    setStage("thanked");
  });
  if (stage === "answered") return null;
  if (stage === "thanked") return <p className="useful" role="status">{t("Thanks for telling Dhool.")}</p>;
  return (
    <>
      <div className="useful" role="group" aria-labelledby={label}>
        <span id={label}>{t("Was this advice useful?")}</span>
        {/* A thumb to look at, a word for a screen reader. */}
        <button type="button" aria-label={t("Yes")} disabled={state.busy} onClick={() => send(true)}><Icon name="thumb" /></button>
        <button type="button" className="down" aria-label={t("No")} disabled={state.busy} onClick={() => send(false)}><Icon name="thumb" /></button>
      </div>
      <ErrorLine error={state.error} />
    </>
  );
}

/** The first screen: the roof as a model, the weather around it, and what to do. `today` is given only by the preview. */
export function RoofTab({ house, verdict: v, go, onAction, today: date }) {
  const scene = useRef(null);
  // The scene rises with the page until it sits under the top bar, and stays there while the sheets slide over
  // it (position: sticky, in the stylesheet). --scrolled (0 to 1) turns the bar to glass as soon as the page
  // moves; --covered (0 to 1) is how far the sheets have come over the scene, which goes out of focus with it.
  useEffect(() => {
    let frame = 0;
    const root = document.documentElement.style, el = scene.current;
    const update = () => {
      frame = 0;
      root.setProperty("--scrolled", Math.min(1, window.scrollY / 160).toFixed(3));
      const box = el.getBoundingClientRect(), next = el.nextElementSibling.getBoundingClientRect();
      // Where rain in the sky stops. Only a scene that is on screen says so (the preview page has several).
      if (box.bottom > 0 && box.top < window.innerHeight) root.setProperty("--floor", `${Math.round(box.top + box.height * 0.8)}px`);
      // The weather row lies over the scene's foreground from the start: only what comes past the array counts.
      el.style.setProperty("--covered", Math.min(1, Math.max(0, ((box.bottom - next.top) / box.height - 0.4) / 0.4)).toFixed(3));
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => { window.removeEventListener("scroll", onScroll); cancelAnimationFrame(frame); root.removeProperty("--scrolled"); root.removeProperty("--floor"); };
  }, []);
  const known = v.cause !== "no_data";
  const running = Math.max(0, Math.round(100 - v.loss_pct));
  const week = v.forecast || [];
  const today = week[0];
  const rain = week.find((d) => d.rain_mm >= 5);
  const month = v.months?.at(-1);  // the month of the last reading
  const lost = !known ? t("Needs two weeks of readings")
    : acting(v) && v.loss_rs_per_week > 0 ? t("About ₹{rs} a week lost", { rs: v.loss_rs_per_week })
    : t("Nothing to fix");

  return (
    <article className={`roof ${tone(v)}`}>
      <header className="top">
        <Wordmark />
        <p className="home-name">{house.name}</p>
      </header>

      {/* The reading, set in the sky over the roof the way a weather app sets the temperature: how the roof is
          running, then what to do about it. Everything further down supports these three lines. */}
      <section className="reading">
        {known && (
          <>
            <p className="reading-figure" aria-label={t("Running at {pct}% of this roof's normal", { pct: running })}>
              {running}<span aria-hidden="true">%</span>
            </p>
            <p className="reading-of">{t("of this roof's normal")}</p>
            <div className="glow-meter" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow={running}
                 aria-label={t("Output compared with this roof's normal")}>
              <i style={{ width: `${Math.min(100, running)}%` }} />
            </div>
          </>
        )}
        <h1 className="reading-verdict">{headline(v)}</h1>
        <p className="reading-sub">{lost}{known && <span>{SURE_SHORT[v.confidence]}</span>}</p>
      </section>

      <div className="hero" ref={scene}><PanelModel verdict={v} /><div className="fall" /></div>

      <dl className="strip">
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
          <Icon name="history" />
          <dt>{t("Last reading")}</dt><dd>{day(v.as_of)}</dd>
        </div>
      </dl>

      <StaleCard house={house} asOf={v.as_of} today={date} go={go} />
      <section className="card verdict-card">
        <p className="reason">{reasonOf(v)}</p>
        {v.verdict === "INSPECT" && (
          <a className="primary" href={`https://wa.me/?text=${encodeURIComponent(vendorMessage(house, v))}`}
             target="_blank" rel="noreferrer">{t("Message your vendor on WhatsApp")}</a>
        )}
        {v.verdict === "CLEAN" && (
          <p className="note">{t("Wash early in the morning or after sunset, with plain water and a soft cloth. Never on hot panels.")}</p>
        )}
        {onAction && v.verdict === "INSPECT" && (
          <details className="more">
            <summary>{t("The vendor replied")}</summary>
            <VendorReply house={house} />
          </details>
        )}
        {onAction && (v.verdict === "CLEAN" || v.verdict === "INSPECT") && (
          <ReportAction key={v.verdict} house={house} type={v.verdict === "CLEAN" ? "wash" : "visit"} onSent={onAction} />
        )}
        {known && <Useful key={v.as_of} house={house} date={v.as_of} />}
      </section>
      {v.check && <CheckCard check={v.check} house={house} onSent={onAction} />}

      <div className="card rows">
        <button className="row-link" onClick={() => go("history")}>
          <span>{t("History")}</span>
          <small>{month ? t("{units} units in {month}", { units: month.kwh, month: monthName(month.month) }) : t("Month by month")}</small>
        </button>
        <button className="row-link" onClick={() => go("why")}>
          <span>{t("Why")}</span>
          <small>{whyLine(v)}</small>
        </button>
      </div>
    </article>
  );
}

/** What the roof made month by month, and the washes and vendor visits the household reported. `actions` is given only by the preview. */
export function HistoryTab({ verdict: v, house, actions }) {
  return (
    <article className={`tab ${tone(v)}`}>
      <h1>{t("Generation History")}</h1>
      <Months verdict={v} />
      <Actions house={house} entries={actions} />
    </article>
  );
}

export function WhyTab({ verdict: v, house, log }) {
  return (
    <article className={`tab ${tone(v)}`}>
      <h1>{t("Synopsis")}</h1>
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
        {v.low_normal && (
          <p className="note">{t("Even in its best weeks this roof makes far less than a system of its size should. If the size in Setup is right, it may have been shaded, dirty or faulty since before Dhool started watching: have it checked once.")}</p>
        )}
        {acting(v) && v.loss_rs_per_week > 0 && (
          <p className="loss">
            {t("About {amount} is being lost ({units} units a day, {tariff}).", {
              amount: <strong key="amount">{t("₹{rs} a week", { rs: v.loss_rs_per_week })}</strong>,
              units: v.loss_kwh_per_day, tariff: t("at ₹{rs} a unit", { rs: v.tariff_rs ?? TARIFF_RS }) })}
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

function Invite({ house }) {
  const [code, setCode] = useState("");
  const [state, run] = useAction();
  if (house.role !== "owner") return null;
  return (
    <section className="card invite">
      <h2>{t("Family code")}</h2>
      {code ? (
        <>
          <p className="code" aria-label={t("Family code {code}", { code: code.split("").join(" ") })}>{code}</p>
          <p className="note">{t("Works for 7 days. Anyone who joins sees this home's readings and verdicts.")}</p>
          <a className="secondary" target="_blank" rel="noreferrer"
             href={`https://wa.me/?text=${encodeURIComponent(t("Join our home on Dhool with this code: {code}", { code }))}`}>{t("Send on WhatsApp")}</a>
        </>
      ) : (
        <button className="row-link" disabled={state.busy}
                onClick={() => run(async () => setCode((await api(`/houses/${house.house_id}/invites`, {})).code))}>
          <span>{t("Get a family code")}</span>
        </button>
      )}
      <ErrorLine error={state.error} />
    </section>
  );
}

const TABS = [["roof", t("Roof")], ["history", t("History")], ["why", t("Why")], ["setup", t("Setup")]];

function Nav({ tab, go }) {
  return (
    <nav className="nav" aria-label={t("Sections")}>
      {/* The lens sits behind the chosen tab; --at is that tab's place, and CSS slides the lens there. */}
      <div style={{ "--at": Math.max(0, TABS.findIndex(([id]) => id === tab)) }}>
        <span className="nav-lens" aria-hidden="true" />
        {TABS.map(([id, label]) => (
          <button key={id} aria-current={tab === id ? "page" : undefined} onClick={() => go(id)}>
            <Icon name={id} />{label}
          </button>
        ))}
      </div>
    </nav>
  );
}


// Each tab has its own address (#/roof, #/history, #/why, #/setup, and #/add for adding a home), so the phone's
// back button moves between them instead of leaving the app.
const onHash = (changed) => { window.addEventListener("hashchange", changed); return () => window.removeEventListener("hashchange", changed); };
const useHash = () => useSyncExternalStore(onHash, () => location.hash);
const go = (id) => { location.hash = `/${id}`; };

function Home({ house: listed, homes, onSignOut }) {
  const id = listed.house_id;
  const [verdict, setVerdict] = useState(undefined); // undefined = loading, null-verdict = none yet
  const [storedAt, setStoredAt] = useState(0);       // when the verdict on screen was kept, if it is not fresh from the network
  const [details, setDetails] = useState(null);      // what GET /houses/{id} adds to the list's entry: location, costs, linked, members
  const [waiting, setWaiting] = useState(false);
  const [late, setLate] = useState(null);            // the wait gave up: the verdict that was on screen then ("" if none)
  const [error, setError] = useState("");
  const round = useRef(0);
  const hash = useHash();
  const tab = TABS.find(([name]) => hash === `#/${name}`)?.[0] || "roof";
  const house = { ...listed, ...details };

  // The last verdict and details stay on the phone, to show when there is no network.
  const show = (v) => { keep(`verdict.${id}`, { v, at: Date.now() }); setStoredAt(0); setError(""); setVerdict(v); };
  const load = () => api(`/houses/${id}/verdict`).then(show).catch((e) => {
    const last = e.offline && kept(`verdict.${id}`);
    if (!last) return setError(e.message);
    setVerdict(last.v);
    setStoredAt(last.at);
  });
  const loadDetails = () =>
    api(`/houses/${id}`).then((h) => { keep(`home.${id}`, h); setDetails(h); }).catch(() => setDetails(kept(`home.${id}`)));
  // eslint-disable-next-line react-hooks/exhaustive-deps -- once per home: App gives each home its own Home (key)
  useEffect(() => { load(); loadDetails(); return () => { round.current = -1; }; }, [id]);
  // The sky behind the app is the weather over this roof. If it cannot be fetched, the clock's sky stays.
  const { lat, lon } = house;
  useEffect(() => {
    if (lat == null) return;
    let gone = false;
    const look = () => skyOver(lat, lon).then((sky) => gone || setSky(sky)).catch(() => {});
    look();
    const every = setInterval(look, 10 * 60 * 1000);  // the weather moves on while the app stays open
    return () => { gone = true; clearInterval(every); };
  }, [lat, lon]);
  useEffect(() => { window.scrollTo(0, 0); }, [tab, waiting]);

  // New data was sent: the analysis runs in the background, so ask until a fresh verdict lands. One question
  // at a time, and none once this home has left the screen or a newer wait has begun.
  const awaitVerdict = async () => {
    const before = verdict?.computed_at, mine = ++round.current;
    go("roof");
    setWaiting(true);
    setLate(null);
    loadDetails();  // what was sent may have changed them (an inverter linked, a new tariff)
    let next = null, fresh = false;
    for (const wait of POLL_MS) {
      await new Promise((done) => setTimeout(done, wait));
      if (mine !== round.current) return;
      next = await api(`/houses/${id}/verdict`).catch(() => null);
      fresh = Boolean(next?.verdict && next.computed_at !== before);
      if (fresh) break;
    }
    if (mine !== round.current) return;
    setWaiting(false);
    if (next) show(next);
    // Gave up with nothing new: say so, or the old verdict would pass for the answer to what was just sent.
    if (!fresh) setLate(before ?? "");
  };

  const has = verdict?.verdict;
  const setup = (
    <>
      <AddData house={house} onSent={awaitVerdict} />
      <Costs key={details ? "saved" : "default"} house={house} onSent={awaitVerdict} />
      <Size key={details ? "size" : "no-size"} house={house} onSent={awaitVerdict} />
      <Alerts house={house} />
      <Homes house={house} homes={homes} />
      <Invite house={house} />
      <Family house={house} onChange={loadDetails} onGone={homes.reload} />
      <section className="card stack"><h2 lang="en">Language{" · "}<span lang="hi">भाषा</span></h2><Language /></section>
      <button className="secondary" onClick={onSignOut}>{t("Sign out")}</button>
      <DeleteAccount houses={homes.all} onGone={onSignOut} />
    </>
  );
  return (
    <main className={`page ${has && !waiting ? "has-nav" : ""}`}>
      <ErrorLine error={error} />
      {storedAt > 0 && !waiting && (
        <section className="card stack" role="status">
          <p className="note">{t("No connection. This is the last result Dhool has, from {when}.", { when: when(storedAt) })}</p>
          <button className="link" onClick={load}>{t("Try again")}</button>
        </section>
      )}
      {late !== null && !waiting && (verdict?.computed_at ?? "") === late && (
        <section className="card stack" role="status">
          <p className="note">{t("This is taking longer than usual. What you see here does not include your change yet.")}</p>
          <button className="link" onClick={load}>{t("Check again")}</button>
        </section>
      )}
      {waiting ? (
        <section className="working" aria-live="polite">
          <Wordmark />
          <div className="hero"><PanelModel verdict={{ cause: "no_data" }} /></div>
          <h1>{t("Working it out")}</h1>
          <p className="lede">{t("Checking the sun, clouds and rain over your roof for each day. This takes about 20 seconds.")}</p>
        </section>
      ) : verdict === undefined ? (
        error ? <button className="secondary" onClick={() => { setError(""); load(); }}>{t("Try again")}</button>
          : <p className="lede" aria-live="polite">{t("Loading your home…")}</p>
      ) : !has ? (
        <>
          <header className="top"><Wordmark /><p className="home-name">{house.name}</p></header>
          {setup}
        </>
      ) : tab === "roof" ? <RoofTab house={house} verdict={verdict} go={go} onAction={awaitVerdict} />
        : tab === "history" ? <HistoryTab verdict={verdict} house={house} />
        : tab === "why" ? <WhyTab verdict={verdict} house={house} />
        : <article className="tab">{setup}</article>}
      {has && !waiting && <Nav tab={tab} go={go} />}
    </main>
  );
}

function Preview() {
  const house = { house_id: "preview", name: t("Sharma house"), role: "owner", kw: 3.3, wash_cost_rs: 50, tariff_rs: 7,
    members: [{ sub: "a", role: "owner", joined_at: null, me: true }, { sub: "b", role: "member", joined_at: 1791158400 }] };
  const guest = { ...house, role: "member" };
  const none = () => {};
  const stale = { asOf: "2026-09-25", today: "2026-09-29", go: none };
  return (
    <main className="page preview">
      {FIXTURES.map((v, i) => <RoofTab key={i} house={house} verdict={v} today={v.as_of} go={none} onAction={none} />)}
      <StaleCard house={{ linked: true }} {...stale} />
      <StaleCard house={house} {...stale} />
      <HistoryTab verdict={FIXTURES[0]} actions={[
        { date: "2026-09-16", type: "wash", status: "verified" },
        { date: "2026-08-19", type: "visit", status: "not_recovered" },
        { date: "2026-07-02", type: "wash", status: null },
      ]} />
      {/* A verdict from before the months were counted, and a home that has reported nothing. */}
      <HistoryTab verdict={{ ...FIXTURES[0], months: undefined }} actions={[]} />
      {/* A verdict from before the days were sent with the months: the months do not open. */}
      <HistoryTab verdict={{ ...FIXTURES[0], daily_kwh: undefined }} actions={[]} />
      <WhyTab verdict={FIXTURES[0]} log={[
        { date: "2026-09-25", kind: "said", verdict: "OK", cause: "ok", loss_pct: 1 },
        { date: "2026-09-16", kind: "did", type: "wash", status: "verified" },
        { date: "2026-09-12", kind: "said", verdict: "CLEAN", cause: "dust", loss_pct: 13 },
        { date: "2026-09-05", kind: "said", verdict: "WAIT", cause: "dust", wait_for: "dust_storm", loss_pct: 9 },
        { date: "2026-08-20", kind: "said", verdict: "OK", cause: "ok", loss_pct: 2 },
      ]} />
      {/* The Setup cards that came with the home switcher and deletion. Their buttons call the live API: look, don't press. */}
      <article className="tab">
        <Costs house={house} onSent={none} />
        <Size house={house} onSent={none} />
        <Size house={{ ...house, linked: true }} onSent={none} />
        <Size house={guest} onSent={none} />
        <Homes house={house} homes={{ all: [house, { house_id: "other", name: "Verma house" }], pick: none, add: none }} />
        <Family house={house} onChange={none} onGone={none} />
        <Family house={guest} onChange={none} onGone={none} />
        <DeleteAccount houses={[house]} onGone={none} />
        <DeleteAccount houses={[guest]} onGone={none} />
      </article>
      <Nav tab="roof" go={none} />
    </main>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(signedIn);
  const [houses, setHouses] = useState(null);
  const [homeId, setHomeId] = useState(() => kept("home"));  // the home last chosen on this phone
  const [error, setError] = useState("");
  const hash = useHash();

  const loadHouses = () => api("/me").then((me) => { keep("me", me.houses); setHouses(me.houses); return me.houses; }).catch((e) => {
    if (e.signedOut) return setAuthed(false);
    const last = e.offline && kept("me");  // no network: the homes as last seen, and Home shows its last verdict
    if (last) setHouses(last); else setError(e.message);
  });
  useEffect(() => { if (authed) loadHouses(); }, [authed]);
  const leave = () => { stopPush(); signOut(); setHouses(null); setAuthed(false); };
  const pick = (id) => { keep("home", id); setHomeId(id); go("roof"); };
  const added = async () => {  // show the home that was not in the list before
    const fresh = (await loadHouses())?.find((h) => !houses.some((old) => old.house_id === h.house_id));
    if (fresh) pick(fresh.house_id); else go("roof");
  };

  if (import.meta.env.DEV && hash === "#preview") return <Preview />;
  if (!authed) return <Auth onDone={() => setAuthed(true)} />;
  if (error) return <main className="page"><ErrorLine error={error} /><button className="secondary" onClick={() => { setError(""); loadHouses(); }}>{t("Try again")}</button></main>;
  if (!houses) return <main className="page"><p className="lede" aria-live="polite">{t("Loading…")}</p></main>;
  if (!houses.length) {
    return (
      <Setup onDone={loadHouses}>
        <button className="secondary" onClick={leave}>{t("Sign out")}</button>
        <DeleteAccount houses={houses} onGone={leave} />
      </Setup>
    );
  }
  if (hash === "#/add") return <Setup onDone={added} onBack={() => go("setup")} />;
  const house = houses.find((h) => h.house_id === homeId) || houses[0];  // the remembered one may be gone
  return <Home key={house.house_id} house={house} homes={{ all: houses, pick, add: () => go("add"), reload: loadHouses }} onSignOut={leave} />;
}
