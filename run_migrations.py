#!/usr/bin/env python
"""Run database migrations before starting the app."""
import os
import sys

# Set the Flask app for migrations
os.environ['FLASK_APP'] = 'pkg'

print("=" * 50)
print("Running database migrations...")
print("=" * 50)

try:
    from flask_migrate import upgrade
    from pkg import app, db
    
    with app.app_context():
        # Run the upgrade
        upgrade()
        print("✓ Migrations completed successfully!")
        print("=" * 50)
except Exception as e:
    print(f"✗ Migration failed: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
