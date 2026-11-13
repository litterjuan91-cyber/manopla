@echo off
cd /d "%~dp0"
echo Instalando librerias...
py -3.13 -m pip install -r requirements.txt
echo.
echo Listo. Ahora abri iniciar.bat
pause
