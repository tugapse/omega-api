#!/bin/env bash

# get current script folder
FOLDER=$(dirname -- "$(realpath -- "$0" )" )
VENV_FOLDER="$FOLDER/.venv"


if [ ! -d "$VENV_FOLDER" ]; then
    echo -e "Creating virtual environment"
    python3 -m venv "$VENV_FOLDER"
fi

# activate virtual environment
echo -e "Activating virtual environment"
source $VENV_FOLDER/bin/activate    

echo -e "Installing dependencies"
if python3 -m pip install --upgrade pip > /dev/null 2>&1 && \
   python3 -m pip install -r requirements.txt; then
    echo -e "${GREEN}✔${NC} System dependencies synchronized."
else
    echo -e "${BOLD}${CYAN}✖${NC} Synchronization failed. Check logic manually."
    deactivate
    exit 1
fi