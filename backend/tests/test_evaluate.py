"""The figures the score reports add under the accuracy line, on tables small enough to check by hand. No network."""
import inspect
from collections import Counter

import pytest

from dhool import evaluate, realcheck

# truth \ verdict   CLEAN  INSPECT  WAIT   OK
# CLEAN                 6        2     0    2   (10 happened)
# INSPECT               1        3     0    0   (4)
# WAIT                  0        0     0    0   (never happened, never said)
# OK                    3        1     0   12   (16)
# said                 10        6     0   14   (30 checks, 21 of them right)
TABLE = Counter({("CLEAN", "CLEAN"): 6, ("CLEAN", "INSPECT"): 2, ("CLEAN", "OK"): 2,
                 ("INSPECT", "CLEAN"): 1, ("INSPECT", "INSPECT"): 3,
                 ("OK", "CLEAN"): 3, ("OK", "INSPECT"): 1, ("OK", "OK"): 12})
# INSPECT happened and was never said, WAIT was said and never happened, CLEAN is nowhere.
LOPSIDED = Counter({("OK", "OK"): 8, ("OK", "WAIT"): 2, ("INSPECT", "OK"): 2})
# What evaluate.report() printed for TABLE before these figures were added: it must still come first, to the letter.
AS_BEFORE = """truth \\ verdict      CLEAN  INSPECT     WAIT       OK
CLEAN                    6        2        0        2
INSPECT                  1        3        0        0
WAIT                     0        0        0        0
OK                       3        1        0       12
CLEAN    precision 0.60  recall 0.60  (n=10)
INSPECT  precision 0.50  recall 0.75  (n=4)
WAIT     precision nan  recall nan  (n=0)
OK       precision 0.86  recall 0.75  (n=16)
accuracy 0.70 over 30 checks
"""


def test_baseline_is_the_commonest_true_class():
    assert evaluate.baseline(TABLE) == ("OK", pytest.approx(16 / 30))
    assert evaluate.baseline(Counter({("CLEAN", "CLEAN"): 1, ("OK", "OK"): 1})) == ("CLEAN", 0.5)  # a tie: first in CLASSES


def test_f1_per_class():
    assert evaluate.f1(TABLE, "CLEAN") == pytest.approx(0.6)  # 2 x 6 / (10 said + 10 happened)
    assert evaluate.f1(TABLE, "INSPECT") == pytest.approx(0.6)  # 2 x 3 / (6 + 4)
    assert evaluate.f1(TABLE, "OK") == pytest.approx(0.8)  # 2 x 12 / (14 + 16)


def test_a_class_that_never_occurs_has_no_f1_and_is_left_out_of_the_mean():
    assert evaluate.f1(TABLE, "WAIT") is None
    assert evaluate.macro_f1(TABLE) == pytest.approx((0.6 + 0.6 + 0.8) / 3)


def test_a_class_only_said_or_only_happening_scores_zero_and_counts():
    assert evaluate.f1(LOPSIDED, "INSPECT") == 0 and evaluate.f1(LOPSIDED, "WAIT") == 0
    assert evaluate.f1(LOPSIDED, "CLEAN") is None
    assert evaluate.macro_f1(LOPSIDED) == pytest.approx((0 + 0 + 0.8) / 3)  # OK: 2 x 8 / (10 + 10)


def test_false_and_wrong_action_alerts():
    assert evaluate.alert_counts(TABLE) == (4, 3)  # OK said CLEAN 3 + INSPECT 1; CLEAN said INSPECT 2 + INSPECT said CLEAN 1
    assert evaluate.alert_counts(LOPSIDED) == (0, 0)  # a wrong WAIT and a missed fault are not alerts
    assert evaluate.per_roof_month(4, 30) == pytest.approx(0.5798, abs=1e-4)  # 4 / 30 x 30.44 / 7
    assert evaluate.per_roof_month(30, 30, every=30.44) == pytest.approx(1)


def test_the_rate_uses_the_spacing_the_checks_are_made_at():
    assert inspect.signature(evaluate.evaluate).parameters["every"].default == evaluate.CHECK_EVERY


def test_report_keeps_its_old_lines_and_adds_the_new_ones_below():
    text = evaluate.report(TABLE)
    assert text.startswith(AS_BEFORE)
    added = text[len(AS_BEFORE):].splitlines()
    assert added[0].startswith("nan above:")  # the old lines do print nan; this says what it means
    assert not any("nan" in line for line in added[1:])
    assert "baseline 0.53: always saying OK" in added[1]
    assert added[2:6] == ["CLEAN    F1 0.60", "INSPECT  F1 0.60",
                          "WAIT     F1 none (never happened, never said: left out of macro-F1)", "OK       F1 0.80"]
    assert added[6].startswith("macro-F1 0.67: the plain mean of the 3 F1s")
    assert added[7].startswith("false alerts 0.58 per roof per month: 4 of 30 checks")
    assert added[-1].startswith("wrong-action alerts 3:")


def test_report_says_nothing_about_nan_when_none_is_printed():
    full = Counter({(t, v): 1 + 4 * (t == v) for t in evaluate.CLASSES for v in evaluate.CLASSES})
    assert "nan" not in evaluate.report(full)


def test_realcheck_counts_alerts_by_verdict_whatever_the_cause():
    said = Counter({"OK:ok": 5, "CLEAN:dust": 3, "INSPECT:fault": 1, "INSPECT:outage": 1, "WAIT:dust": 2})
    assert realcheck.alerts(said) == {"CLEAN": 3, "INSPECT": 2}
