@echo off
REM Automated script to push your project to your GitHub repository

REM Initialize git if not already a repo
if not exist ".git" (
    git init
)

REM Add all files
git add .

REM Commit changes
git commit -m "Automated commit" 

REM Set main branch
git branch -M main

REM Add remote (ignore error if already exists)
git remote add origin https://github.com/AA5123/zebra-rfd40-rfd90-iot-docs.git 2>nul

REM Push to GitHub
git push -u origin main
