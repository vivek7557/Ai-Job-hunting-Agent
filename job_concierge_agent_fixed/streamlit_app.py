import streamlit as st
import logging
from agents.job_scraper_agent import fetch_real_jobs
from agents.recommendation_agent import RecommendationAgent
from tools.cv_upload_tool import read_uploaded_file
from agents.skill_extractor import extract_skills
from memory.long_term_memory import MemoryBank
import time

st.set_page_config(
    page_title="AI Job Concierge - Research System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

logger = logging.getLogger("ui")

# ---------------------------
#  RESEARCH PAPER UI STYLES
# ---------------------------
st.markdown("""
    <style>
    /* Academic Paper Layout */
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Text:wght@400;600;700&family=Source+Sans+Pro:wght@300;400;600&display=swap');
    
    .stApp {
        background: #f8f8f8;
        font-family: 'Crimson Text', serif;
    }
    
    /* Paper Container */
    .main .block-container {
        max-width: 900px;
        padding: 3rem 2rem;
        background: white;
        box-shadow: 0 0 30px rgba(0,0,0,0.1);
        margin: 2rem auto;
    }
    
    /* Title Section - Research Paper Style */
    .paper-title { 
        font-size: 36px; 
        font-weight: 700; 
        text-align: center;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
        line-height: 1.3;
        font-family: 'Crimson Text', serif;
    }
    
    .paper-subtitle { 
        font-size: 16px; 
        text-align: center;
        color: #555;
        margin-bottom: 2rem;
        font-style: italic;
        font-family: 'Source Sans Pro', sans-serif;
    }
    
    .authors {
        text-align: center;
        font-size: 14px;
        color: #333;
        margin-bottom: 1rem;
        font-family: 'Source Sans Pro', sans-serif;
    }
    
    .affiliation {
        text-align: center;
        font-size: 13px;
        color: #666;
        margin-bottom: 2rem;
        font-style: italic;
    }
    
    .date {
        text-align: center;
        font-size: 13px;
        color: #888;
        margin-bottom: 2rem;
        padding-bottom: 2rem;
        border-bottom: 1px solid #ddd;
    }
    
    /* Abstract Box */
    .abstract-box {
        background: #f9f9f9;
        border-left: 4px solid #2c3e50;
        padding: 1.5rem;
        margin: 2rem 0;
        font-size: 15px;
        line-height: 1.7;
    }
    
    .abstract-title {
        font-weight: 700;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.8rem;
        color: #2c3e50;
    }
    
    /* Section Headers */
    h1, h2, h3 {
        font-family: 'Crimson Text', serif;
        color: #1a1a1a;
        font-weight: 700;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    
    h2 {
        font-size: 24px;
        border-bottom: 2px solid #2c3e50;
        padding-bottom: 0.3rem;
    }
    
    h3 {
        font-size: 20px;
        font-style: italic;
    }
    
    /* Body Text */
    p, .stMarkdown {
        font-size: 16px;
        line-height: 1.8;
        color: #333;
        text-align: justify;
        font-family: 'Crimson Text', serif;
    }
    
    /* Results Card - Table Style */
    .result-card {
        background: white;
        border: 1px solid #ddd;
        padding: 1.5rem;
        margin: 1.5rem 0;
        border-radius: 0;
    }
    
    .result-header {
        font-size: 18px;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 0.5rem;
        font-family: 'Crimson Text', serif;
    }
    
    .result-meta {
        font-size: 14px;
        color: #666;
        margin-bottom: 1rem;
        font-family: 'Source Sans Pro', sans-serif;
    }
    
    .result-description {
        font-size: 15px;
        line-height: 1.7;
        color: #444;
        text-align: justify;
        margin-bottom: 1rem;
    }
    
    /* Keywords/Skills - Citation Style */
    .keyword-container {
        margin: 1.5rem 0;
        padding: 1rem;
        background: #fafafa;
        border-top: 1px solid #ddd;
        border-bottom: 1px solid #ddd;
    }
    
    .keyword-label {
        font-weight: 600;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #555;
        margin-bottom: 0.5rem;
        font-family: 'Source Sans Pro', sans-serif;
    }
    
    .keyword {
        display: inline;
        font-size: 14px;
        color: #2c3e50;
        font-family: 'Source Sans Pro', sans-serif;
    }
    
    /* Score Display - Statistical */
    .score-container {
        background: #f5f5f5;
        padding: 0.8rem;
        border-left: 3px solid #27ae60;
        margin-top: 1rem;
        font-family: 'Source Sans Pro', sans-serif;
    }
    
    .score-label {
        font-size: 13px;
        color: #555;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .score-value {
        font-size: 20px;
        font-weight: 700;
        color: #27ae60;
        font-family: 'Crimson Text', serif;
    }
    
    /* Buttons - Academic Style */
    .stButton > button {
        background: #2c3e50;
        color: white;
        border: none;
        padding: 0.6rem 2rem;
        font-family: 'Source Sans Pro', sans-serif;
        font-size: 14px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        border-radius: 0;
        transition: background 0.3s ease;
    }
    
    .stButton > button:hover {
        background: #34495e;
    }
    
    /* Input Fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border: 1px solid #ccc;
        border-radius: 0;
        font-family: 'Crimson Text', serif;
        font-size: 15px;
    }
    
    /* Sidebar - Table of Contents Style */
    section[data-testid="stSidebar"] {
        background: #f5f5f5;
        border-right: 1px solid #ddd;
    }
    
    section[data-testid="stSidebar"] h2 {
        font-family: 'Crimson Text', serif;
        font-size: 18px;
        color: #2c3e50;
        border-bottom: 2px solid #2c3e50;
        padding-bottom: 0.5rem;
    }
    
    /* Links - Citation Style */
    a {
        color: #2c3e50;
        text-decoration: underline;
        font-weight: 400;
    }
    
    a:hover {
        color: #34495e;
    }
    
    /* Figure/Table Caption Style */
    .caption {
        font-size: 13px;
        font-style: italic;
        color: #666;
        text-align: center;
        margin-top: 0.5rem;
        font-family: 'Source Sans Pro', sans-serif;
    }
    
    /* Divider */
    hr {
        border: none;
        border-top: 1px solid #ddd;
        margin: 2rem 0;
    }
    
    /* Success/Info Messages - Footnote Style */
    .stSuccess, .stInfo, .stError {
        border-radius: 0;
        border-left: 3px solid #2c3e50;
        font-family: 'Source Sans Pro', sans-serif;
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Research Paper Header
# ---------------------------
st.markdown("<div class='paper-title'>AI-Driven Job Recommendation System:<br>A Skills-Based Matching Approach</div>", unsafe_allow_html=True)
st.markdown("<div class='paper-subtitle'>An Interactive Platform for Intelligent Career Matching</div>", unsafe_allow_html=True)
st.markdown("<div class='authors'>Research System • AI Job Concierge Laboratory</div>", unsafe_allow_html=True)
st.markdown("<div class='affiliation'>Department of Intelligent Systems & Career Analytics</div>", unsafe_allow_html=True)

# Get current date
from datetime import datetime
current_date = datetime.now().strftime("%B %d, %Y")
st.markdown(f"<div class='date'>Date: {current_date}</div>", unsafe_allow_html=True)

# Abstract
st.markdown("""
<div class='abstract-box'>
<div class='abstract-title'>Abstract</div>
This system implements an AI-powered job recommendation platform that leverages natural language processing 
and embedding-based similarity matching to connect job seekers with relevant opportunities. The platform 
extracts skills from resume documents, queries multiple job databases, and ranks positions using semantic 
similarity algorithms. The system demonstrates the practical application of machine learning in career 
services and recruitment optimization.
</div>
""", unsafe_allow_html=True)

# Memory
mb = MemoryBank()

# Sidebar - Table of Contents
with st.sidebar:
    st.markdown("## Table of Contents")
    st.markdown("""
    1. [Introduction](#introduction)
    2. [Methodology](#methodology)
    3. [Data Input](#data-input)
    4. [Results](#results)
    5. [Settings](#settings)
    """)
    
    st.markdown("---")
    st.markdown("### Settings")
    user_id = st.text_input("User Identifier", help="Optional unique identifier for session tracking")

    if st.button("Initialize Profile"):
        sample = {"name": "Demo User", "preferences": {"role": "ML Engineer", "location": "India"}}
        uid = mb.save_profile(user_id, sample)
        st.success(f"Profile initialized: {uid}")

# ---------------------------
# Section 1: Introduction
# ---------------------------
st.markdown("## 1. Introduction")
st.markdown("""
The job search process presents significant challenges in matching candidate qualifications with employer 
requirements. This research system addresses these challenges through automated skills extraction and 
semantic job matching algorithms.
""")

# ---------------------------
# Section 2: Data Input
# ---------------------------
st.markdown("## 2. Data Input & Preprocessing")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 2.1 Document Upload")
    uploaded = st.file_uploader("Upload Resume Document", type=["pdf", "txt", "docx"], 
                                help="Supported formats: PDF, TXT, DOCX")

with col2:
    st.markdown("### 2.2 Direct Input")
    resume_text = st.text_area("Manual Text Entry", height=150, 
                               help="Alternatively, paste resume content directly")

if uploaded:
    resume_text = read_uploaded_file(uploaded)
    st.success("Document successfully processed and parsed.")

# ---------------------------
# Section 3: Feature Extraction
# ---------------------------
if resume_text:
    st.markdown("## 3. Feature Extraction Results")
    st.markdown("### 3.1 Identified Competencies")
    
    skills = extract_skills(resume_text)
    if len(skills) > 0:
        st.markdown("<div class='keyword-container'>", unsafe_allow_html=True)
        st.markdown("<div class='keyword-label'>Extracted Keywords:</div>", unsafe_allow_html=True)
        keywords_text = ", ".join([f"<span class='keyword'>{s}</span>" for s in skills])
        st.markdown(keywords_text, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown(f"<div class='caption'>Figure 1: Extracted skills and competencies (n={len(skills)})</div>", unsafe_allow_html=True)
    else:
        st.info("**Note:** No significant skills detected in the provided text. Consider expanding the content for improved feature extraction.")

# ---------------------------
# Section 4: Methodology & Execution
# ---------------------------
st.markdown("## 4. Methodology")
st.markdown("### 4.1 Search Parameters")

query = st.text_input("Query Terms", value="Machine Learning Engineer", 
                     help="Enter job role or position keywords")
threshold = st.slider("Similarity Threshold (α)", 0.0, 1.0, 0.20, 
                     help="Minimum matching score for inclusion in results")

st.markdown(f"""
**Search Configuration:**  
- Query: `{query}`  
- Threshold: `α = {threshold}`  
- Data Sources: Indeed, Naukri, LinkedIn
""")

if st.button("Execute Search"):
    if not resume_text:
        st.error("**Error:** Resume data required. Please upload a document or enter text above.")
    else:
        with st.spinner("Querying external databases and computing similarity metrics..."):
            jobs = fetch_real_jobs(query, top_k=10)
            time.sleep(1)

        st.success(f"Search completed. Retrieved {len(jobs)} candidate positions.")

        rec_agent = RecommendationAgent()
        results = rec_agent.recommend_once(resume_text, query, threshold)

        # ---------------------------
        # Section 5: Results
        # ---------------------------
        st.markdown("## 5. Results & Analysis")
        st.markdown("### 5.1 Ranked Job Matches")
        st.markdown(f"The following positions exceeded the similarity threshold (α > {threshold}) and are presented in descending order of match quality.")

        for idx, job in enumerate(results, 1):
            st.markdown(f"#### Position {idx}")
            st.markdown("<div class='result-card'>", unsafe_allow_html=True)
            
            st.markdown(f"<div class='result-header'>{job['title']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='result-meta'>Organization: {job['company']}</div>", unsafe_allow_html=True)
            
            st.markdown(f"<div class='result-description'>{job['description'][:400]}...</div>", unsafe_allow_html=True)
            
            score_pct = int(job["score"] * 100)
            st.markdown(f"""
            <div class='score-container'>
                <span class='score-label'>Match Score:</span> 
                <span class='score-value'>{score_pct}%</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"[View Full Position Details →]({job['url']})")
            st.markdown("</div>", unsafe_allow_html=True)

        # Conclusion
        st.markdown("## 6. Conclusion")
        st.markdown(f"""
        The system successfully identified {len(results)} positions matching the specified criteria. 
        The semantic similarity approach demonstrates effective capability in matching candidate profiles 
        with job requirements, with scores ranging from {min([j['score'] for j in results])*100:.1f}% 
        to {max([j['score'] for j in results])*100:.1f}%.
        """)
