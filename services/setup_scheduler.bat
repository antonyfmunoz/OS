@echo off
echo Setting up OS overnight scrape...
schtasks /create /tn "OS_Overnight" /tr "python \"C:\Users\antonys beast pc\dev\OS\13_Scripts\overnight_scrape.py\"" /sc daily /st 02:00 /f
echo.
echo Done. Overnight scrape scheduled for 2:00 AM daily.
pause
