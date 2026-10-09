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
    reason_hi: "16 अगस्त के आसपास बिजली उत्पादन लगभग 33% गिरा और 40 दिन से कम ही है। धूल धीरे-धीरे जमती है और धुंध छँट जाती है, इसलिए यह हार्डवेयर की ख़राबी लगती है, जैसे कोई स्ट्रिंग बंद होना या पैनलों पर नई छाया पड़ना।",
    evidence: { step_date: "2026-08-16", drop_pct: 33.1, days_down: 40 }, forecast: week(0.67), series: series((i) => (i >= 49 ? 0.67 : 1), [20]) },
  { ...base, verdict: "CLEAN", cause: "dust", actual_kwh: 11.6, loss_pct: 15.0, loss_kwh_per_day: 2.0, loss_rs_per_week: 98,
    reason: "Output has slipped about 0.4% a day for 38 days since the panels were last cleaned, and is now 15% below this roof's normal. No rain is forecast in the next 7 days, so washing will pay off.",
    reason_hi: "पिछली सफ़ाई के बाद 38 दिन से बिजली उत्पादन रोज़ लगभग 0.4% घट रहा है और अब इस छत के सामान्य स्तर से 15% कम है। अगले 7 दिनों में बारिश का अनुमान नहीं है, इसलिए धोना फ़ायदे का रहेगा।",
    evidence: { rate_pct_per_day: 0.4, days_since_clean: 38 }, forecast: week(0.85), series: series((i) => 1 - 0.004 * (i < 52 ? i % 52 : i - 52), [52]) },
  { ...base, verdict: "WAIT", cause: "haze", confidence: "medium", actual_kwh: 11.2, loss_pct: 17.5, loss_kwh_per_day: 2.4, loss_rs_per_week: 118,
    reason: "The air is hazy (PM2.5 around 330) and output across the area fell about 18% in the last few days. Less sunlight is reaching the panels. Washing won't help, so save the water.",
    reason_hi: "हवा में धुंध है (PM2.5 लगभग 330) और पिछले कुछ दिनों में पूरे इलाक़े का बिजली उत्पादन लगभग 18% गिरा है। पैनलों तक धूप कम पहुँच रही है। धोने से फ़ायदा नहीं होगा, इसलिए पानी बचाइए।",
    evidence: { pm25: 330, area_drop_pct: 17.5 }, forecast: week(0.83), series: series((i) => (i >= 84 ? 0.82 : 1), [30]) },
  { ...base, verdict: "WAIT", cause: "dust", confidence: "medium", actual_kwh: 12.4, loss_pct: 9.0, loss_kwh_per_day: 1.2, loss_rs_per_week: 59,
    reason: "Dust has cut output by about 9% over 24 days, but rain is forecast within 2 days and will wash the panels for free.",
    reason_hi: "24 दिनों में धूल से बिजली उत्पादन लगभग 9% घटा है, लेकिन 2 दिन के अंदर बारिश का अनुमान है, जो पैनल मुफ़्त में धो देगी।",
    evidence: { rate_pct_per_day: 0.38, days_since_clean: 24 }, forecast: week(0.91), series: series((i) => 1 - 0.0038 * (i < 66 ? i % 66 : i - 66), [66]) },
  { ...base, verdict: "WAIT", cause: "dust", confidence: "medium", actual_kwh: 12.4, loss_pct: 9.0, loss_kwh_per_day: 1.2, loss_rs_per_week: 59,
    reason: "Dust has cut output by about 9% over 24 days, but a dust storm is forecast on Monday and would dirty the panels again. Wash after it, not before: washing today would save only about ₹17.",
    reason_hi: "24 दिनों में धूल से बिजली उत्पादन लगभग 9% घटा है, लेकिन सोमवार को आँधी का अनुमान है, जो पैनल फिर गंदे कर देगी। आँधी के बाद धोइए, पहले नहीं: आज धोने से सिर्फ़ लगभग ₹17 बचेंगे।",
    evidence: { rate_pct_per_day: 0.38, days_since_clean: 24, wait_for: "dust_storm", saving_rs: 17, wash_cost_rs: 50 }, forecast: week(0.91), series: series((i) => 1 - 0.0038 * (i < 66 ? i % 66 : i - 66), [66]) },
  { ...base, verdict: "WAIT", cause: "dust", confidence: "medium", actual_kwh: 4.2, expected_kwh: 4.5, loss_pct: 6.0, loss_kwh_per_day: 0.3, loss_rs_per_week: 13,
    reason: "Dust is costing about ₹2 a day, 6% of this roof's output. A wash costs about ₹50 in water and effort, so it is not worth it yet. At this rate it will be in about 9 days.",
    reason_hi: "धूल से रोज़ लगभग ₹2 का नुक़सान हो रहा है, यानी इस छत के उत्पादन का 6%। पानी और मेहनत मिलाकर एक धुलाई लगभग ₹50 की है, इसलिए अभी धोना फ़ायदे का नहीं है। इसी रफ़्तार से लगभग 9 दिन में धोना फ़ायदे का हो जाएगा।",
    evidence: { rate_pct_per_day: 0.25, days_since_clean: 24, wait_for: "not_worth_it", saving_rs: 41, wash_cost_rs: 50, worth_it_in_days: 9 }, forecast: week(0.94), series: series((i) => 1 - 0.0025 * (i < 66 ? i % 66 : i - 66), [66]) },
  { ...base, verdict: "OK", cause: "ok", actual_kwh: 13.4, loss_pct: 1.2, loss_kwh_per_day: 0.2, loss_rs_per_week: 10,
    reason: "Your roof is producing what it should: within 1% of its normal.", reason_hi: "आपकी छत उतनी ही बिजली बना रही है जितनी बनानी चाहिए: सामान्य स्तर से 1% के अंदर।", series: series(() => 1, [12, 40, 71]) },
  { ...base, verdict: "OK", cause: "ok", actual_kwh: 13.5, loss_pct: 0.8, loss_kwh_per_day: 0.1, loss_rs_per_week: 5,
    reason: "Your roof is producing what it should: within 1% of its normal.", reason_hi: "आपकी छत उतनी ही बिजली बना रही है जितनी बनानी चाहिए: सामान्य स्तर से 1% के अंदर।", series: series((i) => (i < 80 ? 1 - 0.0015 * i : 1)),
    check: { type: "wash", date: "2026-09-16", status: "verified", predicted_pct: 12.8, observed_pct: 12.1, days_after: 7 } },
  { ...base, verdict: "INSPECT", cause: "not_dust", confidence: "medium", actual_kwh: 11.9, loss_pct: 12.4, loss_kwh_per_day: 1.7, loss_rs_per_week: 83,
    reason: "You washed the panels on 16 Sept, but output is still about 12% below this roof's normal. Dust was not the cause, so have the system inspected.",
    reason_hi: "आपने 16 सितंबर को पैनल धोए, लेकिन बिजली उत्पादन अब भी इस छत के सामान्य स्तर से लगभग 12% कम है। कारण धूल नहीं थी, इसलिए सिस्टम की जाँच करवाइए।",
    forecast: week(0.88), series: series((i) => 1 - 0.0014 * i),
    check: { type: "wash", date: "2026-09-16", status: "not_recovered", predicted_pct: 13.6, observed_pct: 0.9, days_after: 7 } },
  { ...base, verdict: "WAIT", cause: "no_data", confidence: "low", actual_kwh: 12.9, loss_pct: 0, loss_kwh_per_day: 0, loss_rs_per_week: 0,
    reason: "Only 3 days of data so far. Dhool needs about two weeks to learn this roof's normal.",
    reason_hi: "अभी सिर्फ़ 3 दिन का डेटा है। इस छत का सामान्य स्तर समझने के लिए Dhool को लगभग दो हफ़्ते चाहिए।", series: series(() => 1).slice(-3) },
];
