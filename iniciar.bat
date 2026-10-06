@echo off
title Assistente Fran - Tutor de Frances com IA
echo ========================================================
echo   Iniciando o Assistente Fran (Tuteur de Francais)...
echo ========================================================
echo.
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe app.py
) else (
    echo [ERRO] Ambiente virtual nao encontrado na pasta venv!
    echo Execute: python -m venv venv e .\venv\Scripts\pip.exe install -r requirements.txt
    pause
)
