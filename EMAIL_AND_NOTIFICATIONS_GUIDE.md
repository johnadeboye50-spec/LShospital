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
Added in patient routes:
- `generate_email_token()` creates a secure random token.
- `send_email()` sends a basic email via SMTP.
- `send_verification_email()` creates a token + expiry, stores them, and emails a link.

Why: Keeps the verification flow centralized and reusable.

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

## 9) Common Errors
- SMTP not configured → email won’t send. You’ll see a warning flash.
- Token expired → user must resend verification.

## 10) Next Steps (Recommended)
- Add a simple “Resend verification” button on the login page.
- Create a background job (Celery or RQ) for sending emails asynchronously.
- Add rate-limiting to resend endpoint.
- Implement SMS verification if needed.
