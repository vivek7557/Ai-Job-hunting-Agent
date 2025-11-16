"""Simple CV upload helper (for Streamlit demo). Handles plain text uploads.
"""
import io

def read_uploaded_file(uploaded_file) -> str:
    # Streamlit's uploaded_file has read() method. We try to decode as utf-8.
    data = uploaded_file.read()
    try:
        text = data.decode('utf-8')
    except Exception:
        # Binary / PDF - in demo we fallback to a naive replacement
        text = str(data)
    return text
