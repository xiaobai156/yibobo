@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "PERIODS="
set /p "PERIODS=Input periods, example 187 188 189 190: "
if "%PERIODS%"=="" (
  echo Periods are empty.
  pause
  exit /b 1
)

set "UNIQUE_PERIODS="
for %%P in (%PERIODS%) do (
  set "INVALID_PERIOD="
  for /f "delims=0123456789" %%A in ("%%P") do set "INVALID_PERIOD=%%A"
  if defined INVALID_PERIOD (
    echo Invalid period: %%P
    pause
    exit /b 1
  )
  set "SEEN="
  for %%Q in (!UNIQUE_PERIODS!) do if "%%Q"=="%%P" set "SEEN=1"
  if not defined SEEN set "UNIQUE_PERIODS=!UNIQUE_PERIODS! %%P"
)
set "PERIODS=!UNIQUE_PERIODS:~1!"
set "SUCCESS_DIR=%~dp0..\七类数据统一归纳"
set "FAILURE_DIR=%~dp0..\七类数据统一归纳失败"
set "BATCH_FAILED=0"

for %%P in (%PERIODS%) do (
  echo.
  echo ===== Start %%P =====
  set "SUCCESS_FILE=!SUCCESS_DIR!\%%P期-一波.txt"
  set "FAILURE_FILE=!FAILURE_DIR!\%%P期-杀一波-失败.txt"
  if exist "!SUCCESS_FILE!" del /q "!SUCCESS_FILE!"
  if exist "!FAILURE_FILE!" del /q "!FAILURE_FILE!"
  if exist "!SUCCESS_FILE!" (
    echo Could not remove stale reports for period %%P. Summary cancelled.
    set "BATCH_FAILED=1"
    goto :after_crawl
  )
  if exist "!FAILURE_FILE!" (
    echo Could not remove stale reports for period %%P. Summary cancelled.
    set "BATCH_FAILED=1"
    goto :after_crawl
  )
  py -3.10 -X utf8 "%~dp0sha_yibo_crawler.py" --period %%P --workers 8 --no-cache-update --output-dir "!SUCCESS_DIR!" --failure-output-dir "!FAILURE_DIR!"
  set "CRAWL_EXIT=!ERRORLEVEL!"
  if not exist "!SUCCESS_FILE!" (
    echo Period %%P failed before producing a fresh success report. Summary cancelled.
    set "BATCH_FAILED=1"
    goto :after_crawl
  )
  if not "!CRAWL_EXIT!"=="0" if not exist "!FAILURE_FILE!" (
    echo Period %%P returned nonzero without a failure report. Summary cancelled.
    set "BATCH_FAILED=1"
    goto :after_crawl
  )
  if "!CRAWL_EXIT!"=="0" (
    echo Period %%P finished with no site failures.
  ) else (
    echo Period %%P finished with failures. Continue multi-period mode.
  )
)

:after_crawl
if "!BATCH_FAILED!"=="1" (
  pause
  exit /b 1
)

echo.
echo ===== Multi-period all-failed summary =====
py -3.10 -X utf8 "%~dp0summarize_multi_period_failures.py" %PERIODS% --output-dir "!SUCCESS_DIR!" --failure-output-dir "!FAILURE_DIR!"
if errorlevel 1 (
  echo Failed to generate multi-period summary.
  pause
  exit /b 1
)

echo.
echo Finished. recent_10_cache.json was not refreshed by this multi-period mode.
pause
