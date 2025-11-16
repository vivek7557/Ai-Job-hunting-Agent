# AI Job Concierge Agent - Capstone Project

**Track:** Concierge Agents
**Description:** Multi-agent system to discover fresh job postings, analyze resumes, match resumes to job descriptions, and notify candidates of high-quality matches.

## What's included
- `agents/` - job_scraper_agent, resume_parser_agent, jd_matcher_agent, recommendation_agent
- `tools/` - simple tools (mock google search tool, cv upload helper)
- `memory/` - simple in-memory long-term memory implementation
- `app/` - Streamlit demo app (`main_app.py`)
- `evaluation/` - basic evaluation script
- `requirements.txt` - Python dependencies
- `submit_writeup.md` - template for Kaggle submission
- `LICENSE` - MIT

## Quick start (local)
1. Create a virtualenv and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   ```
2. Run the demo Streamlit app:
   ```bash
   streamlit run app/main_app.py
   ```
3. Upload your resume (PDF or TXT) inside the app to see resume parsing and job matching.

## Notes
- The `tools/google_search_tool.py` contains a **mock** job fetcher to keep the demo runnable without external API keys. Replace with a live scraper or Google Search API for production.
- The project demonstrates multi-agent patterns, sessions/memory, loop agent (recommendation loop), simple observability via logging, and evaluation scripts.
- See `submit_writeup.md` for the Kaggle submission template.


## NEW: Added features
- Scheduler (pause/resume) via `agents/scheduler_controller.py` (APScheduler fallback implemented)
- A2A Router (`agents/a2a_router.py`) for agent-to-agent messaging
- MCP and OpenAPI tool stubs (`tools/mcp_tool.py`, `tools/openapi_tool.py`)
- Parallel job fetching helper (`agents/job_scraper_agent.fetch_from_sources_parallel`)
- Observability helpers (`observability/metrics.py`)
- Extended evaluation metrics (`evaluation/metrics_extended.py`)
- Demo video script and enhanced Kaggle submission docs (`docs/demo_video_script.md`)
