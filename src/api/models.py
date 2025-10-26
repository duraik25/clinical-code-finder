from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class CodeResult(BaseModel):
    """Standardized code result across all systems"""
    code: str
    display: str
    system: str
    relevance_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class APIResponse(BaseModel):
    """Standardized API response wrapper"""
    success: bool
    results: List[CodeResult]
    error: Optional[str] = None
    search_metadata: Dict[str, Any] = Field(default_factory=dict)