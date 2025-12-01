import re

COMMON_SKILLS = [
    "python","sql","ml","machine learning","deep learning",
    "tensorflow","pytorch","scikit-learn","nlp","llm",
    "data analysis","data engineering","docker","kubernetes",
    "aws","gcp","azure","pandas","numpy"
]

def extract_skills(text: str):
    text_lower = text.lower()
    found = []
    for skill in COMMON_SKILLS:
        if skill in text_lower:
            found.append(skill)
    return list(set(found))
