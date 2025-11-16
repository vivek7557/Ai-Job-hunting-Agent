"""Resume Parser Agent
Simple parser that accepts text or PDF content (text expected in demo) and extracts a basic skills list.
For production, integrate with a robust resume parser or use OCR for PDFs.
"""
import re, logging
from typing import Dict

logger = logging.getLogger(__name__)

COMMON_SKILLS = ["python","sql","machine learning","nlp","deep learning","aws","docker","kubernetes","pandas","numpy","tensorflow","pytorch","react","node"]

def parse_resume_text(text: str) -> Dict:
    text_low = text.lower()
    skills = [s for s in COMMON_SKILLS if s in text_low]
    # Simple experience extractor (years)
    years = None
    m = re.search(r"(\d+)\+?\s+years", text_low)
    if m:
        years = int(m.group(1))
    parsed = {
        "raw_text": text,
        "skills": skills,
        "years_experience": years
    }
    logger.info(f"Parsed resume: {len(skills)} skills found, years_experience={years}")
    return parsed
