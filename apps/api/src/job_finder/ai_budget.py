"""A small local budget guard that never blocks non-AI Job Finder operations."""

from dataclasses import dataclass
from decimal import Decimal
from threading import Lock

from job_finder.ai_usage import LunaPricing
from job_finder.settings import Settings


@dataclass(frozen=True)
class BudgetConfig:
    monthly_budget_usd: Decimal | None = None
    alert_percentages: tuple[int, ...] = (50, 80, 100)

    @classmethod
    def from_settings(cls, settings: Settings) -> "BudgetConfig":
        return cls(monthly_budget_usd=settings.openai_monthly_budget_usd)


@dataclass(frozen=True)
class BudgetState:
    budget_usd: float | None
    spent_usd: float
    percent: float
    alerts: tuple[int, ...]
    blocked: bool


class AiBudgetExceeded(RuntimeError):
    """Raised before a provider call when the configured monthly ceiling is reached."""


def evaluate_budget(
    spent_usd: float,
    config: BudgetConfig,
    *,
    already_alerted: tuple[int, ...] = (),
) -> BudgetState:
    """Compute threshold alerts deterministically; no budget means unlimited local use."""

    if config.monthly_budget_usd is None or config.monthly_budget_usd <= 0:
        return BudgetState(None, max(0.0, spent_usd), 0.0, (), False)
    budget = float(config.monthly_budget_usd)
    percent = max(0.0, spent_usd / budget * 100)
    alerts = tuple(
        threshold
        for threshold in config.alert_percentages
        if percent >= threshold and threshold not in already_alerted
    )
    return BudgetState(budget, max(0.0, spent_usd), percent, alerts, percent >= 100)


def pricing_from_settings(settings: Settings) -> LunaPricing:
    return LunaPricing(
        input_usd_per_million=settings.openai_input_price_usd_per_million,
        cached_input_usd_per_million=settings.openai_cached_input_price_usd_per_million,
        output_usd_per_million=settings.openai_output_price_usd_per_million,
    )


AI_BUDGET_LOCK = Lock()
