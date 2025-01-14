
# Ad-hoc Windows PowerShell script to invoke the graph microservice endpoints locally.
# Chris Joakim, Microsoft, 2025

Write-Host '---'
Write-Host 'GET /'
$url = "http://localhost:8001/"
$response = Invoke-RestMethod -Uri $url -Method Get
Write-Host $response

Write-Host '---'
Write-Host 'GET /ping'
$url = "http://localhost:8001/ping"
$response = Invoke-RestMethod -Uri $url -Method Get
Write-Host $response

Write-Host '---'
Write-Host 'GET /health'
$url = "http://localhost:8001/health"
$response = Invoke-RestMethod -Uri $url -Method Get
Write-Host $response

Write-Host '---'
Write-Host 'POST /sparql_query'
$url = "http://localhost:8001/sparql_query"
$data = @{
    sparql = "PREFIX c: <http://cosmosdb.com/caig#> SELECT ?used_lib WHERE { <http://cosmosdb.com/caig/pypi_flask> c:uses_lib ?used_lib . } LIMIT 10"
}  | ConvertTo-Json

$response = Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json" -Body $data
Write-Host $response
# Iterate over the response (assuming it's an array)
#foreach ($item in $response) {
#    Write-Host "item: $($item)"
#}

Write-Host '---'
Write-Host 'GET /health'
$url = "http://localhost:8001/health"
$response = Invoke-RestMethod -Uri $url -Method Get
Write-Host $response
