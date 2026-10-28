from app.db import db


class BlocklistModel(db.Model):
    """
    Revoked JWT ids. A row is only needed until the token would have expired
    anyway; `flask prune-blocklist` removes rows past expires_at.
    """

    __tablename__ = "blocklist"

    jti_blocklist = db.Column(db.String(), primary_key=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
