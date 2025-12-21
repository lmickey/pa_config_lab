#!/usr/bin/env python3
"""
Launch script for Prisma Access Configuration Manager GUI.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import main

if __name__ == "__main__":
    main()
