@echo off
REM Nightly prep - refreshes the ats-autopilot review queue so it's full each morning.
REM Runs prep (DRY-RUN: discovers + prepares only, never submits) and appends to logs\prep.log.
REM Edit BOARDS to change where it hunts. Prefix non-Greenhouse boards with the ATS name + colon
REM (e.g. ashby:ramp). A bare token is treated as Greenhouse.
setlocal
cd /d "%~dp0.."
if not exist logs mkdir logs

set "BOARDS=coinbase,gemini,ripple,consensys,brex,ashby:ramp,ashby:opensea,ashby:watershed"
set "LIMIT=20"

>>logs\prep.log echo.
>>logs\prep.log echo ==================================================
>>logs\prep.log echo Nightly prep %DATE% %TIME%
python -m ats_autopilot.cli prep --boards "%BOARDS%" --limit %LIMIT% >>logs\prep.log 2>&1
>>logs\prep.log echo Review the queue with: ats-autopilot queue
endlocal
