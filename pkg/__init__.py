import os
from flask import Flask, session, render_template, redirect, url_for
from dotenv import load_dotenv
from flask_wtf import CSRFProtect
from flask_migrate import Migrate

load_dotenv()

csrf = CSRFProtect()

def create_app():
    from pkg import config
    from pkg.models import db, Patient, Doctor   # <-- added Patient & Doctor import

    app = Flask(__name__, instance_relative_config=True)
    
    # Set template and static folders relative to the pkg module directory
    app.template_folder = os.path.join(os.path.dirname(__file__), 'templates')
    app.static_folder = os.path.join(os.path.dirname(__file__), 'static')
    
    app.config.from_pyfile('config.py', silent=True)
    
    # Use environment to determine config
    env = os.environ.get("RENDER", None)
    if env:
        app.config.from_object(config.LiveConfig)
    else :
        app.config.from_object(config.DevelopmentConfig)


    csrf.init_app(app)
    db.init_app(app)
    Migrate(app, db)
    


    #(GLOBAL DEETS + DOCTOR)
    @app.context_processor
    def inject_user():
        patient = None
        doctor = None

        if session.get("patient_id"):
            patient = Patient.query.get(session["patient_id"])

        if session.get("doctor_id"):
            doctor = Doctor.query.get(session["doctor_id"])

        return dict(deets=patient, doctor=doctor)
    
    @app.errorhandler(404)
    def page_not_found(e):
        if session.get('patient_id') != None:
            return redirect(url_for('patient_dashboard'))
        elif session.get('doctor_id') != None:
            return redirect(url_for('doctor_dashboard'))
        elif session.get('admin_id') != None:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('home'))
        
    @app.errorhandler(500)
    def internal_server_error(e):
        if session.get('patient_id') != None:
            return redirect(url_for('patient_dashboard'))
        elif session.get('doctor_id') != None:
            return redirect(url_for('doctor_dashboard'))
        elif session.get('admin_id') != None:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('home'))
        
    @app.errorhandler(403)
    def forbidden(e):
        if session.get('patient_id') != None:
            return redirect(url_for('patient_dashboard'))
        elif session.get('doctor_id') != None:
            return redirect(url_for('doctor_dashboard'))
        elif session.get('admin_id') != None:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('home'))
    
    return app

app = create_app()

from pkg import config, patient_routes, admin_routes, models, forms, doctor_route
