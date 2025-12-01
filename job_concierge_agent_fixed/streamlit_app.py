import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import logging

from tools.cv_upload_tool import read_uploaded_file
from agents.resume_parser_agent import parse_resume_text
from agents.recommendation_agent import RecommendationAgent
from memory.long_term_memory import MemoryBank
from tools.google_search_tool import search_jobs   # optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("job_agent")

# -----------------------------
# Streamlit Page Config
# -----------------------------
st.set_page_config(
    page_title="AI Job Concierge",
    layout="wide",
    page_icon="💼"
)

st.title("💼 AI Job Concierge — Professional Job Matching Tool")
st.markdown("""
Upload your resume → Parse → Fetch jobs → Get recommendations  
**Fully automated ML-powered job concierge.**
""")

# Memory instance
memory = MemoryBank()

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("👤 User Profile")

    user_id = st.text_input("User ID (optional)")
    if st.button("Load Profile"):
        profile = memory.get_profile(user_id)
        if profile:
            st.success("Profile Loaded")
            st.json(profile)
        else:
            st.error("Profile not found!")

    if st.button("Create Sample Profile"):
        sample = {"name": "Demo User", "preferences": {"role": "ML Engineer", "location": "India"}}
        saved_id = memory.save_profile(user_id, sample)
        st.success(f"Profile created: {saved_id}")

# -----------------------------
# Resume Section
# -----------------------------
st.header("📄 Step 1 — Upload Resume")
col1, col2 = st.columns(2)

with col1:
    uploaded = st.file_uploader("Upload resume file", type=["txt", "pdf", "docx"])

with col2:
    resume_text = st.text_area("Or paste resume text manually")

if uploaded:
    resume_text = read_uploaded_file(uploaded)
    st.success("Resume loaded successfully")

# -----------------------------
# Parse Resume
# -----------------------------
st.header("🔍 Step 2 — Parse Resume")

parsed_resume = None
if st.button("Parse Resume"):
    if not resume_text:
        st.error("Please upload or paste your resume first.")
    else:
        parsed_resume = parse_resume_text(resume_text)
        st.subheader("Extracted Resume Details")
        st.json(parsed_resume)

# -----------------------------
# Job Search + Recommendation
# -----------------------------
st.header("🎯 Step 3 — Job Search & Recommendations")

query = st.text_input("Job Search Query", value="Machine Learning Engineer")
threshold = st.slider("Match Threshold", 0.0, 1.0, 0.20)

if st.button("Search & Recommend"):
    if not resume_text:
        st.error("Resume required!")
    else:
        st.info("Fetching jobs…")

        # 🤖 Initialize agent
        recommender = RecommendationAgent()

        # You can replace search_jobs() with live scraper later
        jobs = search_jobs(query)

        if not jobs:
            st.error("No jobs found!")
        else:
            st.success(f"Fetched {len(jobs)} jobs")

            st.info("Matching your resume with job descriptions…")
            results = recommender.recommend_once(resume_text, query, threshold)

            st.subheader(f"Top {len(results)} Matched Jobs")
            for job in results[:30]:
                st.markdown(f"### **{job['title']}** — *{job['company']}*")
                st.markdown(f"[Apply Here]({job['url']})")
                st.caption(f"Score: **{job['score']:.3f}**")
                st.write(job["description"][:250] + "…")
                st.markdown("---")

