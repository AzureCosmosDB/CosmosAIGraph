#!/bin/bash

# Bash build script for the graph microservice.
# Compiles and packages the Java code with the Gradle build tool.
# Chris Joakim, Microsoft, 2025

mkdir -p tmp

echo 'clean ...'
gradle clean

echo 'build ...'
gradle build -x test

echo 'jar ...'
gradle jar

# echo 'dependencies ...'
# gradle dependencies > tmp/gradle_dependencies.txt

echo 'done'
