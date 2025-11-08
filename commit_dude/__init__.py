import sys, pathlib
# Ensure project root is on sys.path when running with uv
root = pathlib.Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
