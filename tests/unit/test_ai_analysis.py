import pytest
from pydantic import ValidationError

from job_finder.ai_analysis import StructuredJobAnalysis


def valid_analysis_payload() -> dict[str, object]:
    return {
        "assessment": {
            "confidence": 82,
            "evidence": [
                {
                    "claim": "A vaga pede SQL.",
                    "quote": "Strong SQL skills are required.",
                    "source": "job_description",
                }
            ],
            "gaps": ["Não há informação sobre faixa salarial."],
            "score": 74,
            "summary": "Boa aderência para análise de dados, com local a confirmar.",
            "strengths": ["SQL e análise de dados aparecem explicitamente."],
            "warnings": ["Regime de trabalho não identificado."],
        },
        "extraction": {
            "benefits": ["Plano de saúde"],
            "company": "Example Labs",
            "contract_type": "full_time",
            "location": "Remote — Brazil",
            "required_skills": ["SQL", "Power BI"],
            "responsibilities": ["Criar dashboards"],
            "salary_currency": "BRL",
            "salary_maximum_monthly": 9000,
            "salary_minimum_monthly": 7000,
            "seniority": "mid",
            "title": "Data Analyst",
            "work_model": "remote",
        },
    }


def test_structured_job_analysis_accepts_a_complete_bounded_response() -> None:
    analysis = StructuredJobAnalysis.model_validate(valid_analysis_payload())

    assert analysis.assessment.score == 74
    assert analysis.assessment.evidence[0].source == "job_description"
    assert analysis.extraction.work_model == "remote"
    assert analysis.extraction.salary_minimum_monthly == 7000


def test_structured_job_analysis_rejects_missing_or_out_of_range_fields() -> None:
    missing_assessment = valid_analysis_payload()
    missing_assessment.pop("assessment")
    with pytest.raises(ValidationError):
        StructuredJobAnalysis.model_validate(missing_assessment)

    invalid_score = valid_analysis_payload()
    invalid_score["assessment"] = {
        **invalid_score["assessment"],
        "score": 101,
    }
    with pytest.raises(ValidationError, match="less than or equal to 100"):
        StructuredJobAnalysis.model_validate(invalid_score)

    missing_extraction_field = valid_analysis_payload()
    missing_extraction_field["extraction"] = {
        key: value
        for key, value in missing_extraction_field["extraction"].items()
        if key != "salary_currency"
    }
    with pytest.raises(ValidationError, match="salary_currency"):
        StructuredJobAnalysis.model_validate(missing_extraction_field)


def test_structured_job_analysis_rejects_invalid_evidence_and_inconsistent_salary() -> None:
    invalid_evidence = valid_analysis_payload()
    invalid_evidence["assessment"] = {
        **invalid_evidence["assessment"],
        "evidence": [
            {
                "claim": "Sem citação utilizável.",
                "quote": "   ",
                "source": "profile",
            }
        ],
    }
    with pytest.raises(ValidationError):
        StructuredJobAnalysis.model_validate(invalid_evidence)

    inverted_salary = valid_analysis_payload()
    inverted_salary["extraction"] = {
        **inverted_salary["extraction"],
        "salary_minimum_monthly": 10000,
        "salary_maximum_monthly": 9000,
    }
    with pytest.raises(ValidationError, match="salary minimum cannot exceed maximum"):
        StructuredJobAnalysis.model_validate(inverted_salary)
