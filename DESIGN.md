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
not fixed at first: it rises with the page until it sits just under the top bar, and stays there while the
sheets slide over it. So after a little scrolling the array is at the top of the screen with the advice under
it. It goes out of focus (up to 5px) only as the sheets cover it (`--covered`, set in `RoofTab`), and keeps
its colours. (A full dissolve into a wash of the sky's colour was tried on 10 Oct and dropped: the owner
wanted the panels kept. Thin sheets with the array showing through the text were tried and dropped too: the
text sat on a smear.) `.roof` is a block, not a grid: a sticky child of a grid is held inside its own row.

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
Roof tab, sign-in, "Working it out"). History, Why and Setup open with a heading right where the sun
would be, so there the sky keeps its colour, clouds and stars but not the sun or moon (`#sky::after`,
faded out with `:has()`).

No people and no landscape illustration: the only scene is the roof model. Everything drawn has to be
physically possible. Rain and snow fall both behind the page and in front of the roof scene; blown sand
stays in the air and thins out before the terrace floor rather than streaking across it. Surfaces turn to dark glass tinted by the sky
(`--glass`), and `--wash` and `--fault` are lightened so text keeps its contrast. Text never sits
directly on the sky except large headings: everything small is on a surface. Nothing moves under
reduced motion. The graphite tokens above are the fallback when no sky is set.

## Type
One family, **Anek Devanagari** (SIL OFL; served from the app's own `public/fonts/`, not from Google Fonts): it covers Hindi and English.
Normal width throughout. Size and a light or regular weight carry the hierarchy; 600 is the heaviest anything
gets: the reading figure is 300 at up to 6rem, page headings 1.75rem/600, section titles 1.0625rem/600, body
1rem/400, labels and captions 0.8125rem/500. Numbers are tabular. Sentence case everywhere; no all-caps labels.
The "Dhool" wordmark is drawn, not set: marker strokes with round ends and two filled o's (`Wordmark` in `visuals.jsx`).

## Surfaces and buttons (10 Oct 2026)
Three levels and no more. **Sky:** no surface; the reading, the scene and the weather row sit straight on it.
**Sheet** (`.card`): tinted, blurred glass with a 28px radius and no outline or lit edge; hairlines only
between rows inside it. **Well:** the darker inset of an input or a switch, 14px radius.
Buttons in falling weight: one solar-yellow primary action on a screen, a quiet filled secondary, a link.
Nothing is outlined. A **row** (`.row-link`, `details.more`) is a line with an arrow at its end that goes
somewhere or opens something; a **switch** (`.switch`) shows one of a few views of a sheet.
One loud thing per screen: on Roof it is the reading. Yellow is kept for the primary action, the current in
the array and the history bars.

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
| Roof | The top bar (the wordmark, the home's name); **the reading** in the sky: the percentage of this roof's normal, large and light, a thin meter in the verdict's colour, what to do, money lost, how sure; the roof model; four readings in a row on the sky (today's weather, next rain, units possible today, date of the last reading); one sheet with the reason, the action, and rows that open the vendor-reply box and the wash or visit report; rows to History and Why |
| Roof, on "Call your vendor" | Paste the vendor's WhatsApp reply: Dhool sorts it into four kinds (coming, wants something first, won't help, no clear answer), shows them as four buttons with its pick selected, and says the next step. The homeowner can change the pick; if the reader is unavailable the same buttons work by hand |
| History | What the roof made in each of the last six months (fewer for a newer home): a bar and the units for each month, the total above, and a plain note under a month with no readings, with days missing, or still running. A month opens, on a tap, to its weeks by date (1–7, 8–14, 15–21, 22–28, 29 to the end), each with its units, and a week to its days; a day with no reading says so, and nothing after the last reading is listed. Native `<details>`, so the keyboard and a screen reader get it too; a verdict stored without the days shows the months alone. Below it, the last 20 washes and vendor visits, newest first, each with whether it worked where Dhool measured it |
| Why | The reason, should-have-made against made, money lost, the chart (90 days, or from three weeks before a fault) |

**What "should have made" and "possible" mean.** What this roof makes when it is clean and healthy: the
physics at the roof's own normal share, the same basis the verdict measures against. Never the physics
alone, which no roof reaches; a healthy roof would otherwise look a few percent short everywhere. On the
Why tab, should-have-made and made are a day, averaged over the week to the last reading, and the loss
shown beside them is exactly their difference.
| Setup | Upload a screenshot (the model reads it, then the homeowner checks and corrects every number before saving; while it reads, a timer, "about a minute", and "Type the number instead" one tap away, with the other forms still usable), connect an inverter with its API key, type a reading, the wash cost and electricity rate, the system size in kW (a typed number the owner can change; only shown, with where it came from, on a home linked to an inverter or for a family member), family code, sign out |

The meter and the percentage show output against **this roof's own normal** (100 minus the loss), not
against the physics number, which no roof reaches.
The bottom bar is a capsule of glass floating over the page (blurred, a little brighter, a lit top edge), with a clearer lens behind the chosen tab that slides to the next one with a small overshoot; a tab's page rises into place. None of it moves under "reduce motion". The bar is hidden until a home has its first verdict.

## Wide screens (60rem and up; 11 Oct 2026)
The same app and code, laid out as a website: one media query at the end of `styles.css`. The tabs become the
site's header across the top (the wordmark on the left, the tabs in the middle with the sliding lens, the
home's name on the right); the phone's top bar is hidden there. Roof opens on a wide band: the reading on the
left as a large headline (what to do) with the reason and the weather row under it. The scene is the band's
backdrop from edge to edge of the screen: the array on the right, the terrace and city running on behind the
headline (drawn `WING` units to the left for this) under a shade that keeps the words readable. Beyond the drawn wall is a rendered
picture of the sky of the moment over trees, low houses and towers (`web/public/scene/<sky>.webp`, seven of
them; after dark every sky uses the night one). Everything in front of it is drawn and turns together when
dragged: the parapet, the terrace floor and the array, which shows a dead string or dust as on a phone. Only
the drawn city (`.pm-city`) is hidden. Two earlier tries were dropped the same day: pictures with the panels
in them (they could not turn or show a fault), and the drawn array on a pictured terrace (it floated, and the
terrace stood still while the array turned). The pictures are mirrored and their own terrace is cut away, so
the drawn wall always covers their lower edge. Phones keep the fully drawn scene. On both, the terrace ends at a corner on the left where the parapet turns
toward the viewer, and potted plants stand along the walls. Below, two sheets of equal size: the advice sheet
(headed by the money lost, the percentage and the meter) and the units made on each of the last 7, 30 or 90
days (`Trend`, from the verdict's `daily_kwh`; wide screens only). The rows to History and Why are not shown
there: the header has those tabs. Sheets' corners are 16px on wide screens. Pieces that exist only here carry `.wide-only`. History, Synopsis and Setup set their
sheets in two columns; on Setup "Add readings" runs across the top. A first version with a rail on the left
and two narrow columns was dropped the same day: the owner found it still a phone screen, not a website.
The sign-in and add-home pages keep their single centred column. `RoofTab` wraps its two groups in
`.roof-scene` and `.roof-advice`, which make no box on a phone (`display: contents`).

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
