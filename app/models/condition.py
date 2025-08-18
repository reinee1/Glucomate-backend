from app.extensions import db

class Condition(db.Model):
    __tablename__ = "condition"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
