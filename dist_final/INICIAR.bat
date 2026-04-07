@echo off
title Cafeteria Grao - PDV

cd /d "%~dp0"

echo Iniciando sistema...

start "" "CafePDV.exe"

timeout /t 5 >nul

start "" "%~dp0frontend\index.html"

exit