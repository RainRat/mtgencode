import sys
import os

# Add both project root and lib directory to sys.path
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
libdir = os.path.join(rootdir, 'lib')
if rootdir not in sys.path:
    sys.path.append(rootdir)
if libdir not in sys.path:
    sys.path.append(libdir)

