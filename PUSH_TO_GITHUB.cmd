@echo off
cd /d "%~dp0"
if not exist .git (
  git init -b main
  git remote add origin https://github.com/SkyPilotSamurai/AlundraMaker.git
)
git add -A
git commit -m "Alundra Maker"
rem Replaces the history on GitHub with this folder (the old repository contents are dropped).
git push --force -u origin main
pause
