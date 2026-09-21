BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type WHERE typname = 'token_purpose'
    ) THEN
        CREATE TYPE token_purpose AS ENUM (
            'verify',
            'reset'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_type WHERE typname = 'task_status'
    ) THEN
        CREATE TYPE task_status AS ENUM (
            'Active',
            'Notified',
            'Paused',
            'Expired'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_type WHERE typname = 'threshold_type'
    ) THEN
        CREATE TYPE threshold_type AS ENUM (
            'absolute',
            'percent'
        );
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    username        VARCHAR(80) NOT NULL,
    email           VARCHAR(120) NOT NULL,
    password_hash   VARCHAR(256) NOT NULL,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMPTZ NULL,
    otp_code        VARCHAR(6) NULL,
    otp_expires_at  TIMESTAMPTZ NULL,

    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT chk_users_username_length
        CHECK (char_length(username) >= 3),
    CONSTRAINT chk_users_email_length
        CHECK (char_length(email) >= 5),
    CONSTRAINT chk_users_otp_code
        CHECK (
            otp_code IS NULL
            OR otp_code ~ '^[0-9]{6}$'
        )
);

CREATE TABLE IF NOT EXISTS tokens (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    token_hash      VARCHAR(128) NOT NULL,
    purpose         token_purpose NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    used            BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_tokens_hash UNIQUE (token_hash),

    CONSTRAINT fk_tokens_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tracking_tasks (
    id                BIGSERIAL PRIMARY KEY,
    user_id           BIGINT NOT NULL,
    train_number      VARCHAR(10) NOT NULL,
    train_name        VARCHAR(120),
    travel_date       DATE NOT NULL,
    seat_class        VARCHAR(5) NOT NULL,
    from_station      VARCHAR(10) NOT NULL,
    to_station        VARCHAR(10) NOT NULL,
    initial_count     INTEGER,
    target_threshold  INTEGER,
    threshold_type    threshold_type NOT NULL DEFAULT 'absolute',
    threshold_value   DOUBLE PRECISION,
    user_email        VARCHAR(120) NOT NULL,
    status            task_status NOT NULL DEFAULT 'Active',
    last_checked      TIMESTAMPTZ,
    last_availability INTEGER,
    notified_at       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    check_count       INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT fk_tracking_tasks_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT chk_tracking_tasks_initial_count
        CHECK (
            initial_count IS NULL
            OR initial_count >= 0
        ),

    CONSTRAINT chk_tracking_tasks_target_threshold
        CHECK (
            target_threshold IS NULL
            OR target_threshold >= 0
        ),

    CONSTRAINT chk_tracking_tasks_threshold_value
        CHECK (
            threshold_value IS NULL
            OR threshold_value >= 0
        ),

    CONSTRAINT chk_tracking_tasks_percent
        CHECK (
            threshold_type <> 'percent'
            OR (
                threshold_value IS NULL
                OR (
                    threshold_value >= 0
                    AND threshold_value <= 100
                )
            )
        ),

    CONSTRAINT chk_tracking_tasks_availability
        CHECK (
            last_availability IS NULL
            OR last_availability >= 0
        ),

    CONSTRAINT chk_tracking_tasks_check_count
        CHECK (
            check_count >= 0
        ),

    CONSTRAINT chk_tracking_tasks_stations
        CHECK (
            from_station <> to_station
        )
);

CREATE TABLE IF NOT EXISTS notification_logs (
    id          BIGSERIAL PRIMARY KEY,
    task_id     BIGINT NOT NULL,
    sent_to     VARCHAR(120) NOT NULL,
    subject     VARCHAR(200) NOT NULL,
    seats_avail INTEGER,
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    success     BOOLEAN NOT NULL DEFAULT TRUE,
    error_msg   TEXT,

    CONSTRAINT fk_notification_logs_task
        FOREIGN KEY (task_id)
        REFERENCES tracking_tasks(id)
        ON DELETE CASCADE,

    CONSTRAINT chk_notification_logs_seats
        CHECK (
            seats_avail IS NULL
            OR seats_avail >= 0
        )
);

CREATE INDEX IF NOT EXISTS idx_users_created_at
    ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_last_login
    ON users(last_login);

CREATE INDEX IF NOT EXISTS idx_tokens_user_id
    ON tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_tokens_purpose
    ON tokens(purpose);
CREATE INDEX IF NOT EXISTS idx_tokens_expires_at
    ON tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_tokens_active
    ON tokens(token_hash, purpose, used, expires_at);

CREATE INDEX IF NOT EXISTS idx_tracking_tasks_user_id
    ON tracking_tasks(user_id);

CREATE INDEX IF NOT EXISTS idx_tracking_tasks_status
    ON tracking_tasks(status);

CREATE INDEX IF NOT EXISTS idx_tracking_tasks_travel_date
    ON tracking_tasks(travel_date);

CREATE INDEX IF NOT EXISTS idx_tracking_tasks_train_number
    ON tracking_tasks(train_number);

CREATE INDEX IF NOT EXISTS idx_tracking_tasks_active
    ON tracking_tasks(status, travel_date);

CREATE INDEX IF NOT EXISTS idx_tracking_tasks_user_status
    ON tracking_tasks(user_id, status);

CREATE INDEX IF NOT EXISTS idx_notification_logs_task_id
    ON notification_logs(task_id);

CREATE INDEX IF NOT EXISTS idx_notification_logs_sent_at
    ON notification_logs(sent_at);

CREATE INDEX IF NOT EXISTS idx_notification_logs_success
    ON notification_logs(success);

COMMENT ON TABLE users IS
    'Application users and authentication information';

COMMENT ON TABLE tokens IS
    'Email verification and password reset tokens';

COMMENT ON TABLE tracking_tasks IS
    'Railway seat availability tracking jobs';

COMMENT ON TABLE notification_logs IS
    'History of notification attempts for tracking tasks';

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ
    NOT NULL DEFAULT NOW();

ALTER TABLE tracking_tasks
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ
    NOT NULL DEFAULT NOW();

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_users_updated_at
ON users;
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();
DROP TRIGGER IF EXISTS trg_tracking_tasks_updated_at
ON tracking_tasks;
CREATE TRIGGER trg_tracking_tasks_updated_at
BEFORE UPDATE ON tracking_tasks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

COMMIT;