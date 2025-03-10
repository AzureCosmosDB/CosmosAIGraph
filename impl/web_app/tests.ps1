# This script executes the complete set of python code unit tests.
#
# Notes: 
# 1) The Graph microservice should be running on localhost
#    when these tests are executed.
# 2) These tests use the "live" services (CosmosDB, Azure OpenAI, etc)
#    rather than fixtures or mocks.
# 3) Code coverage is generated and is useful in identifying dead 
#    or untested code.
# 4) The pytest testing framework is used
# 5) The test scripts are in the tests\ directory.
# 6) The following annotation can be used to disable a test:
#    @pytest.mark.skip(reason="This test is currently disabled.")
# 7) Individual tests can also be executed from the command line.
#    See the comments atop each test script, such as:
#    pytest -v tests/test_config_service.py
#
# Chris Joakim, Microsoft, 2025

New-Item -ItemType Directory -Force -Path .\tmp | out-null
del tmp/*.*

echo 'executing unit tests with code coverage ...'
pytest -v --cov=src/ --cov-report html tests/
