@ECHO OFF

CD /D "%~dp0"

python -m pip install -U -r requirements.txt

PAUSE
