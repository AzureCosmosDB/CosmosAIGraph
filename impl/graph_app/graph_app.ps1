
# Windows PowerShell script to start the graph microservice as a java process.
# Chris Joakim, Microsoft, 2025

# Remove-Item -Path tmp\*.* -Force

.\gradlew.bat bootRun
