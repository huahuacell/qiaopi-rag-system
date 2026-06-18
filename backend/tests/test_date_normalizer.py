from app.utils.date_normalizer import normalize_qiaopi_date


def test_normalizes_gregorian_dates_to_display_format():
    for raw_value in ("1999年4月27日", "1999-04-27", "1999/04/27", "1999.04.27"):
        result = normalize_qiaopi_date(raw_value)

        assert result.date_standard == "1999.4.27"
        assert result.date_year == 1999
        assert result.date_month == 4
        assert result.date_day == 27
        assert result.date_precision == "day"
        assert result.date_calendar == "gregorian"
        assert result.date_parse_confidence == 1.0


def test_normalizes_roc_dates():
    for raw_value in ("民国22年9月11日", "民国二十二年九月十一日"):
        result = normalize_qiaopi_date(raw_value)

        assert result.date_standard == "1933.9.11"
        assert result.date_year == 1933
        assert result.date_month == 9
        assert result.date_day == 11
        assert result.date_precision == "day"
        assert result.date_calendar == "roc"
        assert result.date_parse_confidence >= 0.9


def test_normalizes_traditional_text_with_explicit_western_year_for_display_only():
    cases = {
        "癸(1933)九月十一日": "1933.9.11",
        "辛（1911）阳月初十日": "1911.10.10",
        "1933年九月十一日": "1933.9.11",
    }

    for raw_value, expected_standard in cases.items():
        result = normalize_qiaopi_date(raw_value)

        assert result.date_standard == expected_standard
        assert result.date_precision == "day"
        assert result.date_calendar == "traditional_lunar_text"
        assert "not converted to exact Gregorian calendar date" in result.date_parse_note


def test_preserves_partial_precision_without_inventing_missing_parts():
    year_only = normalize_qiaopi_date("1969")
    assert year_only.date_standard == "1969"
    assert year_only.date_precision == "year"
    assert year_only.date_month is None
    assert year_only.date_day is None

    year_month = normalize_qiaopi_date("1971年5月")
    assert year_month.date_standard == "1971.5"
    assert year_month.date_precision == "month"
    assert year_month.date_month == 5
    assert year_month.date_day is None

    month_day = normalize_qiaopi_date("九月十一日")
    assert month_day.date_standard == ""
    assert month_day.date_precision == "month_day_no_year"
    assert month_day.date_year is None
    assert month_day.date_month == 9
    assert month_day.date_day == 11
    assert "Missing year" in month_day.date_parse_note


def test_unknown_date_is_not_normalized():
    result = normalize_qiaopi_date("不详")

    assert result.date_standard == ""
    assert result.date_precision == "unknown"
    assert result.date_calendar == "unknown"
    assert result.date_parse_confidence == 0.0


def test_context_year_can_complete_traditional_text_when_year_is_explicit_in_title():
    result = normalize_qiaopi_date(
        "癸九月十一日",
        context_text="癸（1933）九月十一日，越姚丁南寄潮安南桂家母亲大人",
        year_hint="1933",
    )

    assert result.date_standard == "1933.9.11"
    assert result.date_year == 1933
    assert result.date_month == 9
    assert result.date_day == 11
    assert result.date_calendar == "traditional_lunar_text"
