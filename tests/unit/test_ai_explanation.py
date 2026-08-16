from job_finder.ai_analysis import AnalysisEvidence, StructuredJobAnalysis
from job_finder.ai_explanation import build_explanation


def make_analysis() -> StructuredJobAnalysis:
    return StructuredJobAnalysis.model_validate(
        {
            "extraction": {
                "title": "Data Analyst",
                "company": "Example Labs",
                "location": "Brazil",
                "work_model": "remote",
                "contract_type": "full_time",
                "seniority": "mid",
                "salary_currency": None,
                "salary_minimum_monthly": None,
                "salary_maximum_monthly": None,
                "required_skills": ["SQL"],
                "responsibilities": ["Create dashboards"],
                "benefits": [],
            },
            "assessment": {
                "score": 82,
                "confidence": 90,
                "summary": "Boa aderência para análise de dados.",
                "strengths": ["Strong SQL skills are required."],
                "gaps": ["A vaga não informa salário."],
                "warnings": ["O modelo de trabalho precisa ser confirmado."],
                "evidence": [
                    {
                        "claim": "A vaga pede SQL.",
                        "quote": "Strong SQL skills are required.",
                        "source": "job_description",
                    },
                    {
                        "claim": "A vaga seria híbrida.",
                        "quote": "Hybrid work is available.",
                        "source": "job_description",
                    },
                ],
            },
        }
    )


def test_explanation_only_marks_claims_as_supported_when_their_quote_exists_in_source() -> None:
    explanation = build_explanation(
        make_analysis(),
        title="Data Analyst",
        company="Example Labs",
        location="Brazil",
        raw_content="Strong SQL skills are required. The role is remote in Brazil.",
    )

    assert [item.model_dump() for item in explanation.supported_evidence] == [
        {
            "claim": "A vaga pede SQL.",
            "quote": "Strong SQL skills are required.",
            "source": "job_description",
        }
    ]
    assert [item.model_dump() for item in explanation.unsupported_claims] == [
        {
            "category": "evidence",
            "citations": [],
            "status": "needs_review",
            "text": "A vaga seria híbrida.",
        }
    ]
    assert explanation.strengths[0].status == "supported"
    assert explanation.strengths[0].citations == ["Strong SQL skills are required."]
    assert explanation.gaps[0].status == "needs_review"
    assert explanation.gaps[0].citations == []
    assert explanation.warnings[0].status == "needs_review"
    assert explanation.summary.status == "needs_review"


def test_explanation_checks_the_declared_title_and_metadata_sources_too() -> None:
    analysis = make_analysis()
    analysis.assessment.evidence = [
        AnalysisEvidence.model_validate(
            {
            "claim": "O cargo é de analista de dados.",
            "quote": "Data Analyst",
            "source": "job_title",
            }
        ),
        AnalysisEvidence.model_validate(
            {
            "claim": "A empresa é Example Labs.",
            "quote": "Example Labs",
            "source": "job_metadata",
            }
        ),
    ]

    explanation = build_explanation(
        analysis,
        title="Data Analyst",
        company="Example Labs",
        location="Brazil",
        raw_content="A descrição não repete os metadados.",
    )

    assert len(explanation.supported_evidence) == 2
    assert explanation.unsupported_claims == []
