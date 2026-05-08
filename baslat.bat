@echo off
cd backend
..\venv\Scripts\python.exe -m uvicorn main:app --reload
pause
