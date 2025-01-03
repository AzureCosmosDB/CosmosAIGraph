#!/bin/bash

# Linux/macOS bash script to start the graph microservice as a java process.
# Chris Joakim, Microsoft, 2025

rm tmp/*.*

./gradlew bootRun
