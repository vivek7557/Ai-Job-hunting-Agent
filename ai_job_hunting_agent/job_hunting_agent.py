import os
import json
import time
import schedule
from datetime import datetime
from typing import List, Dict, Optional
import anthropic
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class JobHuntingAgent:
    """AI-powered job hunting agent that searches, analyzes, and notifies about jobs"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the job hunting agent with configuration"""
        self.config = self.load_config(config_path)
        self.client = anthropic.Anthropic(api_key=self.config.get('anthropic_api_key', os.environ.get('ANTHROPIC_API_KEY', '')))
        self.jobs_db_path = "jobs_database.json"
        self.load_jobs_database()
        
    def load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file {config_path} not found. Creating default config.")
            return self.create_default_config(config_path)
    
    def create_default_config(self, config_path: str) -> Dict:
        """Create default configuration file"""
        default_config = {
            "anthropic_api_key": "YOUR_API_KEY_HERE",
            "user_profile": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1234567890",
                "desired_roles": ["Software Engineer", "Data Scientist", "ML Engineer"],
                "skills": ["Python", "Machine Learning", "SQL", "AWS"],
                "experience_years": 5,
                "education": "BS Computer Science",
                "location_preferences": ["Remote", "San Francisco", "New York"]
            },
            "job_search": {
                "keywords": ["python developer", "machine learning engineer", "data scientist"],
                "excluded_keywords": ["senior", "manager"],
                "min_salary": 80000,
                "job_types": ["full-time", "contract"]
            },
            "notifications": {
                "email_enabled": True,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "your_email@gmail.com",
                "sender_password": "your_app_password",
                "notification_threshold": 0.7
            },
            "schedule": {
                "search_times": ["09:00", "15:00", "21:00"]
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info(f"Created default config at {config_path}. Please update with your details.")
        return default_config
    
    def load_jobs_database(self):
        """Load existing jobs database"""
        try:
            with open(self.jobs_db_path, 'r') as f:
                self.jobs_database = json.load(f)
        except FileNotFoundError:
            self.jobs_database = {"jobs": [], "last_updated": None}
            self.save_jobs_database()
    
    def save_jobs_database(self):
        """Save jobs database to file"""
        with open(self.jobs_db_path, 'w') as f:
            json.dump(self.jobs_database, f, indent=2)
    
    def search_jobs(self) -> List[Dict]:
        """
        Search for jobs using Claude with web search capability
        Returns list of job postings
        """
        logger.info("Starting job search...")
        
        search_queries = self.config['job_search']['keywords']
        all_jobs = []
        
        for query in search_queries:
            prompt = f"""Search for recent job postings for: {query}
            
Focus on jobs that match these criteria:
- Location: {', '.join(self.config['user_profile']['location_preferences'])}
- Job types: {', '.join(self.config['job_search']['job_types'])}

Return job listings with:
1. Job title
2. Company name
3. Location
4. Job description summary
5. Required skills
6. Application link

Format as JSON array."""

            try:
                message = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    tools=[{
                        "type": "web_search_20250305",
                        "name": "web_search"
                    }],
                    messages=[{"role": "user", "content": prompt}]
                )
                
                # Extract jobs from response
                jobs = self.parse_job_results(message)
                all_jobs.extend(jobs)
                logger.info(f"Found {len(jobs)} jobs for query: {query}")
                
            except Exception as e:
                logger.error(f"Error searching jobs for '{query}': {str(e)}")
                continue
        
        return all_jobs
    
    def parse_job_results(self, message) -> List[Dict]:
        """Parse job results from Claude's response"""
        jobs = []
        
        for content in message.content:
            if content.type == "text":
                text = content.text
                # Try to extract JSON from the response
                try:
                    # Look for JSON array in the text
                    start_idx = text.find('[')
                    end_idx = text.rfind(']') + 1
                    if start_idx != -1 and end_idx > start_idx:
                        json_str = text[start_idx:end_idx]
                        parsed_jobs = json.loads(json_str)
                        jobs.extend(parsed_jobs)
                except json.JSONDecodeError:
                    logger.warning("Could not parse JSON from response")
        
        return jobs
    
    def analyze_job_description(self, job: Dict) -> Dict:
        """
        Analyze job description to extract key insights
        Returns analysis with match score and recommendations
        """
        logger.info(f"Analyzing job: {job.get('title', 'Unknown')}")
        
        user_profile = self.config['user_profile']
        
        prompt = f"""Analyze this job posting against the candidate profile:

JOB POSTING:
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Description: {job.get('description', 'N/A')}
Required Skills: {job.get('skills', [])}

CANDIDATE PROFILE:
Skills: {user_profile['skills']}
Experience: {user_profile['experience_years']} years
Education: {user_profile['education']}
Desired Roles: {user_profile['desired_roles']}

Provide analysis in JSON format:
{{
    "match_score": 0.0-1.0,
    "matching_skills": [],
    "missing_skills": [],
    "key_requirements": [],
    "recommendations": [],
    "salary_estimate": "estimated range",
    "application_priority": "high/medium/low"
}}"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            analysis_text = message.content[0].text
            
            # Extract JSON from response
            start_idx = analysis_text.find('{')
            end_idx = analysis_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = analysis_text[start_idx:end_idx]
                analysis = json.loads(json_str)
                return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing job: {str(e)}")
            return {"match_score": 0.0, "error": str(e)}
        
        return {"match_score": 0.0}
    
    def generate_cv(self, job: Dict, analysis: Dict) -> str:
        """
        Generate tailored CV for specific job
        Returns CV as formatted text
        """
        logger.info(f"Generating CV for: {job.get('title', 'Unknown')}")
        
        user_profile = self.config['user_profile']
        
        prompt = f"""Generate a tailored CV/resume for this job application:

TARGET JOB:
{job.get('title', 'N/A')} at {job.get('company', 'N/A')}

KEY REQUIREMENTS:
{analysis.get('key_requirements', [])}

CANDIDATE PROFILE:
Name: {user_profile['name']}
Email: {user_profile['email']}
Phone: {user_profile['phone']}
Skills: {user_profile['skills']}
Experience: {user_profile['experience_years']} years
Education: {user_profile['education']}

Create a professional CV that:
1. Highlights relevant skills matching the job requirements
2. Emphasizes experience relevant to this role
3. Uses achievement-oriented language
4. Includes a tailored professional summary
5. Follows standard CV format

Format the CV professionally with clear sections."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            cv_text = message.content[0].text
            
            # Save CV to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            company_name = job.get('company', 'Unknown').replace(' ', '_')
            filename = f"cv_{company_name}_{timestamp}.txt"
            
            with open(f"generated_cvs/{filename}", 'w') as f:
                f.write(cv_text)
            
            logger.info(f"CV saved to generated_cvs/{filename}")
            return cv_text
            
        except Exception as e:
            logger.error(f"Error generating CV: {str(e)}")
            return f"Error generating CV: {str(e)}"
    
    def send_notification(self, jobs: List[Dict], analyses: List[Dict]):
        """
        Send email notification about new job opportunities
        """
        if not self.config['notifications']['email_enabled']:
            logger.info("Email notifications disabled")
            return
        
        # Filter high-priority jobs
        threshold = self.config['notifications']['notification_threshold']
        priority_jobs = [
            (job, analysis) for job, analysis in zip(jobs, analyses)
            if analysis.get('match_score', 0) >= threshold
        ]
        
        if not priority_jobs:
            logger.info("No high-priority jobs to notify")
            return
        
        # Compose email
        subject = f"🎯 {len(priority_jobs)} New Job Matches Found!"
        
        body = f"""<html><body>
<h2>New Job Opportunities - {datetime.now().strftime('%Y-%m-%d')}</h2>
<p>Found {len(priority_jobs)} jobs matching your profile:</p>
"""
        
        for job, analysis in priority_jobs:
            match_score = analysis.get('match_score', 0) * 100
            body += f"""
<div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
    <h3>{job.get('title', 'Unknown')} - {job.get('company', 'Unknown')}</h3>
    <p><strong>Location:</strong> {job.get('location', 'N/A')}</p>
    <p><strong>Match Score:</strong> {match_score:.0f}%</p>
    <p><strong>Priority:</strong> {analysis.get('application_priority', 'N/A').upper()}</p>
    <p><strong>Matching Skills:</strong> {', '.join(analysis.get('matching_skills', []))}</p>
    <p><strong>Missing Skills:</strong> {', '.join(analysis.get('missing_skills', []))}</p>
    <p><strong>Apply:</strong> <a href="{job.get('link', '#')}">Application Link</a></p>
</div>
"""
        
        body += "</body></html>"
        
        try:
            self.send_email(subject, body)
            logger.info(f"Notification sent for {len(priority_jobs)} jobs")
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
    
    def send_email(self, subject: str, body: str):
        """Send email notification"""
        notif_config = self.config['notifications']
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = notif_config['sender_email']
        msg['To'] = self.config['user_profile']['email']
        
        html_part = MIMEText(body, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP(notif_config['smtp_server'], notif_config['smtp_port']) as server:
            server.starttls()
            server.login(notif_config['sender_email'], notif_config['sender_password'])
            server.send_message(msg)
    
    def is_duplicate_job(self, new_job: Dict) -> bool:
        """Check if job already exists in database"""
        for existing_job in self.jobs_database['jobs']:
            if (existing_job.get('title') == new_job.get('title') and
                existing_job.get('company') == new_job.get('company')):
                return True
        return False
    
    def run_job_search_cycle(self):
        """Run complete job search cycle"""
        logger.info("=" * 50)
        logger.info("Starting job search cycle")
        logger.info("=" * 50)
        
        # Step 1: Search for jobs
        jobs = self.search_jobs()
        logger.info(f"Total jobs found: {len(jobs)}")
        
        # Step 2: Filter out duplicates
        new_jobs = [job for job in jobs if not self.is_duplicate_job(job)]
        logger.info(f"New jobs (after filtering duplicates): {len(new_jobs)}")
        
        if not new_jobs:
            logger.info("No new jobs found")
            return
        
        # Step 3: Analyze each job
        analyses = []
        for job in new_jobs:
            analysis = self.analyze_job_description(job)
            analyses.append(analysis)
            
            # Add analysis to job data
            job['analysis'] = analysis
            job['discovered_date'] = datetime.now().isoformat()
        
        # Step 4: Generate CVs for high-match jobs
        for job, analysis in zip(new_jobs, analyses):
            if analysis.get('match_score', 0) >= 0.7:
                self.generate_cv(job, analysis)
        
        # Step 5: Send notifications
        self.send_notification(new_jobs, analyses)
        
        # Step 6: Update database
        self.jobs_database['jobs'].extend(new_jobs)
        self.jobs_database['last_updated'] = datetime.now().isoformat()
        self.save_jobs_database()
        
        logger.info("Job search cycle completed")
        logger.info("=" * 50)
    
    def start_agent(self):
        """Start the job hunting agent with scheduled runs"""
        logger.info("Starting Job Hunting Agent...")
        
        # Create necessary directories
        os.makedirs("generated_cvs", exist_ok=True)
        
        # Schedule job searches
        search_times = self.config['schedule']['search_times']
        for search_time in search_times:
            schedule.every().day.at(search_time).do(self.run_job_search_cycle)
            logger.info(f"Scheduled job search at {search_time}")
        
        # Run initial search
        logger.info("Running initial job search...")
        self.run_job_search_cycle()
        
        # Keep running
        logger.info("Agent is now running. Press Ctrl+C to stop.")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Agent stopped by user")

def main():
    """Main entry point"""
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║      AI Job Hunting Agent                         ║
    ║      Powered by Claude                            ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    # Initialize and start agent
    agent = JobHuntingAgent()
    agent.start_agent()

if __name__ == "__main__":
    main()
