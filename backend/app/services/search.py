"""Hybrid search: vector + keyword + RRF fusion + reranking."""

from __future__ import annotations

import logging
import math
from typing import Any

from app.core.config import settings
from app.core.supabase_client import get_supabase_client
from app.models.chunk import SearchFilters, SearchResultItem
from app.services.embedding import EmbeddingService
from app.services.korean_normalizer import normalize_for_fts

logger = logging.getLogger(__name__)

# RRF constant (standard value)
RRF_K = 60  # score=1/(RRF_K+rank)


class SearchService:
    """Hybrid search with vector similarity, keyword matching, RRF, and reranking."""

    def __init__(self, embedding_service: EmbeddingService):
        self._embedding = embedding_service
        self._supabase = get_supabase_client()
        self._reranker: Any = None
        self._reranker_loaded = False

    def _load_reranker(self) -> None:
        """Lazily load the FlashRank reranker model."""
        if self._reranker_loaded:
            return

        if settings.RERANK_MODEL == "none":
            self._reranker = None
            self._reranker_loaded = True
            return

        try:
            logger.info("Loading FlashRank reranker: %s", settings.RERANK_MODEL)
            from flashrank import Ranker

            self._reranker = Ranker(
                model_name=settings.RERANK_MODEL,
                max_length=512,
            )
            logger.info("FlashRank reranker loaded")
        except ImportError:
            logger.warning(
                "flashrank not available; disabling reranker. "
                "Install with: pip install flashrank"
            )
            self._reranker = None
        except Exception as exc:
            logger.warning("Failed to load FlashRank reranker: %s", exc)
            self._reranker = None

        self._reranker_loaded = True

    def search(
        self,
        query: str,
        user_id: str,
        top_k: int | None = None,
        filters: SearchFilters | None = None,
    ) -> list[SearchResultItem]:
        """Execute hybrid search: vector + keyword → RRF fusion → rerank.

        Args:
            query: Natural language search query.
            user_id: Current user's ID (for RLS scoping).
            top_k: Number of results to return (default from settings).
            filters: Optional search filters.

        Returns:
            Ranked list of SearchResultItem.
        """
        top_k = top_k or settings.TOP_K
        candidate_count = 20  # Retrieve top 20 from each method before fusion

        if settings.SEARCH_DEBUG:
            logger.info(
                "[search] query=%r top_k=%d candidate_count=%d",
                query,
                top_k,
                candidate_count,
            )

        # Step 1: Embed the query
        query_embedding = self._embedding.embed_query(query)

        # Step 2: Vector search
        vector_results = self._vector_search(
            query_embedding, user_id, candidate_count, filters
        )
        if settings.SEARCH_DEBUG:
            logger.info(
                "[search] vector: count=%d embedding_dim=%d",
                len(vector_results),
                len(query_embedding),
            )

        # Step 3: Keyword search
        keyword_results = self._keyword_search(
            query, user_id, candidate_count, filters
        )
        if settings.SEARCH_DEBUG:
            logger.info("[search] keyword: count=%d", len(keyword_results))

        # Step 4: RRF fusion
        fused_results = self._rrf_fusion(vector_results, keyword_results)
        if settings.SEARCH_DEBUG:
            logger.info("[search] rrf: fused_count=%d", len(fused_results))

        # Step 5: Rerank
        reranked = self._rerank(query, fused_results, top_k)
        if settings.SEARCH_DEBUG:
            logger.info("[search] final: returned=%d", len(reranked))

        return reranked

    def _vector_search(
        self,
        query_embedding: list[float],
        user_id: str,
        limit: int,
        filters: SearchFilters | None,
    ) -> list[dict[str, Any]]:
        """Cosine similarity search against chunk embeddings."""
        # Apply filters
        filter_document_ids = None
        if filters and filters.document_ids:
            filter_document_ids = filters.document_ids

        threshold = settings.VECTOR_SIMILARITY_THRESHOLD
        if settings.SEARCH_DEBUG:
            logger.info(
                "[search] vector: threshold=%.2f limit=%d",
                threshold,
                limit,
            )
        try:
            result = self._supabase.rpc(
                "match_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_count": limit,
                    "p_user_id": user_id,
                    "p_document_ids": filter_document_ids,
                    "p_threshold": threshold,
                },
            ).execute()

            results = result.data or []
            if settings.SEARCH_DEBUG:
                logger.info("[search] vector: db_count=%d", len(results))

            # Filter out low-similarity results (align with DB threshold)
            filtered_results = [
                r for r in results
                if r.get("similarity", 0) >= threshold
            ]

            if settings.SEARCH_DEBUG and filtered_results:
                sims = [r.get("similarity", 0) for r in filtered_results]
                logger.info(
                    "[search] vector: after_filter=%d sim_min=%.3f sim_max=%.3f",
                    len(filtered_results),
                    min(sims),
                    max(sims),
                )
            elif settings.SEARCH_DEBUG:
                logger.info("[search] vector: after_filter=0")

            if len(filtered_results) < len(results):
                logger.debug(
                    "Vector search: filtered %d/%d results below similarity threshold %.2f",
                    len(results) - len(filtered_results),
                    len(results),
                    threshold,
                )

            return filtered_results
        except Exception as exc:
            logger.error("Vector search failed: %s", exc)
            return []

    def _keyword_search(
        self,
        query: str,
        user_id: str,
        limit: int,
        filters: SearchFilters | None,
    ) -> list[dict[str, Any]]:
        """Full-text keyword search on chunk content (uses MeCab-normalized query when available)."""
        filter_document_ids = None
        if filters and filters.document_ids:
            filter_document_ids = filters.document_ids

        # Normalize query for Korean FTS (content words; matches content_normalized in DB)
        search_query = normalize_for_fts(query)
        if not search_query.strip():
            search_query = query

        try:
            result = self._supabase.rpc(
                "keyword_search_chunks",
                {
                    "search_query": search_query,
                    "match_count": limit,
                    "p_user_id": user_id,
                    "p_document_ids": filter_document_ids,
                },
            ).execute()

            data = result.data or []
            if settings.SEARCH_DEBUG:
                logger.info(
                    "[search] keyword: count=%d ids=%s",
                    len(data),
                    [r.get("id") for r in data[:5]] if data else [],
                )
            return data
        except Exception as exc:
            logger.error("Keyword search failed: %s", exc)
            return []

    def _rrf_fusion(
        self,
        vector_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Reciprocal Rank Fusion to merge vector and keyword results.

        score = 1 / (k + rank) for each source, then sum.
        """
        if settings.SEARCH_DEBUG:
            logger.info(
                "[search] rrf: vector=%d keyword=%d",
                len(vector_results),
                len(keyword_results),
            )
        scores: dict[str, float] = {}
        chunk_data: dict[str, dict[str, Any]] = {}

        # Score vector results
        for rank, result in enumerate(vector_results, start=1):
            chunk_id = result["id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (RRF_K + rank)
            chunk_data[chunk_id] = result

        # Score keyword results
        for rank, result in enumerate(keyword_results, start=1):
            chunk_id = result["id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (RRF_K + rank)
            if chunk_id not in chunk_data:
                chunk_data[chunk_id] = result
            else:
                # Preserve max similarity from either source
                existing_sim = chunk_data[chunk_id].get("similarity", 0)
                new_sim = result.get("similarity", 0)
                chunk_data[chunk_id]["similarity"] = max(existing_sim, new_sim)

        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)

        fused: list[dict[str, Any]] = []
        for chunk_id in sorted_ids:
            data = chunk_data[chunk_id]
            data["rrf_score"] = scores[chunk_id]
            fused.append(data)

        if settings.SEARCH_DEBUG and fused:
            top_rrf = [
                (str(c["id"]), round(c["rrf_score"], 4))
                for c in fused[:10]
            ]
            logger.info(
                "[search] rrf: fused=%d top_rrf=%s",
                len(fused),
                top_rrf,
            )
        return fused

    @staticmethod
    def _sigmoid(x: float) -> float:
        """Convert a raw logit score to a 0-1 probability."""
        try:
            return 1.0 / (1.0 + math.exp(-x))
        except OverflowError:
            return 0.0 if x < 0 else 1.0

    @staticmethod
    def _query_terms_for_overlap(query: str) -> set[str]:
        """Tokenize query into terms for lexical-overlap check (normalized + original)."""
        normalized = normalize_for_fts(query)
        terms = set()
        if normalized and normalized.strip():
            terms.update(normalized.split())
        for part in query.split():
            if part.strip():
                terms.add(part.strip())
        return {t for t in terms if len(t) > 0}

    @staticmethod
    def _chunk_has_query_overlap(content: str, query_terms: set[str]) -> bool:
        """True if content contains at least one of the query terms (substring match)."""
        if not content or not query_terms:
            return True
        content_lower = content.lower()
        for term in query_terms:
            if len(term) < 2:
                continue
            if term in content or term.lower() in content_lower:
                return True
        return False

    def _rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[SearchResultItem]:
        """Rerank candidates using a FlashRank model.

        When a reranker is active, scores are normalized to 0-1 via sigmoid
        and results below SEARCH_SCORE_THRESHOLD are filtered out.
        When no reranker is configured, RRF scores are used and the top
        result's score is used as a reference to filter out low-relevance
        chunks (those scoring less than threshold × best_score).
        """
        if not candidates:
            return []

        self._load_reranker()
        threshold = settings.SEARCH_SCORE_THRESHOLD
        max_per_doc = settings.MAX_CHUNKS_PER_DOCUMENT
        use_reranker = self._reranker is not None

        if settings.SEARCH_DEBUG:
            logger.info(
                "[search] rerank: candidates=%d use_reranker=%s threshold=%.2f max_per_doc=%d",
                len(candidates),
                use_reranker,
                threshold,
                max_per_doc,
            )

        if use_reranker:
            from flashrank import RerankRequest

            # Format passages for FlashRank
            passages = [
                {"id": c["id"], "text": c["content"]}
                for c in candidates
            ]

            rerank_request = RerankRequest(query=query, passages=passages)
            reranked_results = self._reranker.rerank(rerank_request)

            # Map scores back to candidates and normalize via sigmoid
            score_map = {r["id"]: r["score"] for r in reranked_results}
            raw_scores = list(score_map.values())
            if settings.SEARCH_DEBUG and raw_scores:
                logger.info(
                    "[search] rerank: raw_min=%.3f raw_max=%.3f raw_avg=%.3f",
                    min(raw_scores),
                    max(raw_scores),
                    sum(raw_scores) / len(raw_scores),
                )
            for candidate in candidates:
                raw_score = score_map.get(candidate["id"], 0.0)
                candidate["final_score"] = self._sigmoid(float(raw_score))

            candidates.sort(key=lambda c: c["final_score"], reverse=True)
            if settings.SEARCH_DEBUG and candidates:
                final_scores = [c["final_score"] for c in candidates]
                logger.info(
                    "[search] rerank: final_min=%.3f final_max=%.3f best=%.3f",
                    min(final_scores),
                    max(final_scores),
                    candidates[0]["final_score"],
                )
        else:
            # No reranker: use similarity scores (actual relevance) instead of RRF scores
            # Fall back to RRF score if similarity is not available
            for candidate in candidates:
                candidate["final_score"] = candidate.get(
                    "similarity", candidate.get("rrf_score", 0.0)
                )

            # Re-sort by similarity score since order may differ from RRF order
            candidates.sort(key=lambda c: c["final_score"], reverse=True)

        # Demote chunks with no lexical overlap to the query (avoids generic chunks ranking first)
        penalty = settings.SEARCH_NO_OVERLAP_PENALTY
        if penalty > 0 and penalty < 1 and candidates:
            query_terms = self._query_terms_for_overlap(query)
            for c in candidates:
                if not self._chunk_has_query_overlap(c.get("content") or "", query_terms):
                    c["final_score"] = c["final_score"] * penalty
            candidates.sort(key=lambda c: c["final_score"], reverse=True)

        # Build response items with relevance filtering and optional per-document cap
        results: list[SearchResultItem] = []
        best_score = candidates[0]["final_score"] if candidates else 0.0
        doc_counts: dict[str, int] = {}
        dropped_by_score = 0
        dropped_by_cap = 0

        for candidate in candidates:
            if len(results) >= top_k:
                break
            score = round(candidate["final_score"], 4)

            if use_reranker:
                # Absolute threshold: sigmoid scores are 0-1
                if score < threshold:
                    dropped_by_score += 1
                    logger.debug(
                        "Dropping chunk %s (score %.4f < threshold %.2f)",
                        candidate["id"],
                        score,
                        threshold,
                    )
                    continue
            else:
                # Relative threshold: drop if score is less than
                # threshold * best_score (filters out chunks that are
                # much less relevant than the top hit)
                min_score = threshold * best_score
                if best_score > 0 and score < min_score:
                    dropped_by_score += 1
                    logger.debug(
                        "Dropping chunk %s (score %.6f < %.2f × best %.6f = %.6f)",
                        candidate["id"],
                        score,
                        threshold,
                        best_score,
                        min_score,
                    )
                    continue

            # Per-document cap: limit chunks per document so one file doesn't dominate
            doc_id = candidate.get("document_id", "") or ""
            if max_per_doc > 0:
                if doc_counts.get(doc_id, 0) >= max_per_doc:
                    dropped_by_cap += 1
                    logger.debug(
                        "Skipping chunk %s (document %s already has %d chunks)",
                        candidate["id"],
                        doc_id,
                        max_per_doc,
                    )
                    continue
                doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1

            results.append(
                SearchResultItem(
                    chunk_id=candidate["id"],
                    document_id=candidate.get("document_id", ""),
                    document_name=candidate.get("document_name", candidate.get("filename", "")),
                    content=candidate["content"],
                    score=score,
                    metadata=candidate.get("metadata", {}),
                )
            )

        if settings.SEARCH_DEBUG:
            result_ids = [str(r.chunk_id) for r in results]
            result_scores = [r.score for r in results]
            logger.info(
                "[search] filter: kept=%d dropped_score=%d dropped_cap=%d result_scores=%s",
                len(results),
                dropped_by_score,
                dropped_by_cap,
                result_scores,
            )

        return results
