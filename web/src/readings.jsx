// The three ways a reading gets in: a screenshot the model reads, the inverter's API key, a typed number.
import { useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { API_URL } from "./config.js";
import { ErrorLine, Field, useAction } from "./form.jsx";
import { t } from "./i18n.js";
import { localDay } from "./store.js";
import { day } from "./visuals.jsx";

/** While the model reads a screenshot: how long it has been, and the way to type the number instead. */
function Reading({ since, onType }) {
  const [now, setNow] = useState(() => Date.now());
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

export function AddData({ house, onSent }) {
  const today = localDay();
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

      {/* The key reaches a whole inverter account: it is the owner's to give, and the API refuses anyone else. */}
      {house.role === "owner" && (
        <form className="card" onSubmit={send("/inverter", () => ({ api_key: key.trim() }))}>
          <h2>{t("Connect your inverter")}</h2>
          <p className="note">
            {t("Dhool then reads every day on its own. Copy your API key from the {app}. It holds simulated homes, not a real inverter brand.", { app: demoApp })}
          </p>
          <Field label={t("API key from your inverter app")} required autoComplete="off" autoCapitalize="none" spellCheck={false}
                 value={key} onChange={(e) => setKey(e.target.value)} />
          <button className="primary" disabled={state.busy}>{t("Connect")}</button>
        </form>
      )}

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
