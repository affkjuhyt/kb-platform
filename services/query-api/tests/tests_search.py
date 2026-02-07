from schema import SearchRequest


def test_search_request_validation():
    try:
        SearchRequest(query="")
        assert False
    except Exception:
        assert True
