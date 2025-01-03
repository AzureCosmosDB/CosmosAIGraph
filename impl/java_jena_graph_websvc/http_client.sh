#!/bin/bash

# Ad-hoc Linux/macOS bash script to invoke the graph microservice endpoints locally.
# Chris Joakim, Microsoft, 2025


echo '---'
echo 'GET /'
curl http://localhost:8001/

echo '---'
echo 'GET /ping'
curl http://localhost:8001/ping

echo '---'
echo 'GET /health'
curl http://localhost:8001/health

echo '---'
echo 'POST /sparql_query'
curl --header "Content-Type: application/json" \
     --request POST \
     --data '{"sparql":"SELECT (COUNT(?s) AS ?triples) WHERE { ?s ?p ?o }"}' \
     http://localhost:8001/sparql_query

echo '---'
echo 'GET /health'
curl http://localhost:8001/health
