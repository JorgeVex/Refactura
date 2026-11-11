@echo off
chcp 65001 > nul
title Compilando Refactura
cd /d "%~dp0"

echo ============================================
echo   Refactura - generando el ejecutable
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creando entorno virtual .venv ...
    python -m venv .venv || goto :error
) else (
    echo [1/3] Entorno virtual .venv encontrado
)

echo [2/3] Instalando dependencias ...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt -q || goto :error

echo [3/3] Compilando con PyInstaller (puede tardar 1-3 minutos) ...
".venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm Refactura.spec || goto :error

echo.
echo ============================================
echo   Listo: dist\Refactura.exe
echo ============================================
explorer dist
pause
exit /b 0

:error
echo.
echo *** Ocurrio un error. Revisa los mensajes de arriba. ***
pause
exit /b 1
