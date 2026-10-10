// The pieces every form in the app is built from.
import { useState } from "react";
import { t } from "./i18n.js";
import { toNumber } from "./store.js";

export function useAction() {
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

/** A typed system size as a number of kW, or an error that says what it has to be (the server's own limits). */
export function kwOf(typed) {
  const kw = toNumber(typed);
  if (!(kw >= 0.1 && kw <= 100)) throw new Error(t("Type the system size in kW: a number from 0.1 to 100."));
  return kw;
}

export const ErrorLine = ({ error }) => (error ? <p className="error" role="alert">{t(error)}</p> : null);

export function Field({ label, hint, ...input }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input {...input} />
      {hint && <small>{hint}</small>}
    </label>
  );
}
