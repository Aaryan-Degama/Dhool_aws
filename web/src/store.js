// What Dhool keeps on the phone (sign-in, the chosen home, the last results for when the network is away),
// and how old a reading is. Storage can be full, switched off or hold something broken: a read then gives null.
const PREFIX = "dhool.";

export function kept(key) {
  try {
    return JSON.parse(localStorage.getItem(PREFIX + key));
  } catch {
    return null;
  }
}

export function keep(key, value) {
  try {
    if (value == null) localStorage.removeItem(PREFIX + key);
    else localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch { /* nothing kept: the app still works, only not offline */ }
}

/** On signing out: everything about the person and their homes goes; the language stays with the phone. */
export function forget() {
  try {
    Object.keys(localStorage).filter((k) => k.startsWith(PREFIX) && k !== PREFIX + "lang").forEach((k) => localStorage.removeItem(k));
  } catch { /* as above */ }
}

export const localDay = (at = new Date()) => at.toLocaleDateString("en-CA");  // YYYY-MM-DD on the phone's clock

/** Whole days from one YYYY-MM-DD date to another. */
export const daysSince = (date, today = localDay()) => Math.round((Date.parse(today) - Date.parse(date)) / 86400000);
export const STALE_DAYS = 3;  // from here on, the roof screen says the readings have stopped
