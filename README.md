# LS Hospital

## What it is
A hospital management web app for patients, doctors, and admins. Patients can book appointments, doctors manage schedules and consultations, and admins manage departments and specialties.

## Problem it solves
Provides an end‑to‑end flow for hospital appointments and basic clinical/admin operations in one system.

## Tech stack
- Python + Flask
- Flask‑SQLAlchemy + Flask‑Migrate (Alembic)
- PostgreSQL
- HTML/CSS/Bootstrap + JavaScript
- Gunicorn (production)

## How to run (local)
1. Create a virtual environment and install dependencies.
2. Set environment variables (example):
   - `FLASK_APP=pkg`
   - `FLASK_ENV=development`
   - `DATABASE_URL=postgresql://...`
3. Run migrations and start the app:
   - `flask db upgrade`
   - `flask run`


## Commands used (high‑level)
- `git add <files>`
- `git commit -m "<message>"`
- `git push`
- `flask db upgrade`
