import logging
from datetime import datetime, timezone
import pytz

log = logging.getLogger("irctc_tracker.worker")
IST = pytz.timezone("Asia/Kolkata")


def _in_maintenance_window(cfg) -> bool:
    """
    Returns True if current IST time falls in the IRCTC maintenance window
    (default 23:30 – 00:30 IST).
    """
    now = datetime.now(IST)
    h, m = now.hour, now.minute

    start_h = cfg["MAINTENANCE_START_HOUR"]
    start_m = cfg["MAINTENANCE_START_MIN"]
    end_h   = cfg["MAINTENANCE_END_HOUR"]
    end_m   = cfg["MAINTENANCE_END_MIN"]

    # Convert to minutes-since-midnight for easy comparison
    cur_min   = h * 60 + m
    start_min = start_h * 60 + start_m   # e.g. 23*60+30 = 1410
    end_min   = end_h   * 60 + end_m     # e.g.  0*60+30 =   30

    # Window crosses midnight
    if start_min > end_min:
        return cur_min >= start_min or cur_min < end_min
    return start_min <= cur_min < end_min


def run_availability_check(app):
    """
    Called by APScheduler every N minutes.
    Iterates active tasks and fires alerts when thresholds are crossed.
    """
    with app.app_context():
        cfg = app.config

        if _in_maintenance_window(cfg):
            log.info("IRCTC maintenance window — skipping this cycle.")
            return

        from models import TrackingTask, NotificationLog, db
        from services.rail_api    import get_seat_availability
        from services.email_service import send_seat_alert

        # changes tempory initilization
        # def get_seat_availability(*args, **kwargs):
        #     return {"success": True, "seats": 45}

        tasks = TrackingTask.query.filter_by(status="Active").all()
        log.info("Worker: %d active task(s) to check.", len(tasks))

        for task in tasks:
            _process_task(task, db, get_seat_availability, send_seat_alert)


def _process_task(task, db, get_seat_avail_fn, send_alert_fn):
    log.info("Checking task #%d — Train %s %s %s", task.id, task.train_number,
             task.travel_date, task.seat_class)
    try:
        result = get_seat_avail_fn(
            train_number=task.train_number,
            date=task.travel_date,
            seat_class=task.seat_class,
            from_stn=task.from_station,
            to_stn=task.to_station,
        )
        task.last_checked = datetime.now(timezone.utc)
        task.check_count  = (task.check_count or 0) + 1

        if not result["success"]:
            log.warning("Task #%d: API error — %s", task.id, result.get("error"))
            db.session.commit()
            return

        seats = result["seats"]
        task.last_availability = str(seats)
        log.info("Task #%d: seats available = %s", task.id, seats) #--changes---

        # Set initial count on first successful check
        if task.initial_count is None and seats >= 0:
            task.initial_count = seats
            # Compute threshold if percent-based
            if task.threshold_type == "percent" and task.threshold_value:
                task.target_threshold = int(
                    task.initial_count * (1 - task.threshold_value / 100)
                )
            db.session.commit()
            log.info("Task #%d: initial count set to %d, threshold=%d",
                     task.id, task.initial_count, task.target_threshold or -1)
            return   # No alert on first check

        # Check threshold breach
        threshold = task.target_threshold or 0
        if seats >= 0 and seats <= threshold: #condition
            log.info("Task #%d: seats %d ≤ threshold %d → alerting.", task.id, seats, threshold)
            success = send_alert_fn(task, seats)
            log.entry = NotificationLog(
                task_id=task.id, sent_to=task.user_email,
                subject=f"Seat Alert: {task.train_number}",
                seats_avail=seats, success=success,
                error_msg=None if success else "Send failed",
            )
            db.session.add(log.entry)
            if success:
                task.status      = "Notified"
                task.notified_at = datetime.now(timezone.utc)

        db.session.commit()

    except Exception as exc:
        log.exception("Task #%d: unhandled error — %s", task.id, exc)
        db.session.rollback()
