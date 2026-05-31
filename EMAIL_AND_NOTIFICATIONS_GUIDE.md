# Email Verification and Notifications Guide

This guide explains how email verification works in this project, why each part exists, and how to extend it to SMS or real-world providers.

## 1) Goal
- Prevent logins with unverified/fake emails.
- Require users to confirm they own the email address.
- Keep the flow simple and production-friendly.

## 2) What Was Added
### Model fields (patient)
New columns in the Patient table:
- `email_verified` (bool): whether the email is confirmed.
- `email_verified_at` (datetime): when it was confirmed.
- `email_verification_token` (string): the random token in the verification link.
- `email_verification_expires_at` (datetime): expiration time for the token.

Why: This lets us block login until confirmation and safely expire tokens.

### Email helper functions
Added in `pkg/auth_utils.py` and used by patient routes:
- `generate_email_token()` creates a secure random token.
- `send_email()` sends a basic email via SMTP.
- `send_verification_message()` sends the verification email body.
- `send_password_reset_message()` is also available for future password reset flows.

Why: This keeps email logic in one place so patient and doctor verification can both reuse the same code.

### Shared helper update
- `pkg/auth_utils.py` now centralizes email and token helper code.
- `patient_routes.py` now imports `generate_email_token()` and `send_verification_message()` instead of defining them locally.
- This means if you later add doctor verification, doctor routes can import the same helpers too.

### Doctor email verification notes
If you want doctor email verification, you only need to:
1. Add the same email verification fields to `Doctor` in `pkg/models.py`.
2. Create doctor-specific verification routes in `pkg/doctor_route.py`.
3. Use `generate_email_token()` and `send_verification_message()` from `pkg.auth_utils.py`.

That keeps the email message format and SMTP logic shared, while the route names and user model are doctor-specific.

### Routes
- `GET /patient/verify-email/<token>`
  - Validates token and expiry.
  - Marks email as verified.
  - Clears token and expiry.

- `GET/POST /patient/resend-verification`
  - Re-sends a verification link if the email exists and is not verified.

### Login behavior
- If email/password is correct BUT `email_verified` is false, login is blocked and user is redirected to resend verification.

## 3) How It Works (Flow)
1. User registers.
2. System generates a token and stores it with an expiry.
3. System emails a verification link.
4. User clicks link to verify.
5. After verification, login succeeds.

This is a standard real-world pattern used by most web apps.

## 4) Email Setup (SMTP)
The email sender uses environment variables:
- `SMTP_HOST`
- `SMTP_PORT` (default 587)
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_USE_TLS` (true/false)

Example (Render or local env):
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM="LS Hospital <your_email@gmail.com>"
SMTP_USE_TLS=true
```

Important: For Gmail, you must use an App Password (not your normal password).

## 5) Migrations
Because new columns were added, you must run:
```
flask db migrate -m "Add patient email verification fields"
flask db upgrade
```

## 6) SMS Verification (Optional, Real-World)
Email verification is step one. To support phone verification:

### Option A: Twilio (most common)
- Create a Twilio account.
- Buy a phone number.
- Use Twilio Verify API.

Flow:
1. User enters phone number.
2. Twilio sends SMS OTP.
3. User enters OTP.
4. Server verifies OTP with Twilio.

### Option B: Termii / Africa’s Talking
- Similar flow, often cheaper in some regions.

## 7) Why Not “Only Gmail”
Limiting to Gmail doesn’t prove the email is real. Verification does.
You can still restrict domains if needed (e.g., only `@gmail.com`), but verification is the real safety measure.

## 8) Files Changed
- Models: `pkg/models.py`
- Patient auth: `pkg/patient_routes.py`
- Shared email helpers: `pkg/auth_utils.py`

> Note: No new Python virtual environment was created. Only a shared helper file was added.

## 9) Common Errors
- SMTP not configured → email won’t send. You’ll see a warning flash.
- Token expired → user must resend verification.

## 10) Next Steps (Recommended)
- Add a simple “Resend verification” button on the login page.
- Create a background job (Celery or RQ) for sending emails asynchronously.
- Add rate-limiting to resend endpoint.
- Implement SMS verification if needed.

## 11) Detailed Code Walkthrough (patient_routes.py)

To help you learn by reading the actual code we inserted/changed, the
following sections reproduce every relevant block from `pkg/patient_routes.py`.
Each snippet notes the approximate line numbers in the version you have and
includes a teacher-style explanation of why it exists and what it does.

### 11.1 – Imports added at the top (lines 1–13)
```python
from datetime import date, datetime, timedelta     # datetime tools for
                                                  # timestamps and expiry
from functools import wraps                       # decorator helper used
                                                  # later for login_required
import secrets, os, requests, json, smtplib        # `secrets` for tokens,
                                                  # `smtplib` for SMTP
from email.message import EmailMessage             # convenient email object
from werkzeug.utils import secure_filename
from flask import redirect, render_template,
    request, session, url_for, jsonify, flash      # normal Flask imports
from werkzeug.security import generate_password_hash, check_password_hash
from pkg import app
from pkg.forms import LoginForm, RegistrationForm,CompleteProfileForm,PatientSettingsForm
from pkg.models import db,Doctor,Patient,Payment,
    Consultation,Specialty,Appointment,DoctorSchedule
from markupsafe import escape
```
> **Explanation:**
> - The new imports (`secrets`, `smtplib`, `EmailMessage`) are solely for the
>   email verification flow. `secrets` generates unguessable tokens.  `smtplib`
>   and `EmailMessage` let us connect to an SMTP server and compose/send
>   messages.  The other imports were already in the file; we just keep them
>   here for context.

### 11.2 – Helper functions (lines 20–80)
These three functions live immediately after the imports.

```python

def generate_email_token():
    return secrets.token_urlsafe(32)


def send_email(to_email, subject, body):
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    sender = os.environ.get("SMTP_FROM") or user
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"

    if not host or not user or not password or not sender:
        app.logger.warning("SMTP not configured. Email not sent.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port) as server:
            if use_tls:
                server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as exc:
        app.logger.error(f"Email send failed: {exc}")
        return False


def send_verification_email(patient):
    token = generate_email_token()
    patient.email_verification_token = token
    patient.email_verification_expires_at = datetime.utcnow() + timedelta(hours=24)
    db.session.commit()

    verify_link = url_for("verify_patient_email", token=token, _external=True)
    body = (
        "Welcome to LS Hospital.\n\n"
        "Please verify your email address by clicking the link below:\n"
        f"{verify_link}\n\n"
        "This link expires in 24 hours."
    )

    return send_email(patient.patient_email, "Verify your email", body)
```
> **Why these functions?**
> - `generate_email_token` produces a 32‑byte URL‑safe random string.  The
>   longer and more random the token, the harder it is for attackers to guess.
> - `send_email` is a thin wrapper around Python’s built‑in SMTP client.  It
>   reads configuration from environment variables, constructs an `EmailMessage`,
>   negotiates TLS, logs in, and sends the message.  Logging and return values
>   make debugging easier when emails fail.
> - `send_verification_email` ties everything together: it generates the token,
>   stores it and an expiration timestamp on the patient record, commits those
>   changes, builds a link using `url_for(..., _external=True)` so the full URL
>   is sent, and finally calls `send_email`.

### 11.3 – Login route modification (lines 130–170)
Inside `user_login()`, we added a check after password verification:

```python
                if chk == True:
                    if not record.email_verified:
                        flash("Please verify your email before logging in.", category='error')
                        return redirect(url_for('resend_patient_verification', email=record.patient_email))
                    session['patient_id'] = userid
                    return redirect(url_for('patient_dashboard'))
```
> **What changed and why?**
> - Before allowing the session cookie to be set we look at
>   `record.email_verified`.  If it’s `False` we redirect the user to the
>   “resend verification” endpoint, passing their email as a query parameter.
>   This prevents unverified accounts from accessing any authenticated pages.
>   The flash message informs them what they must do.

### 11.4 – Registration route changes (lines 170–210)
When the patient object is created we ensure that `email_verified=False` and
immediately attempt to send the verification email:

```python
            patient = Patient(
                patient_fname=first_name,
                patient_lname=last_name,
                patient_email=email,
                patient_password=to_bestored,
                email_verified=False
            )
            
            try:
                db.session.add(patient)
                db.session.commit()
                send_ok = send_verification_email(patient)
                if send_ok:
                    flash('Registration successful. Please check your email to verify your account.', category='success')
                else:
                    flash('Registration successful, but email could not be sent. Please contact support.', category='warning')
                return redirect(url_for('user_login'))
```
> **Why these changes?**
> - New accounts start unverified by default, so the login check above knows to
>   block them.
> - After committing the new patient we call `send_verification_email` and
>   flash different messages depending on whether the SMTP send succeeded.  The
>   warning message handles the case where configuration is missing (which you
>   saw earlier) while still creating the user.

### 11.5 – Verification endpoint (lines 240–280)
This new route lives just after the registration logic:

```python
@app.get('/patient/verify-email/<token>')
def verify_patient_email(token):
    if not token:
        flash('Invalid verification link.', category='error')
        return redirect(url_for('user_login'))

    patient = Patient.query.filter_by(email_verification_token=token).first()
    if not patient:
        flash('Verification link is invalid or expired.', category='error')
        return redirect(url_for('user_login'))

    if patient.email_verified:
        flash('Email already verified. Please log in.', category='info')
        return redirect(url_for('user_login'))

    if patient.email_verification_expires_at and patient.email_verification_expires_at < datetime.utcnow():
        flash('Verification link expired. Please request a new one.', category='warning')
        return redirect(url_for('resend_patient_verification', email=patient.patient_email))

    patient.email_verified = True
    patient.email_verified_at = datetime.utcnow()
    patient.email_verification_token = None
    patient.email_verification_expires_at = None
    db.session.commit()

    flash('Email verified successfully. You can now log in.', category='success')
    return redirect(url_for('user_login'))
```
> **Step-by-step:**
> 1. Ensure a token was supplied.
> 2. Look up the patient by the token – if not found it’s either invalid or
>    already consumed/expired.
> 3. If the account was already verified, inform the user instead of fiddling
>    with the database.
> 4. Check expiration time to prevent reuse of old links.
> 5. Mark the flags/columns on the record and clear the token fields to avoid
>    replay attacks.
> 6. Commit the change and flash success.

### 11.6 – Resend verification route (lines 280–340)
Finally, the helper to issue a fresh email when the link has expired:

```python
@app.route('/patient/resend-verification', methods=['GET', 'POST'])
def resend_patient_verification():
    if request.method == 'GET':
        email = (request.args.get('email') or '').strip()
    else:
        email = (request.form.get('email') or '').strip()

    if not email:
        flash('Please provide your email address.', category='error')
        return redirect(url_for('user_login'))

    patient = Patient.query.filter_by(patient_email=email).first()
    if not patient:
        flash('No patient account found with that email.', category='error')
        return redirect(url_for('user_login'))

    if patient.email_verified:
        flash('Email already verified. Please log in.', category='info')
        return redirect(url_for('user_login'))

    send_ok = send_verification_email(patient)
    if send_ok:
        flash('Verification email sent. Please check your inbox.', category='success')
    else:
        flash('Email could not be sent. Please contact support.', category='warning')

    return redirect(url_for('user_login'))
```
> **Explanation:**
> - Accepts either a query parameter (when coming from the login block) or a
>   form post (if you build a simple HTML page to let users type their email).
> - Verifies the address belongs to an existing, unverified patient.
> - Calls the same `send_verification_email` helper, meaning the token/expiry
>   logic is reused.
> - Flashes outcome and redirects back to the login page.

Now that you've studied the complete patient-side implementation you should
feel comfortable replicating the same steps for doctors (or any other user
model). The four model columns, the three helpers, and the three new/modified
routes are exactly what you need to copy into `doctor_route.py` and adjust the
variable names accordingly.

---

(End of guide)

