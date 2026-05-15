from datetime import datetime, timezone
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets, hashlib


# ─── User ─────────────────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_verified    = db.Column(db.Boolean, default=False)
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login     = db.Column(db.DateTime, nullable=True)
    otp_code       = db.Column(db.String(6),  nullable=True)
    otp_expires_at = db.Column(db.DateTime,   nullable=True)

    tasks = db.relationship("TrackingTask", backref="owner", lazy=True, cascade="all, delete-orphan")
    tokens = db.relationship("Token", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ─── Token (email verification + password reset) ──────────────────────────────

class Token(db.Model):
    __tablename__ = "tokens"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token_hash = db.Column(db.String(128), unique=True, nullable=False)
    purpose    = db.Column(db.String(20), nullable=False)   # "verify" | "reset"
    expires_at = db.Column(db.DateTime, nullable=False)
    used       = db.Column(db.Boolean, default=False)

    @staticmethod
    def generate(user_id: int, purpose: str, ttl_seconds: int) -> str:
        """Create a token record and return the raw token string."""
        raw   = secrets.token_urlsafe(32)
        hashed = hashlib.sha256(raw.encode()).hexdigest()
        from datetime import timedelta
        record = Token(
            user_id=user_id,
            token_hash=hashed,
            purpose=purpose,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        )
        db.session.add(record)
        db.session.commit()
        return raw

    @staticmethod
    def verify(raw: str, purpose: str):
        """Return Token record if valid, else None."""
        hashed = hashlib.sha256(raw.encode()).hexdigest()
        t = Token.query.filter_by(token_hash=hashed, purpose=purpose, used=False).first()
        if t and t.expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
            return t
        return None


# ─── TrackingTask ─────────────────────────────────────────────────────────────

class TrackingTask(db.Model):
    __tablename__ = "tracking_tasks"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    train_number     = db.Column(db.String(10), nullable=False)
    train_name       = db.Column(db.String(120), nullable=True)
    travel_date      = db.Column(db.String(10), nullable=False)   # DD-MM-YYYY
    seat_class       = db.Column(db.String(5),  nullable=False)
    from_station     = db.Column(db.String(10), nullable=False)
    to_station       = db.Column(db.String(10), nullable=False)
    initial_count    = db.Column(db.Integer, nullable=True)
    target_threshold = db.Column(db.Integer, nullable=True)   # absolute seats
    threshold_type   = db.Column(db.String(10), default="absolute")  # absolute | percent
    threshold_value  = db.Column(db.Float, nullable=True)     # raw input value
    user_email       = db.Column(db.String(120), nullable=False)
    status           = db.Column(db.String(20), default="Active")  # Active | Notified | Paused | Expired
    last_checked     = db.Column(db.DateTime, nullable=True)
    last_availability= db.Column(db.String(50), nullable=True)
    notified_at      = db.Column(db.DateTime, nullable=True)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    check_count      = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Task #{self.id} {self.train_number} {self.travel_date} {self.seat_class}>"


# ─── NotificationLog ──────────────────────────────────────────────────────────

class NotificationLog(db.Model):
    __tablename__ = "notification_logs"

    id         = db.Column(db.Integer, primary_key=True)
    task_id    = db.Column(db.Integer, db.ForeignKey("tracking_tasks.id"), nullable=False)
    sent_to    = db.Column(db.String(120), nullable=False)
    subject    = db.Column(db.String(200), nullable=False)
    seats_avail= db.Column(db.Integer, nullable=True)
    sent_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    success    = db.Column(db.Boolean, default=True)
    error_msg  = db.Column(db.Text, nullable=True)
