# Render Deployment Guide - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Initial Setup](#initial-setup)
3. [Files Created/Modified](#files-createdmodified)
4. [Configuration Explanation](#configuration-explanation)
5. [Git Commands Used](#git-commands-used)
6. [Deployment Process](#deployment-process)
7. [Troubleshooting](#troubleshooting)
8. [Key Learnings](#key-learnings)

---

## Overview

**Project:** LShospital - Hospital Management System  
**Framework:** Flask (Python)  
**Deployment Platform:** Render  
**Database:** PostgreSQL (on Render)  
**Production Server:** Gunicorn  
**Version Control:** GitHub

### What is Render?
Render is a cloud platform similar to Heroku that allows you to deploy web applications. We used Render's free tier to deploy our Flask application.

---

## Initial Setup

### Step 1: Create GitHub Repository
Before deploying, the project was pushed to GitHub at: `https://github.com/johnadeboye50-spec/LShospital`

```bash
# Initialize git in your local project
git init

# Add all files to staging area
git add .

# Create initial commit
git commit -m "Initial commit"

# Add remote GitHub repository
git remote add origin https://github.com/yourusername/yourrepo.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 2: Connect GitHub to Render
1. Go to `https://render.com`
2. Sign up or login
3. Create new Web Service
4. Connect your GitHub account
5. Select the repository `LShospital`
6. Authorize Render to access your GitHub

---

## Files Created/Modified

### 1. **render.yaml** (Configuration File)
**Location:** Root directory of project  
**Purpose:** Tells Render how to build and run your application

#### Original Version:
```yaml
services:
  - type: web
    name: lshospital-app
    env: python
    plan: free
    runtime: python-3.11
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn --bind 0.0.0.0:$PORT pkg:app
    envVars:
      - key: RENDER
        value: "1"
      - key: SECRET_KEY
        generateValue: true
      - key: DATABASE_URL
        fromService:
          name: lshospital-db
          property: connectionString

  - type: pserv
    name: lshospital-db
    env: postgres
    plan: free
    ipAllowList: []
```

**Explanation of Each Section:**

```yaml
services:
  - type: web                    # This is a web service (your Flask app)
    name: lshospital-app         # Name of the service on Render
    env: python                  # Programming language
    plan: free                   # Free tier (limited resources)
    runtime: python-3.11         # Python version to use
```

**Build Command:**
```yaml
buildCommand: pip install -r requirements.txt
```
This runs when you deploy. It installs all Python packages listed in `requirements.txt`

**Start Command:**
```yaml
startCommand: gunicorn --bind 0.0.0.0:$PORT pkg:app
```
- `gunicorn` = Production web server (better than Flask's development server)
- `--bind 0.0.0.0:$PORT` = Listen on all network interfaces on Render's assigned port
- `pkg:app` = Run the Flask app object from the `pkg` package

**Environment Variables:**
```yaml
envVars:
  - key: RENDER
    value: "1"                   # Flag to tell app it's running on Render
  - key: SECRET_KEY
    generateValue: true          # Auto-generate a secret key for security
  - key: DATABASE_URL
    fromService:
      name: lshospital-db        # Get database URL from PostgreSQL service
      property: connectionString
```

**Database Service:**
```yaml
  - type: pserv                  # PostgreSQL service
    name: lshospital-db          # Name of database
    env: postgres                # PostgreSQL
    plan: free                   # Free tier
```

---

### 2. **.python-version** (Python Version Lock)
**Location:** Root directory  
**Purpose:** Forces Render to use a specific Python version

```
3.11.11
```

**Why?**
- Render defaults to Python 3.13
- `psycopg2` (PostgreSQL adapter) had compatibility issues with Python 3.13
- By specifying 3.11.11, Render uses Python 3.11 which is compatible

---

### 3. **pkg/config.py** (Database Configuration)
**Location:** Inside `pkg` folder  
**Purpose:** Configure database connection based on environment

#### Original Code:
```python
import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False

class DevelopmentConfig(Config):
    """Development configuration - uses MySQL locally"""
    SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://root:@localhost/hospital"
    DEBUG = True

class LiveConfig(Config):
    """Production configuration - uses PostgreSQL on Render"""
    uri = os.environ.get("DATABASE_URL", "sqlite:///local.db")
    
    # PostgreSQL connection string fix
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = uri
    DEBUG = False
```

**Explanation:**

- **DevelopmentConfig:** Uses MySQL locally (for your computer)
  - Connection: `mysql+mysqlconnector://root:@localhost/hospital`
  - This connects to MySQL running on your computer

- **LiveConfig:** Uses PostgreSQL on Render
  - Gets `DATABASE_URL` from environment variable set by Render
  - Replaces `postgres://` with `postgresql://` because newer versions of SQLAlchemy require `postgresql://`
  - Falls back to SQLite if DATABASE_URL is not found

---

### 4. **pkg/__init__.py** (Flask App Factory)
**Location:** Inside `pkg` folder  
**Purpose:** Create and configure Flask application

#### Key Changes Made:

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import os

# Initialize extensions
db = SQLAlchemy()
csrf = CSRFProtect()

def create_app():
    """Application factory function"""
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Determine configuration based on environment
    if os.environ.get("RENDER"):
        from .config import LiveConfig
        app.config.from_object(LiveConfig)
    else:
        from .config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    
    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    Migrate(app, db)
    
    # Register blueprints (routes)
    from . import admin_routes, doctor_route, patient_routes
    app.register_blueprint(admin_routes.admin_bp)
    app.register_blueprint(doctor_route.doctor_bp)
    app.register_blueprint(patient_routes.patient_bp)
    
    return app

app = create_app()
```

**Important Changes:**
- Template and static folder paths use `os.path.dirname(__file__)` instead of hardcoded paths
- Environment detection: If `RENDER` environment variable exists, use `LiveConfig`, otherwise use `DevelopmentConfig`
- This allows same code to work locally and on Render with different databases

---

### 5. **starter.py** (Local Development Entry Point)
**Location:** Root directory  
**Purpose:** Run Flask app locally during development

```python
import os
from pkg import app

if __name__ == '__main__':
    # Get PORT from environment variable, default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run on all network interfaces
    app.run(host='0.0.0.0', port=port, debug=False)
```

**Explanation:**
- `host='0.0.0.0'` = Listen on all network interfaces
- `port = int(os.environ.get('PORT', 5000))` = Use PORT env var if set, else 5000
- `debug=False` = Don't use debug mode in production-like environment

---

### 6. **requirements.txt** (Python Dependencies)
**Location:** Root directory  
**Purpose:** Lists all Python packages needed

```
blinker==1.9.0
click==8.3.0
colorama==0.4.6
dnspython==2.8.0
email-validator==2.3.0
Flask==3.1.2
Flask-WTF==1.2.2
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.4
gunicorn==21.2.0
idna==3.11
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.3
python-dotenv==1.2.1
Werkzeug==3.1.3
WTForms==3.2.1
mysql-connector-python==8.1.0
requests==2.32.3
psycopg2==2.9.9
```

**Important Packages:**

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.1.2 | Web framework |
| Flask-SQLAlchemy | 3.1.1 | Database ORM |
| Flask-Migrate | 4.0.4 | Database migrations |
| gunicorn | 21.2.0 | Production web server |
| psycopg2 | 2.9.9 | PostgreSQL driver (specifically 2.9.9 for Python 3.11 compatibility) |
| mysql-connector-python | 8.1.0 | MySQL driver (for local development) |

---

### 7. **Template Path Fixes** (patient_routes.py & doctor_route.py)
**Location:** `pkg/patient_routes.py` and `pkg/doctor_route.py`  
**Purpose:** Fix template references

#### Problem:
```python
# WRONG - causes TemplateNotFound error
return render_template('/user/home.html')  # Leading slash breaks it
```

#### Solution:
```python
# CORRECT - Render works with relative paths
return render_template('user/home.html')  # No leading slash
```

**Example Changes:**
```python
# In doctor_route.py
@doctor_bp.route('/doctor_dashboard', methods=['GET', 'POST'])
def doctor_dashboard():
    return render_template('doctors/doctor_dashboard.html')  # No leading slash

# In patient_routes.py
@patient_bp.route('/home', methods=['GET', 'POST'])
def patient_home():
    return render_template('user/home.html')  # No leading slash
```

**Total changes:** ~24 template paths fixed across both files

---

## Configuration Explanation

### Environment Detection Logic

```python
# In pkg/__init__.py
if os.environ.get("RENDER"):
    # Running on Render - use PostgreSQL
    from .config import LiveConfig
    app.config.from_object(LiveConfig)
else:
    # Running locally - use MySQL
    from .config import DevelopmentConfig
    app.config.from_object(DevelopmentConfig)
```

**How it works:**
1. Render automatically sets `RENDER=1` environment variable
2. Our code checks for this variable
3. If `RENDER` exists → Use `LiveConfig` (PostgreSQL)
4. If `RENDER` doesn't exist → Use `DevelopmentConfig` (MySQL)
5. Same code, different configurations!

### Database URL Conversion

```python
# In config.py
uri = os.environ.get("DATABASE_URL", "sqlite:///local.db")

if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

SQLALCHEMY_DATABASE_URI = uri
```

**Why?**
- Render sends DATABASE_URL with `postgres://` prefix
- SQLAlchemy 2.0+ requires `postgresql://` prefix
- We convert it: `postgres://user:pass@host/db` → `postgresql://user:pass@host/db`

---

## Git Commands Used

### Basic Git Workflow

#### 1. **First Time Setup**
```bash
# Initialize git in your project folder
git init

# Add GitHub as remote repository
git remote add origin https://github.com/yourusername/yourrepo.git

# Create initial commit
git add .
git commit -m "Initial commit"

# Push to GitHub
git branch -M main
git push -u origin main
```

**Explanation:**
- `git init` = Initialize git repository locally
- `git remote add origin URL` = Link to GitHub
- `git add .` = Stage all files for commit
- `git commit -m "message"` = Create a snapshot with a message
- `git push -u origin main` = Upload to GitHub (main branch)

#### 2. **Making Changes**
```bash
# See what files changed
git status

# Stage changed files
git add filename.py
# Or add everything
git add .

# Commit the changes
git commit -m "Descriptive message about what changed"

# Push to GitHub
git push
```

**Example:**
```bash
git add render.yaml
git commit -m "Add render.yaml configuration for deployment"
git push
```

#### 3. **Commands Used During This Project**

**Creating render.yaml:**
```bash
git add render.yaml
git commit -m "Add render.yaml for Render deployment"
git push
```

**Creating .python-version:**
```bash
git add .python-version
git commit -m "Force Python 3.11.11 for psycopg2 compatibility"
git push
```

**Fixing template paths:**
```bash
git add pkg/patient_routes.py pkg/doctor_route.py
git commit -m "Fix template paths - remove leading slashes"
git push
```

**Reverting migration changes:**
```bash
git add -A
git commit -m "Revert migration scripts - back to clean state for fresh database setup"
git push
```

**Removing unused files:**
```bash
git add -A
git commit -m "Remove unused prerun.sh script"
git push
```

**Updating contact form:**
```bash
git add pkg/templates/user/contact.html
git commit -m "Update contact form to use Formspree"
git push
```

### Git Best Practices

```bash
# Good commit message (clear and descriptive)
git commit -m "Fix template paths in doctor and patient routes"

# Bad commit message (vague)
git commit -m "fixed stuff"

# Atomic commits (one feature per commit)
git commit -m "Add render.yaml configuration"
git commit -m "Fix template path issues"

# Not (doing multiple things in one commit)
git commit -m "Added render.yaml, fixed templates, and changed config"
```

---

## Deployment Process

### Step-by-Step What Happens

#### 1. **Code Pushed to GitHub**
```bash
git push
```
Your local changes are uploaded to GitHub.

#### 2. **Render Detects Changes**
- Render watches your GitHub repository
- Detects new push to main branch
- Automatically starts deployment

#### 3. **Build Phase**
```bash
# Render runs this command from render.yaml
pip install -r requirements.txt
```
- Installs all Python packages
- Takes 1-2 minutes

#### 4. **Run Phase**
```bash
# Render runs this command from render.yaml
gunicorn --bind 0.0.0.0:$PORT pkg:app
```
- Starts the Flask application
- Gunicorn listens on assigned port
- App is now live!

#### 5. **Application Running**
Your app is now accessible at: `https://your-app-name.onrender.com`

### Viewing Logs

In Render Dashboard:
1. Go to your service
2. Click "Logs" tab
3. View deployment logs and runtime logs
4. See errors if deployment fails

**Typical Log Output:**
```
==> Build successful 🎉
==> Setting WEB_CONCURRENCY=1 by default
==> Deploying...
[PID] [INFO] Booting worker with pid: 56
==> Your service is live 🎉
==> Available at https://lshospital.onrender.com
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: TemplateNotFound Error
**Problem:**
```
TemplateNotFound: user/home.html
```

**Cause:**
- Template paths have leading slashes: `'/user/home.html'`
- Flask can't find templates with leading slashes

**Solution:**
```python
# Remove leading slash
render_template('user/home.html')  # Correct
render_template('/user/home.html')  # Wrong
```

#### Issue 2: psycopg2 ImportError
**Problem:**
```
ImportError: undefined symbol: _PyInterpreterState_Get
```

**Cause:**
- Using `psycopg2-binary` with Python 3.13
- Compatibility issue

**Solution:**
```
# In requirements.txt
psycopg2==2.9.9  # Not psycopg2-binary

# Create .python-version file with:
3.11.11
```

#### Issue 3: DATABASE_URL Not Found
**Problem:**
```
ProgrammingError: relation 'patient' does not exist
```

**Cause:**
- DATABASE_URL environment variable not set
- App using SQLite instead of PostgreSQL
- Database tables don't exist

**Solution:**
- In Render dashboard, set DATABASE_URL environment variable
- Use internal connection string from PostgreSQL service

#### Issue 4: Port Binding Error
**Problem:**
```
Address already in use
```

**Cause:**
- App hardcoded to specific port
- Render assigns dynamic port

**Solution:**
```python
# Use environment variable
port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port)
```

---

## Key Learnings

### 1. **Environment Configuration**
- Use environment variables for different configurations
- Same code can work locally and in production
- Check for `os.environ.get()` to detect environment

### 2. **Database URLs**
- Local: `mysql+mysqlconnector://user:pass@localhost/dbname`
- Render: `postgresql://user:pass@host:5432/dbname`
- Always handle database URL conversion

### 3. **Production Server**
- Never use Flask's development server in production
- Use Gunicorn for production
- Configure with `--bind 0.0.0.0:$PORT`

### 4. **Static Files and Templates**
- Use relative paths, not absolute paths
- Use `os.path.dirname(__file__)` for dynamic paths
- Don't use leading slashes in template paths

### 5. **Git Workflow**
```
Code → git add → git commit → git push → Render Deploy
```
- Clear, descriptive commit messages
- Atomic commits (one feature per commit)
- Push frequently to avoid losing work

### 6. **Version Control**
- Always use version control (Git/GitHub)
- Commit before making major changes
- Easy to rollback if something breaks

### 7. **Python Version Management**
- Use `.python-version` file to specify Python version
- Important for package compatibility
- Render respects this file

### 8. **PostgreSQL vs MySQL**
| Feature | PostgreSQL | MySQL |
|---------|-----------|-------|
| Best for | Production (Render) | Local development |
| Connection | `psycopg2` | `mysql-connector-python` |
| URL format | `postgresql://` | `mysql+mysqlconnector://` |
| Stability | Excellent | Good |

---

## Complete Workflow Example

### Scenario: Deploying a New Feature

#### 1. Make Changes Locally
```python
# Edit pkg/patient_routes.py
@patient_bp.route('/new-feature')
def new_feature():
    return render_template('user/new_feature.html')
```

#### 2. Test Locally
```bash
python starter.py
# Visit http://localhost:5000/new-feature
# Verify it works
```

#### 3. Commit Changes
```bash
git add pkg/patient_routes.py pkg/templates/user/new_feature.html
git commit -m "Add new feature to patient routes"
```

#### 4. Push to GitHub
```bash
git push
```

#### 5. Render Automatically Deploys
- Render detects push
- Runs build command
- Deploys your app
- Feature is live!

#### 6. Check Logs
- Visit Render dashboard
- Click Logs
- Verify deployment successful

---

## Summary

### What We Set Up

| Component | Purpose | File |
|-----------|---------|------|
| Flask App | Web framework | `pkg/__init__.py` |
| Configuration | Database settings | `pkg/config.py` |
| Entry Point | Run app locally | `starter.py` |
| Dependencies | Python packages | `requirements.txt` |
| Render Config | Deployment settings | `render.yaml` |
| Python Version | Force specific version | `.python-version` |
| Version Control | Track changes | Git/GitHub |

### What Happens on Deploy

1. Push code to GitHub
2. Render detects change
3. Pulls code from GitHub
4. Runs `pip install -r requirements.txt`
5. Runs `gunicorn --bind 0.0.0.0:$PORT pkg:app`
6. App is live!

### Key Files to Remember

```
LShospital/
├── render.yaml              # Render deployment config
├── .python-version          # Force Python 3.11.11
├── requirements.txt         # Python dependencies
├── starter.py              # Local dev entry point
├── pkg/
│   ├── __init__.py         # Flask app factory
│   ├── config.py           # Environment configuration
│   ├── patient_routes.py   # Patient routes (fixed paths)
│   ├── doctor_route.py     # Doctor routes (fixed paths)
│   ├── templates/          # HTML templates (relative paths)
│   └── static/             # CSS, JS, images
```

---

## Additional Resourcest

- **Render Docs:** https://render.com/docs
- **Flask Docs:** https://flask.palletsprojects.com/
- **SQLAlchemy Docs:** https://www.sqlalchemy.org/
- **Git Tutorial:** https://git-scm.com/docs
- **PostgreSQL Docs:** https://www.postgresql.org/docs/

---

**Created:** December 11, 2025  
**Purpose:** Complete documentation of LShospital Render deployment process  
**Author:** Development Team
