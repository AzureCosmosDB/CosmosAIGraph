#!/bin/bash

# Bash script to open a mongo shell CLI pointing one of several
# named environments - atlas, cosmos_ru, cosmos_vcore, localhost.
#
# Usage:
#   mongosh.sh <envname> <optional-commands-file>
#   mongosh.sh ru
#   mongosh.sh vcore
#   mongosh.sh localhost
#
# Chris Joakim, Microsoft, 2024

source
if [ "$1" == 'ru' ]
then 
    echo 'connecting to: '$AZURE_COSMOSDB_MONGODB_CONN_STRING
    mongosh $AZURE_COSMOSDB_MONGODB_CONN_STRING --ssl
fi

if [ "$1" == 'vcore' ]
then 
    echo 'connecting to: '$CAIG_AZURE_MONGO_VCORE_CONN_STR
    mongosh $CAIG_AZURE_MONGO_VCORE_CONN_STR --ssl
fi

if [ "$1" == 'localhost' ]
then 
    echo 'connecting to '$MONGODB_LOCAL_URL
    mongosh $MONGODB_LOCAL_URL
fi
