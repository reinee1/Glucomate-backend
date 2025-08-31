from app.extensions import db

class UserCondition(db.Model):
    __tablename__ = "user_condition"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    condition_id = db.Column(db.Integer, db.ForeignKey("condition.id", ondelete="CASCADE"), nullable=False, index=True)
    other = db.Column(db.String(255), nullable=True)  # free text when 'other' is selected

    __table_args__ = (db.UniqueConstraint("user_id", "condition_id", name="uq_user_condition"),)

    user = db.relationship("User", backref=db.backref("user_conditions", cascade="all,delete-orphan"))
    condition = db.relationship("Condition", backref=db.backref("user_links", cascade="all,delete-orphan"))
