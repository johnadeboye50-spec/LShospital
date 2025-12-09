from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admin'
    admin_id = db.Column(db.Integer, primary_key=True)
    admin_username = db.Column(db.String(100))
    admin_password = db.Column(db.String(200))
    admin_logindate = db.Column(db.DateTime)


class Patient(db.Model):
    __tablename__ = 'patient'
    patient_id = db.Column(db.Integer, primary_key=True)
    patient_fname = db.Column(db.String(100), nullable=False)
    patient_lname = db.Column(db.String(100), nullable=False)
    patient_email = db.Column(db.String(150), unique=True, nullable=False)
    patient_password = db.Column(db.String(255), nullable=False)
    patient_address = db.Column(db.String(255),nullable=True)
    phone_num = db.Column(db.String(255),unique=True, nullable=True)
    patient_bio = db.Column(db.Text, nullable=True)
    patient_profilepic = db.Column(db.String(255), nullable=True)
    patient_dob = db.Column(db.Date)
    patient_regdate = db.Column(db.DateTime, default=datetime.utcnow)
    patient_gender = db.Column(db.Enum('male', 'female'))

    appointments = db.relationship('Appointment', backref='patient',lazy=True)
    payment = db.relationship('Payment', backref='patient',lazy=True)

class Doctor(db.Model):
    __tablename__ = 'doctor'
    doctor_id = db.Column(db.Integer, primary_key=True)
    specialty_id = db.Column(db.Integer,db.ForeignKey('specialty.specialty_id', ondelete='CASCADE', onupdate='CASCADE'),nullable=False)
    department_id = db.Column(db.Integer,db.ForeignKey('department.department_id', ondelete='CASCADE', onupdate='CASCADE'),nullable=True)
    doctor_fname = db.Column(db.String(100), nullable=False)
    doctor_lname = db.Column(db.String(100), nullable=False)
    doctor_email = db.Column(db.String(150), unique=True, nullable=False)
    doctor_phone = db.Column(db.String(50), unique=True, nullable=False)
    doctor_license = db.Column(db.String(100), unique=True, nullable=False)
    doctor_experience = db.Column(db.Integer, nullable=False)
    doctor_bio = db.Column(db.Text, nullable=True)
    doctor_profilepic = db.Column(db.String(255), nullable=True)
    doctor_password = db.Column(db.String(255), nullable=False)
    doctor_address = db.Column(db.String(255),nullable=True)
    doctor_gender = db.Column(db.Enum('male', 'female'))
    doctor_status = db.Column(db.Enum('active', 'inactive'), default='active')
    doctor_regdate = db.Column(db.DateTime, default=datetime.utcnow)


    appointments = db.relationship('Appointment', backref='doctor', lazy=True)

class DoctorSchedule(db.Model):
    __tablename__ = 'doctor_schedule'
    
    schedule_id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.doctor_id', ondelete='CASCADE'), nullable=False, unique=True)
    
    monday = db.Column(db.Boolean, default=False)
    tuesday = db.Column(db.Boolean, default=False)
    wednesday = db.Column(db.Boolean, default=False)
    thursday = db.Column(db.Boolean, default=False)
    friday = db.Column(db.Boolean, default=False)
    saturday = db.Column(db.Boolean, default=False)
    sunday = db.Column(db.Boolean, default=False)
    
   
    start_time = db.Column(db.Time, nullable=False)  # e.g., 09:00:00
    end_time = db.Column(db.Time, nullable=False)    # e.g., 17:00:00

    slot_duration = db.Column(db.Integer, default=30)  # 30-minute appointments
    

    max_appointments_per_slot = db.Column(db.Integer, default=1)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    doctor = db.relationship('Doctor', backref=db.backref('schedule', uselist=False))

    
class Appointment(db.Model):
    __tablename__ = 'appointment'
    app_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.patient_id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.doctor_id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    patient_note = db.Column(db.String(255), nullable=True) 
    doctor_note = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum('pending', 'accepted', 'declined', 'cancelled', 'completed'), default='pending')
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    consultation = db.relationship('Consultation', backref='appointment', lazy=True)

class Consultation(db.Model):
    __tablename__ = 'consultaion'

    cun_id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('appointment.app_id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)

    diagnose = db.Column(db.Text, nullable=False)
    treatment = db.Column(db.Text)
    medications = db.Column(db.Text)
    tests = db.Column(db.Text)

    amt = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Department(db.Model):
    __tablename__ = 'department'
    department_id = db.Column(db.Integer, primary_key=True)
    department_name =  db.Column(db.String(100), nullable=False)

    doctor = db.relationship('Doctor', backref='department', lazy=True)


class Specialty(db.Model):
    __tablename__ = 'specialty'
    specialty_id = db.Column(db.Integer, primary_key=True)
    specialty_name =  db.Column(db.String(100), nullable=False)

    doctor = db.relationship('Doctor', backref='specialty', lazy=True)

class Payment(db.Model):
    __tablename__ = 'payment'
    pay_id = db.Column(db.Integer, primary_key=True)
    pay_amt = db.Column(db.Float)
    pay_patientid = db.Column(db.Integer, db.ForeignKey('patient.patient_id',ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    cun_id = db.Column(db.Integer, db.ForeignKey('consultaion.cun_id',ondelete='CASCADE', onupdate='CASCADE'), nullable=True)
    pay_ref = db.Column(db.String(100), unique=True)
    pay_method = db.Column(db.Enum('cash', 'transfer'), default='transfer')
    pay_status = db.Column(db.Enum('pending', 'failed', 'paid'), default='pending')
    pay_data = db.Column(db.JSON)
    pay_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    consultation = db.relationship('Consultation', backref='payments', lazy=True)



