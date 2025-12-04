"""Main entry point for the Streamlit application"""
import sys
from pathlib import Path

# Add the job_concierge_agent_fixed directory to Python path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir / "job_concierge_agent_fixed"))

# Now import and run the streamlit app
from streamlit_app import RecommendationAgent

# Your Streamlit UI code goes here
import streamlit as st

st.title("AI Job Hunting Agent")

# Initialize the recommendation agent
if 'agent' not in st.session_state:
    st.session_state.agent = RecommendationAgent()

# Add your UI components here
st.write("Welcome to the AI Job Hunting Agent!")
