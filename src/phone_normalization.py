from __future__ import annotations

import re


EXTENSION_PATTERN = re.compile(r"(ext\.?|x)\s*\d+$", re.IGNORECASE)
NON_DIGIT_PATTERN = re.compile(r"\D+")


def normalize_phone_digits(raw_phone: str | None) -> str:
    if not raw_phone:
        return ""
    without_extension = EXTENSION_PATTERN.sub("", raw_phone.strip())
    digits = NON_DIGIT_PATTERN.sub("", without_extension)
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:]
    return digits


def to_e164_us(raw_phone: str | None) -> str:
    digits = normalize_phone_digits(raw_phone)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return ""


def generate_phone_variants(raw_phone: str | None) -> set[str]:
    digits = normalize_phone_digits(raw_phone)
    variants: set[str] = set()
    if not digits:
        return variants

    variants.add(digits)
    if len(digits) == 10:
        variants.add(f"1{digits}")
        variants.add(f"+1{digits}")
    elif len(digits) == 11 and digits.startswith("1"):
        local_digits = digits[1:]
        variants.add(local_digits)
        variants.add(f"+{digits}")

    return {variant for variant in variants if variant}
