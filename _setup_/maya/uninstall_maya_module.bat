
:: mocap_browser is determined by the current folder name
for %%I in (.) do set mocap_browser=%%~nxI

:: Check if modules folder exists
if not exist %UserProfile%\Documents\maya\modules mkdir %UserProfile%\Documents\maya\modules

:: Delete .mod file if it already exists
del %UserProfile%\Documents\maya\modules\%mocap_browser%.mod

:: end print 
echo .mod file removed from %UserProfile%\Documents\maya\modules\%mocap_browser%.mod



