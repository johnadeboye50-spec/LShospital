# Password Reset and Email Validation Fix Report

Date: 2026-06-24

This file documents what was wrong, your original code pattern, what I changed, and why.

## 1) Invalid email error in local password reset/login/register

Your issue:
- You kept seeing Invalid email address even with valid-looking emails.
- This commonly happens from input spaces/case and strict validation behavior.

Your original pattern (from forms.py):

    email = StringField('Email', validators=[DataRequired(), Email(check_deliverability=False)])

Problem in this pattern:
- It did not normalize user input before validation.
- If user enters leading/trailing spaces (example: " user@mail.com "), validation can fail.
- Case differences can also cause lookup mismatch later (example: USER@MAIL.COM vs user@mail.com).

What I changed it to:

    def normalize_email(value):
        if value is None:
            return None
        return value.strip().lower()

    email = StringField(
        'Email',
        validators=[
            DataRequired(),
            Email(check_deliverability=False, message='Please enter a valid email address.')
        ],
        filters=[normalize_email]
    )

Where applied:
- RegistrationForm.email
- LoginForm.email
- DoctorForm.email
- DoctorLoginForm.email
- PasswordResetRequestForm.email
- DoctorPasswordResetRequestForm.email

Why this fix works:
- Every submitted email is cleaned first (trim + lowercase).
- Validation now checks clean input.
- Query logic becomes more reliable with normalized values.


## 2) Password reset request looked like button not working

Your issue:
- Clicking submit stayed on the same page, so it looked like the button was broken.

Your original template pattern:

    <form method="post" action="">
        {{ reset_form.csrf_token }}

Problem in this pattern:
- action="" can still work, but explicit endpoint is safer and clearer.
- Using hidden_tag() is the recommended Flask-WTF pattern for hidden fields.

What I changed it to:

    <form method="post" action="{{ url_for('request_patient_password_reset') }}">
        {{ reset_form.hidden_tag() }}

And for doctor page:

    <form method="post" action="{{ url_for('doctor_password_reset_request') }}">
        {{ reset_form.hidden_tag() }}

Why this fix works:
- Form posts directly to the exact route.
- Hidden fields are rendered consistently.
- Removes ambiguity and improves reliability.


## 3) Reset request route could silently fail and re-render

Your original pattern (patient route):

    if reset_form.validate_on_submit():
        email = reset_form.email.data
        patient = Patient.query.filter_by(patient_email=email).first()
        ...

    return render_template('user/patient_passwordrequest.html', reset_form=reset_form)

Problem in this pattern:
- No normalization at query point.
- Validation failure path did not always explain why clearly.

What I changed it to:

    if reset_form.validate_on_submit():
        email = (reset_form.email.data or '').strip().lower()
        patient = Patient.query.filter(
            func.lower(Patient.patient_email) == email
        ).first()
        ...

    for field, errors in reset_form.errors.items():
        if errors:
            flash(errors[0], category='error')
    return render_template('user/patient_passwordrequest.html', reset_form=reset_form)

Why this fix works:
- Lookup is now case-insensitive.
- Users now get a visible reason when validation fails.

Same logic was applied for doctor password reset request.


## 4) Doctor reset link endpoint mismatch (caused server error)

Your original code:

    reset_link = url_for('reset_doctor_password', token=token, _external=True)

Problem:
- Endpoint name did not match the actual function name.

Changed to:

    reset_link = url_for('doctor_password_reset', token=token, _external=True)

Why this fix works:
- The reset URL now points to an existing Flask endpoint.


## 5) View function returned None in reset POST flow

Your original pattern in reset handlers:
- POST branch returned only on successful validate_on_submit().
- Failed validation could reach end of function without return.

Changed to:
- Added explicit fallback return of reset template when validation fails.

Why this fix works:
- Flask always gets a valid response object.


## Files changed

- pkg/forms.py
- pkg/patient_routes.py
- pkg/doctor_route.py
- pkg/templates/user/patient_passwordrequest.html
- pkg/templates/doctors/doctor_passwordrequest.html


## 6) Render production error after requesting reset link

Your Render error:
- `sqlalchemy.exc.ProgrammingError`
- `column patient.password_reset_token does not exist`

What this means:
- Your application code on Render includes the new password reset fields.
- But the Render PostgreSQL database schema does not yet match that code.
- So SQLAlchemy tries to select `patient.password_reset_token`, and Postgres fails because that column is missing.

Important:
- This is not a form/button problem.
- This is not an email validation problem.
- This is a production database migration problem.

What already existed:

    migrations/versions/5f24f8acde9f_aded_password_rest_columns_to_doctor_.py

What I added as a defensive fix:

    migrations/versions/8b9e6f1a2c4d_fix_missing_password_reset_columns.py

Why I added it:
- If Render's migration history is out of sync with the actual database schema, this new migration checks whether each password reset column exists before adding it.
- That makes deployment more resilient.

Columns ensured by this migration:
- `patient.password_reset_token`
- `patient.password_reset_expires_at`
- `doctor.password_reset_token`
- `doctor.password_reset_expires_at`

Expected result after deploy:
- Render runs the migration.
- Missing reset columns get created.
- Password reset request should stop crashing with 500.


## What to test now

1. Enter email with spaces before/after and submit reset request.
2. Enter uppercase email and submit reset request.
3. Test both patient and doctor reset request pages.
4. Confirm you get either success flash or clear error flash, not silent refresh.
