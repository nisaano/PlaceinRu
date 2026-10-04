"""Small deterministic BM25 lexical baseline for the local fixture catalogue."""
import math
import re
from collections import Counter

from mrt_ai.contracts.catalog import Candidate, PlaceSearchHit

TOKEN_PATTERN = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)
RUSSIAN_SUFFIXES = tuple(sorted({
    "ическими", "ического", "ической", "ический", "ические", "ическую", "ическая",
    "иями", "ями", "ами", "его", "ого", "ему", "ому", "ими", "ыми", "ать", "ять",
    "ться", "иться", "аться", "енный", "ённый", "ован", "еван", "остью",
    "ость", "ение", "ения", "ений", "ого", "ему", "ыми", "ими", "ая", "яя", "ое",
    "ее", "ые", "ие", "ый", "ий", "ой", "ую", "юю", "ых", "их", "ом", "ем",
    "ам", "ям", "ах", "ях", "ов", "ев", "ей", "а", "я", "ы", "и", "е", "у",
    "ю", "о", "ь",
}, key=len, reverse=True))


def tokenize(text: str) -> list[str]:
    tokens = []
    for match in TOKEN_PATTERN.findall(text.casefold().replace("ё", "е")):
        if len(match) > 4:
            for suffix in RUSSIAN_SUFFIXES:
                if match.endswith(suffix) and len(match) - len(suffix) >= 3:
                    match = match[:-len(suffix)]
                    break
            if match.endswith(("н", "ск")) and len(match) > 5:
                match = match[:-1] if match.endswith("н") else match[:-2]
        match = {"музе": "музей", "пешком": "пеш", "пеш": "пеш"}.get(match, match)
        tokens.append(match)
    return tokens


class BM25PlaceSearch:
    def __init__(self, candidates: list[Candidate], k1: float = 1.5, b: float = 0.75):
        self.candidates = candidates
        self.k1 = k1
        self.b = b
        self.documents = []
        for candidate in candidates:
            weighted_tokens = (
                tokenize(candidate.name) * 3
                + tokenize(" ".join(candidate.tags)) * 3
                + tokenize(candidate.description)
            )
            self.documents.append(Counter(weighted_tokens))
        self.lengths = [sum(document.values()) for document in self.documents]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 0
        self.document_frequency = Counter(
            token for document in self.documents for token in document
        )

    def search(self, query: str, top_k: int = 5) -> list[PlaceSearchHit]:
        query_terms = list(dict.fromkeys(tokenize(query)))
        if not query_terms or not self.documents:
            return []
        hits = []
        document_count = len(self.documents)
        for candidate, document, length in zip(self.candidates, self.documents, self.lengths):
            matched = [term for term in query_terms if document.get(term, 0)]
            if not matched:
                continue
            score = 0.0
            for term in matched:
                frequency = document[term]
                document_frequency = self.document_frequency[term]
                inverse_frequency = math.log1p(
                    (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * length / self.average_length
                )
                score += inverse_frequency * frequency * (self.k1 + 1) / denominator
            hits.append(PlaceSearchHit(
                candidate=candidate,
                score=round(score, 6),
                matched_terms=matched,
            ))
        hits.sort(key=lambda hit: (-hit.score, hit.candidate.object_id))
        return hits[:top_k]
