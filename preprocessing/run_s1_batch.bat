@echo off
setlocal enabledelayedexpansion

:: 1. Force the terminal window to switch to E: Drive
E:

:: 2. CORRECTED SNAP PATH (Matching your exact folder name and executable type)
set GPT="C:\Program Files\esa-snap\bin\gpt"

:: 3. Your E: drive workspace folders
set GRAPH="E:\sagar-sakshi\preprocessing\s1_grd_workflow.xml"
set INPUT_DIR="E:\sagar-sakshi\data\01_raw_zip\S1A_IW_GRDH_1SDV_20250727T004109_20250727T004134_060262_077D37_F7F7.zip"
set OUTPUT_DIR="E:\sagar-sakshi\data\02_processed_tiff"

echo ==============================================
echo       SAGAR-SAKSHI: PREPROCESSING
echo ==============================================

:: Double check if input directory is visible on D:
if not exist %INPUT_DIR% (
    echo ❌ ERROR: Cannot find the input directory on D-Drive!
    pause
    exit
)

:: Loop through the zip file on D: drive
for %%f in (%INPUT_DIR%\*.zip) do (
    echo.
    echo 🚀 Found scene: %%~nf
    echo Running Orbit Correction, Calibration, Speckle Filter, and Terrain Correction...
    
    %GPT% %GRAPH% -Pinput="%%f" -Poutput="%OUTPUT_DIR%\%%~nf_Processed.tif"
)

echo.
echo ==============================================
echo Preprocessing Complete! Check E:\sagar-sakshi\data\02_processed_tiff
echo ==============================================
pause