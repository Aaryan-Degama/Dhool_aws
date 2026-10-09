"""The sentence that goes with a verdict, in English and Hindi.

Fixed text written by hand; the figures are filled in by `say()` from what the rules computed, the same
ones in both languages. No model writes or rewords any of it. "Dhool" stays in Latin letters in Hindi:
धूल is also the word for dust, and the sentences are about both.
"""

MONTHS_HI = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
WEEKDAYS_HI = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]

REASONS = {
    "no_data": {
        "en": "Only {n} days of data so far. Dhool needs about two weeks to learn this roof's normal.",
        "hi": "अभी सिर्फ़ {n} दिन का डेटा है। इस छत का सामान्य स्तर समझने के लिए Dhool को लगभग दो हफ़्ते चाहिए।",
    },
    "outage": {
        "en": "Your roof {when}, though the sun was good. Check that the inverter is switched on and shows "
              "no error. If it is off or shows an error, call the vendor.",
        "hi": "धूप अच्छी थी, फिर भी आपकी छत ने {when} लगभग कुछ भी बिजली नहीं बनाई। देखिए कि इन्वर्टर चालू है "
              "और उस पर कोई एरर नहीं दिख रहा। अगर वह बंद है या एरर दिखा रहा है, तो वेंडर को बुलाइए।",
    },
    "outage_on": {"en": "made almost nothing on {day:%-d %b}", "hi": "{day:%-d %b} को"},
    "outage_since": {"en": "has made almost nothing since {day:%-d %b}", "hi": "{day:%-d %b} से"},
    "fault": {
        "en": "Output fell about {drop:.0%} around {day:%-d %b} and has stayed down for {days} days. "
              "Dust builds slowly and haze lifts, so this looks like a hardware fault, such as a failed "
              "string or new shading.",
        "hi": "{day:%-d %b} के आसपास बिजली उत्पादन लगभग {drop:.0%} गिरा और {days} दिन से कम ही है। "
              "धूल धीरे-धीरे जमती है और धुंध छँट जाती है, इसलिए यह हार्डवेयर की ख़राबी लगती है, जैसे कोई "
              "स्ट्रिंग बंद होना या पैनलों पर नई छाया पड़ना।",
    },
    "trips": {
        "en": "Output dropped sharply on {n} separate days in the last 30 and came back each time. "
              "This can be the inverter shutting down for part of the day.",
        "hi": "पिछले 30 दिनों में {n} अलग-अलग दिन बिजली उत्पादन अचानक गिरा और हर बार वापस आ गया। "
              "हो सकता है इन्वर्टर दिन में कुछ देर के लिए बंद हो रहा हो।",
    },
    "just_cleaned": {
        "en": "{by} on {day:%-d %b} should have brought the panels back. Dhool will confirm it "
              "over the next few clear days.",
        "hi": "{day:%-d %b} {by} पैनल ठीक हो जाने चाहिए। अगले कुछ साफ़ दिनों में Dhool इसकी पुष्टि करेगा।",
    },
    "by_rain": {"en": "Rain", "hi": "की बारिश से"},
    "by_wash": {"en": "Your wash", "hi": "को आपकी धुलाई से"},
    "by_visit": {"en": "The vendor's visit", "hi": "को वेंडर के आने से"},
    "ok": {
        "en": "Your roof is producing what it should: within {loss:.0%} of its normal.",
        "hi": "आपकी छत उतनी ही बिजली बना रही है जितनी बनानी चाहिए: सामान्य स्तर से {loss:.0%} के अंदर।",
    },
    "haze": {
        "en": "The air is hazy (PM2.5 around {pm:.0f}) and output across the area fell about "
              "{fell:.0%} in the last few days. Less sunlight is reaching the panels. "
              "Washing won't help, so save the water.",
        "hi": "हवा में धुंध है (PM2.5 लगभग {pm:.0f}) और पिछले कुछ दिनों में पूरे इलाक़े का बिजली उत्पादन लगभग "
              "{fell:.0%} गिरा है। पैनलों तक धूप कम पहुँच रही है। धोने से फ़ायदा नहीं होगा, इसलिए पानी बचाइए।",
    },
    "not_dust": {
        "en": "You washed the panels on {day:%-d %b}, but output is still about {loss:.0%} below "
              "this roof's normal. Dust was not the cause, so have the system inspected.",
        "hi": "आपने {day:%-d %b} को पैनल धोए, लेकिन बिजली उत्पादन अब भी इस छत के सामान्य स्तर से लगभग "
              "{loss:.0%} कम है। कारण धूल नहीं थी, इसलिए सिस्टम की जाँच करवाइए।",
    },
    "clean": {
        "en": "Output has slipped about {rate:.1%} a day for {days} days since the panels were last cleaned, "
              "and is now {loss:.0%} below this roof's normal. Not washing would lose about ₹{saved} {until}; "
              "a wash costs ₹{cost}, so washing now leaves you about ₹{ahead} ahead.{storm}",
        "hi": "पिछली सफ़ाई के बाद {days} दिन से बिजली उत्पादन रोज़ लगभग {rate:.1%} घट रहा है और अब इस छत के "
              "सामान्य स्तर से {loss:.0%} कम है। न धोने पर {until} लगभग ₹{saved} का नुक़सान होगा; "
              "एक धुलाई ₹{cost} की है, इसलिए अभी धोने से आप लगभग ₹{ahead} फ़ायदे में रहेंगे।{storm}",
    },
    "until_rain": {"en": "before the rain on {on:%A}", "hi": "{on:%A} की बारिश से पहले"},
    "until_dust_storm": {"en": "before the dust storm on {on:%A}", "hi": "{on:%A} की आँधी से पहले"},
    "until_dry": {"en": "over the next {n} days if it stays dry", "hi": "अगले {n} दिनों में (अगर बारिश न हुई तो)"},
    "storm_after": {
        "en": " The storm will mean washing again afterwards either way.",
        "hi": " आँधी के बाद पैनल दोबारा धोने ही पड़ेंगे।",
    },
    "wait_rain": {
        "en": "Dust has cut output by about {loss:.0%} over {days} days, but rain is forecast on {on:%A} and will "
              "wash the panels for free. Until then you lose about ₹{saved}; a wash costs ₹{cost}. Waiting is "
              "₹{diff} cheaper.",
        "hi": "{days} दिनों में धूल से बिजली उत्पादन लगभग {loss:.0%} घटा है, लेकिन {on:%A} को बारिश का अनुमान है, "
              "जो पैनल मुफ़्त में धो देगी। तब तक लगभग ₹{saved} का नुक़सान होगा; एक धुलाई ₹{cost} की है। "
              "इंतज़ार करना ₹{diff} सस्ता है।",
    },
    "wait_dust_storm": {
        "en": "Dust has cut output by about {loss:.0%} over {days} days, but a dust storm is forecast on {on:%A} "
              "and would dirty the panels again. Wash now and again after it: ₹{twice}. Wait and wash once "
              "after it: ₹{saved} lost and ₹{cost} for the wash, ₹{total}. Waiting is ₹{diff} cheaper.",
        "hi": "{days} दिनों में धूल से बिजली उत्पादन लगभग {loss:.0%} घटा है, लेकिन {on:%A} को आँधी का अनुमान है, "
              "जो पैनल फिर गंदे कर देगी। अभी धोएँ और आँधी के बाद दोबारा: ₹{twice}। इंतज़ार करें और आँधी के बाद "
              "एक बार धोएँ: ₹{saved} का नुक़सान और धुलाई के ₹{cost}, कुल ₹{total}। इंतज़ार करना ₹{diff} सस्ता है।",
    },
    "not_worth_it": {
        "en": "Dust is costing about ₹{per_day} a day, {loss:.0%} of this roof's output: about ₹{saved} over "
              "the next {n} days. A wash costs ₹{cost}, so it is not worth it yet.{later}",
        "hi": "धूल से रोज़ लगभग ₹{per_day} का नुक़सान हो रहा है, यानी इस छत के उत्पादन का {loss:.0%}: अगले {n} दिनों "
              "में लगभग ₹{saved}। एक धुलाई ₹{cost} की है, इसलिए अभी धोना फ़ायदे का नहीं है।{later}",
    },
    "worth_it_later": {
        "en": " At this rate it will be in about {in_days} days.",
        "hi": " इसी रफ़्तार से लगभग {in_days} दिन में धोना फ़ायदे का हो जाएगा।",
    },
    "unclear": {
        "en": "Output is about {loss:.0%} below this roof's normal, but the pattern is not clear yet. "
              "Dhool will check again as more days come in.",
        "hi": "बिजली उत्पादन इस छत के सामान्य स्तर से लगभग {loss:.0%} कम है, लेकिन कारण अभी साफ़ नहीं है। "
              "और दिनों का डेटा आने पर Dhool फिर जाँचेगा।",
    },
}


class _HindiDate:
    """A date that fills `{day:%-d %b}` and `{on:%A}` with Hindi month and weekday names."""

    def __init__(self, date):
        self.date = date

    def __format__(self, spec):
        return self.date.strftime(spec.replace("%b", MONTHS_HI[self.date.month - 1]).replace("%A", WEEKDAYS_HI[self.date.weekday()]))


def say(key, **figures):
    """{"en": ..., "hi": ...} for one reason. A figure may itself be the result of `say()` (a part of the
    sentence that varies, such as "before the rain on Monday") and is then filled in language by language."""
    def fill(lang):
        values = {name: v[lang] if isinstance(v, dict) else _HindiDate(v) if lang == "hi" and hasattr(v, "strftime") else v
                  for name, v in figures.items()}
        return REASONS[key][lang].format(**values)
    return {"en": fill("en"), "hi": fill("hi")}
