# IRCTC Seat Tracker

Automated IRCTC seat availability monitoring with email alerts, user accounts, and a live dashboard.

---

## Features

| Feature | Details |
|---|---|
| **Auto Monitoring** | APScheduler checks every 60 minutes |
| **Smart Thresholds** | Absolute count OR percentage-drop logic |
| **Maintenance Window** | Skips 11:30 PM – 12:30 AM IST automatically |
| **Email Alerts** | Beautiful HTML emails via SMTP |
| **User Accounts** | Register/Login/Logout with Flask-Login |
| **Email Verification** | Token-based, 1-hour TTL |
| **Password Reset** | Secure token-based flow |
| **SQLite DB** | SQLAlchemy ORM — zero setup required |

---

## Project Structure

```
irctc_tracker/
├── run.py                  # Entry point
├── app.py                  # Flask factory + APScheduler setup
├── config.py               # All config (keys, SMTP, DB, timing)
├── models.py               # User, Token, TrackingTask, NotificationLog
├── requirements.txt
├── .env.example            # Template — copy to .env and fill
├── routes/
│   ├── auth.py             # Register/Login/Verify/Reset
│   ├── main.py             # Dashboard
│   ├── tasks.py            # CRUD for tracking tasks
│   └── api.py              # Station autocomplete endpoint
├── services/
│   ├── rail_api.py         # RapidAPI wrapper (seat availability, train info)
│   ├── email_service.py    # smtplib email sender (verification + alerts)
│   └── worker.py           # APScheduler job + maintenance window logic
└── templates/
    ├── base.html
    ├── index.html
    ├── dashboard.html
    ├── auth/               # login, register, forgot/reset password, resend verify
    └── tasks/              # new_task, task_detail
```

---

## Quick Start

### 1. Install dependencies

```bash
cd <name-irctc-tracker>
pip install -r requirements.txt
```

### 2. Get a RapidAPI key

1. Go to https://rapidapi.com/IRCTC1/api/indian-railway-irctc
2. Click **Subscribe** (free tier available)
3. Copy your `X-RapidAPI-Key`

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your values:
#   RAPIDAPI_KEY, MAIL_USERNAME, MAIL_PASSWORD, SECRET_KEY
```

Or export variables directly:

```bash
export RAPIDAPI_KEY="your_key"
export MAIL_USERNAME="you@gmail.com"
export MAIL_PASSWORD="your_app_password"
export SECRET_KEY="something-long-and-random"
```

### 4. Gmail App Password (required for SMTP)

1. Enable 2FA on your Google account
2. Go to https://myaccount.google.com/apppasswords
3. Create an app password for "Mail"
4. Use that 16-character password as `MAIL_PASSWORD`

### 5. Run the app

```bash
python run.py
```

Open http://localhost:5000

---

## How the Threshold Works

| Type | Example Input | Behavior |
|---|---|---|
| **Absolute** | `10` | Alert when seats ≤ 10 |
| **Percentage** | `50` | Alert when seats drop ≥ 50% from initial count |

For percentage thresholds, the actual seat threshold is calculated on the **first successful API check** (which sets `initial_count`). Subsequent checks compare against the derived absolute number.

---

## Maintenance Window

The APScheduler job checks IST time before each run. If it falls between **11:30 PM and 12:30 AM IST**, the cycle is skipped entirely — no API calls, no wasted credits.

---

## API Used

**Indian Railway IRCTC API** via RapidAPI  
https://rapidapi.com/IRCTC1/api/indian-railway-irctc

Endpoints used:
- `GET /api/v3/checkSeatAvailability` — seat count
- `GET /api/v3/getTrainDetails` — train name lookup  -nope
- `GET /api/v3/getStationByName` — station autocomplete  -nope

---

## Database Schema

- **users** — accounts with hashed passwords and verification flag
- **tokens** — email verification & password reset (hashed, TTL-enforced)
- **tracking_tasks** — train + date + class + threshold + status
- **notification_logs** — history of every email sent

SQLite file is created automatically at `instance/irctc_tracker.db`.

---


