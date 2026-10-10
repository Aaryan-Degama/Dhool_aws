"""Whether a nightly run is worth a notification on the family's phones, and what it says. Pure.

The text is fixed and written by hand in both languages; the body is the verdict's own reason.
"""

STOPPED_AFTER_DAYS = 3  # said on this day only, so a silent inverter is one alert and not one every night

TEXT = {
    "INSPECT": {"en": ("Dhool: call your vendor", "Your panels are making less than they should."),
                "hi": ("Dhool: वेंडर को बुलाइए", "आपके पैनल जितनी बिजली बनानी चाहिए उससे कम बना रहे हैं।")},
    "CLEAN": {"en": ("Dhool: wash the panels", "The dust is now costing more than a wash."),
              "hi": ("Dhool: पैनल धो दीजिए", "धूल का नुकसान अब एक धुलाई के ख़र्च से ज़्यादा है।")},
    "stopped": {"en": ("Dhool: no readings for 3 days",
                       "Check that the inverter is on and connected to Wi-Fi, or add a reading yourself."),
                "hi": ("Dhool: 3 दिन से कोई रीडिंग नहीं",
                       "देख लीजिए कि इन्वर्टर चालू है और Wi-Fi से जुड़ा है, या ख़ुद एक रीडिंग डाल दीजिए।")},
}


def message(told, new, days_since_reading, lang):
    """told is what the family's phones were last told, {"verdict", "cause"} (or None: nothing yet, or the
    trouble has passed since). new is this run's verdict. Returns {"title", "body", "url"} to send, or None
    when there is nothing new to say."""
    lang = lang if lang in ("en", "hi") else "en"
    if days_since_reading == STOPPED_AFTER_DAYS:
        title, body = TEXT["stopped"][lang]
    elif new["verdict"] in ("INSPECT", "CLEAN") and (
            not told or (told.get("verdict"), told.get("cause")) != (new["verdict"], new.get("cause"))):
        title, body = TEXT[new["verdict"]][lang]
        body = new.get("reason_hi" if lang == "hi" else "reason") or body
    else:
        return None
    return {"title": title, "body": body, "url": "/#/roof"}
