#!/bin/bash
# Script to properly reinstall dia2 package

echo "Uninstalling incomplete dia2 package..."
pip uninstall dia2 -y

echo "Reinstalling dia2 from GitHub (this may take a few minutes)..."
pip install --no-cache-dir git+https://github.com/nari-labs/dia2.git

echo "Verifying installation..."
python -c "from dia2 import Dia2, GenerationConfig, SamplingConfig; print('✅ dia2 installed successfully!')"

echo "Done!"
