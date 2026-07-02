# bs"d

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import pprint

@dataclass
class RawLmmResponse:
    """Response object from LMM API calls."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        metadata_str = pprint.pformat(self.metadata, indent=4, width=80)

        return (
            "RawLmmResponse(\n"
            f"  success: {self.success}\n"
            f"  content:\n    {self.content}\n"
            f"  error:\n    {self.error}\n"
            f"  metadata:\n{metadata_str}\n"
            ")"
        )
