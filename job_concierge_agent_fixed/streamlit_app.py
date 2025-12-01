import streamlit as st
import logging
from agents.job_scraper_agent import fetch_real_jobs
from agents.recommendation_agent import RecommendationAgent
from tools.cv_upload_tool import read_uploaded_file
from agents.skill_extractor import extract_skills
from memory.long_term_memory import MemoryBank
import time

st.set_page_config(
    page_title="AI Job Concierge",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

logger = logging.getLogger("ui")

# ---------------------------
#  UI STYLES
# ---------------------------
st.markdown("""
    <style>
    .big-title { font-size: 40px; font-weight: bold; padding-bottom: 10px; }
    .sub { font-size: 20px; opacity: 0.85; margin-bottom: 20px; }
    .card {
        background: #ffffff08; 
        padding: 20px; 
        border-radius: 15px; 
        backdrop-filter: blur(10px); 
        border: 1px solid #ffffff30;
        margin-bottom: 25px;
    }
    .job-title { font-size: 22px; font-weight: 700; }
    .job-company { font-size: 18px; opacity: 0.85; }
    .chip {
        display: inline-block;
        padding: 6px 12px;
        background: #4a4a4a;
        color: white;
        border-radius: 15px;
        margin: 3px;
        font-size: 13px;
    }
    .score-bar {
        height: 12px;
        border-radius: 6px;
        background: #444;
        margin-top: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Title
# ---------------------------
st.markdown("<div class='big-title'>💼 AI Job Concierge</div>", unsafe_allow_html=True)
st.markdown("<div class='sub'>Upload resume → Extract skills → Fetch real jobs → Rank using AI embeddings</div>", unsafe_allow_html=True)

# Memory
mb = MemoryBank()

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    user_id = st.text_input("User ID (optional)")

    if st.button("Create Sample Profile"):
        sample = {"name": "Demo User", "preferences": {"role": "ML Engineer", "location": "India"}}
        uid = mb.save_profile(user_id, sample)
        st.success(f"Profile Created: {uid}")

# ---------------------------
# Resume Upload
# ---------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 Upload Resume")
    uploaded = st.file_uploader("Upload your resume file", type=["pdf", "txt", "docx"])

with col2:
    resume_text = st.text_area("Or paste resume text manually")

if uploaded:
    resume_text = read_uploaded_file(uploaded)
    st.success("Resume loaded successfully!")

# ---------------------------
# Skill Extraction
# ---------------------------
if resume_text:
    st.markdown("### 🧠 Extracted Skills")
    skills = extract_skills(resume_text)
    if len(skills) > 0:
        chip_html = "".join([f"<span class='chip'>{s}</span>" for s in skills])
        st.markdown(chip_html, unsafe_allow_html=True)
    else:
        st.info("No major skills detected — try adding more content.")

# ---------------------------
# Job Search
# ---------------------------
st.markdown("### 🔍 Job Search")
query = st.text_input("Search Jobs", value="Machine Learning Engineer")
threshold = st.slider("Recommendation Threshold", 0.0, 1.0, 0.20)

if st.button("Fetch Jobs"):
    if not resume_text:
        st.error("Upload or paste resume first.")
    else:
        with st.spinner("Fetching real jobs from Indeed, Naukri, LinkedIn..."):
            jobs = fetch_real_jobs(query, top_k=10)
            time.sleep(1)

        st.success(f"Fetched {len(jobs)} jobs!")

        rec_agent = RecommendationAgent()
        results = rec_agent.recommend_once(resume_text, query, threshold)

        st.markdown("## 🎯 Top Recommended Jobs")

        for job in results:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='job-title'>{job['title']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='job-company'>{job['company']}</div>", unsafe_allow_html=True)
            st.write(job["description"][:300] + "...")
            st.markdown(f"[Apply →]({job['url']})")

            score_pct = int(job["score"] * 100)
            st.markdown(f"Score: **{score_pct}%**")

            st.markdown(
                f"<div class='score-bar' style='width:{score_pct}%; background:#00c853;'></div>",
                unsafe_allow_html=True
            )
            st.markdown("</div>", unsafe_allow_html=True)
