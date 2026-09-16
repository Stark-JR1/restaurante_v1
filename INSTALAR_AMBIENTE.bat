@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "ROOT=%~dp0"
pushd "%ROOT%" >nul 2>&1
if errorlevel 1 exit /b 1

echo ==============================================
echo  SISTERMI - Preparar ambiente do Restaurante
echo ==============================================
echo.

if exist "%ROOT%venv\Scripts\python.exe" goto instalar

where py >nul 2>&1
if not errorlevel 1 (
    py -3.12 -m venv "%ROOT%venv" 2>nul
    if not exist "%ROOT%venv\Scripts\python.exe" py -m venv "%ROOT%venv"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo ERRO: Python nao encontrado.
        echo Instale Python 3.12+ e habilite o PATH.
        echo.
        pause
        exit /b 1
    )
    python -m venv "%ROOT%venv"
)

if not exist "%ROOT%venv\Scripts\python.exe" (
    echo ERRO: nao foi possivel criar o ambiente virtual.
    pause
    exit /b 1
)

:instalar
echo Atualizando pip...
"%ROOT%venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto erro

echo Instalando dependencias...
"%ROOT%venv\Scripts\python.exe" -m pip install -r "%ROOT%requirements.txt"
if errorlevel 1 goto erro

echo.
echo Ambiente preparado com sucesso.
echo Agora execute EXECUTAR_RESTAURANTE.bat
echo.
popd
pause
exit /b 0

:erro
echo.
echo ERRO durante a preparacao do ambiente.
popd
pause
exit /b 1
