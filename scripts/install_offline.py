"""Create a new project venv using the provided Python. No downloads or dependencies."""
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
def main():
    if sys.version_info<(3,10):raise SystemExit('Python 3.10+ with Tk is required.')
    try:import tkinter
    except ImportError:raise SystemExit('Tk is missing. Obtain Python/Tk through your approved installer.')
    target=ROOT/'.venv'
    if os.path.lexists(target):raise SystemExit('Existing .venv is preserved. Use a new extracted folder.')
    target.mkdir()
    result=subprocess.run([sys.executable,'-m','venv',str(target)],cwd=ROOT)
    if result.returncode:raise SystemExit('venv creation failed. Partial environment retained; no online fallback.')
    print('Offline environment ready. Zero third-party packages to download. Next: test.bat, then start-app.bat.')
    return 0
if __name__=='__main__':raise SystemExit(main())
