from modules.utils.normalization import clean_optional_text, coerce_bool, normalize_choice, normalize_email


def test_normalize_email_trims_and_lowercases() -> None:
    assert normalize_email("  ANA@Example.COM ") == "ana@example.com"


def test_normalize_choice_keeps_first_uppercase_letter() -> None:
    assert normalize_choice(" b ") == "B"
    assert normalize_choice("c") == "C"


def test_coerce_bool_supports_common_spreadsheet_values() -> None:
    assert coerce_bool("sim", default=False) is True
    assert coerce_bool("0", default=True) is False
    assert coerce_bool("", default=True) is True


def test_clean_optional_text_returns_none_for_blank_values() -> None:
    assert clean_optional_text("   ") is None
    assert clean_optional_text("texto") == "texto"
