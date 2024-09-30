#!/bin/bash

# Start the web service, running within the hypercorn server.
# Entry point is websvc.py, 'app' is the FastAPI object.
# Chris Joakim, Microsoft

mkdir -p tmp

hypercorn webapp:app --bind 127.0.0.1:8000
