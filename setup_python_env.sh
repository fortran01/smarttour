#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Created virtual environment"
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

echo "Python environment setup complete!"
echo "To activate the environment, run: source venv/bin/activate" 