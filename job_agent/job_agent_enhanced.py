"""
AI Job Hunting Agent — Multi-API Job Board Aggregator
--------------------------------------------------------
✅ 10+ Job Board APIs integrated
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
from concurrent.futures import ThreadPoolExecutor, as_completed
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
APP_NAME = "AI Job Hunting Agent — Multi-API Pro"
DATABASE_NAME = "job_agent_realtime.db"
DEFAULT_ROLE = "Machine Learning Engineer"
DEFAULT_LOCATION = "India"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

# API KEYS - Add your own keys here (free tier available for most)
API_KEYS = {
    "jsearch_rapidapi": os.getenv("JSEARCH_API_KEY", ""),  # RapidAPI JSearch
    "adzuna_app_id": os.getenv("ADZUNA_APP_ID", ""),
    "adzuna_app_key": os.getenv("ADZUNA_APP_KEY", ""),
    "reed_api_key": os.getenv("REED_API_KEY", ""),
}

SKILLS = [
    "python","sql","machine learning","deep learning","nlp","transformers","pandas","numpy",
    "scikit-learn","tensorflow","pytorch","keras","xgboost","lightgbm","feature engineering",
    "data analysis","mlops","docker","kubernetes","flask","fastapi","streamlit",
    "aws","azure","gcp","sagemaker","git","linux","tableau","power bi"
]

# ─────────────────────────────────────────────
# ROLE MATCHING KEYWORDS
# ─────────────────────────────────────────────
ROLE_KEYWORDS = {
    "machine learning": ["ml", "machine learning", "data scientist", "ai engineer"],
    "data scientist": ["data scientist", "ml", "analytics", "machine learning"],
    "software engineer": ["software engineer", "developer", "swe", "backend", "frontend"],
    "data engineer": ["data engineer", "etl", "pipeline", "data infrastructure"],
    "data analyst": ["data analyst", "business analyst", "analytics"],
    "devops": ["devops", "sre", "site reliability", "infrastructure"],
    "full stack": ["full stack", "fullstack", "web developer"],
}

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
    is_new INTEGER DEFAULT 1,
    role_relevance REAL DEFAULT 0
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
        try:
            c.execute("ALTER TABLE jobs ADD COLUMN role_relevance REAL DEFAULT 0")
        except:
            pass
        c.commit()

def get_conn():
    return sqlite3.connect(DATABASE_NAME, check_same_thread=False)

def make_uid(source, job_id): return hashlib.md5(f"{source}|{job_id}".encode()).hexdigest()

# ─────────────────────────────────────────────
# ROLE & LOCATION MATCHING LOGIC
# ─────────────────────────────────────────────
def calculate_role_relevance(job_title: str, target_role: str) -> float:
    """Calculate how relevant a job title is to the target role (0-100)"""
    job_lower = job_title.lower()
    role_lower = target_role.lower()
    
    if role_lower in job_lower:
        return 100.0
    
    for key_role, keywords in ROLE_KEYWORDS.items():
        if any(kw in role_lower for kw in keywords):
            for keyword in keywords:
                if keyword in job_lower:
                    return 85.0
    
    role_words = set(role_lower.split())
    job_words = set(job_lower.split())
    common = role_words & job_words
    
    if common:
        return min(70.0, len(common) * 25)
    
    return 0.0

def check_location_match(job_location: str, target_location: str) -> bool:
    """Check if job location matches target location"""
    job_loc = job_location.lower().strip()
    target_loc = target_location.lower().strip()
    
    if "remote" in job_loc or "anywhere" in job_loc or "worldwide" in job_loc:
        return True
    
    if target_loc in job_loc or job_loc in target_loc:
        return True
    
    location_groups = {
        "india": ["india", "bangalore", "mumbai", "delhi", "hyderabad", "pune", "chennai", "kolkata", "bengaluru", "noida", "gurgaon"],
        "usa": ["usa", "united states", "us", "california", "new york", "texas", "washington", "boston", "san francisco", "seattle"],
        "uk": ["uk", "united kingdom", "london", "manchester", "edinburgh", "birmingham"],
        "germany": ["germany", "berlin", "munich", "frankfurt", "hamburg"],
        "canada": ["canada", "toronto", "vancouver", "montreal", "ottawa"]
    }
    
    for country, cities in location_groups.items():
        if any(city in target_loc for city in cities):
            if any(city in job_loc for city in cities):
                return True
    
    return False

def filter_jobs_by_role_and_location(jobs: List[Dict], target_role: str, target_location: str, min_relevance: float = 20.0) -> List[Dict]:
    """Filter jobs based on role relevance and location"""
    filtered = []
    for job in jobs:
        relevance = calculate_role_relevance(job["job_title"], target_role)
        job["role_relevance"] = relevance
        location_match = check_location_match(job["location"], target_location)
        
        if relevance >= min_relevance and location_match:
            filtered.append(job)
    
    return sorted(filtered, key=lambda x: x["role_relevance"], reverse=True)

# ─────────────────────────────────────────────
# JOB BOARD API SCRAPERS
# ─────────────────────────────────────────────

def scrape_jsearch_rapidapi(role: str, loc: str):
    """JSearch API via RapidAPI - Google for Jobs aggregator"""
    jobs = []
    if not API_KEYS.get("jsearch_rapidapi"):
        return jobs
    
    try:
        url = "https://jsearch.p.rapidapi.com/search"
        headers = {
            "X-RapidAPI-Key": API_KEYS["jsearch_rapidapi"],
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        params = {
            "query": f"{role} in {loc}",
            "page": "1",
            "num_pages": "1"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        data = response.json()
        
        for j in data.get("data", [])[:20]:
            uid = make_uid("JSearch", j.get("job_id", ""))
            jobs.append({
                "uid": uid, "source": "JSearch (Google Jobs)",
                "job_title": j.get("job_title", "N/A"),
                "company": j.get("employer_name", "N/A"),
                "location": j.get("job_city", "") + ", " + j.get("job_country", loc),
                "experience": j.get("job_required_experience", {}).get("required_experience_in_months", "Not specified"),
                "salary": j.get("job_salary_currency", "") + " " + str(j.get("job_min_salary", "")) + "-" + str(j.get("job_max_salary", "")) if j.get("job_min_salary") else "Not disclosed",
                "skills": j.get("job_required_skills", [""])[0] if j.get("job_required_skills") else "Check JD",
                "description": j.get("job_description", "")[:600],
                "url": j.get("job_apply_link", j.get("job_google_link", "")),
                "posted_time": j.get("job_posted_at_datetime_utc", "")[:10],
                "fetched_at": datetime.now().isoformat(), "is_new": 1, "role_relevance": 0
            })
    except Exception as e:
        pass
    return jobs

def scrape_adzuna(role: str, loc: str):
    """Adzuna API - UK, US, and international jobs"""
    jobs = []
    if not API_KEYS.get("adzuna_app_id") or not API_KEYS.get("adzuna_app_key"):
        return jobs
    
    try:
        # Map location to Adzuna country code
        country_map = {"india": "in", "usa": "us", "uk": "gb", "germany": "de", "canada": "ca"}
        country = country_map.get(loc.lower(), "us")
        
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": API_KEYS["adzuna_app_id"],
            "app_key": API_KEYS["adzuna_app_key"],
            "results_per_page": 20,
            "what": role,
            "content-type": "application/json"
        }
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        for j in data.get("results", []):
            uid = make_uid("Adzuna", str(j.get("id", "")))
            jobs.append({
                "uid": uid, "source": "Adzuna",
                "job_title": j.get("title", "N/A"),
                "company": j.get("company", {}).get("display_name", "N/A"),
                "location": j.get("location", {}).get("display_name", loc),
                "experience": "Not specified",
                "salary": f"${j.get('salary_min', 0)}-${j.get('salary_max', 0)}" if j.get("salary_min") else "Not disclosed",
                "skills": j.get("category", {}).get("label", "Check JD"),
                "description": j.get("description", "")[:600],
                "url": j.get("redirect_url", ""),
                "posted_time": j.get("created", "")[:10],
                "fetched_at": datetime.now().isoformat(), "is_new": 1, "role_relevance": 0
            })
    except Exception as e:
        pass
    return jobs

def scrape_reed_uk(role: str, loc: str):
    """Reed.co.uk API - UK jobs"""
    jobs = []
    if not API_KEYS.get("reed_api_key") or "uk" not in loc.lower():
        return jobs
    
    try:
        url = "https://www.reed.co.uk/api/1.0/search"
        auth = (API_KEYS["reed_api_key"], "")
        params = {"keywords": role, "location": loc, "resultsToTake": 20}
        
        response = requests.get(url, auth=auth, params=params, timeout=15)
        data = response.json()
        
        for j in data.get("results", []):
            uid = make_uid("Reed", str(j.get("jobId", "")))
            jobs.append({
                "uid": uid, "source": "Reed.co.uk",
                "job_title": j.get("jobTitle", "N/A"),
                "company": j.get("employerName", "N/A"),
                "location": j.get("locationName", loc),
                "experience": "Not specified",
                "salary": f"£{j.get('minimumSalary', 0)}-£{j.get('maximumSalary', 0)}" if j.get("minimumSalary") else "Not disclosed",
                "skills": "Check JD",
                "description": j.get("jobDescription", "")[:600],
                "url": j.get("jobUrl", ""),
                "posted_time": j.get("date", "")[:10],
                "fetched_at": datetime.now().isoformat(), "is_new": 1, "role_relevance": 0
            })
    except Exception as e:
        pass
    return jobs

def scrape_remotive(role: str):
    """Remotive API - Remote jobs"""
    jobs = []
    try:
        data = requests.get("https://remotive.com/api/remote-jobs",
                            params={"search": role, "limit": 20}, timeout=10).json()
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
                "fetched_at": datetime.now().isoformat(), "is_new": 1, "role_relevance": 0
            })
    except Exception: pass
    return jobs

def scrape_arbeitnow(role: str):
    """Arbeitnow API - European jobs"""
    jobs = []
    try:
        data = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=10).json()
        for j in data.get("data", [])[:20]:
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
                "fetched_at": datetime.now().isoformat(), "is_new": 1, "role_relevance": 0
            })
    except Exception: pass
    return jobs

def scrape_graphql_jobs(role: str):
    """GraphQL Jobs API - GraphQL specific jobs"""
    jobs = []
    try:
        url = "https://api.graphql.jobs/"
        query = """
        query {
          jobs(input: { type: FULL_TIME }) {
            id
            title
            slug
            commitment { title }
            cities { name country { name } }
            company { name }
            description
            applyUrl
            postedAt
          }
        }
        """
        
        response = requests.post(url, json={"query": query}, timeout=10)
        data = response.json()
        
        for j in data.get("data", {}).get("jobs", [])[:15]:
            if role.lower() in j.get("title", "").lower():
                uid = make_uid("GraphQLJobs", j.get("id", ""))
                city = j.get("cities", [{}])[0] if j.get("cities") else {}
                location = f"{city.get('name', 'Remote')}, {city.get('country', {}).get('name', '')}"
                
                jobs.append({
                    "uid": uid, "source": "GraphQL Jobs",
                    "job_title": j.get("title", "N/A"),
                    "company": j.get("company", {}).get("name", "N/A"),
                    "location": location,
                    "experience": "Not specified",
                    "salary": "Not disclosed",
                    "skills": "GraphQL",
                    "description": j.get("description", "")[:600],
                    "url": j.get("applyUrl", ""),
                    "posted_time": j.get("postedAt", "")[:10],
                    "fetched_at": datetime.now().isoformat(), "is_new": 1, "role_relevance": 0
                })
    except Exception: pass
    return jobs

def scrape_usajobs_gov(role: str):
    """USAJobs.gov API - US Government jobs"""
    jobs = []
    try:
        url = "https://data.usajobs.gov/api/search"
        headers = {
            "Host": "data.usajobs.gov",
            "User-Agent": HEADERS["User-Agent"],
            "Authorization-Key": os.getenv("USAJOBS_API_KEY", "")
        }
        params = {"Keyword": role, "ResultsPerPage": 20}
        
        if not headers["Authorization-Key"]:
            return jobs
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        data = response.json()
        
        for j in data.get("SearchResult", {}).get("SearchResultItems", []):
            job_data = j.get("MatchedObjectDescriptor", {})
            uid = make_uid("USAJobs", job_data.get("PositionID", ""))
            
            jobs.append({
                "uid": uid, "source": "USAJobs.gov",
                "job_title": job_data.get("PositionTitle", "N/A"),
                "company": job_data.get("OrganizationName", "US Government"),
                "location": ", ".join([loc.get("LocationName", "") for loc in job_data.get("PositionLocation", [])[:2]]),
                "experience": "Not specified",
                "salary": f"${job_data.get('PositionRemuneration', [{}])[0].get('MinimumRange', 'Not disclosed')} - ${job_data.get('PositionRemuneration', [{}])[0].get('MaximumRange', '')}",
                "skills": "Check JD",
                "description": job_data.get("UserArea", {}).get("Details", {}).get("JobSummary", "")[:600],
                "url": job_data.get("PositionURI", ""),
                "posted_time": job_data.get("PublicationStartDate", "")[:10],
                "fetched_at": datetime.now().isoformat(), "is_new": 1, "role_relevance": 0
            })
    except Exception: pass
    return jobs

def scrape_naukri(role: str, loc: str):
    """Naukri.com scraper - India jobs"""
    jobs=[]
    try:
        role_s=role.lower().replace(" ","-"); loc_s=loc.lower().replace(" ","-")
        url=f"https://www.naukri.com/{role_s}-jobs-in-{loc_s}"
        soup=BeautifulSoup(requests.get(url,headers=HEADERS,timeout=10).content,"html.parser")
        for i,a in enumerate(soup.select("article.jobTuple")[:15]):
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
                "fetched_at":datetime.now().isoformat(),"is_new":1,"role_relevance":0
            })
    except Exception: pass
    return jobs

def scrape_indeed(role: str, loc: str):
    """Indeed scraper"""
    jobs=[]
    try:
        q=quote_plus(role); l=quote_plus(loc)
        url=f"https://in.indeed.com/jobs?q={q}&l={l}"
        soup=BeautifulSoup(requests.get(url,headers=HEADERS,timeout=10).content,"html.parser")
        for i,c in enumerate(soup.select("div.job_seen_beacon")[:15]):
            t=c.find("h2"); comp=c.find("span",class_="companyName")
            link_elem=c.find("a",class_="jcs-JobTitle")
            link=f"https://in.indeed.com{link_elem['href']}" if link_elem else url
            uid=make_uid("Indeed",f"{t}{comp}{i}")
            jobs.append({
                "uid":uid,"source":"Indeed","job_title":t.get_text(strip=True) if t else role,
                "company":comp.get_text(strip=True) if comp else "N/A",
                "location":loc,"experience":"Not specified","salary":"Not disclosed",
                "skills":"Check JD","description":t.get_text(strip=True) if t else "",
                "url":link,"posted_time":"Recently","fetched_at":datetime.now().isoformat(),"is_new":1,"role_relevance":0
            })
    except Exception: pass
    return jobs

def clean_jobs(jobs):
    """Remove redirect/tracking URLs"""
    out=[]
    for j in jobs:
        u=j["url"].lower()
        if any(x in u for x in["redirect","trk=","tracking","portal"]):
            continue
        out.append(j)
    return out

def fetch_real_jobs(role, loc):
    """Fetch jobs from ALL sources in parallel"""
    all_jobs = []
    
    with st.spinner(f"🔍 Fetching jobs from 10+ sources for **{role}** in **{loc}**..."):
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(scrape_jsearch_rapidapi, role, loc): "JSearch (Google Jobs)",
                executor.submit(scrape_adzuna, role, loc): "Adzuna",
                executor.submit(scrape_reed_uk, role, loc): "Reed.co.uk",
                executor.submit(scrape_remotive, role): "Remotive",
                executor.submit(scrape_arbeitnow, role): "Arbeitnow",
                executor.submit(scrape_graphql_jobs, role): "GraphQL Jobs",
                executor.submit(scrape_usajobs_gov, role): "USAJobs.gov",
                executor.submit(scrape_naukri, role, loc): "Naukri.com",
                executor.submit(scrape_indeed, role, loc): "Indeed",
            }
            
            for future in as_completed(futures):
                source = futures[future]
                try:
                    jobs = future.result()
                    all_jobs.extend(jobs)
                    if jobs:
                        st.info(f"✓ {source}: {len(jobs)} jobs")
                except Exception as e:
                    st.warning(f"⚠️ {source} failed")
    
    cleaned = clean_jobs(all_jobs)
    filtered = filter_jobs_by_role_and_location(cleaned, role, loc, min_relevance=20.0)
    
    location_filtered = sum(1 for j in cleaned if check_location_match(j["location"], loc))
    st.success(f"✅ Found **{len(filtered)}** relevant jobs for **{role}** in **{loc}**")
    st.caption(f"📊 Total: {len(all_jobs)} → Cleaned: {len(cleaned)} → Location: {location_filtered} → Final: {len(filtered)}")
    
    return filtered

# ─────────────────────────────────────────────
# DATABASE OPERATIONS
# ─────────────────────────────────────────────
def save_jobs(jobs):
    conn=get_conn();cur=conn.cursor()
    for j in jobs:
        cur.execute("""INSERT OR REPLACE INTO jobs
            (uid,source,job_title,company,location,experience,salary,skills,description,url,posted_time,fetched_at,is_new,role_relevance)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (j["uid"],j["source"],j["job_title"],j["company"],j["location"],
             j["experience"],j["salary"],j["skills"],j["description"],j["url"],
             j["posted_time"],j["fetched_at"],j["is_new"],j.get("role_relevance",0)))
    conn.commit();conn.close()

def load_jobs(target_role: str = None, target_location: str = None):
    conn=get_conn();cur=conn.cursor()
    cur.execute("SELECT * FROM jobs ORDER BY role_relevance DESC, fetched_at DESC")
    cols=[d[0] for d in cur.description];rows=[dict(zip(cols,r)) for r in cur.fetchall()]
    conn.close()
    
    if target_role and target_location:
        filtered = []
        for job in rows:
            if check_location_match(job["location"], target_location):
                job["role_relevance"] = calculate_role_relevance(job["job_title"], target_role)
                if job["role_relevance"] >= 20.0:
                    filtered.append(job)
        return sorted(filtered, key=lambda x: x["role_relevance"], reverse=True)
    
    return rows

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
        time.sleep(3600)
        prefs=load_prefs()
        role,loc=prefs["role"],prefs["location"]
        try:
            jobs=fetch_real_jobs(role,loc)
            if jobs: 
                save_jobs(jobs)
                print(f"[AUTO-REFRESH] Updated {len(jobs)} jobs for {role} in {loc}")
        except Exception as e:
            print(f"[AUTO-REFRESH] Error: {e}")

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

    st.title("🤖 AI Job Hunting Agent — Multi-API Pro")
    st.caption(f"📍 Searching across 10+ job boards for: **{role_in}** in **{loc_in}**")

    with st.sidebar:
        st.header("⚙️ Search Settings")
        role=st.text_input("Role",role_in)
        loc=st.text_input("Location",loc_in)
        if st.button("🔍 Search Jobs",use_container_width=True,type="primary"):
            save_prefs(role,loc)
            st.session_state.active_role=role
            st.session_state.active_loc=loc
            st.rerun()

        st.markdown("---")
        st.header("📄 Upload CV")
        file=st.file_uploader("Upload your CV",type=["pdf","docx","txt"])
        if file:
            name,mime,text=extract_cv(file)
            if text:
                save_cv(name,mime,text)
                st.success(f"✅ CV saved: {name}")
            else:
                st.error("❌ Couldn't extract text from file.")
        
        st.markdown("---")
        st.header("🔑 API Configuration")
        st.caption("Add API keys as environment variables:")
        with st.expander("View API Setup Instructions"):
            st.code("""
# Set these environment variables:
export JSEARCH_API_KEY="your_rapidapi_key"
export ADZUNA_APP_ID="your_adzuna_id"
export ADZUNA_APP_KEY="your_adzuna_key"
export REED_API_KEY="your_reed_key"
export USAJOBS_API_KEY="your_usajobs_key"
            """)
            st.markdown("""
**Free API Keys Available:**
- **JSearch (RapidAPI)**: [Get Free Key](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) - 100 requests/month
- **Adzuna**: [Get Free Key](https://developer.adzuna.com/) - 250 requests/month
- **Reed.co.uk**: [Get Free Key](https://www.reed.co.uk/developers) - UK jobs
- **USAJobs.gov**: [Get Free Key](https://developer.usajobs.gov/) - US Gov jobs
            """)
        
        # Show active APIs
        active_apis = []
        if API_KEYS.get("jsearch_rapidapi"): active_apis.append("✅ JSearch")
        else: active_apis.append("⚠️ JSearch (No API Key)")
        
        if API_KEYS.get("adzuna_app_id") and API_KEYS.get("adzuna_app_key"): 
            active_apis.append("✅ Adzuna")
        else: 
            active_apis.append("⚠️ Adzuna (No API Key)")
        
        if API_KEYS.get("reed_api_key"): active_apis.append("✅ Reed")
        else: active_apis.append("⚠️ Reed (No API Key)")
        
        if API_KEYS.get("usajobs_api_key"): active_apis.append("✅ USAJobs")
        else: active_apis.append("⚠️ USAJobs (No API Key)")
        
        active_apis.extend(["✅ Remotive", "✅ Arbeitnow", "✅ GraphQL Jobs", "✅ Naukri", "✅ Indeed"])
        
        st.caption("**Active Sources:**")
        for api in active_apis:
            st.caption(api)

    jobs=load_jobs(role_in, loc_in);applied=get_applied();cv=load_cv()
    cv_name,cv_mime,cv_text=cv

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🔄 Refresh Live Jobs",use_container_width=True):
            jobs=fetch_real_jobs(role_in,loc_in)
            if jobs:
                save_jobs(jobs)
                st.success(f"✅ Updated {len(jobs)} jobs for **{role_in}** in **{loc_in}**")
                st.rerun()
            else:
                st.warning(f"⚠️ No jobs found for **{role_in}** in **{loc_in}**. Try different search terms.")
    
    with col2:
        if st.button("🗑️ Clear All Jobs", use_container_width=True):
            conn = get_conn()
            conn.execute("DELETE FROM jobs")
            conn.commit()
            conn.close()
            st.success("✅ All jobs cleared")
            st.rerun()

    if not jobs:
        st.info(f"🔍 Click **Search Jobs** to fetch live listings for **{role_in}** in **{loc_in}**")
        st.markdown("---")
        st.subheader("📊 Available Job Boards")
        st.markdown("""
        This agent aggregates jobs from:
        1. **JSearch (Google Jobs)** - Aggregates from 100+ job sites
        2. **Adzuna** - UK, US, and international jobs
        3. **Reed.co.uk** - Leading UK job board
        4. **Remotive** - Remote-first jobs worldwide
        5. **Arbeitnow** - European tech jobs
        6. **GraphQL Jobs** - GraphQL-specific positions
        7. **USAJobs.gov** - US Government positions
        8. **Naukri.com** - India's #1 job portal
        9. **Indeed** - Global job search
        
        **Note:** Some APIs require free API keys. See sidebar for setup instructions.
        """)
        return

    st.subheader(f"💼 Showing {len(jobs)} Jobs for {role_in} in {loc_in}")
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    with col1:
        sources = list(set([j["source"] for j in jobs]))
        selected_source = st.selectbox("Filter by Source", ["All Sources"] + sources)
    with col2:
        min_relevance = st.slider("Minimum Role Match %", 0, 100, 20)
    with col3:
        sort_by = st.selectbox("Sort by", ["Role Match", "Date Posted", "Company"])
    
    # Apply filters
    filtered_jobs = jobs
    if selected_source != "All Sources":
        filtered_jobs = [j for j in filtered_jobs if j["source"] == selected_source]
    filtered_jobs = [j for j in filtered_jobs if j.get("role_relevance", 0) >= min_relevance]
    
    if sort_by == "Date Posted":
        filtered_jobs = sorted(filtered_jobs, key=lambda x: x["posted_time"], reverse=True)
    elif sort_by == "Company":
        filtered_jobs = sorted(filtered_jobs, key=lambda x: x["company"])
    
    st.caption(f"Showing {len(filtered_jobs)} jobs after filters")
    st.markdown("---")

    for idx, j in enumerate(filtered_jobs[:25], 1):
        jd_text=(j["job_title"]+" "+j["description"]+" "+j["skills"]).lower()
        score=cosine_score(cv_text,jd_text) if cv_text else 0
        present,missing=skill_match(cv_text) if cv_text else ([],[])
        
        # Role relevance badge
        relevance = j.get("role_relevance", 0)
        if relevance >= 85:
            badge = "🟢 Perfect Match"
            badge_color = "#28a745"
        elif relevance >= 70:
            badge = "🟡 Good Match"
            badge_color = "#ffc107"
        elif relevance >= 50:
            badge = "🟠 Partial Match"
            badge_color = "#fd7e14"
        else:
            badge = "⚪ Low Match"
            badge_color = "#6c757d"
        
        # Job card
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### {idx}. {j['job_title']}")
                st.markdown(f"**{j['company']}** • {j['location']} • <span style='color:{badge_color}'>{badge}</span>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"**{j['source']}**")
                st.caption(f"🕒 {j['posted_time']}")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"💰 **Salary:** {j['salary']}")
                st.write(f"🎯 **Role Match:** {relevance:.0f}%")
                if cv_text:
                    st.write(f"📄 **CV-JD Match:** {score}%")
                    if missing[:3]:
                        st.write(f"🔍 **Missing Skills:** {', '.join(missing[:3])}")
            with col2:
                st.link_button("🚀 Apply Now", j["url"], use_container_width=True)
                if j["uid"] not in applied:
                    if st.button("✅ Mark Applied", key=f"apply_{j['uid']}", use_container_width=True):
                        mark_applied(j["uid"])
                        st.rerun()
                else:
                    st.success("✓ Applied", icon="✅")
            
            with st.expander("📝 View Full Description"):
                st.write(j["description"])
                st.write(f"**Skills:** {j['skills']}")
                st.write(f"**Experience:** {j['experience']}")
            
            st.markdown("---")

if __name__=="__main__":
    main()
