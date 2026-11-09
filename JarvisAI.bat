@echo off
setlocal

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "PYTHON=%ROOT_DIR%venv\Scripts\pythonw.exe"
if not exist "%PYTHON%" (
    echo [JarvisAI] No encontre el entorno virtual. Consulta README.md.
    pause
    exit /b 1
)

if not exist "%ROOT_DIR%JarvisAI.lnk" start "" /wait "%PYTHON%" "%ROOT_DIR%main.py" --create-shortcut
start "" "%PYTHON%" "%ROOT_DIR%main.py" --desktop --require-wake-word %*
