# bs"d

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class RawLmmResponse:
    """Response object from LMM API calls."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        if self.success:
            return f"LmmResponse(success=True, content_length={len(self.content) if self.content else 0})"
        return f"LmmResponse(success=False, error={self.error})"
