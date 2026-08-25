import re
import threading
from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.real_mplads.loader import RealMPLADSLoader, get_real_data_loader


# Boilerplate administrative and geographic stopwords
GEO_BOILERPLATE_PATTERNS = [
    r"\bvillage\b", r"\bgram\b", r"\bpanchayat\b", r"\bgp\b", r"\bblock\b", r"\bmandal\b",
    r"\bdistrict\b", r"\bdist\b", r"\bward\b", r"\bno\b", r"\bh/o\b", r"\bw/no\b",
    r"\bprakhand\b", r"\bcolony\b", r"\bnagar\b", r"\bstate\b", r"\btown\b", r"\bcity\b",
    r"\btehsil\b", r"\btaluka\b", r"\bconstituency\b", r"\bcontact\b", r"\bmob\b", r"\bphone\b",
    r"\bhouse\b", r"\bresidence\b", r"\bnear\b", r"\bunder\b", r"\bfrom\b", r"\bto\b",
    r"\band\b", r"\bthe\b", r"\bof\b", r"\bin\b", r"\bat\b"
]


def clean_work_description(text: str) -> str:
    """
    Cleans work description by stripping administrative/geographic boilerplate tokens
    while strictly preserving asset nouns and work terms.
    """
    t = (text or "").lower()
    for pattern in GEO_BOILERPLATE_PATTERNS:
        t = re.sub(pattern, " ", t)
    t = re.sub(r"[^a-zA-Z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


class RealMPLADSSearchIndex:
    """
    In-memory TF-IDF n-gram search index for real MPLADS work descriptions.
    Uses cleaned descriptions (free of geographic boilerplate) and is precomputed once upon startup.
    """
    _instance: Optional["RealMPLADSSearchIndex"] = None
    _lock = threading.Lock()

    def __init__(self, loader: Optional[RealMPLADSLoader] = None):
        self.loader = loader or get_real_data_loader()
        self.rec_vectorizer: Optional[TfidfVectorizer] = None
        self.rec_tfidf_matrix = None
        self.comp_vectorizer: Optional[TfidfVectorizer] = None
        self.comp_tfidf_matrix = None
        self._is_indexed = False

    def build_index(self, force_rebuild: bool = False) -> None:
        if self._is_indexed and not force_rebuild:
            return

        with self._lock:
            if self._is_indexed and not force_rebuild:
                return

            self.loader.load_all()

            # 1. Index Recommended Works using cleaned descriptions
            if not self.loader.recommended_df.empty:
                descriptions = self.loader.recommended_df["work_description"].fillna("").astype(str).apply(clean_work_description).tolist()
                self.rec_vectorizer = TfidfVectorizer(
                    stop_words="english",
                    ngram_range=(1, 2),
                    max_features=25000,
                    sublinear_tf=True,
                )
                self.rec_tfidf_matrix = self.rec_vectorizer.fit_transform(descriptions)

            # 2. Index Completed Works using cleaned descriptions
            if not self.loader.completed_df.empty:
                comp_descriptions = self.loader.completed_df["work_description"].fillna("").astype(str).apply(clean_work_description).tolist()
                self.comp_vectorizer = TfidfVectorizer(
                    stop_words="english",
                    ngram_range=(1, 2),
                    max_features=20000,
                    sublinear_tf=True,
                )
                self.comp_tfidf_matrix = self.comp_vectorizer.fit_transform(comp_descriptions)

            self._is_indexed = True

    def compute_similarity(
        self,
        query_text: str,
        dataset: str = "recommended",
    ) -> np.ndarray:
        """
        Computes cosine similarity of cleaned query_text against all documents in the specified dataset.
        Returns 1D numpy array of similarity scores.
        """
        self.build_index()

        vectorizer = self.rec_vectorizer if dataset == "recommended" else self.comp_vectorizer
        tfidf_matrix = self.rec_tfidf_matrix if dataset == "recommended" else self.comp_tfidf_matrix

        cleaned_query = clean_work_description(query_text)
        if vectorizer is None or tfidf_matrix is None or not cleaned_query.strip():
            count = len(self.loader.recommended_records) if dataset == "recommended" else len(self.loader.completed_records)
            return np.zeros(count)

        query_vec = vectorizer.transform([cleaned_query])
        sims = cosine_similarity(query_vec, tfidf_matrix).flatten()
        return sims


_index_instance = RealMPLADSSearchIndex()


def get_real_search_index() -> RealMPLADSSearchIndex:
    if not _index_instance._is_indexed:
        _index_instance.build_index()
    return _index_instance
