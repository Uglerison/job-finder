"""Versioned, deterministic prompt configuration for controlled job analysis."""

import json
from dataclasses import dataclass
from typing import Literal

from job_finder.profile_criteria import ProfileCriteria
from job_finder.redaction import redact_personal_data

ANALYSIS_PROMPT_VERSION = "2026-08-15.1"
AnalysisMode = Literal["batch", "detailed"]
ReasoningEffort = Literal["low", "medium"]


@dataclass(frozen=True)
class AnalysisConfiguration:
    """Version and deliberate reasoning budget for one local analysis operation."""

    version: str
    reasoning_effort: ReasoningEffort


def analysis_configuration(mode: AnalysisMode = "batch") -> AnalysisConfiguration:
    """Choose low effort for volume and medium only for an explicit detailed review."""

    return AnalysisConfiguration(
        version=ANALYSIS_PROMPT_VERSION,
        reasoning_effort="medium" if mode == "detailed" else "low",
    )


def render_analysis_instructions(profile: ProfileCriteria) -> str:
    """Render a stable instruction prefix without forwarding detectable personal data."""

    serialized_profile = json.dumps(
        profile.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    redacted_profile = redact_personal_data(serialized_profile).redacted_text
    return "\n".join(
        (
            "Você analisa uma vaga para orientar uma decisão humana de carreira.",
            f"Versão do prompt: {ANALYSIS_PROMPT_VERSION}.",
            "Use somente fatos presentes na vaga e no perfil redigido abaixo.",
            "Não invente requisitos, salário, regime, localização ou experiência.",
            "Não use atributos sensíveis para pontuar: idade, gênero, raça, religião, "
            "deficiência, estado civil, nacionalidade ou qualquer proxy desses atributos.",
            "Não use atributos sensíveis; quando faltar informação, informe como não especificada.",
            "Toda afirmação sobre a vaga deve ter evidência textual curta do anúncio.",
            "Para tratar um ponto como fato, repita no ponto uma citação exata da evidência.",
            "Retorne somente o objeto JSON compatível com o schema fornecido.",
            f"Perfil redigido: {redacted_profile}",
        )
    )
