@echo off
setlocal
pushd "%~dp0\.."
if not exist "dist" mkdir dist
call .\venv\Scripts\python.exe ".\scripts\context_pack.py"
popd
endlocal
