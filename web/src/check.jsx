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

// What the vendor's reply amounts to, and what to do next. The model (Laya) picks one; the homeowner can change it.
const REPLY = {
  visit_scheduled: ["They are coming", "Good. Once they have been, press “The vendor has visited” below and Dhool will check that the repair worked."],
  asking_details: ["They want something first", "Send what they asked for: usually a photo of the inverter screen, the model or error code, your address, or a yes to a visit charge. The inverter app's error code helps most."],
  refused: ["They won't help", "Ask again in writing and mention the maintenance that came with the installation. If they still refuse, your installer's company or your electricity distributor's rooftop solar cell is the next step."],
  unclear: ["No clear answer", "They have not said they will come. Ask for a day and a time."],
};

/** Paste the vendor's WhatsApp reply; Dhool says which of four things it is, and the next step. */
export function VendorReply({ house }) {
  const [text, setText] = useState("");
  const [state, setState] = useState({ busy: false, label: "", read: "", note: "" });
  const read = async (e) => {
    e.preventDefault();
    setState({ busy: true, label: "", read: "", note: "" });
    try {
      const { label } = await api(`/houses/${house.house_id}/vendor-reply`, { text });
      setState({ busy: false, label, read: label, note: "" });
    } catch (err) {  // the reader is down or starting: the four buttons do the same job by hand
      setState({ busy: false, label: "", read: "", note: err.message });
    }
  };
  return (
    <form className="vendor-reply" onSubmit={read}>
      <label className="field">
        <span>Got a reply from the vendor? Paste it here</span>
        <textarea rows="3" maxLength="1000" required value={text} onChange={(e) => setText(e.target.value)}
                  placeholder="Sir kal 11 baje aata hu" />
      </label>
      <button className="secondary" disabled={state.busy}>{state.busy ? "Reading…" : "What does it mean?"}</button>
      {state.note && <p className="note" role="status">{state.note}</p>}
      {(state.label || state.note) && (
        <>
          <div className="reply-kinds" role="group" aria-label="What the reply says">
            {Object.entries(REPLY).map(([id, [name]]) => (
              <button type="button" key={id} aria-pressed={state.label === id}
                      onClick={() => setState({ ...state, label: id })}>{name}</button>
            ))}
          </div>
          {state.label && (
            <p role="status">
              {state.read === state.label ? "Dhool reads this as: " : ""}<strong>{REPLY[state.label][0]}.</strong> {REPLY[state.label][1]}
              {state.read === state.label && <small> Not right? Pick another above.</small>}
            </p>
          )}
        </>
      )}
    </form>
  );
}
