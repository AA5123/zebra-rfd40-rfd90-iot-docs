@echo off
title RFD40/RFD90 API Docs
cd /d "%~dp0"
echo.
echo  RFD40 / RFD90 IoT Connector API Reference
echo  -----------------------------------------
echo  Serving docs at http://localhost:8080/
echo  Open that URL in your browser, then click index.html
echo  Press Ctrl+C to stop.
echo.
python scripts\serve_docs.py
pause

