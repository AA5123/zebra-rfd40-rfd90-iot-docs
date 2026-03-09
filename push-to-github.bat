@echo off
setlocal

REM Automated script to rebuild docs and push changes to GitHub

REM Move to repository root (folder where this .bat file lives)
cd /d "%~dp0"

echo [1/5] Generating OpenAPI spec from schemas...
python scripts\generate_openapi.py
if errorlevel 1 (
    echo OpenAPI generation failed. Push stopped.
    exit /b 1
)

echo [2/6] Rebuilding documentation pages...
python scripts\build_pages.py
if errorlevel 1 (
    echo Build failed. Push stopped.
    exit /b 1
)

REM Initialize git if not already a repo
if not exist ".git" (
    git init
)

echo [3/6] Staging files...
REM Add all files
git add .

git diff --cached --quiet
if %errorlevel%==0 (
    echo No changes to commit after rebuild.
    exit /b 0
)

echo [4/6] Creating commit...
REM Commit changes
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""') do set "TS=%%i"
set "COMMIT_MSG=Automated update %TS%"
git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
    echo Commit failed. Push stopped.
    exit /b 1
)

echo [5/6] Ensuring main branch...
REM Set main branch
git branch -M main

REM Add remote (ignore error if already exists)
git remote add origin https://github.com/AA5123/zebra-rfd40-rfd90-iot-docs.git 2>nul

echo [6/6] Pushing to GitHub...
REM Push to GitHub
git push -u origin main
if errorlevel 1 (
    echo Push failed.
    exit /b 1
)

echo Push completed successfully.
echo GitHub Pages (after workflow completes): https://aa5123.github.io/zebra-rfd40-rfd90-iot-docs/
