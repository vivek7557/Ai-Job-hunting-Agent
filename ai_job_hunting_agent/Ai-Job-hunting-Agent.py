import os, re, json, time, subprocess, hashlib
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from apscheduler.schedulers.blocking import BlockingScheduler
import yaml
from jinja2 import Template


# ─────────────────────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────────────────────
def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def sha1(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

# ─────────────────────────────────────────────────────────────
# Config and State
# ─────────────────────────────────────────────────────────────
CFG = {}
SEEN_PATH = "seen.jsonl"

def load_cfg():
    global CFG
    with open("config.yaml", "r", encoding="utf-8") as f:
        CFG = yaml.safe_load(f)

def load_seen():
    seen = set()
    if os.path.exists(SEEN_PATH):
        with open(SEEN_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    seen.add(json.loads(line)["id"])
                except Exception:
                    pass
    return seen

def mark_seen(item):
    with open(SEEN_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

# ─────────────────────────────────────────────────────────────
# Fetchers
# ─────────────────────────────────────────────────────────────
HEADERS = {"User-Agent": "Mozilla/5.0 (JobAgent/1.0)"}

def fetch_rss(url):
    r = requests.get(url, timeout=30, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "xml")
    items = []
    for it in soup.find_all("item"):
        title = it.title.text if it.title else "(no title)"
        link = it.link.text if it.link else None
        desc = (it.description.text if it.description else "").strip()
        pub = it.pubDate.text if it.pubDate else None
        try:
            date = dateparser.parse(pub).isoformat() if pub else None
        except Exception:
            date = None
        items.append({
            "title": title,
            "link": link,
            "description": BeautifulSoup(desc, "lxml").text,
            "date": date,
            "source": url,
        })
    return items

def fetch_json(url):
    r = requests.get(url, timeout=30, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    items = []

    if isinstance(data, list):
        for d in data:
            if not isinstance(d, dict):
                continue
            title = d.get("position") or d.get("title") or "(no title)"
            desc = d.get("description") or d.get("body") or ""
            link = d.get("url") or d.get("apply_url") or d.get("applyUrl")
            date = d.get("date") or d.get("published_at") or d.get("created_at")
            try:
                date = dateparser.parse(date).isoformat() if date else None
            except Exception:
                date = None
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
            try:
                date = dateparser.parse(date).isoformat() if date else None
            except Exception:
                date = None
            items.append({
                "title": title,
                "link": link,
                "description": BeautifulSoup(desc, "lxml").text,
                "date": date,
                "source": url,
            })
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

# ─────────────────────────────────────────────────────────────
# NLP / Skill Extraction
# ─────────────────────────────────────────────────────────────
STOPWORDS = set("a an the and or of to for with in on at by from as is are were be been being".split())

def load_skillset(path="skills.txt"):
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set([s.strip().lower() for s in f if s.strip()])

CANON_SKILLS = load_skillset()

def tokenize(text):
    toks = re.findall(r"[a-zA-Z0-9+#.]+", (text or "").lower())
    return [t for t in toks if t not in STOPWORDS and len(t) > 1]

def extract_skills(text):
    toks = tokenize(text)
    if not CANON_SKILLS:
        return list(sorted(set([t for t in toks if len(t) > 2])))[:20]
    hits = [t for t in toks if t in CANON_SKILLS]
    seen = set()
    ordered = []
    for h in hits:
        if h not in seen:
            ordered.append(h)
            seen.add(h)
    return ordered

def score_job(job, prefs):
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "").lower()
    text = f"{title}\n{desc}"
    inc = sum(1 for k in prefs.get("include_keywords", []) if k.lower() in text)
    exc = sum(1 for k in prefs.get("exclude_keywords", []) if k.lower() in text)
    title_match = any(t.lower() in title for t in prefs.get("titles", []))
    loc_match = any(l.lower() in text for l in prefs.get("locations", []))
    skills = extract_skills(text)
    score = inc * 3 + (5 if title_match else 0) + (2 if loc_match else 0) - exc * 4 + min(len(skills), 8)
    return max(score, 0), skills

# ─────────────────────────────────────────────────────────────
# Notifications
# ─────────────────────────────────────────────────────────────
def notify_email(cfg, subject, body):
    if not cfg.get("enabled"):
        return
    import smtplib
    from email.mime.text import MIMEText
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = cfg["smtp_user"]
    msg["To"] = cfg["to"]
    s = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"])
    s.starttls()
    s.login(cfg["smtp_user"], cfg["smtp_pass"])
    s.sendmail(cfg["smtp_user"], [cfg["to"]], msg.as_string())
    s.quit()

# ─────────────────────────────────────────────────────────────
# CV Generation
# ─────────────────────────────────────────────────────────────
def render_cv(job, matched_skills):
    if not CFG.get("cv", {}).get("enabled"):
        return None
    base_path = CFG["cv"]["base_resume_md"]
    if not os.path.exists(base_path):
        return None
    with open(base_path, "r", encoding="utf-8") as f:
        tpl = Template(f.read())

    title = job.get("title") or "Target Role"
    company = urlparse(job.get("link") or "").netloc
    data = {
        "name": CFG["user"]["name"],
        "email": CFG["user"]["email"],
        "target_title": title,
        "company": company,
        "matched_skills": matched_skills[:15],
        "top_skills": matched_skills[:8],
        "job_focus": title,
    }

    outdir = CFG["cv"].get("output_dir", "./generated_cvs")
    os.makedirs(outdir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    base = slugify(f"{title}-{company}-{ts}")
    md_path = os.path.join(outdir, f"{base}.md")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(tpl.render(**data))

    return md_path

# ─────────────────────────────────────────────────────────────
# Core Agent
# ─────────────────────────────────────────────────────────────
ADAPTERS = {
    "rss": lambda src: fetch_rss(src["url"]),
    "json": lambda src: fetch_json(src["url"]),
    "lever": lambda src: fetch_lever(src["subdomain"]),
    "greenhouse": lambda src: fetch_greenhouse(src["board_token"]),
    "ashby": lambda src: fetch_ashby(src["org"]),
}

def normalize(job):
    title = job.get("title") or "(no title)"
    link = job.get("link") or job.get("url")
    desc = job.get("description") or job.get("content") or ""
    date = job.get("date")
    jid = sha1(f"{title}|{link}")
    return {"id": jid, "title": title, "link": link, "description": desc, "date": date, "source": job.get("source")}

def search_once():
    prefs = CFG.get("preferences", {})
    seen = load_seen()
    found = []
    for src in CFG.get("sources", []):
        typ = src.get("type")
        if typ not in ADAPTERS:
            continue
        try:
            raw_items = ADAPTERS[typ](src)
        except Exception as e:
            print(f"[err] {src.get('name')}: {e}")
            continue
        for r in raw_items or []:
            job = normalize(r)
            if not job.get("link") or job["id"] in seen:
                continue
            score, skills = score_job(job, prefs)
            job["score"] = score
            job["skills"] = skills
            found.append(job)
    found.sort(key=lambda x: (x.get("score", 0), x.get("date") or ""), reverse=True)
    return found

def format_job_msg(job, cv_path=None):
    title = job.get("title")
    link = job.get("link")
    score = job.get("score")
    skills = ", ".join(job.get("skills", [])[:10])
    msg = f"🔥 {title} [score {score}]\n{link}\nSkills: {skills}"
    if cv_path:
        msg += f"\nTailored CV: {os.path.abspath(cv_path)}"
    return msg

def run_agent_once():
    results = search_once()
    if not results:
        print("No new jobs found this run.")
        return
    email_cfg = CFG.get("notify", {}).get("email", {})
    for job in results[:10]:
        cv_path = render_cv(job, job.get("skills", []))
        msg = format_job_msg(job, cv_path)
        if email_cfg.get("enabled"):
            notify_email(email_cfg, f"New job: {job['title']}", msg)
        print("\n" + msg + "\n")
        mark_seen(job)

# ─────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    load_cfg()
    interval = CFG.get("schedule", {}).get("interval_minutes", 60)
    print(f"[JobAgent] Running every {interval} minutes.")
    run_agent_once()
    scheduler = BlockingScheduler()
    scheduler.add_job(run_agent_once, 'interval', minutes=interval)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[JobAgent] Stopped.")

