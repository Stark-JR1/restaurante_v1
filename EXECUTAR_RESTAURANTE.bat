@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "ROOT=%~dp0"
pushd "%ROOT%" >nul 2>&1
if errorlevel 1 (
    echo Nao foi possivel acessar a pasta do projeto:
    echo %ROOT%
    echo.
    pause
    exit /b 1
)

title SISTERMI - Auditoria de Refeicoes

echo ==============================================
echo  SISTERMI - Auditoria de Refeicoes
echo ==============================================
echo.

set "PYTHON=%ROOT%venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Ambiente virtual nao encontrado:
    echo %PYTHON%
    echo.
    echo Abra o projeto no caminho correto ou reinstale as dependencias.
    echo.
    popd
    pause
    exit /b 1
)

echo Pasta do projeto:
echo %ROOT%
echo.
echo Iniciando sistema em: http://127.0.0.1:8000
echo Para encerrar, pressione CTRL+C nesta janela.
echo.

start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; Start-Process 'http://127.0.0.1:8000'"

"%PYTHON%" -B "%ROOT%main.py"

echo.
echo Sistema encerrado.
popd
pause
