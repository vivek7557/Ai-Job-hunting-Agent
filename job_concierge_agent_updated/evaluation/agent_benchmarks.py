"""Simple evaluation utilities for JD matching quality (mocked)
Real evaluation should compare predicted matches to labeled ground truth.
"""
from typing import List, Dict
import numpy as np

def precision_at_k(preds: List[Dict], ground_truth: List[str], k: int = 5) -> float:
    topk = [p['job_id'] for p in preds[:k]]
    hits = sum(1 for t in topk if t in ground_truth)
    return hits / k

if __name__ == '__main__':
    # Example usage (mock)
    preds = [{'job_id':'job_1'},{'job_id':'job_3'},{'job_id':'job_5'}]
    gt = ['job_3','job_5']
    print('Precision@3:', precision_at_k(preds, gt, k=3))
