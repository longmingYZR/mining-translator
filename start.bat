@echo off
chcp 65001 > nul
title Mining Translator

cd /d "%~dp0"
set PYTHON=C:\Users\28307\AppData\Local\Python\pythoncore-3.14-64\python.exe

echo Starting Mining Translator GUI...
echo Browser: http://127.0.0.1:7860
echo Close this window to stop.
echo.

"%PYTHON%" -m mining_translator.gui
pause
