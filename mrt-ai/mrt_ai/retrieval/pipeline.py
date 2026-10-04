"""MRT-AI-owned orchestration for lexical and embedding place retrieval."""
from dataclasses import dataclass
from typing import Literal

from mrt_ai.contracts.catalog import Candidate, PlaceSearchHit
from mrt_ai.retrieval.bm25 import BM25PlaceSearch
from mrt_ai.retrieval.encoders.sbert import LocalSbertPlaceSearch, RANKING_VERSION

RankingMethod = Literal["bm25", "embedding"]
RANKING_VERSIONS = {
    "bm25": "bm25-lexical-v1",
    "embedding": RANKING_VERSION,
}


@dataclass(frozen=True)
class RetrievalResult:
    ranking_version: str
    results: list[PlaceSearchHit]
    warning: str


class MrtAiRetrievalPipeline:
    def __init__(self, embedding_searcher: LocalSbertPlaceSearch):
        self.embedding_searcher = embedding_searcher

    @staticmethod
    def version_for(ranking_method: RankingMethod) -> str:
        return RANKING_VERSIONS[ranking_method]

    def search(
        self,
        query: str,
        candidates: list[Candidate],
        top_k: int,
        ranking_method: RankingMethod,
    ) -> RetrievalResult:
        if ranking_method == "embedding":
            return RetrievalResult(
                ranking_version=self.version_for(ranking_method),
                results=self.embedding_searcher.search(query, candidates, top_k),
                warning=(
                    "Семантическое ранжирование использует локальную SBERT-модель; "
                    "каталог остаётся полностью синтетическим."
                ),
            )
        if ranking_method == "bm25":
            return RetrievalResult(
                ranking_version=self.version_for(ranking_method),
                results=BM25PlaceSearch(candidates).search(query, top_k),
                warning=(
                    "Ранжирование — лексический BM25 baseline, не нейросетевая "
                    "семантическая модель."
                ),
            )
        raise ValueError(f"Unsupported ranking method: {ranking_method}")
