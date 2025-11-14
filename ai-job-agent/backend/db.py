import sqlite3
from pathlib import Path
from typing import List, Optional
import json


DB_PATH = Path(__file__).parent / '../../jobs.db'


def init_db():
conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS jobs (
id TEXT PRIMARY KEY,
title TEXT,
company TEXT,
location TEXT,
posted_at TEXT,
description TEXT,
url TEXT
)
''')
conn.commit()
conn.close()


def save_jobs(jobs: List[dict]):
conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()
for j in jobs:
try:
cur.execute('INSERT OR REPLACE INTO jobs (id,title,company,location,posted_at,description,url) VALUES (?,?,?,?,?,?,?)',
(j['id'], j['title'], j['company'], j['location'], j['posted_at'], j['description'], j['url']))
except Exception as e:
print('db error', e)
conn.commit()
conn.close()


def get_jobs(role: Optional[str] = None, location: Optional[str] = None, limit: int = 50):
conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()
query = 'SELECT id,title,company,location,posted_at,description,url FROM jobs'
params = []
filters = []
if role:
filters.append('title LIKE ?')
params.append(f'%{role}%')
if location:
filters.append('location LIKE ?')
params.append(f'%{location}%')
if filters:
query += ' WHERE ' + ' AND '.join(filters)
query += ' ORDER BY posted_at DESC LIMIT ?'
params.append(limit)
cur.execute(query, params)
rows = cur.fetchall()
conn.close()
keys = ['id','title','company','location','posted_at','description','url']
return [dict(zip(keys, r)) for r in rows]
