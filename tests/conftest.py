import sys
import os
import pytest

# Add lib directory to sys.path
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if libdir not in sys.path:
    sys.path.append(libdir)

from lib.cardlib import Card
