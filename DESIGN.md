# DESIGN.md — how Dhool looks and speaks

Set on Oct 8, reworked on Oct 8 into a premium, car-app style at the owner's request (reference: the
Tesla app). Tokens live in `web/src/styles.css`; change them there, not in components.

## Idea
The roof is the product shot. The one loud element is **the roof model**: a rooftop array drawn in
perspective, standing in a pool of light, which shows the cause instead of naming it. A dead string goes
dark, dust lies on the glass, haze veils it, a healthy array is lit with a strip of current along its
lower rail. Everything else is graphite and quiet.

## The roof model (`PanelModel` in `web/src/visuals.jsx`)
- Six columns by two rows of modules on a tilted frame: three strings of two columns each.
- It is projected from 3D points in code, so it can be turned by dragging sideways. No 3D library.
- Each module has an aluminium rim, half-cut cells with pale gaps, fine busbar wires, and a soft
  reflection that slides across the glass as the model turns.
- States: `fault` darkens whole columns (the share that dropped) with a dashed red rim; `dust` adds a
  khaki film and speckles; `haze` puts a cloud over it and drains the colour; `trips` blinks the rail
  light; `no_data` and `unclear` show only the outlines on the frame.
- The light on the floor under the array takes the verdict's colour.

## Colour
| Token | Hex | Used for |
|---|---|---|
| `--paper` / `--lit` | `#0B0C0F` / `#1B1E24` | Page, and where the light falls at the top |
| `--card-top` / `--card-low` | `#1F2329` / `#171A1F` | Raised surfaces, lit edge to shaded edge |
| `--well` | `#101216` | Inputs and meter tracks, set into a surface |
| `--ink` / `--soft` / `--muted` | `#F3F5F8` / `#C6CCD6` / `#8E97A6` | Text, long text on a card, labels |
| `--current` | `#FFC21A` | Electricity: rail light, likely-output bars, the main button, the active tab |
| `--dhool` / `--dhool-ink` | `#B9A27F` / `#D8C39A` | Dust; WAIT |
| `--wash` | `#4DB3F0` | Water: CLEAN, rain, links |
| `--fault` | `#FF6B57` | INSPECT, errors |
| `--good` | `#4ADE80` | OK |

A verdict is never colour alone: the headline says what to do and the model shows why.
Surfaces use a 22px radius; things you press or type into use 14px.

## Type
One family, **Anek Devanagari** (SIL OFL, Google Fonts): it covers Hindi and English and has a width axis.
Headlines are heavy and wide (800, 112%), the home's name is widest (125%), small labels slightly narrow
(92%), body regular. Numbers are tabular. Sentence case everywhere; no all-caps labels.

## Voice
- Say what to do, not the system's label: "Call your vendor", "Wash the panels", "Wait for the rain",
  "Don't wash. It's haze.", "Your solar is working".
- Say "units", the word on an Indian electricity bill, with kWh only where the inverter app uses it.
- Numbers come from the analysis, never invented. Estimates are stated as estimates ("about ₹165 a week").
- Errors say what happened and what to do next. No apologies, no jokes.
- The vendor message is a polite request, not a legal claim.

## Layout
Phone first: one column, 30rem at most, 16px gutters, touch targets 48px or more. Four tabs in a bottom
bar, each with an icon and a word:

| Tab | What it holds |
|---|---|
| Roof | Home name and "running at N% of normal"; the roof model; a strip of four readings (today's weather, next rain, units possible today, date of the last reading); the verdict card (what to do, a glowing meter, money lost, how sure, the reason, the action); two tiles leading to Forecast and Why |
| Forecast | The next 7 days: weather, likely against possible units |
| Why | The reason, should-have-made against made, money lost, the 90-day chart |
| Setup | Connect an inverter or type a reading, family code, sign out |

The meter and the percentage show output against **this roof's own normal** (100 minus the loss), not
against the physics number, which no roof reaches.
The bottom bar is hidden until a home has its first verdict.

## Motion
One sequence when a verdict arrives: the camera settles onto the roof, the rail lights up column by column,
then the meter fills. Dragging turns the model. Nothing moves under reduced motion.

## Not done yet
Hindi strings, screenshot upload, the "I washed them" verification step, a service worker for offline use,
a home switcher for people in two homes.
