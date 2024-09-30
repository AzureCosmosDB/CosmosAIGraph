#!/bin/bash

# PowerShell script to open a mongo shell CLI pointing one of several
# named environments - ru, vcore, or localhost.
#
# Usage:
#   .\mongosh.ps1 <envname> <optional-commands-file>
#   .\mongosh.ps1 ru
#   .\mongosh.ps1 vcore
#   .\mongosh.ps1 localhost
#
# Chris Joakim, Microsoft, 2024

param(
    [Parameter()]
    [String]$env_name  = "xxx",
    [String]$commands_file = ""
)

Write-Output "using env_name '$env_name' and commands file '$commands_file'"

if ('ru' -eq $env_name) {
    if ("" -eq $commands_file) {
        mongosh $env:AZURE_COSMOSDB_MONGODB_CONN_STRING --ssl
    }
    else {
        mongosh $env:AZURE_COSMOSDB_MONGODB_CONN_STRING --ssl -f $commands_file
    } 
}
elseif ('vcore' -eq $env_name) {
    if ("" -eq $commands_file) {
        mongosh $env:CAIG_AZURE_MONGO_VCORE_CONN_STR --tls
    }
    else {
        mongosh $env:CAIG_AZURE_MONGO_VCORE_CONN_STR --tls -f $commands_file
    } 
}
elseif ('localhost' -eq $env_name) {
    if ("" -eq $commands_file) {
        mongosh $env:MONGODB_LOCAL_URL
    }
    else {
        mongosh $env:MONGODB_LOCAL_URL -f $commands_file
    } 
}
else {
    Write-Output "unknown env_name $env_name, terminating"
    Write-Output ""
    Write-Output "Usage:"
    Write-Output ".\mongosh.ps1 <env> <optional-commands-file> where env is atlas, cosmos_ru, cosmos_vcore, or localhost"
    Write-Output ".\mongosh.ps1 cosmos_ru"
    Write-Output ""
}
