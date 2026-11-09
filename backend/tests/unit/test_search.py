import pytest
from app.services.search_service import cosine_similarity, SearchService
from app.schemas.search import SearchRequest
from app.core.errors import ValidationException


def test_cosine_similarity():
    # Identical vectors -> similarity 1.0
    v1 = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(v1, v1) - 1.0) < 1e-5

    # Orthogonal vectors -> similarity 0.0
    v2 = [0.0, 1.0, 0.0]
    assert abs(cosine_similarity(v1, v2) - 0.0) < 1e-5

    # Opposite vectors -> similarity -1.0
    v3 = [-1.0, 0.0, 0.0]
    assert abs(cosine_similarity(v1, v3) - (-1.0)) < 1e-5


def test_search_rejects_empty_query():
    service = SearchService(db=None, embedding_provider=None)
    with pytest.raises(ValidationException) as exc:
        service.search(SearchRequest(query="   "), owner_id="user1")
    assert exc.value.code == "SEARCH_EMPTY_QUERY"
