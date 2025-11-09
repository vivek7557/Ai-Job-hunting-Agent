import streamlit as st
import sqlite3, pandas as pd, time, os, yaml, io, re, subprocess
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
from typing import List, Tuple
from PyPDF2 import PdfReader
from docx import Document

# ───────────────────────── Config ─────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
DB_PATH = os.path.join(BASE_DIR, "jobs.db")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

COMMON_SKILLS = [
    "python","sql","pandas","numpy","scikit-learn","tensorflow","pytorch",
    "transformers","huggingface","nlp","llm","deep learning","mlflow",
    "airflow","docker","kubernetes","spark","gcp","aws","azure","fastapi",
    "streamlit","git","linux","data pipelines","feature engineering"
]

# ───────────────────────── Helpers ─────────────────────────
def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_data(show_spinner=False)
def load_jobs():
    con = db()
    df = pd.read_sql_query("SELECT * FROM jobs ORDER BY date DESC, score DESC", con)
    con.close()
    for col in ["title","company","location","link","description","skills","date","status"]:
        if col in df.columns:
            df[col] = df[col].fillna("")
    return df

def mark_applied(job_id):
    con = db()
    con.execute("UPDATE jobs SET status='applied' WHERE id=?", (job_id,))
    con.commit(); con.close()

def fetch_new_jobs(role=None, location=None):
    cmd = ["python", os.path.join(BASE_DIR, "ai_job.py")]
    if role: cmd.append(role)
    if location: cmd.append(location)
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def extract_text_from_resume(upload) -> str:
    if upload is None: return ""
    name = upload.name.lower(); data = upload.read()
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(data))
            return "\n".join([p.extract_text() or "" for p in reader.pages])
        except Exception: return ""
    if name.endswith(".docx"):
        try:
            doc = Document(io.BytesIO(data))
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception: return ""
    try: return data.decode("utf-8", errors="ignore")
    except Exception: return ""

def clean_text(x: str) -> str:
    return re.sub(r"\s+", " ", (x or "")).strip()

@st.cache_resource(show_spinner=False)
def load_embedder():
    return SentenceTransformer("all-MiniLM-L6-v2")

def compute_similarity_scores(df: pd.DataFrame, resume_text: str) -> pd.DataFrame:
    resume_text = clean_text(resume_text)
    if not resume_text or df.empty:
        df["similarity"] = 0.0
        return df
    model = load_embedder()
    resume_vec = model.encode(resume_text, convert_to_tensor=True)
    texts = (df["title"].astype(str) + " " + df["description"].astype(str)).tolist()
    job_vecs = model.encode(texts, convert_to_tensor=True, batch_size=64)
    sims = util.cos_sim(resume_vec, job_vecs).cpu().numpy()[0]
    df["similarity"] = sims
    return df.sort_values(["similarity","score"], ascending=[False, False])

# ───────────────────────── UI Setup ─────────────────────────
st.set_page_config(page_title="⚡ Fast Job Hunter", layout="wide", page_icon="⚡")

# CSS
st.markdown("""
<style>
.metric-card {
  background: linear-gradient(135deg,#f9fafb,#ffffff);
  padding:1rem 1.5rem;border-radius:12px;
  box-shadow:0 4px 12px rgba(0,0,0,0.08);
  text-align:center;color:#111827;
}
.job-card {
  background: linear-gradient(135deg,#ffffff,#f9fafb);
  border-radius:12px;padding:1.2rem;margin-bottom:1rem;
  box-shadow:0 2px 8px rgba(0,0,0,0.06);
}
.badge {display:inline-block;padding:4px 8px;border-radius:8px;
        font-size:0.75rem;margin-right:6px;}
.badge-high {background:#22c55e;color:white;}
.badge-mid {background:#facc15;color:#111827;}
.badge-low {background:#9ca3af;color:white;}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("## ⚡ Fast Job Hunter")
st.caption("Instant job search across all major AI/ML job portals • Smart resume matching • CV insights")

# Inputs
col1, col2, col3 = st.columns([2,2,2])
with col1: role = st.text_input("🎯 Job Role", "Machine Learning Engineer")
with col2: location = st.text_input("📍 Location", "India")
with col3: upload = st.file_uploader("📄 Upload Resume", type=["pdf","docx","txt"])

if st.button("🔍 Search Jobs"):
    with st.spinner("Fetching and analyzing latest jobs..."):
        fetch_new_jobs(role, location)
        time.sleep(5)
        st.cache_data.clear()
    st.success("✅ Jobs updated successfully!")

# Load all jobs (no filtering)
df = load_jobs()

if df.empty:
    st.warning("No jobs in the database yet. Click **Search Jobs** to fetch.")
    st.stop()

# Similarity (optional)
resume_text = extract_text_from_resume(upload) if upload else ""
df = compute_similarity_scores(df, resume_text)

# Dashboard metrics
con = db()
applied_count = con.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'").fetchone()[0]
new_jobs = con.execute("SELECT COUNT(*) FROM jobs WHERE status='new'").fetchone()[0]
con.close()

cols = st.columns(4)
metrics = [("Jobs Found", len(df)), ("Applied", applied_count),
           ("New Jobs", new_jobs), ("Sources", len(CFG["sources"]))]
for i, (label, value) in enumerate(metrics):
    with cols[i]:
        st.markdown(f"<div class='metric-card'><h2>{value}</h2><p>{label}</p></div>", unsafe_allow_html=True)

# Tabs
tabs = st.tabs(["💼 Jobs", "🧠 CV Suggestions", "✅ Applied", "📊 Analytics"])

# ───────── TAB 1: JOB LISTINGS ─────────
with tabs[0]:
    for _, row in df.iterrows():
        sim = float(row.get("similarity", 0.0))
        badge_class = "badge-low"
        if sim > 0.7: badge_class = "badge-high"
        elif sim > 0.4: badge_class = "badge-mid"

        with st.container():
            st.markdown("<div class='job-card'>", unsafe_allow_html=True)
            st.markdown(f"### {row['title']}  <span class='badge {badge_class}'>Match: {int(sim*100)}%</span>", unsafe_allow_html=True)
            st.caption(f"🏢 {row['company']} | 📍 {row['location'] or 'N/A'} | 🕓 {row['date'] or 'Recently posted'}")
            st.write(row['description'] or "No description available.")

            if row['skills']:
                st.markdown("**Skills:** " + " ".join([f"`{s.strip()}`" for s in row['skills'].split(',')[:8]]))

            c1, c2 = st.columns([1,1])
            with c1:
                if row.get('link'):
                    st.link_button("🌐 Apply Now", row['link'])
                else:
                    st.warning("No link available.")
            with c2:
                if st.button(f"✅ Mark Applied ({row['id'][:6]})"):
                    mark_applied(row['id'])
                    st.toast(f"Marked {row['title']} as applied ✅")
            st.markdown("</div>", unsafe_allow_html=True)

# ───────── TAB 2: CV SUGGESTIONS ─────────
with tabs[1]:
    if not resume_text:
        st.info("Upload your resume to get AI-powered CV suggestions.")
    else:
        st.subheader("📈 General CV Optimization Tips")
        st.markdown("""
        - Emphasize metrics like accuracy, latency, or model performance.
        - List tools explicitly (Python, SQL, Docker, Airflow, etc.).
        - Add recent AI/ML projects or GitHub links.
        - Group skills by domain: NLP, CV, MLOps.
        - Quantify your work (e.g., “Improved model F1-score by 15%”).
        """)

# ───────── TAB 3: APPLIED JOBS ─────────
with tabs[2]:
    con = db()
    applied_df = pd.read_sql_query("SELECT * FROM jobs WHERE status='applied'", con)
    con.close()
    if applied_df.empty:
        st.info("No applied jobs yet. Click **Mark Applied** to track.")
    else:
        st.dataframe(applied_df[["title","company","location","link","date"]])

# ───────── TAB 4: ANALYTICS ─────────
with tabs[3]:
    st.write("📊 Analytics coming soon — trends, portals, and skill frequency visualizations.")
