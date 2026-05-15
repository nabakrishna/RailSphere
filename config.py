import os
from datetime import timedelta

class Config:
    # ─── Flask ────────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production-!@#$%")
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

    # ─── Database ─────────────────────────────────────────────────────────────
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    _db_path = os.path.join(BASE_DIR, "instance", "irctc_tracker.db")
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or "sqlite:///" + _db_path.replace("\\", "/")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ─── RapidAPI / Indian Rail API ───────────────────────────────────────────
    # Sign up free at: https://rapidapi.com/IRCTC1/api/indian-railway-irctc
    RAPIDAPI_KEY    = os.environ.get("RAPIDAPI_KEY", "YOUR_RAPIDAPI_KEY_HERE")
    RAPIDAPI_HOST   = "irctc1.p.rapidapi.com"
    RAPIDAPI_BASE   = "https://irctc1.p.rapidapi.com"
    
    
    # ─── Email (SMTP) ─────────────────────────────────────────────────────────
    MAIL_SERVER   = os.environ.get("MAIL_SERVER",   "smtp.gmail.com")
    MAIL_PORT     = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS  = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "your_email@gmail.com")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "your_app_password_here")
    MAIL_FROM     = os.environ.get("MAIL_FROM",     "IRCTC Tracker <your_email@gmail.com>")

    # ─── Scheduler ────────────────────────────────────────────────────────────
    SCHEDULER_INTERVAL_MINUTES = int(os.environ.get("SCHEDULER_INTERVAL_MINUTES", 5)) # time 5 min
    # Maintenance window — scheduler sleeps during these hours (IST)
    MAINTENANCE_START_HOUR = 23   # 11:30 PM
    MAINTENANCE_START_MIN  = 30
    MAINTENANCE_END_HOUR   = 0    # 12:30 AM
    MAINTENANCE_END_MIN    = 30

    # ─── Session ──────────────────────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # ─── Email Verification Token TTL (seconds) ────────────────────────────
    EMAIL_VERIFY_TOKEN_TTL = 3600   # 1 hour
    PASSWORD_RESET_TOKEN_TTL = 1800  # 30 minutes


#RAPIDAPI_HOST = "irctc1.p.rapidapi.com"
#RAPIDAPI_BASE = "https://irctc1.p.rapidapi.com"