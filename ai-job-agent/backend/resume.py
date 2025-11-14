import re
from typing import Dict, Any


# Choose embedding backend: OpenAI or sentence-transformers
USE_OPENAI = True
OPENAI_API_KEY = None # set from env in production


# Minimal parser for demo (use pdfminer/pyresparser/spacy in prod)


def parse_resume_text(filename: str, data: bytes) -> str:
# naive fallback: try decode
try:
text = data.decode('utf-8')
except Exception:
text = ' '.join(re.findall(r"[\w'\-]+", str(data)))
return text




def analyze_resume_vs_jd(resume_text: str, job_description: str) -> Dict[str, Any]:
"""Return a dict: score, matches, missing, suggestions (GPT-style)"""
# simple keyword overlap for demo
def extract_keywords(text):
tokens = re.findall(r"[A-Za-z]+", text.lower())
stop = {'and', 'with', 'the', 'a', 'an', 'in', 'for', 'to', 'of'}
return set(t for t in tokens if t not in stop and len(t) > 2)


resume_kw = extract_keywords(resume_text)
jd_kw = extract_keywords(job_description)
matches = sorted(list(resume_kw & jd_kw))
missing = sorted(list(jd_kw - resume_kw))


# naive score
score = int(len(matches) / max(1, len(jd_kw)) * 100)


suggestions = []
if score < 50:
suggestions.append('Add missing technical keywords and quantify achievements.')
else:
suggestions.append('Good keyword match; tailor summary to the role.')


return {
'score': score,
'matches': matches[:50],
'missing': missing[:50],
'suggestions': suggestions,
}
