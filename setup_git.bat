@echo off
REM Run this once from inside the PDF Converter folder (VS Code terminal).
REM It removes the partial .git left by the sync layer and links this folder
REM to the convertToPDF GitHub repo.

echo Removing any partial .git folder...
if exist .git rmdir /s /q .git

echo Initializing repo...
git init
git remote add origin https://github.com/muhammadmirza97/convertToPDF.git
git add .
git commit -m "Combine image-to-PDF and convertToPDF into one multi-format converter"
git branch -M main

echo.
echo Linked to: https://github.com/muhammadmirza97/convertToPDF.git
echo To publish, review the changes then run:  git push -u origin main
echo (add --force only if you intend to overwrite the existing repo contents)
pause
