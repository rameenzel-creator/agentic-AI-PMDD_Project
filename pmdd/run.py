"""PMDD — Start the application server"""
import os
import sys
import subprocess

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"
    ])
