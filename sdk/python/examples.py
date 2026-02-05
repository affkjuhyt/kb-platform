"""
Example usage of RAG Python SDK

This file demonstrates various use cases for the RAG SDK.
"""

from rag_sdk import RAGClient, AuthenticationError, RateLimitError, APIError


def example_basic_usage():
    """Example 1: Basic usage with login."""
    print("\n=== Example 1: Basic Usage ===")

    client = RAGClient(base_url="http://localhost:8000", tenant_id="demo-tenant")

    try:
        # Login
        token = client.login("user@example.com", "password")
        print(f"✓ Logged in. Token expires in {token.expires_in} seconds")

        # Health check
        health = client.health_check()
        print(f"✓ API Health: {health['status']}")

    except AuthenticationError as e:
        print(f"✗ Authentication failed: {e}")
    finally:
        client.close()


def example_api_key_auth():
    """Example 2: Using API key authentication."""
    print("\n=== Example 2: API Key Authentication ===")

    # No login needed with API key
    client = RAGClient(
        base_url="http://localhost:8000",
        tenant_id="demo-tenant",
        api_key="rag_your_api_key_here",
    )

    try:
        # Directly use search without login
        results = client.search("machine learning", top_k=3)
        print(f"✓ Found {len(results)} results using API key")

    except APIError as e:
        print(f"✗ API error: {e}")
    finally:
        client.close()


def example_context_manager():
    """Example 3: Using context manager."""
    print("\n=== Example 3: Context Manager ===")

    try:
        with RAGClient(
            base_url="http://localhost:8000",
            tenant_id="demo-tenant",
            api_key="rag_your_api_key_here",
        ) as client:
            results = client.search("deep learning", top_k=5)
            print(f"✓ Found {len(results)} documents")

            for i, result in enumerate(results[:3], 1):
                print(f"  {i}. {result.doc_id} (score: {result.score:.2f})")

    except Exception as e:
        print(f"✗ Error: {e}")


def example_rag_query():
    """Example 4: RAG query with citations."""
    print("\n=== Example 4: RAG Query ===")

    with RAGClient(
        base_url="http://localhost:8000",
        tenant_id="demo-tenant",
        api_key="rag_your_api_key_here",
    ) as client:
        try:
            response = client.rag_query(
                "What is machine learning?", top_k=5, session_id="session-001"
            )

            print(f"✓ Answer: {response.answer}")
            print(f"  Confidence: {response.confidence:.2f}")
            print(f"  Citations: {len(response.citations)}")

            for citation in response.citations[:3]:
                print(
                    f"    - {citation.get('doc_id')} (source: {citation.get('source')})"
                )

        except APIError as e:
            print(f"✗ API error: {e}")


def example_data_extraction():
    """Example 5: Structured data extraction."""
    print("\n=== Example 5: Data Extraction ===")

    with RAGClient(
        base_url="http://localhost:8000",
        tenant_id="demo-tenant",
        api_key="rag_your_api_key_here",
    ) as client:
        # Define extraction schema
        schema = {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "Name of the company",
                },
                "founded_year": {
                    "type": "integer",
                    "description": "Year the company was founded",
                },
                "headquarters": {
                    "type": "string",
                    "description": "Location of headquarters",
                },
                "employees": {"type": "integer", "description": "Number of employees"},
            },
            "required": ["company_name"],
        }

        try:
            result = client.extract(
                "Extract company information from the about page",
                schema=schema,
                top_k=5,
                min_confidence=0.7,
            )

            if result.success:
                print(f"✓ Extraction successful")
                print(f"  Confidence: {result.confidence:.2f}")
                print(f"  Data: {result.data}")
            else:
                print(f"✗ Extraction failed")
                print(f"  Errors: {result.validation_errors}")

        except APIError as e:
            print(f"✗ API error: {e}")


def example_async_extraction():
    """Example 6: Async extraction with job tracking."""
    print("\n=== Example 6: Async Extraction ===")

    with RAGClient(
        base_url="http://localhost:8000",
        tenant_id="demo-tenant",
        api_key="rag_your_api_key_here",
    ) as client:
        schema = {
            "type": "object",
            "properties": {
                "employees": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                            "department": {"type": "string"},
                        },
                    },
                }
            },
        }

        try:
            result = client.extract_with_job(
                "Extract all employee information",
                schema=schema,
                schema_name="employee_list",
                top_k=10,
                poll_interval=2,
                max_wait=60,
            )

            if result.success:
                print(f"✓ Async extraction completed")
                print(f"  Job ID: {result.job_id}")
                print(f"  Found {len(result.data.get('employees', []))} employees")
            else:
                print(f"✗ Async extraction failed")
                print(f"  Errors: {result.validation_errors}")

        except APIError as e:
            print(f"✗ API error: {e}")


def example_error_handling():
    """Example 7: Error handling."""
    print("\n=== Example 7: Error Handling ===")

    with RAGClient(base_url="http://localhost:8000", tenant_id="demo-tenant") as client:
        try:
            # Try to search without authentication
            results = client.search("test")

        except AuthenticationError as e:
            print(f"✓ Caught authentication error: {e}")

        except RateLimitError as e:
            print(f"✓ Caught rate limit error: {e}")
            print(f"  Retry after: {e.retry_after} seconds")

        except APIError as e:
            print(f"✓ Caught API error: {e}")
            print(f"  Status code: {e.status_code}")

        except Exception as e:
            print(f"✗ Unexpected error: {e}")


def example_conversation_session():
    """Example 8: Multi-turn conversation with session."""
    print("\n=== Example 8: Conversation Session ===")

    import uuid

    session_id = str(uuid.uuid4())
    print(f"Session ID: {session_id}")

    with RAGClient(
        base_url="http://localhost:8000",
        tenant_id="demo-tenant",
        api_key="rag_your_api_key_here",
    ) as client:
        questions = [
            "What is machine learning?",
            "What are the types of machine learning?",
            "Give me an example of supervised learning.",
        ]

        for i, question in enumerate(questions, 1):
            try:
                response = client.rag_query(question, session_id=session_id)

                print(f"\nQ{i}: {question}")
                print(f"A{i}: {response.answer[:100]}...")

            except APIError as e:
                print(f"✗ Error in turn {i}: {e}")


def example_batch_search():
    """Example 9: Batch search operations."""
    print("\n=== Example 9: Batch Search ===")

    queries = [
        "machine learning",
        "deep learning",
        "neural networks",
        "natural language processing",
    ]

    with RAGClient(
        base_url="http://localhost:8000",
        tenant_id="demo-tenant",
        api_key="rag_your_api_key_here",
    ) as client:
        for query in queries:
            try:
                results = client.search(query, top_k=3)
                print(f"✓ '{query}': {len(results)} results")

            except APIError as e:
                print(f"✗ '{query}': Error - {e}")


def example_quick_functions():
    """Example 10: Quick convenience functions."""
    print("\n=== Example 10: Quick Functions ===")

    from rag_sdk import search, rag_query

    config = {
        "baseUrl": "http://localhost:8000",
        "tenantId": "demo-tenant",
        "apiKey": "rag_your_api_key_here",
    }

    try:
        # Quick search
        results = search(config, "machine learning", top_k=5)
        print(f"✓ Quick search: {len(results)} results")

        # Quick RAG query
        answer = rag_query(config, "What is AI?")
        print(f"✓ Quick RAG: {answer.answer[:50]}...")

    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    print("=" * 70)
    print("RAG SDK Python Examples")
    print("=" * 70)

    # Run examples
    examples = [
        example_basic_usage,
        example_api_key_auth,
        example_context_manager,
        example_rag_query,
        example_data_extraction,
        example_async_extraction,
        example_error_handling,
        example_conversation_session,
        example_batch_search,
        example_quick_functions,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n✗ Example failed: {e}")

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
