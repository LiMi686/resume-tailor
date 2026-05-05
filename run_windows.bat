@echo off
setlocal

cd /d %~dp0

set "VENV_DIR=.venv311"
set "PYTHON_LAUNCHER=py -3.11"

if not exist %VENV_DIR% (
    %PYTHON_LAUNCHER% -m venv %VENV_DIR%
    call %VENV_DIR%\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call %VENV_DIR%\Scripts\activate.bat
)

streamlit run app\main.py
