// The Hindi for every line of the app, by its English. Written by hand; no model translates anything while
// the app runs. "Dhool" stays in Latin letters: धूल is also the word for dust. The reasons that come with a
// verdict are not here: the server sends those in both languages (backend/dhool/reasons.py).
// i18n.test.js fails when a line used in the app is missing here, or a {name} does not match.
export const HI = {
  // Headlines (words.js)
  "Your solar has stopped": "आपका सोलर बंद हो गया है",
  "Call your vendor": "वेंडर को बुलाइए",
  "Wash the panels": "पैनल धो दीजिए",
  "Wait for the rain": "बारिश का इंतज़ार कीजिए",
  "Wash after the dust storm": "आँधी के बाद धोइए",
  "Not worth washing yet": "अभी धोना फ़ायदे का नहीं",
  "Don't wash. It's haze.": "मत धोइए। यह धुंध है।",
  "Wait and watch": "इंतज़ार कीजिए और नज़र रखिए",
  "Still learning your roof": "अभी आपकी छत को समझ रहा है",
  "Your solar is working": "आपका सोलर ठीक चल रहा है",

  // How sure
  "Dhool is sure about this.": "Dhool को इस पर पूरा भरोसा है।",
  "Dhool is fairly sure about this.": "Dhool को इस पर काफ़ी भरोसा है।",
  "Dhool is not sure yet.": "Dhool अभी पक्का नहीं है।",
  "Dhool is sure": "पूरा भरोसा",
  "Fairly sure": "काफ़ी भरोसा",
  "Not sure yet": "अभी पक्का नहीं",

  // Sign-in
  "Is your solar actually working?": "क्या आपका सोलर सच में काम कर रहा है?",
  "Your inverter app shows a number. Dhool tells you what your roof should have made, and what to do when it falls short.":
    "आपका इन्वर्टर ऐप सिर्फ़ एक नंबर दिखाता है। Dhool बताता है कि आपकी छत को कितनी बिजली बनानी चाहिए थी, और कम बनने पर क्या करना है।",
  "Code from your email": "ईमेल पर आया कोड",
  "Sent to {email}": "{email} पर भेजा गया",
  "Email": "ईमेल",
  "Password": "पासवर्ड",
  "At least 8 characters, with a capital letter, a number and a symbol": "कम से कम 8 अक्षर, जिनमें एक बड़ा अक्षर, एक अंक और एक चिह्न हो",
  "One moment…": "एक पल…",
  "Sign in": "साइन इन",
  "Create account": "खाता बनाइए",
  "Confirm and sign in": "पुष्टि करके साइन इन कीजिए",
  "New here? Create an account": "नए हैं? खाता बनाइए",
  "Already have an account? Sign in": "पहले से खाता है? साइन इन कीजिए",

  // Add a home
  "Add your home": "अपना घर जोड़िए",
  "Dhool needs to know where your roof is and how big the system is. That is all.": "Dhool को बस यह जानना है कि आपकी छत कहाँ है और सिस्टम कितना बड़ा है।",
  "Name for this home": "इस घर का नाम",
  "Sharma house": "शर्मा निवास",
  "System size": "सिस्टम का आकार",
  "It is on your installation papers and in your inverter app.": "यह आपके इंस्टॉलेशन के काग़ज़ों और इन्वर्टर ऐप में लिखा होता है।",
  "Latitude": "अक्षांश",
  "Longitude": "देशांतर",
  "Use my location": "मेरी लोकेशन इस्तेमाल कीजिए",
  "Location is off for this site. Type the two numbers in, or allow location and try again.":
    "इस साइट के लिए लोकेशन बंद है। दोनों नंबर ख़ुद लिखिए, या लोकेशन की अनुमति देकर फिर कोशिश कीजिए।",
  "Saving…": "सेव हो रहा है…",
  "Add home": "घर जोड़िए",
  "Someone at home already uses Dhool?": "घर में कोई पहले से Dhool इस्तेमाल करता है?",
  "Family code": "परिवार का कोड",
  "Ask them for the six-letter code from their Dhool app.": "उनसे उनके Dhool ऐप का छह अक्षरों वाला कोड माँगिए।",
  "Join their home": "उनके घर से जुड़िए",
  "Back": "वापस",

  // The message to the vendor
  "Namaste,": "नमस्ते,",
  "Our rooftop solar system ({name}) is producing much less than it should.": "हमारा रूफ़टॉप सोलर सिस्टम ({name}) जितनी बिजली बनानी चाहिए उससे काफ़ी कम बना रहा है।",
  "In the week to {date} it made about {made} units a day, where it normally makes {normal} in that weather.":
    "{date} तक के हफ़्ते में इसने रोज़ लगभग {made} यूनिट बनाईं, जबकि ऐसे मौसम में यह आम तौर पर {normal} यूनिट बनाता है।",
  "Please send someone to inspect it under the maintenance that comes with the installation.": "कृपया इंस्टॉलेशन के साथ मिली मेंटेनेंस के तहत किसी को जाँच के लिए भेजिए।",
  "Thank you.": "धन्यवाद।",

  // Roof tab
  "No new reading for {n} days": "{n} दिन से नई रीडिंग नहीं आई",
  "The last reading Dhool has is from {date}. What you see below is from that day.": "Dhool के पास आख़िरी रीडिंग {date} की है। नीचे जो दिख रहा है वह उसी दिन का है।",
  "Your inverter may be offline. Check that it is switched on and that its Wi-Fi stick is connected.":
    "हो सकता है आपका इन्वर्टर ऑफ़लाइन हो। देखिए कि वह चालू है और उसकी Wi-Fi स्टिक जुड़ी हुई है।",
  "Add a new reading to bring this up to date.": "इसे ताज़ा करने के लिए नई रीडिंग जोड़िए।",
  "Add a reading": "रीडिंग जोड़िए",
  "No connection. This is the last result Dhool has, from {when}.": "इंटरनेट नहीं है। यह Dhool के पास का आख़िरी नतीजा है, {when} का।",
  "Nothing made on {date}": "{date} को बिजली नहीं बनी",
  "Nothing made for {n} days, since {date}": "{date} से {n} दिन बिजली नहीं बनी",
  "Fell {pct}% on {date}": "{date} को {pct}% गिरा",
  "{n} sharp dips this month": "इस महीने {n} बार अचानक गिरावट",
  "Air at PM2.5 {pm}": "हवा में PM2.5 {pm}",
  "{rate}% a day for {days} days": "{days} दिन से रोज़ {rate}%",
  "Not enough days yet": "अभी काफ़ी दिन नहीं हुए",
  "The last 90 days": "पिछले 90 दिन",
  "Needs two weeks of readings": "दो हफ़्ते की रीडिंग चाहिए",
  "About ₹{rs} a week lost": "हर हफ़्ते लगभग ₹{rs} का नुक़सान",
  "Nothing to fix": "कुछ ठीक करने की ज़रूरत नहीं",
  "Running at {pct}% of this roof's normal": "इस छत के सामान्य स्तर के {pct}% पर चल रहा है",
  "Today": "आज",
  "Next rain": "अगली बारिश",
  "None": "नहीं",
  "Units possible": "संभव यूनिट",
  "Last reading": "पिछली रीडिंग",
  "Output compared with this roof's normal": "इस छत के सामान्य स्तर के मुक़ाबले बिजली उत्पादन",
  "Message your vendor on WhatsApp": "वेंडर को WhatsApp पर संदेश भेजिए",
  "Wash early in the morning or after sunset, with plain water and a soft cloth. Never on hot panels.":
    "सुबह जल्दी या सूरज ढलने के बाद, सादे पानी और मुलायम कपड़े से धोइए। गरम पैनलों पर कभी नहीं।",
  "Next 7 days": "अगले 7 दिन",
  "{likely} of {possible} units likely": "{possible} में से {likely} यूनिट की उम्मीद",
  "No forecast yet": "अभी अनुमान नहीं",
  "Why": "क्यों",

  // Forecast and Why tabs
  "The next 7 days": "अगले 7 दिन",
  "Why Dhool says this": "Dhool ऐसा क्यों कहता है",
  "Should have made": "बनानी चाहिए थी",
  "Made": "बनाई",
  "units": "यूनिट",
  "A day, on average, in the week to {date}.": "{date} तक के हफ़्ते में रोज़ का औसत।",
  " “Should have made” is what this roof normally makes in that weather.": " “बनानी चाहिए थी” वह है जो यह छत ऐसे मौसम में आम तौर पर बनाती है।",
  "About {amount} is being lost ({units} units a day, {tariff}).": "हर हफ़्ते {amount} का नुक़सान हो रहा है (रोज़ {units} यूनिट, {tariff})।",
  "₹{rs} a week": "लगभग ₹{rs}",
  "at ₹{rs} a unit": "₹{rs} प्रति यूनिट की दर से",
  "{sure} Reading from {date}.": "{sure} रीडिंग {date} की है।",
  "Daily output from {from} to {to}. On the last day the roof should have made {expected} units and made {made}.":
    "{from} से {to} तक रोज़ का बिजली उत्पादन। आख़िरी दिन छत को {expected} यूनिट बनानी चाहिए थीं; बनीं: {made}।",
  "no reading": "कोई रीडिंग नहीं",
  "Rain that washes panels": "पैनल धोने वाली बारिश",
  "No forecast yet. It appears with the next reading.": "अभी अनुमान नहीं। अगली रीडिंग के साथ आ जाएगा।",
  "About {likely} units likely.": "लगभग {likely} यूनिट की उम्मीद।",
  "About {likely} units likely, out of {possible} this roof could make in this weather if it were clean and healthy.":
    "लगभग {likely} यूनिट की उम्मीद, जबकि साफ़ और ठीक हालत में यह छत इस मौसम में {possible} बना सकती है।",
  "Likely": "उम्मीद",
  "Possible if clean and healthy": "साफ़ और ठीक हो तो संभव",
  "Sunny": "धूप",
  "Cloudy": "बादल",
  "Rain": "बारिश",

  // The roof picture
  "Rooftop solar array with {n} of {cols} columns dark": "छत का सोलर ऐरे, {cols} में से {n} कॉलम बंद",
  "Rooftop solar array switching off and on": "छत का सोलर ऐरे, बार-बार बंद और चालू होता हुआ",
  "Rooftop solar array covered in dust": "धूल से ढका छत का सोलर ऐरे",
  "Rooftop solar array under hazy air": "धुंध भरी हवा में छत का सोलर ऐरे",
  "Rooftop solar array, fully lit": "छत का सोलर ऐरे, पूरी तरह चालू",
  "Rooftop solar array, still being measured": "छत का सोलर ऐरे, अभी मापा जा रहा है",

  // Setup: readings
  "Reading your screenshot: about a minute. Stay on this page.": "आपका स्क्रीनशॉट पढ़ा जा रहा है: लगभग एक मिनट। इसी पेज पर रहिए।",
  "Still reading. After a quiet spell the reader starts up first, which can take up to five minutes.":
    "अभी पढ़ रहा है। काफ़ी देर बाद इस्तेमाल होने पर रीडर पहले चालू होता है, जिसमें पाँच मिनट तक लग सकते हैं।",
  "Type the number instead": "इसकी जगह नंबर लिखिए",
  "The upload did not go through. Check the image is under 5 MB, then try again.": "अपलोड नहीं हो पाया। देखिए कि तस्वीर 5 MB से छोटी है, फिर कोशिश कीजिए।",
  "demo inverter app": "डेमो इन्वर्टर ऐप",
  "How should Dhool get your readings?": "Dhool आपकी रीडिंग कैसे ले?",
  "Upload a screenshot": "स्क्रीनशॉट अपलोड कीजिए",
  "A screenshot of your inverter app showing the units made each day: today's figure, or a list of days. Dhool reads the numbers printed on it; it does not guess from charts. Try it with a screen saved from the {app}.":
    "आपके इन्वर्टर ऐप का स्क्रीनशॉट जिसमें हर दिन बनी यूनिट दिखें: आज का आँकड़ा, या दिनों की सूची। Dhool उस पर छपे नंबर पढ़ता है; चार्ट देखकर अंदाज़ा नहीं लगाता। {app} से सेव की गई स्क्रीन के साथ आज़माइए।",
  "Dhool read {days} from your screenshot. Check them against it. Correct any number that is wrong, or clear a box to leave that day out.":
    "Dhool ने आपके स्क्रीनशॉट से {days} की रीडिंग पढ़ी। इसे स्क्रीनशॉट से मिलाइए। जो नंबर ग़लत हो उसे ठीक कीजिए, या किसी दिन को छोड़ने के लिए उसका बॉक्स ख़ाली कर दीजिए।",
  "1 day": "1 दिन",
  "{n} days": "{n} दिन",
  "Readings found in the screenshot": "स्क्रीनशॉट में मिली रीडिंग",
  "These are right. Save them": "ये सही हैं। सेव कीजिए",
  "Not right? Choose another image": "सही नहीं? दूसरी तस्वीर चुनिए",
  "Choose a screenshot": "स्क्रीनशॉट चुनिए",
  "Dhool could not read daily units from that image. Try a screen where the number is printed, or type it in.":
    "Dhool उस तस्वीर से रोज़ की यूनिट नहीं पढ़ पाया। ऐसी स्क्रीन आज़माइए जिस पर नंबर छपा हो, या ख़ुद लिख दीजिए।",
  "Connect your inverter": "अपना इन्वर्टर जोड़िए",
  "Dhool then reads every day on its own. Copy your API key from the {app}. It holds simulated homes, not a real inverter brand.":
    "फिर Dhool हर दिन की रीडिंग ख़ुद ले लेता है। अपनी API key {app} से कॉपी कीजिए। उसमें सिम्युलेटेड घर हैं, कोई असली इन्वर्टर ब्रांड नहीं।",
  "API key from your inverter app": "आपके इन्वर्टर ऐप की API key",
  "Connect": "जोड़िए",
  "Or type today's number": "या आज का नंबर लिखिए",
  "Date": "तारीख़",
  "Units made (kWh)": "बनी यूनिट (kWh)",
  "Save reading": "रीडिंग सेव कीजिए",

  // Setup: costs, alerts, homes, family, language, sign out, deleting
  "Wash cost and electricity rate": "धुलाई का ख़र्च और बिजली की दर",
  "Electricity rate (₹ per unit)": "बिजली की दर (₹ प्रति यूनिट)",
  "It is on your electricity bill. Dhool uses it to work out the money lost.": "यह आपके बिजली के बिल पर लिखी होती है। Dhool इसी से नुक़सान का हिसाब लगाता है।",
  "Alerts on this phone": "इस फ़ोन पर सूचनाएँ",
  "Dhool will tell you when it is time to call the vendor, when it is time to wash, and when readings have stopped.":
    "Dhool आपको बताएगा जब वेंडर को बुलाने का समय हो, जब धोने का समय हो, और जब रीडिंग आनी बंद हो जाएँ।",
  "Alerts": "सूचनाएँ",
  "On": "चालू",
  "Off": "बंद",
  "Notifications are blocked for this site. Allow them in your browser's settings, then try again.":
    "इस साइट के लिए सूचनाएँ बंद हैं। ब्राउज़र की सेटिंग में अनुमति देकर फिर कोशिश कीजिए।",
  "Your homes": "आपके घर",
  "Show this home": "यह घर दिखाइए",
  "Add another home": "एक और घर जोड़िए",
  "Who is in this home": "इस घर में कौन-कौन है",
  "You": "आप",
  "Family member": "परिवार का सदस्य",
  "Family member, joined {date}": "परिवार का सदस्य, {date} को जुड़े",
  "Remove": "हटाइए",
  "Remove this family member? They will no longer see this home.": "इस सदस्य को हटाएँ? फिर वे यह घर नहीं देख पाएँगे।",
  "Delete this home": "यह घर मिटाइए",
  "Delete {name}? Its readings and screenshots are deleted for everyone in the family. This cannot be undone.":
    "{name} मिटाएँ? इसकी रीडिंग और स्क्रीनशॉट परिवार के सभी लोगों के लिए मिट जाएँगे। इसे वापस नहीं लाया जा सकता।",
  "You joined this home with a family code.": "आप इस घर से परिवार के कोड से जुड़े हैं।",
  "Leave this home": "यह घर छोड़िए",
  "Leave {name}? You will no longer see its readings and advice.": "{name} छोड़ें? फिर आप इसकी रीडिंग और सलाह नहीं देख पाएँगे।",
  "Delete my account": "मेरा खाता मिटाइए",
  "What Dhool keeps about you": "Dhool आपके बारे में क्या रखता है",
  "Your email, to sign you in. Your home's name, its system size and its location to about 1 km, to look up the weather over it. The readings you add or your inverter sends, the washes and vendor visits you report, and the advice Dhool gave. Screenshots are deleted after 30 days. A vendor's reply you paste is read and not kept.":
    "आपका ईमेल, साइन इन के लिए। आपके घर का नाम, सिस्टम का साइज़ और लगभग 1 किमी तक की जगह, वहाँ का मौसम देखने के लिए। जो रीडिंग आप जोड़ते हैं या आपका इन्वर्टर भेजता है, जो धुलाई और वेंडर का आना आप बताते हैं, और Dhool की दी हुई सलाह। स्क्रीनशॉट 30 दिन बाद मिटा दिए जाते हैं। वेंडर का जो जवाब आप पेस्ट करते हैं वह पढ़ा जाता है, रखा नहीं जाता।",
  "Nothing is sold or shared. The location, with no name on it, goes to the weather service (Open-Meteo); everything else stays on Dhool's servers on AWS in Mumbai. Everyone you give your family code to sees the home.":
    "कुछ भी बेचा या साझा नहीं किया जाता। जगह, बिना किसी नाम के, मौसम सेवा (Open-Meteo) को जाती है; बाक़ी सब मुंबई में AWS पर Dhool के सर्वर पर रहता है। जिसे भी आप परिवार का कोड देते हैं, वह यह घर देख सकता है।",
  "The owner can delete a home with everything in it, and anyone can delete their account, in Setup.":
    "घर का मालिक सेटअप में घर को उसकी हर चीज़ के साथ मिटा सकता है, और कोई भी अपना खाता मिटा सकता है।",
  "Even in its best weeks this roof makes far less than a system of its size should. If the size in Setup is right, it may have been shaded, dirty or faulty since before Dhool started watching: have it checked once.":
    "अपने सबसे अच्छे हफ़्तों में भी यह छत इस साइज़ के सिस्टम से बहुत कम बिजली बनाती है। अगर सेटअप में साइज़ सही है, तो हो सकता है Dhool के देखना शुरू करने से पहले से इस पर छाया, धूल या कोई ख़राबी हो: एक बार जाँच करवा लीजिए।",
  "You are the owner of {names}. Delete the home first, then your account.": "{names} के मालिक आप हैं। पहले घर मिटाइए, फिर अपना खाता।",
  "This removes your sign-in for good. You leave every home you have joined; the homes and their readings stay for the others.":
    "इससे आपका साइन इन हमेशा के लिए हट जाएगा। आप जिन घरों से जुड़े हैं वे सब छूट जाएँगे; घर और उनकी रीडिंग बाक़ी लोगों के लिए बनी रहेंगी।",
  "Delete your Dhool account? This cannot be undone.": "अपना Dhool खाता मिटाएँ? इसे वापस नहीं लाया जा सकता।",
  "Cost of one wash (₹)": "एक धुलाई का ख़र्च (₹)",
  "What you pay a cleaner, or about ₹50 for water and your time if you wash them yourself. Dhool tells you to wash only when the dust is costing more than this before the next rain or dust storm.":
    "जो आप सफ़ाई वाले को देते हैं, या ख़ुद धोते हैं तो पानी और समय के लगभग ₹50। Dhool धोने को तभी कहता है जब अगली बारिश या आँधी से पहले धूल का नुक़सान इससे ज़्यादा हो।",
  "Save": "सेव कीजिए",
  "Share with your family": "अपने परिवार के साथ साझा कीजिए",
  "Family code {code}": "परिवार का कोड {code}",
  "Works for 7 days. Anyone who joins sees this home's readings and verdicts.": "7 दिन तक चलता है। जो भी जुड़ेगा, वह इस घर की रीडिंग और सलाह देख सकेगा।",
  "Join our home on Dhool with this code: {code}": "इस कोड से Dhool पर हमारे घर से जुड़िए: {code}",
  "Send on WhatsApp": "WhatsApp पर भेजिए",
  "Get a family code": "परिवार का कोड बनाइए",
  "Language": "भाषा",
  "Sign out": "साइन आउट",

  // Navigation and waiting
  "Roof": "छत",
  "Forecast": "अनुमान",
  "Setup": "सेटअप",
  "Sections": "हिस्से",
  "Working it out": "हिसाब लगाया जा रहा है",
  "Checking the sun, clouds and rain over your roof for each day. This takes about 20 seconds.":
    "हर दिन के लिए आपकी छत पर धूप, बादल और बारिश देखी जा रही है। इसमें लगभग 20 सेकंड लगते हैं।",
  "Loading your home…": "आपका घर लोड हो रहा है…",
  "Loading…": "लोड हो रहा है…",
  "Try again": "फिर कोशिश कीजिए",

  // After a wash or a vendor visit (check.jsx)
  "Checking your wash": "आपकी धुलाई की जाँच हो रही है",
  "Washing worked": "धुलाई काम आई",
  "Washing did not help": "धुलाई से फ़ायदा नहीं हुआ",
  "Nothing to win back": "वापस पाने को कुछ नहीं था",
  "Checking the repair": "मरम्मत की जाँच हो रही है",
  "The repair worked": "मरम्मत काम आई",
  "Still not fixed": "अब भी ठीक नहीं हुआ",
  "You washed the panels": "आपने पैनल धोए",
  "The vendor visited": "वेंडर आया",
  "{did} on {date}. Dhool compares the week before with three clear days after: {n} so far.":
    "{date} को {did}। Dhool पहले के हफ़्ते की तुलना बाद के तीन साफ़ दिनों से करता है: अब तक {n}।",
  "{did} on {date}, but the roof was already at its normal, so there was nothing to gain.":
    "{date} को {did}, लेकिन छत पहले से अपने सामान्य स्तर पर थी, इसलिए फ़ायदे की गुंजाइश नहीं थी।",
  "{did} on {date}. Getting back to this roof's normal needed {needed}; the days after show {got}.":
    "{date} को {did}। इस छत के सामान्य स्तर पर लौटने के लिए {needed} चाहिए था; बाद के दिनों में {got} दिखा।",
  "Before and after": "पहले और बाद",
  "Needed": "चाहिए था",
  "Came back": "वापस आया",
  "Recorded by mistake? Remove it": "ग़लती से दर्ज हुआ? हटा दीजिए",
  "I washed the panels": "मैंने पैनल धो दिए",
  "The vendor has visited": "वेंडर आ चुका है",
  "When did you wash them?": "आपने कब धोए?",
  "When did the vendor come?": "वेंडर कब आया?",
  "Dhool will compare the week before with the clear days after, and tell you whether it worked.":
    "Dhool पहले के हफ़्ते की तुलना बाद के साफ़ दिनों से करेगा और बताएगा कि फ़ायदा हुआ या नहीं।",
  "Save and check": "सेव करके जाँचिए",

  // The vendor's reply
  "They are coming": "वे आ रहे हैं",
  "Good. Once they have been, press “The vendor has visited” below and Dhool will check that the repair worked.":
    "अच्छा है। उनके आ जाने के बाद नीचे “वेंडर आ चुका है” दबाइए, और Dhool जाँचेगा कि मरम्मत काम आई या नहीं।",
  "They want something first": "उन्हें पहले कुछ चाहिए",
  "Send what they asked for: usually a photo of the inverter screen, the model or error code, your address, or a yes to a visit charge. The inverter app's error code helps most.":
    "जो माँगा है वह भेजिए: अक्सर इन्वर्टर की स्क्रीन की फ़ोटो, मॉडल या एरर कोड, आपका पता, या विज़िट शुल्क के लिए हाँ। इन्वर्टर ऐप का एरर कोड सबसे ज़्यादा काम आता है।",
  "They won't help": "वे मदद नहीं करेंगे",
  "Ask again in writing and mention the maintenance that came with the installation. If they still refuse, your installer's company or your electricity distributor's rooftop solar cell is the next step.":
    "लिखकर दोबारा कहिए और इंस्टॉलेशन के साथ मिली मेंटेनेंस का ज़िक्र कीजिए। फिर भी मना करें, तो अगला क़दम इंस्टॉलर की कंपनी या आपकी बिजली वितरण कंपनी का रूफ़टॉप सोलर सेल है।",
  "No clear answer": "साफ़ जवाब नहीं",
  "They have not said they will come. Ask for a day and a time.": "उन्होंने आने की बात नहीं कही है। दिन और समय पूछिए।",
  "Got a reply from the vendor? Paste it here": "वेंडर का जवाब आया? यहाँ पेस्ट कीजिए",
  "Reading…": "पढ़ रहा है…",
  "What does it mean?": "इसका क्या मतलब है?",
  "What the reply says": "जवाब क्या कहता है",
  "Dhool reads this as: ": "Dhool इसे ऐसे समझता है: ",
  " Not right? Pick another above.": " सही नहीं? ऊपर से दूसरा चुनिए।",
  "{name}.": "{name}।",

  // The log (plan.jsx)
  "It worked.": "फ़ायदा हुआ।",
  "Output did not come back.": "बिजली उत्पादन वापस नहीं आया।",
  "Dhool is still measuring.": "Dhool अभी माप रहा है।",
  "The roof was already at its normal.": "छत पहले से अपने सामान्य स्तर पर थी।",
  "What Dhool said, and what you did": "Dhool ने क्या कहा, और आपने क्या किया",
  "Dhool said: {what}": "Dhool ने कहा: {what}",
  " ({pct}% down)": " ({pct}% कम)",

  // Messages that come from the server or from sign-in, shown as they arrive (ErrorLine). Any other
  // message stays in English.
  "Please sign in again": "कृपया फिर साइन इन कीजिए",
  "Something went wrong. Try again.": "कुछ गड़बड़ हो गई। फिर कोशिश कीजिए।",
  "Something went wrong": "कुछ गड़बड़ हो गई",
  "You can be in up to 5 homes. Leave or delete one first.": "आप ज़्यादा से ज़्यादा 5 घरों में हो सकते हैं। पहले कोई एक छोड़िए या मिटाइए।",
  "This home already has 10 people. Ask its owner to remove someone first.": "इस घर में पहले से 10 लोग हैं। घर के मालिक से कहिए कि पहले किसी को हटाएँ।",
  "Sign-in failed": "साइन इन नहीं हो पाया",
  "Incorrect username or password.": "ईमेल या पासवर्ड ग़लत है।",
  "Not allowed": "इसकी अनुमति नहीं है",
  "Invite code not found or expired": "कोड नहीं मिला या उसका समय निकल गया",
  "date cannot be in the future": "तारीख़ आगे की नहीं हो सकती",
  "Dhool could not read the reply just now. Pick what it says below.": "Dhool अभी जवाब नहीं पढ़ पाया। नीचे से चुनिए कि उसमें क्या लिखा है।",
  "The screenshot must be a PNG or JPEG image": "स्क्रीनशॉट PNG या JPEG तस्वीर होनी चाहिए",
  "That API key did not work. Copy it again from your inverter app.": "यह API key नहीं चली। अपने इन्वर्टर ऐप से दोबारा कॉपी कीजिए।",
  "No connection. Check your internet and try again.": "इंटरनेट नहीं है। कनेक्शन देखकर फिर कोशिश कीजिए।",
  "Too many wrong codes. Try again in an hour.": "बहुत बार ग़लत कोड डाला गया। एक घंटे बाद फिर कोशिश कीजिए।",
  "The owner cannot leave. Delete the home instead.": "घर का मालिक घर नहीं छोड़ सकता। इसकी जगह घर मिटाइए।",
  "This browser's notifications are not supported.": "इस ब्राउज़र की सूचनाएँ काम नहीं करतीं।",
};

// Lines above that the app never writes out itself (they arrive in a variable), so the test does not expect to find them in the source.
export const ARRIVES = [
  "Please sign in again", "Something went wrong. Try again.", "Something went wrong", "Sign-in failed",
  "Incorrect username or password.",
  "Not allowed", "Invite code not found or expired", "date cannot be in the future",
  "Dhool could not read the reply just now. Pick what it says below.", "The screenshot must be a PNG or JPEG image",
  "That API key did not work. Copy it again from your inverter app.", "No connection. Check your internet and try again.",
  "Too many wrong codes. Try again in an hour.", "The owner cannot leave. Delete the home instead.",
  "This browser's notifications are not supported.",
  "You can be in up to 5 homes. Leave or delete one first.",
  "This home already has 10 people. Ask its owner to remove someone first.",
];
