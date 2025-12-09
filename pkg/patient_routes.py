from datetime import date, datetime
from functools import wraps
import secrets, os, requests, json
from werkzeug.utils import secure_filename
from flask import redirect, render_template, request, session,url_for,jsonify,flash
from werkzeug.security import generate_password_hash,check_password_hash
from pkg import app
from pkg.forms import LoginForm, RegistrationForm,CompleteProfileForm,PatientSettingsForm
from pkg.models import db,Doctor,Patient,Payment,Consultation,Specialty,Appointment,DoctorSchedule
from markupsafe import escape

@app.after_request
def after_request(response):
    response.headers["Cache-Control"]="no-casche, no-store,must-revalate"
    return response

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('patient_id') is None:
            flash('You must be logged in to view this page', category='error')
            return redirect(url_for('user_login'))
        return f(*args, **kwargs)
    return decorated_function

def profile_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('patient_id') is None:
            flash('You must be logged in to view this page', category='error')
            return redirect(url_for('user_login'))

        patient = db.session.query(Patient).get(session['patient_id'])
        if patient.phone_num is None or patient.patient_address is None:
            flash('You must complete your profile before accessing this page.', category='warning')
            return redirect(url_for('complete_profileform'))

        return f(*args, **kwargs)
    return decorated_function

@app.get('/')
def home():
    patient = None
    doctor = None
    if session.get('patient_id'):
        patient = Patient.query.get(session['patient_id'])
    if session.get('doctor_id'):
        doctor = Doctor.query.get(session['doctor_id'])
    return render_template('/user/home.html', deets=patient, doctor=doctor)

@app.get('/about/')
def about():
    return render_template('/user/about.html')

@app.get('/services/')
def services():
    return render_template('/user/services.html')

@app.get('/contact/')
def contact():
    return render_template('/user/contact.html')

@app.get('/login/')
def login_page():
    if session.get('patient_id') != None:
        return redirect(url_for('patient_dashboard'))
    if session.get('doctor_id') != None:
        return redirect(url_for('doctor_dashboard'))
    
    return render_template('/user/login.html')

@app.route('/patient/login/', methods=['POST', 'GET'])
def user_login():
    logform = LoginForm()
    if session.get('doctor_id') != None:
        return redirect(url_for('doctor_dashboard'))
    
    if session.get('patient_id') != None:
        return redirect(url_for('patient_dashboard'))
    if request.method == 'GET':
        return render_template('/user/patient_login.html', logform=logform)
    else:
        if logform.validate_on_submit():
            email = logform.email.data
            password = logform.password.data
            record = Patient.query.filter(Patient.patient_email==email).first()
            if record:
                stored_hash = record.patient_password
                userid = record.patient_id
                chk = check_password_hash(stored_hash, password)
                if chk == True:
                    session['patient_id'] = userid
                    return redirect(url_for('patient_dashboard'))
                else:
                    flash('Incorrect password. Please try again.', category='error')
                    return redirect(url_for('user_login'))  
            else:
                flash('This Email Address Is Incorrect', category='error')
                return redirect(url_for('user_login'))
        else:
            return render_template('/user/patient_login.html', logform=logform)

@app.route('/register/', methods=['POST', 'GET'])
def user_register():
    regform = RegistrationForm()
    if request.method == 'GET':
        return render_template('/user/register.html', regform=regform)
    else:
        if regform.validate_on_submit():
            email = regform.email.data
            
            # Check if email already exists in patient table
            existing_patient = Patient.query.filter_by(patient_email=email).first()
            if existing_patient:
                flash('This email is already registered as a patient. Please use a different email or login.', category='error')
                return render_template('/user/register.html', regform=regform)
            
            # Check if email already exists in doctor table
            existing_doctor = Doctor.query.filter_by(doctor_email=email).first()
            if existing_doctor:
                flash('This email is already registered as a doctor. Please use a different email.', category='error')
                return render_template('/user/register.html', regform=regform)
            
            # Proceed with registration
            first_name = regform.first_name.data
            last_name = regform.last_name.data
            password = regform.password.data
            to_bestored = generate_password_hash(password)
            
            patient = Patient(
                patient_fname=first_name,
                patient_lname=last_name,
                patient_email=email,
                patient_password=to_bestored
            )
            
            try:
                db.session.add(patient)
                db.session.commit()
                flash('Registration Successful. Please log in.', category='success')
                return redirect(url_for('user_login'))
            except Exception as e:
                db.session.rollback()
                flash('Registration failed. Please try again.', category='error')
                return render_template('/user/register.html', regform=regform)
        else:
            return render_template('/user/register.html', regform=regform)

#method 1 for logout
# @app.get('/logout/')
# def user_logout():
#     if session.get('patient_id') != None:
#         session.pop('patient_id')
#     if session.get('doctor_id') != None:
#         session.pop('doctor_id')
#     return redirect(url_for('home'))

#method 2 for logout
@app.get('/logout/')
def user_logout():
    session.pop('patient_id', None)

    session.pop('doctor_id', None)

    return redirect(url_for('home'))


    

@app.get('/dashboard/')
def patient_dashboard():
    if session.get('patient_id') != None:
        deets = Patient.query.get(session['patient_id'])
        # Appointments ordered by most recent update
        appointments = Appointment.query.filter_by(patient_id=session['patient_id']).order_by(Appointment.updated_at.desc()).all()

        # Recent activities: build lightweight feed from appointments, consultations, and payments
        activities = []
        
        # Add appointments
        for a in appointments[:5]:
            activities.append({
                'title': f"Appointment - Dr. {a.doctor.doctor_fname} {a.doctor.doctor_lname}",
                'description': f"{a.status.capitalize()} • {a.appointment_date.strftime('%b %d, %Y')}",
                'date': a.updated_at,
                'icon': 'doctor',
                'pic': a.doctor.doctor_profilepic,
                'link': url_for('patient_appointments')
            })

        # Consultations tied to patient's appointments
        cons = Consultation.query.join(Appointment, Consultation.app_id == Appointment.app_id)\
            .filter(Appointment.patient_id == session['patient_id']).order_by(Consultation.date.desc()).all()
        for c in cons[:5]:
            activities.append({
                'title': 'Consultation Completed',
                'description': (c.diagnose[:60] + '...') if c.diagnose and len(c.diagnose) > 60 else c.diagnose or 'Consultation recorded',
                'date': c.date,
                'icon': 'C',
                'pic': None,
                'link': url_for('patient_appointments')
            })

        # Payments
        pays = Payment.query.filter_by(pay_patientid=session['patient_id']).order_by(Payment.pay_date.desc()).all()
        for p in pays[:5]:
            activities.append({
                'title': 'Payment',
                'description': f"{p.pay_status.capitalize()} • ₦{p.pay_amt:,.2f}",
                'date': p.pay_date,
                'icon': '₦',
                'pic': None,
                'link': None
            })
        
        # Sort all activities by date descending
        activities = sorted(activities, key=lambda x: x['date'] if x['date'] else datetime.min, reverse=True)

        # Simple medications from latest consultation medications text
        medications = []
        for c in cons[:3]:
            if c.medications:
                medications.append({
                    'name': c.medications,
                    'dosage': None,
                    'instructions': c.treatment,
                    'last_refill': c.date
                })

        # Conditions from consultation diagnose
        conditions = []
        for c in cons[:3]:
            if c.diagnose:
                conditions.append({
                    'name': c.diagnose,
                    'description': c.treatment,
                    'primary_doctor': None,
                    'added_at': c.date
                })

        # Bills from consultations (showing consultation fees) and payments
        bills = []
        
        # Add consultation bills
        for c in cons[:3]:
            if c.amt and c.amt > 0:
                # Check if this consultation has a corresponding payment using cun_id
                payment = Payment.query.filter_by(
                    pay_patientid=session['patient_id'],
                    cun_id=c.cun_id
                ).first()
                
                bills.append({
                    'amount': c.amt,
                    'status': payment.pay_status if payment else 'unpaid',
                    'paid_at': payment.pay_date if payment and payment.pay_status == 'paid' else None,
                    'reference': payment.pay_ref if payment else f"CON-{c.cun_id}",
                    'type': 'Consultation Fee',
                    'consultation_id': c.cun_id,
                    'payment_id': payment.pay_id if payment else None
                })
        
        # Sort bills by date (most recent first) and limit to 3
        bills = sorted(bills, key=lambda x: x['paid_at'] if x['paid_at'] else datetime.min, reverse=True)[:3]

        return render_template(
            '/user/patient_dashboard.html',
            deets=deets,
            appointments=appointments,
            activities=activities,
            medications=medications,
            conditions=conditions,
            bills=bills
        )
    else:
        flash('You must be logged in to view this page',category='error')
        return redirect(url_for('user_login'))

@app.route('/complete_profileform/', methods=['GET', 'POST'])
def complete_profileform():
    if session.get('patient_id') != None:
        conform = CompleteProfileForm()
        if request.method == 'GET':
            return render_template('/user/complete_form.html', conform=conform)
        else:
            if conform.validate_on_submit():

                phone = conform.phone.data
                address = conform.address.data
                gender = conform.gender.data
                dob = conform.dob.data
                
                # Check if phone number already exists for another patient
                existing_phone = Patient.query.filter(
                    Patient.phone_num == phone,
                    Patient.patient_id != session['patient_id']
                ).first()
                
                if existing_phone:
                    flash('This phone number is already registered. Please use a different phone number.', category='error')
                    return render_template('/user/complete_profileform.html', conform=conform)
                
                patient = db.session.query(Patient).get(session['patient_id'])
                patient.phone_num = phone
                patient.patient_gender = gender
                patient.patient_address = address
                patient.patient_dob = dob
                db.session.commit()
                flash('Profile updated successfully! You can now book an appointment.', category='success')
                return redirect(url_for('book_appointment'))
            else:
                return render_template('/user/complete_profileform.html', conform=conform)
    else:
        flash('You must be logged in to view this page',category='error')
        return redirect(url_for('user_login'))
    
@app.route('/book_appointment/', methods=['GET', 'POST'])
def book_appointment():
    # Prevent doctors from accessing patient booking page
    if session.get("doctor_id"):
        flash("Doctors cannot book appointments. Please use your doctor dashboard.", category='warning')
        return redirect(url_for("doctor_dashboard"))
    
    # Check if patient is logged in
    if not session.get("patient_id"):
        flash('You must be logged in to book an appointment', category='error')
        return redirect(url_for("user_login"))
    
    # Check if patient profile is complete
    patient = db.session.query(Patient).get(session['patient_id'])
    if patient.phone_num is None or patient.patient_address is None:
        flash('You must complete your profile before booking an appointment.', category='warning')
        return redirect(url_for('complete_profileform'))

    if request.method == "POST":
        doctor_id = request.form.get("doctor_id")
        appointment_date = request.form.get("appointment_date")
        appointment_time = request.form.get("appointment_time")
        patient_note = request.form.get("patient_note")

        # VALIDATIONS
        if not doctor_id:
            flash("❗ Please select a doctor.", "danger")
            return redirect(url_for("book_appointment"))

        if not appointment_date:
            flash("❗ Please choose an appointment date.", "danger")
            return redirect(url_for("book_appointment"))

        if not appointment_time:
            flash("❗ Please choose a time slot.", "danger")
            return redirect(url_for("book_appointment"))

        if not patient_note:
            flash("❗ Please describe your symptoms.", "danger")
            return redirect(url_for("book_appointment"))

        # Server-side availability checks
        schedule = DoctorSchedule.query.filter_by(doctor_id=doctor_id).first()
        if not schedule:
            flash("⚠️ This doctor has not set a schedule.", "warning")
            return redirect(url_for("book_appointment"))

        # Check that the selected date is today and doctor is available today
        try:
            sel_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
            today_date = date.today()
        except Exception:
            flash("❗ Invalid date format.", "danger")
            return redirect(url_for("book_appointment"))

        # Only allow booking for today
        if sel_date != today_date:
            flash("⚠️ You can only book for today. Please select today's date.", "warning")
            return redirect(url_for("book_appointment"))

        # Check doctor's day availability
        weekday = today_date.strftime('%A').lower()  # e.g., 'monday'
        day_map = {
            'monday': schedule.monday,
            'tuesday': schedule.tuesday,
            'wednesday': schedule.wednesday,
            'thursday': schedule.thursday,
            'friday': schedule.friday,
            'saturday': schedule.saturday,
            'sunday': schedule.sunday,
        }
        if not day_map.get(weekday):
            flash(f"⚠️ Doctor is not available today ({weekday}).", "warning")
            return redirect(url_for("book_appointment"))

        # Enforce slot capacity: max_appointments_per_slot
        existing_count = Appointment.query.filter_by(
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time
        ).filter(Appointment.status != 'cancelled').count()

        max_per_slot = getattr(schedule, 'max_appointments_per_slot', 1) or 1
        if existing_count >= max_per_slot:
            flash("❗ This time slot is fully booked. Please choose another time.", "danger")
            return redirect(url_for("book_appointment"))

        # Create appointment
        new_app = Appointment(
            patient_id=session["patient_id"],
            doctor_id=doctor_id,
            patient_note=patient_note,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status="pending"
        )

        db.session.add(new_app)
        db.session.commit()

        flash("✅ Appointment booked successfully!", "success")
        return redirect(url_for("patient_appointments"))


    specialties = Specialty.query.all()
    doctors = Doctor.query.all()
    today = date.today().strftime("%Y-%m-%d")
    
    # Get all doctor schedules
    schedules = {s.doctor_id: s for s in DoctorSchedule.query.all()}
    
    # Get today's weekday name (e.g., 'monday')
    today_weekday = date.today().strftime('%A').lower()

    return render_template(
        "user/book_appointment.html",
        specialties=specialties,
        doctors=doctors,
        current_date=today,
        schedules=schedules,
        today_weekday=today_weekday
    )

@app.get('/patient/appointments/')
@profile_required
def patient_appointments():
    if session.get('patient_id') != None:
        deets = Patient.query.get(session['patient_id'])
        appointments = Appointment.query.filter_by(
            patient_id=session["patient_id"]
        ).order_by(Appointment.updated_at.desc()).all()  # Changed to updated_at
        return render_template('/user/patient_appointments.html', deets=deets, appointments=appointments)
    else:
        flash('You must be logged in to view this page', category='error')
        return redirect(url_for('user_login'))
    
@app.route('/patient/appointment/<int:id>/cancel')
@profile_required
def cancel_appointment(id):
    patient_id = session.get("patient_id")
    app = Appointment.query.get_or_404(id)

    # SECURITY: Ensure patient owns the appointment
    if app.patient_id != patient_id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('patient_appointments'))

    # Check if cancellation is allowed
    if app.status not in ["pending", "accepted"]:
        flash("This appointment cannot be cancelled.", "warning")
        return redirect(url_for('patient_appointments'))

    # Cancel it
    app.status = "cancelled"
    db.session.commit()

    flash("Appointment cancelled successfully.", "success")
    return redirect(url_for('patient_appointments'))

@app.route('/patient/appointment/<int:id>/reschedule')
@profile_required
def reschedule_appointment(id):
    patient_id = session.get("patient_id")
    app = Appointment.query.get_or_404(id)

    if app.patient_id != patient_id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('patient_appointments'))

    if app.status != "pending":
        flash("Only pending appointments can be rescheduled.", "warning")
        return redirect(url_for('patient_appointments'))

    return render_template(
        "user/reschedule_appointment.html",
        app=app
    )

@app.route('/patient/appointment/<int:id>/reschedule', methods=['POST'])
@profile_required
def save_reschedule(id):
    app = Appointment.query.get_or_404(id)

    if app.patient_id != session.get("patient_id"):
        flash("Unauthorized action.", "danger")
        return redirect(url_for('patient_appointments'))

    if app.status != "pending":
        flash("This appointment cannot be rescheduled.", "warning")
        return redirect(url_for('patient_appointments'))

    new_date = request.form.get("date")
    new_time = request.form.get("time")
    new_note = request.form.get("note")

    app.appointment_date = new_date
    app.appointment_time = new_time
    app.patient_note = new_note

    db.session.commit()

    flash("Appointment rescheduled successfully.", "success")
    return redirect(url_for('patient_appointments'))

    
@app.route("/patient/update/settings", methods=['GET', 'POST'])
@login_required
def update_patient_settings():
    form = PatientSettingsForm()
    if session.get("patient_id") != None:

        deets = Patient.query.get(session["patient_id"])

        if form.validate_on_submit():
            # Get the data from the form
            fname = form.fname.data
            lname = form.lname.data
            phone = form.phone.data
            address = form.address.data
            bio = form.bio.data
            picture = form.picture.data  # file or None

            existing_phone = Patient.query.filter(
                Patient.phone_num == phone,
                Patient.patient_id != session["patient_id"]
            ).first()
            if existing_phone:
                flash('This phone number is already registered. Please use a different phone number.', category='error')
                return render_template("user/settings.html", form=form, deets=deets)

            # If user selected a picture
            if picture:
                filename = picture.filename
                _, ext = os.path.splitext(filename)
                newname = secrets.token_hex(10) + ext
                picture.save("pkg/static/uploads/patients/" + newname)

                # Update database field
                deets.patient_profilepic = newname

            # Update all fields
            deets.patient_fname = fname
            deets.patient_lname = lname
            deets.phone_num = phone
            deets.patient_address = address
            deets.patient_bio = bio

            db.session.commit()

            flash("Profile updated successfully", category="msg")
            return redirect(url_for("update_patient_settings"))

        else:
            # Pre-populate form with existing data
            form.fname.data = deets.patient_fname
            form.lname.data = deets.patient_lname
            form.phone.data = deets.phone_num
            form.address.data = deets.patient_address
            form.bio.data = deets.patient_bio
            
            return render_template("user/settings.html", form=form, deets=deets)

    else:
        flash("You must be logged in to access this page", category="errormsg")
        return redirect(url_for("login_page"))

# @app.route('/clear_appointments/')
# def clear_appointments():
#     """Clear all appointments and reset auto-increment"""
    
#     try:
#         Appointment.query.delete()
#         db.session.commit()
        
#         # Reset auto-increment (for MySQL/MariaDB)
#         db.session.execute(db.text("ALTER TABLE appointment AUTO_INCREMENT = 1;"))
#         db.session.commit()
        
#         flash('Appointment table cleared and ID reset successfully.')
#     except Exception as e:
#         db.session.rollback()
#         flash(f'Error clearing appointments: {str(e)}')
    
#     return 'success'

@app.route("/patient/consultation/<int:id>")
@login_required
def patient_view_consultation(id):
    if session.get("patient_id") is None:
        flash("You must be logged in to view this page", category="error")
        return redirect(url_for("user_login"))

    consultation = (
        db.session.query(Consultation)
        .join(Appointment, Consultation.app_id == Appointment.app_id)
        .filter(
            Consultation.app_id == id,
            Appointment.patient_id == session["patient_id"]
        )
        .first()
    )

    if consultation is None:
        flash("Consultation not found or access denied.", category="error")
        return redirect(url_for("patient_appointments"))

    return render_template(
        "user/view_consultation.html",
        consultation=consultation
    )


@app.route("/payment/initiate/<int:consultation_id>/")
@login_required
def initiate_payment(consultation_id):
    """Initiate payment for a consultation"""
    patient_id = session.get('patient_id')
    
    # Get consultation and verify patient owns it
    consult = db.session.query(Consultation).join(Appointment).filter(
        Consultation.cun_id == consultation_id,
        Appointment.patient_id == patient_id
    ).first()
    
    if not consult:
        flash("Consultation not found or access denied.", category="error")
        return redirect(url_for("patient_appointments"))
    
    if not consult.amt:
        flash("No payment required for this consultation.", category="info")
        return redirect(url_for("patient_view_consultation", id=consult.app_id))
    
    # Check if already paid
    existing_payment = Payment.query.filter_by(
        cun_id=consultation_id,
        pay_patientid=patient_id,
        pay_status='paid'
    ).first()
    
    if existing_payment:
        flash("This consultation has already been paid for.", category="success")
        return redirect(url_for("patient_view_consultation", id=consult.app_id))
    
    # Check for existing pending payment
    pending_payment = Payment.query.filter_by(
        cun_id=consultation_id,
        pay_patientid=patient_id
    ).filter(Payment.pay_status.in_(['pending', 'failed'])).first()
    
    # If there's a pending transfer payment, delete it and create a new one with new reference
    # (Cash payments can be reused, but transfer payments need new references for Paystack)
    if pending_payment:
        if pending_payment.pay_method == 'transfer' or pending_payment.pay_method is None:
            # Delete old pending transfer payment to avoid duplicate reference error
            db.session.delete(pending_payment)
            db.session.commit()
            pending_payment = None
    
    # Generate unique reference
    ref = 'LS-' + secrets.token_hex(8).upper()
    
    # Create new payment record
    if not pending_payment:
        pending_payment = Payment(
            pay_patientid=patient_id,
            cun_id=consultation_id,
            pay_amt=consult.amt,
            pay_ref=ref,
            pay_status='pending'
        )
        db.session.add(pending_payment)
    else:
        # Reuse existing cash payment
        ref = pending_payment.pay_ref
    
    db.session.commit()
    session['pay_ref'] = ref
    
    return redirect(url_for('payment_page'))


@app.route('/payment/')
@login_required
def payment_page():
    """Payment page where patient selects payment method"""
    if session.get('patient_id') is None:
        flash("You must be logged in to view this page", category="error")
        return redirect(url_for('user_login'))
    
    if session.get('pay_ref') is None:
        flash("No payment reference found", category="error")
        return redirect(url_for('patient_dashboard'))
    
    patient = Patient.query.get(session['patient_id'])
    ref = session['pay_ref']
    payment = Payment.query.filter_by(pay_ref=ref).first()
    
    if not payment:
        flash("Payment record not found", category="error")
        return redirect(url_for('patient_dashboard'))
    
    return render_template('user/payment.html', patient=patient, payment=payment)


@app.post('/paystack/')
@login_required
def paystack_step1():
    """Initialize Paystack payment"""
    if session.get('patient_id') is None:
        flash("You must be logged in to view this page", category="error")
        return redirect(url_for('user_login'))
    
    if session.get('pay_ref') is None:
        flash("Please complete the payment form", category="error")
        return redirect(url_for('patient_dashboard'))
    
    try:
        url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer sk_test_c6e04ab768c3398440bc0a4f87ba0a03b70d19a7"
        }
        
        ref = session['pay_ref']
        payment = Payment.query.filter_by(pay_ref=ref).first()
        
        if not payment:
            flash("Payment record not found", category="error")
            return redirect(url_for('payment_page'))
        
        patient = Patient.query.get(session['patient_id'])
        amount = payment.pay_amt
        email = patient.patient_email
        
        data = {
            "amount": int(amount * 100),  # Convert to kobo
            "reference": ref,
            "email": email,
            "callback_url": "http://127.0.0.1:8888/paystack/landing"
        }
        
        rsp = requests.post(url, headers=headers, data=json.dumps(data))
        jsonrsp = rsp.json()
        
        if jsonrsp and jsonrsp.get('status') == True:
            auth_url = jsonrsp['data']['authorization_url']
            # Update payment method
            payment.pay_method = 'transfer'
            db.session.commit()
            return redirect(auth_url)
        else:
            error_msg = jsonrsp.get('message', 'Unknown error') if jsonrsp else 'No response from Paystack'
            flash(f"Payment initialization failed: {error_msg}", category="error")
            return redirect(url_for('payment_page'))
    
    except requests.exceptions.RequestException as e:
        flash(f"Network error connecting to Paystack: {str(e)}", category="error")
        return redirect(url_for('payment_page'))
    except Exception as e:
        flash(f"Error processing payment: {str(e)}", category="error")
        return redirect(url_for('payment_page'))


@app.route('/paystack/landing')
def paystack_landing():
    """Paystack will redirect the user here after payment"""
    if session.get('patient_id') is None or session.get('pay_ref') is None:
        flash("You must be logged in to view this page", category="error")
        return redirect(url_for('user_login'))
    
    try:
        ref = session['pay_ref']
        url = f"https://api.paystack.co/transaction/verify/{ref}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer sk_test_c6e04ab768c3398440bc0a4f87ba0a03b70d19a7"
        }
        
        rsp = requests.get(url, headers=headers)
        jsonrsp = rsp.json()
        
        if jsonrsp and jsonrsp.get('status') == True:
            status = 'paid'
            flash('Payment was successful!', category="success")
        else:
            status = 'failed'
            flash("Payment was not successful", category="error")
        
        # Update payment record
        payment = Payment.query.filter_by(pay_ref=ref).first()
        if payment:
            payment.pay_status = status
            payment.pay_data = jsonrsp
            db.session.commit()
            
            # Clear session ref
            session.pop('pay_ref', None)
            
            # Redirect to consultation view
            if payment.consultation:
                return redirect(url_for('patient_view_consultation', id=payment.consultation.app_id))
        
        return redirect(url_for('patient_dashboard'))
    
    except Exception as e:
        flash(f"Error verifying payment: {str(e)}", category="error")
        return redirect(url_for('patient_dashboard'))


@app.post('/payment/cash/')
@login_required
def process_cash_payment():
    """Process cash payment (mark as pending for admin verification)"""
    if session.get('patient_id') is None:
        flash("You must be logged in", category="error")
        return redirect(url_for('user_login'))
    
    if session.get('pay_ref') is None:
        flash("No payment reference found", category="error")
        return redirect(url_for('patient_dashboard'))
    
    ref = session['pay_ref']
    payment = Payment.query.filter_by(pay_ref=ref).first()
    
    if payment:
        payment.pay_method = 'cash'
        payment.pay_status = 'pending'
        db.session.commit()
        
        flash('Cash payment recorded! Please pay at the hospital reception. Show your reference number: ' + ref, category="success")
        session.pop('pay_ref', None)
        
        if payment.consultation:
            return redirect(url_for('patient_view_consultation', id=payment.consultation.app_id))
    
    return redirect(url_for('patient_dashboard'))


@app.route('/patient/payments/')
@login_required
def patient_payments():
    """View all patient payment history"""
    if session.get('patient_id') is None:
        flash("You must be logged in to view this page", category="error")
        return redirect(url_for('user_login'))
    
    patient = Patient.query.get(session['patient_id'])
    
    # Get all payments for this patient
    payments = Payment.query.filter_by(pay_patientid=session['patient_id']).order_by(Payment.pay_date.desc()).all()
    
    # Calculate summary statistics
    total_paid = sum(p.pay_amt for p in payments if p.pay_status == 'paid')
    total_pending = sum(p.pay_amt for p in payments if p.pay_status == 'pending')
    total_transactions = len(payments)
    
    return render_template(
        'user/patient_payments.html',
        deets=patient,
        payments=payments,
        total_paid=total_paid,
        total_pending=total_pending,
        total_transactions=total_transactions
    )


