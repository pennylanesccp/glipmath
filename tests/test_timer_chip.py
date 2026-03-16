from app.components.timer_chip import format_elapsed_time


def test_format_elapsed_time_formats_minutes_and_seconds() -> None:
    assert format_elapsed_time(0) == "00:00"
    assert format_elapsed_time(65.9) == "01:05"


def test_format_elapsed_time_formats_hours_when_needed() -> None:
    assert format_elapsed_time(3723) == "1:02:03"
