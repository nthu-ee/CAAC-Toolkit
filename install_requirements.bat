@echo OFF

cd /D "%~dp0"

python -m pip install -U pip wheel
python -m pip install -U -r requirements.txt

pushd bin

rem extract bundled binaries
7-zip\7za.exe x -aoa chromium.7z
7-zip\7za.exe x -aoa tesseract-ocr.7z

popd

pause
