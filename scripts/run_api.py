import subprocess
import sys
import os
from pathlib import Path

def main():
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Ensure src is in python path
    env = os.environ.copy()
    src_path = str(project_root / "src")
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = src_path

    print("Starting Pricing Tool API (FastAPI)...")
    try:
        # Run uvicorn
        # src.pricing_tool.api.main:app
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "pricing_tool.api.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], env=env)
    except KeyboardInterrupt:
        print("\nAPI stopped.")

if __name__ == "__main__":
    main()
