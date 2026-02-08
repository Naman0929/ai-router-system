from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class RouteType(str, Enum):
    FACT_FROM_DOCS = "FACT_FROM_DOCS"
    STRUCTURED_DATA = "STRUCTURED_DATA" 
    SMALL_TALK = "SMALL_TALK"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"

class Query(BaseModel):
    text: str
    user_id: Optional[str] = None

class RouteDecision(BaseModel):
    route: RouteType
    confidence: float
    reasoning: str

class RetrievalResult(BaseModel):
    chunks: List[str]
    confidence: float
    grounded: bool

class ToolCall(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]

class Response(BaseModel):
    answer: str
    confidence: float
    route_used: RouteType
    reasoning_trace: List[str]
    sources: Optional[List[str]] = None
    tool_calls: Optional[List[ToolCall]] = None
    query_id: Optional[str] = None

class Feedback(BaseModel):
    query_id: str
    rating: int  # 1 for thumbs up, -1 for thumbs down
    comment: Optional[str] = None