# Password Reset Guide

This guide explains how password reset should work in this project, why each part exists, and how to implement it safely.

## 1) Goal
- Let users recover access to their account if they forget their password.
- Keep the flow secure by using a one-time token that expires.
- Avoid exposing the current password in any way.

## 2) What Should Be Added

### Model fields
Add these fields to the user model you want to support (patient or doctor):
- `password_reset_token` (string): random token placed in the reset link.
- `password_reset_expires_at` (datetime): when the token expires.

Why:
- The token is what proves the user owns the email account.
- Expiry prevents old links from being reused forever.

### Helper function reuse
The project already has a reusable email helper in `pkg/auth_utils.py`:
- `send_password_reset_message(to_email, reset_link, expiry_hours=1)`

This means you do not need to build new email logic from scratch. You only need to:
1. Generate a token.
2. Store it on the user record.
3. Build the reset link.
4. Send it with `send_password_reset_message()`.

## 3) Recommended Flow
1. User clicks “Forgot Password”.
2. User enters their email.
3. If the email exists, server generates a reset token and stores it.
4. Server emails a reset link.
5. User clicks link and lands on a reset form.
6. User enters a new password.
7. Server validates the token, updates the password, and clears the token.

This is the standard secure pattern used by most web apps.

## 4) Suggested Routes
You will usually need these routes:

- `GET/POST /patient/forgot-password` or `/doctor/forgot-password`
  - Accepts email.
  - Creates token and sends reset email.

- `GET /patient/reset-password/<token>`
  - Shows the reset form if the token is valid.

- `POST /patient/reset-password/<token>`
  - Validates the token.
  - Updates the password.
  - Clears the token.

## 5) How It Works

### Step 1: Generate the token
Use a secure random token:

```python
import secrets

def generate_password_reset_token():
    return secrets.token_urlsafe(32)
```

### Step 2: Store token + expiry
When the reset request is submitted:

```python
user.password_reset_token = token
user.password_reset_expires_at = datetime.utcnow() + timedelta(hours=1)
db.session.commit()
```

### Step 3: Build the reset link
Use the token in a URL:

```python
reset_link = url_for('reset_patient_password', token=token, _external=True)
```

### Step 4: Send email
Use the existing helper:

```python
send_password_reset_message(user.patient_email, reset_link, expiry_hours=1)
```

### Step 5: Validate when user opens the link
On the reset route:

```python
user = Patient.query.filter_by(password_reset_token=token).first()

if not user:
    flash('Invalid or expired reset link.', category='error')
    return redirect(url_for('user_login'))

if user.password_reset_expires_at and user.password_reset_expires_at < datetime.utcnow():
    flash('Reset link has expired. Please request a new one.', category='error')
    return redirect(url_for('forgot_password'))
```

### Step 6: Update password
After the user submits the new password:

```python
user.password_reset_token = None
user.password_reset_expires_at = None
user.patient_password = generate_password_hash(new_password)
db.session.commit()
```

## 6) Security Notes
- Never store the password in plain text.
- Always hash the new password with `generate_password_hash()`.
- Always invalidate the token after use.
- Expire tokens after a short time, usually 1 hour.
- Do not reveal whether an email exists or not in a way that helps attackers.

A safer user message is:
- “If an account exists for that email, a reset link has been sent.”

## 7) Recommended Files to Update
- `pkg/models.py` → add reset token fields
- `pkg/auth_utils.py` → reuse the email helper
- `pkg/patient_routes.py` → add forgot/reset password routes
- `pkg/doctor_route.py` → do the same for doctors if needed
- templates → add forgot-password and reset-password forms

## 8) Example Patient Flow

### Forgot password route
```python
@app.route('/patient/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        patient = Patient.query.filter_by(patient_email=email).first()

        if patient:
            token = generate_email_token()
            patient.password_reset_token = token
            patient.password_reset_expires_at = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            reset_link = url_for('reset_patient_password', token=token, _external=True)
            send_password_reset_message(patient.patient_email, reset_link, expiry_hours=1)

        flash('If an account exists for that email, a reset link has been sent.', category='info')
        return redirect(url_for('user_login'))

    return render_template('user/forgot_password.html')
```

### Reset password route
```python
@app.route('/patient/reset-password/<token>', methods=['GET', 'POST'])
def reset_patient_password(token):
    patient = Patient.query.filter_by(password_reset_token=token).first()

    if not patient:
        flash('Invalid or expired reset link.', category='error')
        return redirect(url_for('user_login'))

    if patient.password_reset_expires_at and patient.password_reset_expires_at < datetime.utcnow():
        flash('Reset link has expired. Please request a new one.', category='error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        if new_password:
            patient.patient_password = generate_password_hash(new_password)
            patient.password_reset_token = None
            patient.password_reset_expires_at = None
            db.session.commit()
            flash('Your password was updated successfully.', category='success')
            return redirect(url_for('user_login'))

    return render_template('user/reset_password.html', token=token)
```

## 9) Why This Is Better Than Plain Email
A password reset link is safer than sending the old password because:
- the user proves they control the email inbox
- the password is not exposed in email
- the link can be expired and single-use

## 10) Common Mistakes to Avoid
- Forgetting to clear the token after use
- Not checking token expiry
- Sending the new password in plain text
- Using a token that is too short or predictable
- Forgetting to hash the new password

## 11) Next Steps
- Add a forgot-password page for patients.
- Add a similar flow for doctors.
- Optionally make the reset token one-time use.
- Add rate limiting so reset requests cannot be abused.

---

(End of guide)
