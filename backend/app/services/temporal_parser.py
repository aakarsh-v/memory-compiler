import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ParsedEvent:
    id: int
    query: str


@dataclass
class TemporalConstraint:
    left_event: int
    relation: str  # "before", "after", "during", "first", "last"
    right_event: Optional[int] = None


@dataclass
class ParsedQuery:
    raw_query: str
    events: List[ParsedEvent] = field(default_factory=list)
    constraints: List[TemporalConstraint] = field(default_factory=list)
    has_constraints: bool = False


class TemporalQueryParser:
    """
    Constrained temporal query parser for Phase 6.
    Parses structured temporal relations ('before', 'after', 'during', 'first', 'last')
    without executing unvalidated SQL or arbitrary LLM code.
    Gracefully falls back to plain semantic search for unconstrained or unsupported syntax.
    """

    def parse(self, raw_query: str) -> ParsedQuery:
        cleaned = raw_query.strip()
        lower = cleaned.lower()

        # Clean leading command words like "find", "search for", "show me"
        cleaned_search = re.sub(r"^(find|search for|show me|look for)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        lower_search = cleaned_search.lower()

        # 1. Extremum constraints: "first (time)? ..." or "last (time)? ..."
        first_match = re.match(r"^first(?:\s+time)?\s+(?:that\s+|the\s+)?(.+)$", lower_search)
        if first_match:
            event_text = first_match.group(1).strip()
            return ParsedQuery(
                raw_query=cleaned,
                events=[ParsedEvent(id=0, query=event_text)],
                constraints=[TemporalConstraint(left_event=0, relation="first")],
                has_constraints=True
            )

        last_match = re.match(r"^last(?:\s+time)?\s+(?:that\s+|the\s+)?(.+)$", lower_search)
        if last_match:
            event_text = last_match.group(1).strip()
            return ParsedQuery(
                raw_query=cleaned,
                events=[ParsedEvent(id=0, query=event_text)],
                constraints=[TemporalConstraint(left_event=0, relation="last")],
                has_constraints=True
            )

        # 2. Binary relational constraints: "before", "after", "during"
        # We look for whole word matching
        for relation in ("before", "after", "during"):
            pattern = rf"^(.+?)\s+\b{relation}\b\s+(.+)$"
            match = re.match(pattern, lower_search)
            if match:
                left_text = match.group(1).strip()
                right_text = match.group(2).strip()

                if left_text and right_text:
                    return ParsedQuery(
                        raw_query=cleaned,
                        events=[
                            ParsedEvent(id=0, query=left_text),
                            ParsedEvent(id=1, query=right_text)
                        ],
                        constraints=[
                            TemporalConstraint(left_event=0, relation=relation, right_event=1)
                        ],
                        has_constraints=True
                    )

        # 3. Fallback: unconstrained single semantic query
        return ParsedQuery(
            raw_query=cleaned,
            events=[ParsedEvent(id=0, query=cleaned_search if cleaned_search else cleaned)],
            constraints=[],
            has_constraints=False
        )
