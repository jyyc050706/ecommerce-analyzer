@echo off
cd /d D:\ecommerce-analyzer
set STREAMLIT_SERVER_HEADLESS=true
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
start "" http://localhost:8501
D:\Marvis\MarvisAgent\1.0.1100.230\runtime\python311\python.exe -m streamlit run dashboard\app.py --server.port 8501
pause
