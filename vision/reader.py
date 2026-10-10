"""Reads a screenshot: plain OCR first, the vision model only when OCR finds nothing it can vouch for.

OCR (ocr_reader.py) answers in about a second and returns a number only when it is tied to a date or a "today"
label; in the trial it never returned a wrong one. The model (screenshot_reader.py) takes about a minute and
reads screens OCR cannot (tilted, an icon between label and figure). Same call and result as either.
"""
import ocr_reader
import screenshot_reader

def prime():
    screenshot_reader.prime()  # the model stays loaded for the screens OCR hands on


def read(image):
    try:
        result = ocr_reader.read(image)
        if result["readings"]:
            return result
    except Exception as e:  # OCR missing or broken must never cost the homeowner the read
        print(f'{{"vision": "ocr_failed", "error": "{type(e).__name__}"}}')
    return screenshot_reader.read(image)
