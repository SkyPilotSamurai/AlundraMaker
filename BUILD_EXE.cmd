@echo off
cd /d "%~dp0"
if not exist Output mkdir Output
py -3 -m pip install --quiet pyinstaller pillow numpy
py -3 -m PyInstaller --noconfirm --onedir --windowed --name "Alundra Maker" --icon "%~dp0tools\editor_icon.ico" --add-data "%~dp0tools\editor_icon.ico;." --collect-submodules PIL --hidden-import numpy --hidden-import tkinter --hidden-import tkinter.ttk --hidden-import tkinter.filedialog --hidden-import tkinter.messagebox --hidden-import tkinter.simpledialog --hidden-import tkinter.colorchooser --hidden-import tkinter.font --hidden-import winsound --hidden-import wave --hidden-import csv --hidden-import uuid --hidden-import zipfile --hidden-import unittest --distpath build\dist --workpath build\work --specpath build tools\exe_launcher.py
if not exist "build\dist\Alundra Maker\Alundra Maker.exe" (echo Build failed.& pause & exit /b 1)
if exist "Output\AlundraMaker" rmdir /s /q "Output\AlundraMaker"
mkdir "Output\AlundraMaker"
xcopy /e /i /q "build\dist\Alundra Maker" "Output\AlundraMaker\Alundra Maker" >nul
xcopy /e /i /q tools "Output\AlundraMaker\tools" >nul
xcopy /e /i /q data "Output\AlundraMaker\data" >nul
xcopy /e /i /q extras "Output\AlundraMaker\extras" >nul
xcopy /e /i /q Randomizer "Output\AlundraMaker\Randomizer" >nul
if exist "Output\AlundraMaker\tools\__pycache__" rmdir /s /q "Output\AlundraMaker\tools\__pycache__"
if exist Output\AlundraMaker.zip del Output\AlundraMaker.zip
powershell -NoProfile -Command "Compress-Archive -Path 'Output\AlundraMaker\*' -DestinationPath 'Output\AlundraMaker.zip'"
echo Done: Output\AlundraMaker.zip
pause
