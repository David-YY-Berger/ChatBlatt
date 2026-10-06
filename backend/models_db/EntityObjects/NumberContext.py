# bs"d - lehagdil torah velahadir

from typing import List, Optional

from pydantic import BaseModel, Field


class NumberContext(BaseModel):
    """
    One context an ENumber was mentioned in (e.g. "korbanot on sukkot").
    An ENumber (same value + category + unit) keeps a list of these instead of being
    duplicated per context. source_keys lists the sources the number appeared in with
    this context, so each source can still be shown with its own context.
    """
    en_context: str                      # 1-6 word topic summary so the number is understandable out of context
    heb_context: Optional[str] = None    # Hebrew translation of en_context (filled by the enrichment pipeline)
    source_keys: List[str] = Field(default_factory=list)

    def matches(self, en_context: str) -> bool:
        return self.en_context.lower() == en_context.strip().lower()

    def merge(self, other: "NumberContext") -> bool:
        """Absorb other's source keys (and its heb_context, if this one has none). Returns True if changed."""
        changed = False
        for source_key in other.source_keys:
            if source_key not in self.source_keys:
                self.source_keys.append(source_key)
                changed = True
        if not self.heb_context and other.heb_context:
            self.heb_context = other.heb_context
            changed = True
        return changed
