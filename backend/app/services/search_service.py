import math
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ValidationException
from app.db.models import Video, Frame, VideoWindow
from app.ml.base import EmbeddingProvider
from app.services.temporal_parser import TemporalQueryParser, ParsedQuery
from app.services.constraint_evaluator import TemporalConstraintEvaluator
from app.schemas.search import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    EvidenceItem,
)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class SearchService:
    def __init__(self, db: Session, embedding_provider: EmbeddingProvider):
        self.db = db
        self.embedding_provider = embedding_provider
        self.parser = TemporalQueryParser()
        self.evaluator = TemporalConstraintEvaluator()

    def search(self, request: SearchRequest, owner_id: str) -> SearchResponse:
        query_text = request.query.strip()
        if not query_text:
            raise ValidationException("SEARCH_EMPTY_QUERY", "Search query cannot be empty")

        # 1. Parse query for temporal constraints (Phase 6)
        parsed_query = self.parser.parse(query_text)

        if parsed_query.has_constraints:
            # Multi-event or extremum temporal evaluation
            event_candidates = {}
            for ev in parsed_query.events:
                sub_req = SearchRequest(
                    query=ev.query,
                    video_ids=request.video_ids,
                    limit=request.limit,
                    threshold=request.threshold,
                    search_mode=request.search_mode
                )
                sub_resp = self._dispatch_mode(sub_req, owner_id, ev.query)
                event_candidates[ev.id] = sub_resp.results

            constrained_results = self.evaluator.evaluate_constraints(parsed_query, event_candidates)
            if constrained_results:
                return SearchResponse(
                    query=query_text,
                    search_mode="temporal_constraint_v1",
                    results=constrained_results[: request.limit]
                )
            # If constraint evaluation produced 0 pairs (e.g. order reversal or missing event),
            # fall back gracefully to plain semantic retrieval and flag constraints were not applied.

        # 2. Standard single-event retrieval (or graceful fallback)
        resp = self._dispatch_mode(request, owner_id, query_text)
        for r in resp.results:
            r.applied_constraints = []  # Explicitly flag that constraints were not applied
        return resp

    def _dispatch_mode(self, request: SearchRequest, owner_id: str, query_text: str) -> SearchResponse:
        mode = request.search_mode.lower()
        if mode == "video_window_v1":
            return self._search_video_windows(request, owner_id, query_text)
        elif mode == "hybrid_v1":
            return self._search_hybrid(request, owner_id, query_text)
        else:
            return self._search_frames(request, owner_id, query_text)

    def _search_frames(self, request: SearchRequest, owner_id: str, query_text: str) -> SearchResponse:
        query_vector = self.embedding_provider.embed_texts([query_text])[0]

        # 2. Query candidates restricted to owned and READY videos
        db_query = (
            self.db.query(Frame, Video)
            .join(Video, Frame.video_id == Video.id)
            .filter(
                Video.owner_id == owner_id,
                Video.status == "READY",
                Frame.embedding.isnot(None),
                Frame.embedding_model == self.embedding_provider.model_id
            )
        )

        if request.video_ids:
            db_query = db_query.filter(Video.id.in_(request.video_ids))

        rows = db_query.all()
        if not rows:
            return SearchResponse(query=query_text, search_mode="frame_semantic_v1", results=[])

        # 3. Score candidate frames
        scored_candidates = []
        for frame, video in rows:
            score = cosine_similarity(query_vector, frame.embedding)
            if request.threshold is not None and score < request.threshold:
                continue
            scored_candidates.append({
                "frame": frame,
                "video": video,
                "score": round(score, 4)
            })

        if not scored_candidates:
            return SearchResponse(query=query_text, search_mode="frame_semantic_v1", results=[])

        # 4. Group candidate frames by video and merge near-duplicate temporal intervals
        # Max gap between frames to merge into the same window: 2 * sample_interval
        merge_gap = settings.FRAME_SAMPLE_SECONDS * 2.0
        sample_half = settings.FRAME_SAMPLE_SECONDS / 2.0

        candidates_by_video: Dict[str, List[Dict[str, Any]]] = {}
        for item in scored_candidates:
            vid = item["video"].id
            candidates_by_video.setdefault(vid, []).append(item)

        merged_windows: List[SearchResultItem] = []

        for vid, items in candidates_by_video.items():
            # Sort frames chronologically by timestamp
            items.sort(key=lambda x: x["frame"].timestamp_seconds)
            video = items[0]["video"]
            duration = video.duration_seconds or 3600.0

            current_window: List[Dict[str, Any]] = [items[0]]

            for item in items[1:]:
                prev_ts = current_window[-1]["frame"].timestamp_seconds
                curr_ts = item["frame"].timestamp_seconds

                if (curr_ts - prev_ts) <= merge_gap:
                    current_window.append(item)
                else:
                    # Flush current window
                    merged_windows.append(self._build_window_result(current_window, video, sample_half, duration))
                    current_window = [item]

            if current_window:
                merged_windows.append(self._build_window_result(current_window, video, sample_half, duration))

        # 5. Sort candidate windows by best similarity score descending and take top-K
        merged_windows.sort(key=lambda w: w.score, reverse=True)
        top_k = merged_windows[: request.limit]

        return SearchResponse(
            query=query_text,
            search_mode="frame_semantic_v1",
            results=top_k
        )

    def _build_window_result(
        self,
        window_items: List[Dict[str, Any]],
        video: Video,
        sample_half: float,
        duration: float
    ) -> SearchResultItem:
        # Highest scoring frame in the window serves as the evidence anchor
        best_item = max(window_items, key=lambda x: x["score"])
        best_frame = best_item["frame"]

        min_ts = window_items[0]["frame"].timestamp_seconds
        max_ts = window_items[-1]["frame"].timestamp_seconds

        start_seconds = round(max(0.0, min_ts - sample_half), 2)
        end_seconds = round(min(duration, max_ts + sample_half), 2)

        evidence = [
            EvidenceItem(frame_id=it["frame"].id, timestamp_seconds=it["frame"].timestamp_seconds)
            for it in window_items
        ]

        return SearchResultItem(
            video_id=video.id,
            filename=video.filename,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            evidence_timestamp_seconds=best_frame.timestamp_seconds,
            thumbnail_url=f"/api/v1/frames/{best_frame.id}/thumbnail",
            description="Visually similar frame candidate",
            score=best_item["score"],
            score_type="cosine_similarity",
            applied_constraints=[],
            evidence=evidence
        )

    def _search_video_windows(self, request: SearchRequest, owner_id: str, query_text: str) -> SearchResponse:
        query_vector = self.embedding_provider.embed_texts([query_text])[0]

        db_query = (
            self.db.query(VideoWindow, Video)
            .join(Video, VideoWindow.video_id == Video.id)
            .filter(
                Video.owner_id == owner_id,
                Video.status == "READY",
                VideoWindow.embedding.isnot(None)
            )
        )
        if request.video_ids:
            db_query = db_query.filter(Video.id.in_(request.video_ids))

        rows = db_query.all()
        if not rows:
            return SearchResponse(query=query_text, search_mode="video_window_v1", results=[])

        candidates = []
        for window, video in rows:
            score = cosine_similarity(query_vector, window.embedding)
            if request.threshold is not None and score < request.threshold:
                continue

            # Look up closest evidence frame in this window
            evidence_frame = (
                self.db.query(Frame)
                .filter(
                    Frame.video_id == video.id,
                    Frame.timestamp_seconds >= window.start_seconds,
                    Frame.timestamp_seconds <= window.end_seconds
                )
                .first()
            )
            thumb_url = f"/api/v1/frames/{evidence_frame.id}/thumbnail" if evidence_frame else ""
            evidence_ts = evidence_frame.timestamp_seconds if evidence_frame else window.start_seconds

            candidates.append(
                SearchResultItem(
                    video_id=video.id,
                    filename=video.filename,
                    start_seconds=window.start_seconds,
                    end_seconds=window.end_seconds,
                    evidence_timestamp_seconds=evidence_ts,
                    thumbnail_url=thumb_url,
                    description="Temporally pooled video-window candidate",
                    score=round(score, 4),
                    score_type="cosine_similarity",
                    applied_constraints=[],
                    evidence=[EvidenceItem(frame_id=evidence_frame.id, timestamp_seconds=evidence_ts)] if evidence_frame else []
                )
            )

        candidates.sort(key=lambda w: w.score, reverse=True)
        return SearchResponse(
            query=query_text,
            search_mode="video_window_v1",
            results=candidates[: request.limit]
        )

    def _search_hybrid(self, request: SearchRequest, owner_id: str, query_text: str) -> SearchResponse:
        frame_resp = self._search_frames(request, owner_id, query_text)
        window_resp = self._search_video_windows(request, owner_id, query_text)

        # Merge candidate windows with combined score
        combined: List[SearchResultItem] = []
        for item in frame_resp.results:
            combined.append(item)
        for item in window_resp.results:
            combined.append(item)

        # Sort by score descending
        combined.sort(key=lambda x: x.score, reverse=True)
        return SearchResponse(
            query=query_text,
            search_mode="hybrid_v1",
            results=combined[: request.limit]
        )
