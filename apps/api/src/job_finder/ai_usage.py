"""Local accounting for GPT-5.6 Luna usage and configurable pricing."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict

from job_finder.openai_client import OpenAiUsage


@dataclass(frozen=True)
class LunaPricing:
    """USD per million tokens; values are configurable so provider prices can change."""

    input_usd_per_million: Decimal = Decimal("0.20")
    cached_input_usd_per_million: Decimal = Decimal("0.02")
    output_usd_per_million: Decimal = Decimal("1.20")


class AnalysisUsage(BaseModel):
    """Auditable usage attached to each analysis, including unmetered fallbacks."""

    model_config = ConfigDict(extra="forbid")

    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    latency_ms: int = 0
    estimated_cost_usd: float | None = None
    metered: bool = False
    cache_hit: bool = False
    fallback: bool = False
    fallback_reason: str | None = None


class UsageSummary(BaseModel):
    """Aggregated local usage for the dashboard and budget guard."""

    operations: int
    metered_operations: int
    total_input_tokens: int
    total_cached_input_tokens: int
    total_output_tokens: int
    total_estimated_cost_usd: float
    average_latency_ms: int


DEFAULT_LUNA_PRICING = LunaPricing()


def usage_from_response(
    usage: OpenAiUsage,
    latency_ms: int,
    *,
    pricing: LunaPricing = DEFAULT_LUNA_PRICING,
    cache_hit: bool = False,
    fallback: bool = False,
    fallback_reason: str | None = None,
) -> AnalysisUsage:
    """Estimate cost only when provider returned enough counters to be honest."""

    input_tokens = usage.input_tokens
    cached_tokens = usage.cached_input_tokens
    output_tokens = usage.output_tokens
    cost: float | None = None
    if input_tokens is not None and output_tokens is not None:
        cached = min(cached_tokens or 0, input_tokens)
        billable_input = input_tokens - cached
        amount = (
            Decimal(billable_input) * pricing.input_usd_per_million
            + Decimal(cached) * pricing.cached_input_usd_per_million
            + Decimal(output_tokens) * pricing.output_usd_per_million
        ) / Decimal(1_000_000)
        cost = float(amount.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
    return AnalysisUsage(
        input_tokens=input_tokens,
        cached_input_tokens=cached_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=usage.reasoning_tokens,
        latency_ms=max(0, latency_ms),
        estimated_cost_usd=cost,
        metered=cost is not None and not fallback,
        cache_hit=cache_hit,
        fallback=fallback,
        fallback_reason=fallback_reason,
    )


def summarize_usage(records: Iterable[dict[str, object]]) -> UsageSummary:
    """Aggregate persisted usage records without exposing prompts or job content."""

    rows = [AnalysisUsage.model_validate(record) for record in records]
    metered = [row for row in rows if row.metered]
    latencies = [row.latency_ms for row in rows]
    return UsageSummary(
        operations=len(rows),
        metered_operations=len(metered),
        total_input_tokens=sum(row.input_tokens or 0 for row in rows),
        total_cached_input_tokens=sum(row.cached_input_tokens or 0 for row in rows),
        total_output_tokens=sum(row.output_tokens or 0 for row in rows),
        total_estimated_cost_usd=round(
            sum(row.estimated_cost_usd or 0.0 for row in rows),
            6,
        ),
        average_latency_ms=round(sum(latencies) / len(latencies)) if latencies else 0,
    )
