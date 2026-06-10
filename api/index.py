import os
import sys

# Add parent directory (project root) to sys.path so Flask can find local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
