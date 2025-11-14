from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from .scraper import fetch_recent_jobs
from .resume import analyze_resume_vs_jd, parse_resume_text
from .db import init_db, save_jobs, get_jobs
from .scheduler import start_scheduler


app = FastAPI()
app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)


class JobQuery(BaseModel):
role: Optional[str] = None
location: Optional[str] = None
limit: int = 50


@app.on_event("startup")
async def startup_event():
init_db()
start_scheduler()


@app.get("/jobs")
async def api_get_jobs(role: Optional[str] = None, location: Optional[str] = None, limit: int = 50):
jobs = get_jobs(role=role, location=location, limit=limit)
return {"count": len(jobs), "jobs": jobs}


@app.post("/jobs/refresh")
async def api_refresh_jobs():
jobs = fetch_recent_jobs(hours=1)
save_jobs(jobs)
return {"added": len(jobs)}


@app.post("/resume/upload")
async def api_upload_resume(file: UploadFile = File(...)):
data = await file.read()
text = parse_resume_text(file.filename, data)
return {"text": text[:200]}


class MatchRequest(BaseModel):
resume_text: str
job_description: str


@app.post("/resume/match")
async def api_match(req: MatchRequest):
result = analyze_resume_vs_jd(req.resume_text, req.job_description)
return result


if __name__ == "__main__":
uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
