"""OpenAPI tool stub for calling external REST endpoints (e.g., ATS, HR APIs).
Replace 'requests' calls with proper API keys and schemas in production.
"""
import requests

def call_openapi(url: str, method: str = 'GET', json_data: dict = None, headers: dict = None):
    try:
        resp = requests.request(method, url, json=json_data, headers=headers, timeout=10)
        return {'status_code': resp.status_code, 'body': resp.text}
    except Exception as e:
        return {'error': str(e)}
