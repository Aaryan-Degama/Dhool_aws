// The sky behind the app follows the weather and the time over the roof: the clock until the weather is
// known, then Open-Meteo's current conditions (free, no key), refreshed while the app is open.
export const SKIES = ["day", "cloud", "rain", "storm", "snow", "sand", "night"];

/** Current conditions -> { sky, dark }. `dark` is night-time: cloud, snow and sand each have a dark version. */
export function skyFor({ code, isDay, dust = 0, gusts = 0, visibility = Infinity }) {
  const dark = !isDay;
  const rain = (code >= 51 && code <= 67) || (code >= 80 && code <= 82);
  const snow = (code >= 71 && code <= 77) || code === 85 || code === 86;
  // A sandstorm is wind and lost visibility, not just dust in the air: Delhi's air carries 300 µg/m³ of
  // dust on a calm, clear night. All three must hold.
  if (dust >= 150 && gusts >= 40 && visibility <= 5000) return { sky: "sand", dark };
  if (snow) return { sky: "snow", dark };
  // Thunder, heavy rain, or any rain after dark: the dark, wet sky.
  if (code >= 95 || (rain && (dark || [65, 67, 82].includes(code)))) return { sky: "storm", dark };
  if (rain) return { sky: "rain", dark };
  if ([3, 45, 48].includes(code)) return { sky: "cloud", dark };
  return { sky: dark ? "night" : "day", dark };
}

export function skyByClock(hour = new Date().getHours()) {
  const dark = hour < 6 || hour >= 19;
  return { sky: dark ? "night" : "day", dark };
}

/** `?sky=snow&dark=1` in the address forces a sky, for demos and screenshots. */
export function setSky({ sky, dark }) {
  const forced = new URLSearchParams(location.search);
  const root = document.documentElement;
  if (SKIES.includes(forced.get("sky"))) [sky, dark] = [forced.get("sky"), forced.has("dark")];
  root.dataset.sky = sky;
  root.toggleAttribute("data-dark", dark);
  // The browser's own bar takes the colour at the top of the sky.
  const top = getComputedStyle(root).getPropertyValue("--sky-top").trim();
  if (top) document.querySelector('meta[name="theme-color"]')?.setAttribute("content", top);
}

export async function skyOver(lat, lon) {
  // Two decimals is about a kilometre: enough for weather, and not the exact roof.
  const at = `latitude=${Number(lat).toFixed(2)}&longitude=${Number(lon).toFixed(2)}`;
  const get = (url) => fetch(url).then((r) => (r.ok ? r.json() : Promise.reject(new Error(url))));
  const [weather, air] = await Promise.all([
    get(`https://api.open-meteo.com/v1/forecast?${at}&current=weather_code,is_day,wind_gusts_10m,visibility`),
    get(`https://air-quality-api.open-meteo.com/v1/air-quality?${at}&current=dust`).catch(() => null),
  ]);
  const now = weather.current;
  return skyFor({ code: now.weather_code, isDay: now.is_day === 1, gusts: now.wind_gusts_10m,
                  visibility: now.visibility, dust: air?.current?.dust ?? 0 });
}
