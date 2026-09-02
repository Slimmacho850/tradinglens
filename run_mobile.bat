@echo off
title Trading Lens - Mobile Network Server
echo ===================================================
echo   DR LENS - MOBILE NETWORK SERVER
echo ===================================================
echo.
echo Your local network IP address is:
for /f "tokens=4" %%a in ('route print ^| findstr 0.0.0.0 ^| findstr /v "0.0.0.0.*0.0.0.0"') do (
    echo   ==^> Open on your phone: http://%%a:8501
    goto :done_ip
)
:done_ip
echo.
echo Starting Streamlit server...
echo Press Ctrl+C in this window to stop the server.
echo ===================================================
echo.

call venv\Scripts\activate.bat 2>nul
streamlit run src\dashboard.py --server.address=0.0.0.0 --server.port=8501
pause
