from flask       import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app         import db
from models      import TrackingTask, NotificationLog
# from services.rail_api import search_train -- changes -----
import re

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")

CLASSES = ["1A", "2A", "3A", "SL", "CC", "2S", "EC", "FC"]


@tasks_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_task():
    if request.method == "POST":
        train_no      = request.form.get("train_number", "").strip()
        travel_date   = request.form.get("travel_date", "").strip()
        seat_class    = request.form.get("seat_class", "").strip().upper()
        from_stn      = request.form.get("from_station", "").strip().upper()
        to_stn        = request.form.get("to_station", "").strip().upper()
        thresh_type   = request.form.get("threshold_type", "absolute")
        thresh_val    = request.form.get("threshold_value", "")
        notify_email  = request.form.get("notify_email", current_user.email).strip()

        errors = []
        if not re.match(r"^\d{5}$", train_no): #--changes---
            errors.append("Invalid train number — must be exactly 5 digits.") # --chages---
        if not re.match(r"^\d{2}-\d{2}-\d{4}$", travel_date):
            errors.append("Date must be DD-MM-YYYY.")
        if seat_class not in CLASSES:
            errors.append(f"Invalid class. Choose from: {', '.join(CLASSES)}.")
        if not from_stn or not to_stn:
            errors.append("Station codes are required.")
        try:
            thresh_val = float(thresh_val)
            if thresh_val < 0:
                raise ValueError
        except (ValueError, TypeError):
            errors.append("Threshold must be a positive number.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("tasks/new_task.html", classes=CLASSES)

        # Resolve absolute threshold (percent types resolved on first check)
        target = int(thresh_val) if thresh_type == "absolute" else None

        # Fetch train name
        # info = search_train(train_no) --changes--
        # train_name = info.get("train_name", "") if info.get("success") else ""   -- chnages--

        train_name = ""

        task = TrackingTask(
            user_id=current_user.id,
            train_number=train_no,
            train_name=train_name,
            travel_date=travel_date,
            seat_class=seat_class,
            from_station=from_stn,
            to_station=to_stn,
            threshold_type=thresh_type,
            threshold_value=thresh_val,
            target_threshold=target,
            user_email=notify_email,
            status="Active",
        )
        db.session.add(task)
        db.session.commit()
        flash(f"Tracking task #{task.id} created successfully!", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("tasks/new_task.html", classes=CLASSES,
                           default_email=current_user.email)


@tasks_bp.route("/<int:task_id>")
@login_required
def task_detail(task_id):
    task = TrackingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    logs = (
        NotificationLog.query
        .filter_by(task_id=task_id)
        .order_by(NotificationLog.sent_at.desc())
        .limit(20).all()
    )
    return render_template("tasks/task_detail.html", task=task, logs=logs)


@tasks_bp.route("/<int:task_id>/pause", methods=["POST"])
@login_required
def pause_task(task_id):
    task = TrackingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    task.status = "Paused" if task.status == "Active" else "Active"
    db.session.commit()
    flash(f"Task #{task_id} {'paused' if task.status == 'Paused' else 'resumed'}.", "info")
    return redirect(url_for("main.dashboard"))


@tasks_bp.route("/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    task = TrackingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    flash(f"Task #{task_id} deleted.", "info")
    return redirect(url_for("main.dashboard"))


@tasks_bp.route("/<int:task_id>/check-now", methods=["POST"])
@login_required
def check_now(task_id):
    """Manually trigger an availability check for a single task."""
    task = TrackingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    from services.rail_api       import get_seat_availability
    from services.email_service  import send_seat_alert
    from services.worker         import _process_task
    _process_task(task, db, get_seat_availability, send_seat_alert)
    flash(f"Task #{task_id} checked. Latest: {task.last_availability or 'N/A'} seats.", "info")
    return redirect(url_for("tasks.task_detail", task_id=task_id))
