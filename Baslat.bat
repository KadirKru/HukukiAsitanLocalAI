@echo off
color 0B
echo =======================================================
echo         HUKUKI DANISMAN AI - BASLATMA EKRANI
echo =======================================================
echo.

echo [1/2] Arka Plan API Sunucusu (Backend) Baslatiliyor...
cd /d "%~dp0\backend"
start "Hukuki Danisman - API Sunucusu" cmd /k "venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo [2/2] Gorsel Arayuz (Frontend) Baslatiliyor...
cd /d "%~dp0\frontend\LegalAdvisorWPF\LegalAdvisorWPF"
start "Hukuki Danisman - Arayuz" cmd /c "dotnet run"

echo.
echo Uygulama basariyla acildi! 
echo.
echo -------------------------------------------------------
echo ONEMLI NOT (Cevrimdisi Model Icin):
echo Eger uygulamada "Ollama Llama3 (Local)" kullanacaksaniz,
echo baslat menusunden ayrica "Ollama"yi acmayi unutmayin.
echo -------------------------------------------------------
echo.
pause
