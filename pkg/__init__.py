import os
from flask import Flask, session
from flask_wtf import CSRFProtect
from flask_migrate import Migrate

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
    
    
    return app

app = create_app()

from pkg import config, patient_routes, admin_routes, models, forms, doctor_route
