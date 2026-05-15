@echo off
title Make Automatic Short Video
cd /d "C:\Users\zivfe\OneDrive\Documents\New project 2\viral-video-automation"
echo Creating your cinematic quote video...
echo.
"C:\Users\zivfe\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "C:\Users\zivfe\OneDrive\Documents\New project 2\viral-video-automation\MAKE_QUOTE_VIDEO_WITH_VOICE.py"
if errorlevel 1 (
  echo.
  echo Something failed. Send Codex the text in this window.
  echo.
  pause
  exit /b 1
)
echo.
echo If it worked, your video is here:
echo C:\Users\zivfe\OneDrive\Documents\New project 2\viral-video-automation\output\latest\video.mp4
echo.
pause
