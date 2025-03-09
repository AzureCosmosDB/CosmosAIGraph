# Start the web app, running within the hypercorn server.
# Entry point is web_app.py, 'app' is the FastAPI object.
# hypercorn enables restarting the app as the Python code changes.
# Chris Joakim, Microsoft, 2025

New-Item -ItemType Directory -Force -Path .\tmp | out-null

Write-Host 'deleting tmp\ files ...'
Remove-Item tmp\*.*

Write-Host 'activating the venv ...'
.\venv\Scripts\Activate.ps1

Write-Host '.env file contents ...'
Get-Content .env 

hypercorn web_app:app --bind 127.0.0.1:8000 --workers 1 