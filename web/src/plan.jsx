// What a wash costs this household (the figure Dhool's wash-or-wait sums use), and the log of what Dhool
// advised and what the household did.
import { useEffect, useState } from "react";
import { api } from "./api.js";
import { t } from "./i18n.js";
import { day } from "./visuals.jsx";
import { headline } from "./words.js";
import "./check.css";

export function WashCost({ house, onSent }) {
  const [cost, setCost] = useState("");
  const [state, setState] = useState({ busy: false, error: "" });
  useEffect(() => { api(`/houses/${house.house_id}`).then((h) => setCost(String(h.wash_cost_rs))).catch(() => {}); }, [house.house_id]);
  const save = async (e) => {
    e.preventDefault();
    setState({ busy: true, error: "" });
    try {
      await api(`/houses/${house.house_id}/settings`, { wash_cost_rs: Number(cost) });
      onSent();
    } catch (err) {
      setState({ busy: false, error: err.message });
    }
  };
  return (
    <form className="card" onSubmit={save}>
      <h2>{t("What does one wash cost you?")}</h2>
      <label className="field">
        <span>{t("Cost of one wash (₹)")}</span>
        <input inputMode="numeric" required value={cost} onChange={(e) => setCost(e.target.value)} />
        <small>{t("What you pay a cleaner, or about ₹50 for water and your time if you wash them yourself. Dhool tells you to wash only when the dust is costing more than this before the next rain or dust storm.")}</small>
      </label>
      {state.error && <p className="error" role="alert">{t(state.error)}</p>}
      <button className="secondary" disabled={state.busy || cost.trim() === ""}>{state.busy ? t("Saving…") : t("Save")}</button>
    </form>
  );
}

const DID = { wash: t("You washed the panels"), visit: t("The vendor visited") };
const CAME = { verified: t("It worked."), not_recovered: t("Output did not come back."), waiting: t("Dhool is still measuring."), was_fine: t("The roof was already at its normal.") };

export function Log({ house, entries }) {
  const [log, setLog] = useState(entries);
  useEffect(() => { if (!entries) api(`/houses/${house.house_id}/history`).then((h) => setLog(h.log)).catch(() => setLog([])); }, [house?.house_id]);
  if (!log?.length) return null;
  return (
    <section className="card stack">
      <h2>{t("What Dhool said, and what you did")}</h2>
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
