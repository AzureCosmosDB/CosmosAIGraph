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

# Load environment variables from .env file
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*?)\s*=\s*(.+?)\s*$') {
        $name = $matches[1]
        $value = $matches[2] -replace '^"' -replace '"$'
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}

# Get port from environment variable, default to 9008 if not set
$port = if ($env:CAIG_WEB_APP_PORT) { $env:CAIG_WEB_APP_PORT } else { "9008" }
Write-Host "Starting web app on port $port ..."

hypercorn web_app:app --bind "127.0.0.1:$port" --workers 1 