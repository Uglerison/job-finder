"""Deterministic redaction of personal data before any AI request."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionReplacement:
    """Describe one category replaced in a redacted preview."""

    kind: str
    count: int
    token: str


@dataclass(frozen=True)
class RedactionResult:
    """Contain exactly the text that is safe to forward after redaction."""

    redacted_text: str
    replacements: list[RedactionReplacement]


_REDACTION_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "email",
        re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w-])", re.IGNORECASE),
        "[E-MAIL REMOVIDO]",
    ),
    (
        "phone",
        re.compile(r"(?<!\d)(?:\+?55\s*)?(?:\(\d{2}\)|\d{2})\s*9?\d{4}[-\s]?\d{4}(?!\d)"),
        "[TELEFONE REMOVIDO]",
    ),
    (
        "identifier",
        re.compile(
            r"(?<!\d)(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{11}|\d{14})(?!\d)"
        ),
        "[IDENTIFICADOR REMOVIDO]",
    ),
    (
        "address",
        re.compile(
            r"\b(?:rua|avenida|av\.|alameda|travessa|rodovia|estrada)\s+[^,\n]+,\s*\d+(?:\s*[-–]\s*[^.\n]+)?",
            re.IGNORECASE,
        ),
        "[ENDEREÇO REMOVIDO]",
    ),
)


def redact_personal_data(text: str) -> RedactionResult:
    """Replace supported personal-data patterns in a stable, explainable order."""

    redacted_text = text
    replacements: list[RedactionReplacement] = []
    for kind, pattern, token in _REDACTION_RULES:
        redacted_text, count = pattern.subn(token, redacted_text)
        if count:
            replacements.append(
                RedactionReplacement(kind=kind, count=count, token=token),
            )

    return RedactionResult(redacted_text=redacted_text, replacements=replacements)
