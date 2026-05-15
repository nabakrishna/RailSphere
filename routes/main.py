from flask       import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models      import TrackingTask, NotificationLog

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    tasks = (
        TrackingTask.query
        .filter_by(user_id=current_user.id)
        .order_by(TrackingTask.created_at.desc())
        .all()
    )
    active    = sum(1 for t in tasks if t.status == "Active")
    notified  = sum(1 for t in tasks if t.status == "Notified")
    total     = len(tasks)
    return render_template(
        "dashboard.html",
        tasks=tasks, active=active, notified=notified, total=total,
    )
