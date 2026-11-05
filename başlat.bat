@echo off
title Luminar CS2 Modding Tool - Baslatici
color 0A

echo ===================================================
echo        LUMINAR CS2 MODDING TOOL BASLATILIYOR...
echo ===================================================
echo.

:: Scriptin calistigi dizine git
cd /d "%~dp0"

echo [1/3] Gerekli Python kutuphaneleri kontrol ediliyor ve yukleniyor...
echo Bu islem internet hiziniza bagli olarak biraz surebilir.
pip install -r requirements.txt
echo.

echo [2/3] FastAPI Sunucusu (Backend) yeni pencerede baslatiliyor...
cd backend
start "Luminar Backend Server" cmd /k "python -m uvicorn main:app --host 127.0.0.1 --port 8000"
cd ..
echo.

echo [3/3] Sunucunun hazir olmasi icin kisa bir sure bekleniyor...
timeout /t 3 /nobreak > NUL

echo Tarayici aciliyor...
start http://localhost:8000

echo.
echo ===================================================
echo ISLEM TAMAM! 
echo Luminar CS2 Modding Tool tarayicinizda acildi.
echo Arka planda acilan siyah "Luminar Backend Server" 
echo penceresini araci kullandiginiz surece KAPATMAYIN.
echo ===================================================
pause
