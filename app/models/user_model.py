from datetime import datetime, timezone

from app.db import db


def _utcnow():
    return datetime.now(timezone.utc)


class UserModel(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(), nullable=False)
    block = db.Column(db.Boolean, default=False, nullable=False)
    # Callable default: evaluated for every INSERT (a plain datetime.now()
    # call here would be evaluated once, at import time, for all rows).
    time_created = db.Column(
        db.DateTime(timezone=True), default=_utcnow, nullable=False
    )
    roles = db.relationship("RoleModel", back_populates="users", secondary="user_role")
