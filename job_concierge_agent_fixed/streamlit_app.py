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
#  GRADIENT UI STYLES
# ---------------------------
st.markdown("""
    <style>
    /* Global Gradient Background */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #4facfe 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Title Styling */
    .big-title { 
        font-size: 48px; 
        font-weight: 800; 
        padding-bottom: 10px;
        background: linear-gradient(90deg, #fff 0%, #e0e7ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 4px 20px rgba(255,255,255,0.3);
        letter-spacing: -1px;
    }
    
    .sub { 
        font-size: 20px; 
        color: rgba(255,255,255,0.9);
        margin-bottom: 30px;
        font-weight: 300;
    }
    
    /* Glass Card Effect */
    .card {
        background: rgba(255, 255, 255, 0.12); 
        padding: 25px; 
        border-radius: 20px; 
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.25);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        margin-bottom: 25px;
        transition: all 0.3s ease;
    }
    
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.4);
    }
    
    /* Job Styling */
    .job-title { 
        font-size: 24px; 
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 8px;
    }
    
    .job-company { 
        font-size: 18px;
        color: rgba(255, 255, 255, 0.85);
        margin-bottom: 12px;
    }
    
    /* Skill Chips with Gradient */
    .chip {
        display: inline-block;
        padding: 8px 16px;
        background: linear-gradient(135deg, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0.1) 100%);
        color: white;
        border-radius: 20px;
        margin: 5px;
        font-size: 14px;
        font-weight: 500;
        border: 1px solid rgba(255,255,255,0.3);
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    .chip:hover {
        background: linear-gradient(135deg, rgba(255,255,255,0.3) 0%, rgba(255,255,255,0.2) 100%);
        transform: scale(1.05);
    }
    
    /* Gradient Score Bar */
    .score-bar {
        height: 14px;
        border-radius: 10px;
        background: rgba(255,255,255,0.2);
        margin-top: 10px;
        overflow: hidden;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .score-fill {
        height: 100%;
        background: linear-gradient(90deg, #00f260 0%, #0575e6 100%);
        border-radius: 10px;
        transition: width 0.6s ease;
        box-shadow: 0 0 10px rgba(0,242,96,0.5);
    }
    
    /* Streamlit Component Overrides */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 12px;
        color: white;
        backdrop-filter: blur(10px);
    }
    
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: rgba(255, 255, 255, 0.6);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 30px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(102, 126, 234, 0.3) 0%, rgba(118, 75, 162, 0.3) 100%);
        backdrop-filter: blur(20px);
    }
    
    section[data-testid="stSidebar"] h2 {
        color: white;
    }
    
    /* Section Headers */
    h3 {
        color: white;
        font-weight: 700;
        margin-top: 30px;
        margin-bottom: 15px;
        text-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    
    /* Link Styling */
    a {
        color: #a5f3fc;
        text-decoration: none;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    a:hover {
        color: #67e8f9;
        text-shadow: 0 0 10px rgba(103, 232, 249, 0.5);
    }
    
    /* Success/Info Messages */
    .stSuccess, .stInfo {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        border-radius: 12px;
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
    resume_text = st.text_area("Or paste resume text manually", height=150)

if uploaded:
    resume_text = read_uploaded_file(uploaded)
    st.success("✅ Resume loaded successfully!")

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

if st.button("🚀 Fetch Jobs"):
    if not resume_text:
        st.error("⚠️ Upload or paste resume first.")
    else:
        with st.spinner("Fetching real jobs from Indeed, Naukri, LinkedIn..."):
            jobs = fetch_real_jobs(query, top_k=10)
            time.sleep(1)

        st.success(f"✨ Fetched {len(jobs)} jobs!")

        rec_agent = RecommendationAgent()
        results = rec_agent.recommend_once(resume_text, query, threshold)

        st.markdown("## 🎯 Top Recommended Jobs")

        for job in results:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='job-title'>{job['title']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='job-company'>🏢 {job['company']}</div>", unsafe_allow_html=True)
            st.write(job["description"][:300] + "...")
            st.markdown(f"[Apply Now →]({job['url']})")

            score_pct = int(job["score"] * 100)
            st.markdown(f"**Match Score: {score_pct}%**")

            st.markdown(
                f"<div class='score-bar'><div class='score-fill' style='width:{score_pct}%;'></div></div>",
                unsafe_allow_html=True
            )
            st.markdown("</div>", unsafe_allow_html=True)
