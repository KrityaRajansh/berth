"""Initial schema

Creates all tables from the SDD domain model, including the exclusion
constraint that stops two confirmed passengers sharing a berth on
overlapping segments.

Revision ID: b89b1fb6dc5d
Revises:
Create Date: 2026-10-26 00:44:57.280758

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b89b1fb6dc5d"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Needed for the "=" operator on plain columns inside a GiST exclusion constraint.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "audit_event",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("entity", sa.String(length=30), nullable=False),
        sa.Column("entity_id", sa.String(length=40), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_event")),
    )
    op.create_table(
        "job_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_name", sa.String(length=40), nullable=False),
        sa.Column("triggered_by", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "RUNNING", "SUCCEEDED", "FAILED", name="jobstatus", native_enum=False, length=20
            ),
            nullable=False,
        ),
        sa.Column("items_processed", sa.Integer(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_run")),
    )
    op.create_table(
        "login_attempt",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_attempt")),
    )
    op.create_index(
        op.f("ix_login_attempt_email_attempted_at"),
        "login_attempt",
        ["email", "attempted_at"],
        unique=False,
    )
    op.create_table(
        "station",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_station")),
        sa.UniqueConstraint("code", name=op.f("uq_station_code")),
    )
    op.create_table(
        "train",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=5), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("running_days", sa.SmallInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_train")),
        sa.UniqueConstraint("number", name=op.f("uq_train_number")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("mobile", sa.String(length=15), nullable=False),
        sa.Column("password_hash", sa.String(length=100), nullable=False),
        sa.Column(
            "role",
            sa.Enum("PASSENGER", "ADMIN", name="role", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.UniqueConstraint("mobile", name=op.f("uq_users_mobile")),
    )
    op.create_table(
        "coach",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("train_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=4), nullable=False),
        sa.Column(
            "travel_class",
            sa.Enum("SL", "3A", "2A", "1A", name="travelclass", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("berth_count", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["train_id"], ["train.id"], name=op.f("fk_coach_train_id_train"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_coach")),
        sa.UniqueConstraint("train_id", "code", name=op.f("uq_coach_train_id_code")),
    )
    op.create_table(
        "route_stop",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("train_id", sa.Integer(), nullable=False),
        sa.Column("seq", sa.SmallInteger(), nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("arrival", sa.Time(), nullable=True),
        sa.Column("departure", sa.Time(), nullable=True),
        sa.Column("day_offset", sa.SmallInteger(), nullable=False),
        sa.Column("distance_km", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["station_id"], ["station.id"], name=op.f("fk_route_stop_station_id_station")
        ),
        sa.ForeignKeyConstraint(
            ["train_id"],
            ["train.id"],
            name=op.f("fk_route_stop_train_id_train"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_route_stop")),
        sa.UniqueConstraint("train_id", "seq", name=op.f("uq_route_stop_train_id_seq")),
        sa.UniqueConstraint(
            "train_id", "station_id", name=op.f("uq_route_stop_train_id_station_id")
        ),
    )
    op.create_table(
        "train_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("train_id", sa.Integer(), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "SCHEDULED",
                "CHART_PREPARED",
                "COMPLETED",
                "CANCELLED",
                name="runstatus",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("chart_prepared_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["train_id"], ["train.id"], name=op.f("fk_train_run_train_id_train")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_train_run")),
        sa.UniqueConstraint("train_id", "run_date", name=op.f("uq_train_run_train_id_run_date")),
    )
    op.create_table(
        "train_run_class",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column(
            "travel_class",
            sa.Enum("SL", "3A", "2A", "1A", name="travelclass", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("berth_capacity", sa.Integer(), nullable=False),
        sa.Column("waitlist_limit", sa.SmallInteger(), nullable=False),
        sa.Column("coaches", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["train_run.id"],
            name=op.f("fk_train_run_class_run_id_train_run"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_train_run_class")),
        sa.UniqueConstraint(
            "run_id", "travel_class", name=op.f("uq_train_run_class_run_id_travel_class")
        ),
    )
    op.create_table(
        "booking",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pnr", sa.String(length=10), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("run_class_id", sa.Integer(), nullable=False),
        sa.Column(
            "travel_class",
            sa.Enum("SL", "3A", "2A", "1A", name="travelclass", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("from_station_id", sa.Integer(), nullable=False),
        sa.Column("to_station_id", sa.Integer(), nullable=False),
        sa.Column("from_seq", sa.SmallInteger(), nullable=False),
        sa.Column("to_seq", sa.SmallInteger(), nullable=False),
        sa.Column("journey_date", sa.Date(), nullable=False),
        sa.Column("departure_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arrival_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("distance_km", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING_PAYMENT",
                "BOOKED",
                "FAILED",
                "EXPIRED",
                "CANCELLED",
                "COMPLETED",
                name="bookingstatus",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("total_fare_paise", sa.Integer(), nullable=False),
        sa.Column("confirm_only", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["from_station_id"], ["station.id"], name=op.f("fk_booking_from_station_id_station")
        ),
        sa.ForeignKeyConstraint(
            ["run_class_id"],
            ["train_run_class.id"],
            name=op.f("fk_booking_run_class_id_train_run_class"),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["train_run.id"], name=op.f("fk_booking_run_id_train_run")
        ),
        sa.ForeignKeyConstraint(
            ["to_station_id"], ["station.id"], name=op.f("fk_booking_to_station_id_station")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_booking_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_booking")),
        sa.UniqueConstraint("pnr", name=op.f("uq_booking_pnr")),
    )
    op.create_index(
        op.f("ix_booking_user_id_journey_date"),
        "booking",
        ["user_id", "journey_date"],
        unique=False,
    )
    op.create_table(
        "passenger",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("run_class_id", sa.Integer(), nullable=False),
        sa.Column("from_seq", sa.SmallInteger(), nullable=False),
        sa.Column("to_seq", sa.SmallInteger(), nullable=False),
        sa.Column("seq_no", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("age", sa.SmallInteger(), nullable=False),
        sa.Column(
            "gender",
            sa.Enum("M", "F", "T", name="gender", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column(
            "berth_pref",
            sa.Enum("LB", "MB", "UB", "SL", "SU", name="berthtype", native_enum=False, length=20),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum("CNF", "WL", "CAN", name="passengerstatus", native_enum=False, length=20),
            nullable=True,
        ),
        sa.Column("coach_code", sa.String(length=4), nullable=True),
        sa.Column("berth_no", sa.SmallInteger(), nullable=True),
        sa.Column(
            "berth_type",
            sa.Enum("LB", "MB", "UB", "SL", "SU", name="berthtype", native_enum=False, length=20),
            nullable=True,
        ),
        sa.Column("wl_seq", sa.Integer(), nullable=True),
        sa.Column("booking_status_label", sa.String(length=20), nullable=True),
        sa.Column("fare_paise", sa.Integer(), nullable=False),
        sa.Column("refund_paise", sa.Integer(), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        postgresql.ExcludeConstraint(
            (sa.column("run_class_id"), "="),
            (sa.column("coach_code"), "="),
            (sa.column("berth_no"), "="),
            (sa.text("int4range(from_seq, to_seq)"), "&&"),
            where=sa.text("status = 'CNF'"),
            using="gist",
            name="ex_passenger_berth_overlap",
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["booking.id"],
            name=op.f("fk_passenger_booking_id_booking"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_class_id"],
            ["train_run_class.id"],
            name=op.f("fk_passenger_run_class_id_train_run_class"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_passenger")),
    )
    op.create_index(
        op.f("ix_passenger_run_class_id_status_wl_seq"),
        "passenger",
        ["run_class_id", "status", "wl_seq"],
        unique=False,
    )
    op.create_table(
        "payment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("instrument", sa.String(length=40), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "INITIATED", "SUCCESS", "FAILED", name="paymentstatus", native_enum=False, length=20
            ),
            nullable=False,
        ),
        sa.Column("gateway_ref", sa.String(length=40), nullable=True),
        sa.Column("failure_reason", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["booking.id"], name=op.f("fk_payment_booking_id_booking")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment")),
    )
    op.create_index(op.f("ix_payment_booking_id"), "payment", ["booking_id"], unique=False)
    op.create_table(
        "refund",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column(
            "reason",
            sa.Enum(
                "USER_CANCELLATION",
                "CHART_PREPARED",
                "RUN_CANCELLED",
                name="refundreason",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("gateway_ref", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["booking.id"], name=op.f("fk_refund_booking_id_booking")
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"], ["payment.id"], name=op.f("fk_refund_payment_id_payment")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refund")),
    )
    op.create_index(op.f("ix_refund_booking_id"), "refund", ["booking_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_refund_booking_id"), table_name="refund")
    op.drop_table("refund")
    op.drop_index(op.f("ix_payment_booking_id"), table_name="payment")
    op.drop_table("payment")
    op.drop_index(op.f("ix_passenger_run_class_id_status_wl_seq"), table_name="passenger")
    op.drop_table("passenger")
    op.drop_index(op.f("ix_booking_user_id_journey_date"), table_name="booking")
    op.drop_table("booking")
    op.drop_table("train_run_class")
    op.drop_table("train_run")
    op.drop_table("route_stop")
    op.drop_table("coach")
    op.drop_table("users")
    op.drop_table("train")
    op.drop_table("station")
    op.drop_index(op.f("ix_login_attempt_email_attempted_at"), table_name="login_attempt")
    op.drop_table("login_attempt")
    op.drop_table("job_run")
    op.drop_table("audit_event")
