#!/bin/env bash

# close on any command fail
set -e  

# get current script folder
FOLDER=$(dirname -- "$(realpath -- "$0" )" )
VENV_FOLDER="$FOLDER/.venv"


if [ ! -d "$VENV_FOLDER" ]; then
    echo -e "Environment not ready. Run build.sh first."
    exit 1
fi

source $VENV_FOLDER/bin/activate 
python3 $FOLDER/main.py
deactivate
exit 0