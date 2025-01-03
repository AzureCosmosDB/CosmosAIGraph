#!/bin/bash

# Linux/macOS bash build script for this application.
# Chris Joakim, Microsoft, 2025

gradle clean

gradle build -x test

gradle jar

gradle dependencies > tmp/gradle_dependencies.txt
