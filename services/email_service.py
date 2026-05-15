import smtplib, logging
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from flask                import current_app, url_for

log = logging.getLogger("irctc_tracker.email")


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _send(to: str, subject: str, html: str, plain: str = "") -> bool:
    cfg = current_app.config
    msg = MIMEMultipart("alternative")
    msg["From"]    = cfg["MAIL_FROM"]
    msg["To"]      = to
    msg["Subject"] = subject
    if plain:
        msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=15) as s:
            s.ehlo()
            if cfg["MAIL_USE_TLS"]:
                s.starttls()
                s.ehlo()
            s.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            s.sendmail(cfg["MAIL_USERNAME"], to, msg.as_string())
        log.info("Email sent to %s | %s", to, subject)
        return True
    except Exception as exc:
        log.error("Email failed → %s | %s", to, exc)
        return False


def _base_html(title: str, body_html: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>
  body{{margin:0;padding:0;background:#0f172a;font-family:'Segoe UI',Arial,sans-serif;color:#e2e8f0}}
  .wrap{{max-width:600px;margin:40px auto;background:#1e293b;border-radius:16px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.5)}}
  .header{{background:linear-gradient(135deg,#6366f1 0%,#0ea5e9 100%);padding:32px 40px;text-align:center}}
  .header h1{{margin:0;font-size:24px;color:#fff;letter-spacing:-.5px}}
  .header p{{margin:8px 0 0;color:rgba(255,255,255,.8);font-size:14px}}
  .body{{padding:36px 40px}}
  .badge{{display:inline-block;padding:4px 12px;border-radius:9999px;font-size:12px;font-weight:600;letter-spacing:.5px;text-transform:uppercase}}
  .badge-blue{{background:#1d4ed8;color:#bfdbfe}}
  .badge-red{{background:#991b1b;color:#fecaca}}
  .badge-green{{background:#166534;color:#bbf7d0}}
  .info-card{{background:#0f172a;border-radius:12px;padding:20px 24px;margin:20px 0}}
  .info-row{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #1e293b;font-size:14px}}
  .info-row:last-child{{border-bottom:none}}
  .info-label{{color:#94a3b8}}
  .info-val{{color:#f1f5f9;font-weight:600}}
  .btn{{display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#6366f1,#0ea5e9);color:#fff;text-decoration:none;border-radius:10px;font-weight:700;font-size:15px;margin:20px 0}}
  .footer{{background:#0f172a;padding:20px 40px;text-align:center;font-size:12px;color:#475569}}
  .alert-bar{{background:#1d4ed8;border-left:4px solid #60a5fa;padding:16px 20px;border-radius:0 8px 8px 0;margin:16px 0;font-size:14px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>🚆 IRCTC Seat Tracker</h1>
    <p>Automated Seat Availability Notifications</p>
  </div>
  <div class="body">{body_html}</div>
  <div class="footer">
    &copy; 2025 IRCTC Seat Tracker &nbsp;|&nbsp; This is an automated message — do not reply.<br/>
    Powered by RapidAPI Indian Railway API
  </div>
</div>
</body>
</html>"""


# ─── Public API ───────────────────────────────────────────────────────────────

def send_verification_otp(user, otp: str) -> bool:
    body = f"""
<h2 style="color:#f1f5f9;margin:0 0 8px">Welcome, {user.username}! 👋</h2>
<p style="color:#94a3b8;margin:0 0 24px">Thanks for signing up. Enter the OTP below to verify your email address and activate your account.</p>
<div class="alert-bar">
  ⏱ This OTP expires in <strong>10 minutes</strong>.
</div>
<div style="text-align:center;margin:32px 0">
  <div style="display:inline-block;background:#0f172a;border:2px solid #6366f1;border-radius:16px;padding:20px 48px">
    <div style="font-size:11px;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">Your OTP</div>
    <div style="font-size:40px;font-weight:800;letter-spacing:12px;color:#f1f5f9;font-family:monospace">{otp}</div>
  </div>
</div>
<p style="font-size:13px;color:#64748b;text-align:center">If you didn't sign up, you can safely ignore this email.</p>"""
    html = _base_html("Verify Your Email — OTP", body)
    plain = f"Hello {user.username},\n\nYour verification OTP is: {otp}\n\nIt expires in 10 minutes."
    return _send(user.email, "Your IRCTC Tracker verification OTP", html, plain)


# Keep old link-based function in case it's referenced elsewhere
def send_verification_email(user, token: str) -> bool:
    from flask import url_for as _url_for
    verify_url = _url_for("auth.verify_email", token=token, _external=True)
    body = f"""
<h2 style="color:#f1f5f9;margin:0 0 8px">Welcome, {user.username}! 👋</h2>
<p style="color:#94a3b8;margin:0 0 24px">Thanks for signing up. Please verify your email address to activate your account and start tracking seats.</p>
<div class="alert-bar">
  ⏱ This link expires in <strong>1 hour</strong>.
</div>
<div style="text-align:center;margin:28px 0">
  <a href="{verify_url}" class="btn">✅ Verify My Email</a>
</div>
<p style="font-size:13px;color:#64748b">If you didn't sign up, you can safely ignore this email.</p>"""
    html = _base_html("Verify Your Email", body)
    plain = f"Hello {user.username},\n\nVerify your email:\n{verify_url}\n\nExpires in 1 hour."
    return _send(user.email, "Verify your IRCTC Tracker account", html, plain)


def send_password_reset_email(user, token: str) -> bool:
    reset_url = url_for("auth.reset_password", token=token, _external=True)
    body = f"""
<h2 style="color:#f1f5f9;margin:0 0 8px">Password Reset Request 🔑</h2>
<p style="color:#94a3b8">We received a request to reset the password for <strong>{user.email}</strong>.</p>
<div class="alert-bar">
  ⏱ This link expires in <strong>30 minutes</strong>.
</div>
<div style="text-align:center;margin:28px 0">
  <a href="{reset_url}" class="btn">🔒 Reset My Password</a>
</div>
<p style="font-size:13px;color:#64748b">If you didn't request this, please ignore this email — your password won't change.</p>"""
    html = _base_html("Password Reset", body)
    plain = f"Reset your password:\n{reset_url}\n\nExpires in 30 minutes."
    return _send(user.email, "Reset your IRCTC Tracker password", html, plain)


def send_seat_alert(task, current_seats: int) -> bool:
    direction = "dropped below" if current_seats <= task.target_threshold else "changed"
    body = f"""
<h2 style="color:#f1f5f9;margin:0 0 4px">🚨 Seat Availability Alert</h2>
<p style="color:#94a3b8;margin:0 0 20px">Seats for your tracked train have {direction} your threshold.</p>
<div class="info-card">
  <div class="info-row"><span class="info-label">Train</span><span class="info-val">🚆 {task.train_number} — {task.train_name or 'N/A'}</span></div>
  <div class="info-row"><span class="info-label">Date</span><span class="info-val">📅 {task.travel_date}</span></div>
  <div class="info-row"><span class="info-label">Class</span><span class="info-val">💺 {task.seat_class}</span></div>
  <div class="info-row"><span class="info-label">Route</span><span class="info-val">📍 {task.from_station} → {task.to_station}</span></div>
  <div class="info-row"><span class="info-label">Seats Available</span><span class="info-val" style="color:#f87171">{current_seats}</span></div>
  <div class="info-row"><span class="info-label">Your Threshold</span><span class="info-val">{task.target_threshold}</span></div>
  <div class="info-row"><span class="info-label">Initial Count</span><span class="info-val">{task.initial_count or 'N/A'}</span></div>
</div>
<p style="color:#94a3b8;font-size:14px">⚡ Act fast — availability can change at any moment. Book at <a href="https://www.irctc.co.in" style="color:#60a5fa">irctc.co.in</a>.</p>"""
    html  = _base_html("Seat Alert", body)
    plain = (
        f"IRCTC Alert: Seats for Train {task.train_number} ({task.seat_class}) on {task.travel_date}\n"
        f"Current seats: {current_seats} | Threshold: {task.target_threshold}\n"
        f"Book now: https://www.irctc.co.in"
    )
    subject = f"🚨 Seat Alert: Train {task.train_number} | {task.seat_class} | {task.travel_date}"
    return _send(task.user_email, subject, html, plain)


def send_welcome_confirmed(user) -> bool:
    body = f"""
<h2 style="color:#f1f5f9;margin:0 0 8px">You're all set, {user.username}! 🎉</h2>
<p style="color:#94a3b8">Your email has been verified. You can now log in and start tracking seat availability.</p>
<div class="info-card">
  <div class="info-row"><span class="info-label">Account</span><span class="info-val">{user.email}</span></div>
  <div class="info-row"><span class="info-label">Status</span><span class="badge badge-green">Verified</span></div>
</div>
<div style="text-align:center;margin:28px 0">
  <a href="{url_for('auth.login', _external=True)}" class="btn">🚀 Start Tracking</a>
</div>"""
    html = _base_html("Account Verified", body)
    return _send(user.email, "Account verified — welcome aboard!", html)
