// The sky behind the app follows the weather over the roof: the clock until the weather is known,
// then Open-Meteo's current conditions (free, no key).
export const SKIES = ["day", "cloud", "rain", "storm", "snow", "sand", "night"];
const SAND_DUST = 200;  // µg/m³ of dust in the air before it counts as a sandstorm
const NIGHT_BAR = { night: "#14163A", storm: "#252F44" };

/** WMO weather code, day or night, and dust in the air -> which sky to draw. */
export function skyFor({ code, isDay, dust = 0 }) {
  const rain = (code >= 51 && code <= 67) || (code >= 80 && code <= 82);
  const snow = (code >= 71 && code <= 77) || code === 85 || code === 86;
  if (dust >= SAND_DUST) return "sand";
  if (snow) return "snow";
  // Thunder, heavy rain, or rain after dark: the dark, wet sky.
  if (code >= 95 || (rain && (!isDay || [65, 67, 82].includes(code)))) return "storm";
  if (rain) return "rain";
  if (!isDay) return "night";
  return [3, 45, 48].includes(code) ? "cloud" : "day";
}

export function skyByClock(hour = new Date().getHours()) {
  return hour < 6 || hour >= 19 ? "night" : "day";
}

/** `?sky=rain` (or any other sky) in the address forces it, for demos and screenshots. */
export function setSky(sky) {
  const forced = new URLSearchParams(location.search).get("sky");
  const shown = SKIES.includes(forced) ? forced : sky;
  document.documentElement.dataset.sky = shown;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", NIGHT_BAR[shown] || "#1B62C4");
}

export async function skyOver(lat, lon) {
  // Two decimals is about a kilometre: enough for weather, and not the exact roof.
  const at = `latitude=${Number(lat).toFixed(2)}&longitude=${Number(lon).toFixed(2)}`;
  const get = (url) => fetch(url).then((r) => (r.ok ? r.json() : Promise.reject(new Error(url))));
  const [weather, air] = await Promise.all([
    get(`https://api.open-meteo.com/v1/forecast?${at}&current=weather_code,is_day`),
    get(`https://air-quality-api.open-meteo.com/v1/air-quality?${at}&current=dust`).catch(() => null),
  ]);
  return skyFor({ code: weather.current.weather_code, isDay: weather.current.is_day === 1, dust: air?.current?.dust ?? 0 });
}
