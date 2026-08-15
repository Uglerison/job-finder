"""HTTP routes for previewing safe, redacted text before an AI request."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from job_finder.redaction import redact_personal_data

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


class RedactionRequest(BaseModel):
    """Text submitted only for a local redaction preview."""

    text: str = Field(min_length=1, max_length=20_000)


class ReplacementResponse(BaseModel):
    """Explain one category of data removed from the preview."""

    kind: str
    count: int
    token: str


class RedactionResponse(BaseModel):
    """Return the exact text eligible for a future AI request."""

    redacted_text: str
    replacements: list[ReplacementResponse]


@router.post("/redact", response_model=RedactionResponse)
def redact_preview(payload: RedactionRequest) -> RedactionResponse:
    """Redact personal data without persisting or forwarding the original text."""

    result = redact_personal_data(payload.text)
    return RedactionResponse(
        redacted_text=result.redacted_text,
        replacements=[
            ReplacementResponse.model_validate(item.__dict__) for item in result.replacements
        ],
    )
