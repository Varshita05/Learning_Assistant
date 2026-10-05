from datetime import date

from learning_assistant import limits


def test_guest_question_allowance_is_once_per_ip_per_day(monkeypatch):
    monkeypatch.setattr(limits, "_guest_questions", {})
    monkeypatch.setattr(limits, "_utc_today", lambda: date(2026, 10, 5))

    assert limits.allow_guest_question("192.0.2.1")
    assert not limits.allow_guest_question("192.0.2.1")
    assert limits.allow_guest_question("192.0.2.2")


def test_guest_question_allowance_resets_on_new_utc_day(monkeypatch):
    monkeypatch.setattr(limits, "_guest_questions", {})
    current_date = date(2026, 10, 5)
    monkeypatch.setattr(limits, "_utc_today", lambda: current_date)
    assert limits.allow_guest_question("192.0.2.1")

    current_date = date(2026, 10, 6)

    assert limits.allow_guest_question("192.0.2.1")