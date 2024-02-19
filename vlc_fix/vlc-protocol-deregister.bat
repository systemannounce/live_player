@echo off
:: 检查权限
net file 1>NUL 2>NUL || powershell Start-Process -FilePath cmd.exe -ArgumentList """/c pushd %~dp0 && %~s0 %*""" -Verb RunAs && exit
pause
@echo.
echo If you see "ERROR: Access is denied." then you need to right click and use "Run as Administrator".
@echo.
echo Removing vlc:// association...

reg delete HKCR\vlc /f

@echo.
pause
