@echo off
setlocal
if not exist data mkdir data
start "CMS FastAPI" cmd /k "cd /d %~dp0 && .venv\Scripts\python.exe -m uvicorn sidecar:app --host 127.0.0.1 --port 8001"
start "CMS Streamlit" cmd /k "cd /d %~dp0 && .venv\Scripts\python.exe -m streamlit run app.py --server.port 8501"
echo CMS started at http://localhost:8501
