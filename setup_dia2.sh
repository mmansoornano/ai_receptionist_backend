#!/bin/bash
# Script to upgrade Python and install Dia2 TTS library

echo "Upgrading Python in conda environment 'backend' to 3.10+..."
conda install -n backend python=3.10 -y

echo "Installing Dia2 library..."
conda run -n backend pip install git+https://github.com/nari-labs/dia2.git

echo "Verifying installation..."
conda run -n backend python -c "from dia2 import Dia2; print('Dia2 installed successfully!')"

echo "Done! You can now use Dia2 TTS."
