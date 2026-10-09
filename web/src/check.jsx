// The wash or vendor visit the homeowner reported, and whether output came back afterwards.
import { useState } from "react";
import { api } from "./api.js";
import { day } from "./visuals.jsx";
import "./check.css";

const signed = (n) => `${n > 0 ? "+" : ""}${Math.round(n)}%`;
const TITLE = {
  wash: { waiting: "Checking your wash", verified: "Washing worked", not_recovered: "Washing did not help", was_fine: "Nothing to win back" },
  visit: { waiting: "Checking the repair", verified: "The repair worked", not_recovered: "Still not fixed", was_fine: "Nothing to win back" },
};

function line(c) {
  const did = c.type === "wash" ? "You washed the panels" : "The vendor visited";
  if (c.status === "waiting") {
    return `${did} on ${day(c.date)}. Dhool compares the week before with three clear days after: ${c.days_after} so far.`;
  }
  if (c.status === "was_fine") return `${did} on ${day(c.date)}, but the roof was already at its normal, so there was nothing to gain.`;
  return `${did} on ${day(c.date)}. Getting back to this roof's normal needed ${signed(c.predicted_pct)}; the days after show ${signed(c.observed_pct)}.`;
}

/** What came of the last wash or visit. `onSent` is given when the homeowner may take the report back. */
export function CheckCard({ check: c, house, onSent }) {
  const [busy, setBusy] = useState(false);
  const undo = async () => {
    setBusy(true);
    await api(`/houses/${house.house_id}/actions`, { date: c.date, remove: true }).then(onSent).catch(() => setBusy(false));
  };
  return (
    <section className={`card check check-${c.status}`} aria-label="Before and after">
      <h2>{TITLE[c.type][c.status]}</h2>
      {c.observed_pct !== null && c.status !== "was_fine" && (
        <dl className="check-figures">
          <div><dt>Needed</dt><dd>{signed(c.predicted_pct)}</dd></div>
          <div><dt>Came back</dt><dd>{signed(c.observed_pct)}</dd></div>
        </dl>
      )}
      <p className="note">{line(c)}</p>
      {onSent && <button className="link" disabled={busy} onClick={undo}>Recorded by mistake? Remove it</button>}
    </section>
  );
}

/** "I washed the panels" or "The vendor has visited": the date, then Dhool measures before against after. */
export function ReportAction({ house, type, onSent }) {
  const today = new Date().toLocaleDateString("en-CA");
  const [date, setDate] = useState("");  // "" until the button is pressed
  const [state, setState] = useState({ busy: false, error: "" });
  const save = async (e) => {
    e.preventDefault();
    setState({ busy: true, error: "" });
    try {
      await api(`/houses/${house.house_id}/actions`, { type, date });
      onSent();
    } catch (err) {
      setState({ busy: false, error: err.message });
    }
  };
  if (!date) {
    return (
      <button className="secondary" onClick={() => setDate(today)}>
        {type === "wash" ? "I washed the panels" : "The vendor has visited"}
      </button>
    );
  }
  return (
    <form className="report" onSubmit={save}>
      <label className="field">
        <span>{type === "wash" ? "When did you wash them?" : "When did the vendor come?"}</span>
        <input type="date" required max={today} value={date} onChange={(e) => setDate(e.target.value)} />
        <small>Dhool will compare the week before with the clear days after, and tell you whether it worked.</small>
      </label>
      {state.error && <p className="error" role="alert">{state.error}</p>}
      <button className="secondary" disabled={state.busy}>{state.busy ? "Saving…" : "Save and check"}</button>
    </form>
  );
}
