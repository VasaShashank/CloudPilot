import sys
import os

# Ensure the cloudpilot root is on sys.path so 'backend' package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
