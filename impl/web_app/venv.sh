#!/bin/bash

# Recreate the python virtual environment and reinstall libs on mac/linux.
# Note: This script works with 3.12.3 but not 3.13.x as of 1/3/2025.
# python3 --version -> Python 3.12.3
# Chris Joakim, Microsoft, 2025

# delete previous venv directory
mkdir -p venv 
rm -rf venv 

echo 'creating new python3 virtual environment in the venv directory ...'
python3 -m venv venv

echo 'activating new venv ...'
source venv/bin/activate

echo 'upgrading pip ...'
python -m pip install --upgrade pip 

echo 'install pip-tools ...'
pip install --upgrade pip-tools

echo 'displaying python location and version'
which python
python --version

echo 'displaying pip location and version'
which pip
pip --version

echo 'pip-compile requirements.in ...'
pip-compile --output-file requirements.txt requirements.in

echo 'pip install requirements.txt ...'
pip install -q -r requirements.txt

echo 'pip list ...'
pip list

echo 'done; next -> source venv/bin/activate'
