@echo off
chcp 65001 >nul
title 矿业翻译工具 Mining Translator

set "PYTHON_EXE=C:\Users\28307\AppData\Local\Python\pythoncore-3.14-64\python.exe"

cd /d "%~dp0"

echo 正在启动矿业翻译工具...
echo 浏览器将自动打开 http://127.0.0.1:7860
echo 关闭此窗口即可停止服务
echo.

"%PYTHON_EXE%" -m mining_translator.gui
pause
