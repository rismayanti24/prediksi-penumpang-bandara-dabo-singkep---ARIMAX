@echo off
title Dashboard Bandara Dabo Singkep
echo ========================================================
echo   Menjalankan Server Web Dashboard Bandara Dabo Singkep
echo ========================================================
echo.
echo Membuka browser di http://localhost:5000 ...
timeout /t 2 /nobreak >nul
start http://localhost:5000
echo.
echo Server aktif! Jangan tutup jendela hitam ini selama membuka web.
echo Untuk mematikan server, cukup tutup jendela ini.
echo.
python app.py
pause
