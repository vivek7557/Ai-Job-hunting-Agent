import streamlit as st
import logging
from tools.cv_upload_tool import read_uploaded_file
from agents.resume_parser_agent import parse_resume_text
from agents.recommendation_agent import RecommendationAgent
from tools.google_search_tool import search_jobs
from memory.long_term_memory import MemoryBank

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ai_job_concierge')

st.set_page_config(page_title='AI Job Concierge Agent', layout='centered')

st.title('AI Job Concierge — Demo')
st.markdown('Upload your resume (TXT/PDF) and search for roles. This demo uses a mocked job fetcher.')

mb = MemoryBank()

with st.sidebar:
    st.header('User Profile')
    user_id = st.text_input('User ID (optional)')
    if st.button('Create sample profile'):
        sample = {'name':'Demo User', 'preferences':{'location':'India','role':'ML Engineer'}}
        uid = mb.save_profile(user_id, sample)
        st.success(f'Created profile {uid}')

uploaded = st.file_uploader('Upload your resume (txt or paste text)', type=['txt','pdf','docx'])
resume_text = st.text_area('Or paste resume text here (quick)')

resume_parsed = None
if uploaded is not None:
    resume_text = read_uploaded_file(uploaded)

if st.button('Parse Resume') and resume_text:
    resume_parsed = parse_resume_text(resume_text)
    st.subheader('Parsed Resume')
    st.json(resume_parsed)

st.markdown('---')
st.subheader('Job Search & Match')
query = st.text_input('Search query (e.g., Machine Learning)', value='Machine Learning')
threshold = st.slider('Recommendation threshold (cosine similarity)', min_value=0.0, max_value=1.0, value=0.15)
if st.button('Fetch & Recommend'):
    if not resume_text:
        st.error('Upload or paste resume text first.')
    else:
        rec_agent = RecommendationAgent()
        recommended = rec_agent.recommend_once(resume_text, query, threshold)
        st.write(f'Found {len(recommended)} recommended jobs (threshold={threshold})')
        for r in recommended[:20]:
            st.markdown(f"**{r['title']}** at *{r['company']}* — score: {r['score']:.3f}")
            st.markdown(r['url'])
            st.caption(r['description'][:300] + '...')
