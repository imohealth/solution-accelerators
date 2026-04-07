#!/bin/bash

# Ambient AI Solution Launcher
echo "=========================================="
echo "  Ambient AI Solution Launcher"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    echo "Visit: https://www.python.org/downloads/"
    exit 1
fi

# Get Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        echo "Run 'pip install -r requirements.txt' manually to see errors"
        exit 1
    fi
    echo "✓ Dependencies installed"
else
    echo "⚠️  requirements.txt not found. Installing basic dependencies..."
    pip install flask boto3 requests > /dev/null 2>&1
fi

echo ""
echo "=========================================="
echo "🚀 Starting Ambient AI Solution..."
echo "=========================================="
echo ""
echo "The application will open in your browser at:"
echo "👉 http://127.0.0.1:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the Flask app
python app.py
