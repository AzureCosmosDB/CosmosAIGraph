#!/bin/bash

# Start the web app, running within the hypercorn server.
# Entry point is web_app.py, 'app' is the FastAPI object.
# hypercorn enables restarting the app as the Python code changes.
# Chris Joakim, Microsoft, 2025

mkdir -p tmp

echo 'activating the venv ...'
source venv/bin/activate

echo '.env file contents ...'
cat .env 

hypercorn web_app:app --bind 127.0.0.1:8000 --workers 1 
