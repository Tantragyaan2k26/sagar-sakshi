import sys
import os
import subprocess
import glob

print(f"Current Python: {sys.executable}")
print(f"Python Version: {sys.version}")

# Search for Python installations
found_pythons = []
for p in glob.glob("C:/Users/*/AppData/Local/Programs/Python/*/python.exe") + \
         glob.glob("C:/Program Files/Python*/**/python.exe", recursive=True) + \
         glob.glob("C:/Python*/**/python.exe", recursive=True) + \
         glob.glob("C:/Users/*/AppData/Local/Python/**/python.exe", recursive=True):
    if os.path.exists(p) and p not in found_pythons:
        found_pythons.append(p)

print("\nInstalled Pythons found:")
for p in found_pythons:
    try:
        ver = subprocess.check_output([p, "--version"], text=True).strip()
        print(f"  {p} -> {ver}")
    except Exception as e:
        print(f"  {p} -> Error: {e}")
