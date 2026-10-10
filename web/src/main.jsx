import { Component } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { t } from "./i18n.js";
import { setSky, skyByClock } from "./sky.js";
import "./styles.css";

/** A screen that breaks while it is being drawn lands here, in place of a blank page. */
class ErrorBoundary extends Component {
  state = { broken: false };
  static getDerivedStateFromError() { return { broken: true }; }
  render() {
    if (!this.state.broken) return this.props.children;
    return (
      <main className="page">
        <h1>{t("Something went wrong")}</h1>
        <p className="lede">{t("Dhool could not show this screen. Your readings are safe. Open the app again.")}</p>
        <button className="primary" onClick={() => location.reload()}>{t("Open again")}</button>
      </main>
    );
  }
}

setSky(skyByClock());  // the weather over the roof takes over once a home is loaded (see Home in App.jsx)
createRoot(document.getElementById("root")).render(<ErrorBoundary><App /></ErrorBoundary>);
// The offline shell and alerts (public/sw.js). Not under `npm run dev`, where it would serve stale files.
if (import.meta.env.PROD) navigator.serviceWorker?.register("/sw.js").catch(() => {});
