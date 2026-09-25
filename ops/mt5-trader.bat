@echo off
rem Thin wrapper the MT5Trader scheduled task / Startup folder runs.
rem All the logic is in run_bot.ps1 (start terminal with Algo Trading on, restart-loop the bot).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_bot.ps1"
