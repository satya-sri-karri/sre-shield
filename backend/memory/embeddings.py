import re
from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class HybridSearchEngine:
    """
    Hybrid Search Engine combining TF-IDF semantic vector representation
    with exact keyword matching and domain-specific SRE boosting.
    """

    CRITICAL_KEYWORDS = [
        "http 500", "http 503", "502 bad gateway", "504 gateway timeout",
        "connection pool exhausted", "connection refused", "timeout",
        "oomkilled", "out of memory", "crashloopbackoff", "memory leak",
        "redis", "postgresql", "kafka", "disk full", "cpu throttle",
        "deadlock", "tls certificate", "circuit breaker", "dns failure"
    ]

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            token_pattern=r'(?u)\b[\w\-\.:/]+\b',
            stop_words='english'
        )
        self.is_fitted = False
        self.corpus_ids: List[str] = []
        self.corpus_texts: List[str] = []
        self.tfidf_matrix = None

    def fit_corpus(self, docs: List[Dict[str, str]]):
        """
        docs: List of dicts with 'id' and 'text'
        """
        if not docs:
            self.is_fitted = False
            self.corpus_ids = []
            self.corpus_texts = []
            self.tfidf_matrix = None
            return

        self.corpus_ids = [doc["id"] for doc in docs]
        self.corpus_texts = [doc["text"] for doc in docs]

        try:
            self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus_texts)
            self.is_fitted = True
        except ValueError:
            # Empty vocabulary or invalid input
            self.is_fitted = False

    def search(self, query: str, top_k: int = 5, service_filter: str = None) -> List[Tuple[str, float]]:
        """
        Returns list of (id, similarity_score) sorted by relevance.
        Score is between 0.0 and 1.0.
        """
        if not self.is_fitted or not self.corpus_texts:
            return []

        # 1. Vector Cosine Similarity
        try:
            query_vec = self.vectorizer.transform([query])
            cos_sims = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        except Exception:
            cos_sims = np.zeros(len(self.corpus_ids))

        # 2. Domain Keyword Boost & Service Matching
        query_lower = query.lower()
        scored_results: List[Tuple[str, float]] = []

        for idx, doc_id in enumerate(self.corpus_ids):
            base_score = float(cos_sims[idx])
            doc_text = self.corpus_texts[idx].lower()

            # Boost if exact critical SRE patterns match
            keyword_bonus = 0.0
            for kw in self.CRITICAL_KEYWORDS:
                if kw in query_lower and kw in doc_text:
                    keyword_bonus += 0.15

            # Boost if service name matches
            if service_filter and service_filter.lower() in doc_text:
                keyword_bonus += 0.20

            final_score = min(base_score + keyword_bonus, 1.0)
            if final_score > 0.10: # Relevance threshold
                scored_results.append((doc_id, round(final_score, 4)))

        # Sort descending by score
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:top_k]
