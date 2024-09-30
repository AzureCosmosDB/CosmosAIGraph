#!/bin/bash

# This script reformats the python codebase per the formatting rules defined
# in the 'black' library.
# Chris Joakim, Microsoft

black *.py
black src 
