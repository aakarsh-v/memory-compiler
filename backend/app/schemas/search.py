from typing import List, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    video_ids: Optional[List[str]] = Field(None, description="Optional list of video IDs to restrict the search")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of candidate intervals to return")
    threshold: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Optional minimum cosine similarity score")
    include_evidence: bool = Field(True, description="Whether to include supporting evidence frames in results")
    search_mode: str = Field("frame_semantic_v1", description="Retrieval mode: frame_semantic_v1, video_window_v1, or hybrid_v1")


class EvidenceItem(BaseModel):
    frame_id: str
    timestamp_seconds: float


class SearchResultItem(BaseModel):
    video_id: str
    filename: str
    start_seconds: float
    end_seconds: float
    evidence_timestamp_seconds: float
    thumbnail_url: str
    description: str = "Visually similar frame candidate"
    score: float
    score_type: str = "cosine_similarity"
    applied_constraints: List[str] = []
    evidence: List[EvidenceItem] = []


class SearchResponse(BaseModel):
    query: str
    search_mode: str = "frame_semantic_v1"
    results: List[SearchResultItem]
