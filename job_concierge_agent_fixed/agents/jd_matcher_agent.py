"""Job Description Matcher Agent
Uses TF-IDF vectorization and cosine similarity to compute match score between resume and job descriptions.
"""
from typing import List, Dict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import logging

logger = logging.getLogger(__name__)

class JDMatcher:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=10000)
        self.fitted = False

    def fit(self, documents: List[str]):
        self.vectorizer.fit(documents)
        self.fitted = True
        logger.info("JDMatcher fitted on documents") 

    def score(self, resume_text: str, job_descriptions: List[Dict]) -> List[Dict]:
        # Ensure vectorizer is fitted
        docs = [jd['description'] for jd in job_descriptions]
        if not self.fitted:
            self.fit(docs + [resume_text])
        tfidf = self.vectorizer.transform(docs + [resume_text])
        resume_vec = tfidf[-1]
        job_vecs = tfidf[:-1]
        sims = linear_kernel(resume_vec, job_vecs).flatten()
        results = []
        for jd, s in zip(job_descriptions, sims):
            results.append({
                'job_id': jd['id'],
                'title': jd['title'],
                'company': jd['company'],
                'url': jd['url'],
                'score': float(s),
                'description': jd['description']
            })
        results.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"Scored {len(results)} jobs; top score={results[0]['score'] if results else None}")
        return results
