"""Search service for vector, full-text, and hybrid retrieval."""

import asyncio
import logging

import aiosqlite
import sqlite_vec

from src.db import (
    ChunkSearchResult,
    ContentType,
    SearchResultItem,
    configure_connection,
)
from src.exceptions import EmbeddingError, SearchError

# Direct sub-module import to avoid circular import: src.services.__init__ imports
# SearchService from this module, so we cannot import from src.services here.
from src.services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

MAX_LIMIT = 100
MIN_LIMIT = 1


def reciprocal_rank_fusion(
    vector_results: list[ChunkSearchResult],
    fts_results: list[ChunkSearchResult],
    k: int = 60,
) -> list[ChunkSearchResult]:
    """Fuse ranked result lists using Reciprocal Rank Fusion (RRF).

    Args:
        vector_results: Ranked vector-search results (best first).
        fts_results: Ranked full-text-search results (best first).
        k: RRF smoothing constant.

    Returns:
        Deduplicated fused results sorted by fused score descending and
        chunk_id ascending for deterministic tie-breaking. Scores are
        normalized to [0, 1] so the top result always has score=1.0.
    """
    if k <= 0:
        raise ValueError("RRF parameter k must be positive")

    fused_scores: dict[str, float] = {}
    canonical_results: dict[str, ChunkSearchResult] = {}

    for rank, result in enumerate(vector_results, start=1):
        fused_scores[result.chunk_id] = fused_scores.get(result.chunk_id, 0.0) + (
            1.0 / (k + rank)
        )
        canonical_results.setdefault(result.chunk_id, result)

    for rank, result in enumerate(fts_results, start=1):
        fused_scores[result.chunk_id] = fused_scores.get(result.chunk_id, 0.0) + (
            1.0 / (k + rank)
        )
        canonical_results.setdefault(result.chunk_id, result)

    fused_results = [
        ChunkSearchResult(
            chunk_id=chunk_id,
            item_id=canonical_results[chunk_id].item_id,
            content=canonical_results[chunk_id].content,
            score=score,
        )
        for chunk_id, score in fused_scores.items()
    ]
    fused_results.sort(key=lambda result: (-result.score, result.chunk_id))

    # Normalize RRF scores to [0, 1] so they are comparable to vector/FTS scores.
    # Raw RRF scores cluster near 0 (e.g. 0.016 for rank-1 with k=60), which would
    # make hybrid results appear near-zero to API consumers reading the score field.
    if fused_results:
        max_score = fused_results[0].score  # already sorted descending
        if max_score > 0:
            fused_results = [
                r.model_copy(update={"score": r.score / max_score})
                for r in fused_results
            ]

    return fused_results


class SearchService:
    """Hybrid search service combining vector and FTS retrieval."""

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    async def vector_search(
        self,
        query: str,
        db: aiosqlite.Connection,
        limit: int = 20,
        query_embedding: list[float] | None = None,
    ) -> list[ChunkSearchResult]:
        """Run vector similarity search against sqlite-vec."""
        normalized_query = self._validate_query(query)
        normalized_limit = self._normalize_limit(limit)

        try:
            embedding = (
                query_embedding
                if query_embedding is not None
                else await self._embedding_service.embed_query(normalized_query, db=db)
            )
            serialized_embedding = sqlite_vec.serialize_float32(embedding)

            cursor = await db.execute(
                """
                SELECT v.chunk_id, v.distance
                FROM vec_chunks v
                WHERE v.embedding MATCH ? AND k = ?
                ORDER BY v.distance
                """,
                [serialized_embedding, normalized_limit],
            )
            vec_rows = await cursor.fetchall()
            if not vec_rows:
                return []

            chunk_ids = [row["chunk_id"] for row in vec_rows]
            placeholders = ",".join("?" for _ in chunk_ids)
            cursor = await db.execute(
                f"SELECT id, item_id, content FROM chunks WHERE id IN ({placeholders})",
                chunk_ids,
            )
            chunk_rows = await cursor.fetchall()
            chunk_by_id = {row["id"]: row for row in chunk_rows}

            results: list[ChunkSearchResult] = []
            for row in vec_rows:
                chunk_id = row["chunk_id"]
                chunk = chunk_by_id.get(chunk_id)
                if chunk is None:
                    logger.debug(
                        "Skipping vector hit for missing chunk row: chunk_id=%s",
                        chunk_id,
                    )
                    continue

                score = _clamp_score(1.0 - (float(row["distance"]) / 2.0))
                results.append(
                    ChunkSearchResult(
                        chunk_id=chunk_id,
                        item_id=chunk["item_id"],
                        content=chunk["content"],
                        score=score,
                    )
                )

            return results
        except SearchError:
            logger.debug(
                "Propagating SearchError from vector_search: query=%s", normalized_query
            )
            raise
        except EmbeddingError as e:
            raise SearchError(
                f"Vector search failed: {e}",
                query=normalized_query,
                step="vector_search",
            ) from e
        except Exception as e:
            logger.exception("Unexpected vector search failure")
            raise SearchError(
                f"Vector search failed: {e}",
                query=normalized_query,
                step="vector_search",
            ) from e

    async def fts_search(
        self, query: str, db: aiosqlite.Connection, limit: int = 20
    ) -> list[ChunkSearchResult]:
        """Run full-text search against the FTS5 index."""
        normalized_query = self._validate_query(query)
        normalized_limit = self._normalize_limit(limit)
        sanitized_query = self._sanitize_fts_query(normalized_query)

        try:
            cursor = await db.execute(
                """
                SELECT
                    c.id AS chunk_id,
                    c.item_id AS item_id,
                    c.content AS content,
                    bm25(chunks_fts) AS bm25_score
                FROM chunks_fts
                JOIN chunks c ON c.rowid = chunks_fts.rowid
                WHERE chunks_fts MATCH ?
                -- bm25() returns negative values; most-relevant row has the most-negative
                -- score. ORDER BY ASC puts the best match first. Do not change to DESC.
                ORDER BY bm25_score ASC
                LIMIT ?
                """,
                [sanitized_query, normalized_limit],
            )
            rows = await cursor.fetchall()
            if not rows:
                return []

            bm25_scores = [float(row["bm25_score"]) for row in rows]
            min_score = min(bm25_scores)
            max_score = max(bm25_scores)
            range_val = max_score - min_score

            results: list[ChunkSearchResult] = []
            for row in rows:
                row_score = float(row["bm25_score"])
                if range_val == 0:
                    normalized_score = 1.0
                else:
                    normalized_score = (max_score - row_score) / range_val

                results.append(
                    ChunkSearchResult(
                        chunk_id=row["chunk_id"],
                        item_id=row["item_id"],
                        content=row["content"],
                        score=_clamp_score(normalized_score),
                    )
                )

            results.sort(key=lambda result: (-result.score, result.chunk_id))
            return results
        except SearchError:
            logger.debug(
                "Propagating SearchError from fts_search: query=%s", normalized_query
            )
            raise
        except Exception as e:
            logger.exception("Unexpected FTS search failure")
            raise SearchError(
                f"FTS search failed: {e}",
                query=normalized_query,
                step="fts_search",
            ) from e

    async def hybrid_search(
        self, query: str, db: aiosqlite.Connection, limit: int = 20
    ) -> list[ChunkSearchResult]:
        """Run vector and FTS search on separate DB connections, then fuse with RRF."""
        # Re-validation here is intentional: public methods are always safe to call
        # directly. Sub-calls re-validate the already-normalized values, which is
        # harmless (idempotent) and keeps each method independently defensible.
        normalized_query = self._validate_query(query)
        normalized_limit = self._normalize_limit(limit)
        secondary_db: aiosqlite.Connection | None = None

        try:
            db_path = await self._resolve_main_db_path(db)
            if db_path is None:
                logger.debug(
                    "Unable to open secondary DB connection; falling back to "
                    "single-connection hybrid search."
                )
                vector_results = await self.vector_search(
                    normalized_query, db=db, limit=normalized_limit
                )
                fts_results = await self.fts_search(
                    normalized_query, db=db, limit=normalized_limit
                )
            else:
                secondary_db = await self._open_secondary_read_connection(db_path)
                vector_out, fts_out = await asyncio.gather(
                    self.vector_search(normalized_query, db=db, limit=normalized_limit),
                    self.fts_search(
                        normalized_query,
                        db=secondary_db,
                        limit=normalized_limit,
                    ),
                    return_exceptions=True,
                )
                if isinstance(vector_out, BaseException):
                    raise vector_out
                if isinstance(fts_out, BaseException):
                    raise fts_out
                vector_results = vector_out
                fts_results = fts_out

            fused_results = reciprocal_rank_fusion(vector_results, fts_results)
            return fused_results[:normalized_limit]
        except SearchError:
            raise
        except Exception as e:
            logger.exception("Unexpected hybrid search failure")
            raise SearchError(
                f"Hybrid search failed: {e}",
                query=normalized_query,
                step="hybrid_search",
            ) from e
        finally:
            if secondary_db is not None:
                await secondary_db.close()

    @staticmethod
    async def enrich_results(
        results: list[ChunkSearchResult], db: aiosqlite.Connection
    ) -> list[SearchResultItem]:
        """Attach item metadata and produce API-facing search results."""
        if not results:
            return []

        try:
            # dict.fromkeys preserves insertion order while deduplicating item_ids
            item_ids = list(dict.fromkeys(result.item_id for result in results))
            placeholders = ",".join("?" for _ in item_ids)
            cursor = await db.execute(
                f"SELECT id, title, content_type FROM items WHERE id IN ({placeholders})",
                item_ids,
            )
            item_rows = await cursor.fetchall()
            item_by_id = {row["id"]: row for row in item_rows}

            enriched: list[SearchResultItem] = []
            for result in results:
                item = item_by_id.get(result.item_id)
                if item is None:
                    logger.debug(
                        "Skipping search result for missing item row: item_id=%s",
                        result.item_id,
                    )
                    continue

                enriched.append(
                    SearchResultItem(
                        item_id=result.item_id,
                        item_title=item["title"],
                        content_type=ContentType(item["content_type"]),
                        chunk_id=result.chunk_id,
                        chunk_content=result.content,
                        score=_clamp_score(float(result.score)),
                        rank=len(enriched) + 1,
                    )
                )

            return enriched
        except SearchError:
            raise
        except Exception as e:
            logger.exception("Unexpected result enrichment failure")
            raise SearchError(
                f"Result enrichment failed: {e}",
                step="enrich_results",
            ) from e

    @staticmethod
    def _normalize_limit(limit: int) -> int:
        """Clamp requested limit to supported range."""
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise SearchError(
                "Search limit must be an integer",
                query=repr(limit),
                step="validate_limit",
            )
        return max(MIN_LIMIT, min(limit, MAX_LIMIT))

    @staticmethod
    def _validate_query(query: str) -> str:
        """Normalize and validate incoming query text."""
        if not isinstance(query, str):
            raise SearchError(
                "Search query must be a string",
                query=repr(query),
                step="validate_query",
            )
        normalized = query.strip()
        if not normalized:
            raise SearchError(
                "Search query must not be blank",
                query=repr(query),
                step="validate_query",
            )
        return normalized

    @staticmethod
    def _sanitize_fts_query(query: str) -> str:
        """Escape and quote query terms to prevent malformed MATCH syntax.

        Assumes query is non-blank (guaranteed by _validate_query).
        """
        words = query.strip().split()
        escaped_words = [word.replace('"', '""') for word in words]
        return " ".join(f'"{word}"' for word in escaped_words)

    @staticmethod
    async def _resolve_main_db_path(db: aiosqlite.Connection) -> str | None:
        """Return the main database file path for the active connection."""
        cursor = await db.execute("PRAGMA database_list")
        rows = await cursor.fetchall()

        for row in rows:
            if isinstance(row, aiosqlite.Row):
                db_name = row["name"]
                db_file = row["file"]
            else:
                db_name = row[1]
                db_file = row[2]

            if db_name == "main":
                if not db_file or db_file == ":memory:":
                    return None
                return str(db_file)

        return None

    @staticmethod
    async def _open_secondary_read_connection(db_path: str) -> aiosqlite.Connection:
        """Open a second read-capable connection for parallel search."""
        secondary_db = await aiosqlite.connect(db_path)
        try:
            await configure_connection(secondary_db)
            return secondary_db
        except Exception:
            await secondary_db.close()
            raise


def _clamp_score(score: float) -> float:
    """Clamp search scores to [0, 1] range."""
    return max(0.0, min(1.0, score))
