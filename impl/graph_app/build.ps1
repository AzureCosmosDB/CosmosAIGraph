
# Windows PowerShell build script for the graph microservice.
# Compiles and packages the Java code with the Gradle build tool.
# Chris Joakim, Microsoft, 2025

$tmp_dir = ".\tmp\"
if (-not(Test-Path $tmp_dir -PathType Container)) {
    Write-Host 'creating the tmp directory ...'
    New-Item -path $tmp_dir -ItemType Directory
}

Write-Host 'clean ...'
gradle clean

Write-Host 'build ...'
gradle build -x test

Write-Host 'jar ...'
gradle jar

# Write-Host 'dependencies ...'
# gradle dependencies > tmp\gradle_dependencies.txt

Write-Host 'done'
