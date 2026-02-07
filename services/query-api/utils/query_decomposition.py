"""
Query Decomposition Module

Decomposes complex queries into simpler sub-queries for improved search.
Uses LLM to identify distinct aspects of a query and generate focused sub-queries.

Benefits:
- Handles multi-intent queries
- Improves recall for complex questions
- Enables parallel search execution
"""

import hashlib
import json
import re
import httpx
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

from config import settings


class DecompositionStrategy(Enum):
    """Strategies for query decomposition."""

    SINGLE = "single"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    HYBRID = "hybrid"


@dataclass
class SubQuery:
    """A decomposed sub-query."""

    id: int
    query: str
    intent: str
    keywords: List[str]
    is_primary: bool


@dataclass
class DecomposedQuery:
    """A query decomposed into sub-queries."""

    original_query: str
    sub_queries: List[SubQuery]
    strategy: DecompositionStrategy
    merged_context: str = ""


class QueryDecomposer:
    """Decomposes complex queries into simpler sub-queries."""

    def __init__(
        self,
        llm_gateway_url: str = None,
        max_subqueries: int = None,
    ):
        self.llm_gateway_url = llm_gateway_url or settings.llm_gateway_url
        self.max_subqueries = max_subqueries or settings.decomposition_max_subqueries
        self._decomposition_cache: Dict[str, DecomposedQuery] = {}

    def _generate_decomposition_prompt(self, query: str) -> str:
        """Generate the prompt for decomposing a query."""
        return f"""Analyze this complex query and break it down into {self.max_subqueries} or fewer simpler sub-questions.

Original Query: {query}

Identify the distinct aspects or questions within this query.
Each sub-question should:
1. Be answerable independently
2. Focus on one specific aspect
3. Use clear, specific keywords

Return your response as JSON:
{{
    "sub_queries": [
        {{
            "query": "the sub-question text",
            "intent": "what aspect this addresses",
            "keywords": ["keyword1", "keyword2"],
            "is_primary": true/false
        }}
    ],
    "strategy": "parallel" or "sequential"
}}

JSON Response:"""

    async def decompose(self, query: str, use_cache: bool = True) -> DecomposedQuery:
        """
        Decompose a complex query into sub-queries.

        Args:
            query: The original complex query
            use_cache: Whether to use cached results

        Returns:
            DecomposedQuery with sub-queries
        """
        cache_key = hashlib.md5(query.encode()).hexdigest()

        if use_cache and cache_key in self._decomposition_cache:
            return self._decomposition_cache[cache_key]

        sub_queries = []
        strategy = DecompositionStrategy.PARALLEL

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.llm_gateway_url}/generate",
                    json={
                        "prompt": self._generate_decomposition_prompt(query),
                        "max_tokens": 500,
                        "temperature": 0.3,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                text = data.get("text", "").strip()

                json_match = re.search(r"\{[\s\S]*\}", text)
                if json_match:
                    parsed = json.loads(json_match.group())
                    parsed_queries = parsed.get("sub_queries", [])

                    for i, sq in enumerate(parsed_queries):
                        sub_queries.append(
                            SubQuery(
                                id=i,
                                query=sq.get("query", ""),
                                intent=sq.get("intent", ""),
                                keywords=sq.get("keywords", []),
                                is_primary=sq.get("is_primary", i == 0),
                            )
                        )

                    strategy_str = parsed.get("strategy", "parallel")
                    strategy = DecompositionStrategy(strategy_str)

        except Exception as e:
            print(f"Query decomposition failed: {e}")
            sub_queries = [
                SubQuery(
                    id=0,
                    query=query,
                    intent="original query",
                    keywords=query.split()[:10],
                    is_primary=True,
                )
            ]

        if not sub_queries:
            sub_queries = [
                SubQuery(
                    id=0,
                    query=query,
                    intent="original query",
                    keywords=query.split()[:10],
                    is_primary=True,
                )
            ]

        result = DecomposedQuery(
            original_query=query,
            sub_queries=sub_queries,
            strategy=strategy,
        )

        self._decomposition_cache[cache_key] = result
        return result

    def decompose_simple(self, query: str) -> DecomposedQuery:
        """
        Simple rule-based decomposition without LLM.

        Useful for simple multi-intent queries.
        """
        keywords = query.lower().split()
        sub_queries = []

        question_patterns = [
            (
                r"(?i)(what|who|where|when|why|how)\s+(is|are|was|were|do|does|can|could|should)",
                "question",
            ),
            (r"(?i)(explain|describe|compare|difference|versus|vs)", "comparison"),
            (r"(?i)(step|process|how to|tutorial|guide)", "procedure"),
        ]

        has_complex = any(re.search(p[0], query) for p in question_patterns)

        if not has_complex and len(keywords) < 5:
            return DecomposedQuery(
                original_query=query,
                sub_queries=[
                    SubQuery(
                        id=0,
                        query=query,
                        intent="original",
                        keywords=keywords,
                        is_primary=True,
                    )
                ],
                strategy=DecompositionStrategy.SINGLE,
            )

        return DecomposedQuery(
            original_query=query,
            sub_queries=[
                SubQuery(
                    id=0,
                    query=query,
                    intent="comprehensive",
                    keywords=keywords,
                    is_primary=True,
                )
            ],
            strategy=DecompositionStrategy.PARALLEL,
        )

    def clear_cache(self):
        """Clear the decomposition cache."""
        self._decomposition_cache.clear()


class MultiQuerySearchEngine:
    """
    Search engine that uses query decomposition for improved recall.

    Flow:
    1. Decompose query into sub-queries
    2. Search each sub-query
    3. Merge and rerank results
    """

    def __init__(
        self,
        decomposer: QueryDecomposer = None,
        search_engine=None,
    ):
        self.decomposer = decomposer or QueryDecomposer()
        self.search_engine = search_engine
        self._results_cache: Dict[str, List[dict]] = {}

    def configure_search_engine(self, search_engine):
        """Configure the underlying search engine."""
        self.search_engine = search_engine

    async def search(
        self,
        query: str,
        tenant_id: str = None,
        top_k: int = 10,
        use_decomposition: bool = None,
        filters: dict = None,
    ) -> Tuple[List[dict], DecomposedQuery]:
        """
        Perform multi-query search with decomposition.

        Args:
            query: Search query
            tenant_id: Tenant ID for filtering
            top_k: Results per sub-query
            use_decomposition: Override decomposition setting
            filters: Additional filters

        Returns:
            Tuple of (merged_results, decomposed_query)
        """
        use_decomposition = (
            use_decomposition
            if use_decomposition is not None
            else settings.query_decomposition_enabled
        )

        if not use_decomposition:
            decomposed = self.decomposer.decompose_simple(query)
        else:
            decomposed = await self.decomposer.decompose(query)

        if filters is None:
            filters = {}
        if tenant_id:
            filters["tenant_id"] = tenant_id

        all_results = []

        for sub_query in decomposed.sub_queries:
            results = await self._search_subquery(
                sub_query.query,
                filters,
                top_k,
            )
            for r in results:
                r["_sub_query_id"] = sub_query.id
                r["_sub_query_intent"] = sub_query.intent
                r["_is_primary"] = sub_query.is_primary
            all_results.extend(results)

        merged = self._merge_subquery_results(all_results, top_k, decomposed)

        return merged, decomposed

    async def _search_subquery(
        self,
        sub_query: str,
        filters: dict,
        top_k: int,
    ) -> List[dict]:
        """Search for a single sub-query."""
        if self.search_engine is None:
            return []

        results = self.search_engine.search(
            query=sub_query,
            filters=filters,
            top_k=top_k,
        )
        return results

    def _merge_subquery_results(
        self,
        all_results: List[dict],
        top_k: int,
        decomposed: DecomposedQuery,
    ) -> List[dict]:
        """Merge results from multiple sub-queries."""
        from fusion import rrf_fusion

        score_map: Dict[str, Tuple[float, List[int]]] = {}

        for result in all_results:
            doc_id = result.get("id", "")
            score = result.get("score", 0.0)
            sub_query_ids = result.get(
                "_sub_query_ids", [result.get("_sub_query_id", 0)]
            )

            if doc_id not in score_map:
                score_map[doc_id] = (score, sub_query_ids)
            else:
                current_score, current_ids = score_map[doc_id]
                score_map[doc_id] = (
                    max(current_score, score),
                    list(set(current_ids + sub_query_ids)),
                )

        final_scores: Dict[str, float] = {}
        for doc_id, (base_score, sub_query_ids) in score_map.items():
            if len(sub_query_ids) > 1:
                bonus = 0.1 * len(sub_query_ids)
            else:
                bonus = 0.0

            if any(r["_is_primary"] for r in all_results if r.get("id") == doc_id):
                bonus += 0.05

            final_scores[doc_id] = base_score + bonus

        ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        return [
            {
                "id": doc_id,
                "score": score,
                "sub_query_matches": list(
                    set(
                        r.get("_sub_query_ids", [])
                        for r in all_results
                        if r.get("id") == doc_id
                    )
                ),
            }
            for doc_id, score in ranked[:top_k]
        ]

    def clear_caches(self):
        """Clear all internal caches."""
        self.decomposer.clear_cache()
        self._results_cache.clear()
