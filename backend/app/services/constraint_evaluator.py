from typing import List, Dict, Any, Optional
from app.schemas.search import SearchResultItem, EvidenceItem
from app.services.temporal_parser import ParsedQuery, TemporalConstraint


class TemporalConstraintEvaluator:
    """
    Evaluates temporal constraints (before, after, during, first, last)
    across candidate intervals and filters out order reversals and invalid pairs.
    """

    def evaluate_constraints(
        self,
        parsed_query: ParsedQuery,
        event_candidates: Dict[int, List[SearchResultItem]]
    ) -> List[SearchResultItem]:
        """
        Validates temporal relations between candidate intervals.
        """
        if not parsed_query.has_constraints or not parsed_query.constraints:
            # No constraints to evaluate; return primary candidates
            return event_candidates.get(0, [])

        constraint = parsed_query.constraints[0]
        relation = constraint.relation.lower()

        # 1. Extremum: "first"
        if relation == "first":
            candidates = event_candidates.get(0, [])
            if not candidates:
                return []
            # Sort chronologically by start_seconds
            sorted_by_time = sorted(candidates, key=lambda c: c.start_seconds)
            earliest = sorted_by_time[0]
            earliest.applied_constraints = [f"first({parsed_query.events[0].query})"]
            earliest.description = f"First occurrence of: {parsed_query.events[0].query}"
            return [earliest]

        # 2. Extremum: "last"
        if relation == "last":
            candidates = event_candidates.get(0, [])
            if not candidates:
                return []
            sorted_by_time = sorted(candidates, key=lambda c: c.start_seconds, reverse=True)
            latest = sorted_by_time[0]
            latest.applied_constraints = [f"last({parsed_query.events[0].query})"]
            latest.description = f"Last occurrence of: {parsed_query.events[0].query}"
            return [latest]

        # 3. Binary relations: "before", "after", "during"
        left_candidates = event_candidates.get(0, [])
        right_candidates = event_candidates.get(1, [])

        # Missing event handling: if either event has no candidates, constraint cannot be satisfied
        if not left_candidates or not right_candidates:
            return []

        valid_pairs: List[SearchResultItem] = []

        # Compare candidates within the same video
        for left in left_candidates:
            for right in right_candidates:
                if left.video_id != right.video_id:
                    continue

                is_valid = False
                constraint_label = ""

                if relation == "before":
                    # Event A must end before Event B begins
                    # Detect order reversals: if left starts after right, it is rejected
                    if left.end_seconds <= right.start_seconds:
                        is_valid = True
                        constraint_label = f"before({parsed_query.events[0].query}, {parsed_query.events[1].query})"

                elif relation == "after":
                    # Event A must begin after Event B ends
                    if left.start_seconds >= right.end_seconds:
                        is_valid = True
                        constraint_label = f"after({parsed_query.events[0].query}, {parsed_query.events[1].query})"

                elif relation == "during":
                    # Event A occurs within Event B
                    if right.start_seconds <= left.start_seconds and left.end_seconds <= right.end_seconds:
                        is_valid = True
                        constraint_label = f"during({parsed_query.events[0].query}, {parsed_query.events[1].query})"

                if is_valid:
                    # Compound candidate interval
                    compound_start = min(left.start_seconds, right.start_seconds)
                    compound_end = max(left.end_seconds, right.end_seconds)
                    combined_score = round((left.score + right.score) / 2.0, 4)

                    # Merge evidence frames
                    combined_evidence = left.evidence + right.evidence

                    valid_pairs.append(
                        SearchResultItem(
                            video_id=left.video_id,
                            filename=left.filename,
                            start_seconds=compound_start,
                            end_seconds=compound_end,
                            evidence_timestamp_seconds=left.evidence_timestamp_seconds,
                            thumbnail_url=left.thumbnail_url,
                            description=f"Temporal match: {constraint_label}",
                            score=combined_score,
                            score_type="cosine_similarity",
                            applied_constraints=[constraint_label],
                            evidence=combined_evidence
                        )
                    )

        valid_pairs.sort(key=lambda x: x.score, reverse=True)
        return valid_pairs
