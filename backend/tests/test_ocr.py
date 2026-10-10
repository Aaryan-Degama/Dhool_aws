"""The OCR trial's layout rules: which of the words on a screen are readings.
Tesseract itself is not run here (CI does not have it); scripts/eval-vision.py --ocr measures it on real images."""

import ocr_reader


def screen(*lines):
    """Lines of (x, y, "words ...", letter height) -> words with boxes, as Tesseract would give them."""
    found = []
    for x, y, text, *height in lines:
        height = height[0] if height else 30
        for word in text.split():
            width = int(len(word) * height * 0.6)
            found.append(ocr_reader.Word(word, x, y, x + width, y + height))
            x += width + height // 3
    return found


HEAD = [(60, 60, "Inverter Cloud", 40), (60, 135, "home-00 - 2 kW system - demo")]
TODAY_SCREEN = HEAD + [
    (100, 306, "Generation today, 25 September 2026"),
    (100, 378, "5.5", 124),
    (350, 452, "kWh", 46),
    (100, 670, "Last 30 days"),
    (100, 720, "167.2 kWh", 40),
    (100, 885, "Daily generation (kWh)"),
    (60, 1040, "7", 20),
    (60, 1295, "3", 20),
    (60, 1590, "27 Aug"),
    (920, 1590, "25 Sept"),
]


def test_a_list_of_days_is_read_row_by_row_under_its_kwh_heading():
    found = screen(
        *HEAD,
        (100, 306, "Daily generation"),
        (100, 368, "Date"),
        (916, 368, "kWh"),
        (100, 440, "2026-09-25"),
        (900, 440, "5.52"),
        (100, 528, "2026-09-24"),
        (900, 528, "5.96"),
        (100, 616, "24/09/2026"),
        (900, 616, "9.99"),
        (100, 704, "23 Sep 2026"),
        (880, 704, "6.07kWh"),
    )
    assert ocr_reader.layout(found) == (
        "A",
        [{"date": "2026-09-25", "kwh": 5.52}, {"date": "2026-09-24", "kwh": 5.96}, {"date": "2026-09-23", "kwh": 6.07}],
    )  # a date printed twice keeps its first row


def test_todays_figure_is_the_one_under_the_today_label_with_the_date_printed_on_it():
    # Not the 30-day total, and not the 7 and the 3 on the chart's axis under "Daily generation (kWh)".
    assert ocr_reader.layout(screen(*TODAY_SCREEN)) == ("B", [{"date": "2026-09-25", "kwh": 5.5}])


def test_a_figure_with_no_date_printed_comes_back_as_today():
    found = screen((100, 100, "Yield today"), (800, 100, "12.3 kWh"), (100, 180, "Total yield"), (800, 180, "4.1 MWh"))
    assert ocr_reader.layout(found) == ("B", [{"date": "TODAY", "kwh": 12.3}])
    assert ocr_reader.layout(screen((100, 100, "E-Today (kWh)"), (100, 150, "8.4", 60))) == (
        "B",
        [{"date": "TODAY", "kwh": 8.4}],
    )
    assert ocr_reader.layout(screen((100, 100, "850 Wh", 60), (100, 180, "Today"))) == (
        "B",
        [{"date": "TODAY", "kwh": 0.85}],
    )


def test_nothing_is_returned_that_is_not_tied_to_a_date_or_a_today_label():
    refused = [
        [(100, 100, "Today"), (800, 100, "0.22 kW")],  # power now
        [(100, 100, "Units possible today"), (100, 150, "9.1 kWh", 60)],  # Dhool's own screen
        [(100, 100, "Today's consumption"), (800, 100, "7.0 kWh")],
        [(100, 100, "Updated 2026-09-25 14:32"), (700, 100, "1500 kWh")],  # one dated figure is not a list
        [(100, 100, "Energy"), (100, 150, "12.3 kWh", 60)],  # no label says today
        [(100, 100, "Today"), (100, 150, "? kWh", 60)],  # the figure did not read
        [(100, 100, "Today"), (100, 150, "5.0 kWh"), (600, 100, "Today"), (600, 150, "7.0 kWh")],  # which one?
        [(100, 100, "3.0 kWh"), (100, 150, "Today"), (100, 200, "90.0 kWh"), (100, 250, "Month")],  # over or under?
    ]
    for lines in refused:
        assert ocr_reader.layout(screen(*lines)) == ("C", []), lines
