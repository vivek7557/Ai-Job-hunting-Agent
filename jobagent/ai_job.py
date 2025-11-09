import os, re, sqlite3, smtplib, hashlib, yaml, requests, traceback
from email.mime.text import MIMEText
from datetime import datetime
from urllib.parse import urlparse
from dateutil import parser as dateparser
from bs4 import BeautifulSoup

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "jobs.db")
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

TITLES    = [t.lower() for t in CFG["preferences"]["titles"]]
INCLUDE   = [k.lower() for k in CFG["preferences"]["include_keywords"]]
EXCLUDE   = [k.lower() for k in CFG["preferences"]["exclude_keywords"]]
LOCATIONS = [l.lower() for l in CFG["preferences"]["locations"]]
SOURCES   = CFG["sources"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    con = db(); cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs(
        id TEXT PRIMARY KEY,
        title TEXT,
        company TEXT,
        location TEXT,
        link TEXT,
        source TEXT,
        date TEXT,
        description TEXT,
        score REAL DEFAULT 0,
        skills TEXT DEFAULT '',
        status TEXT DEFAULT 'new'
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS runs(
        run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_time TEXT,
        fetched INTEGER,
        inserted INTEGER
    )""")
    con.commit(); con.close()

def sha1(x: str) -> str:
    return hashlib.sha1(x.encode("utf-8")).hexdigest()

def _clean_html(text: str) -> str:
    if not text: return ""
    return BeautifulSoup(text, "lxml").get_text(" ", strip=True)

def fetch_rss(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"[RSS ERROR] {url} - {r.status_code}")
            return []
        soup = BeautifulSoup(r.text, "xml")
        items = []
        for it in soup.find_all("item"):
            title = it.title.text if it.title else ""
            link  = (it.link.text if it.link else "") or (it.guid.text if it.guid else "")
            desc  = _clean_html(it.description.text) if it.description else ""
            raw_date = (it.pubDate.text if it.pubDate else None) or (it.date.text if it.find("date") else None)
            try:
                iso_date = dateparser.parse(raw_date).isoformat() if raw_date else None
            except Exception:
                iso_date = None
            host = urlparse(link).netloc.replace("www.", "") if link else urlparse(url).netloc.replace("www.", "")
            # naive location guess from text
            loc_guess = ""
            for L in LOCATIONS:
                if L in f"{title.lower()} {desc.lower()}":
                    loc_guess = L.title(); break
            items.append({
                "title": title.strip(),
                "company": host,
                "location": loc_guess,
                "link": link.strip(),
                "source": url,
                "date": iso_date,
                "description": desc.strip()
            })
        return items
    except Exception as e:
        print(f"[RSS ERROR] {url}: {e}")
        return []

def fetch_all():
    all_items = []
    for url in SOURCES:
        all_items.extend(fetch_rss(url))
    return all_items

def basic_score(title, description):
    t = (title or "").lower()
    d = (description or "").lower()
    text = f"{t} {d}"
    score = 0
    if any(tt in t for tt in TITLES): score += 5
    if any(lc in text for lc in LOCATIONS): score += 2
    score += sum(2 for k in INCLUDE if k in text)
    score -= sum(4 for k in EXCLUDE if k in text)
    return float(score)

COMMON_SKILLS = set([
    "python","sql","pandas","numpy","scikit-learn","tensorflow","pytorch",
    "transformers","huggingface","nlp","llm","deep learning","mlflow",
    "airflow","docker","kubernetes","spark","gcp","aws","azure","fastapi"
])

def tfidf_suggest_skills(jobs):
    if not jobs: return {}
    if not SKLEARN_AVAILABLE:
        out = {}
        for j in jobs:
            text = f"{j['title']} {j['description']}".lower()
            hits = sorted({s for s in COMMON_SKILLS if s in text})
            out[j["id"]] = hits[:12]
        return out

    docs = [f"{j['title']} {j['description']}" for j in jobs]
    vec = TfidfVectorizer(stop_words="english", max_features=5000, ngram_range=(1,2))
    X = vec.fit_transform(docs)
    terms = vec.get_feature_names_out()
    suggestions = {}
    for i, j in enumerate(jobs):
        row = X[i].toarray().ravel()
        top_idx = row.argsort()[-20:][::-1]
        tops = [terms[k] for k in top_idx]
        picks = [t for t in tops if len(t) > 2 and (t in COMMON_SKILLS or re.search(r"[a-zA-Z]+", t))]
        suggestions[j["id"]] = list(dict.fromkeys(picks))[:12]
    return suggestions

def insert_jobs(items):
    con = db(); cur = con.cursor()
    for it in items:
        it["id"] = sha1((it.get("title") or "") + (it.get("link") or ""))
        it["score"] = basic_score(it.get("title"), it.get("description"))
    sugg = tfidf_suggest_skills(items)
    inserted = 0
    for it in items:
        skills = ", ".join(sugg.get(it["id"], []))
        try:
            cur.execute("""
            INSERT INTO jobs(id,title,company,location,link,source,date,description,score,skills)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (it["id"], it.get("title",""), it.get("company",""), it.get("location",""),
             it.get("link",""), it.get("source",""), it.get("date"), it.get("description",""),
             it.get("score",0.0), skills))
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    con.commit(); con.close()
    return inserted

def send_daily_email():
    if not CFG.get("email", {}).get("enabled"): return
    conf = CFG["email"]
    con = db(); cur = con.cursor()
    cur.execute("""SELECT title,company,location,link,score,skills
                   FROM jobs
                   WHERE datetime(date) >= datetime('now','-1 day')
                   ORDER BY score DESC LIMIT 10""")
    rows = cur.fetchall(); con.close()
    if not rows: return
    lines = []
    for t,c,l,link,score,skills in rows:
        lines.append(f"🎯 {t} — {c} — {l}\nScore: {score:.1f}\nSkills: {skills}\nApply: {link}\n")
    body = "\n\n".join(lines)
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Daily ML/AI Job Matches (last 24h)"
    msg["From"] = conf["sender_email"]; msg["To"] = conf["to"]
    try:
        s = smtplib.SMTP(conf["smtp_host"], conf["smtp_port"])
        s.starttls(); s.login(conf["sender_email"], conf["sender_password"])
        s.sendmail(conf["sender_email"], [conf["to"]], msg.as_string()); s.quit()
        print("[email] Daily summary sent.")
    except Exception:
        print("[email] Failed:\n", traceback.format_exc())

def run_once():
    print("🔎 Fetching jobs…")
    items = fetch_all()
    ins = insert_jobs(items)
    con = db(); cur = con.cursor()
    cur.execute("INSERT INTO runs(run_time,fetched,inserted) VALUES(?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), len(items), ins))
    con.commit(); con.close()
    print(f"✅ Fetched={len(items)} | Inserted new={ins}")

if __name__ == "__main__":
    import sys
    init_db()
    role = sys.argv[1] if len(sys.argv) >= 2 else None   # reserved (not used in RSS)
    location = sys.argv[2] if len(sys.argv) >= 3 else None
    print(f"\n🚀 Starting AI Job Agent {'for ' + role if role else ''}{' in ' + location if location else ''} ...\n")
    run_once()
    # quick sanity count
    con = sqlite3.connect(DB_PATH)
    total = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]; con.close()
    print(f"🗂️ Total jobs in DB: {total}\n")
