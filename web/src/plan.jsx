// What a wash and a unit of electricity cost this household (the figures Dhool's wash-or-wait and money-lost
// sums use), the system's size, and the log of what Dhool advised and what the household did.
import { useEffect, useState } from "react";
import { api } from "./api.js";
import { TARIFF_RS } from "./config.js";
import { ErrorLine, Field, kwOf, useAction } from "./form.jsx";
import { t } from "./i18n.js";
import { toNumber } from "./store.js";
import { day } from "./visuals.jsx";
import { headline } from "./words.js";
import "./check.css";

/** The two rupee figures the advice rests on. `house` carries the saved ones once its details have loaded. */
export function Costs({ house, onSent }) {
  const [cost, setCost] = useState(String(house.wash_cost_rs ?? ""));
  const [tariff, setTariff] = useState(String(house.tariff_rs ?? TARIFF_RS));
  const [state, setState] = useState({ busy: false, error: "" });
  const save = async (e) => {
    e.preventDefault();
    setState({ busy: true, error: "" });
    try {
      await api(`/houses/${house.house_id}/settings`, { wash_cost_rs: toNumber(cost), tariff_rs: toNumber(tariff) });
      onSent();
    } catch (err) {
      setState({ busy: false, error: err.message });
    }
  };
  return (
    <form className="card" onSubmit={save}>
      <h2>{t("Costs")}</h2>
      <label className="field">
        <span>{t("Cost of one wash (₹)")}</span>
        <input inputMode="numeric" required value={cost} onChange={(e) => setCost(e.target.value)} />
        <small>{t("What you pay a cleaner, or about ₹50 for water and your time if you wash them yourself. Dhool tells you to wash only when the dust is costing more than this before the next rain or dust storm.")}</small>
      </label>
      <label className="field">
        <span>{t("Electricity rate (₹ per unit)")}</span>
        <input type="number" min="1" max="30" step="any" inputMode="decimal" required value={tariff} onChange={(e) => setTariff(e.target.value)} />
        <small>{t("It is on your electricity bill. Dhool uses it to work out the money lost.")}</small>
      </label>
      {state.error && <p className="error" role="alert">{t(state.error)}</p>}
      <button className="secondary" disabled={state.busy || cost.trim() === ""}>{state.busy ? t("Saving…") : t("Save")}</button>
    </form>
  );
}

/**
 * The system's size in kW: what the roof should make, and the most a day's reading can be, both rest on it.
 * The owner changes it. A linked home's is the inverter's (written again each time it is linked), so it is
 * only shown. Nothing until the home's details have loaded.
 */
export function Size({ house, onSent }) {
  const [kw, setKw] = useState(String(house.kw ?? ""));
  const [state, run] = useAction();
  if (house.kw == null) return null;
  const fixed = house.linked ? t("Taken from your inverter when it was linked.")
    : house.role !== "owner" ? t("Only the owner of this home can change it.") : "";
  if (fixed) {
    return (
      <section className="card stack">
        <h2>{t("System size")}</h2>
        <p><strong>{t("{kw} kW", { kw: house.kw })}</strong></p>
        <p className="note">{fixed}</p>
      </section>
    );
  }
  const save = (e) => {
    e.preventDefault();
    run(async () => {
      await api(`/houses/${house.house_id}/settings`, { kw: kwOf(kw) });
      onSent();
    });
  };
  return (
    <form className="card" onSubmit={save}>
      <h2>{t("System size")}</h2>
      <Field label={t("System size (kW)")} inputMode="decimal" required value={kw} onChange={(e) => setKw(e.target.value)}
             hint={t("It is on your installation papers and in your inverter app. Dhool works out what your roof should make from it.")} />
      <ErrorLine error={state.error} />
      <button className="secondary" disabled={state.busy}>{state.busy ? t("Saving…") : t("Save")}</button>
    </form>
  );
}

const DID = { wash: t("You washed the panels"), visit: t("The vendor visited") };
const CAME = { verified: t("It worked."), not_recovered: t("Output did not come back."), waiting: t("Dhool is still measuring."), was_fine: t("The roof was already at its normal.") };

export function Log({ house, entries }) {
  const [log, setLog] = useState(entries);
  useEffect(() => { if (!entries) api(`/houses/${house.house_id}/history`).then((h) => setLog(h.log)).catch(() => setLog([])); }, [house?.house_id, entries]);
  if (!log?.length) return null;
  return (
    <section className="card stack">
      <h2>{t("Advice log")}</h2>
      <ol className="log">
        {log.map((e) => (
          <li key={e.date + e.kind} className={`log-${e.kind}`}>
            <time dateTime={e.date}>{day(e.date)}</time>
            {e.kind === "said"
              ? <span>{t("Dhool said: {what}", { what: <strong key="what">{headline(e)}</strong> })}{e.loss_pct >= 5 && e.verdict !== "OK" ? t(" ({pct}% down)", { pct: Math.round(e.loss_pct) }) : ""}</span>
              : <span><strong>{t("{name}.", { name: DID[e.type] })}</strong> {CAME[e.status] || ""}</span>}
          </li>
        ))}
      </ol>
    </section>
  );
}

/**
 * The household's washes and vendor visits, newest first (the server sends the newest 20), each with how it
 * came out where Dhool measured it. Nothing while it loads or when it cannot be fetched: "none yet" would be untrue.
 */
export function Actions({ house, entries }) {
  const [list, setList] = useState(entries);
  useEffect(() => { if (!entries) api(`/houses/${house.house_id}/history`).then((h) => setList(h.actions)).catch(() => {}); }, [house?.house_id, entries]);
  if (!list) return null;
  return (
    <section className="card stack">
      <h2>{t("Washes and visits")}</h2>
      {list.length ? (
        <ol className="log">
          {list.map((e) => (
            <li key={e.date} className="log-did">
              <time dateTime={e.date}>{day(e.date)}</time>
              <span><strong>{t("{name}.", { name: DID[e.type] })}</strong> {CAME[e.status] || ""}</span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="note">{t("Nothing reported yet. When Dhool says to wash or to call the vendor, a button under that advice on the Roof tab lets you say you have done it.")}</p>
      )}
    </section>
  );
}
