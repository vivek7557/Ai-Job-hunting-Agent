import streamlit as st
import logging
from agents.job_scraper_agent import fetch_real_jobs
from agents.recommendation_agent import RecommendationAgent
from tools.cv_upload_tool import read_uploaded_file
from agents.skill_extractor import extract_skills
from memory.long_term_memory import MemoryBank
import time

st.set_page_config(
    page_title="AI Job Concierge Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

logger = logging.getLogger("ui")

# ---------------------------
#  ADVANCED GRADIENT REACT UI
# ---------------------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Modern Gradient Background with Mesh */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #4facfe 75%, #00f2fe 100%);
        background-size: 400% 400%;
        animation: gradientFlow 20s ease infinite;
        position: relative;
        overflow-x: hidden;
    }
    
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: 
            radial-gradient(circle at 20% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(255, 255, 255, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 40% 20%, rgba(120, 119, 198, 0.3) 0%, transparent 50%);
        pointer-events: none;
        z-index: 0;
    }
    
    @keyframes gradientFlow {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Container Styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
        position: relative;
        z-index: 1;
    }
    
    /* Hero Section */
    .hero-section {
        text-align: center;
        padding: 3rem 2rem;
        margin-bottom: 3rem;
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(40px);
        border-radius: 30px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 
            0 8px 32px rgba(31, 38, 135, 0.37),
            inset 0 1px 0 rgba(255, 255, 255, 0.4);
    }
    
    .hero-title {
        font-size: 64px;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #e0e7ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
        letter-spacing: -2px;
        text-shadow: 0 4px 30px rgba(255, 255, 255, 0.2);
        line-height: 1.1;
    }
    
    .hero-subtitle {
        font-size: 20px;
        color: rgba(255, 255, 255, 0.9);
        font-weight: 400;
        max-width: 600px;
        margin: 0 auto;
        line-height: 1.6;
    }
    
    .hero-badge {
        display: inline-block;
        padding: 8px 20px;
        background: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 50px;
        color: white;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 1.5rem;
        backdrop-filter: blur(10px);
    }
    
    /* Section Headers with Depth */
    .section-header {
        font-size: 28px;
        font-weight: 700;
        color: white;
        margin: 2.5rem 0 1.5rem 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .section-header::before {
        content: '';
        width: 4px;
        height: 32px;
        background: linear-gradient(180deg, #ffffff 0%, rgba(255, 255, 255, 0.5) 100%);
        border-radius: 4px;
        box-shadow: 0 0 20px rgba(255, 255, 255, 0.5);
    }
    
    /* Glass Card Components */
    .glass-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(30px) saturate(180%);
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.18);
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 
            0 8px 32px rgba(31, 38, 135, 0.37),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .glass-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.5), transparent);
    }
    
    .glass-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 
            0 16px 48px rgba(31, 38, 135, 0.5),
            inset 0 1px 0 rgba(255, 255, 255, 0.4);
        border-color: rgba(255, 255, 255, 0.3);
    }
    
    /* Job Card with Advanced Styling */
    .job-card {
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(30px) saturate(180%);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 2rem;
        margin-bottom: 2rem;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        box-shadow: 
            0 10px 40px rgba(31, 38, 135, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
    }
    
    .job-card::after {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
        opacity: 0;
        transition: opacity 0.4s ease;
    }
    
    .job-card:hover::after {
        opacity: 1;
    }
    
    .job-card:hover {
        transform: translateY(-6px);
        border-color: rgba(255, 255, 255, 0.35);
        box-shadow: 
            0 20px 60px rgba(31, 38, 135, 0.6),
            inset 0 1px 0 rgba(255, 255, 255, 0.4);
    }
    
    .job-title {
        font-size: 26px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.5rem;
        line-height: 1.3;
    }
    
    .job-company {
        font-size: 18px;
        color: rgba(255, 255, 255, 0.85);
        font-weight: 500;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .job-description {
        font-size: 15px;
        line-height: 1.7;
        color: rgba(255, 255, 255, 0.8);
        margin-bottom: 1.5rem;
    }
    
    /* Skill Chips with Animation */
    .skills-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin: 1.5rem 0;
    }
    
    .skill-chip {
        display: inline-flex;
        align-items: center;
        padding: 10px 18px;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.2) 0%, rgba(255, 255, 255, 0.1) 100%);
        color: white;
        border-radius: 50px;
        font-size: 14px;
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(10px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: default;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    
    .skill-chip:hover {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.3) 0%, rgba(255, 255, 255, 0.2) 100%);
        transform: translateY(-2px) scale(1.05);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
        border-color: rgba(255, 255, 255, 0.4);
    }
    
    /* Score Display with Gradient */
    .score-section {
        margin-top: 1.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid rgba(255, 255, 255, 0.15);
    }
    
    .score-label {
        font-size: 13px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.7);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    
    .score-bar-container {
        height: 12px;
        background: rgba(255, 255, 255, 0.15);
        border-radius: 10px;
        overflow: hidden;
        position: relative;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    
    .score-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #00f260 0%, #0575e6 50%, #00f260 100%);
        background-size: 200% 100%;
        border-radius: 10px;
        transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 
            0 0 20px rgba(0, 242, 96, 0.6),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
        animation: shimmer 2s infinite;
        position: relative;
    }
    
    @keyframes shimmer {
        0% { background-position: 0% 0%; }
        100% { background-position: 200% 0%; }
    }
    
    .score-percentage {
        font-size: 24px;
        font-weight: 700;
        color: #00f260;
        text-shadow: 0 0 10px rgba(0, 242, 96, 0.5);
        margin-top: 8px;
    }
    
    /* Input Fields with Depth */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(255, 255, 255, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 16px;
        color: white;
        backdrop-filter: blur(10px);
        font-size: 15px;
        padding: 14px 18px;
        transition: all 0.3s ease;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        background: rgba(255, 255, 255, 0.18);
        border-color: rgba(255, 255, 255, 0.4);
        box-shadow: 
            inset 0 2px 4px rgba(0, 0, 0, 0.1),
            0 0 0 3px rgba(255, 255, 255, 0.1);
    }
    
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: rgba(255, 255, 255, 0.5);
    }
    
    /* Button with Gradient and Animation */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 16px;
        padding: 14px 32px;
        font-weight: 700;
        font-size: 15px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 
            0 8px 25px rgba(102, 126, 234, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
        transition: left 0.5s ease;
    }
    
    .stButton > button:hover::before {
        left: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 
            0 12px 35px rgba(102, 126, 234, 0.6),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
    }
    
    .stButton > button:active {
        transform: translateY(-1px) scale(0.98);
    }
    
    /* File Uploader Styling */
    .stFileUploader > div {
        background: rgba(255, 255, 255, 0.1);
        border: 2px dashed rgba(255, 255, 255, 0.3);
        border-radius: 16px;
        padding: 2rem;
        transition: all 0.3s ease;
    }
    
    .stFileUploader > div:hover {
        background: rgba(255, 255, 255, 0.15);
        border-color: rgba(255, 255, 255, 0.4);
    }
    
    /* Sidebar with Gradient */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(102, 126, 234, 0.3) 0%, rgba(118, 75, 162, 0.3) 100%);
        backdrop-filter: blur(30px);
        border-right: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    section[data-testid="stSidebar"] h2 {
        color: white;
        font-weight: 700;
    }
    
    /* Slider Customization */
    .stSlider > div > div > div {
        background: rgba(255, 255, 255, 0.2);
    }
    
    .stSlider > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Alert Messages */
    .stSuccess, .stInfo, .stWarning, .stError {
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(20px);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white;
    }
    
    /* Links with Glow Effect */
    a {
        color: #a5f3fc;
        text-decoration: none;
        font-weight: 600;
        transition: all 0.3s ease;
        position: relative;
    }
    
    a::after {
        content: '';
        position: absolute;
        bottom: -2px;
        left: 0;
        width: 0;
        height: 2px;
        background: linear-gradient(90deg, #a5f3fc 0%, #67e8f9 100%);
        transition: width 0.3s ease;
    }
    
    a:hover::after {
        width: 100%;
    }
    
    a:hover {
        color: #67e8f9;
        text-shadow: 0 0 10px rgba(103, 232, 249, 0.5);
    }
    
    /* Loading Spinner */
    .stSpinner > div {
        border-color: rgba(255, 255, 255, 0.3);
        border-top-color: white;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
        margin: 2rem 0;
    }
    
    /* Research Badge */
    .research-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        background: rgba(0, 242, 96, 0.2);
        border: 1px solid rgba(0, 242, 96, 0.4);
        border-radius: 20px;
        color: #00f260;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-left: 12px;
    }
    
    /* Stats Grid */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .stat-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.2);
        text-align: center;
    }
    
    .stat-value {
        font-size: 36px;
        font-weight: 800;
        color: white;
        line-height: 1;
        margin-bottom: 0.5rem;
    }
    
    .stat-label {
        font-size: 13px;
        color: rgba(255, 255, 255, 0.7);
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Hero Section
# ---------------------------
st.markdown("""
    <div class='hero-section'>
        <div class='hero-title'>🚀 AI Job Concierge</div>
        <div class='hero-subtitle'>
            Advanced AI-powered platform that analyzes your resume, extracts key skills, 
            searches multiple job databases, and ranks opportunities using deep semantic matching
        </div>
        <div class='hero-badge'>✨ Enhanced with Deep Research</div>
    </div>
""", unsafe_allow_html=True)

# Memory
mb = MemoryBank()

# Sidebar
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    user_id = st.text_input("User Identifier", placeholder="Enter unique ID")
    
    st.markdown("---")
    
    st.markdown("### 📊 Search Settings")
    st.markdown("Configure how the AI searches and analyzes job opportunities")

    if st.button("🎯 Create Profile"):
        sample = {"name": "Demo User", "preferences": {"role": "ML Engineer", "location": "India"}}
        uid = mb.save_profile(user_id, sample)
        st.success(f"✅ Profile Created: {uid}")
    
    st.markdown("---")
    st.markdown("### 💡 Features")
    st.markdown("""
    - 🔍 Multi-source job search
    - 🧠 AI skill extraction
    - 📊 Semantic matching
    - 🎯 Smart ranking
    """)

# ---------------------------
# Resume Upload Section
# ---------------------------
st.markdown("<div class='section-header'>📄 Resume Analysis</div>", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("#### Upload Document")
    uploaded = st.file_uploader(
        "Drop your resume here or click to browse",
        type=["pdf", "txt", "docx"],
        help="Supports PDF, TXT, and DOCX formats"
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("#### Manual Entry")
    resume_text = st.text_area(
        "Paste your resume content",
        height=150,
        placeholder="Enter your resume text here..."
    )
    st.markdown("</div>", unsafe_allow_html=True)

if uploaded:
    resume_text = read_uploaded_file(uploaded)
    st.success("✅ Resume successfully loaded and parsed!")

# ---------------------------
# Skill Extraction
# ---------------------------
if resume_text:
    st.markdown("<div class='section-header'>🧠 Extracted Skills & Competencies</div>", unsafe_allow_html=True)
    
    skills = extract_skills(resume_text)
    if len(skills) > 0:
        skills_html = "<div class='skills-container'>" + \
                     "".join([f"<span class='skill-chip'>{s}</span>" for s in skills]) + \
                     "</div>"
        st.markdown(skills_html, unsafe_allow_html=True)
        
        # Stats
        st.markdown(f"""
        <div class='stats-grid'>
            <div class='stat-card'>
                <div class='stat-value'>{len(skills)}</div>
                <div class='stat-label'>Skills Identified</div>
            </div>
            <div class='stat-card'>
                <div class='stat-value'>{len(resume_text.split())}</div>
                <div class='stat-label'>Words Analyzed</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("ℹ️ No skills detected. Try adding more detailed information about your experience.")

# ---------------------------
# Job Search Section
# ---------------------------
st.markdown("<div class='section-header'>🔍 Intelligent Job Search <span class='research-badge'>🔬 Deep Research Enabled</span></div>", unsafe_allow_html=True)

search_col1, search_col2 = st.columns([3, 1])

with search_col1:
    query = st.text_input(
        "Job Search Query",
        value="Machine Learning Engineer",
        placeholder="e.g., Data Scientist, Software Engineer..."
    )

with search_col2:
    threshold = st.slider(
        "Match Threshold",
        0.0, 1.0, 0.20,
        help="Minimum similarity score (0-1)"
    )

st.markdown(f"""
<div class='glass-card'>
    <strong>🎯 Search Configuration:</strong><br>
    Query: <code>{query}</code> | Threshold: <code>{threshold}</code><br>
    Sources: Indeed, Naukri, LinkedIn | Analysis: Deep semantic matching with multi-source verification
</div>
""", unsafe_allow_html=True)

if st.button("🚀 START DEEP SEARCH"):
    if not resume_text:
        st.error("⚠️ Please upload or paste your resume first!")
    else:
        # Progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("🔍 Phase 1: Searching job databases...")
        progress_bar.progress(20)
        time.sleep(0.5)
        
        with st.spinner("Fetching jobs from multiple sources..."):
            jobs = fetch_real_jobs(query, top_k=10)
            time.sleep(0.8)
        
        status_text.text("🧠 Phase 2: Analyzing job descriptions...")
        progress_bar.progress(50)
        time.sleep(0.5)
        
        status_text.text("📊 Phase 3: Computing semantic similarities...")
        progress_bar.progress(70)
        time.sleep(0.5)
        
        status_text.text("🎯 Phase 4: Ranking and filtering results...")
        progress_bar.progress(90)
        
        rec_agent = RecommendationAgent()
        results = rec_agent.recommend_once(resume_text, query, threshold)
        
        progress_bar.progress(100)
        status_text.empty()
        progress_bar.empty()
        
        st.success(f"✨ Analysis complete! Found {len(results)} matching positions out of {len(jobs)} total jobs.")

        # Results Section
        st.markdown("<div class='section-header'>🎯 Top Matched Opportunities</div>", unsafe_allow_html=True)
        
        if len(results) == 0:
            st.warning(f"⚠️ No jobs matched the threshold of {threshold}. Try lowering the threshold or adjusting your query.")
        else:
            for idx, job in enumerate(results, 1):
                score_pct = int(job["score"] * 100)
                
                st.markdown(f"""
                <div class='job-card'>
                    <div class='job-title'>#{idx} {job['title']}</div>
                    <div class='job-company'>🏢 {job['company']}</div>
                    <div class='job-description'>{job["description"][:350]}...</div>
                    
                    <div class='score-section'>
                        <div class='score-label'>AI Match Score</div>
                        <div class='score-bar-container'>
                            <div class='score-bar-fill' style='width:{score_pct}%;'></div>
                        </div>
                        <div class='score-percentage'>{score_pct}%</div>
                    </div>
                    
                    <a href='{job['url']}' target='_blank'>📋 View Full Job Description →</a>
                </div>
                """, unsafe_allow_html=True)

            # Summary Stats
            avg_score = sum([j['score'] for j in results]) / len(results) * 100
            st.markdown(f"""
            <div class='stats-grid'>
                <div class='stat-card'>
                    <div class='stat-value'>{len(results)}</div>
                    <div class='stat-label'>Matched Jobs</div>
                </div>
                <div class='stat-card'>
                    <div class='stat-value'>{avg_score:.1f}%</div>
                    <div class='stat-label'>Average Match</div>
                </div>
                <div class='stat-card'>
                    <div class='stat-value'>{max([j['score'] for j in results])*100:.0f}%</div>
                    <div class='stat-label'>Best Match</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
