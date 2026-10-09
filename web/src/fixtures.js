// Sample verdicts for looking at every state of the verdict screen without signing in: npm run dev, then /#preview.
const DAYS = 90;
function series(shape, rainDays = []) {
  return Array.from({ length: DAYS }, (_, i) => {
    const date = new Date(Date.UTC(2026, 5, 28 + i)).toISOString().slice(0, 10);
    const expected = +(13 + 2 * Math.sin(i / 9) + ((i * 7) % 5) * 0.3).toFixed(2);
    return { date, expected, actual: +(expected * shape(i) * (0.98 + ((i * 7) % 5) * 0.01)).toFixed(2), rain_mm: rainDays.includes(i) ? 18 : 0 };
  });
}
const week = (running) =>
  [[14.2, 0, 33], [13.8, 0, 34], [9.1, 0, 31], [6.4, 14, 28], [12.9, 0, 30], [14.4, 0, 32], [14.6, 0, 33]].map(
    ([possible_kwh, rain_mm, temp_max], i) => ({
      date: new Date(Date.UTC(2026, 8, 26 + i)).toISOString().slice(0, 10),
      possible_kwh, likely_kwh: +(possible_kwh * running).toFixed(1), rain_mm, temp_max,
    }));
const base = { as_of: "2026-09-25", expected_kwh: 13.6, confidence: "high", evidence: {}, forecast: week(0.99) };

export const FIXTURES = [
  { ...base, verdict: "INSPECT", cause: "fault", actual_kwh: 9.1, loss_pct: 33.1, loss_kwh_per_day: 4.5, loss_rs_per_week: 220,
    reason: "Output fell about 33% around 16 Aug and has stayed down for 40 days. Dust builds slowly and haze lifts, so this looks like a hardware fault, such as a failed string or new shading.",
    evidence: { step_date: "2026-08-16", drop_pct: 33.1, days_down: 40 }, forecast: week(0.67), series: series((i) => (i >= 49 ? 0.67 : 1), [20]) },
  { ...base, verdict: "CLEAN", cause: "dust", actual_kwh: 11.6, loss_pct: 15.0, loss_kwh_per_day: 2.0, loss_rs_per_week: 98,
    reason: "Output has slipped about 0.4% a day for 38 days since the panels were last cleaned, and is now 15% below this roof's normal. No rain is forecast in the next 7 days, so washing will pay off.",
    evidence: { rate_pct_per_day: 0.4, days_since_clean: 38 }, forecast: week(0.85), series: series((i) => 1 - 0.004 * (i < 52 ? i % 52 : i - 52), [52]) },
  { ...base, verdict: "WAIT", cause: "haze", confidence: "medium", actual_kwh: 11.2, loss_pct: 17.5, loss_kwh_per_day: 2.4, loss_rs_per_week: 118,
    reason: "The air is hazy (PM2.5 around 330) and output across the area fell about 18% in the last few days. Less sunlight is reaching the panels. Washing won't help, so save the water.",
    evidence: { pm25: 330, area_drop_pct: 17.5 }, forecast: week(0.83), series: series((i) => (i >= 84 ? 0.82 : 1), [30]) },
  { ...base, verdict: "WAIT", cause: "dust", confidence: "medium", actual_kwh: 12.4, loss_pct: 9.0, loss_kwh_per_day: 1.2, loss_rs_per_week: 59,
    reason: "Dust has cut output by about 9% over 24 days, but rain is forecast within 2 days and will wash the panels for free.",
    evidence: { rate_pct_per_day: 0.38, days_since_clean: 24 }, forecast: week(0.91), series: series((i) => 1 - 0.0038 * (i < 66 ? i % 66 : i - 66), [66]) },
  { ...base, verdict: "OK", cause: "ok", actual_kwh: 13.4, loss_pct: 1.2, loss_kwh_per_day: 0.2, loss_rs_per_week: 10,
    reason: "Your roof is producing what it should: within 1% of its normal.", series: series(() => 1, [12, 40, 71]) },
  { ...base, verdict: "WAIT", cause: "no_data", confidence: "low", actual_kwh: 12.9, loss_pct: 0, loss_kwh_per_day: 0, loss_rs_per_week: 0,
    reason: "Only 3 days of data so far. Dhool needs about two weeks to learn this roof's normal.", series: series(() => 1).slice(-3) },
];
