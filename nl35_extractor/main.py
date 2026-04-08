"""
main.py — NL-35 extraction entry point.
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline import main

if __name__ == "__main__":
    main()
