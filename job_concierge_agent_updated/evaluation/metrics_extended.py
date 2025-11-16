"""Extended evaluation metrics: recall@k, mean average precision (MAP), nDCG"""
from typing import List, Dict
import math

def recall_at_k(preds: List[Dict], ground_truth: List[str], k: int = 10) -> float:
    topk = [p['job_id'] for p in preds[:k]]
    hits = sum(1 for t in topk if t in ground_truth)
    return hits / len(ground_truth) if ground_truth else 0.0

def average_precision(preds: List[Dict], ground_truth: List[str]) -> float:
    hits = 0
    sum_prec = 0.0
    for i, p in enumerate(preds, start=1):
        if p['job_id'] in ground_truth:
            hits += 1
            sum_prec += hits / i
    return sum_prec / len(ground_truth) if ground_truth else 0.0

def mean_average_precision(list_of_preds: List[List[Dict]], list_of_gts: List[List[str]]) -> float:
    aps = [average_precision(p, gt) for p, gt in zip(list_of_preds, list_of_gts)]
    return sum(aps)/len(aps) if aps else 0.0

def dcg_at_k(relevances: List[int], k: int) -> float:
    dcg = 0.0
    for i, rel in enumerate(relevances[:k], start=1):
        dcg += (2**rel - 1) / math.log2(i+1)
    return dcg

def ndcg_at_k(preds: List[Dict], ground_truth: List[str], k: int = 10) -> float:
    relevances = [1 if p['job_id'] in ground_truth else 0 for p in preds[:k]]
    ideal = sorted(relevances, reverse=True)
    return dcg_at_k(relevances, k) / dcg_at_k(ideal, k) if dcg_at_k(ideal, k) > 0 else 0.0
