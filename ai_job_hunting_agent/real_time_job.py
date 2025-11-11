"""
AI Job Hunting Agent — Location Fixed + CV Intelligence
--------------------------------------------------------
✅ Instant location updates (India, USA, etc.)
✅ CV upload + JD match scoring
✅ Skill analytics & suggestions
✅ Hourly auto-refresh using latest preferences
✅ Direct job links only (no redirect portals)
"""

import os, sqlite3, threading, time, io, re, hashlib
from datetime import datetime
from urllib.parse import quote_plus
from typing import List, Dict, Any, Tuple
import requests
from bs4 import BeautifulSoup
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Optional PDF/DOCX parsing
try:
    import PyPDF2
except Exception:
    PyPDF2 = None
try:
    import docx
except Exception:
    docx = None

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
APP_NAME = "AI Job Hunting Agent — Pro"
DATABASE_NAME = "job_agent_realtime.db"
DEFAULT_ROLE = "Machine Learning Engineer"
DEFAULT_LOCATION = "India"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

SKILLS = [
    "python","sql","machine learning","deep learning","nlp","transformers","pandas","numpy",
    "scikit-learn","tensorflow","pytorch","keras","xgboost","lightgbm","feature engineering",
    "data analysis","mlops","docker","kubernetes","flask","fastapi","streamlit",
    "aws","azure","gcp","sagemaker","git","linux","tableau","power bi"
]

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    uid TEXT PRIMARY KEY,
    source TEXT,
    job_title TEXT,
    company TEXT,
    location TEXT,
    experience TEXT,
    salary TEXT,
    skills TEXT,
    description TEXT,
    url TEXT,
    posted_time TEXT,
    fetched_at TEXT,
    is_new INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS applied_jobs (
    uid TEXT PRIMARY KEY,
    applied_at TEXT
);
CREATE TABLE IF NOT EXISTS preferences (
    id INTEGER PRIMARY KEY CHECK(id=1),
    role TEXT,
    location TEXT,
    experience TEXT
);
CREATE TABLE IF NOT EXISTS cv_store (
    id INTEGER PRIMARY KEY CHECK(id=1),
    file_name TEXT,
    mime TEXT,
    uploaded_at TEXT,
    text TEXT
);
"""

def init_db():
    with sqlite3.connect(DATABASE_NAME) as c:
        c.executescript(SCHEMA)
        c.commit()

def get_conn():
    return sqlite3.connect(DATABASE_NAME, check_same_thread=False)

def make_uid(source, job_id): return hashlib.md5(f"{source}|{job_id}".encode()).hexdigest()

# ─────────────────────────────────────────────
# SCRAPERS (Simplified + Direct Links)
# ─────────────────────────────────────────────
def scrape_remotive(role: str):
    jobs = []
    try:
        data = requests.get("https://remotive.com/api/remote-jobs",
                            params={"search": role, "limit": 15}, timeout=10).json()
        for j in data.get("jobs", []):
            uid = make_uid("Remotive", str(j.get("id")))
            jobs.append({
                "uid": uid, "source": "Remotive",
                "job_title": j.get("title","N/A"),
                "company": j.get("company_name","N/A"),
                "location": j.get("candidate_required_location","Remote"),
                "experience": "Not specified",
                "salary": j.get("salary","Not disclosed"),
                "skills": ", ".join(j.get("tags",[])[:6]),
                "description": BeautifulSoup(j.get("description",""),"html.parser").get_text()[:600],
                "url": j.get("url",""), "posted_time": j.get("publication_date","")[:10],
                "fetched_at": datetime.now().isoformat(), "is_new": 1
            })
    except Exception: pass
    return jobs

def scrape_arbeitnow(role: str):
    jobs = []
    try:
        data = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=10).json()
        for j in data.get("data", []):
            if role.lower() in j.get("title","").lower():
                uid = make_uid("Arbeitnow", j.get("slug",""))
                jobs.append({
                    "uid": uid, "source": "Arbeitnow",
                    "job_title": j.get("title","N/A"),
                    "company": j.get("company_name","N/A"),
                    "location": j.get("location","Remote"),
                    "experience": "Not specified", "salary": "Not disclosed",
                    "skills": ", ".join(j.get("tags",[])[:6]),
                    "description": j.get("description","")[:600],
                    "url": j.get("url",""), "posted_time": j.get("created_at","")[:10],
                    "fetched_at": datetime.now().isoformat(), "is_new": 1
                })
    except Exception: pass
    return jobs

def scrape_naukri(role: str, loc: str):
    jobs=[]
    try:
        role_s=role.lower().replace(" ","-"); loc_s=loc.lower().replace(" ","-")
        url=f"https://www.naukri.com/{role_s}-jobs-in-{loc_s}"
        soup=BeautifulSoup(requests.get(url,headers=HEADERS,timeout=10).content,"html.parser")
        for i,a in enumerate(soup.select("article.jobTuple")[:10]):
            t=a.select_one("a.title"); c=a.select_one("a.subTitle")
            link=t.get("href") if t else url
            if link and not link.startswith("http"): link="https://www.naukri.com"+link
            uid=make_uid("Naukri",f"{t}{c}{i}")
            jobs.append({
                "uid":uid,"source":"Naukri.com",
                "job_title":t.get_text(strip=True) if t else role,
                "company":c.get_text(strip=True) if c else "N/A",
                "location":loc,"experience":"Check JD","salary":"Not disclosed",
                "skills":"Check description","description":t.get_text(strip=True) if t else "",
                "url":link,"posted_time":"Recently",
                "fetched_at":datetime.now().isoformat(),"is_new":1
            })
    except Exception: pass
    return jobs

def scrape_indeed(role: str, loc: str):
    jobs=[]
    try:
        q=quote_plus(role); l=quote_plus(loc)
        url=f"https://in.indeed.com/jobs?q={q}&l={l}"
        soup=BeautifulSoup(requests.get(url,headers=HEADERS,timeout=10).content,"html.parser")
        for i,c in enumerate(soup.select("div.job_seen_beacon")[:10]):
            t=c.find("h2"); comp=c.find("span",class_="companyName")
            link_elem=c.find("a",class_="jcs-JobTitle")
            link=f"https://in.indeed.com{link_elem['href']}" if link_elem else url
            uid=make_uid("Indeed",f"{t}{comp}{i}")
            jobs.append({
                "uid":uid,"source":"Indeed","job_title":t.get_text(strip=True) if t else role,
                "company":comp.get_text(strip=True) if comp else "N/A",
                "location":loc,"experience":"Not specified","salary":"Not disclosed",
                "skills":"Check JD","description":t.get_text(strip=True) if t else "",
                "url":link,"posted_time":"Recently","fetched_at":datetime.now().isoformat(),"is_new":1
            })
    except Exception: pass
    return jobs

def clean_jobs(jobs):
    out=[]
    for j in jobs:
        u=j["url"].lower()
        if any(x in u for x in["redirect","trk=","tracking","portal","apply-now"]):
            continue
        out.append(j)
    return out

def fetch_real_jobs(role, loc):
    all=[]
    with st.spinner(f"🔍 Fetching jobs for {loc}..."):
        all+=scrape_remotive(role)
        all+=scrape_arbeitnow(role)
        all+=scrape_naukri(role,loc)
        all+=scrape_indeed(role,loc)
    return clean_jobs(all)

# ─────────────────────────────────────────────
# DATABASE OPERATIONS
# ─────────────────────────────────────────────
def save_jobs(jobs):
    conn=get_conn();cur=conn.cursor()
    for j in jobs:
        cur.execute("""INSERT OR REPLACE INTO jobs
            (uid,source,job_title,company,location,experience,salary,skills,description,url,posted_time,fetched_at,is_new)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (j["uid"],j["source"],j["job_title"],j["company"],j["location"],
             j["experience"],j["salary"],j["skills"],j["description"],j["url"],
             j["posted_time"],j["fetched_at"],j["is_new"]))
    conn.commit();conn.close()

def load_jobs():
    conn=get_conn();cur=conn.cursor()
    cur.execute("SELECT * FROM jobs ORDER BY fetched_at DESC")
    cols=[d[0] for d in cur.description];rows=[dict(zip(cols,r)) for r in cur.fetchall()]
    conn.close();return rows

def mark_applied(uid):
    conn=get_conn();conn.execute("INSERT OR REPLACE INTO applied_jobs VALUES (?,?)",
                                 (uid,datetime.now().isoformat()))
    conn.commit();conn.close()

def get_applied():
    conn=get_conn();rows=conn.execute("SELECT uid FROM applied_jobs").fetchall()
    conn.close();return {r[0] for r in rows}

def save_prefs(role, loc):
    conn=get_conn();conn.execute(
        "INSERT OR REPLACE INTO preferences (id,role,location,experience) VALUES (1,?,?,?)",
        (role,loc,"Any"));conn.commit();conn.close()

def load_prefs():
    conn=get_conn();r=conn.execute("SELECT role,location FROM preferences WHERE id=1").fetchone()
    conn.close();return {"role":r[0],"location":r[1]} if r else {"role":DEFAULT_ROLE,"location":DEFAULT_LOCATION}

def save_cv(name,mime,text):
    conn=get_conn();conn.execute(
        "INSERT OR REPLACE INTO cv_store (id,file_name,mime,uploaded_at,text) VALUES (1,?,?,?,?)",
        (name,mime,datetime.now().isoformat(),text));conn.commit();conn.close()

def load_cv():
    conn=get_conn();r=conn.execute("SELECT file_name,mime,text FROM cv_store WHERE id=1").fetchone()
    conn.close();return r if r else ("","","")

# ─────────────────────────────────────────────
# CV PROCESSING
# ─────────────────────────────────────────────
def extract_cv(file):
    content=file.read();mime=file.type.lower()
    text=""
    if "pdf" in mime and PyPDF2:
        reader=PyPDF2.PdfReader(io.BytesIO(content))
        text="\n".join([p.extract_text() or "" for p in reader.pages])
    elif "wordprocessingml" in mime and docx:
        d=docx.Document(io.BytesIO(content))
        text="\n".join([p.text for p in d.paragraphs])
    else:
        try:text=content.decode("utf-8",errors="ignore")
        except:pass
    text=re.sub(r"[^a-zA-Z0-9\s\.\-]"," ",text).lower()
    text=re.sub(r"\s+"," ",text)
    return file.name,mime,text

def cosine_score(a,b):
    try:
        vec=TfidfVectorizer(stop_words="english");X=vec.fit_transform([a,b])
        return round(float(cosine_similarity(X[0:1],X[1:2])[0][0])*100,1)
    except: return 0.0

def skill_match(cv_text):
    present=[s for s in SKILLS if s in cv_text]
    missing=[s for s in SKILLS if s not in cv_text]
    return present,missing

# ─────────────────────────────────────────────
# AUTO REFRESH
# ─────────────────────────────────────────────
def auto_refresh():
    while True:
        prefs=load_prefs()
        role,loc=prefs["role"],prefs["location"]
        try:
            jobs=fetch_real_jobs(role,loc)
            if jobs: save_jobs(jobs)
        except: pass
        time.sleep(3600)

# ─────────────────────────────────────────────
# STREAMLIT APP
# ─────────────────────────────────────────────
def main():
    st.set_page_config(page_title=APP_NAME, page_icon="💼", layout="wide")
    init_db()

    if "refresh" not in st.session_state:
        threading.Thread(target=auto_refresh,daemon=True).start()
        st.session_state.refresh=True

    prefs=load_prefs()
    role_in=st.session_state.get("active_role",prefs["role"])
    loc_in=st.session_state.get("active_loc",prefs["location"])

    st.title("🤖 AI Job Hunting Agent — Pro")
    st.caption(f"📍 Currently fetching jobs for: **{loc_in}**")

    with st.sidebar:
        st.header("Search Settings")
        role=st.text_input("Role",role_in)
        loc=st.text_input("Location",loc_in)
        if st.button("Search Jobs",use_container_width=True,type="primary"):
            save_prefs(role,loc)
            st.session_state.active_role=role
            st.session_state.active_loc=loc
            st.rerun()

        st.markdown("---")
        st.header("Upload CV")
        file=st.file_uploader("Upload your CV",type=["pdf","docx","txt"])
        if file:
            name,mime,text=extract_cv(file)
            if text:
                save_cv(name,mime,text)
                st.success(f"CV saved: {name}")
            else:
                st.error("Couldn't extract text from file.")

    jobs=load_jobs();applied=get_applied();cv=load_cv()
    cv_name,cv_mime,cv_text=cv

    if st.button("🔄 Refresh Live Jobs",use_container_width=True):
        jobs=fetch_real_jobs(role_in,loc_in)
        if jobs:
            save_jobs(jobs)
            st.success(f"Updated {len(jobs)} jobs for {loc_in}")
            st.rerun()

    if not jobs:
        st.info("Click **Search Jobs** to fetch live listings.")
        return

    st.subheader(f"💼 Showing {len(jobs)} Jobs")

    for j in jobs[:15]:
        jd_text=(j["job_title"]+" "+j["description"]+" "+j["skills"]).lower()
        score=cosine_score(cv_text,jd_text) if cv_text else 0
        present,missing=skill_match(cv_text) if cv_text else ([],[])
        st.markdown(f"### {j['job_title']} — {j['company']} ({j['location']})")
        st.write(f"🌐 {j['source']} | 💰 {j['salary']} | 🕒 {j['posted_time']}")
        if cv_text:
            st.write(f"**CV ↔ JD Match:** {score}%  |  Missing: {', '.join(missing[:5]) or 'None'}")
        st.write(j["description"])
        st.link_button("🚀 Apply Now",j["url"])
        if j["uid"] not in applied:
            if st.button("✅ Mark as Applied",key=j["uid"]):
                mark_applied(j["uid"])
                st.rerun()
        st.markdown("---")

if __name__=="__main__":
    main()
