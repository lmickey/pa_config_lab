@echo off
REM Run the GUI application with virtual environment (Windows)

REM Get the directory where this script is located
cd /d "%~dp0"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the GUI
python pa_config_gui.py

REM Deactivate virtual environment when done
deactivate
