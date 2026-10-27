@echo off
cd /d "%~dp0"
set "ALUNDRA_PY=C:\Users\Comp\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"
if exist "%ALUNDRA_PY%" (
 start "" "%ALUNDRA_PY%" -B tools/editor_launcher.py
) else (
 start "" pyw -3 -B tools/editor_launcher.py
)
