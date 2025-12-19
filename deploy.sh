#!/bin/bash

set -e

echo "Starting deployment..."

ensure_uv() {
    if ! command -v uv &> /dev/null; then
        echo "uv not found. Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        
        if [ -f "$HOME/.cargo/env" ]; then
            source "$HOME/.cargo/env"
        elif [ -f "$HOME/.local/bin/env" ]; then
            source "$HOME/.local/bin/env"
        elif [ -f "$HOME/snap/code/current/.local/bin/env" ]; then
             source "$HOME/snap/code/current/.local/bin/env"
        else
            export PATH="$HOME/.local/bin:$HOME/snap/code/current/.local/bin:$PATH"
        fi
    fi
}

if ! python3 -m venv .venv > /dev/null 2>&1; then
    echo "Standard 'python3 -m venv' failed (likely missing python3-venv)."
    echo "Switching to 'uv' as recommended by hackathon rules..."
    
    ensure_uv
    
    echo "Creating virtual environment with uv..."
    uv venv .venv
else
    echo "Virtual environment created with standard python3 venv."
fi

source .venv/bin/activate

echo "Installing dependencies..."
if command -v uv &> /dev/null; then
    echo "Using uv for fast installation..."
    uv pip install -r requirements.txt
else
    pip install --upgrade pip
    pip install -r requirements.txt
fi

echo "Starting server on port 8080..."
nohup uvicorn src.main:app --host 0.0.0.0 --port 8080 > server.log 2>&1 &

echo "Deployment complete. Server running in background with PID $!"
