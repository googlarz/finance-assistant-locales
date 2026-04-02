import sys, os
# Add locales/ root to path so `from de import ...` and `from context import ...` work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
