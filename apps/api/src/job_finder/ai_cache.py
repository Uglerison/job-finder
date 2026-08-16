"""Bounded process-local cache for stable, redacted analysis instructions."""

from collections import OrderedDict
from dataclasses import dataclass

from job_finder.ai_prompts import (
    ANALYSIS_PROMPT_VERSION,
    AnalysisMode,
    render_analysis_instructions,
)
from job_finder.profile_criteria import ProfileCriteria


@dataclass(frozen=True)
class CachedInstructions:
    value: str
    hit: bool


class AnalysisPromptCache:
    """Cache only profile-derived instructions; job text and API keys never enter it."""

    def __init__(self, max_entries: int = 128) -> None:
        self._max_entries = max(1, max_entries)
        self._items: OrderedDict[tuple[int, str, AnalysisMode], str] = OrderedDict()

    def get(
        self,
        profile_version_id: int,
        profile: ProfileCriteria,
        mode: AnalysisMode,
    ) -> CachedInstructions:
        key = (profile_version_id, ANALYSIS_PROMPT_VERSION, mode)
        value = self._items.get(key)
        if value is not None:
            self._items.move_to_end(key)
            return CachedInstructions(value=value, hit=True)
        value = render_analysis_instructions(profile)
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self._max_entries:
            self._items.popitem(last=False)
        return CachedInstructions(value=value, hit=False)

    def clear_profile(self, profile_version_id: int) -> None:
        for key in tuple(self._items):
            if key[0] == profile_version_id:
                self._items.pop(key, None)
