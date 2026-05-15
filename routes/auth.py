from flask          import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login    import login_user, logout_user, login_required, current_user
from app            import db
from models         import User, Token
from services.email_service import (
    send_verification_email, send_verification_otp,
    send_welcome_confirmed, send_password_reset_email
)
from datetime import datetime, timezone, timedelta
import re, random

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ─── Register ─────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        pwd      = request.form.get("password", "")
        pwd2     = request.form.get("confirm_password", "")

        errors = []
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not EMAIL_RE.match(email):
            errors.append("Invalid email address.")
        if len(pwd) < 8:
            errors.append("Password must be at least 8 characters.")
        if pwd != pwd2:
            errors.append("Passwords do not match.")
        if User.query.filter_by(username=username).first():
            errors.append("Username already taken.")
        if User.query.filter_by(email=email).first():
            errors.append("Email already registered.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html")

        user = User(username=username, email=email)
        user.set_password(pwd)

        # Generate a 6-digit OTP and store it on the user
        otp = f"{random.randint(0, 999999):06d}"
        user.otp_code       = otp
        user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        db.session.add(user)
        db.session.commit()

        email_sent = send_verification_otp(user, otp)

        # Store user_id in session so verify-otp page knows who to verify
        session["otp_user_id"] = user.id
        if email_sent:
            flash("Account created! Enter the 6-digit OTP we just sent to your email.", "success")
        else:
            flash(
                "Account created, but couldn\'t send OTP email — "
                "check MAIL_USERNAME / MAIL_PASSWORD in your .env (Gmail needs an App Password). "
                "Use \'Resend OTP\' once email is configured.",
                "warning"
            )
        return redirect(url_for("auth.verify_otp"))

    return render_template("auth/register.html")


# ─── Verify OTP ───────────────────────────────────────────────────────────────

@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    user_id = session.get("otp_user_id")
    if not user_id:
        flash("No pending verification. Please register or log in.", "warning")
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("auth.login"))

    if user.is_verified:
        session.pop("otp_user_id", None)
        flash("Email already verified. Please log in.", "info")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        entered = request.form.get("otp", "").strip()

        if not user.otp_code or not user.otp_expires_at:
            flash("No OTP found. Please request a new one.", "danger")
            return render_template("auth/verify_otp.html", email=user.email)

        if datetime.now(timezone.utc) > user.otp_expires_at.replace(tzinfo=timezone.utc):
            flash("OTP has expired. Please request a new one.", "danger")
            return render_template("auth/verify_otp.html", email=user.email)

        if entered != user.otp_code:
            flash("Incorrect OTP. Please try again.", "danger")
            return render_template("auth/verify_otp.html", email=user.email)

        # OTP is valid — mark verified and clear OTP fields
        user.is_verified   = True
        user.otp_code      = None
        user.otp_expires_at = None
        db.session.commit()

        session.pop("otp_user_id", None)
        send_welcome_confirmed(user)
        flash("Email verified! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/verify_otp.html", email=user.email)


# ─── Resend OTP ───────────────────────────────────────────────────────────────

@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    user_id = session.get("otp_user_id")
    if not user_id:
        flash("No pending verification session.", "warning")
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)
    if user and not user.is_verified:
        otp = f"{random.randint(0, 999999):06d}"
        user.otp_code       = otp
        user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        db.session.commit()
        send_verification_otp(user, otp)

    flash("A new OTP has been sent to your email.", "info")
    return redirect(url_for("auth.verify_otp"))


# ─── Legacy link-based verify (kept for backward compatibility) ───────────────

@auth_bp.route("/verify/<token>")
def verify_email(token):
    t = Token.verify(token, "verify")
    if not t:
        flash("Invalid or expired verification link.", "danger")
        return redirect(url_for("auth.login"))

    user = db.session.get(User, t.user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("auth.login"))

    user.is_verified = True
    t.used = True
    db.session.commit()
    send_welcome_confirmed(user)
    flash("Email verified! You can now log in.", "success")
    return redirect(url_for("auth.login"))


# ─── Resend Verification (for users who lost their OTP session) ───────────────

@auth_bp.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user  = User.query.filter_by(email=email).first()
        if user and not user.is_verified:
            otp = f"{random.randint(0, 999999):06d}"
            user.otp_code       = otp
            user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
            db.session.commit()
            send_verification_otp(user, otp)
            session["otp_user_id"] = user.id
            flash("A new OTP has been sent to your email.", "info")
            return redirect(url_for("auth.verify_otp"))
        # Always show same message to prevent enumeration
        flash("If that email is registered and unverified, we've sent a new OTP.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/resend_verification.html")


# ─── Login ────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password   = request.form.get("password", "")
        remember   = bool(request.form.get("remember"))

        user = (
            User.query.filter_by(email=identifier.lower()).first()
            or User.query.filter_by(username=identifier).first()
        )

        if not user or not user.check_password(password):
            flash("Invalid credentials.", "danger")
            return render_template("auth/login.html")

        if not user.is_verified:
            flash("Please verify your email before logging in. "
                  '<a href="/auth/resend-verification">Resend OTP</a>', "warning")
            return render_template("auth/login.html")

        login_user(user, remember=remember)
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()

        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.dashboard"))

    return render_template("auth/login.html")


# ─── Logout ───────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for("auth.login"))


# ─── Forgot Password ──────────────────────────────────────────────────────────

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user  = User.query.filter_by(email=email).first()
        if user and user.is_verified:
            ttl   = db.get_app().config["PASSWORD_RESET_TOKEN_TTL"]
            token = Token.generate(user.id, "reset", ttl)
            send_password_reset_email(user, token)
        flash("If that email is registered, we've sent a reset link.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html")


# ─── Reset Password ───────────────────────────────────────────────────────────

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    t = Token.verify(token, "reset")
    if not t:
        flash("Invalid or expired reset link.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        pwd  = request.form.get("password", "")
        pwd2 = request.form.get("confirm_password", "")
        if len(pwd) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("auth/reset_password.html", token=token)
        if pwd != pwd2:
            flash("Passwords do not match.", "danger")
            return render_template("auth/reset_password.html", token=token)

        user = db.session.get(User, t.user_id)
        user.set_password(pwd)
        t.used = True
        db.session.commit()
        flash("Password reset successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)
