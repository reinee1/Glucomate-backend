from app.extensions import db

class Allergy(db.Model):
    __tablename__ = "allergies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


    user = db.relationship("User", backref="allergies")
