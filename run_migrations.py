#!/usr/bin/env python
"""Run database migrations before starting the app."""
import subprocess
import sys

print("Running database migrations...")
result = subprocess.run(["flask", "db", "upgrade"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)
if result.returncode != 0:
    print(f"Migration failed with code {result.returncode}", file=sys.stderr)
    sys.exit(result.returncode)
print("Migrations complete!")
