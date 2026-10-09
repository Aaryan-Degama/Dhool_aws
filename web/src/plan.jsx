// What a wash costs this household (the figure Dhool's wash-or-wait sums use), and the log of what Dhool
// advised and what the household did.
import { useEffect, useState } from "react";
import { api } from "./api.js";
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
      <h2>What does one wash cost you?</h2>
      <label className="field">
        <span>Cost of one wash (₹)</span>
        <input inputMode="numeric" required value={cost} onChange={(e) => setCost(e.target.value)} />
        <small>
          What you pay a cleaner, or about ₹50 for water and your time if you wash them yourself. Dhool tells you
          to wash only when the dust is costing more than this before the next rain or dust storm.
        </small>
      </label>
      {state.error && <p className="error" role="alert">{state.error}</p>}
      <button className="secondary" disabled={state.busy || cost.trim() === ""}>{state.busy ? "Saving…" : "Save"}</button>
    </form>
  );
}

const DID = { wash: "You washed the panels", visit: "The vendor visited" };
const CAME = { verified: "It worked.", not_recovered: "Output did not come back.", waiting: "Dhool is still measuring.", was_fine: "The roof was already at its normal." };

export function Log({ house, entries }) {
  const [log, setLog] = useState(entries);
  useEffect(() => { if (!entries) api(`/houses/${house.house_id}/history`).then((h) => setLog(h.log)).catch(() => setLog([])); }, [house?.house_id]);
  if (!log?.length) return null;
  return (
    <section className="card stack">
      <h2>What Dhool said, and what you did</h2>
      <ol className="log">
        {log.map((e) => (
          <li key={e.date + e.kind} className={`log-${e.kind}`}>
            <time dateTime={e.date}>{day(e.date)}</time>
            {e.kind === "said"
              ? <span>Dhool said: <strong>{headline(e)}</strong>{e.loss_pct >= 5 && e.verdict !== "OK" ? ` (${Math.round(e.loss_pct)}% down)` : ""}</span>
              : <span><strong>{DID[e.type]}.</strong> {CAME[e.status] || ""}</span>}
          </li>
        ))}
      </ol>
    </section>
  );
}
