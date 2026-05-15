@echo off
title Make Three Topic Prototypes
cd /d "C:\Users\zivfe\OneDrive\Documents\New project 2\viral-video-automation"
echo Creating three prototype videos...
echo.
"C:\Users\zivfe\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "C:\Users\zivfe\OneDrive\Documents\New project 2\viral-video-automation\MAKE_TOPIC_PROTOTYPES.py"
if errorlevel 1 (
  echo.
  echo Something failed. Send Codex the text in this window.
  echo.
  pause
  exit /b 1
)
echo.
echo Done. Open this folder:
echo C:\Users\zivfe\OneDrive\Documents\New project 2\viral-video-automation\output\prototypes
echo.
pause
