import os, re, json, time, subprocess, hashlib, textwrap
try:
date = dateparser.parse(date).isoformat()
except Exception:
pass
items.append({
"title": title,
"link": link,
"description": BeautifulSoup(desc, "lxml").text,
"date": date,
"source": url,
})
elif isinstance(data, dict) and "jobs" in data:
for d in data["jobs"]:
title = d.get("title", "(no title)")
desc = d.get("content") or d.get("description") or ""
link = d.get("absolute_url") or d.get("url")
date = d.get("updated_at") or d.get("created_at")
if date:
try:
date = dateparser.parse(date).isoformat()
except Exception:
pass
items.append({
"title": title,
"link": link,
"description": BeautifulSoup(desc, "lxml").text,
"date": date,
"source": url,
})
else:
# Generic: flatten top level
for k, v in (data.items() if isinstance(data, dict) else []):
if isinstance(v, dict):
title = v.get("title", k)
desc = v.get("description", "")
link = v.get("url")
items.append({"title": title, "link": link, "description": desc, "date": None, "source": url})
return items




def fetch_lever(subdomain):
url = f"https://jobs.lever.co/{subdomain}.json"
return fetch_json(url)




def fetch_greenhouse(board_token):
url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
return fetch_json(url)




def fetch_ashby(org):
url = f"https://jobs.ashbyhq.com/api/org/{org}/jobs"
return fetch_json(url)


# ──────────────────────────────────────────────────────────────────────────────
# NLP / Scoring (lightweight, no ML dependency)
# ──────────────────────────────────────────────────────────────────────────────


STOPWORDS = set("""
a an the and or of to for with in on at by from as is are were be been being
only plus years experience strong excellent communication leadership
""".split())




def load_skillset(path="skills.txt"):
if not os.path.exists(path):
return set()
with open(path, "r", encoding="utf-8") as f:
return set([s.strip().lower() for s in f if s.strip()])




CANON_SKILLS = load_skillset()




def tokenize(text):
# simple tokens, keep words & numbers
toks = re.findall(r"[a-zA-Z0-9+#.]+", (text or "").lower())
return [