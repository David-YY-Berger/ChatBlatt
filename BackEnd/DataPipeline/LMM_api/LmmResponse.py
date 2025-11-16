# bs"d
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LmmResponse:
    """Response object from LMM API calls."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __str__(self):
        if self.success:
            return f"LmmResponse(success=True, content_length={len(self.content) if self.content else 0})"
        return f"LmmResponse(success=False, error={self.error})"
