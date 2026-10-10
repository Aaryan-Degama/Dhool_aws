// Signing in, adding or joining a home, and what belongs to the person rather than to a reading: the homes
// they are in, the family, alerts on this phone, and deleting the home or the account.
import { useEffect, useState } from "react";
import { api, confirmSignUp, deleteAccount, mySub, signIn, signUp } from "./api.js";
import { VAPID_PUBLIC_KEY } from "./config.js";
import { ErrorLine, Field, useAction } from "./form.jsx";
import { lang, setLang, t } from "./i18n.js";
import { keep, kept, localDay } from "./store.js";
import { day, PanelModel } from "./visuals.jsx";

export function Auth({ onDone }) {
  const [mode, setMode] = useState("in"); // in | up | code
  const [form, setForm] = useState({ email: "", password: "", code: "" });
  const [state, run] = useAction();
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = (e) => {
    e.preventDefault();
    run(async () => {
      if (mode === "up") {
        await signUp(form.email, form.password);
        return setMode("code");
      }
      if (mode === "code") await confirmSignUp(form.email, form.code);
      await signIn(form.email, form.password);
      onDone();
    });
  };

  return (
    <main className="page auth">
      <p className="brand">Dhool</p>
      <div className="hero"><PanelModel verdict={{ cause: "ok" }} /></div>
      <h1>{t("Is your solar actually working?")}</h1>
      <p className="lede">
        {t("Your inverter app shows a number. Dhool tells you what your roof should have made, and what to do when it falls short.")}
      </p>
      <form onSubmit={submit} className="card">
        {mode === "code" ? (
          <Field label={t("Code from your email")} inputMode="numeric" autoComplete="one-time-code" required
                 value={form.code} onChange={set("code")} hint={t("Sent to {email}", { email: form.email })} />
        ) : (
          <>
            <Field label={t("Email")} type="email" autoComplete="email" required value={form.email} onChange={set("email")} />
            <Field label={t("Password")} type="password" required minLength={8} value={form.password} onChange={set("password")}
                   autoComplete={mode === "up" ? "new-password" : "current-password"}
                   hint={mode === "up" ? t("At least 8 characters, with a capital letter, a number and a symbol") : undefined} />
          </>
        )}
        <ErrorLine error={state.error} />
        <button className="primary" disabled={state.busy}>
          {state.busy ? t("One moment…") : mode === "in" ? t("Sign in") : mode === "up" ? t("Create account") : t("Confirm and sign in")}
        </button>
        {mode !== "code" && (
          <button type="button" className="link" onClick={() => setMode(mode === "in" ? "up" : "in")}>
            {mode === "in" ? t("New here? Create an account") : t("Already have an account? Sign in")}
          </button>
        )}
      </form>
      {/* Setup, where the language is chosen, comes after signing in: offer the other one here too. */}
      {lang === "hi"
        ? <button className="link" lang="en" onClick={() => setLang("en")}>English</button>
        : <button className="link" lang="hi" onClick={() => setLang("hi")}>हिंदी</button>}
    </main>
  );
}

/** Add a home or join one. `onBack` is given when the person already has a home; `children` go under the forms. */
export function Setup({ onDone, onBack, children }) {
  const [form, setForm] = useState({ name: "", kw: "3", lat: "", lon: "", code: "" });
  const [state, run] = useAction();
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const [locationHelp, setLocationHelp] = useState(false);
  const locate = () =>
    navigator.geolocation.getCurrentPosition(
      (p) => setForm((f) => ({ ...f, lat: p.coords.latitude.toFixed(4), lon: p.coords.longitude.toFixed(4) })),
      () => setLocationHelp(true),
    );

  const create = (e) => {
    e.preventDefault();
    run(async () => {
      await api("/houses", { name: form.name, kw: Number(form.kw), lat: Number(form.lat), lon: Number(form.lon) });
      onDone();
    });
  };
  const join = (e) => {
    e.preventDefault();
    run(async () => {
      await api("/join", { code: form.code });
      onDone();
    });
  };

  return (
    <main className="page">
      <p className="brand">Dhool</p>
      {onBack && <button className="link" onClick={onBack}>{t("Back")}</button>}
      <h1>{t("Add your home")}</h1>
      <p className="lede">{t("Dhool needs to know where your roof is and how big the system is. That is all.")}</p>
      <form onSubmit={create} className="card">
        <Field label={t("Name for this home")} required maxLength={60} placeholder={t("Sharma house")} value={form.name} onChange={set("name")} />
        <label className="field">
          <span>{t("System size")}</span>
          <select value={form.kw} onChange={set("kw")}>
            {[1, 2, 3, 4, 5, 6, 8, 10].map((kw) => <option key={kw} value={kw}>{kw} kW</option>)}
          </select>
          <small>{t("It is on your installation papers and in your inverter app.")}</small>
        </label>
        <div className="row">
          <Field label={t("Latitude")} inputMode="decimal" required value={form.lat} onChange={set("lat")} />
          <Field label={t("Longitude")} inputMode="decimal" required value={form.lon} onChange={set("lon")} />
        </div>
        <button type="button" className="secondary" onClick={locate}>{t("Use my location")}</button>
        {locationHelp && <p className="note">{t("Location is off for this site. Type the two numbers in, or allow location and try again.")}</p>}
        <ErrorLine error={state.error} />
        <button className="primary" disabled={state.busy}>{state.busy ? t("Saving…") : t("Add home")}</button>
      </form>

      <form onSubmit={join} className="card">
        <h2>{t("Someone at home already uses Dhool?")}</h2>
        <Field label={t("Family code")} required maxLength={6} autoCapitalize="characters" className="code-input"
               value={form.code} onChange={set("code")} hint={t("Ask them for the six-letter code from their Dhool app.")} />
        <button className="secondary" disabled={state.busy}>{t("Join their home")}</button>
      </form>
      {children}
    </main>
  );
}

/** Which home is on screen, for someone in more than one, and the way to add another. */
export function Homes({ house, homes }) {
  return (
    <section className="card stack">
      <h2>{t("Your homes")}</h2>
      {homes.all.length > 1 && (
        <label className="field">
          <span>{t("Show this home")}</span>
          <select value={house.house_id} onChange={(e) => homes.pick(e.target.value)}>
            {homes.all.map((h) => <option key={h.house_id} value={h.house_id}>{h.name}</option>)}
          </select>
        </label>
      )}
      <button className="secondary" onClick={homes.add}>{t("Add another home")}</button>
    </section>
  );
}

/** The owner sees who is in the home, can remove them, and can delete the home. Anyone else can leave it. */
export function Family({ house, onChange, onGone }) {
  const [state, run] = useAction();
  const base = `/houses/${house.house_id}`;
  const gone = (path, then) => run(async () => { await api(path, undefined, "DELETE"); then(); });
  const remove = (sub) => () =>
    confirm(t("Remove this family member? They will no longer see this home.")) && gone(`${base}/members/${sub}`, onChange);
  const leave = () =>
    confirm(t("Leave {name}? You will no longer see its readings and advice.", { name: house.name })) && gone(`${base}/members/${mySub()}`, onGone);
  const erase = () =>
    confirm(t("Delete {name}? Its readings and screenshots are deleted for everyone in the family. This cannot be undone.", { name: house.name })) && gone(base, onGone);
  const joined = (m) => (m.joined_at
    ? t("Family member, joined {date}", { date: day(localDay(new Date(m.joined_at * 1000))) }) : t("Family member"));

  return (
    <section className="card stack">
      {house.role === "owner" ? (
        <>
          <h2>{t("Who is in this home")}</h2>
          <ul className="members">
            {(house.members || []).map((m) => (
              <li key={m.sub}>
                <span>{m.me ? t("You") : joined(m)}</span>
                {!m.me && <button className="link" disabled={state.busy} onClick={remove(m.sub)}>{t("Remove")}</button>}
              </li>
            ))}
          </ul>
          <button className="link error" disabled={state.busy} onClick={erase}>{t("Delete this home")}</button>
        </>
      ) : (
        <>
          <h2>{house.name}</h2>
          <p className="note">{t("You joined this home with a family code.")}</p>
          <button className="link error" disabled={state.busy} onClick={leave}>{t("Leave this home")}</button>
        </>
      )}
      <ErrorLine error={state.error} />
    </section>
  );
}

const keyBytes = (b64) => Uint8Array.from(atob(b64.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));

/** On signing out: this phone stops getting alerts. The push service then tells the server the address is gone. */
export const stopPush = () =>
  navigator.serviceWorker?.getRegistration().then((reg) => reg?.pushManager?.getSubscription()).then((sub) => sub?.unsubscribe()).catch(() => {});

/**
 * Alerts for this home on this phone. Shown only where they can work: a push key in config.js, a browser
 * with push, and the service worker running (it is not under `npm run dev`).
 */
export function Alerts({ house }) {
  const id = house.house_id;
  const [reg, setReg] = useState(null);
  const [on, setOn] = useState(false);
  const [state, run] = useAction();
  useEffect(() => {
    if (!VAPID_PUBLIC_KEY || !("PushManager" in window) || !("Notification" in window)) return;
    navigator.serviceWorker?.getRegistration().then(async (found) => {
      if (!found) return;
      setReg(found);
      setOn(Boolean(await found.pushManager.getSubscription()) && (kept("push") || []).includes(id));
    }).catch(() => {});
  }, [id]);
  if (!reg) return null;

  // ponytail: the phone remembers which homes it switched on ("push"); the server is not asked, and the
  // language sent is the one in use at that moment. Add a GET of the subscription if the two drift apart.
  const turn = (want) => () => run(async () => {
    const others = (kept("push") || []).filter((h) => h !== id);
    if (want) {
      if (await Notification.requestPermission() !== "granted") {
        throw new Error(t("Notifications are blocked for this site. Allow them in your browser's settings, then try again."));
      }
      const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(VAPID_PUBLIC_KEY) });
      await api(`/houses/${id}/push`, { subscription: sub.toJSON(), lang });
    } else {
      const sub = await reg.pushManager.getSubscription();
      if (sub) await api(`/houses/${id}/push`, { endpoint: sub.endpoint }, "DELETE");
      if (sub && !others.length) await sub.unsubscribe();  // one address serves every home on this phone
    }
    keep("push", want ? [...others, id] : others);
    setOn(want);
  });

  return (
    <section className="card stack">
      <h2>{t("Alerts on this phone")}</h2>
      <p className="note">{t("Dhool will tell you when it is time to call the vendor, when it is time to wash, and when readings have stopped.")}</p>
      <div className="reply-kinds" role="group" aria-label={t("Alerts")}>
        <button type="button" aria-pressed={on} disabled={state.busy} onClick={turn(true)}>{t("On")}</button>
        <button type="button" aria-pressed={!on} disabled={state.busy} onClick={turn(false)}>{t("Off")}</button>
      </div>
      <ErrorLine error={state.error} />
    </section>
  );
}

/** Deleting the sign-in. An owner deletes the home first; anyone else leaves their homes on the way out. */
export function DeleteAccount({ houses, onGone }) {
  const [state, run] = useAction();
  const owned = houses.filter((h) => h.role === "owner").map((h) => h.name);
  const erase = () => confirm(t("Delete your Dhool account? This cannot be undone.")) && run(async () => {
    for (const h of houses) await api(`/houses/${h.house_id}/members/${mySub()}`, undefined, "DELETE");
    await deleteAccount();
    onGone();
  });
  return (
    <section className="card stack">
      <h2>{t("Delete my account")}</h2>
      {owned.length ? (
        <p className="note">{t("You are the owner of {names}. Delete the home first, then your account.", { names: owned.join(", ") })}</p>
      ) : (
        <>
          <p className="note">{t("This removes your sign-in for good. You leave every home you have joined; the homes and their readings stay for the others.")}</p>
          <button className="link error" disabled={state.busy} onClick={erase}>{state.busy ? t("One moment…") : t("Delete my account")}</button>
        </>
      )}
      <ErrorLine error={state.error} />
    </section>
  );
}
