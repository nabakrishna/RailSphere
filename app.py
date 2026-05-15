from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from apscheduler.schedulers.background import BackgroundScheduler
import logging, atexit

db          = SQLAlchemy()
login_manager = LoginManager()
scheduler   = BackgroundScheduler(timezone="Asia/Kolkata")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("irctc_tracker")


def create_app(config_object="config.Config"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)

    # Ensure the instance folder exists (needed for SQLite on Windows)
    import os
    os.makedirs(app.instance_path, exist_ok=True)

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view        = "auth.login"
    login_manager.login_message     = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    # ── Blueprints ────────────────────────────────────────────────────────────
    from routes.auth   import auth_bp
    from routes.main   import main_bp
    from routes.tasks  import tasks_bp
    from routes.api    import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(api_bp)

    # ── DB & Scheduler ────────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        _start_scheduler(app)

    return app


def _start_scheduler(app):
    from services.worker import run_availability_check
    interval = app.config["SCHEDULER_INTERVAL_MINUTES"]

    scheduler.add_job(
        func=lambda: run_availability_check(app),
        trigger="interval",
        minutes=interval,
        id="availability_check",
        replace_existing=True,
        max_instances=1,
    )
    if not scheduler.running:
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown(wait=False))
        log.info("APScheduler started — checking every %d minutes.", interval)
