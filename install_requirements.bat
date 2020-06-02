@ECHO OFF

CD /D "%~dp0"

python -m pip install -U pip
python -m pip install -U wheel
python -m pip install -U -r requirements.txt

PUSHD bin

REM extract bundled binaries
7-zip\7za.exe x -aoa chromium.7z
7-zip\7za.exe x -aoa tesseract-ocr.7z

POPD

PAUSE
