from functools import wraps
from flask import render_template, url_for,request,flash, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash

from pkg import app
import re
from pkg.forms import AdminLoginForm, DepartmentForm, SpecialtyForm, AdminPasswordChangeForm
from pkg.models import db, Admin, Patient, Doctor, Appointment, Consultation, Payment, Department, Specialty
from sqlalchemy import func
from datetime import datetime, timedelta

def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('adminonline') != None:
            return f(*args, **kwargs)
        else:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('admin_login'))
    return decorated_function

@app.route('/admin/login/', methods=['GET','POST'])
def admin_login():
    logform = AdminLoginForm()
    # If already logged in, go to dashboard
    if session.get('adminonline'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'GET':
        return render_template('admin/admin_login.html', logform=logform)
    else:
        if logform.validate_on_submit():
            username = logform.username.data
            password = logform.password.data
            admin_deets = Admin.query.filter(Admin.admin_username==username).first()
            if admin_deets:
                stored = admin_deets.admin_password
                chk = check_password_hash(stored, password)
                if chk:
                    session['adminonline'] = admin_deets.admin_id
                    flash('Login successful!', 'success')
                    return redirect(url_for('admin_dashboard'))
                else:
                    flash('Invalid login', category='adminmsg')
                    return redirect(url_for('admin_login'))
            else:
                flash('Invalid login, check username', category='adminmsg')
                return redirect(url_for('admin_login'))
        # Failed validation: re-render form
        return render_template('admin/admin_login.html', logform=logform)
    
@app.route('/admin/dashboard/')
@admin_login_required
def admin_dashboard():
    # Count totals
    total_patients = Patient.query.count()
    total_doctors = Doctor.query.count()
    total_appointments = Appointment.query.count()
    total_departments = Department.query.count()
    total_specialties = Specialty.query.count()
    
    # Active/Inactive doctors
    active_doctors = Doctor.query.filter_by(doctor_status='active').count()
    inactive_doctors = Doctor.query.filter_by(doctor_status='inactive').count()
    
    # Appointment statistics
    pending_appointments = Appointment.query.filter_by(status='pending').count()
    accepted_appointments = Appointment.query.filter_by(status='accepted').count()
    completed_appointments = Appointment.query.filter_by(status='completed').count()
    cancelled_appointments = Appointment.query.filter_by(status='cancelled').count()
    declined_appointments = Appointment.query.filter_by(status='declined').count()
    
    # Payment statistics
    total_revenue = db.session.query(func.sum(Payment.pay_amt)).filter_by(pay_status='paid').scalar() or 0
    pending_payments = Payment.query.filter_by(pay_status='pending').count()
    paid_payments = Payment.query.filter_by(pay_status='paid').count()
    failed_payments = Payment.query.filter_by(pay_status='failed').count()
    
    # Cash vs Transfer payments
    cash_payments = Payment.query.filter_by(pay_method='cash', pay_status='paid').count()
    transfer_payments = Payment.query.filter_by(pay_method='transfer', pay_status='paid').count()
    
    # Recent appointments (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_appointments = Appointment.query.filter(
        Appointment.created_at >= seven_days_ago
    ).count()
    
    # Recent patients (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_patients = Patient.query.filter(
        Patient.patient_regdate >= thirty_days_ago
    ).count()
    
    # Recent doctors (last 30 days)
    new_doctors = Doctor.query.filter(
        Doctor.doctor_regdate >= thirty_days_ago
    ).count()
    
    # Top 5 departments by doctor count
    top_departments = db.session.query(
        Department.department_name,
        func.count(Doctor.doctor_id).label('doctor_count')
    ).join(Doctor).group_by(Department.department_id).order_by(
        func.count(Doctor.doctor_id).desc()
    ).limit(5).all()
    
    # Top 5 specialties by doctor count
    top_specialties = db.session.query(
        Specialty.specialty_name,
        func.count(Doctor.doctor_id).label('doctor_count')
    ).join(Doctor).group_by(Specialty.specialty_id).order_by(
        func.count(Doctor.doctor_id).desc()
    ).limit(5).all()
    
    # Latest 10 appointments
    latest_appointments = Appointment.query.order_by(
        Appointment.created_at.desc()
    ).limit(10).all()
    
    # Current date for template
    current_date = datetime.utcnow()
    
    return render_template('admin/admin_dashboard.html',
                         total_patients=total_patients,
                         total_doctors=total_doctors,
                         total_appointments=total_appointments,
                         total_departments=total_departments,
                         total_specialties=total_specialties,
                         active_doctors=active_doctors,
                         inactive_doctors=inactive_doctors,
                         pending_appointments=pending_appointments,
                         accepted_appointments=accepted_appointments,
                         completed_appointments=completed_appointments,
                         cancelled_appointments=cancelled_appointments,
                         declined_appointments=declined_appointments,
                         total_revenue=total_revenue,
                         pending_payments=pending_payments,
                         paid_payments=paid_payments,
                         failed_payments=failed_payments,
                         cash_payments=cash_payments,
                         transfer_payments=transfer_payments,
                         recent_appointments=recent_appointments,
                         new_patients=new_patients,
                         new_doctors=new_doctors,
                         top_departments=top_departments,
                         top_specialties=top_specialties,
                         latest_appointments=latest_appointments,
                         current_date=current_date)

@app.route('/admin/logout/')
@admin_login_required
def admin_logout():
    session.pop('adminonline', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin/setup/')
def admin_setup():
    # Create the admin account
    admin = Admin(
        admin_username='admin',
        admin_password=generate_password_hash('lsadmin1')
    )
    db.session.add(admin)
    db.session.commit()
    
    return "Admin account created successfully! Username: admin, Password: lsadmin1. You can now <a href='/admin/login/'>login</a>."

# Department Routes
@app.route('/admin/departments/', methods=['GET', 'POST'])
@admin_login_required
def admin_departments():
    form = DepartmentForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        raw_input = form.department_name.data or ''
        # Allow multiple names separated by commas or new lines
        parts = [p.strip() for p in re.split(r'[\n\r,]+', raw_input) if p and p.strip()]

        if not parts:
            flash('Please enter at least one department name.', 'warning')
            return redirect(url_for('admin_departments'))

        # Deduplicate input preserving order (case-insensitive)
        seen = set()
        names = []
        for p in parts:
            key = p.lower()
            if key not in seen:
                seen.add(key)
                names.append(p)

        # Existing departments
        existing_lower = {d.department_name.lower() for d in Department.query.all() if d.department_name}
        to_create = [n for n in names if n.lower() not in existing_lower]
        skipped = [n for n in names if n.lower() in existing_lower]

        if not to_create:
            flash('No new departments to add. All provided names already exist.', 'warning')
            return redirect(url_for('admin_departments'))

        try:
            for name in to_create:
                db.session.add(Department(department_name=name))
            db.session.commit()
            msg = f"Added {len(to_create)} department(s)."
            if skipped:
                msg += f" Skipped {len(skipped)} existing: {', '.join(skipped[:5])}{'…' if len(skipped) > 5 else ''}."
            flash(msg, 'success')
        except Exception:
            db.session.rollback()
            flash('Error adding departments. Please try again.', 'error')
        return redirect(url_for('admin_departments'))
    
    # Get all departments
    departments = Department.query.all()
    
    return render_template('admin/admin_department.html', form=form, departments=departments)

@app.route('/admin/departments/edit/<int:dept_id>/', methods=['GET', 'POST'])
@admin_login_required
def admin_edit_department(dept_id):
    department = Department.query.get_or_404(dept_id)
    form = DepartmentForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        new_name = form.department_name.data
        
        # Check if new name already exists (excluding current department)
        existing = Department.query.filter(
            Department.department_name == new_name,
            Department.department_id != dept_id
        ).first()
        
        if existing:
            flash('Department name already exists!', 'warning')
            return redirect(url_for('admin_edit_department', dept_id=dept_id))
        
        # Update department
        department.department_name = new_name
        try:
            db.session.commit()
            flash('Department updated successfully!', 'success')
            return redirect(url_for('admin_departments'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating department. Please try again.', 'error')
            return redirect(url_for('admin_edit_department', dept_id=dept_id))
    
    # Pre-populate form
    if request.method == 'GET':
        form.department_name.data = department.department_name
    
    return render_template('admin/admin_edit_department.html', form=form, department=department)

@app.route('/admin/departments/delete/<int:dept_id>/', methods=['POST'])
@admin_login_required
def admin_delete_department(dept_id):
    department = Department.query.get_or_404(dept_id)
    
    # Check if department has doctors
    doctor_count = Doctor.query.filter_by(department_id=dept_id).count()
    if doctor_count > 0:
        flash(f'Cannot delete department. {doctor_count} doctor(s) are assigned to this department.', 'warning')
        return redirect(url_for('admin_departments'))
    
    try:
        db.session.delete(department)
        db.session.commit()
        flash('Department deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting department. Please try again.', 'error')
    
    return redirect(url_for('admin_departments'))

# Specialty Routes
@app.route('/admin/specialties/', methods=['GET', 'POST'])
@admin_login_required
def admin_specialties():
    form = SpecialtyForm()
    if request.method == 'POST' and form.validate_on_submit():
        raw_input = form.specialty_name.data or ''
        parts = [p.strip() for p in re.split(r'[\n\r,]+', raw_input) if p and p.strip()]
        if not parts:
            flash('Please enter at least one specialty name.', 'warning')
            return redirect(url_for('admin_specialties'))
        seen = set(); names = []
        for p in parts:
            key = p.lower()
            if key not in seen:
                seen.add(key); names.append(p)
        existing_lower = {s.specialty_name.lower() for s in Specialty.query.all() if s.specialty_name}
        to_create = [n for n in names if n.lower() not in existing_lower]
        skipped = [n for n in names if n.lower() in existing_lower]
        if not to_create:
            flash('No new specialties to add. All provided names already exist.', 'warning')
            return redirect(url_for('admin_specialties'))
        try:
            for name in to_create:
                db.session.add(Specialty(specialty_name=name))
            db.session.commit()
            msg = f"Added {len(to_create)} specialty(s)."
            if skipped:
                msg += f" Skipped {len(skipped)} existing: {', '.join(skipped[:5])}{'…' if len(skipped) > 5 else ''}."
            flash(msg, 'success')
        except Exception:
            db.session.rollback()
            flash('Error adding specialties. Please try again.', 'error')
        return redirect(url_for('admin_specialties'))
    specialties = Specialty.query.all()
    return render_template('admin/admin_specialties.html', form=form, specialties=specialties)

@app.route('/admin/specialties/edit/<int:spec_id>/', methods=['GET', 'POST'])
@admin_login_required
def admin_edit_specialty(spec_id):
    specialty = Specialty.query.get_or_404(spec_id)
    form = SpecialtyForm()
    if request.method == 'POST' and form.validate_on_submit():
        new_name = form.specialty_name.data
        existing = Specialty.query.filter(
            Specialty.specialty_name == new_name,
            Specialty.specialty_id != spec_id
        ).first()
        if existing:
            flash('Specialty name already exists!', 'warning')
            return redirect(url_for('admin_edit_specialty', spec_id=spec_id))
        specialty.specialty_name = new_name
        try:
            db.session.commit()
            flash('Specialty updated successfully!', 'success')
            return redirect(url_for('admin_specialties'))
        except Exception:
            db.session.rollback()
            flash('Error updating specialty. Please try again.', 'error')
            return redirect(url_for('admin_edit_specialty', spec_id=spec_id))
    if request.method == 'GET':
        form.specialty_name.data = specialty.specialty_name
    return render_template('admin/admin_edit_specialty.html', form=form, specialty=specialty)

@app.route('/admin/specialties/delete/<int:spec_id>/', methods=['POST'])
@admin_login_required
def admin_delete_specialty(spec_id):
    specialty = Specialty.query.get_or_404(spec_id)
    doctor_count = Doctor.query.filter_by(specialty_id=spec_id).count()
    if doctor_count > 0:
        flash(f'Cannot delete specialty. {doctor_count} doctor(s) are assigned to this specialty.', 'warning')
        return redirect(url_for('admin_specialties'))
    try:
        db.session.delete(specialty)
        db.session.commit()
        flash('Specialty deleted successfully!', 'success')
    except Exception:
        db.session.rollback()
        flash('Error deleting specialty. Please try again.', 'error')
    return redirect(url_for('admin_specialties'))


@app.route('/admin/appointments/')
@admin_login_required
def admin_appointments():
    appointments = Appointment.query.order_by(
        Appointment.created_at.desc()
    ).all()

    return render_template('admin/admin_appointments.html', appointments=appointments)

@app.route('/admin/doctors/')
@admin_login_required
def admin_doctors():
    doctors = Doctor.query.order_by(Doctor.doctor_regdate.desc()).all()
    total_doctors = Doctor.query.count()
    active_doctors = Doctor.query.filter_by(doctor_status='active').count()
    inactive_doctors = Doctor.query.filter_by(doctor_status='inactive').count()
    
    return render_template('admin/admin_doctors.html', 
                         doctors=doctors,
                         total_doctors=total_doctors,
                         active_doctors=active_doctors,
                         inactive_doctors=inactive_doctors)

@app.route('/admin/doctors/delete/<int:doctor_id>/', methods=['POST'])
@admin_login_required
def admin_delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    

    appointment_count = Appointment.query.filter_by(doctor_id=doctor_id).count()
    if appointment_count > 0:
        flash(f'Cannot delete doctor. {appointment_count} appointment(s) are assigned to this doctor.', 'warning')
        return redirect(url_for('admin_doctors'))
    
    try:
        db.session.delete(doctor)
        db.session.commit()
        flash('Doctor deleted successfully!', 'success')
    except Exception:
        db.session.rollback()
        flash('Error deleting doctor. Please try again.', 'error')
    
    return redirect(url_for('admin_doctors'))


@app.route('/admin/patients/')
@admin_login_required
def admin_patients():
    patients = Patient.query.order_by(Patient.patient_regdate.desc()).all()
    total_patients = Patient.query.count()
    
    return render_template('admin/admin_patient.html',patients=patients,total_patients=total_patients)

@app.route('/admin/settings/', methods=['GET', 'POST'])
@admin_login_required
def admin_settings():
    form = AdminPasswordChangeForm()
    admin_id = session.get('adminonline')
    admin = Admin.query.get_or_404(admin_id)
    
    if request.method == 'POST' and form.validate_on_submit():
        current_password = form.current_password.data
        new_password = form.new_password.data

        if not check_password_hash(admin.admin_password, current_password):
            flash('Current password is incorrect!', 'danger')
            return redirect(url_for('admin_settings'))

        admin.admin_password = generate_password_hash(new_password)
        try:
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('admin_settings'))
        except Exception:
            db.session.rollback()
            flash('Error changing password. Please try again.', 'error')
            return redirect(url_for('admin_settings'))
    
    return render_template('admin/admin_settings.html', form=form, admin=admin)
