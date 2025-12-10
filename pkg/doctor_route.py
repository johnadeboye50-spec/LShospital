from datetime import date, datetime,timedelta
import os, secrets
from functools import wraps
from flask import redirect, render_template, request, session,url_for,jsonify,flash
from werkzeug.security import generate_password_hash,check_password_hash
from pkg import app
from pkg.forms import DoctorForm, DoctorLoginForm, DoctorSettingsForm
from pkg.models import db,Doctor,Department,Patient,Payment,Consultation,Specialty,Admin,Appointment,DoctorSchedule
from markupsafe import escape


def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("doctor_id") is None:
            return redirect(url_for("doctor_login"))
        return f(*args, **kwargs)
    return decorated_function


@app.get('/doctors/')
def doctors_page():
    doctors = Doctor.query.all()
    specialties = Specialty.query.all()
    return render_template('user/doctor_page.html',doctors=doctors,specialties=specialties)

@app.get('/doctor/<int:doctor_id>/')
def doctor_profile(doctor_id):
    doctor = db.session.query(Doctor).get_or_404(doctor_id)
    
    # Get doctor's schedule
    schedule = DoctorSchedule.query.filter_by(doctor_id=doctor_id).first()
    
    # Get total appointments, completed consultations
    total_appointments = Appointment.query.filter_by(doctor_id=doctor_id).count()
    completed_consultations = Consultation.query.join(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status == 'completed'
    ).count()
    
    # Get recent patient reviews/feedback (if available)
    recent_appointments = Appointment.query.filter_by(
        doctor_id=doctor_id,
        status='completed'
    ).order_by(Appointment.updated_at.desc()).limit(5).all()
    
    return render_template(
        'user/doctor_profile.html',
        doctor=doctor,
        schedule=schedule,
        total_appointments=total_appointments,
        completed_consultations=completed_consultations,
        recent_appointments=recent_appointments
    )


@app.route('/doctors/login/', methods=['GET', 'POST'])
def doctor_login():
    docform = DoctorLoginForm()
    if session.get('doctor_id') != None:
        return redirect(url_for('doctor_dashboard'))
    if request.method == 'GET':
        return render_template('doctors/doctor_login.html', docform=docform)
    else:
        if docform.validate_on_submit():
            email = docform.email.data
            password = docform.password.data
            record = Doctor.query.filter(Doctor.doctor_email==email).first()
            if record:
                stored_hash = record.doctor_password
                doctorid = record.doctor_id
                chk = check_password_hash(stored_hash, password)
                if chk == True:
                    session['doctor_id'] = doctorid
                    flash('Login successful!', 'success')
                    return redirect(url_for('doctor_dashboard'))
                else:
                    flash('Incorrect password. Please try again.', 'error')
                    return redirect(url_for('doctor_login'))
            else:
                flash('No account found with that email.', 'error')
                return redirect(url_for('doctor_login'))
        else:
            return render_template('doctors/doctor_login.html', docform=docform)

@app.route('/doctor/register/', methods=['POST', 'GET'])
def doctor_register():
    form = DoctorForm()
    specialties = Specialty.query.all()
    form.specialization.choices = [(str(s.specialty_id), s.specialty_name) for s in specialties]

    if request.method == 'GET':
        return render_template('doctors/doctor_register.html', form=form)
    else:
        if form.validate_on_submit():
            email = form.email.data
            
            # Check if email already exists in doctor table
            existing_doctor = Doctor.query.filter_by(doctor_email=email).first()
            if existing_doctor:
                flash('This email is already registered as a doctor. Please use a different email or login.', 'error')
                return render_template('doctors/doctor_register.html', form=form)
            
            # Check if email already exists in patient table
            existing_patient = Patient.query.filter_by(patient_email=email).first()
            if existing_patient:
                flash('This email is already registered as a patient. Please use a different email.', 'error')
                return render_template('doctors/doctor_register.html', form=form)
            
            # Check if license number already exists
            existing_license = Doctor.query.filter_by(doctor_license=form.license_no.data).first()
            if existing_license:
                flash('This license number is already registered. Please check your license number.', 'error')
                return render_template('doctors/doctor_register.html', form=form)
            
            try:
                hashed_password = generate_password_hash(form.password.data)
                new_doctor = Doctor(
                    doctor_fname=form.firstname.data,
                    doctor_lname=form.lastname.data,
                    doctor_email=email,
                    doctor_phone=form.phone.data,
                    specialty_id=int(form.specialization.data),
                    doctor_license=form.license_no.data,
                    doctor_experience=form.experience.data,
                    doctor_bio=form.bio.data,
                    doctor_gender=form.doctor_gender.data,
                    doctor_password=hashed_password,
                    doctor_profilepic="default_doc.png"
                )
                
                pix = form.profile_pic.data
                if pix:
                    filename = pix.filename
                    _, ext = os.path.splitext(filename)
                    newname = secrets.token_hex(10) + ext
                    save_path = os.path.join("pkg", "static", "uploads", "doctors", newname)
                    pix.save(save_path)
                    new_doctor.doctor_profilepic = newname
                else:
                    new_doctor.doctor_profilepic = "default_doc.png"
                
                db.session.add(new_doctor)
                db.session.commit()
                flash('Doctor account created successfully!', 'success')
                return redirect(url_for('doctor_login'))
            except Exception as e:
                db.session.rollback()
                flash('Registration failed. Please try again.', 'error')
                return render_template('doctors/doctor_register.html', form=form)
        else:
            return render_template('doctors/doctor_register.html', form=form)

@app.route("/add_specialties/")
def add_specialties():
    specialties = [
        "Cardiology",
        "Neurology",
        "Pediatrics",
        "Dermatology",
        "General Surgery",
        "Family Medicine",
        "Orthopedics",
        "Gastroenterology"
    ]

    for name in specialties:
        sp = Specialty(specialty_name=name)
        db.session.add(sp)

    db.session.commit()
    return "Specialties added!"

@app.route('/doctor/dashboard/')
@doctor_required
def doctor_dashboard():
    doctor = Doctor.query.get(session['doctor_id'])
    
    # Get today's appointments (latest first, limit 4)
    today = date.today()
    todays_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.doctor_id,
        Appointment.appointment_date == today
    ).order_by(Appointment.created_at.desc()).limit(4).all()
    
    # Get appointments by status for quick stats
    accepted_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.doctor_id,
        Appointment.status == 'accepted'
    ).count()
    
    declined_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.doctor_id,
        Appointment.status == 'declined'
    ).count()
    
    completed_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.doctor_id,
        Appointment.status == 'completed'
    ).count()
    
    # Get today's stats
    todays_total = Appointment.query.filter(
        Appointment.doctor_id == doctor.doctor_id,
        Appointment.appointment_date == today
    ).count()
    
    todays_completed = Appointment.query.filter(
        Appointment.doctor_id == doctor.doctor_id,
        Appointment.appointment_date == today,
        Appointment.status == 'completed'
    ).count()
    
    # Get recent patients
    recent_patients = db.session.query(Patient).join(Appointment).filter(
        Appointment.doctor_id == doctor.doctor_id
    ).distinct().order_by(Appointment.created_at.desc()).limit(5).all()
    
    # Get statistics
    total_patients = db.session.query(Patient).join(Appointment).filter(
        Appointment.doctor_id == doctor.doctor_id
    ).distinct().count()
    
    total_appointments = Appointment.query.filter_by(doctor_id=doctor.doctor_id).count()
    
    pending_appointments = Appointment.query.filter_by(
        doctor_id=doctor.doctor_id,
        status='pending'
    ).count()
    
    completed_consultations = Consultation.query.join(Appointment).filter(
        Appointment.doctor_id == doctor.doctor_id
    ).count()
    
    # Recent activity (limit 4)
    activities = []
    
    # Recent appointments
    recent_appts = Appointment.query.filter_by(
        doctor_id=doctor.doctor_id
    ).order_by(Appointment.created_at.desc()).limit(3).all()
    
    for appt in recent_appts:
        activities.append({
            'title': f'Appointment with {appt.patient.patient_fname} {appt.patient.patient_lname}',
            'description': f'{appt.status.capitalize()} - {appt.appointment_date.strftime("%b %d, %Y")}',
            'date': appt.created_at,
            'icon': 'patient',
            'pic': appt.patient.patient_profilepic
        })
    
    # Recent consultations
    recent_consults = Consultation.query.join(Appointment).filter(
        Appointment.doctor_id == doctor.doctor_id
    ).order_by(Consultation.date.desc()).limit(2).all()
    
    for consult in recent_consults:
        activities.append({
            'title': f'Consultation completed',
            'description': f'Patient: {consult.appointment.patient.patient_fname} {consult.appointment.patient.patient_lname}',
            'date': consult.date,
            'icon': 'C',
            'pic': None
        })
    
    # Sort activities by date and limit to 4
    activities.sort(key=lambda x: x['date'], reverse=True)
    activities = activities[:4]
    
    return render_template(
        '/doctors/doctor_dashboard.html',
        doctor=doctor,
        todays_appointments=todays_appointments,
        accepted_appointments=accepted_appointments,
        declined_appointments=declined_appointments,
        completed_appointments=completed_appointments,
        todays_total=todays_total,
        todays_completed=todays_completed,
        recent_patients=recent_patients,
        total_patients=total_patients,
        total_appointments=total_appointments,
        pending_appointments=pending_appointments,
        completed_consultations=completed_consultations,
        activities=activities
    )

@app.route('/doctors/filter', methods=['POST'])
def filter_doctors():
    data = request.json
    search = data.get("search", "").lower()
    gender = data.get("gender", "any")
    specialty = data.get("specialty", "any")

    query = Doctor.query.join(Specialty)

    # SEARCH
    if search:
        query = query.filter(
            (Doctor.doctor_fname.ilike(f"%{search}%")) |
            (Doctor.doctor_lname.ilike(f"%{search}%")) |
            (Specialty.specialty_name.ilike(f"%{search}%"))
        )

    # GENDER
    if gender != "any":
        query = query.filter(Doctor.doctor_gender == gender)

    # SPECIALTY
    if specialty != "any":
        query = query.filter(Doctor.specialty_id == int(specialty))
    doctors = query.all()

    return render_template("user/doctor_cards.html", doctors=doctors)

@app.route("/doctor/update/settings", methods=['GET', 'POST'])
@doctor_required
def update_doctor_settings():
    form = DoctorSettingsForm()
    if session.get("doctor_id") != None:

        doct = Doctor.query.get(session["doctor_id"])

        # Populate department choices
        departments = Department.query.order_by(Department.department_name.asc()).all()
        form.department.choices = [(str(d.department_id), d.department_name) for d in departments]

        if form.validate_on_submit():
            # Get the data from the form
            fname = form.fname.data
            lname = form.lname.data
            phone = form.phone.data
            address = form.address.data
            department_id = form.department.data
            bio = form.bio.data
            picture = form.picture.data  # file or None

            # If user selected a picture
            if picture:
                filename = picture.filename
                _, ext = os.path.splitext(filename)
                newname = secrets.token_hex(10) + ext
                picture.save("pkg/static/uploads/doctors/" + newname)

                # Update database field
                doct.doctor_profilepic = newname

            # Update all fields
            doct.doctor_fname = fname
            doct.doctor_lname = lname
            doct.doctor_phone = phone
            doct.doctor_address = address
            # Update department
            if department_id:
                try:
                    doct.department_id = int(department_id)
                except ValueError:
                    pass
            doct.doctor_bio = bio

            db.session.commit()

            flash("Profile updated successfully", category="msg")
            return redirect(url_for("update_doctor_settings"))

        else:
            # Pre-populate form with existing data
            form.fname.data = doct.doctor_fname
            form.lname.data = doct.doctor_lname
            form.phone.data = doct.doctor_phone
            form.address.data = doct.doctor_address
            form.department.data = str(doct.department_id) if getattr(doct, 'department_id', None) else None
            form.bio.data = doct.doctor_bio
            
            return render_template("doctors/doctor_setting.html", form=form, doct=doct)

    else:
        flash("You must be logged in to access this page", category="errormsg")
        return redirect(url_for("login_page"))


@app.route('/doctor/appointments/')
@doctor_required
def doctor_appointments():
    doctor_id = session["doctor_id"]

    appointments = Appointment.query.filter_by(doctor_id=doctor_id).order_by(
        Appointment.updated_at.desc()
    ).all()

    return render_template("doctors/appointments.html", appointments=appointments)

@app.route('/doctor/appointment/<int:id>/accept/')
@doctor_required
def accept_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    # Ownership check: only the assigned doctor can modify
    if appointment.doctor_id != session.get("doctor_id"):
        flash("Access denied: You cannot modify another doctor's appointment.", "danger")
        return redirect(url_for("doctor_appointments"))

    if appointment.status == "pending":
        appointment.status = "accepted"
        db.session.commit()

    return redirect(url_for("doctor_appointments"))

@app.route('/doctor/appointment/<int:id>/decline/')
@doctor_required
def decline_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    if appointment.doctor_id != session.get("doctor_id"):
        flash("Access denied: You cannot modify another doctor's appointment.", "danger")
        return redirect(url_for("doctor_appointments"))

    if appointment.status == "pending":
        appointment.status = "declined"
        db.session.commit()

    return redirect(url_for("doctor_appointments"))

@app.route("/doctor/appointment/<int:id>/add-note/", methods=['GET', 'POST'])
@doctor_required
def add_doctor_note(id):
    appnt = Appointment.query.get_or_404(id)
    if appnt.doctor_id != session.get("doctor_id"):
        flash("Access denied: You cannot add a note to another doctor's appointment.", "danger")
        return redirect(url_for("doctor_appointments"))

    if request.method == 'GET':
        return redirect(url_for("doctor_appointments"))

    note = request.form.get("doctor_note")

    if note:
        appnt.doctor_note = note
        db.session.commit()
        flash("Note sent to patient!", "success")
    else:
        flash("Note cannot be empty.", "danger")

    return redirect(url_for("doctor_appointments"))


@app.route('/doctor/appointment/<int:id>/complete/')
@doctor_required
def complete_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    if appointment.doctor_id != session.get("doctor_id"):
        flash("Access denied: You cannot complete another doctor's appointment.", "danger")
        return redirect(url_for("doctor_appointments"))

    if appointment.status == "accepted":
        appointment.status = "completed"
        db.session.commit()

    return redirect(url_for("doctor_appointments"))


@app.route("/doctor/consultation/<int:id>/", methods=["GET", "POST"])
@doctor_required
def start_consultation(id):

    # Fetch appointment
    app = Appointment.query.get_or_404(id)

    # Ownership check
    if app.doctor_id != session.get("doctor_id"):
        flash("Access denied: You cannot consult appointments not assigned to you.", "danger")
        return redirect(url_for("doctor_appointments"))

    # Only accepted appointments can be consulted
    if app.status != "accepted":
        flash("You can only consult accepted appointments.", "danger")
        return redirect(url_for("doctor_appointments"))

    if request.method == "POST":

        diagnose = request.form.get("diagnose")
        treatment = request.form.get("treatment")
        medications = request.form.get("medications")
        tests = request.form.get("tests")
        amt = request.form.get("amt")

        if not diagnose:
            flash("Diagnosis is required.", "danger")
            return redirect(request.url)

        # Save consultation record
        new_consult = Consultation(
            app_id=app.app_id,
            diagnose=diagnose,
            treatment=treatment,
            medications=medications,
            tests=tests,
            amt=float(amt) if amt else None,
            date=datetime.utcnow()
        )

        db.session.add(new_consult)

        # Update appointment status to completed
        app.status = "completed"

        db.session.commit()

        flash("Consultation saved successfully.", "success")
        return redirect(url_for("doctor_appointments"))

    return render_template("doctors/consultation_form.html", app=app)

@app.route("/doctor/view/consultation/<int:id>/")
@doctor_required
def doctor_view_consultation(id):
    consultation = (
        db.session.query(Consultation)
        .join(Appointment, Consultation.app_id == Appointment.app_id)
        .filter(
            Consultation.app_id == id,
            Appointment.doctor_id == session["doctor_id"]
        )
        .first()
    )

    if consultation is None:
        flash("Consultation not found or access denied.", category="error")
        return redirect(url_for("doctor_appointments"))

    return render_template(
        "doctors/view_consultation.html",
        consultation=consultation
    )
    
@app.route("/doctor/patients")
@doctor_required
def doctor_patients():
    doc_id = session.get("doctor_id")

    # Get patients linked to this doctor's appointments
    patients = (
        db.session.query(Patient)
        .join(Appointment, Appointment.patient_id == Patient.patient_id)
        .filter(Appointment.doctor_id == doc_id)
        .group_by(Patient.patient_id)
        .order_by(db.func.max(Appointment.updated_at).desc())
        .all()
    )

    return render_template("doctors/doctor_patients.html", patients=patients)

@app.route("/doctor/patient/<int:id>")
@doctor_required
def doctor_view_patient(id):
    patient = Patient.query.get_or_404(id)

    # Verify the patient has a relationship with the logged-in doctor
    related = Appointment.query.filter_by(
        patient_id=id,
        doctor_id=session.get("doctor_id")
    ).count() > 0

    if not related:
        flash("Access denied: You can only view patients you've treated or have appointments with.", "danger")
        return redirect(url_for("doctor_patients"))

    # Get history with that doctor only
    appointments = Appointment.query.filter_by(
        patient_id=id, 
        doctor_id=session.get("doctor_id")
    ).order_by(Appointment.appointment_date.desc()).all()

    consultations = Consultation.query.join(Appointment).filter(
        Appointment.patient_id == id,
        Appointment.doctor_id == session.get("doctor_id")
    ).order_by(Consultation.date.desc()).all()

    return render_template("doctors/view_patient.html",patient=patient,appointments=appointments,consultations=consultations)

@app.route('/doctor/schedule/', methods=['GET', 'POST'])
@doctor_required
def doctor_schedule():
    doctor_id = session['doctor_id']
    schedule = DoctorSchedule.query.filter_by(doctor_id=doctor_id).first()
    
    if request.method == 'POST':
        # Get form data
        days = {
            'monday': bool(request.form.get('monday')),
            'tuesday': bool(request.form.get('tuesday')),
            'wednesday': bool(request.form.get('wednesday')),
            'thursday': bool(request.form.get('thursday')),
            'friday': bool(request.form.get('friday')),
            'saturday': bool(request.form.get('saturday')),
            'sunday': bool(request.form.get('sunday')),
        }

        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        slot_duration = request.form.get('slot_duration', type=int)
        max_per_slot = request.form.get('max_appointments_per_slot', type=int)

        # Basic validations
        if not start_time or not end_time:
            flash('Start and end time are required.', 'danger')
            return redirect(url_for('doctor_schedule'))

        try:
            st = datetime.strptime(start_time, '%H:%M').time()
            et = datetime.strptime(end_time, '%H:%M').time()
        except ValueError:
            flash('Invalid time format. Use HH:MM (24-hour).', 'danger')
            return redirect(url_for('doctor_schedule'))

        if slot_duration not in [15, 20, 30, 45, 60]:
            slot_duration = 30

        if not max_per_slot or max_per_slot < 1:
            max_per_slot = 1

        if schedule is None:
            schedule = DoctorSchedule(
                doctor_id=doctor_id,
                start_time=st,
                end_time=et,
                slot_duration=slot_duration,
                max_appointments_per_slot=max_per_slot,
                **days
            )
            db.session.add(schedule)
        else:
            schedule.start_time = st
            schedule.end_time = et
            schedule.slot_duration = slot_duration
            schedule.max_appointments_per_slot = max_per_slot
            for k, v in days.items():
                setattr(schedule, k, v)

        db.session.commit()
        flash('Schedule saved successfully.', 'success')
        return redirect(url_for('doctor_schedule'))
    
    days_enabled = None
    if schedule:
        days_enabled = {
            'monday': bool(schedule.monday),
            'tuesday': bool(schedule.tuesday),
            'wednesday': bool(schedule.wednesday),
            'thursday': bool(schedule.thursday),
            'friday': bool(schedule.friday),
            'saturday': bool(schedule.saturday),
            'sunday': bool(schedule.sunday),
        }

    return render_template('doctors/schedule.html', schedule=schedule, days_enabled=days_enabled)


@app.route('/doctor/statistics/')
@doctor_required
def doctor_statistics():
    doctor_id = session.get('doctor_id')
    doctor = Doctor.query.get(doctor_id)
    
    if not doctor:
        flash("Doctor not found", "error")
        return redirect(url_for('doctor_login'))
    
    # Overall Statistics
    total_appointments = Appointment.query.filter_by(doctor_id=doctor_id).count()
    
    total_patients = db.session.query(Patient).join(Appointment).filter(
        Appointment.doctor_id == doctor_id
    ).distinct().count()
    
    total_consultations = Consultation.query.join(Appointment).filter(
        Appointment.doctor_id == doctor_id
    ).count()
    
    # Appointment Status Breakdown
    pending_appointments = Appointment.query.filter_by(doctor_id=doctor_id, status='pending').count()
    accepted_appointments = Appointment.query.filter_by(doctor_id=doctor_id, status='accepted').count()
    completed_appointments = Appointment.query.filter_by(doctor_id=doctor_id, status='completed').count()
    declined_appointments = Appointment.query.filter_by(doctor_id=doctor_id, status='declined').count()
    cancelled_appointments = Appointment.query.filter_by(doctor_id=doctor_id, status='cancelled').count()
    
    # Revenue Statistics
    total_revenue = db.session.query(db.func.sum(Payment.pay_amt)).join(Consultation).join(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Payment.pay_status == 'paid'
    ).scalar() or 0
    
    pending_revenue = db.session.query(db.func.sum(Payment.pay_amt)).join(Consultation).join(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Payment.pay_status == 'pending'
    ).scalar() or 0
    
    # This Month Statistics
    today = date.today()
    first_day_of_month = today.replace(day=1)
    
    this_month_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.created_at >= first_day_of_month
    ).count()
    
    this_month_consultations = Consultation.query.join(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Consultation.date >= first_day_of_month
    ).count()
    
    this_month_revenue = db.session.query(db.func.sum(Payment.pay_amt)).join(Consultation).join(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Payment.pay_status == 'paid',
        Payment.pay_date >= first_day_of_month
    ).scalar() or 0
    
    # Top Diagnoses (Most Common)
    top_diagnoses = db.session.query(
        Consultation.diagnose,
        db.func.count(Consultation.cun_id).label('count')
    ).join(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Consultation.diagnose.isnot(None),
        Consultation.diagnose != ''
    ).group_by(Consultation.diagnose).order_by(db.desc('count')).limit(5).all()
    
    # Average Consultation Fee
    avg_fee = db.session.query(db.func.avg(Consultation.amt)).join(Appointment).filter(
        Appointment.doctor_id == doctor_id
    ).scalar() or 0
    
    return render_template(
        'doctors/statistics.html',
        doctor=doctor,
        total_appointments=total_appointments,
        total_patients=total_patients,
        total_consultations=total_consultations,
        pending_appointments=pending_appointments,
        accepted_appointments=accepted_appointments,
        completed_appointments=completed_appointments,
        declined_appointments=declined_appointments,
        cancelled_appointments=cancelled_appointments,
        total_revenue=total_revenue,
        pending_revenue=pending_revenue,
        this_month_appointments=this_month_appointments,
        this_month_consultations=this_month_consultations,
        this_month_revenue=this_month_revenue,
        top_diagnoses=top_diagnoses,
        avg_fee=avg_fee
    )