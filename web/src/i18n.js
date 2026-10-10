// English or Hindi. The phone's language picks the first time; Setup (and the sign-in screen) can change it,
// and the choice stays on that phone. `?lang=hi` or `?lang=en` in the address forces one, for checking.
import { HI } from "./hi.js";

const KEY = "dhool.lang";
const asked = new URLSearchParams(location.search).get("lang");
const chosen = () => { try { return localStorage.getItem(KEY); } catch { return null; } };
export const lang = ["hi", "en"].includes(asked) ? asked
  : chosen() || (navigator.language?.startsWith("hi") ? "hi" : "en");
export const LOCALE = lang === "hi" ? "hi-IN" : "en-IN";  // dates; the digits stay 0-9 in both
document.documentElement.lang = lang;

/** Saves the choice and loads the app again, so text fixed when a file loads (headlines, labels) follows it. */
export function setLang(next) {
  try { localStorage.setItem(KEY, next); } catch { /* storage is off: the choice cannot be kept */ }
  if (!asked) return location.reload();
  const url = new URL(location.href);  // the address forced a language: drop that, or it would win again
  url.searchParams.delete("lang");
  location.replace(url);
}

/**
 * The text in the chosen language. Written in English where it is used; hi.js holds the Hindi for each.
 * `{name}` in the text is filled from `values`. A value may be an element (a link, bold text): the result
 * is then a list React can show, not a string.
 */
export function t(en, values) {
  const text = (lang === "hi" && HI[en]) || en;
  if (!values) return text;
  const parts = text.split(/\{(\w+)\}/).map((part, i) => (i % 2 ? values[part] : part));
  return parts.some((part) => typeof part === "object") ? parts : parts.join("");
}
