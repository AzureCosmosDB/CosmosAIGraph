#!/bin/bash

# This script executes the complete set of unit tests
# for the app_common package, with code coverage.
# Note: The Graph microservice should be running on localhost
# when these tests are executed.
# Chris Joakim, Microsoft

mkdir -p tmp

rm tmp/*.*

source bin/activate

echo 'executing unit tests with code coverage ...'
pytest -v --cov=src/ --cov-report html tests/
