#!/usr/bin/env python
"""
Run the Streamlit pricing application.

Usage:
    python scripts/run_app.py
"""
import subprocess
import sys
from pathlib import Path


def main():
    # Get the UI module path
    project_root = Path(__file__).parent.parent
    ui_path = project_root / 'src' / 'pricing_tool' / 'ui' / 'app_streamlit.py'
    
    if not ui_path.exists():
        print(f"ERROR: UI module not found at {ui_path}")
        sys.exit(1)
    
    # Run streamlit
    cmd = [sys.executable, '-m', 'streamlit', 'run', str(ui_path)]
    print(f"Starting Streamlit: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, cwd=str(project_root))
    except KeyboardInterrupt:
        print("\nApplication stopped.")


if __name__ == "__main__":
    main()
