# DESIGN.md — how Dhool looks and speaks

Tokens live in `web/src/styles.css`; change them there, not in components.

## Idea
Everything on screen comes from the roof: panel glass, electric current, dust, wash water. The one loud
element is **the panel drawing**, which shows the cause instead of naming it: a dead string goes dark,
dust lies on the glass, haze veils it, a healthy panel is fully lit. Everything else stays quiet.

## Colour
Dark and quiet, in the manner of a car app: the panel is the product shot, everything else recedes.

| Token | Hex | Used for |
|---|---|---|
| `--paper` / `--card` | `#0A0D12` / `#131821` | Page; raised tiles (figures, forecast) |
| `--ink` / `--muted` | `#EEF2F7` / `#93A1B5` | Text |
| `--panel` / `--cell` | `#0C1A2E` / `#1B3F6E` | Panel frame and cell faces |
| `--current` | `#FFC21A` | Busbars (electricity), likely-output bars, the main button (dark text on it) |
| `--dhool` / `--dhool-ink` | `#B9A27F` / `#D8C39A` | Dust; WAIT |
| `--wash` | `#4DB3F0` | Water: CLEAN, rain, links |
| `--fault` | `#FF6B57` | INSPECT, errors |
| `--good` | `#4ADE80` | OK |

A verdict is never colour alone: the headline says what to do and the panel shows why.

## Type
One family, **Anek Devanagari** (SIL OFL, Google Fonts): it covers Hindi and English and has a width axis.
Headlines are heavy and wide (800, 112%), small labels slightly narrow (92%), body regular. Numbers are
tabular. Sentence case everywhere; no all-caps labels.

## Voice
- Say what to do, not the system's label: "Call your vendor", "Wash the panels", "Wait for the rain",
  "Don't wash. It's haze.", "Your solar is working".
- Say "units", the word on an Indian electricity bill, with kWh only where the inverter app uses it.
- Numbers come from the analysis, never invented. Estimates are stated as estimates ("about ₹165 a week").
- Errors say what happened and what to do next. No apologies, no jokes.
- The vendor message is a polite request, not a legal claim.

## Layout
Phone first: one column, left-aligned, 30rem at most, 16px gutters, touch targets 48px or more.
Verdict screen order: panel, what to do, why in one sentence, two figures (should have made / made),
money lost, how sure, the action, the next 7 days (weather, and likely against possible units), then the chart. One motion only: current reaches the panel string by
string when a verdict arrives (off under reduced motion).

## Not done yet
Hindi strings, screenshot upload, the "I washed them" verification step, a service worker for offline use,
a home switcher for people in two homes.
