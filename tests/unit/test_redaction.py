from job_finder.redaction import redact_personal_data


def test_redaction_replaces_personal_data_with_a_stable_preview() -> None:
    text = (
        "Fale com Ana em ana.silva@example.com ou (11) 98765-4321. "
        "CPF 123.456.789-09. Rua das Flores, 123 - Centro."
    )

    result = redact_personal_data(text)

    assert result.redacted_text == (
        "Fale com Ana em [E-MAIL REMOVIDO] ou [TELEFONE REMOVIDO]. "
        "CPF [IDENTIFICADOR REMOVIDO]. [ENDEREÇO REMOVIDO]."
    )
    assert [replacement.kind for replacement in result.replacements] == [
        "email",
        "phone",
        "identifier",
        "address",
    ]
    assert [replacement.count for replacement in result.replacements] == [1, 1, 1, 1]
