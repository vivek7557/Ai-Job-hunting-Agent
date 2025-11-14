import React, {useEffect, useState} from 'react'
import axios from 'axios'


export default function App(){
const [jobs, setJobs] = useState([])
const [role, setRole] = useState('')
const [location, setLocation] = useState('')
const [resumeText, setResumeText] = useState('')
const [selectedJob, setSelectedJob] = useState(null)
const [matchResult, setMatchResult] = useState(null)


useEffect(()=>{
fetchJobs()
},[])


async function fetchJobs(){
const res = await axios.get('http://localhost:8000/jobs?limit=20')
setJobs(res.data.jobs)
}


async function refresh(){
await axios.post('http://localhost:8000/jobs/refresh')
fetchJobs()
}


async function onFileChange(e){
const f = e.target.files[0]
const form = new FormData()
form.append('file', f)
const res = await axios.post('http://localhost:8000/resume/upload', form, {headers:{'Content-Type':'multipart/form-data'}})
setResumeText(res.data.text)
}


async function analyze(){
if(!resumeText || !selectedJob) return alert('Upload resume & select a job')
const res = await axios.post('http://localhost:8000/resume/match', {resume_text: resumeText, job_description: selectedJob.description})
setMatchResult(res.data)
}


return (
<div style={{padding:20}}>
<h1>AI Job Agent — Live Jobs (demo)</h1>
<div>
<button onClick={refresh}>Refresh Jobs (manual)</button>
</div>


<div style={{display:'flex', gap:20, marginTop:20}}>
<div style={{flex:1}}>
<h2>Jobs</h2>
<ul>
{jobs.map(j => (
<li key={j.id} style={{border:'1px solid #ddd', padding:8, margin:6}} onClick={()=>setSelectedJob(j)}>
<strong>{j.title}</strong> — {j.company} ({j.location})
<div style={{fontSize:12}}>{j.posted_at}</div>
