@ECHO OFF

CD /D "%~dp0"

python -m pip install -U pip
python -m pip install -U -r requirements.txt

REM download Chromium browser
pyppeteer-install.exe

PAUSE
