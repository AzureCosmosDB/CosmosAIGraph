#!/bin/bash

# Bash script to start the graph microservice as a java process.
# Chris Joakim, Microsoft, 2025

mkdir -p tmp
rm tmp/*.*

./gradlew bootRun
