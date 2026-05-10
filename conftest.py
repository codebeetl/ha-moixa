"""Root conftest - ensure our custom_components package is importable.

HA's loader calls `import custom_components` during test setup and caches the
result.  Importing it here first (with the project root on sys.path) makes the
moixa integration discoverable before HA's internal stub can be registered.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import custom_components  # noqa: E402, F401
