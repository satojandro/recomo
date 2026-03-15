#!/usr/bin/env python3
"""
Run ReCoMo demo from project root without installing.

Usage: python run_demo.py [synthetic|real|path/to/trace.json]
"""

import os
import sys

# So that "recomo" (this directory) is found when run from project root
_root = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.dirname(_root)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from recomo.demo.run_demo import main

if __name__ == "__main__":
    main()
