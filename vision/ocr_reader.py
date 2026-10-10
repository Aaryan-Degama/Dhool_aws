"""Reads the daily generation figures off a screenshot of an inverter app, with plain OCR.

A trial beside screenshot_reader.py (the vision model), with the same call and the same result. Tesseract
(Apache-2.0) finds the words and where they sit; fixed layout rules then decide which numbers are readings:
- a list of days: two or more rows, each holding one printed date and one kWh figure;
- today's figure: the kWh figure beside, under or over a label that says today.
A number is never returned unless it is tied to a date or to such a label. Charts are not read.

What it returns is never trusted as fact: the API drops any value that cannot be true for the roof, and
the homeowner confirms or corrects the rest before anything is saved.
"""

import collections
import datetime
import io
import os
import re
import subprocess

from PIL import Image, ImageOps, ImageStat

TESSERACT = os.environ.get("TESSERACT", "tesseract")
MAX_PIXELS = 30_000_000  # as in screenshot_reader: no phone screenshot is larger
MAX_SIDE = 32_000  # Tesseract refuses a picture with a side over 32,767 pixels
READER = "tesseract-rules"
# Tesseract reads best when letters are about 30 pixels tall. Small screenshots are enlarged to this width;
# print far larger than that (the big figure on a today screen) is cut out, shrunk and read again: at full
# size the demo screen's "5.5" came back as "3.9".
MIN_WIDTH = 1080
SMALL, NORMAL = 20, 30  # if most words are still under SMALL pixels tall, enlarge again to bring them to NORMAL
TALL = 70
REREAD_HEIGHT = 40

Word = collections.namedtuple("Word", "text x0 y0 x1 y1")

UNIT = re.compile(r"(?<![a-z])([km]?)wh(?![a-z])")
# No point or comma may trail a number: "7." is how a "7.7" comes back when its last digit is lost.
NUMBER = re.compile(r"^[\[(]?(\d{1,6}(?:[.,]\d{1,3})?)([km]?wh)?[\]);:]*$")
TO_KWH = {"k": 1, "": 0.001, "m": 1000}
MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()
MONTH = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
DATES = [  # (pattern, the order its groups come in)
    (re.compile(r"(?<!\d)(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)"), "ymd"),
    (re.compile(r"(?<!\d)(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})(?!\d)"), "dmy"),
    (re.compile(rf"(?<!\d)(\d{{1,2}})(?:st|nd|rd|th)?\s+{MONTH},?\s+(\d{{4}})(?!\d)"), "dmy"),
    (re.compile(rf"\b{MONTH}\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})(?!\d)"), "mdy"),
]
# A label that says the figure is today's generation: one of the first words and none of the second (word
# beginnings). "Last 30 days", "Total", "Today's consumption" and a forecast are other figures.
TODAY = {"today", "todays", "etoday", "daily", "day"}
NOT_TODAY = (
    "total",
    "month",
    "year",
    "week",
    "life",
    "last",
    "yesterday",
    "forecast",
    "expect",
    "possible",
    "estimat",
    "predict",
    "consum",
    "import",
    "export",
    "load",
    "grid",
    "purchas",
    "bought",
    "sold",
    "feed",
    "charg",
    "discharg",
    "batter",
    "self",
    "sav",
    "revenue",
    "income",
    "earn",
    "co2",
    "limit",
    "target",
    "capacity",
    "peak",
    "avg",
    "average",
)


def tesseract(picture, psm):
    """A greyscale picture -> its words with their boxes."""
    png = io.BytesIO()
    picture.save(png, "PNG")
    out = subprocess.run(
        [TESSERACT, "stdin", "stdout", "--psm", str(psm), "tsv"],
        input=png.getvalue(),
        capture_output=True,
        check=True,
        timeout=120,
    ).stdout.decode("utf-8", "replace")
    found = []
    for line in out.splitlines()[1:]:
        cell = line.split("\t")
        if len(cell) == 12 and cell[0] == "5" and cell[11].strip():
            left, top, width, height = map(int, cell[6:10])
            found.append(Word(cell[11].strip(), left, top, left + width, top + height))
    return found


def spans(shades):
    """A row or column of shades -> the (start, end) of each stretch that has ink in it."""
    out, start = [], None
    for at, shade in enumerate(list(shades) + [0]):
        if shade and start is None:
            start = at
        elif not shade and start is not None:
            out.append((start, at))
            start = None
    return out


def reread(picture, found):
    """Read the oversized print again. Tesseract takes a line of text at one size, and a today screen prints a
    huge figure with a small unit beside it. So the line is cut into runs of large and of small print, and each
    run is trimmed to its own ink, brought to a normal size and read alone."""
    for tall in lines([w for w in found if w.y1 - w.y0 > TALL]):
        height = max(w.y1 for w in tall) - min(w.y0 for w in tall)
        top = max(0, min(w.y0 for w in tall) - height // 5)
        cut = picture.crop((0, top, picture.width, min(picture.height, max(w.y1 for w in tall) + height // 5)))
        left, right = tall[0].x0, tall[-1].x1
        paper = max(
            range(256), key=cut.crop((left, 0, right, cut.height)).histogram().__getitem__
        )  # the commonest shade there
        # B023 below: point() calls the lambda at once, inside this turn of the loop, so it sees this turn's paper
        ink = cut.point(lambda shade: 255 if abs(shade - paper) > 60 else 0)  # noqa: B023
        # Widen to the whole card the print stands on, out to where another background begins (a column that is
        # all "ink"): nothing on the line is cut through, since half a unit must never be read as a unit.
        solid = [shade >= 250 for shade in ink.resize((cut.width, 1), Image.BOX).getdata()]
        while left > 0 and not solid[left - 1]:
            left -= 1
        while right < cut.width and not solid[right]:
            right += 1
        cut, ink = cut.crop((left, 0, right, cut.height)), ink.crop((left, 0, right, cut.height))
        rows = spans(ink.resize((1, cut.height), Image.BOX).getdata())
        if not rows:
            continue
        # Tesseract's box for oversized print is loose and can take in the line above: keep the tallest line only.
        y0, y1 = max(rows, key=lambda row: row[1] - row[0])
        top, cut, ink = top + y0, cut.crop((0, y0, cut.width, y1)), ink.crop((0, y0, cut.width, y1))
        runs = []  # [is it large print, x0, y0, x1, y1]
        for x0, x1 in spans(ink.resize((cut.width, 1), Image.BOX).getdata()):  # each mark of ink between empty columns
            _, y0, _, y1 = ink.crop((x0, 0, x1, cut.height)).getbbox()
            large = y1 - y0 >= 0.6 * cut.height
            if y1 - y0 < 0.3 * cut.height and runs:  # a point or a comma goes with what it follows
                large = runs[-1][0]
            if runs and runs[-1][0] == large:
                runs[-1][2:] = min(runs[-1][2], y0), x1, max(runs[-1][4], y1)
            else:
                runs.append([large, x0, y0, x1, y1])
        found = [
            w
            for w in found
            if not (left <= (w.x0 + w.x1) / 2 <= right and top <= (w.y0 + w.y1) / 2 <= top + cut.height)
        ]
        for _, x0, y0, x1, y1 in runs:
            scale, edge = REREAD_HEIGHT / (y1 - y0), REREAD_HEIGHT // 2
            piece = cut.crop((x0, y0, x1, y1)).resize((max(1, round((x1 - x0) * scale)), REREAD_HEIGHT), Image.LANCZOS)
            framed = Image.new("L", (piece.width + 2 * edge, piece.height + 2 * edge), paper)
            framed.paste(piece, (edge, edge))
            again = tesseract(framed, 7)  # 7: one line of text
            # A run that reads as nothing stays as a word no rule will take for a figure or a unit.
            x0, x1 = left + x0, left + x1
            found += [
                Word(w.text, x0 + round((w.x0 - edge) / scale), top + y0, x0 + round((w.x1 - edge) / scale), top + y1)
                for w in again
            ] or [Word("?", x0, top + y0, x1, top + y1)]
    return found


def words(image):
    """PNG or JPEG bytes -> the words on the screen."""
    picture = Image.open(io.BytesIO(image))
    if picture.width * picture.height > MAX_PIXELS:
        raise ValueError(f"the picture is {picture.width} x {picture.height} pixels, too large for a screenshot")
    if max(picture.size) > MAX_SIDE:
        raise ValueError(f"the picture is {picture.width} x {picture.height} pixels, too long for a screenshot")
    picture = picture.convert("L")
    if ImageStat.Stat(picture).mean[0] < 110:  # a dark theme: Tesseract wants dark letters on light
        picture = ImageOps.invert(picture)
    if picture.width < MIN_WIDTH:
        scale = min(3, MIN_WIDTH / picture.width, MAX_SIDE / picture.height)
        picture = picture.resize((round(picture.width * scale), round(picture.height * scale)), Image.LANCZOS)
    found = tesseract(picture, 11)  # 11: words wherever they are; an app screen is not a page of text
    heights = sorted(w.y1 - w.y0 for w in found)
    if heights and heights[len(heights) // 2] < SMALL:  # small print: a screen shown inside a larger picture
        scale = min(
            3,
            NORMAL / max(1, heights[len(heights) // 2]),
            (MAX_PIXELS / (picture.width * picture.height)) ** 0.5,
            MAX_SIDE / max(picture.size),
        )
        picture = picture.resize((round(picture.width * scale), round(picture.height * scale)), Image.LANCZOS)
        found = tesseract(picture, 11)
    return reread(picture, found)


def lines(found):
    """Words -> rows (words whose middles sit at one height), each row left to right, rows top to bottom."""
    rows = []
    for word in sorted(found, key=lambda w: (w.y0 + w.y1) / 2):
        middle = (word.y0 + word.y1) / 2
        for row in reversed(rows[-3:]):
            if any(w.y0 <= middle <= w.y1 or word.y0 <= (w.y0 + w.y1) / 2 <= word.y1 for w in row):
                row.append(word)
                break
        else:
            rows.append([word])
    return [sorted(row, key=lambda w: w.x0) for row in rows]


def groups(row):
    """A row -> its groups of words that stand together, split where the gap is wide (columns, cards)."""
    out = [[row[0]]]
    for before, word in zip(row, row[1:], strict=False):  # each word with the next: one short on purpose
        if word.x0 - before.x1 > 1.5 * min(before.y1 - before.y0, word.y1 - word.y0):
            out.append([])
        out[-1].append(word)
    return out


def dates(row):
    """A row -> ([ISO dates printed in full on it], the indexes of the words they are made of)."""
    text, starts = "", []
    for word in row:
        starts.append(len(text))
        text += word.text.lower() + " "
    found, used = [], set()
    for pattern, order in DATES:
        for match in pattern.finditer(text):
            part = dict(zip(order, match.groups(), strict=False))
            month = MONTHS.index(part["m"]) + 1 if part["m"] in MONTHS else int(part["m"])
            day = int(part["d"])
            if month > 12 and order == "dmy":  # 09/25/2026: the month came first
                day, month = month, day
            try:
                found.append(datetime.date(int(part["y"]), month, day).isoformat())
            except ValueError:
                continue
            used |= {
                i for i, start in enumerate(starts) if start < match.end() and start + len(row[i].text) > match.start()
            }
    return found, used


def number(text):
    value = text.replace(",", "") if re.fullmatch(r"\d{1,3},\d{3}", text) else text.replace(",", ".")
    return float(value)


def figures(group, skip=()):
    """Words -> ([kWh figures: (value, word)], [numbers with no unit: nothing after them, or another number])."""
    with_unit, bare = [], []
    for i, word in enumerate(group):
        match = NUMBER.match(word.text.lower())
        if not match or i in skip:
            continue
        after = group[i + 1].text.lower() if i + 1 < len(group) and i + 1 not in skip else ""
        unit = UNIT.search(match.group(2) or "") or (not NUMBER.match(after) and UNIT.search(after))
        if unit:
            with_unit.append((round(number(match.group(1)) * TO_KWH[unit.group(1)], 6), word))
        elif not after or NUMBER.match(after):
            bare.append((number(match.group(1)), word))
    return with_unit, bare


def overlap(a, b):
    """Do two runs of words share any width? a and b are (x0, x1)."""
    return a[0] < b[1] and b[0] < a[1]


def is_unit(word):
    """A unit standing on its own or in a label ("kWh", "Yield (kWh)"), not a figure with its unit ("5.5kWh")."""
    return bool(UNIT.search(word.text.lower())) and not NUMBER.match(word.text.lower())


def day_list(rows):
    """Rows that hold one date and one kWh figure: the unit beside the figure, or heading its column."""
    heads = [w for row in rows for w in row if is_unit(w)]
    seen = {}
    for row in rows:
        found, used = dates(row)
        if len(found) != 1:
            continue
        with_unit, bare = figures(row, used)
        if not with_unit and len(bare) == 1:  # no unit on the row: one figure, standing under a "kWh" heading
            value, word = bare[0]
            with_unit = [
                (round(value * TO_KWH[UNIT.search(head.text.lower()).group(1)], 6), word)
                for head in heads
                if head.y1 <= word.y0 and overlap((head.x0, head.x1), (word.x0, word.x1))
            ][:1]
        if len(with_unit) == 1 and len(bare) <= 1:  # two figures on a row (made and used, say) are not told apart
            seen.setdefault(found[0], with_unit[0][0])
    # One dated figure is not a list: it may be a total with the time it was updated.
    return [{"date": date, "kwh": kwh} for date, kwh in seen.items()] if len(seen) >= 2 else []


def today(rows):
    """The kWh figure tied to a label that says today: in the label's own group, alone in the next group on its
    row, or alone in the group straight under or over it."""
    all_dates = {date for row in rows for date in dates(row)[0]}
    grouped = [groups(row) for row in rows]
    found = set()
    for r, row in enumerate(grouped):
        for g, label in enumerate(row):
            said = [re.sub(r"[^a-z0-9]", "", w.text.lower()) for w in label]
            if not TODAY & set(said) or any(word.startswith(NOT_TODAY) for word in said):
                continue
            # A label that carries the unit itself ("Today (kWh)") lets a number stand without one.
            carries = any(is_unit(w) for w in label)

            def alone(group):
                """The one figure a group holds, if it holds nothing else."""
                with_unit, bare = figures(group)
                rest = [w for w in group if not NUMBER.match(w.text.lower()) and not UNIT.search(w.text.lower())]
                # B023 below: alone() is called only further down this same turn of the loop, never kept past it
                if rest or len(with_unit + bare) != 1 or (bare and not carries):  # noqa: B023
                    return None
                return (with_unit + bare)[0][0]

            with_unit, bare = figures(label, dates(label)[1])
            values = with_unit + (bare if carries else [])
            value = values[0][0] if len(values) == 1 else alone(row[g + 1]) if not values and g + 1 < len(row) else None
            if value is None and not values:
                top, bottom = min(w.y0 for w in label), max(w.y1 for w in label)
                near = []
                for other in grouped[:r] + grouped[r + 1 :]:
                    for group in other:
                        gap = max(min(w.y0 for w in group) - bottom, top - max(w.y1 for w in group))  # under or over
                        reach = max(
                            2.5 * (bottom - top), max(w.y1 - w.y0 for w in group)
                        )  # near, for print of either size
                        if (
                            0 <= gap <= reach
                            and overlap((label[0].x0, label[-1].x1), (group[0].x0, group[-1].x1))
                            and alone(group) is not None
                        ):
                            near.append((gap, alone(group)))
                near.sort()
                # Figures about as near on both sides (a column of label, figure, label, figure): which one is
                # today's cannot be told, so none is taken.
                if near and (len(near) == 1 or near[1][0] > 1.5 * max(near[0][0], (bottom - top) / 2)):
                    value = near[0][1]
            if value is not None:
                on_row = dates([w for group in row for w in group])[0]
                found.add(
                    (
                        on_row[0] if len(on_row) == 1 else next(iter(all_dates)) if len(all_dates) == 1 else "TODAY",
                        value,
                    )
                )
    # Two labels that say today with different figures (production and consumption, say): not told apart.
    return [{"date": date, "kwh": kwh} for date, kwh in found] if len(found) == 1 else []


def layout(found):
    """Words with their boxes -> (kind, readings): "A" a list of days, "B" today's figure, "C" neither."""
    rows = lines(found)
    readings = day_list(rows)
    if readings:
        return "A", readings
    readings = today(rows)
    return ("B", readings) if readings else ("C", [])


def read(image):
    """PNG or JPEG bytes ->
    {"reader", "kind", "readings": [{"date": "YYYY-MM-DD" or "TODAY", "kwh": float}], "replies"}"""
    found = words(image)
    kind, readings = layout(found)
    text = "\n".join(" ".join(w.text for w in row) for row in lines(found))
    return {"reader": READER, "kind": kind, "readings": readings, "replies": {"text": text[:1500]}}
