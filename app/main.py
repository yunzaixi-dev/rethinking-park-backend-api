# Compatibility entry point for Docker
# This file imports the main app from the root directory
# until the full refactoring is complete

import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the main app from the root directory
from main import app

# Re-export the app for uvicorn
__all__ = ['app']