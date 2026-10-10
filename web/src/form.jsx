// The pieces every form in the app is built from.
import { useState } from "react";
import { t } from "./i18n.js";

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
