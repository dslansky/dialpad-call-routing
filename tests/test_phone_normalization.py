from src.phone_normalization import generate_phone_variants, normalize_phone_digits, to_e164_us


def test_normalize_phone_digits_strips_symbols() -> None:
    assert normalize_phone_digits("(480) 967-3528 x 1104") == "4809673528"


def test_to_e164_us_formats_ten_digit_number() -> None:
    assert to_e164_us("4809673528") == "+14809673528"


def test_generate_phone_variants_includes_common_forms() -> None:
    variants = generate_phone_variants("+1 (480) 967-3528")
    assert "4809673528" in variants
    assert "14809673528" in variants
    assert "+14809673528" in variants
