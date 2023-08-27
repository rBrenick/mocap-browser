
:: mocap_finder is determined by the current folder name
for %%I in (.) do set mocap_finder=%%~nxI
SET CLEAN_mocap_finder=%mocap_finder:-=_%

:: Check if modules folder exists
if not exist %UserProfile%\Documents\maya\modules mkdir %UserProfile%\Documents\maya\modules

:: Delete .mod file if it already exists
if exist %UserProfile%\Documents\maya\modules\%mocap_finder%.mod del %UserProfile%\Documents\maya\modules\%mocap_finder%.mod

:: Create file with contents in users maya/modules folder
(echo|set /p=+ %mocap_finder% 1.0 %CD%\_setup_\maya & echo; & echo icons: ..\%CLEAN_mocap_finder%\icons)>%UserProfile%\Documents\maya\modules\%mocap_finder%.mod

:: end print
echo .mod file created at %UserProfile%\Documents\maya\modules\%mocap_finder%.mod



