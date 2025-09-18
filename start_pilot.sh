#!/bin/bash
# start_pilot.sh - Fixed for macOS
echo "🚀 Starting AI Cash Flow Assistant - Pilot Mode"

# Check if .env exists and has API key
if [ ! -f .env ]; then
    echo "❌ .env file not found! Please create it first."
    exit 1
fi

if ! grep -q "sk-ant-" .env; then
    echo "⚠️  WARNING: No Claude API key found in .env"
    echo "Please add your ANTHROPIC_API_KEY to .env file"
fi

# Detect Python command (macOS often uses python3)
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python not found! Please install Python 3.8+"
    exit 1
fi

echo "🐍 Using Python command: $PYTHON_CMD"

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment active: $VIRTUAL_ENV"
else
    echo "⚠️  No virtual environment detected"
    echo "💡 Consider running: python3 -m venv venv && source venv/bin/activate"
fi

# Check if app_pilot.py exists
if [ ! -f "src/app_pilot.py" ]; then
    echo "❌ src/app_pilot.py not found!"
    echo "💡 Running the deploy script creates this file. Did you run ./deploy_pilot.sh?"
    exit 1
fi

# Start the application
echo "📱 Starting mobile-optimized pilot app..."
echo "🌐 Will be available at: http://localhost:7860"
echo "📱 Mobile users can access via: http://YOUR_SERVER_IP:7860"
echo ""
echo "Press Ctrl+C to stop"

$PYTHON_CMD src/app_pilot.py