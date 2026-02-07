"""
Test dataset for conflict resolution evaluation.

This dataset provides realistic scenarios for testing the conflict resolver:
- Version conflicts (same doc, different versions)
- Authority conflicts (same doc, different sources)
- Mixed conflicts (both version and authority)
"""

from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class ConflictTestCase:
    """A test case for conflict resolution."""

    name: str
    description: str
    chunks: List[Dict[str, Any]]
    source_priority: Dict[str, int]
    expected_winner: Dict[str, Any]
    expected_conflict_type: str


# Test dataset
def get_conflict_test_dataset() -> List[ConflictTestCase]:
    """Return the complete test dataset for conflict resolution."""

    return [
        # Test Case 1: Simple version conflict
        ConflictTestCase(
            name="version_conflict_simple",
            description="Same source, different versions. Latest should win.",
            chunks=[
                {
                    "doc_id": "policy_doc_001",
                    "source_id": "policy_001",
                    "source": "confluence",
                    "version": 1,
                    "chunk_index": 0,
                    "text": "Old policy version 1",
                    "section_path": "policies/security",
                    "heading_path": ["Security Policy", "Overview"],
                },
                {
                    "doc_id": "policy_doc_001",
                    "source_id": "policy_001",
                    "source": "confluence",
                    "version": 3,
                    "chunk_index": 0,
                    "text": "Latest policy version 3",
                    "section_path": "policies/security",
                    "heading_path": ["Security Policy", "Overview"],
                },
                {
                    "doc_id": "policy_doc_001",
                    "source_id": "policy_001",
                    "source": "confluence",
                    "version": 2,
                    "chunk_index": 0,
                    "text": "Middle policy version 2",
                    "section_path": "policies/security",
                    "heading_path": ["Security Policy", "Overview"],
                },
            ],
            source_priority={"confluence": 5},
            expected_winner={
                "doc_id": "policy_doc_001",
                "version": 3,
                "source": "confluence",
            },
            expected_conflict_type="version_conflict",
        ),
        # Test Case 2: Authority conflict
        ConflictTestCase(
            name="authority_conflict",
            description="Different sources, same version. Higher authority should win.",
            chunks=[
                {
                    "doc_id": "api_spec_001",
                    "source_id": "api_v2",
                    "source": "swagger",
                    "version": 1,
                    "chunk_index": 0,
                    "text": "API spec from swagger",
                    "section_path": "api/endpoints",
                    "heading_path": ["API", "Endpoints"],
                },
                {
                    "doc_id": "api_spec_001",
                    "source_id": "api_v2",
                    "source": "manual",
                    "version": 1,
                    "chunk_index": 0,
                    "text": "API spec from manual docs",
                    "section_path": "api/endpoints",
                    "heading_path": ["API", "Endpoints"],
                },
            ],
            source_priority={"manual": 10, "swagger": 5, "confluence": 3},
            expected_winner={
                "doc_id": "api_spec_001",
                "version": 1,
                "source": "manual",
            },
            expected_conflict_type="authority_conflict",
        ),
        # Test Case 3: Authority overrides version
        ConflictTestCase(
            name="authority_over_version",
            description="Lower version from high-authority source should beat higher version from low-authority.",
            chunks=[
                {
                    "doc_id": "config_001",
                    "source_id": "config_prod",
                    "source": "git",
                    "version": 5,
                    "chunk_index": 0,
                    "text": "Config from git v5",
                    "section_path": "config/production",
                    "heading_path": ["Configuration"],
                },
                {
                    "doc_id": "config_001",
                    "source_id": "config_prod",
                    "source": "manual",
                    "version": 1,
                    "chunk_index": 0,
                    "text": "Config from manual v1",
                    "section_path": "config/production",
                    "heading_path": ["Configuration"],
                },
            ],
            source_priority={"manual": 10, "git": 3},
            expected_winner={
                "doc_id": "config_001",
                "version": 1,
                "source": "manual",
            },
            expected_conflict_type="authority_conflict",
        ),
        # Test Case 4: No conflicts
        ConflictTestCase(
            name="no_conflicts",
            description="All chunks have unique source_ids, no conflicts should be detected.",
            chunks=[
                {
                    "doc_id": "doc_001",
                    "source_id": "src_001",
                    "source": "confluence",
                    "version": 1,
                    "chunk_index": 0,
                    "text": "Document 1",
                    "section_path": "docs/a",
                    "heading_path": ["Doc A"],
                },
                {
                    "doc_id": "doc_002",
                    "source_id": "src_002",
                    "source": "manual",
                    "version": 1,
                    "chunk_index": 0,
                    "text": "Document 2",
                    "section_path": "docs/b",
                    "heading_path": ["Doc B"],
                },
            ],
            source_priority={"manual": 10, "confluence": 5},
            expected_winner={
                "doc_id": "doc_001",  # First one (no conflict)
                "version": 1,
                "source": "confluence",
            },
            expected_conflict_type="none",
        ),
        # Test Case 5: Multiple independent conflicts
        ConflictTestCase(
            name="multiple_conflicts",
            description="Two separate conflict groups should be resolved independently.",
            chunks=[
                {
                    "doc_id": "policy_001",
                    "source_id": "policy_a",
                    "source": "confluence",
                    "version": 1,
                    "chunk_index": 0,
                    "text": "Policy A v1",
                    "section_path": "policies/a",
                    "heading_path": ["Policy A"],
                },
                {
                    "doc_id": "policy_001",
                    "source_id": "policy_a",
                    "source": "confluence",
                    "version": 2,
                    "chunk_index": 0,
                    "text": "Policy A v2",
                    "section_path": "policies/a",
                    "heading_path": ["Policy A"],
                },
                {
                    "doc_id": "policy_002",
                    "source_id": "policy_b",
                    "source": "manual",
                    "version": 1,
                    "chunk_index": 0,
                    "text": "Policy B v1",
                    "section_path": "policies/b",
                    "heading_path": ["Policy B"],
                },
                {
                    "doc_id": "policy_002",
                    "source_id": "policy_b",
                    "source": "git",
                    "version": 3,
                    "chunk_index": 0,
                    "text": "Policy B v3",
                    "section_path": "policies/b",
                    "heading_path": ["Policy B"],
                },
            ],
            source_priority={"manual": 10, "confluence": 5, "git": 3},
            expected_winner={
                "doc_id": "policy_001",  # Just one of them, both resolved
                "version": 2,
                "source": "confluence",
            },
            expected_conflict_type="mixed",
        ),
        # Test Case 6: Unknown source priority
        ConflictTestCase(
            name="unknown_source_priority",
            description="Source not in priority map gets priority 0.",
            chunks=[
                {
                    "doc_id": "doc_unknown",
                    "source_id": "src_unknown",
                    "source": "legacy_system",
                    "version": 2,
                    "chunk_index": 0,
                    "text": "From legacy system v2",
                    "section_path": "legacy/data",
                    "heading_path": ["Legacy"],
                },
                {
                    "doc_id": "doc_unknown",
                    "source_id": "src_unknown",
                    "source": "api",
                    "version": 1,
                    "chunk_index": 0,
                    "text": "From API v1",
                    "section_path": "legacy/data",
                    "heading_path": ["Legacy"],
                },
            ],
            source_priority={"api": 5},  # legacy_system not in map
            expected_winner={
                "doc_id": "doc_unknown",
                "version": 1,
                "source": "api",
            },
            expected_conflict_type="authority_conflict",
        ),
    ]


def get_test_case_by_name(name: str) -> ConflictTestCase:
    """Get a specific test case by name."""
    dataset = get_conflict_test_dataset()
    for case in dataset:
        if case.name == name:
            return case
    raise ValueError(f"Test case '{name}' not found")


def run_conflict_test_suite(resolver_func) -> Dict[str, Any]:
    """
    Run the complete test suite against a resolver function.

    Args:
        resolver_func: Function that takes (chunks, source_priority) and returns
                      (resolved_chunks, conflicts)

    Returns:
        Dict with test results and statistics
    """
    import sys

    sys.path.insert(0, "/Users/thiennlinh/Documents/New project")

    results = {
        "passed": 0,
        "failed": 0,
        "total": 0,
        "details": [],
    }

    for test_case in get_conflict_test_dataset():
        results["total"] += 1

        try:
            # Convert dict chunks to objects
            from types import SimpleNamespace

            chunk_objects = [SimpleNamespace(**chunk) for chunk in test_case.chunks]

            resolved, conflicts = resolver_func(
                chunk_objects, test_case.source_priority, log_conflicts=False
            )

            # Check results
            if test_case.expected_conflict_type == "none":
                if len(conflicts) > 0:
                    raise AssertionError(f"Expected no conflicts, got {len(conflicts)}")
            else:
                if len(conflicts) == 0:
                    raise AssertionError("Expected conflicts but none detected")

            # Check winner
            if test_case.expected_conflict_type != "none":
                winner = resolved[0]
                if winner.source != test_case.expected_winner["source"]:
                    raise AssertionError(
                        f"Expected source {test_case.expected_winner['source']}, "
                        f"got {winner.source}"
                    )

            results["passed"] += 1
            results["details"].append(
                {
                    "name": test_case.name,
                    "status": "PASSED",
                }
            )

        except Exception as e:
            results["failed"] += 1
            results["details"].append(
                {
                    "name": test_case.name,
                    "status": "FAILED",
                    "error": str(e),
                }
            )

    return results


if __name__ == "__main__":
    print("Conflict Resolution Test Dataset")
    print("=" * 60)

    dataset = get_conflict_test_dataset()
    print(f"\nTotal test cases: {len(dataset)}\n")

    for i, test_case in enumerate(dataset, 1):
        print(f"{i}. {test_case.name}")
        print(f"   Description: {test_case.description}")
        print(f"   Chunks: {len(test_case.chunks)}")
        print(f"   Expected conflict type: {test_case.expected_conflict_type}")
        print(f"   Expected winner: {test_case.expected_winner}")
        print()

    # Run test suite
    print("\nRunning test suite...")
    print("-" * 60)

    import sys

    sys.path.insert(0, "/Users/thiennlinh/Documents/New project")

    from resolver import resolve_conflicts

    results = run_conflict_test_suite(resolve_conflicts)

    print(f"\nResults:")
    print(f"  Passed: {results['passed']}/{results['total']}")
    print(f"  Failed: {results['failed']}/{results['total']}")
    print(f"  Success rate: {results['passed'] / results['total'] * 100:.1f}%")

    print("\nDetails:")
    for detail in results["details"]:
        status = "✓" if detail["status"] == "PASSED" else "✗"
        print(f"  {status} {detail['name']}: {detail['status']}")
        if "error" in detail:
            print(f"      Error: {detail['error']}")
