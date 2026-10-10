# DESIGN.md — how Dhool looks and speaks

Set on Oct 8, reworked on Oct 10 into a premium, car-app style at the owner's request (reference: the
Tesla app). Tokens live in `web/src/styles.css`; change them there, not in components.

## Idea
The roof is the product shot. The one loud element is **the roof model**: a rooftop array drawn in
perspective, standing on a terrace with the city behind it, which shows the cause instead of naming it. A dead string goes
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
- The array stands on a tiled terrace with a shaded parapet; beyond it is a city skyline in three depths
  (stepped tops, masts, rooftop water tanks, windows lit at night and in storms) that fades into haze
  toward the horizon. Their colours follow the sky, and the far edge of the glass reflects it.
- The camera is at about eye height on the terrace (13° down), so the horizon and the city are in view.

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

## Scrolling: a pinned scene under frosted glass
Modelled on the phone weather apps the owner showed. On the Roof tab the scene (terrace, city, panels) is
pinned where it first appears, and everything after it slides over it. Once the page moves, a veil blurs
the background below the top 30% of the screen; the top stays sharp, so the sky, sun or moon and the
skyline remain clear. The veil fades in over the first 160 px of scrolling.

Surfaces are frosted glass that mostly shows the sky through: a light white lift over a thin tint of the
sky's own dark colour (`--glass`), 24 px blur. On glass this light, the verdict colours are too weak as
text, so headings and figures stay white and the verdict's colour lives in the bolt, the meter and the
scene. Text sitting straight on the sky has a soft shadow.

## The sky (`web/src/sky.js`, the "The sky" section of `styles.css`)
The whole app sits under the weather over the roof. Until a home is loaded the phone's clock picks day or
night; then Open-Meteo's current conditions for the home's location decide (coordinates rounded to about
a kilometre), and the sky is checked again every ten minutes. `?sky=rain` (or any name below) in the
address forces one, and `&dark=1` gives its night version, for demos and screenshots.

| Sky | When | What is drawn |
|---|---|---|
| `day` | Clear or partly cloudy, daytime | Bright blue gradient, the sun |
| `cloud` | Overcast or fog | Grey-blue gradient, a soft cloud deck; a dark version at night |
| `rain` | Rain or drizzle, daytime | Grey-teal gradient, cloud, falling rain |
| `storm` | Thunder, heavy rain, or any rain after dark | Dark slate gradient, faster rain, lit windows |
| `snow` | Snow | Pale grey-blue gradient, drifting snow, a white terrace; a dark version at night |
| `sand` | A sandstorm: gusts of 40 km/h or more, visibility under 5 km, and dust of 150 µg/m³ or more, all three | Ochre gradient, haze, fine grains blowing sideways; a dark version at night |
| `night` | Dry, after dark | Muted indigo gradient, stars, the moon, lit windows |

Dust in the air alone is not a sandstorm: Delhi's air read 300 to 380 µg/m³ of dust on a calm, clear
night, which wrongly triggered the first version of the rule.

The sun and the moon hang behind the roof scene, so they are drawn only on a page that has the scene (the
Roof tab, sign-in, "Working it out"). Forecast, Why and Setup open with a heading right where the sun
would be, so there the sky keeps its colour, clouds and stars but not the sun or moon (`#sky::after`,
faded out with `:has()`).

No people and no landscape illustration: the only scene is the roof model. Everything drawn has to be
physically possible. Rain and snow fall both behind the page and in front of the roof scene; blown sand
stays in the air and thins out before the terrace floor rather than streaking across it. Surfaces turn to dark glass tinted by the sky
(`--glass`), and `--wash` and `--fault` are lightened so text keeps its contrast. Text never sits
directly on the sky except large headings: everything small is on a surface. Nothing moves under
reduced motion. The graphite tokens above are the fallback when no sky is set.

## Type
One family, **Anek Devanagari** (SIL OFL; served from the app's own `public/fonts/`, not from Google Fonts): it covers Hindi and English and has a width axis.
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
| Roof | Home name and "running at N% of normal"; the roof model; a strip of four readings (today's weather, next rain, units possible today, date of the last reading); the verdict card (what to do, a glowing meter, money lost, how sure, the reason, the action, and at its foot a quiet "Was this advice useful?" with a thumb up and a thumb down); two tiles leading to Forecast and Why |
| Roof, on "Call your vendor" | Paste the vendor's WhatsApp reply: Dhool sorts it into four kinds (coming, wants something first, won't help, no clear answer), shows them as four buttons with its pick selected, and says the next step. The homeowner can change the pick; if the reader is unavailable the same buttons work by hand |
| Forecast | The next 7 days: weather, likely against possible units |
| Why | The reason, should-have-made against made, money lost, the chart (90 days, or from three weeks before a fault) |

**What "should have made" and "possible" mean.** What this roof makes when it is clean and healthy: the
physics at the roof's own normal share, the same basis the verdict measures against. Never the physics
alone, which no roof reaches; a healthy roof would otherwise look a few percent short everywhere. On the
Why tab, should-have-made and made are a day, averaged over the week to the last reading, and the loss
shown beside them is exactly their difference.
| Setup | Upload a screenshot (the model reads it, then the homeowner checks and corrects every number before saving; while it reads, a timer, "about a minute", and "Type the number instead" one tap away, with the other forms still usable), connect an inverter with its API key, type a reading, family code, sign out |

The meter and the percentage show output against **this roof's own normal** (100 minus the loss), not
against the physics number, which no roof reaches.
The bottom bar is hidden until a home has its first verdict.

## Reading a screenshot
Reading takes a minute or two (a small model on two CPU cores), so the upload screen says so and shows a
spinner while it waits. What comes back is shown as a list of days with each number in an editable box:
"Check them against it. Correct any number that is wrong, or clear a box to leave that day out." Nothing
is saved until the homeowner presses "These are right. Save them". If nothing could be read, the screen
says so plainly and points to typing the number in.

## Motion
One sequence when a verdict arrives: the camera settles onto the roof, the rail lights up column by column,
then the meter fills. Dragging turns the model. Nothing moves under reduced motion.

## Two languages
English and Hindi, fixed text in both. The app starts in the phone's language. Setup has a "Language · भाषा" card with the two choices, each named in its own language so a reader of only one can find it; the sign-in screen has a small link to the other language, since Setup comes after signing in. Changing it reloads the app. Dates take Hindi month and weekday names; digits stay 0–9 (₹50, 13.6 units). "Dhool" stays in Latin letters in Hindi, because धूल is also the word for dust. Every line goes through `t()`; see `CLAUDE.md`, Conventions. Checked at 390 px and in the emulator: no Hindi line clips or pushes the page sideways.

## Not done yet
A PNG icon for notifications (Android may not draw the SVG one).
