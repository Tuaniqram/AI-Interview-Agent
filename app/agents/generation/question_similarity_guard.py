"""Question novelty guard for AURA interview generation.

Attempts to detect duplicate or too-similar questions using embeddings when
available, falling back to deterministic lexical similarity otherwise.
"""
import logging
from typing import Iterable

from app.agents.generation.question_memory import semantic_similarity, match_topics

logger = logging.getLogger(__name__)

DEFAULT_SIMILARITY_THRESHOLD = 0.85


class QuestionSimilarityGuard:
    def __init__(self, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD):
        self.similarity_threshold = float(similarity_threshold)
        self.matched_text = ""
        self.similarity_score = 0.0
        self.used_embedding = False

    def is_duplicate(self, new_question: str, previous_questions: Iterable[str]) -> tuple[bool, dict]:
        new_question = (new_question or "").strip()
        questions = [str(q).strip() for q in (previous_questions or []) if str(q).strip()]
        if not new_question or not questions:
            self.similarity_score = 0.0
            self.matched_text = ""
            return False, {}

        # Try embeddings first when available and the model can be loaded.
        similarity, matched = self._embedding_similarity(new_question, questions)
        if similarity is None:
            similarity, matched = self._lexical_similarity(new_question, questions)
            self.used_embedding = False
        else:
            self.used_embedding = True

        self.similarity_score = round(similarity, 4)
        self.matched_text = matched
        if self.similarity_score >= self.similarity_threshold:
            return True, {
                "kind": "similar",
                "against": matched,
                "similarity": self.similarity_score,
            }

        q_topics = match_topics(new_question)
        if len(q_topics) >= 2:
            for prev in questions:
                shared = q_topics & match_topics(prev)
                if len(shared) >= 2:
                    self.similarity_score = 1.0
                    self.matched_text = prev
                    return True, {
                        "kind": "topic_repeat",
                        "against": prev,
                        "topics": sorted(shared),
                    }

        return False, {}

    def _lexical_similarity(self, new_question: str, questions: Iterable[str]) -> tuple[float, str]:
        best = 0.0
        best_text = ""
        for prev in questions:
            score = semantic_similarity(new_question, prev)
            if score > best:
                best = score
                best_text = prev
        return best, best_text

    def _embedding_similarity(self, new_question: str, questions: Iterable[str]) -> tuple[float | None, str]:
        try:
            from app.rag.pinecone_store import get_embedding

            embedder = get_embedding()
            new_vec = embedder.embed_query(new_question)
            candidate_vecs = embedder.embed_documents(list(questions))
            best = 0.0
            best_text = ""
            for prev, vec in zip(questions, candidate_vecs):
                if not new_vec or not vec:
                    continue
                score = self._cosine_similarity(new_vec, vec)
                if score > best:
                    best = score
                    best_text = prev
            return best, best_text
        except Exception as exc:
            logger.debug("Embedding similarity unavailable: %s", exc)
            return None, ""

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))
