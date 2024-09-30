# Start the web service, running within the hypercorn server.
# Entry point is websvc.py, 'app' is the FastAPI object.
# Chris Joakim, Microsoft

New-Item -ItemType Directory -Force -Path .\tmp     | out-null

echo 'activating the venv ...'
.\venv\Scripts\Activate.ps1

echo '.env file contents ...'
cat .env 

echo 'starting the web service...'
hypercorn websvc:app --bind 127.0.0.1:8001
