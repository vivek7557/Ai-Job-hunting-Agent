"""Job Description Matcher Agent (Embedding-based)."""

from typing import List, Dict
import logging
from sentence_transformers import SentenceTransformer, util

logger = logging.getLogger(__name__)

class JDMatcher:
    def __init__(self):
        # Much more accurate than TF-IDF
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Loaded embedding model: all-MiniLM-L6-v2")

    def score(self, resume_text: str, job_descriptions: List[Dict]) -> List[Dict]:

        # Prepare job description list
        docs = [jd["description"] for jd in job_descriptions]

        # Embed all text
        resume_emb = self.model.encode(resume_text, convert_to_tensor=True)
        job_embs = self.model.encode(docs, convert_to_tensor=True)

        # Compute cosine similarity (vectorized)
        similarities = util.cos_sim(resume_emb, job_embs).cpu().numpy()[0]

        results = []
        for jd, score in zip(job_descriptions, similarities):
            results.append({
                "job_id": jd["id"],
                "title": jd["title"],
                "company": jd["company"],
                "url": jd["url"],
                "score": float(score),
                "description": jd["description"]
            })

        results.sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"Scored {len(results)} jobs; top score={results[0]['score']:.4f}")
        return results
