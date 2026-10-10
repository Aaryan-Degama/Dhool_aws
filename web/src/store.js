// What Dhool keeps on the phone (sign-in, the chosen home, the last results for when the network is away),
// how old a reading is, and a month's days split into its weeks. Storage can be full, switched off or hold something broken: a read then gives null.
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

/**
 * A month ("YYYY-MM") as its weeks by date: 1 to 7, 8 to 14, 15 to 21, 22 to 28, and 29 to the end. `daily` is
 * {"YYYY-MM-DD": kWh} for the days that have a reading; a day without one is listed with kwh null and adds
 * nothing to its week. Nothing after `asOf`, the day of the last reading, is listed.
 */
export function weeksOf(month, daily, asOf) {
  const [year, number] = month.split("-").map(Number);
  const last = month === asOf.slice(0, 7) ? Number(asOf.slice(8)) : new Date(year, number, 0).getDate();
  const weeks = [];
  for (let from = 1; from <= last; from += 7) {
    const to = Math.min(from + 6, last);
    const days = Array.from({ length: to - from + 1 }, (_, i) => `${month}-${String(from + i).padStart(2, "0")}`)
      .map((date) => ({ date, kwh: daily[date] ?? null }));
    const read = days.filter((d) => d.kwh != null);
    weeks.push({ from, to, days, read: read.length, kwh: +read.reduce((sum, d) => sum + d.kwh, 0).toFixed(1) });
  }
  return weeks;
}

// How long to wait before each look for a fresh verdict after new data is sent: every 4 seconds for the first
// 20 (a run usually takes that long), then less and less often, giving up after about three minutes.
export const POLL_MS = [4000, 4000, 4000, 4000, 4000, 8000, 16000, 30000, 30000, 30000, 30000];

/** A typed figure as a number. Many keyboards put a comma where the decimal point goes: "5,5" is 5.5. */
export const toNumber = (typed) => Number(String(typed).trim().replace(",", "."));
