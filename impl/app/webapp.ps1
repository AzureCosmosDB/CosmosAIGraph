# Start the web app, running within the hypercorn server.
# Entry point is webapp.py, 'app' is the FastAPI object.
# hypercorn enables restarting the app as the Python code changes.
# Chris Joakim, Microsoft

New-Item -ItemType Directory -Force -Path .\tmp | out-null

echo 'activating the venv ...'
.\venv\Scripts\Activate.ps1

echo '.env file contents ...'
cat .env 

hypercorn webapp:app --bind 127.0.0.1:8000 --workers 1 