@echo off
rem Builds the "Alundra Maker" folder: Alundra Maker.exe plus everything it
rem needs to run (Python, Tk, Pillow, numpy) in its _internal folder. Run once.
cd /d "%~dp0"
set "PY=C:\Users\Comp\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%PY%" set "PY=py -3"
%PY% -m pip install --quiet pyinstaller
%PY% -m PyInstaller --noconfirm --onedir --windowed --name "Alundra Maker" --icon "%~dp0tools\editor_icon.ico" --add-data "%~dp0tools\editor_icon.ico;." --collect-submodules PIL  --hidden-import PIL --hidden-import argparse --hidden-import base64 --hidden-import bisect --hidden-import collections --hidden-import colorsys --hidden-import contextlib --hidden-import copy --hidden-import csv --hidden-import ctypes --hidden-import dataclasses --hidden-import datetime --hidden-import decimal --hidden-import faulthandler --hidden-import functools --hidden-import glob --hidden-import hashlib --hidden-import html --hidden-import importlib --hidden-import io --hidden-import json --hidden-import math --hidden-import msvcrt --hidden-import numpy --hidden-import pathlib --hidden-import pickle --hidden-import queue --hidden-import re --hidden-import runpy --hidden-import shutil --hidden-import struct --hidden-import subprocess --hidden-import tempfile --hidden-import threading --hidden-import time --hidden-import tkinter --hidden-import tkinter.ttk --hidden-import tkinter.filedialog --hidden-import tkinter.messagebox --hidden-import tkinter.simpledialog --hidden-import tkinter.colorchooser --hidden-import tkinter.font --hidden-import traceback --hidden-import types --hidden-import typing --hidden-import unittest --hidden-import uuid --hidden-import wave --hidden-import winsound --hidden-import zipfile --hidden-import zlib --distpath build --workpath build\exe-work --specpath build\exe-work tools\exe_launcher.py
echo.
if exist "build\Alundra Maker\Alundra Maker.exe" (echo Done: "build\Alundra Maker\Alundra Maker.exe") else (echo Build failed - see above.)
pause
