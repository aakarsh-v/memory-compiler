import pytest
from app.services.temporal_parser import TemporalQueryParser, ParsedEvent, TemporalConstraint
from app.services.constraint_evaluator import TemporalConstraintEvaluator
from app.schemas.search import SearchResultItem, EvidenceItem


def test_temporal_parser_relations():
    parser = TemporalQueryParser()

    # Before
    q1 = parser.parse("Find person entering room before sitting on couch")
    assert q1.has_constraints is True
    assert len(q1.events) == 2
    assert q1.events[0].query == "person entering room"
    assert q1.events[1].query == "sitting on couch"
    assert q1.constraints[0].relation == "before"

    # After
    q2 = parser.parse("turning off lights after closing door")
    assert q2.has_constraints is True
    assert q2.constraints[0].relation == "after"

    # Extremum: first & last
    q3 = parser.parse("first time the red car appears")
    assert q3.has_constraints is True
    assert q3.constraints[0].relation == "first"
    assert "red car appears" in q3.events[0].query

    q4 = parser.parse("last time someone waved")
    assert q4.has_constraints is True
    assert q4.constraints[0].relation == "last"


def test_temporal_parser_unconstrained_fallback():
    parser = TemporalQueryParser()
    q = parser.parse("person in a red jacket walking on street")
    assert q.has_constraints is False
    assert len(q.constraints) == 0
    assert q.events[0].query == "person in a red jacket walking on street"


def test_order_reversal_rejected():
    evaluator = TemporalConstraintEvaluator()
    parser = TemporalQueryParser()
    query = parser.parse("person entering before sitting down")

    # Order reversal: "entering" occurs AFTER "sitting down"
    # Event 0 (entering) interval: [4.0, 6.0]
    # Event 1 (sitting) interval: [1.0, 2.0]
    candidate_entering = SearchResultItem(
        video_id="vid-1",
        filename="clip.mp4",
        start_seconds=4.0,
        end_seconds=6.0,
        evidence_timestamp_seconds=4.0,
        thumbnail_url="/thumb/1",
        score=0.9
    )
    candidate_sitting = SearchResultItem(
        video_id="vid-1",
        filename="clip.mp4",
        start_seconds=1.0,
        end_seconds=2.0,
        evidence_timestamp_seconds=1.0,
        thumbnail_url="/thumb/2",
        score=0.85
    )

    event_candidates = {
        0: [candidate_entering],
        1: [candidate_sitting]
    }

    # "entering before sitting": candidate_entering.end_seconds (6.0) > candidate_sitting.start_seconds (1.0)
    # This violates the temporal relation 'before', so it must be REJECTED
    results = evaluator.evaluate_constraints(query, event_candidates)
    assert len(results) == 0


def test_order_compliance_accepted():
    evaluator = TemporalConstraintEvaluator()
    parser = TemporalQueryParser()
    query = parser.parse("person entering before sitting down")

    # Compliant: Event 0 occurs [1.0, 2.5] then Event 1 occurs [3.0, 5.0]
    candidate_entering = SearchResultItem(
        video_id="vid-1",
        filename="clip.mp4",
        start_seconds=1.0,
        end_seconds=2.5,
        evidence_timestamp_seconds=1.0,
        thumbnail_url="/thumb/1",
        score=0.9
    )
    candidate_sitting = SearchResultItem(
        video_id="vid-1",
        filename="clip.mp4",
        start_seconds=3.0,
        end_seconds=5.0,
        evidence_timestamp_seconds=3.0,
        thumbnail_url="/thumb/2",
        score=0.8
    )

    event_candidates = {
        0: [candidate_entering],
        1: [candidate_sitting]
    }

    results = evaluator.evaluate_constraints(query, event_candidates)
    assert len(results) == 1
    res = results[0]
    assert res.start_seconds == 1.0
    assert res.end_seconds == 5.0
    assert res.score == 0.85  # (0.9 + 0.8) / 2
    assert "before(person entering, sitting down)" in res.applied_constraints[0]


def test_missing_event_handling():
    evaluator = TemporalConstraintEvaluator()
    parser = TemporalQueryParser()
    query = parser.parse("person entering before sitting down")

    # Event 0 found, Event 1 missing
    candidate_entering = SearchResultItem(
        video_id="vid-1",
        filename="clip.mp4",
        start_seconds=1.0,
        end_seconds=2.5,
        evidence_timestamp_seconds=1.0,
        thumbnail_url="/thumb/1",
        score=0.9
    )

    event_candidates = {
        0: [candidate_entering],
        1: []  # No candidate for Event 1
    }

    results = evaluator.evaluate_constraints(query, event_candidates)
    assert len(results) == 0


def test_extremum_first_and_last():
    evaluator = TemporalConstraintEvaluator()
    parser = TemporalQueryParser()

    cand_early = SearchResultItem(
        video_id="vid-1",
        filename="clip.mp4",
        start_seconds=1.0,
        end_seconds=3.0,
        evidence_timestamp_seconds=1.0,
        thumbnail_url="/thumb/1",
        score=0.8
    )
    cand_late = SearchResultItem(
        video_id="vid-1",
        filename="clip.mp4",
        start_seconds=7.0,
        end_seconds=9.0,
        evidence_timestamp_seconds=7.0,
        thumbnail_url="/thumb/2",
        score=0.85
    )

    event_candidates = {0: [cand_late, cand_early]}

    # Test "first"
    q_first = parser.parse("first red car")
    first_res = evaluator.evaluate_constraints(q_first, event_candidates)
    assert len(first_res) == 1
    assert first_res[0].start_seconds == 1.0
    assert "first" in first_res[0].applied_constraints[0]

    # Test "last"
    q_last = parser.parse("last red car")
    last_res = evaluator.evaluate_constraints(q_last, event_candidates)
    assert len(last_res) == 1
    assert last_res[0].start_seconds == 7.0
    assert "last" in last_res[0].applied_constraints[0]

