import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class VectorSearch:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = faiss.IndexFlatL2(384)  # vector size for MiniLM
        self.job_texts = []

    def add_jobs(self, jobs):
        embeddings = self.model.encode([j["description"] for j in jobs])
        self.index.add(np.array(embeddings).astype("float32"))
        self.job_texts = jobs

    def search(self, query_text, top_k=5):
        q_emb = self.model.encode([query_text]).astype("float32")
        D, I = self.index.search(q_emb, top_k)
        return [self.job_texts[i] for i in I[0]]
