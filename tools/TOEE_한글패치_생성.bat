@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo  TOEE 한국어 패치 생성기
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
  echo [오류] Python을 찾을 수 없습니다.
  echo Python 3를 설치한 뒤 다시 실행하세요.
  pause
  exit /b 2
)

if not exist "data" (
  echo [오류] data 폴더가 없습니다.
  echo 이 BAT, toee_apply_korean_translation.py, 최종 XLSX를 TOEE 게임 루트에 놓으세요.
  pause
  exit /b 2
)
if not exist "modules\ToEE" (
  echo [오류] modules\ToEE 폴더가 없습니다.
  pause
  exit /b 2
)
if not exist "TOEE_Translation_FILTERED_v2.xlsx" (
  echo [오류] TOEE_Translation_FILTERED_v2.xlsx가 없습니다.
  pause
  exit /b 2
)

python -c "import openpyxl" >nul 2>nul
if errorlevel 1 (
  echo [정보] openpyxl 설치 중...
  python -m pip install openpyxl
  if errorlevel 1 (
    echo [오류] openpyxl 설치 실패
    pause
    exit /b 2
  )
)

python "%~dp0toee_apply_korean_translation.py" --xlsx "%~dp0TOEE_Translation_FILTERED_v2.xlsx" --game-root "%~dp0" --output "%~dp0TOEE_Korean_Patch_Output"
set ERR=%ERRORLEVEL%

echo.
if "%ERR%"=="0" (
  echo [완료] TOEE_Korean_Patch_Output 폴더를 확인하세요.
) else (
  echo [주의] 일부 항목이 보류되었습니다. PATCH_REPORT.json을 확인하세요.
)
pause
exit /b %ERR%
