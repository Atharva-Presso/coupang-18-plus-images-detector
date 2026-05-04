@echo off
echo Installing dependencies...
pip install -r requirements.txt --quiet
echo.
echo Starting dashboard...
echo Open browser to: http://127.0.0.1:5000
echo.
python app.py
pause
